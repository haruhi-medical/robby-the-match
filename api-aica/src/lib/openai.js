/**
 * OpenAI API クライアント（AI多層フォールバック対応）
 *
 * プライマリ: OpenAI GPT-4o-mini
 * セカンダリ: Anthropic Claude Haiku
 * ターシャリ: Google Gemini Flash
 * フォールバック: Cloudflare Workers AI (Llama 3)
 */

const OPENAI_URL = "https://api.openai.com/v1/chat/completions";
const ANTHROPIC_URL = "https://api.anthropic.com/v1/messages";
const GEMINI_URL =
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent";

/**
 * 統一インターフェース: システムプロンプト + 履歴 → テキスト応答
 * @param {object} params
 * @param {string} params.systemPrompt
 * @param {Array<{role:string, content:string}>} params.messages
 * @param {object} params.env - Worker env (API keys in secrets)
 * @param {number} [params.maxTokens=500]
 * @returns {Promise<{text:string, provider:string}>}
 */
export async function generateResponse(params) {
  const { systemPrompt, messages, env, maxTokens = 500 } = params;

  // 1. OpenAI GPT-4o-mini (プライマリ、タイムアウト 8秒)
  if (env.OPENAI_API_KEY) {
    try {
      const text = await callOpenAI({
        apiKey: env.OPENAI_API_KEY,
        systemPrompt,
        messages,
        maxTokens,
      });
      return { text, provider: "openai" };
    } catch (err) {
      console.warn("[openai] failed:", err.message);
    }
  }

  // 2. Anthropic Claude Haiku
  if (env.ANTHROPIC_API_KEY) {
    try {
      const text = await callAnthropic({
        apiKey: env.ANTHROPIC_API_KEY,
        systemPrompt,
        messages,
        maxTokens,
      });
      return { text, provider: "anthropic" };
    } catch (err) {
      console.warn("[anthropic] failed:", err.message);
    }
  }

  // 3. Gemini Flash
  if (env.GEMINI_API_KEY) {
    try {
      const text = await callGemini({
        apiKey: env.GEMINI_API_KEY,
        systemPrompt,
        messages,
        maxTokens,
      });
      return { text, provider: "gemini" };
    } catch (err) {
      console.warn("[gemini] failed:", err.message);
    }
  }

  // 4. Workers AI (最終フォールバック)
  if (env.AI) {
    try {
      const text = await callWorkersAI({
        ai: env.AI,
        systemPrompt,
        messages,
        maxTokens,
      });
      return { text, provider: "workers-ai" };
    } catch (err) {
      console.error("[workers-ai] failed:", err.message);
    }
  }

  throw new Error("All AI providers failed");
}

async function callOpenAI({ apiKey, systemPrompt, messages, maxTokens }) {
  const body = {
    model: "gpt-4o-mini",
    messages: [{ role: "system", content: systemPrompt }, ...messages],
    max_tokens: maxTokens,
    temperature: 0.7,
  };

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const res = await fetch(OPENAI_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`OpenAI ${res.status}: ${text}`);
    }
    const json = await res.json();
    return json.choices[0].message.content.trim();
  } finally {
    clearTimeout(timeout);
  }
}

async function callAnthropic({ apiKey, systemPrompt, messages, maxTokens }) {
  const body = {
    model: "claude-haiku-4-5-20251001",
    system: systemPrompt,
    messages: messages.map((m) => ({
      role: m.role === "assistant" ? "assistant" : "user",
      content: m.content,
    })),
    max_tokens: maxTokens,
  };

  const res = await fetch(ANTHROPIC_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Anthropic ${res.status}: ${text}`);
  }
  const json = await res.json();
  return json.content[0].text.trim();
}

async function callGemini({ apiKey, systemPrompt, messages, maxTokens }) {
  const parts = messages.map((m) => ({
    role: m.role === "assistant" ? "model" : "user",
    parts: [{ text: m.content }],
  }));

  const body = {
    systemInstruction: { parts: [{ text: systemPrompt }] },
    contents: parts,
    generationConfig: { maxOutputTokens: maxTokens, temperature: 0.7 },
  };

  const res = await fetch(`${GEMINI_URL}?key=${apiKey}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Gemini ${res.status}: ${text}`);
  }
  const json = await res.json();
  return json.candidates[0].content.parts[0].text.trim();
}

async function callWorkersAI({ ai, systemPrompt, messages, maxTokens }) {
  const result = await ai.run("@cf/meta/llama-3-8b-instruct", {
    messages: [{ role: "system", content: systemPrompt }, ...messages],
    max_tokens: maxTokens,
  });
  return (result.response || "").trim();
}

/**
 * 軸判定（JSON Mode）
 */
export async function classifyAxis({ userText, systemPrompt, env }) {
  if (!env.OPENAI_API_KEY) {
    // OpenAI無しの場合はヒューリスティック分類にフォールバック
    return heuristicClassify(userText);
  }

  try {
    const res = await fetch(OPENAI_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: "gpt-4o-mini",
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userText },
        ],
        response_format: { type: "json_object" },
        max_tokens: 100,
        temperature: 0.2,
      }),
    });
    const json = await res.json();
    return JSON.parse(json.choices[0].message.content);
  } catch (err) {
    console.warn("[axis classify] failed:", err.message);
    return heuristicClassify(userText);
  }
}

function heuristicClassify(text) {
  const t = text.toLowerCase();
  if (/死にたい|自殺|消えたい|パワハラ|セクハラ|モラハラ|いじめ|DV|虐待/.test(text)) {
    return { axis: "emergency", confidence: 1.0, keywords: [] };
  }
  if (/師長|主任|同僚|先輩|後輩|医師|Dr|患者|陰口|無視|合わない|きつい人/.test(text)) {
    return { axis: "relationship", confidence: 0.7, keywords: [] };
  }
  if (/夜勤|残業|シフト|休み|有給|勤務時間|時間外/.test(text)) {
    return { axis: "time", confidence: 0.7, keywords: [] };
  }
  if (/給料|給与|手当|賞与|ボーナス|年収|時給/.test(text)) {
    return { axis: "salary", confidence: 0.7, keywords: [] };
  }
  if (/やりがい|つまらない|成長|スキル|認定|専門|キャリア/.test(text)) {
    return { axis: "career", confidence: 0.7, keywords: [] };
  }
  if (/子ども|子育て|夫|彼氏|結婚|妊娠|産休|育休|介護|親|家族/.test(text)) {
    return { axis: "family", confidence: 0.7, keywords: [] };
  }
  return { axis: "vague", confidence: 0.5, keywords: [] };
}
