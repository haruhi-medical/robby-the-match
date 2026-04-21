/**
 * ナースロビー AIキャリアアドバイザー Worker エントリポイント
 *
 * @version 0.1.0 (MVP0 - 4ターン対話 + 人間引き継ぎ)
 *
 * Routes:
 *   POST /webhook/line - LINE Messaging API webhook
 *   GET  /health        - ヘルスチェック
 *   GET  /version       - バージョン情報
 */

import { verifyLineSignature, replyMessage, pushMessage, getUserProfile } from "./lib/line.js";
import {
  PHASES,
  getOrCreateCandidate,
  updateCandidate,
  logMessage,
  buildWelcomeMessage,
  isIntakePhase,
  isProfilePhase,
} from "./state-machine.js";
import { handleIntakeTurn } from "./phases/intake.js";
import { buildNextProfileMessage, handleProfileAnswer } from "./phases/profile.js";
import { runMatching } from "./phases/matching.js";
import { getJobByKjno, formatJobDetail } from "./lib/jobs.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          version: env.AICA_VERSION || "0.1.0",
          timestamp: new Date().toISOString(),
        }),
        { headers: { "Content-Type": "application/json" } }
      );
    }

    if (url.pathname === "/version") {
      return new Response(JSON.stringify({ version: env.AICA_VERSION || "0.1.0" }), {
        headers: { "Content-Type": "application/json" },
      });
    }

    // LINE webhook
    if (url.pathname === "/webhook/line" && request.method === "POST") {
      return handleLineWebhook(request, env, ctx);
    }

    return new Response("Not Found", { status: 404 });
  },

  /**
   * Cron Trigger (入職後フォロー Push等)
   * スケジュール: "0 0 * * *" (JST 09:00) / "0 * * * *" (毎時)
   */
  async scheduled(event, env, ctx) {
    // MVP0 ではまだ cron トリガーで何もしない
    // MVP3 で follow_ups テーブルから trigger_at <= now を拾って Push
    console.log("[cron] triggered", event.cron, new Date().toISOString());
  },
};

/**
 * LINE webhook 本体
 */
async function handleLineWebhook(request, env, ctx) {
  const rawBody = await request.text();
  const signature = request.headers.get("x-line-signature");

  // 署名検証
  if (env.LINE_CHANNEL_SECRET) {
    const valid = await verifyLineSignature(rawBody, signature, env.LINE_CHANNEL_SECRET);
    if (!valid) {
      console.warn("[line] invalid signature");
      return new Response("Invalid signature", { status: 401 });
    }
  } else {
    console.warn("[line] LINE_CHANNEL_SECRET not set, skipping signature verification (DEV ONLY)");
  }

  const payload = JSON.parse(rawBody);
  const events = payload.events || [];

  // 3秒以内に 200 を返す（LINE要件）
  ctx.waitUntil(processEvents(events, env));
  return new Response("OK", { status: 200 });
}

/**
 * イベントを非同期で処理
 */
async function processEvents(events, env) {
  for (const event of events) {
    try {
      await processEvent(event, env);
    } catch (err) {
      console.error("[process] event failed:", err.message, err.stack);
    }
  }
}

async function processEvent(event, env) {
  const userId = event.source?.userId;
  if (!userId) return;

  const db = env.AICA_DB;

  // プロフィール取得（displayName）
  let displayName = null;
  if (env.LINE_CHANNEL_ACCESS_TOKEN) {
    const profile = await getUserProfile(userId, env.LINE_CHANNEL_ACCESS_TOKEN);
    displayName = profile?.displayName || null;
  }

  const candidate = await getOrCreateCandidate(db, userId, displayName);

  // Follow イベント（友だち追加）
  if (event.type === "follow") {
    const welcome = buildWelcomeMessage(displayName);
    await logMessage(db, userId, "assistant", welcome, PHASES.NEW, 0, "system");
    // turn_count は welcome 送信後も 0 のまま（Turn 1 質問は送信済み、ユーザー回答待ち）
    await updateCandidate(db, userId, { phase: PHASES.TURN1 });

    if (env.LINE_CHANNEL_ACCESS_TOKEN) {
      await replyMessage(event.replyToken, welcome, env.LINE_CHANNEL_ACCESS_TOKEN);
    }
    return;
  }

  // Unfollow（ブロック）
  if (event.type === "unfollow") {
    await updateCandidate(db, userId, { phase: PHASES.PAUSED });
    return;
  }

  // Postback: ボタンタップ（求人詳細など）
  if (event.type === "postback" && event.postback?.data) {
    const data = event.postback.data;
    const [action, ...rest] = data.split(":");

    if (action === "job_detail") {
      const kjno = rest.join(":");
      const job = await getJobByKjno(env.NURSE_DB, kjno);
      const detailText = formatJobDetail(job);
      await logMessage(db, userId, "assistant", `[job_detail ${kjno}]`, candidate.phase, 0, "job-detail");

      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, detailText, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, detailText, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }
  }

  // テキストメッセージ
  if (event.type === "message" && event.message?.type === "text") {
    const userText = event.message.text;
    await logMessage(db, userId, "user", userText, candidate.phase, candidate.turn_count, null);

    // Handoff中（人間対応中）は BOT沈黙、Slack へのみ転送
    if (candidate.phase === PHASES.HANDOFF || candidate.phase === PHASES.EMERGENCY) {
      await forwardToSlack(candidate, userText, env);
      return;
    }

    // 心理ヒアリング 4ターン（NEW, TURN1-4）
    if (isIntakePhase(candidate.phase)) {
      const { reply, nextPhase, provider } = await handleIntakeTurn({
        candidate,
        userText,
        env,
        db,
      });

      await logMessage(db, userId, "assistant", reply, nextPhase, candidate.turn_count + 1, provider);

      // Turn 4 クロージングの直後、そのままプロファイル補強の1問目を追撃
      const messagesToSend = [reply];
      if (nextPhase === PHASES.SUMMARY) {
        const profileCandidate = { ...candidate, phase: PHASES.SUMMARY };
        const firstProfileMsg = buildNextProfileMessage(profileCandidate);
        if (firstProfileMsg) {
          messagesToSend.push(firstProfileMsg);
          await updateCandidate(db, userId, { phase: PHASES.PROFILE_EXP });
        }
      }

      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, messagesToSend, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, messagesToSend, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // SUMMARY 状態で何か発言された場合 → プロファイル補強の1問目を送って PROFILE_EXP へ
    // （前バージョンの会話継続・手動で「続き」と言った場合もここでリカバー）
    if (candidate.phase === PHASES.SUMMARY) {
      const firstProfileMsg = buildNextProfileMessage({ ...candidate, phase: PHASES.SUMMARY });
      if (firstProfileMsg && env.LINE_CHANNEL_ACCESS_TOKEN) {
        await updateCandidate(db, userId, { phase: PHASES.PROFILE_EXP });
        await logMessage(db, userId, "assistant", firstProfileMsg.text || "[profile q1]", PHASES.PROFILE_EXP, 0, "profile-template");
        try {
          await replyMessage(event.replyToken, [firstProfileMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, [firstProfileMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // プロファイル補強フェーズ
    if (isProfilePhase(candidate.phase)) {
      const { nextPhase, nextMessage } = await handleProfileAnswer({
        candidate,
        userText,
        db,
      });

      if (nextMessage && env.LINE_CHANNEL_ACCESS_TOKEN) {
        const logContent = nextMessage.text || "[profile question]";
        await logMessage(db, userId, "assistant", logContent, nextPhase, 0, "profile-template");
        try {
          await replyMessage(event.replyToken, [nextMessage], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, [nextMessage], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }

      // COMMUTE → MATCHING に到達したら、即求人検索を走らせて Push 送信
      if (nextPhase === PHASES.MATCHING) {
        // "少しお待ちください…" を reply で返した後、別途 Push で求人カルーセル送信
        // ctx.waitUntil の扱いは呼び出し元で処理。ここでは直接 await する（処理後に webhookが完了）
        const latestCandidate = { ...candidate, phase: PHASES.MATCHING };
        await runMatching({ candidate: latestCandidate, env, db });
      }
      return;
    }

    // MATCHING / JOB_QA 状態: 再マッチング要求 or 詳細Q&A
    // MVP1前半では、「見せて」「もう一度」「他も」等の曖昧発言は re-match
    if (candidate.phase === PHASES.MATCHING || candidate.phase === PHASES.JOB_QA) {
      await runMatching({ candidate, env, db });
      return;
    }

    // MVP1範囲外（MATCHING以降）は暫定で Slack転送
    await forwardToSlack(candidate, userText, env);
  }
}

async function forwardToSlack(candidate, userText, env) {
  // Phase 1 以降で実装。MVP0は console.log のみ
  console.log("[handoff-forward]", candidate.id, candidate.phase, userText);
}
