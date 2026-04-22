/**
 * フェーズ8: 求人Q&A（phase: JOB_QA / MATCHING）
 *
 * マッチング提示後のフリー対話。ユーザー発言を以下の意図に分類して分岐:
 *   - apply:   「応募したい」「進めたい」「{employer}に進む」 → APPLY_CONFIRM
 *   - more:    「他の求人」「他も見せて」「もう一度」          → 再マッチング
 *   - change:  「条件を変えたい」                           → CONDITION_HEARING に戻る
 *   - pause:   「やめておく」「また今度」                     → PAUSED
 *   - detail:  「1つ目を詳しく」「{employer}を詳しく」        → 求人詳細テキスト
 *   - question: それ以外（求人への質問）                      → AIが事実ベースで回答
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ8
 */

import { PHASES, updateCandidate, logHandoff } from "../state-machine.js";
import { getJobByKjno, formatJobDetail } from "../lib/jobs.js";
import { buildQuickReplyMessage } from "../lib/line.js";
import { generateResponse } from "../lib/openai.js";
import { notifyHandoff } from "../lib/slack.js";
import { buildApplyConfirmMessage } from "./apply.js";

/**
 * Phase 8 (JOB_QA) 用システムプロンプト
 * 提示済み求人の事実のみを根拠に回答。推測禁止。
 */
const JOB_QA_SYSTEM_PROMPT = `あなたは看護師専門のAIキャリアアドバイザーです。
いま提示した求人について、求職者の質問に答えるフェーズです。

【基本ルール】
・提示済み求人の情報（給与/所在地/福利厚生/勤務体系/休日/仕事内容等）は、
  以下に列挙された事実のみを根拠にしてください
・求人データに記載がない項目（夜勤回数/残業/教育体制/面接の厳しさ 等）を
  聞かれた場合は、推測せず次のテンプレで応答してください:

  「ご質問ありがとうございます。
   その点は弊社データに記録がないため、
   先方に確認のうえ1時間以内にお戻しします。

   その間、他にご質問があればお聞きください。」

・憶測・「たぶん」「一般的には」「おそらく」は禁止
・「確認します」と返答した項目は、この場で勝手に想像で埋めない
・回答は300文字以内、丁寧語
・呼称は候補者を「◯◯さん」、病院を施設名そのまま
・絵文字は使わない（区切り記号のみ）
・複数求人に関する比較質問なら「求人1 / 求人2」で比較可

【禁止】
・データに書かれていない事実を創作しない
・「おそらく月4回程度かと」等の曖昧推測

【出力形式】
プレーンテキスト。JSON・Markdown・コードブロックは使わないでください。`;

/**
 * ユーザー発言の意図を分類
 * @param {string} text
 * @param {Array<object>} presentedJobs 提示済み求人レコード配列（employer/kjno含む）
 * @returns {{type:string, targetKjno?:string, employer?:string}}
 */
export function classifyJobPhaseIntent(text, presentedJobs = []) {
  const t = (text || "").trim();

  // ポーズ（離脱示唆）— 最優先
  if (/^(やめ|やっぱり(やめ|いい)|また今度|保留|考えます|考えておきます|考える$|検討します$)/.test(t)) {
    return { type: "pause" };
  }

  // 条件変更
  if (/条件を?(変え|変更|直|やり直)|条件を?少し|別の条件|違う条件/.test(t)) {
    return { type: "change" };
  }

  // もっと見たい（先に判定して詳細と区別）
  if (/他の(求人|職場|病院|施設)|他も|別の(求人|病院)|もう一度|もっと(見|知)|再検索|違う(求人|病院)|他.*見(たい|せて)/.test(t)) {
    return { type: "more" };
  }

  // 番号指定の詳細 (1つ目/2つ目/3つ目 + 詳しく|内容)
  const numMap = { "1": 0, "１": 0, "一": 0, "2": 1, "２": 1, "二": 1, "3": 2, "３": 2, "三": 2 };
  const numMatch = t.match(/([123１２３一二三])\s*(つ?目|番|件目)/);
  if (numMatch) {
    const idx = numMap[numMatch[1]];
    if (idx !== undefined && presentedJobs[idx]) {
      if (/詳しく|詳細|内容|全部|もっと/.test(t)) {
        return { type: "detail", targetKjno: presentedJobs[idx].kjno };
      }
      // 番号だけ、または「1つ目に進みたい」などの応募意思
      if (/進(み|め|む)|応募|決め|これ(で|に)/.test(t)) {
        return {
          type: "apply",
          targetKjno: presentedJobs[idx].kjno,
          employer: presentedJobs[idx].employer,
        };
      }
    }
  }

  // employer名を含む応募意思（「田中病院に進みたい」等、ボタンからのテキスト）
  for (const job of presentedJobs) {
    if (!job.employer) continue;
    if (t.includes(job.employer) && /進(み|め|む)|応募|決め|これ(で|に)|お願い/.test(t)) {
      return { type: "apply", targetKjno: job.kjno, employer: job.employer };
    }
    if (t.includes(job.employer) && /詳しく|詳細|内容|全部/.test(t)) {
      return { type: "detail", targetKjno: job.kjno };
    }
  }

  // employer名指定なしの一般的な応募意思
  if (/応募(し|進|したい)|進めたい|進みたい|お願いします$|この求人で|決めた/.test(t)) {
    // どの求人かが曖昧 → 1件だけ提示されていればそれ、複数なら選択を促す
    if (presentedJobs.length === 1) {
      return { type: "apply", targetKjno: presentedJobs[0].kjno, employer: presentedJobs[0].employer };
    }
    return { type: "apply_ambiguous" };
  }

  // デフォルト: 質問
  return { type: "question" };
}

/**
 * Phase 8 のメインハンドラ
 * @returns {Promise<{messages:Array, nextPhase:string, provider?:string}>}
 */
export async function handleJobQaTurn({ candidate, userText, env, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const presentedIds = (profile.presented_jobs || "").split(",").filter(Boolean);

  // 提示済み求人を NURSE_DB から復元
  const presentedJobs = [];
  for (const kjno of presentedIds) {
    const job = await getJobByKjno(env.NURSE_DB, kjno);
    if (job) presentedJobs.push(job);
  }

  const intent = classifyJobPhaseIntent(userText, presentedJobs);

  // --- PAUSE ---
  if (intent.type === "pause") {
    await updateCandidate(db, candidate.id, { phase: PHASES.PAUSED });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。\n" +
            "お時間のある時に、またお声がけください。\n" +
            "「続きから」とメッセージをいただければ、\n" +
            "今日お伺いした条件で再開できます。",
        },
      ],
      nextPhase: PHASES.PAUSED,
    };
  }

  // --- CHANGE ---
  if (intent.type === "change") {
    await updateCandidate(db, candidate.id, { phase: PHASES.CONDITION_HEARING });
    return {
      messages: [
        {
          type: "text",
          text:
            "承知しました。条件を見直しますね。\n" +
            "変更したいのはどの項目ですか？\n" +
            "（エリア・働き方・給与・時期 など、自由に教えてください）",
        },
      ],
      nextPhase: PHASES.CONDITION_HEARING,
    };
  }

  // --- MORE ---
  if (intent.type === "more") {
    // runMatching は呼び出し側で実行（既存の挙動を保つ）
    return { messages: null, nextPhase: PHASES.MATCHING, rerunMatching: true };
  }

  // --- DETAIL ---
  if (intent.type === "detail") {
    const job = await getJobByKjno(env.NURSE_DB, intent.targetKjno);
    const detail = formatJobDetail(job);
    return {
      messages: [
        { type: "text", text: detail },
        buildQuickReplyMessage(
          "気になる点や質問があれば教えてください。",
          [
            { label: "この求人で進める", text: `${job?.employer || "この求人"}に進みたい` },
            { label: "他の求人も見たい", text: "他の求人も見たい" },
            { label: "条件を変えたい", text: "条件を変えたい" },
          ]
        ),
      ],
      nextPhase: PHASES.JOB_QA,
    };
  }

  // --- APPLY_AMBIGUOUS ---
  if (intent.type === "apply_ambiguous") {
    const quickItems = presentedJobs.map((j, i) => ({
      label: `${i + 1}つ目で進む`,
      text: `${j.employer}に進みたい`,
    }));
    return {
      messages: [
        buildQuickReplyMessage(
          "応募を進めたい求人はどれですか？",
          quickItems.length > 0 ? quickItems : [{ label: "もう一度見たい", text: "もう一度見せて" }]
        ),
      ],
      nextPhase: PHASES.JOB_QA,
    };
  }

  // --- APPLY ---
  if (intent.type === "apply") {
    const job = presentedJobs.find((j) => j.kjno === intent.targetKjno);
    const employer = intent.employer || job?.employer || "この求人";

    // 応募候補 kjno を保存
    const newProfile = { ...profile, apply_candidate_kjno: intent.targetKjno, apply_candidate_employer: employer };
    await updateCandidate(db, candidate.id, {
      phase: PHASES.APPLY_CONFIRM,
      profile_json: JSON.stringify(newProfile),
    });

    return {
      messages: [buildApplyConfirmMessage({ employer })],
      nextPhase: PHASES.APPLY_CONFIRM,
    };
  }

  // --- QUESTION（AI対話）---
  const contextText = buildJobContextText(presentedJobs);
  const systemPrompt = `${JOB_QA_SYSTEM_PROMPT}\n\n【提示済み求人（事実ベースでのみ回答）】\n${contextText}`;

  const { text: reply, provider } = await generateResponse({
    systemPrompt,
    messages: [{ role: "user", content: userText }],
    env,
    maxTokens: 350,
  });

  // 「記録がないため先方に確認」と返したか判定 → Slack通知
  const unknownSignal =
    /記録がありません|確認のうえ|(先方|病院).{0,5}確認/.test(reply);
  if (unknownSignal) {
    try {
      await logHandoff(db, candidate.id, "Q&A情報不足（病院確認依頼）", "info", PHASES.JOB_QA);
      await notifyHandoff({
        candidateId: candidate.id,
        displayName: candidate.display_name,
        reason: "Q&A情報不足・病院確認依頼",
        phase: PHASES.JOB_QA,
        summary: `候補者の質問:\n${userText}\n\nAI応答:\n${reply}`,
        env,
      });
    } catch (err) {
      console.warn("[job-qa] handoff notify failed:", err.message);
    }
  }

  return {
    messages: [
      { type: "text", text: reply },
      buildQuickReplyMessage(
        "他に気になる点はありますか？",
        [
          { label: "この求人で進める", text: presentedJobs[0] ? `${presentedJobs[0].employer}に進みたい` : "応募したい" },
          { label: "他の求人も見たい", text: "他の求人も見たい" },
          { label: "条件を変えたい", text: "条件を変えたい" },
        ]
      ),
    ],
    nextPhase: PHASES.JOB_QA,
    provider,
  };
}

/** 求人レコード配列 → AIへの事実コンテキストテキスト */
function buildJobContextText(jobs) {
  if (!jobs.length) return "(提示済み求人なし)";
  return jobs
    .map((j, i) => {
      const lines = [`■ 求人${i + 1}: ${j.employer || "施設名不明"} (kjno: ${j.kjno || "-"})`];
      if (j.title) lines.push(`  タイトル: ${j.title}`);
      if (j.salary_display || j.salary_min || j.salary_max) {
        const min = j.salary_min ? `${Math.round(j.salary_min / 10000)}万円` : "";
        const max = j.salary_max ? `${Math.round(j.salary_max / 10000)}万円` : "";
        lines.push(`  給与: ${j.salary_display || `${min}${max ? "〜" + max : ""}`}`);
      }
      if (j.bonus_text) lines.push(`  賞与: ${j.bonus_text}`);
      if (j.work_location) lines.push(`  所在地: ${j.work_location}`);
      if (j.station_text) lines.push(`  最寄駅: ${j.station_text}`);
      if (j.emp_type) lines.push(`  雇用形態: ${j.emp_type}`);
      const shifts = [j.shift1, j.shift2].filter(Boolean).join(" / ");
      if (shifts) lines.push(`  勤務体系: ${shifts}`);
      if (j.holidays) lines.push(`  休日: 年${j.holidays}日`);
      if (j.welfare) lines.push(`  待遇・福利厚生: ${j.welfare.slice(0, 300)}`);
      if (j.description) lines.push(`  仕事内容: ${j.description.slice(0, 400)}`);
      return lines.join("\n");
    })
    .join("\n\n");
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
