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
import { handleConditionTurn, buildConditionIntroMessage } from "./phases/condition.js";
import { runMatching } from "./phases/matching.js";
import { handleJobQaTurn } from "./phases/job-qa.js";
import { handleApplyConfirmTurn } from "./phases/apply.js";
import { handleApplyInfoTurn, isApplyInfoPhase } from "./phases/apply-info.js";
import { handleDocumentsPrepTurn, isDocumentsPrepPhase } from "./phases/documents-prep.js";
import { runDocumentGeneration } from "./phases/documents-gen.js";
import { handleDocumentsReviewTurn, regenerateDocument } from "./phases/documents-review.js";
import { handleInterviewPrepTurn, wantsInterviewPrep, enterInterviewPrep } from "./phases/interview-prep.js";
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
  ctx.waitUntil(processEvents(events, env, ctx));
  return new Response("OK", { status: 200 });
}

/**
 * イベントを非同期で処理
 */
async function processEvents(events, env, ctx) {
  for (const event of events) {
    try {
      await processEvent(event, env, ctx);
    } catch (err) {
      console.error("[process] event failed:", err.message, err.stack);
    }
  }
}

async function processEvent(event, env, ctx) {
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

  // Follow イベント（友だち追加 / ブロック解除）
  if (event.type === "follow") {
    const welcome = buildWelcomeMessage(displayName);
    await logMessage(db, userId, "assistant", welcome, PHASES.NEW, 0, "system");
    // 全フィールドをリセット（ブロック→解除で「最初からやり直し」を正しく機能させる）
    await updateCandidate(db, userId, {
      phase: PHASES.TURN1,
      turn_count: 0,
      axis: null,
      root_cause: null,
      profile_json: null,
      display_name: displayName || null,
    });

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

    // 面接対策への割り込みエントリ（JOB_QA/APPLY_CONFIRM/APPLIED/APPROVED 等から）
    if (
      wantsInterviewPrep(userText) &&
      candidate.phase !== PHASES.INTERVIEW_PREP &&
      !isIntakePhase(candidate.phase) &&
      candidate.phase !== PHASES.CONDITION_HEARING &&
      !isApplyInfoPhase(candidate.phase) &&
      !isDocumentsPrepPhase(candidate.phase)
    ) {
      const result = await enterInterviewPrep({ candidate, db });
      await logMessage(db, userId, "assistant", "[interview-prep-menu]", result.nextPhase, 0, "interview-prep-menu");
      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // 面接対策フェーズ: メニュー / 想定Q&A / 模擬面接 / 逆質問のコツ / 終了
    if (candidate.phase === PHASES.INTERVIEW_PREP) {
      const result = await handleInterviewPrepTurn({ candidate, userText, env, db });
      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[interview-prep ${result.nextPhase}]`,
        result.nextPhase,
        0,
        result.provider || "interview-prep-template"
      );
      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
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

      // Turn 4 クロージングの直後、条件ヒアリングフェーズに橋渡し
      const messagesToSend = [reply];
      if (nextPhase === PHASES.SUMMARY) {
        const introMsg = buildConditionIntroMessage(candidate);
        messagesToSend.push(introMsg);
        await updateCandidate(db, userId, { phase: PHASES.CONDITION_HEARING });
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

    // SUMMARY 状態で何か発言された場合 → 条件ヒアリングへの橋渡し
    if (candidate.phase === PHASES.SUMMARY) {
      const introMsg = buildConditionIntroMessage(candidate);
      await updateCandidate(db, userId, { phase: PHASES.CONDITION_HEARING });
      await logMessage(db, userId, "assistant", introMsg.text, PHASES.CONDITION_HEARING, 0, "condition-intro");
      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, [introMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, [introMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // 条件ヒアリング（AI対話）フェーズ
    if (candidate.phase === PHASES.CONDITION_HEARING) {
      const { reply, isComplete, provider } = await handleConditionTurn({
        candidate,
        userText,
        env,
        db,
      });

      await logMessage(db, userId, "assistant", reply, isComplete ? PHASES.MATCHING : PHASES.CONDITION_HEARING, 0, provider);

      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, reply, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, reply, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }

      // カルテ完成 → MATCHING 実行（Push で求人カルーセル）
      if (isComplete) {
        const latestCandidate = await env.AICA_DB
          .prepare("SELECT * FROM candidates WHERE id = ?")
          .bind(userId)
          .first();
        if (latestCandidate) {
          await runMatching({ candidate: latestCandidate, env, db });
        }
      }
      return;
    }

    // MATCHING / JOB_QA 状態: 意図分類 → 応募/再マッチング/詳細/Q&A
    if (candidate.phase === PHASES.MATCHING || candidate.phase === PHASES.JOB_QA) {
      const result = await handleJobQaTurn({ candidate, userText, env, db });

      if (result.rerunMatching) {
        await runMatching({ candidate, env, db });
        return;
      }

      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[job-qa ${result.nextPhase}]`,
        result.nextPhase,
        0,
        result.provider || "job-qa-template"
      );

      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // APPLY_CONFIRM 状態: 応募意思の最終確認
    if (candidate.phase === PHASES.APPLY_CONFIRM) {
      const result = await handleApplyConfirmTurn({ candidate, userText, db });

      if (result.rerunMatching) {
        await runMatching({ candidate, env, db });
        return;
      }

      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[apply-confirm ${result.nextPhase}]`,
        result.nextPhase,
        0,
        "apply-confirm"
      );

      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // APPLY_INFO_* 状態: 個人情報5問の収集
    if (isApplyInfoPhase(candidate.phase)) {
      const result = await handleApplyInfoTurn({ candidate, userText, db });

      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[apply-info ${result.nextPhase}]`,
        result.nextPhase,
        0,
        "apply-info-template"
      );

      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // DOCUMENTS_PREP_* 状態: 書類作成ヒアリング5問
    if (isDocumentsPrepPhase(candidate.phase)) {
      const result = await handleDocumentsPrepTurn({ candidate, userText, db });

      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[documents-prep ${result.nextPhase}]`,
        result.nextPhase,
        0,
        "documents-prep-template"
      );

      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }

      // 最終ステップ完了 → DOCUMENTS_GEN に遷移済み → 非同期で書類生成トリガー
      if (result.nextPhase === PHASES.DOCUMENTS_GEN && ctx?.waitUntil) {
        ctx.waitUntil(runDocumentGeneration({ candidateId: userId, env, db }));
      }
      return;
    }

    // DOCUMENTS_GEN 状態: 生成中（ユーザー発言は待機応答）
    if (candidate.phase === PHASES.DOCUMENTS_GEN) {
      const msg = {
        type: "text",
        text:
          "書類を作成中です。\n" +
          "30秒〜1分ほどお待ちください。\n" +
          "完成次第、3書類（履歴書/職務経歴書/志望動機書）を\n" +
          "順にお送りします。",
      };
      await logMessage(db, userId, "assistant", msg.text, PHASES.DOCUMENTS_GEN, 0, "doc-gen-waiting");
      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // DOCUMENTS_REVIEW 状態: 書類修正Q&A
    if (candidate.phase === PHASES.DOCUMENTS_REVIEW) {
      const result = await handleDocumentsReviewTurn({ candidate, userText, env, db });

      // 修正要望 → 「修正中…」即返信 + 非同期で再生成
      if (result.runRegen) {
        const waitMsg = {
          type: "text",
          text:
            `承知しました。「${result.runRegen.target === "motivation" ? "志望動機書" : result.runRegen.target === "career" ? "職務経歴書" : "履歴書"}」を修正します。\n` +
            `30秒ほどお待ちください…`,
        };
        await logMessage(
          db,
          userId,
          "assistant",
          waitMsg.text,
          PHASES.DOCUMENTS_REVIEW,
          0,
          "doc-review-regen-wait"
        );
        if (env.LINE_CHANNEL_ACCESS_TOKEN) {
          try {
            await replyMessage(event.replyToken, [waitMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
          } catch (err) {
            console.warn("[line] reply failed, fallback to push:", err.message);
            await pushMessage(userId, [waitMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
          }
        }
        if (ctx?.waitUntil) {
          ctx.waitUntil(
            regenerateDocument({
              candidateId: userId,
              target: result.runRegen.target,
              instruction: result.runRegen.instruction,
              env,
              db,
            })
          );
        }
        return;
      }

      // 承認 or 不明
      await logMessage(
        db,
        userId,
        "assistant",
        result.messages?.[0]?.text || `[doc-review ${result.nextPhase}]`,
        result.nextPhase,
        0,
        "doc-review-template"
      );

      if (env.LINE_CHANNEL_ACCESS_TOKEN && result.messages) {
        try {
          await replyMessage(event.replyToken, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          console.warn("[line] reply failed, fallback to push:", err.message);
          await pushMessage(userId, result.messages, env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // APPROVED 以降 は暫定で Slack転送
    await forwardToSlack(candidate, userText, env);
  }
}

async function forwardToSlack(candidate, userText, env) {
  // Phase 1 以降で実装。MVP0は console.log のみ
  console.log("[handoff-forward]", candidate.id, candidate.phase, userText);
}
