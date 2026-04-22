/**
 * フェーズ9: 応募意思確認（phase: APPLY_CONFIRM）
 *
 * Phase 8 (JOB_QA) で「応募したい」と意思表示された直後に入る。
 * 最終確認 → Phase 10 (APPLY_INFO_NAME) へ遷移、または差し戻し。
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ9
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildQuickReplyMessage } from "../lib/line.js";
import { buildFirstApplyInfoMessage } from "./apply-info.js";

/**
 * APPLY_CONFIRM 入口メッセージ
 */
export function buildApplyConfirmMessage({ employer }) {
  const name = employer || "この求人";
  return buildQuickReplyMessage(
    `${name}への応募、進めましょうか？\n\n` +
      `進める場合、次に応募に必要な情報を5つほどお聞きします。\n` +
      `（お名前・ふりがな・生年月日・電話・現在の勤務先）`,
    [
      { label: "進める", text: "進める" },
      { label: "もう少し質問したい", text: "もう少し質問したい" },
      { label: "やっぱり他も見たい", text: "やっぱり他も見たい" },
    ]
  );
}

/**
 * APPLY_CONFIRM 中のユーザー発言を処理
 * @returns {Promise<{messages:Array, nextPhase:string, rerunMatching?:boolean}>}
 */
export async function handleApplyConfirmTurn({ candidate, userText, db }) {
  const t = (userText || "").trim();

  // 進める → Phase 10（個人情報収集）
  if (/^(進め|はい|お願いします|OK|ok|進みます|進む$|進めて)/.test(t) || t === "進める") {
    await updateCandidate(db, candidate.id, { phase: PHASES.APPLY_INFO_NAME });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。ありがとうございます。\n" +
            "ここから、応募に必要な情報を5つだけお聞きします。",
        },
        buildFirstApplyInfoMessage(),
      ],
      nextPhase: PHASES.APPLY_INFO_NAME,
    };
  }

  // 質問に戻る
  if (/質問|もう少し|聞きたい|確認したい/.test(t)) {
    await updateCandidate(db, candidate.id, { phase: PHASES.JOB_QA });
    return {
      messages: [
        {
          type: "text",
          text: "承知しました。どんな点を確認されたいですか？お気軽にどうぞ。",
        },
      ],
      nextPhase: PHASES.JOB_QA,
    };
  }

  // 他も見たい → 再マッチング
  if (/他(も|の)|見たい|別の|他を|もう一度/.test(t)) {
    return { messages: null, nextPhase: PHASES.MATCHING, rerunMatching: true };
  }

  // やめ
  if (/やめ|いい(です)?$|いらない|保留|考え/.test(t)) {
    await updateCandidate(db, candidate.id, { phase: PHASES.PAUSED });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。\n" +
            "お時間のある時にまたお声がけください。\n" +
            "「続きから」で今日の続きに戻れます。",
        },
      ],
      nextPhase: PHASES.PAUSED,
    };
  }

  // 不明 → 再確認メッセージ
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "この求人";
  return {
    messages: [buildApplyConfirmMessage({ employer })],
    nextPhase: PHASES.APPLY_CONFIRM,
  };
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
