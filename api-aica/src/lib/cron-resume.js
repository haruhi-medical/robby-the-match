/**
 * PAUSED 候補者に「続きから」を促す Push（cron用）
 *
 * 発火: 毎日 09:00 JST (= 00:00 UTC)
 * 対象: candidates.phase='paused' かつ profile_json.paused_at から
 *       3日経過 or 7日経過のユーザー
 *
 * 3日後: 軽めの再開促し
 * 7日後: 最後通告（これ以降はPushしない、自然解消）
 *
 * 重複Push防止: profile_json.resume_push_sent_at にタイムスタンプを保存
 */

import { pushMessage } from "./line.js";
import { phaseToStage } from "./staging.js";

const DAY_MS = 86400000;

export async function processPausedResumePush(env) {
  if (!env.AICA_DB || !env.LINE_CHANNEL_ACCESS_TOKEN) {
    console.warn("[cron-resume] required bindings missing");
    return;
  }

  const now = Date.now();

  // phase=PAUSED の全候補者を取得
  const res = await env.AICA_DB
    .prepare("SELECT id, display_name, profile_json, updated_at FROM candidates WHERE phase = 'paused'")
    .all();

  const candidates = res.results || [];
  let day3Count = 0;
  let day7Count = 0;
  let skipCount = 0;

  for (const c of candidates) {
    const profile = safeParseJson(c.profile_json);
    const pausedAt = profile.paused_at || c.updated_at;
    if (!pausedAt) continue;

    const elapsed = now - pausedAt;
    const daysSince = Math.floor(elapsed / DAY_MS);
    const resumeFrom = profile.resume_from;

    // resume_from が無いユーザーは自然離脱。Pushしない
    if (!resumeFrom) continue;

    const already = profile.resume_push_sent_at || {};
    const stage = phaseToStage(resumeFrom) || 2;
    const employer = profile.apply_candidate_employer || null;

    let pushType = null;
    if (daysSince >= 7 && !already.day7) pushType = "day7";
    else if (daysSince >= 3 && !already.day3) pushType = "day3";

    if (!pushType) {
      skipCount++;
      continue;
    }

    const message = buildResumePushMessage({
      displayName: c.display_name,
      pushType,
      stage,
      employer,
    });

    try {
      await pushMessage(c.id, [message], env.LINE_CHANNEL_ACCESS_TOKEN);
      already[pushType] = now;
      const newProfile = { ...profile, resume_push_sent_at: already };
      await env.AICA_DB
        .prepare("UPDATE candidates SET profile_json = ?, updated_at = ? WHERE id = ?")
        .bind(JSON.stringify(newProfile), now, c.id)
        .run();

      if (pushType === "day3") day3Count++;
      else day7Count++;
    } catch (err) {
      // ブロックされている等は 400 が返る。スキップして次へ
      console.warn(`[cron-resume] push failed for ${c.id}:`, err.message);
    }
  }

  console.log(`[cron-resume] day3=${day3Count} day7=${day7Count} skip=${skipCount} total=${candidates.length}`);

  return { day3Count, day7Count, skipCount, total: candidates.length };
}

function buildResumePushMessage({ displayName, pushType, stage, employer }) {
  const name = displayName ? `${displayName}さん` : "";
  const where = employer ? `${employer}への` : "";
  const stageLabel = stage === 2 ? "応募準備" : stage === 3 ? "面接準備" : "会話";

  if (pushType === "day3") {
    return {
      type: "text",
      text:
        (name ? `${name}、こんにちは。\n\n` : "こんにちは。\n\n") +
        `先日の${where}${stageLabel}、ここまで保存してあります。\n\n` +
        `「続きから」とメッセージを送っていただければ、\n` +
        `前回の続きから再開できます。\n\n` +
        `お時間のある時でかまいません。`,
    };
  }

  // day7: 最終通告（これ以降はPushしない）
  return {
    type: "text",
    text:
      (name ? `${name}、\n\n` : "") +
      `先日の${where}${stageLabel}、まだ保存してあります。\n\n` +
      `「続きから」でいつでも再開できます。\n` +
      `もし今は転職を急いでいないようでしたら、\n` +
      `このメッセージはお気になさらずで大丈夫です。\n\n` +
      `今後は、新着求人のご案内のみお送りします。`,
  };
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
