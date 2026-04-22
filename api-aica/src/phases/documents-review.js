/**
 * フェーズ13: 書類修正Q&A（phase: DOCUMENTS_REVIEW）
 *
 * Phase 12 で生成した3書類について、ユーザーが修正要望 or 承認する。
 *
 * ユーザー発言の意図:
 *   - 承認: 「これで」「OK」「問題ない」「完璧」「これで進めて」 → APPROVED
 *   - 修正: 「◯◯を直して」「◯◯と書いて」等 → 再生成（該当書類のみ）
 *   - 不明: 再確認メッセージ
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ13
 */

import { PHASES, updateCandidate, logMessage } from "../state-machine.js";
import { pushMessage, buildQuickReplyMessage } from "../lib/line.js";
import { generateResponse } from "../lib/openai.js";
import { buildDocumentsMessages } from "./documents-gen.js";
import { notifyHandoff } from "../lib/slack.js";

/**
 * DOCUMENTS_REVIEW の1ターン処理
 * @returns {Promise<{messages:Array, nextPhase:string, runRegen?:{target:string, instruction:string}}>}
 */
export async function handleDocumentsReviewTurn({ candidate, userText, env, db }) {
  const t = (userText || "").trim();

  // 承認
  if (isApproval(t)) {
    await updateCandidate(db, candidate.id, { phase: PHASES.APPROVED });

    // Slack へ「書類承認済み・病院送付待ち」通知（Phase 14で人間1ボタン承認）
    try {
      const profile = safeParseJson(candidate.profile_json);
      const employer = profile.apply_candidate_employer || "(応募先未設定)";
      await notifyHandoff({
        candidateId: candidate.id,
        displayName: candidate.display_name,
        reason: `書類承認済み → ${employer} への送付準備`,
        phase: PHASES.APPROVED,
        summary:
          `候補者が3書類（履歴書/職務経歴書/志望動機書）を承認しました。\n` +
          `応募先: ${employer}\n` +
          `→ 社長確認 → 病院送付のフローへ`,
        env,
      });
    } catch (err) {
      console.warn("[doc-review] slack notify failed:", err.message);
    }

    return {
      messages: [
        {
          type: "text",
          text:
            "承認ありがとうございます。\n" +
            "この書類で応募を進めます。\n\n" +
            "弊社で最終確認ののち、応募先へ送付します。\n" +
            "進捗は1時間以内にご連絡します。\n\n" +
            "しばらくお待ちください。",
        },
      ],
      nextPhase: PHASES.APPROVED,
    };
  }

  // 修正要望
  if (isEditRequest(t)) {
    const target = detectTargetDocument(t);
    return {
      messages: null,
      nextPhase: PHASES.DOCUMENTS_REVIEW,
      runRegen: { target, instruction: t },
    };
  }

  // 不明 → 再確認
  return {
    messages: [
      buildQuickReplyMessage(
        "ご確認ありがとうございます。\n" +
          "書類はこのままで良いですか？\n" +
          "修正したい箇所があれば、具体的にお知らせください。",
        [
          { label: "これで", text: "これで" },
          { label: "志望動機を直したい", text: "志望動機を少し直したい" },
          { label: "職務経歴を直したい", text: "職務経歴を少し直したい" },
          { label: "履歴書を直したい", text: "履歴書を少し直したい" },
        ]
      ),
    ],
    nextPhase: PHASES.DOCUMENTS_REVIEW,
  };
}

function isApproval(t) {
  return /^(これで|それで|OK|ok|問題ない|大丈夫|完璧|いい(です)?$|はい|お願いします|進めて|承認)/.test(t) ||
    /これで(いい|進|OK|ok|お願い)/.test(t);
}

function isEditRequest(t) {
  return /(直して|修正|変更|書き直|やり直|削(って|除)|追加|入れて|書いて|消(して|去)|だめ|違う|おかしい|間違|訂正)/.test(t);
}

/** どの書類を直すか検出 */
function detectTargetDocument(t) {
  if (/志望動機|動機|motivation|志望理由/.test(t)) return "motivation";
  if (/職務経歴|経歴書|career|PR|自己PR/.test(t)) return "career";
  if (/履歴書|rirekisho|学歴|職歴|資格欄/.test(t)) return "resume";
  return "motivation"; // デフォルト: 最も直しやすい志望動機
}

/**
 * 指定した書類をユーザー要望に基づいて再生成し、Push で送る
 */
export async function regenerateDocument({ candidateId, target, instruction, env, db }) {
  // 最新候補者を取得
  const candidate = await env.AICA_DB
    .prepare("SELECT * FROM candidates WHERE id = ?")
    .bind(candidateId)
    .first();
  if (!candidate) return;

  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "（応募先未設定）";

  // ターゲット書類の現状文面
  const currentMap = {
    resume: candidate.resume_text || "",
    career: candidate.career_text || "",
    motivation: candidate.motivation_text || "",
  };
  const targetName = {
    resume: "履歴書",
    career: "職務経歴書",
    motivation: "志望動機書",
  }[target];
  const currentText = currentMap[target];

  const systemPrompt =
    `あなたは看護師専門のキャリアアドバイザーです。\n` +
    `下記の「${targetName}」を、候補者の修正要望に沿って書き直してください。\n` +
    `\n` +
    `【ルール】\n` +
    `・候補者の要望に該当する箇所のみ修正。それ以外は維持\n` +
    `・嘘を追加しない。情報がない項目は作らない\n` +
    `・元の文字数・フォーマットは維持\n` +
    `・絵文字は使わない\n` +
    (target === "motivation" ? `・応募先「${employer}」の文字列は必ず残す\n` : "") +
    `\n` +
    `【候補者の修正要望】\n${instruction}\n` +
    `\n` +
    `【現状の${targetName}】\n${currentText}\n` +
    `\n` +
    `【出力】${targetName}の全文をプレーンテキストで返してください。Markdown・コードブロック・JSON禁止。`;

  try {
    const { text: newText, provider } = await generateResponse({
      systemPrompt,
      messages: [{ role: "user", content: "修正版をください" }],
      env,
      maxTokens: target === "career" ? 1100 : 900,
    });

    const updateField = {
      resume: "resume_text",
      career: "career_text",
      motivation: "motivation_text",
    }[target];

    await updateCandidate(db, candidateId, { [updateField]: newText });
    await logMessage(
      db,
      candidateId,
      "assistant",
      `[document-regenerated ${target}] ${newText.length}文字`,
      PHASES.DOCUMENTS_REVIEW,
      0,
      `doc-regen-${provider}`
    );

    if (env.LINE_CHANNEL_ACCESS_TOKEN) {
      const preface = {
        type: "text",
        text: `${targetName}を修正しました。ご確認ください。`,
      };
      const body = splitForLine(newText, 4900).map((chunk) => ({ type: "text", text: chunk }));
      const footer = buildQuickReplyMessage(
        "このまま進めますか？他にも直す箇所がありますか？",
        [
          { label: "これで", text: "これで" },
          { label: "もう少し直したい", text: "もう少し直したい" },
        ]
      );
      try {
        await pushMessage(candidateId, [preface, ...body, footer], env.LINE_CHANNEL_ACCESS_TOKEN);
      } catch (err) {
        console.error("[doc-review] push failed:", err.message);
      }
    }
  } catch (err) {
    console.error("[doc-review] regenerate failed:", err.message);
    if (env.LINE_CHANNEL_ACCESS_TOKEN) {
      try {
        await pushMessage(
          candidateId,
          [
            {
              type: "text",
              text:
                "申し訳ありません。\n" +
                "修正中にエラーが発生しました。\n" +
                "もう一度「◯◯を直して」とお送りください。",
            },
          ],
          env.LINE_CHANNEL_ACCESS_TOKEN
        );
      } catch {}
    }
  }
}

function splitForLine(text, maxLen = 4900) {
  if (!text) return ["(未生成)"];
  if (text.length <= maxLen) return [text];
  const chunks = [];
  let remaining = text;
  while (remaining.length > maxLen) {
    const cut = remaining.lastIndexOf("\n", maxLen);
    const pos = cut > maxLen / 2 ? cut : maxLen;
    chunks.push(remaining.slice(0, pos));
    remaining = remaining.slice(pos);
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
