/**
 * 会話の段階分割（3ステージ） + 中断/再開 サポート
 *
 * 社長指示（2026-04-23）: 20問超の一気通貫はミサキが離脱する。
 * 今日（Stage 1）→ 明日（Stage 2）→ 本番前（Stage 3）の3段に分け、
 * 各段の終わりに「続ける or 一旦ここまで」を選べるようにする。
 *
 * Stage 1（初回・約5分）:
 *   Welcome → 4ターン心理ヒアリング → 条件ヒアリング → マッチング → Q&A
 *   = phase NEW..TURN4, CONDITION_HEARING, MATCHING, JOB_QA
 *
 * Stage 2（応募準備・約10分）:
 *   応募意思 → 個人情報5問 → 書類作成ヒアリング5問
 *   = APPLY_CONFIRM..APPLY_INFO_WORKPLACE, DOCUMENTS_PREP_LICENSE..STRENGTHS
 *
 * Stage 3（面接前・約10分）:
 *   書類生成 → 修正Q&A → 承認
 *   = DOCUMENTS_GEN, DOCUMENTS_REVIEW, APPROVED
 *
 * 中断ポイント（最適位置）:
 *   - Stage 1 → Stage 2: JOB_QA で「応募したい」を言った直後の APPLY_CONFIRM
 *   - Stage 2 → Stage 3: DOCUMENTS_PREP_STRENGTHS 回答直後（書類生成前）
 *
 * 再開: PAUSED phase 中に「続きから」「続ける」「再開」「昨日の続き」等の
 *   キーワードで profile_json.resume_from に保存された phase に戻す。
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildQuickReplyMessage } from "../lib/line.js";

/** phase → stage 1/2/3 */
export function phaseToStage(phase) {
  if ([
    PHASES.NEW, PHASES.TURN1, PHASES.TURN2, PHASES.TURN3, PHASES.TURN4,
    PHASES.SUMMARY, PHASES.CONDITION_HEARING, PHASES.MATCHING, PHASES.JOB_QA,
  ].includes(phase)) return 1;

  if ([
    PHASES.APPLY_CONFIRM,
    PHASES.APPLY_INFO_NAME, PHASES.APPLY_INFO_KANA, PHASES.APPLY_INFO_BIRTH,
    PHASES.APPLY_INFO_PHONE, PHASES.APPLY_INFO_WORKPLACE,
    PHASES.DOCUMENTS_PREP_LICENSE, PHASES.DOCUMENTS_PREP_SCHOOL,
    PHASES.DOCUMENTS_PREP_HISTORY, PHASES.DOCUMENTS_PREP_CERTS,
    PHASES.DOCUMENTS_PREP_STRENGTHS,
  ].includes(phase)) return 2;

  if ([
    PHASES.DOCUMENTS_GEN, PHASES.DOCUMENTS_REVIEW, PHASES.APPROVED,
  ].includes(phase)) return 3;

  return null;
}

/**
 * Stage 1終了時の中断/続行選択メッセージ
 * ここは APPLY_CONFIRM で「進める」ボタンを押した直後に表示
 */
export function buildStage1EndChoice({ employer }) {
  const name = employer || "この求人";
  return buildQuickReplyMessage(
    `${name}への応募、進めていきましょう。\n\n` +
      `この先はステップ2「応募準備」です:\n` +
      `◇ 個人情報の確認（4問・約3分）\n` +
      `◇ 書類作成のヒアリング（5問・約5分）\n` +
      `所要時間 合計 約8分\n\n` +
      `今すぐ続けても、明日以降でも大丈夫です。\n` +
      `「続きから」とメッセージを送れば、いつでも再開できます。`,
    [
      { label: "今すぐ続ける", text: "今すぐ続ける" },
      { label: "明日以降にする", text: "明日以降にする" },
    ]
  );
}

/**
 * Stage 2終了時の中断/続行選択メッセージ
 * ここは DOCUMENTS_PREP_STRENGTHS 完了直後、書類生成の前に表示
 */
export function buildStage2EndChoice() {
  return buildQuickReplyMessage(
    `情報ありがとうございます。\n\n` +
      `次はステップ3「面接準備」です:\n` +
      `◇ AI書類の自動生成（履歴書・職務経歴書・志望動機書）\n` +
      `◇ 書類の確認と修正\n` +
      `所要時間 約10分\n\n` +
      `書類は面接の前日までに作成すれば十分間に合います。\n` +
      `今すぐ作成しても、後日でも大丈夫です。`,
    [
      { label: "今すぐ作成する", text: "今すぐ作成する" },
      { label: "面接前に作成する", text: "面接前に作成する" },
    ]
  );
}

/** 「今すぐ続ける」系の意図か */
export function wantsContinueNow(text) {
  const t = (text || "").trim();
  return /^(今すぐ|続ける|進める$|はい$|OK|ok|今(行|やる|作成)|作成する)/.test(t) ||
    /今すぐ(続|進|作成)/.test(t);
}

/** 「明日以降」「後日」系の意図か */
export function wantsPauseUntilLater(text) {
  const t = (text || "").trim();
  return /明日|後日|また(後|今度)|後ほど|一旦|面接前|本番前|あとで|後で|夜|夕方|寝る/.test(t);
}

/** 「続きから」「再開」系の意図か */
export function wantsResume(text) {
  const t = (text || "").trim();
  return /続き(から|をやる|ます|やろう|進め)|再開|続ける$|昨日(の(続|話)|のやつ)|前回の(続|話)|やります$/.test(t);
}

/**
 * 中断 → PAUSED 遷移（resume_from 保存）
 */
export async function pauseAt({ candidate, resumeFromPhase, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const newProfile = { ...profile, resume_from: resumeFromPhase, paused_at: Date.now() };
  await updateCandidate(db, candidate.id, {
    phase: PHASES.PAUSED,
    profile_json: JSON.stringify(newProfile),
  });
}

/**
 * PAUSED → resume_from の phase に復帰
 * @returns {string} 復帰した phase
 */
export async function resumeFrom({ candidate, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const resume = profile.resume_from || PHASES.TURN1;
  const newProfile = { ...profile };
  delete newProfile.resume_from;
  delete newProfile.paused_at;
  await updateCandidate(db, candidate.id, {
    phase: resume,
    profile_json: JSON.stringify(newProfile),
  });
  return resume;
}

/** 再開時の案内メッセージを組み立て */
export function buildResumeMessage({ resumeToPhase, candidate }) {
  const name = candidate.display_name ? `${candidate.display_name}さん` : "お客様";
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || null;
  const stage = phaseToStage(resumeToPhase);

  const stageSummary = stage === 2
    ? `ステップ2「応募準備」${employer ? ` (${employer})` : ""} から再開します。`
    : stage === 3
      ? `ステップ3「面接準備」${employer ? ` (${employer})` : ""} から再開します。`
      : `前回の続きから再開します。`;

  // 各 phase への自然な再入メッセージ
  const phaseIntro = getPhaseReentryText(resumeToPhase, name, profile, employer);

  return {
    type: "text",
    text: `おかえりなさい${candidate.display_name ? `、${candidate.display_name}さん` : ""}。\n` +
      `${stageSummary}\n\n` +
      phaseIntro,
  };
}

function getPhaseReentryText(phase, name, profile, employer) {
  switch (phase) {
    case PHASES.APPLY_CONFIRM:
      return `${employer || "応募先"}への応募、進めましょうか？\n` +
        `「進める」とお送りください。`;
    case PHASES.APPLY_INFO_NAME:
      return "まず、お名前を教えてください。\n" +
        "漢字で、姓と名の間にスペースを入れてください。\n（例: 田中 ミサキ）";
    case PHASES.APPLY_INFO_KANA:
      return "ふりがなをひらがなで教えてください。\n（例: たなか みさき）";
    case PHASES.APPLY_INFO_BIRTH:
      return "生年月日を教えてください。\n（例: 1997-06-20）";
    case PHASES.APPLY_INFO_PHONE:
      return "携帯電話番号を教えてください。\n（例: 09012345678）\n※ 面接日程調整時のみの使用です";
    case PHASES.APPLY_INFO_WORKPLACE:
      return "現在の勤務先の正式名称を教えてください。\n（例: 横浜◯◯病院）";
    case PHASES.DOCUMENTS_PREP_LICENSE:
      return "看護師免許を取得された年月を教えてください。\n（例: 2020年3月）";
    case PHASES.DOCUMENTS_PREP_SCHOOL:
      return "出身の看護学校の正式名称を教えてください。";
    case PHASES.DOCUMENTS_PREP_HISTORY:
      return "これまでの勤務歴を年月と合わせて教えてください。";
    case PHASES.DOCUMENTS_PREP_CERTS:
      return "看護師免許以外の資格を教えてください。\nなければ「特になし」でOK。";
    case PHASES.DOCUMENTS_PREP_STRENGTHS:
      return "職務経歴書でアピールしたい強みを教えてください。\n思いつかなければ「任せる」でOK。";
    case PHASES.DOCUMENTS_GEN:
      return "AI書類作成を開始します。「書類作成して」とお送りください。";
    case PHASES.DOCUMENTS_REVIEW:
      return "書類3点をお送りしました。ご確認ください。\n" +
        "修正したい箇所があればお知らせください。\n" +
        "問題なければ「これで」とお送りください。";
    default:
      return "続きからどうぞ。";
  }
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
