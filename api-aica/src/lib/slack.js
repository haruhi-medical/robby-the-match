/**
 * Slack Bot 通知クライアント
 * ハンドオフ・緊急・契約通知用
 */

const SLACK_POST_URL = "https://slack.com/api/chat.postMessage";

/**
 * Slackにメッセージ送信
 * @param {object} params
 * @param {string} params.text
 * @param {string} params.channel
 * @param {string} params.botToken
 * @param {Array} [params.blocks]
 */
export async function postToSlack({ text, channel, botToken, blocks }) {
  const body = { channel, text };
  if (blocks) body.blocks = blocks;

  const res = await fetch(SLACK_POST_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      Authorization: `Bearer ${botToken}`,
    },
    body: JSON.stringify(body),
  });

  const json = await res.json();
  if (!json.ok) {
    console.error("Slack post failed:", json.error);
    throw new Error(`Slack post failed: ${json.error}`);
  }
  return json;
}

/**
 * ハンドオフ通知（標準）
 */
export async function notifyHandoff({ candidateId, displayName, reason, phase, summary, env }) {
  const text = `🟡 AICA ハンドオフ発生\n\n` +
    `候補者: ${displayName || candidateId}\n` +
    `理由: ${reason}\n` +
    `フェーズ: ${phase}\n` +
    `直前のやりとり要約:\n${summary}`;
  return postToSlack({
    text,
    channel: env.SLACK_CHANNEL_AICA,
    botToken: env.SLACK_BOT_TOKEN,
  });
}

/**
 * 緊急通知（即時対応が必要）
 */
export async function notifyEmergency({ candidateId, displayName, keywords, lastMessage, env }) {
  const text = `🔴 【緊急】AICA 緊急キーワード検出\n\n` +
    `候補者: ${displayName || candidateId}\n` +
    `検出キーワード: ${keywords.join(", ")}\n` +
    `直前のメッセージ:\n${lastMessage}\n\n` +
    `※10分以内に対応してください`;
  return postToSlack({
    text,
    channel: env.SLACK_CHANNEL_URGENT || env.SLACK_CHANNEL_AICA,
    botToken: env.SLACK_BOT_TOKEN,
  });
}
