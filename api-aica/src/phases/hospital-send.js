/**
 * フェーズ14: 病院への推薦文送付準備
 *
 * DOCUMENTS_REVIEW で承認（APPROVED）された候補者について:
 *   1) 推薦文（病院向けメール本文）をAIで生成
 *   2) 応募レコードを D1 applications に追加（status='awaiting_send'）
 *   3) Slack に社長レビュー用の通知を送信（候補者サマリ+推薦文+書類要約）
 *   4) ユーザーに「社長確認中」Push
 *
 * 実際の病院送付は社長が手動。将来的には Slack Interactive の
 * 「送付OK」ボタンで自動メール送信（MailChannels + SPF/DKIM）まで発展予定。
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ14
 */

import { PHASES, updateCandidate, logMessage } from "../state-machine.js";
import { generateResponse } from "../lib/openai.js";
import { pushMessage } from "../lib/line.js";
import { postToSlack } from "../lib/slack.js";

const RECOMMENDATION_PROMPT = `あなたは看護師専門の人材紹介会社の担当者です。
以下の候補者情報と志望動機書を元に、
応募先病院宛の「推薦文（メール本文）」を生成してください。

【出力形式】
冒頭あいさつ〜推薦理由〜書類送付の案内〜締め、を含むメール本文。
件名は先頭行に「件名:」で付ける。署名は「神奈川ナース転職 担当者」で統一。

【ルール】
・候補者名・経歴・強み・志望動機の要約を含める
・候補者が話した本音（志望動機書の引用部分）を1-2箇所引用
・誇張や確約（「必ず活躍します」等）は避け、事実と意欲を伝える
・500-800字程度
・改行を適切に入れる
・絵文字は使わない
・「〜申し上げます」等の丁寧語で統一
・宛名は「◯◯病院 採用ご担当者様」で始める`;

/**
 * DOCUMENTS_REVIEW → APPROVED 遷移直後に呼ぶ
 * ctx.waitUntil で非同期実行される想定
 */
export async function runHospitalSendPrep({ candidateId, env, db, ctx }) {
  const candidate = await env.AICA_DB
    .prepare("SELECT * FROM candidates WHERE id = ?")
    .bind(candidateId)
    .first();
  if (!candidate) {
    console.error("[hospital-send] candidate not found:", candidateId);
    return;
  }

  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "（応募先未設定）";

  // 推薦文 AI 生成
  let recommendation = "";
  let provider = "none";
  try {
    const blob = buildRecommendationBlob(candidate, profile, employer);
    const res = await generateResponse({
      systemPrompt: RECOMMENDATION_PROMPT,
      messages: [{ role: "user", content: blob }],
      env,
      maxTokens: 1100,
    });
    recommendation = res.text;
    provider = res.provider;
  } catch (err) {
    console.error("[hospital-send] AI recommendation failed:", err.message);
    recommendation = `(AI生成失敗: ${err.message}\n\n候補者: ${candidate.full_name || candidate.display_name}\n応募先: ${employer})`;
  }

  // D1 applications に記録
  try {
    await env.AICA_DB
      .prepare(
        `INSERT INTO applications (
           candidate_id, facility_name, job_title, status,
           recommendation_letter, applied_at
         ) VALUES (?, ?, ?, ?, ?, ?)`
      )
      .bind(
        candidateId,
        employer,
        profile.apply_candidate_job_title || null,
        "awaiting_send",
        recommendation,
        Date.now()
      )
      .run();
  } catch (err) {
    console.error("[hospital-send] applications insert failed:", err.message);
  }

  // Slack に通知
  try {
    const summary = buildSlackSummary(candidate, profile, employer, recommendation);
    await postToSlack({
      text: summary,
      channel: env.SLACK_CHANNEL_AICA,
      botToken: env.SLACK_BOT_TOKEN,
    });
  } catch (err) {
    console.error("[hospital-send] slack notify failed:", err.message);
  }

  await logMessage(
    db,
    candidateId,
    "assistant",
    `[hospital-send-prep] recommendation ${recommendation.length}文字 provider=${provider}`,
    PHASES.APPROVED,
    0,
    `hospital-send-${provider}`
  );

  // ユーザーへの Push（承認直後の replyMessage で既に1通送っている想定。
  //  重複になるので、ここではフォローアップのみ ctx 経由で push）
  // 実装上 index.js の APPLY 承認ハンドラから呼ばれるので、本関数は
  // 「バックグラウンドで準備完了」に留め、ユーザー通知は index.js 側に任せる
}

function buildRecommendationBlob(candidate, profile, employer) {
  const lines = [];
  lines.push(`【応募先】 ${employer}`);
  lines.push("");
  lines.push("【候補者プロフィール】");
  lines.push(`  氏名: ${candidate.full_name || "未登録"}（${candidate.full_name_kana || "ふりがな未登録"}）`);
  lines.push(`  生年月日: ${candidate.birth_date || "未登録"}`);
  lines.push(`  現勤務先: ${candidate.current_workplace || "未登録"}`);
  lines.push(`  経験年数: ${profile.experience_years || "未登録"}`);
  lines.push(`  現役割: ${profile.current_position || "未登録"}`);
  lines.push(`  経験分野: ${profile.fields_experienced || "未登録"}`);
  lines.push(`  強み: ${profile.strengths || "未登録"} / ${candidate.apply_strengths || ""}`);
  lines.push(`  希望働き方: ${profile.workstyle || "未登録"}`);
  lines.push(`  希望時期: ${profile.timing || "未登録"}`);
  lines.push(`  悩みの根本: ${candidate.root_cause || "未抽出"}`);
  lines.push("");
  lines.push("【候補者の志望動機書（生成済み）】");
  lines.push(candidate.motivation_text || "（未生成）");
  return lines.join("\n");
}

function buildSlackSummary(candidate, profile, employer, recommendation) {
  const name = candidate.full_name || candidate.display_name || "（名前未登録）";
  const kana = candidate.full_name_kana || "";
  const yearsExp = profile.experience_years || "？";
  const fields = profile.fields_experienced || "？";
  const reasonSnippet = (candidate.root_cause || "").slice(0, 120);

  const lines = [
    `📬 *AICA 書類承認 → 病院送付準備*`,
    ``,
    `*応募先*: ${employer}`,
    `*候補者*: ${name} ${kana ? `(${kana})` : ""}`,
    `*LINE userId*: \`${candidate.id}\``,
    `*経験*: ${yearsExp} / ${fields}`,
    `*希望*: ${profile.workstyle || "？"} / ${profile.area || "？"} / ${profile.salary_hope || "？"} / ${profile.timing || "？"}`,
    `*悩みの根本*: ${reasonSnippet}`,
    ``,
    `---`,
    `*推薦文（案・コピー用）*`,
    `\`\`\``,
    recommendation.length > 2500 ? recommendation.slice(0, 2500) + "\n…(切り詰め)" : recommendation,
    `\`\`\``,
    ``,
    `*次のアクション* (社長対応):`,
    `1. 上記メールを ${employer} 採用担当に送付（もしくは修正してから送付）`,
    `2. 送付後、Slackで \`!aica sent ${candidate.id}\` と返信 → APPLIED 遷移`,
    `3. 1営業日以内に推薦完了通知が候補者に届く`,
  ];
  return lines.join("\n");
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
