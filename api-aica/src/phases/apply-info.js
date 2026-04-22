/**
 * フェーズ10: 個人情報収集（5ステップ）
 *
 * APPLY_INFO_NAME → KANA → BIRTH → PHONE → WORKPLACE → DOCUMENTS_PREP_LICENSE
 *
 * 各ステップで:
 *   1. 入力バリデーション（形式チェック）
 *   2. OK → candidates テーブルに保存 + 次の質問
 *   3. NG → 形式エラー + 同じ質問を再提示
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ10
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildFirstDocumentsPrepMessage } from "./documents-prep.js";

/**
 * 5ステップの定義
 * phase: このステップに入る前の phase（= このステップの回答を待つ状態）
 * column: D1 candidates に保存するカラム名
 * question: AI発話（テキスト）
 * validate: (text) => { ok: boolean, value?: string, error?: string }
 * next: 次の phase
 */
const STEPS = {
  [PHASES.APPLY_INFO_NAME]: {
    column: "full_name",
    question:
      "まず、お名前を教えてください。\n" +
      "漢字で、姓と名の間にスペースを入れてください。\n" +
      "（例: 田中 ミサキ）\n\n" +
      "※ この情報は病院が興味を示した後、\n" +
      "  採用担当者のみに開示されます。",
    validate: validateFullName,
    next: PHASES.APPLY_INFO_KANA,
  },
  [PHASES.APPLY_INFO_KANA]: {
    column: "full_name_kana",
    question:
      "ふりがなをひらがなで教えてください。\n" +
      "（例: たなか みさき）",
    validate: validateKana,
    next: PHASES.APPLY_INFO_BIRTH,
  },
  [PHASES.APPLY_INFO_BIRTH]: {
    column: "birth_date",
    question:
      "生年月日を教えてください。\n" +
      "（例: 1997-06-20、または 1997年6月20日）",
    validate: validateBirthDate,
    next: PHASES.APPLY_INFO_PHONE,
  },
  [PHASES.APPLY_INFO_PHONE]: {
    column: "phone",
    question:
      "緊急連絡先として、携帯電話番号を教えてください。\n" +
      "（例: 09012345678）\n\n" +
      "※ 通常のご連絡はLINEのみです。\n" +
      "  電話は面接日程の緊急変更時など、\n" +
      "  どうしても必要な場合のみです。",
    validate: validatePhone,
    next: PHASES.APPLY_INFO_WORKPLACE,
  },
  [PHASES.APPLY_INFO_WORKPLACE]: {
    column: "current_workplace",
    question:
      "最後に、現在の勤務先の正式名称を教えてください。\n" +
      "（例: 横浜○○病院）\n\n" +
      "※ この情報は応募先には開示されません。\n" +
      "  社内の書類作成のために使用します。",
    validate: validateWorkplace,
    next: PHASES.DOCUMENTS_PREP_LICENSE,
  },
};

/**
 * APPLY_INFO_* のステップか
 */
export function isApplyInfoPhase(phase) {
  return Object.prototype.hasOwnProperty.call(STEPS, phase);
}

/**
 * 入力を処理して、次のステップのメッセージを返す
 * @returns {Promise<{messages: Array, nextPhase: string}>}
 */
export async function handleApplyInfoTurn({ candidate, userText, db }) {
  const step = STEPS[candidate.phase];
  if (!step) {
    // ここには来ないはず
    return {
      messages: [{ type: "text", text: "処理を続行できませんでした。もう一度お声がけください。" }],
      nextPhase: candidate.phase,
    };
  }

  const result = step.validate(userText);

  // バリデーション失敗
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

  // 保存
  await updateCandidate(db, candidate.id, {
    [step.column]: result.value,
    phase: step.next,
  });

  // 最終ステップ完了 → DOCUMENTS_PREP へ
  if (step.next === PHASES.DOCUMENTS_PREP_LICENSE) {
    return {
      messages: [
        {
          type: "text",
          text:
            "ありがとうございます。\n" +
            "個人情報の確認が完了しました。\n\n" +
            "次に、応募書類（履歴書・職務経歴書・志望動機書）を\n" +
            "AIで自動作成します。\n\n" +
            "あと5つほど、書類作成のための質問をさせてください。",
        },
        buildFirstDocumentsPrepMessage(),
      ],
      nextPhase: PHASES.DOCUMENTS_PREP_LICENSE,
    };
  }

  // 次の質問
  const nextStep = STEPS[step.next];
  return {
    messages: [{ type: "text", text: nextStep.question }],
    nextPhase: step.next,
  };
}

/**
 * APPLY_CONFIRM → APPLY_INFO_NAME 遷移時の最初の質問（初回プッシュ用）
 */
export function buildFirstApplyInfoMessage() {
  return { type: "text", text: STEPS[PHASES.APPLY_INFO_NAME].question };
}

// ============================================================
// バリデーション関数
// ============================================================

function validateFullName(text) {
  const t = (text || "").trim();
  if (t.length < 2) return { ok: false, error: "お名前が短いようです" };
  if (t.length > 30) return { ok: false, error: "お名前が長すぎるようです" };
  // 姓と名の間にスペース（全角/半角）
  if (!/[\s　]/.test(t)) {
    return {
      ok: false,
      error: "姓と名の間にスペースを入れていただけますか",
    };
  }
  // ひらがなだけは NG（漢字で）
  if (/^[ぁ-んー\s　]+$/.test(t)) {
    return { ok: false, error: "お名前は漢字で入力していただけますか" };
  }
  return { ok: true, value: t.replace(/\s+/g, " ") };
}

function validateKana(text) {
  const t = (text || "").trim();
  if (t.length < 2) return { ok: false, error: "ふりがなが短いようです" };
  if (t.length > 30) return { ok: false, error: "ふりがなが長すぎるようです" };
  // ひらがな + スペース のみ
  if (!/^[ぁ-んー\s　]+$/.test(t)) {
    return {
      ok: false,
      error: "ひらがなで入力していただけますか（カタカナではなく）",
    };
  }
  return { ok: true, value: t.replace(/[\s　]+/g, " ") };
}

function validateBirthDate(text) {
  const t = (text || "").trim();
  if (!t) return { ok: false, error: "生年月日が空のようです" };

  // パターン1: YYYY-MM-DD または YYYY/MM/DD または YYYY.MM.DD
  let m = t.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/);
  // パターン2: YYYY年M月D日
  if (!m) m = t.match(/^(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日?$/);
  // パターン3: 昭和/平成 対応は省略（入力が出たら追加）

  if (!m) {
    return {
      ok: false,
      error: "日付の形式を読み取れませんでした（例: 1997-06-20 または 1997年6月20日）",
    };
  }

  const year = parseInt(m[1], 10);
  const month = parseInt(m[2], 10);
  const day = parseInt(m[3], 10);

  if (year < 1940 || year > new Date().getFullYear()) {
    return { ok: false, error: "生まれ年が正しくないようです" };
  }
  if (month < 1 || month > 12) return { ok: false, error: "月が正しくないようです" };
  if (day < 1 || day > 31) return { ok: false, error: "日が正しくないようです" };

  // 実在日チェック
  const d = new Date(Date.UTC(year, month - 1, day));
  if (
    d.getUTCFullYear() !== year ||
    d.getUTCMonth() !== month - 1 ||
    d.getUTCDate() !== day
  ) {
    return { ok: false, error: "実在しない日付のようです" };
  }

  // ISO形式で保存
  const mm = String(month).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return { ok: true, value: `${year}-${mm}-${dd}` };
}

function validatePhone(text) {
  const t = (text || "").trim();
  // ハイフン・スペース・括弧を除去
  const digits = t.replace(/[-\s()（）]/g, "");
  if (!/^\d+$/.test(digits)) {
    return { ok: false, error: "電話番号は数字で入力してください" };
  }
  if (digits.length !== 11) {
    return {
      ok: false,
      error: "携帯電話番号は11桁です（例: 09012345678）",
    };
  }
  if (!/^0(70|80|90)/.test(digits)) {
    return {
      ok: false,
      error: "携帯電話番号は070/080/090で始まる番号を入力してください",
    };
  }
  return { ok: true, value: digits };
}

function validateWorkplace(text) {
  const t = (text || "").trim();
  if (t.length < 2) {
    return { ok: false, error: "勤務先名が短いようです" };
  }
  if (t.length > 100) {
    return { ok: false, error: "勤務先名が長すぎるようです" };
  }
  return { ok: true, value: t };
}
