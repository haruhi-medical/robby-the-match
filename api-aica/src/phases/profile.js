/**
 * フェーズ6: プロファイル補強（5-7問、1問ずつ）
 * 設計書: docs/aica-conversation-flow.md §フェーズ6
 *
 * 4ターン心理ヒアリング完了後、求人マッチングに必要な属性を
 * 1問ずつ Quick Reply で確認する。ハンドオフしない。
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildQuickReplyMessage } from "../lib/line.js";

/**
 * プロファイル補強 各質問の定義
 * phase: 次の回答を待つ状態
 * buildMessage: LINE に送るメッセージオブジェクト
 * parse: ユーザー回答を profile_json キーに変換
 */
const PROFILE_QUESTIONS = {
  [PHASES.SUMMARY]: {
    // SUMMARY後の最初の質問: 経験年数
    nextPhase: PHASES.PROFILE_EXP,
    buildMessage: () =>
      buildQuickReplyMessage(
        "まず、看護師としての経験は何年目ですか？",
        [
          { label: "1-2年目", text: "1-2年目" },
          { label: "3-5年目", text: "3-5年目" },
          { label: "6-10年目", text: "6-10年目" },
          { label: "11年以上", text: "11年以上" },
        ]
      ),
  },
  [PHASES.PROFILE_EXP]: {
    saveKey: "experience_years",
    nextPhase: PHASES.PROFILE_DEPT,
    buildMessage: () =>
      buildQuickReplyMessage(
        "ありがとうございます。\nこれまで主に経験された診療科を教えてください。\n複数あれば、1つずつでも、まとめてでも構いません。",
        [
          { label: "内科系", text: "内科系" },
          { label: "外科系", text: "外科系" },
          { label: "救急・ICU", text: "救急・ICU" },
          { label: "小児・NICU", text: "小児・NICU" },
          { label: "産科・婦人科", text: "産科・婦人科" },
          { label: "精神科", text: "精神科" },
          { label: "回復期・慢性期", text: "回復期・慢性期" },
          { label: "訪問看護", text: "訪問看護" },
          { label: "介護施設", text: "介護施設" },
          { label: "クリニック・外来", text: "クリニック・外来" },
          { label: "その他", text: "その他" },
        ]
      ),
  },
  [PHASES.PROFILE_DEPT]: {
    saveKey: "departments",
    nextPhase: PHASES.PROFILE_AREA,
    buildMessage: () =>
      buildQuickReplyMessage(
        "勤務を希望される地域はどちらですか？",
        [
          { label: "横浜・川崎", text: "横浜・川崎" },
          { label: "湘南・鎌倉", text: "湘南・鎌倉" },
          { label: "相模原・県央", text: "相模原・県央" },
          { label: "横須賀・三浦", text: "横須賀・三浦" },
          { label: "小田原・県西", text: "小田原・県西" },
          { label: "どこでもOK", text: "どこでもOK" },
          { label: "神奈川県外も", text: "神奈川県外も" },
        ]
      ),
  },
  [PHASES.PROFILE_AREA]: {
    saveKey: "area",
    nextPhase: PHASES.PROFILE_WORKSTYLE,
    buildMessage: (candidate) => {
      // Turn 4 の理想像に応じて少し質問を変える（可能なら）
      const hint = candidate.axis === "time"
        ? "お話を伺うと「夜勤を減らしたい」とのことでしたね。\n具体的には、以下のどれに近いですか？"
        : "希望の働き方を教えてください。";
      return buildQuickReplyMessage(hint, [
        { label: "日勤のみ", text: "日勤のみ" },
        { label: "夜勤月2-3回", text: "夜勤月2-3回なら可" },
        { label: "夜勤ありOK", text: "夜勤ありOK" },
        { label: "パート・非常勤", text: "パート・非常勤" },
        { label: "夜勤専従", text: "夜勤専従" },
      ]);
    },
  },
  [PHASES.PROFILE_WORKSTYLE]: {
    saveKey: "workstyle",
    nextPhase: PHASES.PROFILE_SALARY,
    buildMessage: () =>
      buildQuickReplyMessage(
        "希望される年収水準はありますか？\n現職維持か、条件優先か、ざっくりで大丈夫です。",
        [
          { label: "350-400万円", text: "350-400万円" },
          { label: "400-450万円", text: "400-450万円" },
          { label: "450-500万円", text: "450-500万円" },
          { label: "500万円以上", text: "500万円以上" },
          { label: "条件優先", text: "年収より条件優先" },
          { label: "現職と同水準", text: "現職と同水準を維持" },
        ]
      ),
  },
  [PHASES.PROFILE_SALARY]: {
    saveKey: "salary_hope",
    nextPhase: PHASES.PROFILE_TIMING,
    buildMessage: () =>
      buildQuickReplyMessage(
        "入職の希望時期はおおよそ決まっていますか？",
        [
          { label: "1ヶ月以内", text: "できるだけ早く" },
          { label: "2-3ヶ月先", text: "2-3ヶ月先" },
          { label: "半年以内", text: "半年以内" },
          { label: "情報収集段階", text: "半年以上先・情報収集段階" },
        ]
      ),
  },
  [PHASES.PROFILE_TIMING]: {
    saveKey: "timing",
    nextPhase: PHASES.PROFILE_COMMUTE,
    buildMessage: () =>
      buildQuickReplyMessage(
        "最後に、通勤時間はどれくらいまで許容できますか？",
        [
          { label: "30分以内", text: "30分以内" },
          { label: "45分以内", text: "45分以内" },
          { label: "1時間以内", text: "1時間以内" },
          { label: "こだわらない", text: "こだわらない" },
        ]
      ),
  },
  [PHASES.PROFILE_COMMUTE]: {
    saveKey: "commute_max",
    nextPhase: PHASES.MATCHING,
    buildMessage: (candidate) => ({
      type: "text",
      text:
        `ありがとうございます。\n` +
        `${candidate.display_name || "お客様"}さんの条件に合う求人を、\n` +
        `神奈川県内からお探しします。\n\n` +
        `少しだけお時間をください…`,
    }),
  },
};

/**
 * プロファイル補強の次の質問を返す
 * @param {object} candidate
 * @returns {object|null} LINEメッセージオブジェクト、または null（MATCHING へ）
 */
export function buildNextProfileMessage(candidate) {
  const question = PROFILE_QUESTIONS[candidate.phase];
  if (!question) return null;
  return typeof question.buildMessage === "function"
    ? question.buildMessage(candidate)
    : question.buildMessage;
}

/**
 * プロファイル質問の回答を保存して次の phase に遷移
 */
export async function handleProfileAnswer({ candidate, userText, db }) {
  const currentQuestion = PROFILE_QUESTIONS[candidate.phase];
  if (!currentQuestion || !currentQuestion.saveKey) {
    return { nextPhase: candidate.phase, nextMessage: null };
  }

  // profile_json 更新
  let profile = {};
  try {
    profile = candidate.profile_json ? JSON.parse(candidate.profile_json) : {};
  } catch {
    profile = {};
  }

  if (currentQuestion.saveKey === "departments") {
    profile.departments = profile.departments || [];
    profile.departments.push(userText);
  } else {
    profile[currentQuestion.saveKey] = userText;
  }

  const nextPhase = currentQuestion.nextPhase;

  // 次の質問メッセージを取得
  // ただし candidate.phase を nextPhase に進めた後の質問を使う
  const nextCandidate = { ...candidate, phase: nextPhase, profile_json: JSON.stringify(profile) };
  const nextMessage = buildNextProfileMessage(nextCandidate);

  // DB 更新
  await updateCandidate(db, candidate.id, {
    phase: nextPhase,
    profile_json: JSON.stringify(profile),
  });

  return { nextPhase, nextMessage, profile };
}
