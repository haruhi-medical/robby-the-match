/**
 * フェーズ6（新版）: 条件ヒアリング — AI対話ベース
 *
 * 心理ヒアリング（4ターン）の後に入る。
 * 13項目を 1〜2 項目ずつ深掘りしながら AI対話で収集。
 * 主要項目が埋まったら「希望条件カルテ」を自動出力して MATCHING へ自動遷移。
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ6（AI対話版）
 */

import {
  PHASES,
  updateCandidate,
  getRecentMessages,
} from "../state-machine.js";
import { buildConditionSystemPrompt, CONDITION_FIELDS } from "../prompts.js";
import { generateResponse } from "../lib/openai.js";

/**
 * 条件ヒアリングの1ターン
 * @returns {Promise<{reply:string, isComplete:boolean, profile:object, provider:string}>}
 */
export async function handleConditionTurn({ candidate, userText, env, db }) {
  // 既存 profile_json 取得
  let profile = {};
  try {
    profile = candidate.profile_json ? JSON.parse(candidate.profile_json) : {};
  } catch {
    profile = {};
  }

  // 会話履歴（直近10）
  const history = await getRecentMessages(db, candidate.id, 10);
  const messages = [...history, { role: "user", content: userText }];

  // システムプロンプトを現状の collected で動的構築
  const systemPrompt = buildConditionSystemPrompt({
    collected: profile,
    displayName: candidate.display_name,
  });

  // JSON Mode で呼び出し
  const { text: rawReply, provider } = await generateResponse({
    systemPrompt,
    messages,
    env,
    maxTokens: 900,
    responseFormat: "json",
  });

  // JSON parse
  let parsed;
  try {
    parsed = JSON.parse(extractJson(rawReply));
  } catch (err) {
    console.error("[condition] JSON parse failed:", err.message);
    // フォールバック: rawReply をそのまま返す
    return {
      reply: rawReply.length > 2 ? rawReply : "すみません、もう一度教えていただけますか？",
      isComplete: false,
      profile,
      provider,
    };
  }

  const extracted = parsed.extracted || {};
  const isComplete = parsed.is_complete === true;
  const replyText = parsed.reply || "";

  // profile マージ（既存優先せず上書き。ただし空文字は無視）
  const mergedProfile = { ...profile };
  for (const [k, v] of Object.entries(extracted)) {
    if (!CONDITION_FIELDS.find((f) => f.key === k)) continue;
    if (v === null || v === undefined || String(v).trim() === "") continue;

    // 配列的な項目（fields_experienced / strengths / weaknesses）は既存に追記
    if (["fields_experienced", "strengths", "weaknesses"].includes(k) && mergedProfile[k]) {
      const existing = String(mergedProfile[k]);
      const newVal = String(v);
      if (!existing.includes(newVal)) {
        mergedProfile[k] = existing + " / " + newVal;
      }
    } else {
      mergedProfile[k] = v;
    }
  }

  const nextPhase = isComplete ? PHASES.MATCHING : PHASES.CONDITION_HEARING;

  await updateCandidate(db, candidate.id, {
    phase: nextPhase,
    profile_json: JSON.stringify(mergedProfile),
  });

  return {
    reply: replyText || "（応答なし）",
    isComplete,
    profile: mergedProfile,
    provider,
  };
}

/** "text ```json {...}``` text" 形式からJSON部分を抽出 */
function extractJson(text) {
  const trimmed = text.trim();
  if (trimmed.startsWith("{")) return trimmed;
  const codeBlock = trimmed.match(/```(?:json)?\s*(\{[\s\S]*?\})\s*```/);
  if (codeBlock) return codeBlock[1];
  const anyObj = trimmed.match(/\{[\s\S]*\}/);
  return anyObj ? anyObj[0] : trimmed;
}

/**
 * 条件ヒアリングへの遷移用「ブリッジ」メッセージ
 * Turn 4 クロージング後、「では条件を詳しく聞かせてください」とスムーズに入る用
 */
export function buildConditionIntroMessage(candidate) {
  const name = candidate.display_name ? `${candidate.display_name}さん` : "お客様";
  return {
    type: "text",
    text:
      `ありがとうございます。\n` +
      `ここから、${name}に合う求人をご提案するために、\n` +
      `もう少し具体的な条件を伺わせてください。\n\n` +
      `まず、看護師としての経験は何年目ですか？\n` +
      `そして、現在の部署での役割（リーダー・プリセプターなど）も教えていただけますか？`,
  };
}
