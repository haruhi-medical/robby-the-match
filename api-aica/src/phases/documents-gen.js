/**
 * フェーズ12: AI書類生成（履歴書・職務経歴書・志望動機書）
 *
 * Phase 11 完了直後に自動トリガー。
 * 候補者データから AI で3書類を生成、D1 に保存、LINE に Push で提示。
 * その後 DOCUMENTS_REVIEW へ遷移（Phase 13で修正Q&A）。
 *
 * MVP: テキスト生成のみ。PDF化は後続（R2 + pdf-lib）。
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ12
 */

import { PHASES, updateCandidate, logMessage } from "../state-machine.js";
import { pushMessage } from "../lib/line.js";
import { generateResponse } from "../lib/openai.js";

const RESUME_PROMPT = `あなたは看護師専門の人材紹介会社のキャリアアドバイザーです。
以下の候補者情報から「履歴書」を生成してください。

【出力形式】
下記フォーマットのテキストをそのまま返してください（Markdown・コードブロック・JSON禁止）。

---
【履歴書】

■ 氏名
{氏名}（{ふりがな}）

■ 生年月日
{YYYY年MM月DD日}（{満X歳}）

■ 現住所
※面接時に別紙で開示

■ 電話
※面接時に開示

■ 学歴・職歴

{学歴・職歴を年月ごとに整形}

■ 免許・資格
看護師（{取得年月}）
{その他資格}

■ 本人希望記入欄
{希望条件の要約}
---

【ルール】
・学歴は看護学校から記載。中学・高校は省略可
・職歴は work_history をベースに「YYYY年MM月  △△病院 入職」「YYYY年MM月  △△病院 退職」形式で整形
・現在勤務中なら「YYYY年MM月  現在に至る」で締める
・免許取得は「{年}年{月}  看護師免許取得」の1行
・本人希望欄は「希望施設: / エリア: / 働き方: / 入職時期:」を並べる
・絵文字は使わない`;

const CAREER_PROMPT = `あなたは看護師専門のキャリアアドバイザーです。
以下の候補者情報から「職務経歴書」を生成してください。

【出力形式】
下記フォーマットで1000文字以内のテキストを返してください。

---
【職務経歴書】

■ 職務要約
{2-3行で経歴と得意領域を要約}

■ 職務経歴
{各職歴ごとに「勤務先・期間・役割・業務内容」を箇条書き}

■ 活かせる経験・スキル
{strengths をベースに3-5項目を箇条書き}

■ 保有資格
看護師、{その他資格}

■ 自己PR
{200字程度で、強みと志向性}
---

【ルール】
・全体で1000文字以内を厳守
・看護師の現場語を使う（申し送り、アセスメント、プリセプター、日勤リーダー等）
・「コミュニケーション能力」等の抽象語は避け、具体場面で書く
・絵文字は使わない`;

const MOTIVATION_PROMPT = `あなたは看護師専門のキャリアアドバイザーです。
以下の候補者情報から「志望動機書」を生成してください。

【出力形式】
600文字以内のテキスト（一段落〜三段落）をそのまま返してください。

【ルール】
・志望先の病院名「{employer}」を明記
・候補者が本音ヒアリングで語った「根本的な悩み」や「譲れない条件」と、志望先がそれをどう満たせそうかを紐づける
・嘘は書かない。情報がない強みは書かない
・誇張表現（「必ず貢献できる自信があります」等）は避け、具体例で語る
・「御院」「貴院」どちらでも可。統一すれば良い
・絵文字は使わない

候補者の4ターン心理ヒアリングからの主要な動機・悩みも必ず織り込んでください`;

/**
 * Phase 11 完了後の書類生成エントリポイント（ctx.waitUntil で非同期実行）
 */
export async function runDocumentGeneration({ candidateId, env, db }) {
  // 最新の candidate を取得
  const candidate = await env.AICA_DB
    .prepare("SELECT * FROM candidates WHERE id = ?")
    .bind(candidateId)
    .first();

  if (!candidate) {
    console.error("[doc-gen] candidate not found:", candidateId);
    return;
  }

  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "（応募先未設定）";
  const dataBlob = buildDataBlob(candidate, profile, employer);

  try {
    // 3書類を順次生成
    const [resume, career, motivation] = await Promise.all([
      generateOne({ systemPrompt: RESUME_PROMPT, dataBlob, env, maxTokens: 900 }),
      generateOne({ systemPrompt: CAREER_PROMPT, dataBlob, env, maxTokens: 1100 }),
      generateOne({ systemPrompt: MOTIVATION_PROMPT.replace("{employer}", employer), dataBlob, env, maxTokens: 800 }),
    ]);

    // D1 に保存 + phase 遷移
    await updateCandidate(db, candidateId, {
      resume_text: resume.text,
      career_text: career.text,
      motivation_text: motivation.text,
      phase: PHASES.DOCUMENTS_REVIEW,
    });

    await logMessage(
      db,
      candidateId,
      "assistant",
      `[documents-generated] resume(${resume.text.length}) career(${career.text.length}) motivation(${motivation.text.length})`,
      PHASES.DOCUMENTS_REVIEW,
      0,
      `doc-gen-${resume.provider}`
    );

    // LINE に Push
    if (env.LINE_CHANNEL_ACCESS_TOKEN) {
      const messages = buildDocumentsMessages({ resume: resume.text, career: career.text, motivation: motivation.text, employer });
      try {
        await pushMessage(candidateId, messages, env.LINE_CHANNEL_ACCESS_TOKEN);
      } catch (err) {
        console.error("[doc-gen] push failed:", err.message);
      }
    }
  } catch (err) {
    console.error("[doc-gen] failed:", err.message, err.stack);

    // 失敗時もユーザーに通知（沈黙しない）
    if (env.LINE_CHANNEL_ACCESS_TOKEN) {
      try {
        await pushMessage(
          candidateId,
          [
            {
              type: "text",
              text:
                "申し訳ありません。\n" +
                "書類の作成中にエラーが発生しました。\n" +
                "数分後にもう一度「書類お願いします」と\n" +
                "お送りいただけますでしょうか。",
            },
          ],
          env.LINE_CHANNEL_ACCESS_TOKEN
        );
      } catch {}
    }
    // 再生成できるよう phase を戻す
    await updateCandidate(db, candidateId, { phase: PHASES.DOCUMENTS_GEN });
  }
}

async function generateOne({ systemPrompt, dataBlob, env, maxTokens }) {
  return await generateResponse({
    systemPrompt,
    messages: [{ role: "user", content: dataBlob }],
    env,
    maxTokens,
  });
}

/** AI に渡すデータブロブを組み立て */
function buildDataBlob(candidate, profile, employer) {
  const lines = [];
  lines.push("【候補者情報】");
  lines.push(`氏名: ${candidate.full_name || "未登録"}`);
  lines.push(`ふりがな: ${candidate.full_name_kana || "未登録"}`);
  lines.push(`生年月日: ${candidate.birth_date || "未登録"} (満${ageOf(candidate.birth_date) || "?"}歳)`);
  lines.push(`電話: ${candidate.phone || "未登録"}`);
  lines.push(`現勤務先: ${candidate.current_workplace || "未登録"}`);
  lines.push("");
  lines.push("【書類用ヒアリング】");
  lines.push(`看護師免許取得: ${candidate.license_acquired || "未登録"}`);
  lines.push(`出身校: ${candidate.school_name || "未登録"}`);
  lines.push(`勤務歴:\n${candidate.work_history || "未登録"}`);
  lines.push(`保有資格: ${candidate.certifications || "特になし"}`);
  lines.push(`アピール強み: ${candidate.apply_strengths || "任せる"}`);
  lines.push("");
  lines.push("【条件ヒアリング】");
  lines.push(`経験年数: ${profile.experience_years || "未登録"}`);
  lines.push(`現在の役割: ${profile.current_position || "未登録"}`);
  lines.push(`経験分野: ${profile.fields_experienced || "未登録"}`);
  lines.push(`強み・スキル: ${profile.strengths || "未登録"}`);
  lines.push(`苦手・避けたい: ${profile.weaknesses || "未登録"}`);
  lines.push(`希望施設: ${profile.facility_hope || "未登録"}`);
  lines.push(`希望の理由: ${profile.facility_reason || "未登録"}`);
  lines.push(`希望エリア: ${profile.area || "未登録"}`);
  lines.push(`希望働き方: ${profile.workstyle || "未登録"}`);
  lines.push(`夜勤詳細: ${profile.night_shift_detail || "未登録"}`);
  lines.push(`通勤: ${profile.commute_method || "未登録"}`);
  lines.push(`希望給与: ${profile.salary_hope || "未登録"}`);
  lines.push(`入職希望時期: ${profile.timing || "未登録"}`);
  lines.push("");
  lines.push("【心理ヒアリング要点】");
  lines.push(`悩みの軸: ${candidate.axis || "未分類"}`);
  lines.push(`根本原因: ${candidate.root_cause || "未抽出"}`);
  lines.push("");
  lines.push(`【志望先】 ${employer}`);
  return lines.join("\n");
}

/** 生年月日文字列(YYYY-MM-DD) から満年齢 */
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

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}

/**
 * 3書類を LINE に Push するメッセージ配列
 * LINE Text Message は1通5000字までなので、長文は分割
 */
export function buildDocumentsMessages({ resume, career, motivation, employer }) {
  const messages = [
    {
      type: "text",
      text:
        `${employer} 向けの書類3点が完成しました。\n\n` +
        `◇ 履歴書\n◇ 職務経歴書\n◇ 志望動機書\n\n` +
        `順にお送りします。内容をご確認ください。\n` +
        `修正したい箇所があれば\n` +
        `「ここを直して: ◯◯」\n` +
        `のように具体的にお知らせください。\n\n` +
        `問題なければ「これで」とお送りください。`,
    },
  ];

  // 履歴書
  for (const chunk of splitForLine(resume, 4900)) {
    messages.push({ type: "text", text: chunk });
  }
  // 職務経歴書
  for (const chunk of splitForLine(career, 4900)) {
    messages.push({ type: "text", text: chunk });
  }
  // 志望動機書
  for (const chunk of splitForLine(motivation, 4900)) {
    messages.push({ type: "text", text: chunk });
  }

  messages.push({
    type: "text",
    text:
      "以上が作成した書類3点です。\n\n" +
      "◇ これでOK → 「これで」\n" +
      "◇ 修正したい → 「◯◯を直して」",
  });

  return messages;
}

function splitForLine(text, maxLen = 4900) {
  if (!text) return ["(未生成)"];
  if (text.length <= maxLen) return [text];
  const chunks = [];
  let remaining = text;
  while (remaining.length > maxLen) {
    // 改行境界で切る
    const cut = remaining.lastIndexOf("\n", maxLen);
    const pos = cut > maxLen / 2 ? cut : maxLen;
    chunks.push(remaining.slice(0, pos));
    remaining = remaining.slice(pos);
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}
