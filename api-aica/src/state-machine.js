/**
 * ナースロビー AIキャリアアドバイザー ステートマシン v0.1
 *
 * MVP0範囲: new → turn1 → turn2 → turn3 → turn4 → summary → handoff_to_human
 * MVP1以降: summary 後に profile_q1-5 → matching → ... を追加
 *
 * 状態は D1 candidates.phase に永続化。
 */

export const PHASES = {
  // 心理ヒアリング
  NEW: "new",
  TURN1: "turn1",
  TURN2: "turn2",
  TURN3: "turn3",
  TURN4: "turn4",
  SUMMARY: "summary",

  // プロファイル補強（MVP1）
  PROFILE_EXP: "profile_exp",
  PROFILE_DEPT: "profile_dept",
  PROFILE_AREA: "profile_area",
  PROFILE_WORKSTYLE: "profile_workstyle",
  PROFILE_SALARY: "profile_salary",
  PROFILE_TIMING: "profile_timing",
  PROFILE_COMMUTE: "profile_commute",

  // マッチング以降（MVP1後半〜）
  MATCHING: "matching",
  JOB_QA: "job_qa",
  APPLY_CONFIRM: "apply_confirm",
  APPLY_INFO_NAME: "apply_info_name",
  APPLY_INFO_KANA: "apply_info_kana",
  APPLY_INFO_BIRTH: "apply_info_birth",
  APPLY_INFO_PHONE: "apply_info_phone",
  APPLY_INFO_WORKPLACE: "apply_info_workplace",
  DOCUMENTS_PREP_LICENSE: "documents_prep_license",
  DOCUMENTS_PREP_SCHOOL: "documents_prep_school",
  DOCUMENTS_PREP_HISTORY: "documents_prep_history",
  DOCUMENTS_PREP_CERTS: "documents_prep_certs",
  DOCUMENTS_PREP_STRENGTHS: "documents_prep_strengths",
  DOCUMENTS_GEN: "documents_gen",
  DOCUMENTS_REVIEW: "documents_review",
  APPROVED: "approved",

  // MVP2 以降
  APPLIED: "applied",
  INTERVIEW_SCHEDULING: "interview_scheduling",
  INTERVIEW_PREP: "interview_prep",
  INTERVIEW_DONE: "interview_done",
  RESULT_WAITING: "result_waiting",
  OFFER: "offer",
  NEGOTIATION: "negotiation",
  ACCEPTED: "accepted",
  RESIGNATION_PREP: "resignation_prep",
  RESIGNATION_IN_PROGRESS: "resignation_in_progress",
  RESIGNATION_DONE: "resignation_done",

  // MVP3 以降
  PRE_ONBOARD: "pre_onboard",
  ONBOARDED: "onboarded",
  FOLLOWUP_D1: "followup_d1",
  FOLLOWUP_D3: "followup_d3",
  FOLLOWUP_D7: "followup_d7",
  FOLLOWUP_D30: "followup_d30",
  FOLLOWUP_D90: "followup_d90",
  STABLE: "stable",

  // 特殊
  HANDOFF: "handoff_to_human",
  EMERGENCY: "emergency",
  PAUSED: "paused",
};

/** 心理ヒアリング中か（4ターン+NEW） */
export function isIntakePhase(phase) {
  return [PHASES.NEW, PHASES.TURN1, PHASES.TURN2, PHASES.TURN3, PHASES.TURN4].includes(phase);
}

/** プロファイル補強中か */
export function isProfilePhase(phase) {
  return [
    PHASES.PROFILE_EXP,
    PHASES.PROFILE_DEPT,
    PHASES.PROFILE_AREA,
    PHASES.PROFILE_WORKSTYLE,
    PHASES.PROFILE_SALARY,
    PHASES.PROFILE_TIMING,
    PHASES.PROFILE_COMMUTE,
  ].includes(phase);
}

/**
 * 正常系の遷移マップ
 * phase + user_message_received → next_phase
 */
export function nextPhase(currentPhase, userMessage) {
  switch (currentPhase) {
    case PHASES.NEW:
      // 友だち追加直後の welcome (自動) → ユーザー発言 → Turn 1 判定後に Turn 2 へ
      return PHASES.TURN2;
    case PHASES.TURN1:
      return PHASES.TURN2;
    case PHASES.TURN2:
      return PHASES.TURN3;
    case PHASES.TURN3:
      return PHASES.TURN4;
    case PHASES.TURN4:
      return PHASES.SUMMARY;
    case PHASES.SUMMARY:
      return PHASES.HANDOFF;
    case PHASES.HANDOFF:
      // 人間対応中は state固定、人間がコマンドで切り替える
      return PHASES.HANDOFF;
    default:
      return currentPhase;
  }
}

/**
 * Turn 1 のシステム発言（welcome直後の自動送信 or 友だち追加時）
 */
export function buildWelcomeMessage(displayName) {
  const name = displayName ? `${displayName}さん` : "こんばんは";
  return `こんばんは、${displayName ? displayName + "さん" : "初めまして"}。
ナースロビーAIキャリアアドバイザーです。

私はAIです。
24時間いつでも、誰にも知られずに
お仕事のお話を伺えます。

最大4つの質問で、あなたの「本当に必要な条件」を
整理した後、具体的な求人をご提案します。

今、お仕事で気になっていることを、
一言で言うとどのようなことですか？`;
}

/**
 * Phase から「現在が何ターン目か」を返す（1-4）
 * Turn カウント（turn_count）と phase の対応:
 *   - welcome送信後（NEW→TURN2待ち）: turn_count=0
 *   - ユーザーが Turn 1 回答 → AI応答 (Turn 2 質問): turn_count=1
 *   - ユーザーが Turn 2 回答 → AI応答 (Turn 3 質問): turn_count=2
 *   - ユーザーが Turn 3 回答 → AI応答 (Turn 4 質問): turn_count=3
 *   - ユーザーが Turn 4 回答 → AI応答 (要約): turn_count=4
 */
export function shouldCloseConversation(turnCount) {
  return turnCount >= 4;
}

/**
 * D1 candidates の読み書きヘルパ
 */
export async function getOrCreateCandidate(db, userId, displayName) {
  const now = Date.now();
  const existing = await db
    .prepare("SELECT * FROM candidates WHERE id = ?")
    .bind(userId)
    .first();

  if (existing) return existing;

  await db
    .prepare(
      `INSERT INTO candidates (id, display_name, phase, turn_count, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, ?)`
    )
    .bind(userId, displayName || null, PHASES.NEW, 0, now, now)
    .run();

  return {
    id: userId,
    display_name: displayName,
    phase: PHASES.NEW,
    turn_count: 0,
    axis: null,
    root_cause: null,
    profile_json: null,
    created_at: now,
    updated_at: now,
  };
}

export async function updateCandidate(db, userId, patch) {
  const fields = [];
  const values = [];
  for (const [k, v] of Object.entries(patch)) {
    fields.push(`${k} = ?`);
    values.push(v);
  }
  fields.push("updated_at = ?");
  values.push(Date.now());
  values.push(userId);

  await db
    .prepare(`UPDATE candidates SET ${fields.join(", ")} WHERE id = ?`)
    .bind(...values)
    .run();
}

export async function logMessage(db, candidateId, role, content, phase, turnIndex, provider) {
  await db
    .prepare(
      `INSERT INTO messages (candidate_id, role, content, phase, turn_index, provider, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(candidateId, role, content, phase, turnIndex, provider, Date.now())
    .run();
}

export async function getRecentMessages(db, candidateId, limit = 10) {
  const result = await db
    .prepare(
      `SELECT role, content FROM messages
       WHERE candidate_id = ?
       ORDER BY created_at DESC
       LIMIT ?`
    )
    .bind(candidateId, limit)
    .all();

  return (result.results || []).reverse();
}

export async function logHandoff(db, candidateId, reason, urgency, phase) {
  await db
    .prepare(
      `INSERT INTO handoffs (candidate_id, reason, urgency, phase, created_at)
       VALUES (?, ?, ?, ?, ?)`
    )
    .bind(candidateId, reason, urgency, phase, Date.now())
    .run();
}
