/**
 * フェーズ16: 面接対策（phase: INTERVIEW_PREP）
 *
 * キーワード「面接対策」等で任意のタイミングから入れる。
 * 4モード:
 *   - qa:      想定Q&A 10問（候補者プロフィールから動的生成）
 *   - mock:    模擬面接 5ターン（AIが面接官、ターン毎にフィードバック）
 *   - reverse: 逆質問のコツ（静的アドバイス + 5つの質問例）
 *   - exit:    前のフェーズに戻る
 *
 * 設計書: docs/aica-conversation-flow.md §フェーズ16
 */

import { PHASES, updateCandidate } from "../state-machine.js";
import { buildQuickReplyMessage } from "../lib/line.js";
import { generateResponse } from "../lib/openai.js";

/** 面接対策メニュー */
export function buildInterviewPrepMenu(candidate) {
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "応募先";
  return buildQuickReplyMessage(
    `${employer}の面接対策を始めますか？\n` +
      `以下から選んでください。\n\n` +
      `◇ 想定Q&A → よく聞かれる10問と答え方\n` +
      `◇ 模擬面接 → AIが面接官役で5問\n` +
      `◇ 逆質問のコツ → 面接の最後に聞く質問例\n` +
      `◇ 終わる → 元の会話に戻ります`,
    [
      { label: "想定Q&A", text: "想定Q&A" },
      { label: "模擬面接", text: "模擬面接" },
      { label: "逆質問のコツ", text: "逆質問のコツ" },
      { label: "終わる", text: "面接対策終わる" },
    ]
  );
}

/**
 * Phase 16 のユーザー発言を処理
 * @returns {Promise<{messages:Array, nextPhase:string, provider?:string}>}
 */
export async function handleInterviewPrepTurn({ candidate, userText, env, db }) {
  const t = (userText || "").trim();
  const profile = safeParseJson(candidate.profile_json);
  const mode = profile.interview_mode || null;

  // モードが設定されていない → メニュー表示 or モード選択
  if (!mode) {
    if (/想定.*Q|Q.*A|想定質問|よくある/.test(t)) {
      return await runExpectedQa({ candidate, env, db });
    }
    if (/模擬|練習|シミュ/.test(t)) {
      return await startMockInterview({ candidate, env, db });
    }
    if (/逆質問|最後.*質問|聞きたい.*こと|聞くこと/.test(t)) {
      return runReverseQuestions({ candidate });
    }
    if (/終わる|やめる|戻る|exit/.test(t)) {
      return await exitInterviewPrep({ candidate, db });
    }
    // 不明 → メニュー再表示
    return {
      messages: [buildInterviewPrepMenu(candidate)],
      nextPhase: PHASES.INTERVIEW_PREP,
    };
  }

  // 模擬面接進行中
  if (mode === "mock") {
    if (/終わる|やめる|中止|exit/.test(t)) {
      return await exitInterviewPrep({ candidate, db });
    }
    return await continueMockInterview({ candidate, userText, env, db });
  }

  // それ以外のモードは1ターン完結なので、メニューに戻る
  if (/終わる|やめる|戻る/.test(t)) {
    return await exitInterviewPrep({ candidate, db });
  }
  await clearInterviewMode(db, candidate.id, profile);
  return {
    messages: [buildInterviewPrepMenu(candidate)],
    nextPhase: PHASES.INTERVIEW_PREP,
  };
}

// ============================================================
// 想定Q&A モード
// ============================================================
async function runExpectedQa({ candidate, env, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "応募先の病院";
  const dataBlob = buildCandidateBlob(candidate, profile);

  const systemPrompt = `あなたは看護師の転職面接を数百件支援したキャリアアドバイザーです。
以下の候補者情報に基づき、${employer}での面接で「実際によく聞かれる質問」10問と、
候補者自身のエピソード・強みを引用した「答え方のコツ」を生成してください。

【出力形式（プレーンテキスト、Markdown・コードブロック禁止）】

Q1. {よく聞かれる質問}
ポイント: {この質問の意図。1行}
答え方: {候補者の経歴・強みを1つ引用した、自然な日本語の回答テンプレ。3-4行}

Q2. ...

... Q10まで続ける

【ルール】
・10問の内訳バランス: 志望動機/自己紹介/経験/強み・弱み/キャリアプラン/困難経験/逆質問 を網羅
・候補者プロフィールの具体語（経験分野・役割・心理ヒアリング由来の本音）を引用
・抽象語（「コミュニケーション能力があります」等）は避け、具体場面で語る
・絵文字は使わない
・全体で2500文字以内`;

  const { text, provider } = await generateResponse({
    systemPrompt,
    messages: [{ role: "user", content: dataBlob }],
    env,
    maxTokens: 2500,
  });

  return {
    messages: [
      { type: "text", text: `${employer}の想定Q&Aを作成しました。ご確認ください。` },
      ...splitForLine(text, 4900).map((t) => ({ type: "text", text: t })),
      buildQuickReplyMessage(
        "他の対策もしますか？",
        [
          { label: "模擬面接", text: "模擬面接" },
          { label: "逆質問のコツ", text: "逆質問のコツ" },
          { label: "終わる", text: "面接対策終わる" },
        ]
      ),
    ],
    nextPhase: PHASES.INTERVIEW_PREP,
    provider,
  };
}

// ============================================================
// 模擬面接 モード（5ターン）
// ============================================================
async function startMockInterview({ candidate, env, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "応募先の病院";

  // 初期化
  const newProfile = {
    ...profile,
    interview_mode: "mock",
    interview_mock_turn: 1,
    interview_mock_qa: [],
  };
  await updateCandidate(db, candidate.id, { profile_json: JSON.stringify(newProfile) });

  // 1問目は固定（志望動機）
  const firstQ = `それでは${employer}の模擬面接を始めます。\n` +
    `私が面接官役、${candidate.display_name || "あなた"}さんが応募者役です。\n` +
    `全5問を、実際の面接のつもりで答えてください。\n` +
    `途中で止めたければ「終わる」とお送りください。\n\n` +
    `——————————————\n` +
    `【面接官】1問目\n\n` +
    `本日はお越しいただきありがとうございます。\n` +
    `まず、当院を志望された理由を教えていただけますか？`;

  return {
    messages: [{ type: "text", text: firstQ }],
    nextPhase: PHASES.INTERVIEW_PREP,
  };
}

async function continueMockInterview({ candidate, userText, env, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "応募先の病院";
  const turn = profile.interview_mock_turn || 1;
  const qaHistory = Array.isArray(profile.interview_mock_qa) ? profile.interview_mock_qa : [];

  const dataBlob = buildCandidateBlob(candidate, profile);
  const historyText = qaHistory
    .map((qa, i) => `--- 第${i + 1}問 ---\n面接官: ${qa.q}\n応募者: ${qa.a}`)
    .join("\n\n");

  // 5ターン目の回答後 → 総評
  if (turn >= 5) {
    const systemPrompt = `あなたは看護師の転職面接を数百件支援したキャリアアドバイザーです。
${employer}の模擬面接が5問完了しました。候補者の回答を総合的にフィードバックしてください。

【出力形式】

まず、5問通しての総評を3-5行で。
次に、この候補者に特に助言したいポイントを3つ、箇条書きで。
最後に、本番で特に注意すべき一言。

絵文字は使わない。Markdownは使わない。`;

    const finalTurnText = `--- 第${turn}問 ---\n面接官: ${qaHistory[turn - 1]?.q || ""}\n応募者: ${userText}`;

    const { text: feedback, provider } = await generateResponse({
      systemPrompt,
      messages: [
        { role: "user", content: dataBlob + "\n\n【模擬面接全履歴】\n" + historyText + "\n\n" + finalTurnText },
      ],
      env,
      maxTokens: 700,
    });

    // 5問目を履歴に追加
    qaHistory[turn - 1] = { ...(qaHistory[turn - 1] || {}), a: userText };
    const newProfile = {
      ...profile,
      interview_mode: null,
      interview_mock_turn: null,
      interview_mock_qa: qaHistory,
      interview_mock_last_feedback: feedback,
    };
    await updateCandidate(db, candidate.id, { profile_json: JSON.stringify(newProfile) });

    return {
      messages: [
        { type: "text", text: "おつかれさまでした。5問の模擬面接が完了しました。" },
        { type: "text", text: feedback },
        buildQuickReplyMessage(
          "他の対策もしますか？",
          [
            { label: "もう一度模擬面接", text: "模擬面接" },
            { label: "想定Q&A", text: "想定Q&A" },
            { label: "逆質問のコツ", text: "逆質問のコツ" },
            { label: "終わる", text: "面接対策終わる" },
          ]
        ),
      ],
      nextPhase: PHASES.INTERVIEW_PREP,
      provider,
    };
  }

  // 次の質問を生成（AIがターンごとに動的に決める）
  const systemPrompt = `あなたは${employer}の採用担当者として、看護師候補者の模擬面接を行っています。
現在は全5問中の第${turn}問に対する応募者の回答を受けたところです。
次にやること:
1) 候補者の回答を受け止める一言（共感や評価）
2) 短いフィードバック（良かった点1つ + 改善点1つ、各1行）
3) 次の第${turn + 1}問を投げる（面接官らしく、自然に）

【第${turn + 1}問で聞く内容の推奨】
- 第2問: 自己紹介（経歴・強み）
- 第3問: これまでの経験で最も印象に残っている症例・エピソード
- 第4問: 困難だったこと、どう乗り越えたか
- 第5問: 入職後3年のキャリアプラン、当院で挑戦したいこと

【出力形式】
プレーンテキストで以下の構造:

（受け止めの一言）

【フィードバック】
◯ 良かった点: {1行}
△ 改善点: {1行}

——————————————
【面接官】${turn + 1}問目

（自然な導入 + 質問本文）

絵文字は使わない。Markdownは使わない。全体で400文字以内。`;

  const finalTurnText = `--- 第${turn}問（今回） ---\n面接官: ${qaHistory[turn - 1]?.q || "志望動機を教えてください"}\n応募者: ${userText}`;

  const { text: aiResponse, provider } = await generateResponse({
    systemPrompt,
    messages: [
      { role: "user", content: dataBlob + "\n\n【これまでの面接履歴】\n" + historyText + "\n\n" + finalTurnText },
    ],
    env,
    maxTokens: 600,
  });

  // 次の質問を抽出（「【面接官】...問目」以降の最初のまとまり）
  const nextQMatch = aiResponse.match(/【面接官】[^\n]*\n+([\s\S]*)$/);
  const nextQ = nextQMatch ? nextQMatch[1].trim() : "";

  // 履歴更新
  qaHistory[turn - 1] = { q: qaHistory[turn - 1]?.q || "志望動機", a: userText };
  qaHistory[turn] = { q: nextQ, a: null };

  const newProfile = {
    ...profile,
    interview_mock_turn: turn + 1,
    interview_mock_qa: qaHistory,
  };
  await updateCandidate(db, candidate.id, { profile_json: JSON.stringify(newProfile) });

  return {
    messages: [{ type: "text", text: aiResponse }],
    nextPhase: PHASES.INTERVIEW_PREP,
    provider,
  };
}

// ============================================================
// 逆質問のコツ モード
// ============================================================
function runReverseQuestions({ candidate }) {
  const profile = safeParseJson(candidate.profile_json);
  const employer = profile.apply_candidate_employer || "応募先の病院";
  return {
    messages: [
      {
        type: "text",
        text:
          `${employer}の面接の最後に「何か質問はありますか？」と\n` +
          `必ず聞かれます。ここでの逆質問は、志望度の高さと入職後の\n` +
          `イメージを伝える絶好のチャンスです。\n\n` +
          `【良い逆質問のコツ】\n` +
          `・「御院で働く自分」をイメージさせる\n` +
          `・事前に調べてもわからない「現場の実態」を聞く\n` +
          `・抽象的（「雰囲気は？」）より具体（「日勤リーダーは何年目から？」）\n` +
          `・給与・休日だけ聞くのは避ける（条件面は面接後で可）\n\n` +
          `【NGな逆質問】\n` +
          `・「特にありません」（志望度が低く見える）\n` +
          `・HPで調べればわかること\n` +
          `・給与・残業だけ\n\n` +
          `【看護師面接で使える逆質問5選】\n\n` +
          `1. 「配属後の新人・中途教育体制は、どのような流れでしょうか？」\n` +
          `   → 教育への本気度、自分の早期立ち上がりの話に繋げる\n\n` +
          `2. 「日勤リーダーや委員会活動は、何年目から任されることが多いですか？」\n` +
          `   → 活躍イメージ + 成長意欲を示せる\n\n` +
          `3. 「病棟の平均看護師数と、夜勤体制（2交代/3交代、月あたり回数）を教えていただけますか？」\n` +
          `   → 現場の実態を把握（これは条件面ではなく働き方の具体）\n\n` +
          `4. 「プリセプター制度は何年目からつき、何ヶ月程度で独り立ちですか？」\n` +
          `   → 定着への気配りを見せる\n\n` +
          `5. 「御院が大切にしている看護のあり方を、先輩看護師の方はどんな言葉で表現されますか？」\n` +
          `   → 理念への関心を具体例で聞く`,
      },
      buildQuickReplyMessage(
        "他の対策もしますか？",
        [
          { label: "想定Q&A", text: "想定Q&A" },
          { label: "模擬面接", text: "模擬面接" },
          { label: "終わる", text: "面接対策終わる" },
        ]
      ),
    ],
    nextPhase: PHASES.INTERVIEW_PREP,
  };
}

// ============================================================
// 終了
// ============================================================
async function exitInterviewPrep({ candidate, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const prevPhase = profile.interview_entered_from || PHASES.JOB_QA;

  await clearInterviewMode(db, candidate.id, profile);
  await updateCandidate(db, candidate.id, { phase: prevPhase });

  return {
    messages: [
      {
        type: "text",
        text:
          "面接対策を終わりました。\n" +
          "本番、落ち着いていけば大丈夫です。\n\n" +
          "他にお手伝いが必要なことがあれば、\n" +
          "いつでもお声がけください。",
      },
    ],
    nextPhase: prevPhase,
  };
}

async function clearInterviewMode(db, candidateId, profile) {
  const newProfile = { ...profile };
  delete newProfile.interview_mode;
  delete newProfile.interview_mock_turn;
  delete newProfile.interview_mock_qa;
  delete newProfile.interview_entered_from;
  await updateCandidate(db, candidateId, { profile_json: JSON.stringify(newProfile) });
}

// ============================================================
// エントリ: 既存フェーズから面接対策に入る
// ============================================================
/**
 * ユーザー発言が面接対策への遷移意図を示すか
 */
export function wantsInterviewPrep(text) {
  const t = (text || "").trim();
  return /面接.{0,3}(対策|練習|準備|シミュ|アドバイス|コツ|が不安|どう答え|の相談|どう受け)|模擬面接/.test(t);
}

/**
 * 任意フェーズから INTERVIEW_PREP に入る際のエントリ
 * 元のphaseを interview_entered_from に保存して、終了時に戻れるようにする
 */
export async function enterInterviewPrep({ candidate, db }) {
  const profile = safeParseJson(candidate.profile_json);
  const newProfile = { ...profile, interview_entered_from: candidate.phase };
  await updateCandidate(db, candidate.id, {
    phase: PHASES.INTERVIEW_PREP,
    profile_json: JSON.stringify(newProfile),
  });
  return {
    messages: [buildInterviewPrepMenu(candidate)],
    nextPhase: PHASES.INTERVIEW_PREP,
  };
}

// ============================================================
// ヘルパ
// ============================================================
function buildCandidateBlob(candidate, profile) {
  const lines = [
    `【候補者プロフィール】`,
    `氏名: ${candidate.display_name || "未取得"}`,
    `経験年数: ${profile.experience_years || "未登録"}`,
    `現在の役割: ${profile.current_position || "未登録"}`,
    `経験分野: ${profile.fields_experienced || "未登録"}`,
    `強み: ${profile.strengths || "未登録"}`,
    `苦手: ${profile.weaknesses || "未登録"}`,
    `希望施設: ${profile.facility_hope || "未登録"}`,
    `希望理由: ${profile.facility_reason || "未登録"}`,
    `希望エリア: ${profile.area || "未登録"}`,
    `希望働き方: ${profile.workstyle || "未登録"}`,
    `夜勤詳細: ${profile.night_shift_detail || "未登録"}`,
    `希望給与: ${profile.salary_hope || "未登録"}`,
    `入職時期: ${profile.timing || "未登録"}`,
    `悩みの軸: ${candidate.axis || "未分類"}`,
    `根本原因: ${candidate.root_cause || "未抽出"}`,
    `応募先: ${profile.apply_candidate_employer || "未確定"}`,
  ];
  return lines.join("\n");
}

function splitForLine(text, maxLen = 4900) {
  if (!text) return ["(未生成)"];
  if (text.length <= maxLen) return [text];
  const chunks = [];
  let remaining = text;
  while (remaining.length > maxLen) {
    const cut = remaining.lastIndexOf("\n", maxLen);
    const pos = cut > maxLen / 2 ? cut : maxLen;
    chunks.push(remaining.slice(0, pos));
    remaining = remaining.slice(pos);
  }
  if (remaining) chunks.push(remaining);
  return chunks;
}

function safeParseJson(s) {
  try {
    return s ? JSON.parse(s) : {};
  } catch {
    return {};
  }
}
