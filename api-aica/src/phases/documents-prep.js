/**
 * フェーズ11: 書類作成ヒアリング（5問）
 *
 * DOCUMENTS_PREP_LICENSE → SCHOOL → HISTORY → CERTS → STRENGTHS → DOCUMENTS_GEN
 *
 * 書類（履歴書・職務経歴書・志望動機書）生成に必要な追加情報を収集。
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ11
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildQuickReplyMessage } from "../lib/line.js";

const STEPS = {
  [PHASES.DOCUMENTS_PREP_LICENSE]: {
    column: "license_acquired",
    question:
      "まず、看護師免許を取得された年月を教えてください。\n" +
      "（例: 2020年3月）",
    validate: validateYearMonth,
    next: PHASES.DOCUMENTS_PREP_SCHOOL,
  },
  [PHASES.DOCUMENTS_PREP_SCHOOL]: {
    column: "school_name",
    question:
      "出身の看護学校（大学・専門学校）の正式名称を教えてください。\n" +
      "（例: 横浜医療専門学校 看護学科）",
    validate: validateSchoolName,
    next: PHASES.DOCUMENTS_PREP_HISTORY,
  },
  [PHASES.DOCUMENTS_PREP_HISTORY]: {
    column: "work_history",
    question:
      "これまでに勤務された病院・部署を、年月と合わせて教えてください。\n" +
      "1行にまとめて書いていただければAIが整形します。\n\n" +
      "（例）\n" +
      "2020年4月〜2022年3月 横浜○○病院 内科病棟\n" +
      "2022年4月〜現在 横浜○○病院 内科混合病棟 リーダー",
    validate: validateWorkHistory,
    next: PHASES.DOCUMENTS_PREP_CERTS,
  },
  [PHASES.DOCUMENTS_PREP_CERTS]: {
    column: "certifications",
    question:
      "看護師免許以外の資格があれば教えてください。\n" +
      "なければ「特になし」とお送りください。\n\n" +
      "（例）\n" +
      "・認定看護師（感染管理）\n" +
      "・BLS / ACLS\n" +
      "・ケアマネジャー",
    validate: validateCertifications,
    next: PHASES.DOCUMENTS_PREP_STRENGTHS,
    useQuickReply: true,
  },
  [PHASES.DOCUMENTS_PREP_STRENGTHS]: {
    column: "apply_strengths",
    question:
      "最後に、職務経歴書でアピールしたい強みや実績があれば教えてください。\n" +
      "思いつかなければ「任せる」でも大丈夫です。\n\n" +
      "（例）\n" +
      "・プリセプターとして新人指導3年\n" +
      "・日勤リーダー3年\n" +
      "・褥瘡ケア委員会メンバー",
    validate: validateStrengths,
    next: PHASES.DOCUMENTS_GEN,
    useQuickReply: true,
  },
};

export function isDocumentsPrepPhase(phase) {
  return Object.prototype.hasOwnProperty.call(STEPS, phase);
}

/**
 * Phase 10 → Phase 11 遷移時の最初の質問を返す
 */
export function buildFirstDocumentsPrepMessage() {
  return { type: "text", text: STEPS[PHASES.DOCUMENTS_PREP_LICENSE].question };
}

/**
 * Phase 11 の1ターン処理
 * @returns {Promise<{messages:Array, nextPhase:string}>}
 */
export async function handleDocumentsPrepTurn({ candidate, userText, db }) {
  const step = STEPS[candidate.phase];
  if (!step) {
    return {
      messages: [{ type: "text", text: "処理を続行できませんでした。もう一度お声がけください。" }],
      nextPhase: candidate.phase,
    };
  }

  const result = step.validate(userText);

  if (!result.ok) {
    return {
      messages: [
        {
          type: "text",
          text:
            `申し訳ありません。${result.error}\n\n` +
            `もう一度お願いします。\n\n` +
            step.question,
        },
      ],
      nextPhase: candidate.phase,
    };
  }

  await updateCandidate(db, candidate.id, {
    [step.column]: result.value,
    phase: step.next,
  });

  // 最終ステップ（STRENGTHS）完了 → DOCUMENTS_GEN
  if (step.next === PHASES.DOCUMENTS_GEN) {
    return {
      messages: [
        {
          type: "text",
          text:
            "情報ありがとうございます。\n" +
            "今から履歴書・職務経歴書・志望動機書を作成します。\n" +
            "30秒〜1分ほどお待ちください。\n\n" +
            "（書類生成機能はまもなく実装します。\n" +
            "　しばらくお待ちいただけますと幸いです。）",
        },
      ],
      nextPhase: PHASES.DOCUMENTS_GEN,
    };
  }

  // 次の質問
  const nextStep = STEPS[step.next];
  if (nextStep.useQuickReply && step.next === PHASES.DOCUMENTS_PREP_CERTS) {
    return {
      messages: [
        buildQuickReplyMessage(nextStep.question, [
          { label: "特になし", text: "特になし" },
          { label: "BLS/ACLS", text: "BLS / ACLS" },
          { label: "認定看護師", text: "認定看護師" },
          { label: "ケアマネジャー", text: "ケアマネジャー" },
        ]),
      ],
      nextPhase: step.next,
    };
  }
  if (nextStep.useQuickReply && step.next === PHASES.DOCUMENTS_PREP_STRENGTHS) {
    return {
      messages: [
        buildQuickReplyMessage(nextStep.question, [
          { label: "任せる", text: "任せる" },
        ]),
      ],
      nextPhase: step.next,
    };
  }
  return {
    messages: [{ type: "text", text: nextStep.question }],
    nextPhase: step.next,
  };
}

// ============================================================
// バリデーション
// ============================================================

function validateYearMonth(text) {
  const t = (text || "").trim();
  if (!t) return { ok: false, error: "入力が空のようです" };

  // パターン: YYYY年M月, YYYY-MM, YYYY/MM, YYYY.MM
  let m = t.match(/^(\d{4})\s*年\s*(\d{1,2})\s*月?$/);
  if (!m) m = t.match(/^(\d{4})[-/.](\d{1,2})$/);

  if (!m) {
    return {
      ok: false,
      error: "年月の形式が読み取れませんでした（例: 2020年3月 または 2020-03）",
    };
  }

  const year = parseInt(m[1], 10);
  const month = parseInt(m[2], 10);

  if (year < 1960 || year > new Date().getFullYear()) {
    return { ok: false, error: "年が正しくないようです" };
  }
  if (month < 1 || month > 12) return { ok: false, error: "月が正しくないようです" };

  return { ok: true, value: `${year}-${String(month).padStart(2, "0")}` };
}

function validateSchoolName(text) {
  const t = (text || "").trim();
  if (t.length < 3) return { ok: false, error: "学校名が短いようです" };
  if (t.length > 100) return { ok: false, error: "学校名が長すぎるようです" };
  return { ok: true, value: t };
}

function validateWorkHistory(text) {
  const t = (text || "").trim();
  if (t.length < 5) {
    return {
      ok: false,
      error: "勤務歴が短いようです。病院名と期間（例: 2020年4月〜2022年3月 横浜○○病院 内科）を含めてください",
    };
  }
  if (t.length > 2000) {
    return { ok: false, error: "勤務歴が長すぎるようです" };
  }
  return { ok: true, value: t };
}

function validateCertifications(text) {
  const t = (text || "").trim();
  if (!t) return { ok: false, error: "入力が空のようです。なければ「特になし」とお送りください" };
  if (t.length > 500) return { ok: false, error: "入力が長すぎるようです" };
  // "特になし" または "なし" はそのまま保存
  return { ok: true, value: t };
}

function validateStrengths(text) {
  const t = (text || "").trim();
  if (!t) return { ok: false, error: "入力が空のようです。思いつかなければ「任せる」とお送りください" };
  if (t.length > 1000) return { ok: false, error: "入力が長すぎるようです" };
  return { ok: true, value: t };
}
