/**
 * 導入ヒアリング 4ターンフェーズ
 * 設計書: docs/new-ai-career-advisor-spec.md §4, §6-1
 */

import {
  INTAKE_SYSTEM_PROMPT,
  AXIS_CLASSIFIER_PROMPT,
  SUMMARY_PROMPT,
  EMERGENCY_KEYWORDS,
  EMERGENCY_RESPONSE,
} from "../prompts.js";
import { generateResponse, classifyAxis } from "../lib/openai.js";
import {
  PHASES,
  nextPhase,
  shouldCloseConversation,
  updateCandidate,
  getRecentMessages,
  logMessage,
  logHandoff,
} from "../state-machine.js";
import { notifyEmergency, notifyHandoff } from "../lib/slack.js";

/**
 * 緊急キーワード検出
 */
export function detectEmergency(text) {
  const found = EMERGENCY_KEYWORDS.filter((kw) => text.includes(kw));
  return found.length > 0 ? found : null;
}

/**
 * 導入フェーズ内で1ターン進める
 * @returns {Promise<{reply:string, nextPhase:string, provider:string}>}
 */
export async function handleIntakeTurn({ candidate, userText, env, db }) {
  // 緊急キーワード検出（最優先）
  const emergency = detectEmergency(userText);
  if (emergency) {
    await logHandoff(db, candidate.id, `緊急キーワード検出: ${emergency.join(",")}`, "emergency", candidate.phase);
    await notifyEmergency({
      candidateId: candidate.id,
      displayName: candidate.display_name,
      keywords: emergency,
      lastMessage: userText,
      env,
    });
    await updateCandidate(db, candidate.id, { phase: PHASES.EMERGENCY });
    return {
      reply: EMERGENCY_RESPONSE,
      nextPhase: PHASES.EMERGENCY,
      provider: "emergency-static",
    };
  }

  // Turn 1 の場合、軸判定を実行
  let axis = candidate.axis;
  if (!axis && candidate.turn_count === 0) {
    const classified = await classifyAxis({
      userText,
      systemPrompt: AXIS_CLASSIFIER_PROMPT,
      env,
    });
    axis = classified.axis;
    if (axis === "emergency") {
      // 軸分類で緊急判定された場合も緊急扱い
      await logHandoff(db, candidate.id, "軸判定で緊急と分類", "emergency", candidate.phase);
      await notifyEmergency({
        candidateId: candidate.id,
        displayName: candidate.display_name,
        keywords: classified.keywords || [],
        lastMessage: userText,
        env,
      });
      await updateCandidate(db, candidate.id, { phase: PHASES.EMERGENCY, axis });
      return {
        reply: EMERGENCY_RESPONSE,
        nextPhase: PHASES.EMERGENCY,
        provider: "emergency-ai",
      };
    }
    await updateCandidate(db, candidate.id, { axis });
  }

  // 履歴取得
  const history = await getRecentMessages(db, candidate.id, 10);
  const messages = [...history, { role: "user", content: userText }];

  // 次ターンカウント
  const newTurnCount = candidate.turn_count + 1;
  const isClosing = shouldCloseConversation(newTurnCount);

  // プロンプト合成（Turn Context 注入）
  const contextInfo = buildTurnContext({
    displayName: candidate.display_name,
    axis,
    turnCount: newTurnCount,
    isClosing,
  });

  const systemPrompt = isClosing
    ? `${INTAKE_SYSTEM_PROMPT}\n\n---\n\n【重要: 今回はクロージングです】\n\n${SUMMARY_PROMPT}\n\n${contextInfo}`
    : `${INTAKE_SYSTEM_PROMPT}\n\n---\n\n${contextInfo}`;

  // AI 応答生成
  const { text: reply, provider } = await generateResponse({
    systemPrompt,
    messages,
    env,
    maxTokens: isClosing ? 400 : 250,
  });

  // 状態更新
  const nextPh = isClosing ? PHASES.SUMMARY : nextPhase(candidate.phase, userText);
  await updateCandidate(db, candidate.id, {
    phase: nextPh,
    turn_count: newTurnCount,
    root_cause: isClosing ? extractRootCause(reply) : candidate.root_cause,
  });

  // クロージング時: Slack には「進捗記録」として通知（BOT沈黙ではない）
  if (isClosing) {
    const summary = `軸: ${axis || "不明"}\n` +
      `ターン数: ${newTurnCount}\n` +
      `AI要約:\n${reply}\n\n` +
      `→ そのままAIがプロファイル補強に進みます（ハンドオフではありません）`;
    await logHandoff(db, candidate.id, "4ターン完了・進捗記録", "info", PHASES.SUMMARY);
    await notifyHandoff({
      candidateId: candidate.id,
      displayName: candidate.display_name,
      reason: "4ターン完了（進捗記録）",
      phase: PHASES.SUMMARY,
      summary,
      env,
    });
  }

  return { reply, nextPhase: nextPh, provider };
}

function buildTurnContext({ displayName, axis, turnCount, isClosing }) {
  const name = displayName ? `${displayName}さん` : "（名前未取得）";
  const axisLabel = {
    relationship: "人間関係",
    time: "労働時間",
    salary: "給与・待遇",
    career: "キャリア・やりがい",
    family: "家庭・子育て・介護",
    vague: "漠然（まだ絞れていない）",
  }[axis] || "不明";

  if (isClosing) {
    return `【コンテキスト】
呼称: ${name}
特定された悩みの軸: ${axisLabel}
現在のターン: ${turnCount}（クロージング）

これまでの会話から「${name}の本当に必要な条件」を
1文で具体的にまとめ、求人提案の予告で締めてください。`;
  }

  return `【コンテキスト】
呼称: ${name}
特定された悩みの軸: ${axisLabel}
現在のターン: ${turnCount} / 4

この段階では 1つだけ質問を投げかけてください。
共感表現は ${turnCount === 1 ? "1文だけOK" : "禁止（短い相槌のみ）"}。`;
}

/**
 * クロージング応答から「根本原因」を抽出する簡易ヒューリスティック
 * 本格的にはAI再呼び出しで構造化するが、MVP0では文字列から「一番必要なのは『...』」を正規表現抽出
 */
function extractRootCause(closingText) {
  const match = closingText.match(/一番必要なのは[、\s]*[『「]([^』」]+)[』」]/);
  if (match) return match[1];
  // フォールバック: 最初の80字
  return closingText.slice(0, 80);
}
