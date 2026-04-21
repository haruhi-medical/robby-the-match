/**
 * フェーズ7: 求人マッチング提示
 * プロファイル補強完了直後、D1 jobs から検索して Flex Carousel で提示
 */

import { PHASES, updateCandidate, logMessage } from "../state-machine.js";
import { searchJobs, jobsToFlexCarousel } from "../lib/jobs.js";
import { pushMessage } from "../lib/line.js";
import { buildQuickReplyMessage } from "../lib/line.js";

/**
 * Matching を実行して LINE に Push で求人を送る
 */
export async function runMatching({ candidate, env, db }) {
  let profile = {};
  try {
    profile = candidate.profile_json ? JSON.parse(candidate.profile_json) : {};
  } catch {
    profile = {};
  }

  const jobs = await searchJobs({ profile, db: env.NURSE_DB, limit: 3 });

  const messages = [];

  if (jobs.length === 0) {
    messages.push({
      type: "text",
      text:
        "お待たせしました。\n" +
        "条件に合う求人を神奈川県内からお探ししましたが、\n" +
        "現時点で即ご紹介できるものは限られていました。\n\n" +
        "条件を少し広げて再検索しますか？\n" +
        "それとも他にお聞きしたいことがありますか？",
    });
  } else {
    messages.push({
      type: "text",
      text:
        `お待たせしました。\n` +
        `${candidate.display_name || "お客様"}さんの条件にマッチする求人を\n` +
        `${jobs.length}件お選びしました。`,
    });
    const carousel = jobsToFlexCarousel(jobs);
    if (carousel) messages.push(carousel);
    messages.push(
      buildQuickReplyMessage(
        "気になる求人はありましたか？",
        [
          { label: "1つ目を詳しく", text: "1つ目の求人を詳しく" },
          { label: "2つ目を詳しく", text: "2つ目の求人を詳しく" },
          { label: "3つ目を詳しく", text: "3つ目の求人を詳しく" },
          { label: "他の求人も見たい", text: "他の求人も見たい" },
          { label: "条件を変えたい", text: "条件を変えたい" },
          { label: "質問したい", text: "質問したい" },
        ]
      )
    );
  }

  // 求人IDリストをcandidateに保存（後のQ&Aで参照）
  const presentedIds = jobs.map((j) => j.kjno).join(",");

  await updateCandidate(db, candidate.id, {
    phase: PHASES.JOB_QA,
    profile_json: JSON.stringify({ ...profile, presented_jobs: presentedIds }),
  });

  // Push で送信（reply token は既に消費済みの前提）
  if (env.LINE_CHANNEL_ACCESS_TOKEN) {
    try {
      await pushMessage(candidate.id, messages, env.LINE_CHANNEL_ACCESS_TOKEN);
      await logMessage(
        db,
        candidate.id,
        "assistant",
        `[matching] ${jobs.length} jobs presented`,
        PHASES.JOB_QA,
        0,
        "matching-template"
      );
    } catch (err) {
      console.error("[matching] push failed:", err.message);
    }
  }

  return { jobCount: jobs.length };
}
