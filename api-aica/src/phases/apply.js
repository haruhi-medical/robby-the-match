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
import {
  buildStage1EndChoice,
  wantsContinueNow,
  wantsPauseUntilLater,
  pauseAt,
} from "../lib/staging.js";

/**
 * APPLY_CONFIRM 入口メッセージ
 */
export function buildApplyConfirmMessage({ employer }) {
  const name = employer || "この求人";
  return buildQuickReplyMessage(
    `${name}への応募、進めましょうか？\n\n` +
      `進める場合、次に応募に必要な情報を4つほどお聞きします。\n` +
      `（お名前・ふりがな・生年月日・現在の勤務先）\n\n` +
      `※ 電話番号は面接日程が決まる時点でお伺いします。\n` +
      `  いまの段階では不要です。`,
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

  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "この求人";

  // Step 1: 「進める」→ Stage 1→2 境界の選択肢を提示（今すぐ/明日以降）
  // resume_from に APPLY_INFO_NAME を仮置き
  if (
    (/^(進め|はい|お願いします|OK|ok|進みます|進む$|進めて)/.test(t) || t === "進める") &&
    !profile.stage12_choice_shown
  ) {
    const newProfile = { ...profile, stage12_choice_shown: true };
    await updateCandidate(db, candidate.id, {
      profile_json: JSON.stringify(newProfile),
    });
    return {
      messages: [buildStage1EndChoice({ employer })],
      nextPhase: PHASES.APPLY_CONFIRM,
    };
  }

  // Step 2a: 「今すぐ続ける」→ Phase 10
  if (profile.stage12_choice_shown && wantsContinueNow(t)) {
    const newProfile = { ...profile };
    delete newProfile.stage12_choice_shown;
    await updateCandidate(db, candidate.id, {
      phase: PHASES.APPLY_INFO_NAME,
      profile_json: JSON.stringify(newProfile),
    });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。\n" +
            "ここから、応募に必要な情報をお聞きします。",
        },
        buildFirstApplyInfoMessage(),
      ],
      nextPhase: PHASES.APPLY_INFO_NAME,
    };
  }

  // Step 2b: 「明日以降」→ PAUSED + resume_from=APPLY_INFO_NAME
  if (profile.stage12_choice_shown && wantsPauseUntilLater(t)) {
    const newProfile = { ...profile };
    delete newProfile.stage12_choice_shown;
    await updateCandidate(db, candidate.id, { profile_json: JSON.stringify(newProfile) });
    await pauseAt({ candidate: { ...candidate, profile_json: JSON.stringify(newProfile) }, resumeFromPhase: PHASES.APPLY_INFO_NAME, db });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。\n" +
            `${employer}への応募準備、ここまで保存しました。\n\n` +
            "お時間のある時に「続きから」とメッセージを送ってください。\n" +
            "そこから応募準備を再開できます。\n\n" +
            "ゆっくり休んでください。",
        },
      ],
      nextPhase: PHASES.PAUSED,
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

  // 不明 → 再確認メッセージ（前段で stage12_choice_shown が立っていれば再度選択肢を）
  if (profile.stage12_choice_shown) {
    return {
      messages: [buildStage1EndChoice({ employer })],
      nextPhase: PHASES.APPLY_CONFIRM,
    };
  }
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
