/**
 * キャリアシート自動生成（Layer 1: エージェント内部ツール）
 *
 * 発火タイミング: 条件ヒアリング完了時（is_complete=true）直後、
 *                 候補者フローとは非同期で ctx.waitUntil 実行。
 *
 * 用途: 社長が新規病院営業で「この人どうですか？」とFAX/メール撒くための営業資料。
 *       候補者には見せない（Layer 1）。
 *
 * 仕組み:
 *   1. 候補者の全データ（心理ヒアリング + 条件13項目 + 個人情報）を集約
 *   2. AIで担当者推薦コメント3セクション（ご経験/スキル/コメント）を生成
 *   3. A4縦1枚に収まるHTMLテンプレで整形 + D1保存
 *   4. Slackに「新規キャリアシート完成」通知（プレビューURL付き）
 *
 * 参考サンプル: ファル・メイト（薬剤師）+ SMS（OT）のキャリアシート2種
 */

import { updateCandidate, logMessage } from "../state-machine.js";
import { generateResponse } from "../lib/openai.js";
import { postToSlack } from "../lib/slack.js";

/** 候補者のprofileに明記されていない限り、AIに使わせない禁止語 */
const FORBIDDEN_WORDS_IF_UNMENTIONED = [
  "子育て", "子供", "お子さま", "育児", "育休", "産休",
  "家族", "家庭", "夫", "妻", "配偶者", "介護",
  "残業", "有給", "有休", "休日出勤", "サービス残業",
  "ハラスメント", "パワハラ", "うつ",
  "労働環境", "離職率",
];

const RECOMMENDATION_PROMPT = `あなたは看護師専門の人材紹介会社のキャリアアドバイザーです。
病院向け「キャリアシート」の【担当者推薦コメント】を、下記のデータのみで生成してください。

【最重要・絶対遵守】
- データに明記されていない事実・語・推測を**絶対に書かない**
- 以下のワードはデータの【候補者の実発言】に出現した場合のみ使用可:
  子育て / 子供 / 育児 / 育休 / 産休 / 家族 / 家庭 / 夫 / 妻 / 介護 /
  残業 / 有給 / 有休 / 休日出勤 / サービス残業 / 離職率 / パワハラ
- 悩みの「軸」ラベル（例:「労働時間」「人間関係」）から、具体内容を補完しない
  例: 軸=「労働時間」→ "残業少なく" と書くのは禁止。発言にあれば引用OK
- 期間の補完禁止（「3年間」「4年目から」等、データにない数字は書かない）
- 役職の創作禁止（「主任」「副師長」等、現役割に書かれていないものは使わない）

【出力形式】3セクション、プレーンテキスト、Markdown/JSON/HTML/絵文字禁止

【ご経験】
経験年数・分野・現役割を2-4行で事実のみ。
データにある語をそのまま使う。推測・補完禁止。

【スキル】
"得意・強み" と "書類強み" に記された内容を、そのまま箇条書き（3-5項目）。
勝手にスキル名を追加しない。

【コメント】
150-300字。以下の順で構成:
1. 経験の要約（1文）
2. 希望条件のうち明記されているものを1文で紹介（エリア・給与・働き方・時期のうち明記されたもの）
3. 「お人柄としては、◯◯な方とお見受けしております」で締める
   ◯◯は "得意・強み" から導ける単語1つだけ（例: "リーダーシップのある" "責任感のある"）

書けない場合は短くまとめる。不足は "（要確認）" と明示。嘘より空白が良い。`;

/**
 * キャリアシート生成エントリ
 * @returns {Promise<{serial:string, url?:string}|null>}
 */
export async function generateCareerSheet({ candidateId, env, db }) {
  const candidate = await env.AICA_DB
    .prepare("SELECT * FROM candidates WHERE id = ?")
    .bind(candidateId)
    .first();
  if (!candidate) {
    console.error("[career-sheet] candidate not found:", candidateId);
    return null;
  }

  const profile = safeParseJson(candidate.profile_json);

  // 既に生成済みならスキップ（重複防止）
  if (candidate.career_sheet_serial && candidate.career_sheet_html) {
    console.log("[career-sheet] already generated:", candidate.career_sheet_serial);
    return { serial: candidate.career_sheet_serial };
  }

  // 候補者の実発言を抽出（ハルシネーション防止用の事実ソース）
  const quotes = await extractCandidateQuotes(env.AICA_DB, candidateId);

  // AI推薦コメント生成
  let recommendation = "";
  let provider = "none";
  try {
    const blob = buildCandidateBlob(candidate, profile, quotes);
    const r = await generateResponse({
      systemPrompt: RECOMMENDATION_PROMPT,
      messages: [{ role: "user", content: blob }],
      env,
      maxTokens: 800,
    });
    recommendation = r.text;
    provider = r.provider;

    // 禁止語チェック: 候補者の実発言になく、かつ profile/書類情報にもない禁止語が
    // 推薦コメントに混入していたら、1回だけ再試行（明示的な排除指示付き）
    const leaked = findHallucinatedWords(recommendation, candidate, profile, quotes);
    if (leaked.length > 0) {
      console.warn("[career-sheet] hallucinated words detected:", leaked);
      const retryPrompt =
        RECOMMENDATION_PROMPT +
        "\n\n【再試行・厳密モード】前回の出力に以下の禁止語が混入しました: " +
        leaked.join(", ") +
        "。これらの語は今回の候補者データと発言履歴に**一切出現していません**。" +
        "絶対に使わないでください。書く事実が不足する場合は、該当セクションを短く削り、『（要確認）』と明示してください。";
      const retry = await generateResponse({
        systemPrompt: retryPrompt,
        messages: [{ role: "user", content: blob }],
        env,
        maxTokens: 800,
      });
      const leakedRetry = findHallucinatedWords(retry.text, candidate, profile, quotes);
      if (leakedRetry.length === 0) {
        recommendation = retry.text;
        provider = retry.provider + "-retry";
      } else {
        // 2回目も混入 → 禁止語をマスクして採用（最終防衛）
        console.warn("[career-sheet] retry still has leaks:", leakedRetry);
        recommendation = maskForbiddenWords(retry.text, leakedRetry);
        provider = retry.provider + "-masked";
      }
    }
  } catch (err) {
    console.error("[career-sheet] recommendation AI failed:", err.message);
    recommendation =
      `【ご経験】\n${profile.experience_years || "-"}年目 / ${profile.fields_experienced || "-"}\n\n` +
      `【スキル】\n${profile.strengths || "-"}\n\n` +
      `【コメント】\n（AI生成失敗: ${err.message}。社長による手動記載が必要）`;
  }

  // シリアル番号（NR-YYYYMMDD-XXXX）
  const serial = makeSerial();

  // 匿名化されたイニシャル氏名
  const initials = toInitials(candidate);
  const age = ageOf(candidate.birth_date);
  const ageStr = age !== null ? `${age}歳` : "非公開";

  // HTML組み立て
  const html = renderCareerSheetHtml({
    serial,
    candidate,
    profile,
    initials,
    ageStr,
    recommendation,
  });

  const now = Date.now();
  await updateCandidate(db, candidateId, {
    career_sheet_serial: serial,
    career_sheet_html: html,
    career_sheet_generated_at: now,
  });

  await logMessage(
    db,
    candidateId,
    "assistant",
    `[career-sheet-generated] serial=${serial} html_len=${html.length}`,
    candidate.phase,
    0,
    `career-sheet-${provider}`
  );

  // Slack通知
  const workerBase = env.AICA_WORKER_URL || "https://nurserobby-aica-api.robby-the-robot-2026.workers.dev";
  const viewUrl = `${workerBase}/career-sheet/${serial}`;
  try {
    await notifySlackNewCareerSheet({
      candidate,
      profile,
      initials,
      ageStr,
      serial,
      viewUrl,
      recommendationPreview: recommendation.slice(0, 400),
      env,
    });
  } catch (err) {
    console.warn("[career-sheet] slack notify failed:", err.message);
  }

  return { serial, url: viewUrl };
}

// ============================================================
// シリアル番号
// ============================================================
function makeSerial() {
  const d = new Date();
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(d.getUTCDate()).padStart(2, "0");
  const rand = Math.floor(Math.random() * 9000 + 1000);
  return `NR-${yyyy}${mm}${dd}-${rand}`;
}

// ============================================================
// 匿名化: 氏名 → イニシャル+様
// ============================================================
function toInitials(candidate) {
  const name = candidate.full_name || candidate.display_name || "";
  const kana = candidate.full_name_kana || "";

  if (kana) {
    // 「さとう みさき」→「S・M様」
    const parts = kana.split(/[\s　]+/).filter(Boolean);
    if (parts.length >= 2) {
      const surname = hiraKataToRomajiInitial(parts[0]);
      const given = hiraKataToRomajiInitial(parts.slice(1).join(""));
      if (surname && given) return `${given}・${surname}様`;
    }
  }

  // fallback: full_name の姓名（スペース区切り）
  if (name.includes(" ") || name.includes("　")) {
    const parts = name.split(/[\s　]+/).filter(Boolean);
    if (parts.length >= 2) {
      const surname = parts[0][0];
      const given = parts.slice(1).join("")[0];
      if (surname && given) return `${given}・${surname}様`;
    }
  }
  // display_name の先頭 / 最後
  if (name.length >= 2) {
    return `${name[name.length - 1]}・${name[0]}様`;
  }
  return "ご本人様";
}

/** ひらがな/カタカナ → ローマ字先頭1文字 */
function hiraKataToRomajiInitial(s) {
  if (!s) return "";
  const c = s[0];
  const table = {
    あ: "A", い: "I", う: "U", え: "E", お: "O",
    か: "K", き: "K", く: "K", け: "K", こ: "K",
    さ: "S", し: "S", す: "S", せ: "S", そ: "S",
    た: "T", ち: "C", つ: "T", て: "T", と: "T",
    な: "N", に: "N", ぬ: "N", ね: "N", の: "N",
    は: "H", ひ: "H", ふ: "F", へ: "H", ほ: "H",
    ま: "M", み: "M", む: "M", め: "M", も: "M",
    や: "Y", ゆ: "Y", よ: "Y",
    ら: "R", り: "R", る: "R", れ: "R", ろ: "R",
    わ: "W", を: "W",
    が: "G", ぎ: "G", ぐ: "G", げ: "G", ご: "G",
    ざ: "Z", じ: "J", ず: "Z", ぜ: "Z", ぞ: "Z",
    だ: "D", ぢ: "J", づ: "Z", で: "D", ど: "D",
    ば: "B", び: "B", ぶ: "B", べ: "B", ぼ: "B",
    ぱ: "P", ぴ: "P", ぷ: "P", ぺ: "P", ぽ: "P",
    ア: "A", イ: "I", ウ: "U", エ: "E", オ: "O",
    カ: "K", キ: "K", ク: "K", ケ: "K", コ: "K",
    サ: "S", シ: "S", ス: "S", セ: "S", ソ: "S",
    タ: "T", チ: "C", ツ: "T", テ: "T", ト: "T",
    ナ: "N", ニ: "N", ヌ: "N", ネ: "N", ノ: "N",
    ハ: "H", ヒ: "H", フ: "F", ヘ: "H", ホ: "H",
    マ: "M", ミ: "M", ム: "M", メ: "M", モ: "M",
    ヤ: "Y", ユ: "Y", ヨ: "Y",
    ラ: "R", リ: "R", ル: "R", レ: "R", ロ: "R",
  };
  return table[c] || c.toUpperCase();
}

// ============================================================
// 年齢算出
// ============================================================
function ageOf(birthStr) {
  if (!birthStr) return null;
  const m = birthStr.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!m) return null;
  const birth = new Date(Date.UTC(parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3])));
  const now = new Date();
  let age = now.getUTCFullYear() - birth.getUTCFullYear();
  const beforeBD =
    now.getUTCMonth() < birth.getUTCMonth() ||
    (now.getUTCMonth() === birth.getUTCMonth() && now.getUTCDate() < birth.getUTCDate());
  if (beforeBD) age--;
  return age;
}

// ============================================================
// 候補者の実発言を抽出（ハルシネーション防止のファクトソース）
// ============================================================
async function extractCandidateQuotes(db, candidateId) {
  try {
    const res = await db
      .prepare(
        `SELECT content, phase FROM messages
         WHERE candidate_id = ? AND role = 'user'
         ORDER BY created_at DESC LIMIT 40`
      )
      .bind(candidateId)
      .all();
    const rows = res.results || [];
    const quotes = [];
    for (const r of rows) {
      let t = (r.content || "").trim();
      if (t.startsWith("[voice] ")) t = t.slice(8).trim();
      if (t.length < 5) continue;
      if (t.length > 250) t = t.slice(0, 250) + "…";
      quotes.push(t);
    }
    return quotes.slice(0, 15);
  } catch (err) {
    console.warn("[career-sheet] quotes extraction failed:", err.message);
    return [];
  }
}

/**
 * 推薦コメントに混入した禁止語を検出。
 * 候補者の発言履歴 + profile + 書類情報に出現しない禁止語のみを問題視する。
 */
function findHallucinatedWords(text, candidate, profile, quotes) {
  if (!text) return [];
  const corpus = [
    candidate.root_cause || "",
    candidate.work_history || "",
    candidate.apply_strengths || "",
    ...Object.values(profile || {}).filter((v) => typeof v === "string"),
    ...quotes,
  ].join("\n");

  const leaked = [];
  for (const word of FORBIDDEN_WORDS_IF_UNMENTIONED) {
    if (text.includes(word) && !corpus.includes(word)) {
      leaked.push(word);
    }
  }
  return leaked;
}

/** 禁止語を伏せ字化（最終防衛） */
function maskForbiddenWords(text, words) {
  let out = text;
  for (const w of words) {
    out = out.split(w).join("（※）");
  }
  return out + "\n\n（注: 自動生成で推測が混入したため、一部をマスクしました）";
}

// ============================================================
// AIに渡すデータブロブ
// ============================================================
function buildCandidateBlob(candidate, profile, quotes = []) {
  const lines = [];
  lines.push("【候補者情報（匿名化用）】");
  lines.push(`年齢: ${ageOf(candidate.birth_date) || "？"}歳`);
  lines.push(`看護師経験: ${profile.experience_years || "？"}`);
  lines.push(`現役割: ${profile.current_position || "？"}`);
  lines.push(`経験分野: ${profile.fields_experienced || "？"}`);
  // apply_strengths が「任せる」「特になし」等の非情報的回答なら無視
  const applyStr = candidate.apply_strengths && !/^(任せる|特になし|なし|思いつかない|わからない)$/.test(candidate.apply_strengths.trim())
    ? candidate.apply_strengths
    : "";
  lines.push(`得意・強み: ${profile.strengths || "？"}${applyStr ? " / " + applyStr : ""}`);
  lines.push(`苦手: ${profile.weaknesses || "？"}`);
  lines.push(`希望施設: ${profile.facility_hope || "？"}`);
  lines.push(`希望の理由: ${profile.facility_reason || "？"}`);
  lines.push(`希望働き方: ${profile.workstyle || "？"}`);
  lines.push(`夜勤詳細: ${profile.night_shift_detail || "？"}`);
  lines.push(`希望エリア: ${profile.area || "？"}`);
  lines.push(`希望給与: ${profile.salary_hope || "？"}`);
  lines.push(`入職時期: ${profile.timing || "？"}`);
  lines.push("");
  lines.push("【心理ヒアリング要点】");
  lines.push(`悩みの軸: ${labelOfAxis(candidate.axis)}`);
  lines.push(`根本原因（1文要約）: ${candidate.root_cause || "？"}`);
  lines.push("");
  lines.push("【書類ヒアリング】");
  lines.push(`免許取得: ${candidate.license_acquired || "？"}`);
  lines.push(`勤務歴: ${candidate.work_history || "？"}`);
  lines.push(`保有資格: ${candidate.certifications || "特になし"}`);
  if (quotes.length > 0) {
    lines.push("");
    lines.push("【候補者の実発言（この範囲のみ引用可）】");
    quotes.forEach((q, i) => {
      lines.push(`  ${i + 1}) ${q}`);
    });
  }
  return lines.join("\n");
}

function formatExperienceYears(v) {
  if (v === null || v === undefined || String(v).trim() === "") return "未確認";
  const s = String(v).trim();
  // 数値のみなら「X年目」に
  if (/^\d+$/.test(s)) return `${s}年目`;
  // 「10」が混在した「10年」「10年目」等はそのまま
  return s;
}

function formatLicense(v) {
  if (!v) return "未確認";
  const s = String(v).trim();
  // ISO形式 "2016-03" を「2016年3月」に
  const m = s.match(/^(\d{4})-(\d{1,2})$/);
  if (m) return `${m[1]}年${parseInt(m[2], 10)}月`;
  return s;
}

function labelOfAxis(axis) {
  const map = {
    relationship: "人間関係",
    time: "労働時間",
    salary: "給与・待遇",
    career: "キャリア・やりがい",
    family: "家庭・子育て・介護",
    vague: "漠然",
  };
  return map[axis] || "不明";
}

// ============================================================
// HTML テンプレート（A4 縦1枚）
// ============================================================
function renderCareerSheetHtml({ serial, candidate, profile, initials, ageStr, recommendation }) {
  const now = new Date();
  const updated = `${now.getUTCFullYear()}-${String(now.getUTCMonth() + 1).padStart(2, "0")}-${String(now.getUTCDate()).padStart(2, "0")}`;

  // 勤務歴を3行に整形（生データがあれば1-3行に切る）
  const workHistoryRows = formatWorkHistory(candidate.work_history);

  // 推薦コメントを HTML にエスケープして改行を <br> に
  const recHtml = escapeHtml(recommendation).replace(/\n/g, "<br>");

  const v = {
    serial,
    updated,
    initials: escapeHtml(initials),
    age: escapeHtml(ageStr),
    license: escapeHtml(formatLicense(candidate.license_acquired)),
    experience_years: escapeHtml(formatExperienceYears(profile.experience_years)),
    fields_experienced: escapeHtml(profile.fields_experienced || "未確認"),
    current_position: escapeHtml(profile.current_position || "未確認"),
    workstyle: escapeHtml(profile.workstyle || "未確認"),
    area: escapeHtml(profile.area || "神奈川県内"),
    salary_hope: escapeHtml(profile.salary_hope || "相談"),
    timing: escapeHtml(profile.timing || "相談"),
    facility_hope: escapeHtml(profile.facility_hope || "相談"),
    certifications: escapeHtml(candidate.certifications || "看護師"),
    night_shift_detail: escapeHtml(profile.night_shift_detail || "-"),
    work_history_rows: workHistoryRows,
    recommendation: recHtml,
  };

  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>看護師キャリアシート ${v.serial}</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: "Hiragino Sans", "Yu Gothic", "Meiryo", sans-serif;
    color: #222;
    background: #f6f6f6;
    margin: 0;
    padding: 24px 12px;
    font-size: 13px;
    line-height: 1.6;
  }
  .sheet {
    max-width: 720px;
    margin: 0 auto;
    background: #fff;
    padding: 28px 32px;
    border: 1px solid #d0d0d0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }
  h1 {
    text-align: center;
    font-size: 20px;
    margin: 0 0 4px;
    letter-spacing: 0.05em;
    border-bottom: 2px solid #1a7f64;
    padding-bottom: 6px;
  }
  .meta {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: #666;
    margin-bottom: 16px;
  }
  .section-title {
    background: #e4f1ec;
    color: #0d4f3e;
    font-weight: 600;
    padding: 5px 10px;
    margin: 14px 0 0;
    font-size: 12.5px;
    border-left: 4px solid #1a7f64;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12.5px;
  }
  th, td {
    border: 1px solid #cfcfcf;
    padding: 6px 8px;
    vertical-align: top;
  }
  th {
    background: #f3f3f3;
    font-weight: 600;
    color: #333;
    text-align: left;
    width: 28%;
    white-space: nowrap;
  }
  .name-row th { width: 14%; }
  .name-row td { width: 34%; }
  .recommendation {
    margin-top: 14px;
    padding: 12px 14px;
    background: #fafafa;
    border: 1px solid #d6d6d6;
    border-radius: 2px;
    font-size: 12.5px;
    line-height: 1.8;
    white-space: normal;
  }
  .fax-footer {
    margin-top: 18px;
    border: 2px solid #333;
    padding: 10px 14px;
    font-size: 12.5px;
  }
  .fax-footer .row {
    margin-bottom: 4px;
  }
  .sender {
    margin-top: 12px;
    font-size: 11px;
    color: #555;
    line-height: 1.6;
    text-align: right;
  }
  .caveat {
    margin-top: 8px;
    font-size: 10px;
    color: #888;
    text-align: center;
  }
  @media print {
    body { background: #fff; padding: 0; }
    .sheet { border: none; box-shadow: none; }
  }
</style>
</head>
<body>
<div class="sheet">
  <h1>看護師 キャリアシート</h1>
  <div class="meta">
    <span>紹介シリアル番号: <strong>${v.serial}</strong></span>
    <span>更新日: ${v.updated}</span>
  </div>

  <div class="section-title">候補者プロフィール</div>
  <table>
    <tr class="name-row">
      <th>氏名</th><td>${v.initials}</td>
      <th>年齢</th><td>${v.age}</td>
    </tr>
    <tr class="name-row">
      <th>所在地</th><td colspan="3">神奈川県内（詳細は面接時に別紙で開示）</td>
    </tr>
    <tr class="name-row">
      <th>保有資格</th><td colspan="3">看護師 / ${v.certifications}</td>
    </tr>
    <tr class="name-row">
      <th>資格取得</th><td>${v.license}</td>
      <th>ご経験</th><td>${v.experience_years}</td>
    </tr>
    <tr class="name-row">
      <th>現役割</th><td>${v.current_position}</td>
      <th>経験分野</th><td>${v.fields_experienced}</td>
    </tr>
  </table>

  <div class="section-title">希望条件</div>
  <table>
    <tr>
      <th>雇用形態</th><td>${v.workstyle}</td>
    </tr>
    <tr>
      <th>入職時期</th><td>${v.timing}</td>
    </tr>
    <tr>
      <th>希望給与</th><td>${v.salary_hope}</td>
    </tr>
    <tr>
      <th>希望エリア</th><td>${v.area}</td>
    </tr>
    <tr>
      <th>希望施設</th><td>${v.facility_hope}</td>
    </tr>
    <tr>
      <th>夜勤詳細</th><td>${v.night_shift_detail}</td>
    </tr>
  </table>

  <div class="section-title">職歴（直近）</div>
  <table>
    ${v.work_history_rows}
  </table>

  <div class="section-title">担当者推薦コメント</div>
  <div class="recommendation">
    ${v.recommendation}
  </div>

  <div class="fax-footer">
    <div><strong>【貴社記入欄】</strong></div>
    <div class="row">⇒ 上記求職者に （ <strong>興味あり</strong> ・ <strong>興味なし</strong> ）</div>
    <div class="row">⇒ 興味ありの場合、見学・面接候補日時（ 月 日 時 ）（ 月 日 時 ）</div>
  </div>

  <div class="sender">
    ▼ 送信元 ▼<br>
    <strong>神奈川ナース転職</strong><br>
    電話: （要設定） / メール: （要設定）<br>
    有料職業紹介事業許可番号: （要設定）<br>
    ※紹介料は想定年収の10%（消費税別）
  </div>

  <div class="caveat">
    ※ 求職のタイミングによりご紹介を保証できない場合はご容赦ください。
  </div>
</div>
</body>
</html>`;
}

// ============================================================
// 勤務歴を table行にフォーマット
// ============================================================
function formatWorkHistory(raw) {
  if (!raw || !String(raw).trim()) {
    return `<tr><th>勤務歴</th><td>（未登録）</td></tr>`;
  }
  const lines = String(raw)
    .split(/\n|・|\r/)
    .map((l) => l.trim())
    .filter(Boolean)
    .slice(0, 3);

  if (lines.length === 0) {
    return `<tr><th>勤務歴</th><td>${escapeHtml(raw).replace(/\n/g, "<br>")}</td></tr>`;
  }
  return lines
    .map((line, i) => {
      // 施設名を匿名化（「横浜◯◯病院」→「一般病院 A」等、AI整形なしの簡易版）
      const anonymized = line
        .replace(/[一-龥ぁ-んァ-ンA-Za-z0-9]+病院/g, "一般病院")
        .replace(/[一-龥ぁ-んァ-ンA-Za-z0-9]+クリニック/g, "クリニック")
        .replace(/[一-龥ぁ-んァ-ンA-Za-z0-9]+ステーション/g, "訪問看護ステーション");
      return `<tr><th>職歴${"①②③"[i] || i + 1}</th><td>${escapeHtml(anonymized)}</td></tr>`;
    })
    .join("");
}

// ============================================================
// Slack通知
// ============================================================
async function notifySlackNewCareerSheet({ candidate, profile, initials, ageStr, serial, viewUrl, recommendationPreview, env }) {
  const lines = [
    `📋 *AICA キャリアシート完成*`,
    ``,
    `*候補者*: ${initials} / ${ageStr}`,
    `*経験*: ${profile.experience_years || "?"} / ${profile.fields_experienced || "?"}`,
    `*希望*: ${profile.workstyle || "?"} / ${profile.area || "?"} / ${profile.salary_hope || "?"}`,
    `*悩みの軸*: ${labelOfAxis(candidate.axis)}`,
    `*根本原因*: ${(candidate.root_cause || "").slice(0, 80)}`,
    `*LINE userId*: \`${candidate.id}\``,
    ``,
    `*シリアル*: ${serial}`,
    `*表示URL*: ${viewUrl}`,
    ``,
    `---`,
    `*推薦コメント プレビュー*`,
    "```",
    recommendationPreview,
    "```",
    ``,
    `💡 このシートを求人のある病院・ない病院どちらにもFAX/メール送付できます`,
    `📝 修正したい場合は Slack に \`!cs edit ${serial}\` と書いて指示（今後実装）`,
  ];
  return postToSlack({
    text: lines.join("\n"),
    channel: env.SLACK_CHANNEL_AICA,
    botToken: env.SLACK_BOT_TOKEN,
  });
}

// ============================================================
// HTMLエスケープ
// ============================================================
function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
