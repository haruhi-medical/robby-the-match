/**
 * LINE 音声メッセージの文字起こし（OpenAI Whisper）
 *
 * LINE は m4a (AAC) 形式で音声を返す。OpenAI Whisper は m4a を直接受け付けるので
 * LINE から取得したバイナリを multipart/form-data で Whisper にそのまま送る。
 *
 * 料金: Whisper $0.006/分（約¥1/分）
 * 上限: LINE音声 200秒・100MB、Whisper 25MB
 */

const LINE_CONTENT_URL = "https://api-data.line.me/v2/bot/message/";
const WHISPER_URL = "https://api.openai.com/v1/audio/transcriptions";

/**
 * LINE messageId から音声を取得して Whisper で文字起こし
 * @param {object} params
 * @param {string} params.messageId
 * @param {string} params.accessToken   LINE channel access token
 * @param {string} params.openaiKey     OPENAI_API_KEY
 * @param {string} [params.mimeHint]    LINE の content-type ヒント（なければ audio/m4a）
 * @returns {Promise<string>}           文字起こし結果（前後空白trim済み）
 */
export async function transcribeAudioFromLine({ messageId, accessToken, openaiKey, mimeHint }) {
  if (!messageId) throw new Error("messageId required");
  if (!accessToken) throw new Error("LINE_CHANNEL_ACCESS_TOKEN required");
  if (!openaiKey) throw new Error("OPENAI_API_KEY required");

  // 1. LINE から音声バイナリ取得
  const audioRes = await fetch(`${LINE_CONTENT_URL}${messageId}/content`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!audioRes.ok) {
    const txt = await audioRes.text().catch(() => "");
    throw new Error(`LINE audio fetch ${audioRes.status}: ${txt}`);
  }

  // 一部 LINE レスポンスは content-type が octet-stream のことがある
  const contentType = audioRes.headers.get("content-type") || mimeHint || "audio/m4a";
  const audioBuf = await audioRes.arrayBuffer();

  if (audioBuf.byteLength === 0) {
    throw new Error("empty audio body");
  }

  // サイズチェック: Whisper 25MB まで
  if (audioBuf.byteLength > 24 * 1024 * 1024) {
    throw new Error(`audio too large: ${(audioBuf.byteLength / 1024 / 1024).toFixed(1)}MB`);
  }

  // 2. Whisper に multipart/form-data で送信
  const form = new FormData();
  const blob = new Blob([audioBuf], { type: contentType });
  const ext = mimeToExt(contentType);
  form.append("file", blob, `audio.${ext}`);
  form.append("model", "whisper-1");
  form.append("language", "ja");
  form.append("response_format", "text");
  // prompt: 看護師の現場語を認識させやすくする
  form.append(
    "prompt",
    "看護師、准看護師、師長、主任、プリセプター、アセスメント、夜勤、申し送り、急性期、回復期、訪問看護、クリニック、ICU、HCU、NICU、CCU、オペ介助、看取り、化学療法、人工呼吸器、有給、残業。"
  );

  const transRes = await fetch(WHISPER_URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${openaiKey}` },
    body: form,
  });

  if (!transRes.ok) {
    const errText = await transRes.text().catch(() => "");
    throw new Error(`Whisper ${transRes.status}: ${errText}`);
  }

  const rawText = await transRes.text();
  return (rawText || "").trim();
}

function mimeToExt(mime) {
  if (!mime) return "m4a";
  const lower = mime.toLowerCase();
  if (lower.includes("m4a") || lower.includes("mp4") || lower.includes("aac")) return "m4a";
  if (lower.includes("mpeg") || lower.includes("mp3")) return "mp3";
  if (lower.includes("wav")) return "wav";
  if (lower.includes("ogg") || lower.includes("opus")) return "ogg";
  if (lower.includes("webm")) return "webm";
  return "m4a";
}
