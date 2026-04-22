/**
 * LINE Messaging API クライアント
 * ナースロビー AIキャリアアドバイザー専用
 */

const LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply";
const LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push";
const LINE_PROFILE_URL = "https://api.line.me/v2/bot/profile/";

/**
 * X-Line-Signature 検証
 */
export async function verifyLineSignature(body, signature, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const mac = await crypto.subtle.sign("HMAC", key, encoder.encode(body));
  const expected = btoa(String.fromCharCode(...new Uint8Array(mac)));
  return expected === signature;
}

/**
 * Reply Message を送信（reply_tokenは10分以内・1回限り）
 */
export async function replyMessage(replyToken, messages, accessToken) {
  if (!replyToken) {
    // 音声ackで既に消費済み等。呼び出し側の try/catch で push にフォールバックさせる
    throw new Error("replyToken missing or already consumed");
  }
  const body = {
    replyToken,
    messages: normalizeMessages(messages),
  };

  const res = await fetch(LINE_REPLY_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error("LINE reply failed:", res.status, text);
    throw new Error(`LINE reply failed: ${res.status}`);
  }
  return await res.json();
}

/**
 * Push Message を送信（AI応答の非同期返信用）
 */
export async function pushMessage(userId, messages, accessToken) {
  const body = {
    to: userId,
    messages: normalizeMessages(messages),
  };

  const res = await fetch(LINE_PUSH_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    console.error("LINE push failed:", res.status, text);
    throw new Error(`LINE push failed: ${res.status}`);
  }
  return await res.json();
}

/**
 * ユーザープロフィール取得（displayName取得）
 */
export async function getUserProfile(userId, accessToken) {
  const res = await fetch(`${LINE_PROFILE_URL}${userId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!res.ok) {
    console.error("LINE profile fetch failed:", res.status);
    return null;
  }
  return await res.json();
}

/**
 * メッセージを LINE 仕様に正規化
 * string → {type:"text", text}, array → そのまま
 */
function normalizeMessages(messages) {
  if (typeof messages === "string") {
    return [{ type: "text", text: messages }];
  }
  if (Array.isArray(messages)) {
    return messages.map((m) => (typeof m === "string" ? { type: "text", text: m } : m));
  }
  return [messages];
}

/**
 * Quick Reply 付きテキストメッセージを構築
 * @param {string} text 本文
 * @param {Array<{label:string, data?:string, text?:string}>} items 最大13個
 */
export function buildQuickReplyMessage(text, items) {
  const quickReplyItems = items.slice(0, 13).map((item) => ({
    type: "action",
    action: item.data
      ? { type: "postback", label: item.label, data: item.data, displayText: item.label }
      : { type: "message", label: item.label, text: item.text || item.label },
  }));
  return {
    type: "text",
    text,
    quickReply: { items: quickReplyItems },
  };
}
