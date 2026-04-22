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

  // 1回目呼び出し
  let { text: rawReply, provider } = await generateResponse({
    systemPrompt,
    messages,
    env,
    maxTokens: 900,
    responseFormat: "json",
  });

  let parsed = tryParseJson(rawReply);
  let replyText = parsed && typeof parsed.reply === "string" ? parsed.reply.trim() : "";

  // reply が空だったら1回だけ再試行（明示的に reply 必須を強調）
  if (!replyText) {
    console.warn("[condition] empty reply on first try. raw=", rawReply?.slice(0, 400));
    const retryPrompt =
      systemPrompt +
      "\n\n【重要・再試行】前回の応答で reply が空でした。" +
      "必ず reply に200文字以内のメッセージ本文（次の質問 or 希望条件カルテ）を埋めてください。" +
      "空の reply は禁止です。";
    const retry = await generateResponse({
      systemPrompt: retryPrompt,
      messages,
      env,
      maxTokens: 900,
      responseFormat: "json",
    });
    rawReply = retry.text;
    provider = retry.provider;
    parsed = tryParseJson(rawReply);
    replyText = parsed && typeof parsed.reply === "string" ? parsed.reply.trim() : "";
  }

  const extracted = parsed?.extracted || {};
  let isComplete = parsed?.is_complete === true;

  // profile マージ（空文字・null は無視）
  const mergedProfile = { ...profile };
  for (const [k, v] of Object.entries(extracted)) {
    if (!CONDITION_FIELDS.find((f) => f.key === k)) continue;
    if (v === null || v === undefined || String(v).trim() === "") continue;

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

  // 最後の手段: reply がまだ空なら決定的フォールバック（不足フィールド質問 or 要約完成）
  if (!replyText) {
    console.warn("[condition] empty reply after retry, synthesizing fallback");
    const essentialsMissing = findMissingEssentials(mergedProfile);
    if (essentialsMissing.length === 0) {
      replyText = buildStaticConditionSummary(mergedProfile, candidate.display_name);
      isComplete = true;
    } else {
      const name = candidate.display_name ? `${candidate.display_name}さん` : "お客様";
      const nextQ = buildNextQuestion(essentialsMissing[0], name);
      replyText = nextQ;
      isComplete = false;
    }
  }

  const nextPhase = isComplete ? PHASES.MATCHING : PHASES.CONDITION_HEARING;

  await updateCandidate(db, candidate.id, {
    phase: nextPhase,
    profile_json: JSON.stringify(mergedProfile),
  });

  return {
    reply: replyText,
    isComplete,
    profile: mergedProfile,
    provider,
  };
}

function tryParseJson(raw) {
  if (!raw) return null;
  try {
    return JSON.parse(extractJson(raw));
  } catch (err) {
    console.error("[condition] JSON parse failed:", err.message, "raw=", raw.slice(0, 300));
    return null;
  }
}

/** is_complete 判定に必要な主要フィールドのうち未収集のものを返す */
function findMissingEssentials(profile) {
  const essentials = [
    "experience_years",
    "fields_experienced",
    "strengths",
    "workstyle",
    "facility_hope",
    "area",
    "salary_hope",
    "timing",
  ];
  return essentials.filter((k) => !profile[k] || String(profile[k]).trim() === "");
}

/** 機械的な次の質問（AIがコケた時のフォールバック） */
function buildNextQuestion(missingKey, name) {
  const questions = {
    experience_years: `${name}、看護師として何年目になりますか？\n（例: 5年目、10年目以上 など）`,
    fields_experienced: `${name}、これまで主に経験された診療科・分野を教えてください。\n（例: 呼吸器内科、急性期、ICU など）`,
    strengths: `${name}、得意なことや強みがあれば教えてください。\n（例: アセスメント、急変対応、患者指導 など）`,
    workstyle: `${name}、希望の働き方はどれに近いですか？\n◇ 日勤のみ\n◇ 夜勤あり（月2-3回）\n◇ 夜勤あり（月4回以上）\n◇ パート・非常勤\n◇ 夜勤専従`,
    facility_hope: `${name}、希望する施設の種類はありますか？\n◇ 急性期病院\n◇ 回復期・療養\n◇ クリニック・外来\n◇ 訪問看護\n◇ 介護施設\n◇ 精神科\n◇ こだわらない`,
    area: `${name}、希望する勤務エリアを教えてください。\n（例: 横浜・川崎、小田原・県西、湘南 など）`,
    salary_hope: `${name}、希望される年収や月給はありますか？\n（例: 現職と同水準維持、450万以上、こだわらない など）`,
    timing: `${name}、入職の希望時期はいつごろですか？\n◇ できるだけ早く（1ヶ月以内）\n◇ 2-3ヶ月先\n◇ 半年以内\n◇ 半年以上先・情報収集段階`,
  };
  return questions[missingKey] || "次に伺いたい項目があります。少しだけお教えいただけますか？";
}

/** すべての主要項目が揃った際の静的要約（AIが要約出しそこねた時のフォールバック） */
function buildStaticConditionSummary(profile, displayName) {
  const name = displayName ? `${displayName}さん` : "お客様";
  const p = (k) => profile[k] ? String(profile[k]) : "未設定";
  return (
    "希望条件を整理しました。\n\n" +
    `【希望条件カルテ】\n` +
    `◇ プロフィール\n` +
    `  - 看護師経験: ${p("experience_years")}\n` +
    `  - 現在の役割: ${p("current_position")}\n\n` +
    `◇ 経験分野\n  - ${p("fields_experienced")}\n\n` +
    `◇ 強み・スキル\n  - ${p("strengths")}\n\n` +
    `◇ 希望条件\n` +
    `  - 働き方: ${p("workstyle")}\n` +
    `  - 希望施設: ${p("facility_hope")}\n` +
    `  - エリア: ${p("area")}\n` +
    `  - 給与: ${p("salary_hope")}\n` +
    `  - 入職時期: ${p("timing")}\n\n` +
    `この条件で、${name}にマッチする求人を神奈川県内から\n` +
    `AIがお探しします。少しお待ちください。`
  );
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
