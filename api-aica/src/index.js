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
import { generateCareerSheet } from "./phases/career-sheet.js";
import { runMatching } from "./phases/matching.js";
import { handleJobQaTurn } from "./phases/job-qa.js";
import { handleApplyConfirmTurn } from "./phases/apply.js";
import { handleApplyInfoTurn, isApplyInfoPhase } from "./phases/apply-info.js";
import { handleDocumentsPrepTurn, isDocumentsPrepPhase } from "./phases/documents-prep.js";
import { runDocumentGeneration } from "./phases/documents-gen.js";
import { handleDocumentsReviewTurn, regenerateDocument } from "./phases/documents-review.js";
import { runHospitalSendPrep } from "./phases/hospital-send.js";
import { handleInterviewPrepTurn, wantsInterviewPrep, enterInterviewPrep } from "./phases/interview-prep.js";
import { getJobByKjno, formatJobDetail } from "./lib/jobs.js";
import { transcribeAudioFromLine } from "./lib/transcribe.js";
import {
  wantsResume,
  wantsContinueNow,
  wantsPauseUntilLater,
  resumeFrom,
  pauseAt,
  buildResumeMessage,
  buildStage2EndChoice,
} from "./lib/staging.js";
import { processPausedResumePush } from "./lib/cron-resume.js";

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Health check
    if (url.pathname === "/health") {
      const deep = url.searchParams.get("deep") === "1";
      const base = {
        status: "ok",
        version: env.AICA_VERSION || "0.1.0",
        timestamp: new Date().toISOString(),
      };
      if (!deep) {
        return new Response(JSON.stringify(base), {
          headers: { "Content-Type": "application/json" },
        });
      }
      const deps = await checkDependencies(env);
      const overall = Object.values(deps).every((d) => d.ok) ? "ok" : "degraded";
      return new Response(
        JSON.stringify({ ...base, status: overall, deps }),
        {
          status: overall === "ok" ? 200 : 503,
          headers: { "Content-Type": "application/json" },
        }
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

    // キャリアシート HTML 閲覧（社長・営業用。noindex）
    const csMatch = url.pathname.match(/^\/career-sheet\/([A-Za-z0-9_-]+)$/);
    if (csMatch && request.method === "GET") {
      return handleCareerSheetView(csMatch[1], env);
    }

    // 管理: キャリアシートを手動生成（既存候補者向けバックフィル）
    if (url.pathname === "/admin/career-sheet/generate" && request.method === "POST") {
      return handleAdminCareerSheetGenerate(request, env);
    }

    return new Response("Not Found", { status: 404 });
  },

  /**
   * Cron Trigger
   * スケジュール:
   *   "0 0 * * *" (JST 09:00) → PAUSED 復帰 Push (Day 3 / Day 7)
   *   "0 * * * *" (毎時)      → MVP3 の follow_ups 処理用（未実装）
   */
  async scheduled(event, env, ctx) {
    console.log("[cron] triggered", event.cron, new Date().toISOString());

    if (event.cron === "0 0 * * *") {
      // 毎朝09:00 JST: PAUSED ユーザーに復帰 Push
      ctx.waitUntil(
        processPausedResumePush(env).catch((err) => {
          console.error("[cron-resume] failed:", err.message, err.stack);
        })
      );
    }

    // "0 * * * *" は MVP3 の入職後フォロー Push 用に温存（現在 no-op）
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

  // 音声メッセージ → Whisper で文字起こし → テキスト扱い
  if (event.type === "message" && event.message?.type === "audio") {
    if (!env.OPENAI_API_KEY || !env.LINE_CHANNEL_ACCESS_TOKEN) {
      console.warn("[audio] OPENAI_API_KEY or LINE_CHANNEL_ACCESS_TOKEN missing, skipping transcription");
      return;
    }
    let transcript;
    try {
      transcript = await transcribeAudioFromLine({
        messageId: event.message.id,
        accessToken: env.LINE_CHANNEL_ACCESS_TOKEN,
        openaiKey: env.OPENAI_API_KEY,
      });
    } catch (err) {
      console.error("[audio] transcription failed:", err.message);
      try {
        await replyMessage(
          event.replyToken,
          [
            {
              type: "text",
              text:
                "申し訳ありません。\n" +
                "音声メッセージの文字起こしに失敗しました。\n" +
                "お手数ですが、もう一度お試しいただくか、\n" +
                "テキストで入力してください。",
            },
          ],
          env.LINE_CHANNEL_ACCESS_TOKEN
        );
      } catch {}
      await logMessage(db, userId, "user", "[audio:transcribe-failed]", candidate.phase, candidate.turn_count, null);
      return;
    }

    if (!transcript || transcript.length === 0) {
      try {
        await replyMessage(
          event.replyToken,
          [
            {
              type: "text",
              text:
                "音声は受け取りましたが、\n" +
                "お声が聞き取れませんでした。\n" +
                "もう一度、少しゆっくりお話しいただけますか？",
            },
          ],
          env.LINE_CHANNEL_ACCESS_TOKEN
        );
      } catch {}
      return;
    }

    // user発言として記録（voiceマーカー付き）
    await logMessage(db, userId, "user", `[voice] ${transcript}`, candidate.phase, candidate.turn_count, "whisper");

    // ack: 何を聞き取ったかを即返信（reply token 消費）
    try {
      const preview = transcript.length > 120 ? transcript.slice(0, 120) + "…" : transcript;
      await replyMessage(
        event.replyToken,
        [
          {
            type: "text",
            text: `🎤 音声を聞き取りました\n『${preview}』\n\n少しお待ちください…`,
          },
        ],
        env.LINE_CHANNEL_ACCESS_TOKEN
      );
    } catch (err) {
      console.warn("[audio] ack reply failed:", err.message);
    }

    // 以降の処理のために event.message を text 型に差し替え + reply token は消費済みに
    event.message = { type: "text", text: transcript, _fromVoice: true };
    event.replyToken = null; // 以降の replyMessage は必ず失敗 → push にフォールバック
  }

  // テキストメッセージ
  if (event.type === "message" && event.message?.type === "text") {
    const userText = event.message.text;
    const fromVoice = event.message._fromVoice === true;
    if (!fromVoice) {
      await logMessage(db, userId, "user", userText, candidate.phase, candidate.turn_count, null);
    }

    // Handoff中（人間対応中）は BOT沈黙、Slack へのみ転送
    if (candidate.phase === PHASES.HANDOFF || candidate.phase === PHASES.EMERGENCY) {
      await forwardToSlack(candidate, userText, env);
      return;
    }

    // PAUSED + 「続きから」系キーワード → 再開
    if (candidate.phase === PHASES.PAUSED && wantsResume(userText)) {
      const resumedPhase = await resumeFrom({ candidate, db });
      const refreshed = await env.AICA_DB
        .prepare("SELECT * FROM candidates WHERE id = ?")
        .bind(userId)
        .first();
      const welcomeBack = buildResumeMessage({ resumeToPhase: resumedPhase, candidate: refreshed || candidate });
      await logMessage(db, userId, "assistant", welcomeBack.text, resumedPhase, 0, "staging-resume");
      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, [welcomeBack], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          await pushMessage(userId, [welcomeBack], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // PAUSED + 「続きから」以外の発言 → 「続きから」を促す
    if (candidate.phase === PHASES.PAUSED) {
      const profile = safeParseJson(candidate.profile_json);
      const hasResumePoint = !!profile.resume_from;
      const msg = {
        type: "text",
        text: hasResumePoint
          ? "お帰りなさい。\n「続きから」とお送りいただければ、\n前回の続きから再開できます。"
          : "お時間のある時に、また気軽にお声がけください。",
      };
      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          await pushMessage(userId, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
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
        // キャリアシート自動生成（候補者には見えない / 社長営業用 Layer 1）
        if (ctx?.waitUntil) {
          ctx.waitUntil(
            generateCareerSheet({ candidateId: userId, env, db }).catch((err) => {
              console.error("[career-sheet] gen failed:", err.message, err.stack);
            })
          );
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

      // Stage 2→3 境界: stage2End=true なら選択肢提示のみ、生成はしない
      // stage2End でない場合は従来通り（経由がないパスだが念のため後方互換）
      if (result.stage2End) {
        // 書類生成はここでは起動しない。ユーザーの選択待ち
        return;
      }
      return;
    }

    // DOCUMENTS_GEN 状態: 書類生成の選択肢 or 生成進行中
    if (candidate.phase === PHASES.DOCUMENTS_GEN) {
      const profile = safeParseJson(candidate.profile_json);
      const awaitingChoice = profile.awaiting_gen_choice === true;

      // 選択肢待ち状態
      if (awaitingChoice) {
        if (wantsContinueNow(userText)) {
          // 今すぐ生成トリガー
          const newProfile = { ...profile };
          delete newProfile.awaiting_gen_choice;
          newProfile.gen_in_progress = true;
          await updateCandidate(db, userId, { profile_json: JSON.stringify(newProfile) });

          const msg = {
            type: "text",
            text:
              "承知しました。書類を作成します。\n" +
              "30秒〜1分ほどお待ちください。\n" +
              "完成次第、3書類（履歴書/職務経歴書/志望動機書）を\n" +
              "順にお送りします。",
          };
          await logMessage(db, userId, "assistant", msg.text, PHASES.DOCUMENTS_GEN, 0, "doc-gen-start");
          if (env.LINE_CHANNEL_ACCESS_TOKEN) {
            try {
              await replyMessage(event.replyToken, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
            } catch (err) {
              await pushMessage(userId, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
            }
          }
          if (ctx?.waitUntil) {
            ctx.waitUntil(runDocumentGeneration({ candidateId: userId, env, db }));
          }
          return;
        }

        if (wantsPauseUntilLater(userText)) {
          // 面接前まで保留 → PAUSED + resume_from=DOCUMENTS_GEN
          const newProfile = { ...profile };
          delete newProfile.awaiting_gen_choice;
          await updateCandidate(db, userId, { profile_json: JSON.stringify(newProfile) });
          await pauseAt({
            candidate: { ...candidate, profile_json: JSON.stringify(newProfile) },
            resumeFromPhase: PHASES.DOCUMENTS_GEN,
            db,
          });

          const msg = {
            type: "text",
            text:
              "承知しました。\n" +
              "書類作成は面接の前日までに済ませれば大丈夫です。\n\n" +
              "面接日が決まったら、または作成したくなったら、\n" +
              "「続きから」とメッセージを送ってください。\n" +
              "そこから書類作成を開始します。\n\n" +
              "お時間ありがとうございました。",
          };
          await logMessage(db, userId, "assistant", msg.text, PHASES.PAUSED, 0, "stage2-pause");
          if (env.LINE_CHANNEL_ACCESS_TOKEN) {
            try {
              await replyMessage(event.replyToken, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
            } catch (err) {
              await pushMessage(userId, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
            }
          }
          return;
        }

        // 不明 → 選択肢再表示
        const msg = buildStage2EndChoice();
        if (env.LINE_CHANNEL_ACCESS_TOKEN) {
          try {
            await replyMessage(event.replyToken, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
          } catch (err) {
            await pushMessage(userId, [msg], env.LINE_CHANNEL_ACCESS_TOKEN);
          }
        }
        return;
      }

      // 生成進行中 → 待機応答
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

      // 承認された → 非同期で病院送付準備（推薦文AI生成 + D1記録 + Slack通知）
      if (result.triggerHospitalSend && ctx?.waitUntil) {
        ctx.waitUntil(
          runHospitalSendPrep({ candidateId: userId, env, db, ctx }).catch((err) => {
            console.error("[hospital-send] prep failed:", err.message, err.stack);
          })
        );
      }
      return;
    }

    // APPROVED 状態: 社長の病院送付を待機中の待機応答
    if (candidate.phase === PHASES.APPROVED) {
      const waitMsg = {
        type: "text",
        text:
          "現在、弊社で書類の最終確認を行っています。\n" +
          "応募先への送付完了は翌営業日までにご連絡します。\n\n" +
          "この間も、面接対策など別のお手伝いができます。\n" +
          "「面接対策」とお送りいただければ、想定Q&Aや模擬面接が可能です。",
      };
      await logMessage(db, userId, "assistant", waitMsg.text, PHASES.APPROVED, 0, "approved-waiting");
      if (env.LINE_CHANNEL_ACCESS_TOKEN) {
        try {
          await replyMessage(event.replyToken, [waitMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        } catch (err) {
          await pushMessage(userId, [waitMsg], env.LINE_CHANNEL_ACCESS_TOKEN);
        }
      }
      return;
    }

    // APPLIED 以降は暫定で Slack転送
    await forwardToSlack(candidate, userText, env);
  }
}

async function forwardToSlack(candidate, userText, env) {
  // Phase 1 以降で実装。MVP0は console.log のみ
  console.log("[handoff-forward]", candidate.id, candidate.phase, userText);
}

/**
 * 管理エンドポイント: キャリアシートを1名または複数名分を即時生成
 * Body: { candidateId: "Uxxx" }  or  { mode: "backfill_all" }
 * Auth: Authorization: Bearer <AICA_ADMIN_KEY>
 */
async function handleAdminCareerSheetGenerate(request, env) {
  const authHeader = request.headers.get("Authorization") || "";
  const expected = env.AICA_ADMIN_KEY || "";
  if (!expected) {
    return new Response(JSON.stringify({ error: "AICA_ADMIN_KEY not configured" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
  if (authHeader !== `Bearer ${expected}`) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const results = [];

  if (body.candidateId) {
    try {
      const r = await generateCareerSheet({ candidateId: body.candidateId, env, db: env.AICA_DB });
      results.push({ candidateId: body.candidateId, ok: true, serial: r?.serial, url: r?.url });
    } catch (err) {
      results.push({ candidateId: body.candidateId, ok: false, error: err.message });
    }
  } else if (body.mode === "backfill_all") {
    // 条件ヒアリングを越えていて serial が無い候補者をスキャン
    const rows = await env.AICA_DB
      .prepare(
        `SELECT id FROM candidates
         WHERE career_sheet_serial IS NULL
           AND profile_json IS NOT NULL
           AND phase IN ('matching','job_qa','apply_confirm','apply_info_name',
                         'apply_info_kana','apply_info_birth','apply_info_phone','apply_info_workplace',
                         'documents_prep_license','documents_prep_school','documents_prep_history',
                         'documents_prep_certs','documents_prep_strengths','documents_gen',
                         'documents_review','approved','applied','paused')
         LIMIT 50`
      )
      .all();
    for (const row of rows.results || []) {
      try {
        const r = await generateCareerSheet({ candidateId: row.id, env, db: env.AICA_DB });
        results.push({ candidateId: row.id, ok: true, serial: r?.serial, url: r?.url });
      } catch (err) {
        results.push({ candidateId: row.id, ok: false, error: err.message });
      }
    }
  } else {
    return new Response(
      JSON.stringify({ error: "provide candidateId or mode=backfill_all" }),
      { status: 400, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(JSON.stringify({ results }, null, 2), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

/** キャリアシート HTML を D1 から取得して返す（社長営業用） */
async function handleCareerSheetView(serial, env) {
  if (!env.AICA_DB) {
    return new Response("DB not bound", { status: 500 });
  }
  try {
    const row = await env.AICA_DB
      .prepare("SELECT career_sheet_html FROM candidates WHERE career_sheet_serial = ?")
      .bind(serial)
      .first();
    if (!row || !row.career_sheet_html) {
      return new Response("Career sheet not found", { status: 404 });
    }
    return new Response(row.career_sheet_html, {
      status: 200,
      headers: {
        "Content-Type": "text/html; charset=utf-8",
        "X-Robots-Tag": "noindex, nofollow",
        "Cache-Control": "private, max-age=60",
      },
    });
  } catch (err) {
    console.error("[career-sheet-view] failed:", err.message);
    return new Response("Internal error", { status: 500 });
  }
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}

/** /health?deep=1 用の依存疎通チェック */
async function checkDependencies(env) {
  const result = {};

  result.aica_db = await timedCheck(async () => {
    const res = await env.AICA_DB.prepare("SELECT 1 AS ok").first();
    if (!res || res.ok !== 1) throw new Error("unexpected result");
  });

  result.nurse_db = await timedCheck(async () => {
    if (!env.NURSE_DB) throw new Error("NURSE_DB not bound");
    const res = await env.NURSE_DB.prepare("SELECT COUNT(*) AS c FROM jobs").first();
    if (!res) throw new Error("unexpected result");
  });

  result.aica_sessions = await timedCheck(async () => {
    if (!env.AICA_SESSIONS) throw new Error("AICA_SESSIONS not bound");
    const key = "__health_probe__";
    await env.AICA_SESSIONS.put(key, String(Date.now()), { expirationTtl: 60 });
    const v = await env.AICA_SESSIONS.get(key);
    if (!v) throw new Error("read-back failed");
  });

  result.openai = await timedCheck(async () => {
    if (!env.OPENAI_API_KEY) throw new Error("OPENAI_API_KEY missing");
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 6000);
    try {
      const r = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${env.OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: "gpt-4o-mini",
          messages: [{ role: "user", content: "ok" }],
          max_tokens: 2,
        }),
        signal: ctrl.signal,
      });
      if (!r.ok) throw new Error(`status ${r.status}`);
    } finally {
      clearTimeout(timeout);
    }
  });

  result.line = await timedCheck(async () => {
    if (!env.LINE_CHANNEL_ACCESS_TOKEN) throw new Error("LINE_CHANNEL_ACCESS_TOKEN missing");
    if (!env.LINE_CHANNEL_SECRET) throw new Error("LINE_CHANNEL_SECRET missing");
  });

  result.slack = await timedCheck(async () => {
    if (!env.SLACK_BOT_TOKEN) throw new Error("SLACK_BOT_TOKEN missing");
    if (!env.SLACK_CHANNEL_AICA) throw new Error("SLACK_CHANNEL_AICA missing");
  });

  return result;
}

async function timedCheck(fn) {
  const start = Date.now();
  try {
    await fn();
    return { ok: true, latency_ms: Date.now() - start };
  } catch (err) {
    return { ok: false, latency_ms: Date.now() - start, error: err.message };
  }
}
