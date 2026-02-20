# ROBBY THE MATCH - AI統合アーキテクチャ設計書

**作成日:** 2026-02-16
**バージョン:** 1.0
**対象システム:** ROBBY THE MATCH 医療人材マッチングプラットフォーム

---

## 目次

1. [現状分析](#1-現状分析)
2. [Claude API統合（Cloudflare Workers経由）](#2-claude-api統合cloudflare-workers経由)
3. [会話インテリジェンス](#3-会話インテリジェンス)
4. [マッチングエンジン](#4-マッチングエンジン)
5. [安全性・コンプライアンス](#5-安全性コンプライアンス)
6. [リクルーターダッシュボード強化](#6-リクルーターダッシュボード強化)
7. [実装ロードマップ](#7-実装ロードマップ)

---

## 1. 現状分析

### 1.1 既存アーキテクチャ

```
[ブラウザ] ── chat.js（デモモード） ── 固定レスポンス9パターン
                                          │
                                    ── config.js（workerEndpoint未設定）
                                          │
[Cloudflare Workers] ── worker.js ── /api/register（フォーム送信のみ）
                                   ── Slack通知
                                   ── Google Sheets連携
```

### 1.2 現状の制約

| 項目 | 現状 | 課題 |
|------|------|------|
| チャット応答 | デモモード（固定9パターン） | ユーザーの実回答に無関係な応答 |
| API連携 | `workerEndpoint`未設定 | Claude APIへの接続なし |
| プロファイリング | なし | 会話からの情報抽出不可 |
| マッチング | 固定病院1件のみ提示 | 個別条件に応じた提案不可 |
| Slack通知 | フォーム送信時のみ | チャット完了時の通知はコンソール出力のみ |
| データ永続化 | Google Sheets（フォーム送信のみ） | チャットデータの保存なし |

### 1.3 既存コードの強み（活用ポイント）

- **chat.js**: 5ステップ会話フロー設計が堅実。ステップ管理・タイピングインジケータ・同意管理が実装済み
- **SYSTEM_PROMPT**: JSON形式のレスポンス仕様が明確に定義済み（`reply`, `step`, `score`, `done`, `summary`）
- **worker.js**: レート制限・リトライ・サニタイズ・Google認証など基盤が整備済み
- **chat.css**: モバイル対応済みのUI。ストリーミング対応に拡張可能

---

## 2. Claude API統合（Cloudflare Workers経由）

### 2.1 アーキテクチャ概要

```
[ブラウザ chat.js]
     │
     │ POST /api/chat  （会話履歴 + システムプロンプト）
     ▼
[Cloudflare Workers]  ── APIキーをサーバー側で保持（env.ANTHROPIC_API_KEY）
     │
     │ POST https://api.anthropic.com/v1/messages
     │   Headers: x-api-key, anthropic-version
     │   Body: system + messages + max_tokens + temperature
     ▼
[Anthropic Claude API]
     │
     │ レスポンス（JSON or ストリーミング）
     ▼
[Cloudflare Workers]  ── レスポンス解析・検証・変換
     │
     │ JSON or SSE（Server-Sent Events）
     ▼
[ブラウザ chat.js]  ── 表示・ステップ更新・スコア更新
```

### 2.2 Workers APIエンドポイント設計

#### `/api/chat` - チャットメッセージ送信

```javascript
// リクエスト
POST /api/chat
Content-Type: application/json

{
  "messages": [
    { "role": "user", "content": "夜勤が多くて体がきついので転職を考えています" },
    { "role": "assistant", "content": "{\"reply\": \"...\", \"step\": 1, ...}" }
  ],
  "sessionId": "uuid-v4",    // セッション追跡用
  "stream": false             // true でストリーミングモード
}

// レスポンス（通常モード）
{
  "reply": "お気持ちはよく分かります。夜勤の負担は...",
  "step": 2,
  "score": "C",
  "done": false,
  "summary": null,
  "profile": {                // Phase 2b で追加
    "transferReason": "夜勤の身体的負担",
    "currentWorkStyle": "夜勤あり"
  }
}
```

#### `/api/chat/stream` - ストリーミングチャット

```javascript
// リクエスト: 同上（stream: true）
// レスポンス: SSE (Server-Sent Events)

data: {"type": "text_delta", "text": "お気持ちは"}
data: {"type": "text_delta", "text": "よく分かります。"}
data: {"type": "text_delta", "text": "夜勤の負担は..."}
data: {"type": "metadata", "step": 2, "score": "C", "done": false}
data: [DONE]
```

#### `/api/notify` - Slack通知（既存の拡張）

```javascript
// リクエスト
POST /api/notify
Content-Type: application/json

{
  "type": "chat_summary",
  "sessionId": "uuid-v4",
  "score": "A",
  "summary": "看護師転職希望...",
  "profile": { ... },
  "messageCount": 12,
  "conversationDuration": "18分"
}
```

### 2.3 Workers実装設計

```javascript
// worker.js に追加するチャットハンドラ

async function handleChat(request, env) {
  const allowedOrigin = getAllowedOrigin(env);

  // 1. レート制限（チャット用: 1分あたり20メッセージ）
  const clientIP = request.headers.get("CF-Connecting-IP") || "unknown";
  const chatRateLimit = checkChatRateLimit(clientIP, env);
  if (!chatRateLimit.allowed) {
    return jsonResponse(
      { error: "メッセージ送信が速すぎます。少しお待ちください。" },
      429, allowedOrigin
    );
  }

  // 2. リクエスト解析・検証
  const { messages, sessionId, stream } = await request.json();

  if (!messages || !Array.isArray(messages)) {
    return jsonResponse({ error: "Invalid messages format" }, 400, allowedOrigin);
  }

  // メッセージ数上限チェック（コスト制御）
  if (messages.length > 60) {
    return jsonResponse(
      { error: "会話が長くなりました。新しい相談を開始してください。" },
      400, allowedOrigin
    );
  }

  // 3. システムプロンプト構築（サーバー側で管理）
  const systemPrompt = buildSystemPrompt(env);

  // 4. Claude API呼び出し
  const apiResponse = await callClaudeAPI(systemPrompt, messages, env, stream);

  if (stream) {
    // SSEストリーミング返却
    return new Response(apiResponse.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Access-Control-Allow-Origin": allowedOrigin,
      },
    });
  }

  // 5. レスポンス解析・検証
  const parsed = parseAndValidateResponse(apiResponse);

  // 6. セッションデータ保存（KV/D1）
  if (sessionId) {
    await saveSessionData(sessionId, messages, parsed, env);
  }

  return jsonResponse(parsed, 200, allowedOrigin);
}
```

### 2.4 APIキー管理とセキュリティ

```
[Cloudflare Workers 環境変数（Secrets）]
├── ANTHROPIC_API_KEY    ← Claude APIキー（絶対にクライアントに露出させない）
├── SLACK_WEBHOOK_URL    ← 既存
├── GOOGLE_SERVICE_ACCOUNT_JSON ← 既存
├── ALLOWED_ORIGIN       ← 既存（CORS制御）
└── SESSION_ENCRYPTION_KEY ← セッションデータ暗号化キー
```

**セキュリティ原則:**
- APIキーはCloudflare Workers Secretsに格納。`wrangler secret put ANTHROPIC_API_KEY` で設定
- クライアント側（chat.js）にはAPIキーを一切含めない
- `SYSTEM_PROMPT`もサーバー側で構築し、クライアントから送信されたものは無視する
- セッションデータはAES-256-GCMで暗号化して保存

### 2.5 レート制限・コスト制御

```javascript
// コスト制御の多層防御

const COST_LIMITS = {
  // レイヤー1: IPベースレート制限
  chatMessagesPerMinute: 20,      // 1分あたり20メッセージ/IP
  chatSessionsPerHour: 5,         // 1時間あたり5セッション/IP

  // レイヤー2: メッセージ制限
  maxMessagesPerSession: 30,       // 1セッション最大30往復
  maxInputTokens: 2000,            // ユーザー入力は2000トークンまで

  // レイヤー3: API呼び出し制限
  maxTokensPerResponse: 500,       // AIレスポンスは500トークンまで
  claudeModel: "claude-sonnet-4-5-20250929", // コスト効率の良いモデル

  // レイヤー4: 月間コスト上限
  monthlyBudgetUSD: 100,           // 月間100ドル上限
  alertThresholdPercent: 80,       // 80%到達でSlackアラート
};
```

**モデル選択の根拠:**
- Phase 2a: `claude-sonnet-4-5-20250929` -- コスト効率が良く、会話品質も十分
- Phase 2c（高度なマッチング分析時のみ）: `claude-opus-4-6` -- 複雑な推論が必要な場合

**推定コスト:**
- 1会話あたり平均: 入力3,000トークン + 出力1,500トークン = 約$0.02
- 月間500会話想定: 約$10/月
- バッファ含め月間予算: $100

---

## 3. 会話インテリジェンス

### 3.1 看護師プロファイリング

会話の自然な流れから以下の情報を段階的に抽出する。

```javascript
// NurseProfile データモデル
const NurseProfile = {
  // Step 1-2 で抽出
  basic: {
    transferReason: "",          // 転職理由（例: "夜勤の身体的負担"）
    currentFacility: "",         // 現在の施設（例: "急性期200床"）
    currentDepartment: "",       // 現在の診療科
    yearsOfExperience: null,     // 経験年数
    specialties: [],             // 専門分野（例: ["救急", "ICU"]）
    certifications: [],          // 資格（例: ["正看護師", "認定看護師"]）
    currentWorkStyle: "",        // 現在の勤務形態
    urgency: "",                 // 転職の緊急度
  },

  // Step 3 で抽出
  preferences: {
    desiredSalary: { min: null, max: null },  // 希望月給レンジ
    desiredHolidays: "",                       // 休日希望
    nightShiftPreference: "",                  // 夜勤希望（可/不可/相談）
    maxCommuteTime: null,                      // 最大通勤時間（分）
    commuteMethod: "",                         // 通勤手段
    facilitySize: "",                          // 希望病院規模
    facilityType: "",                          // 希望施設タイプ
    departmentPreference: [],                  // 希望診療科
    workLifeBalance: [],                       // WLB要因（育児、介護等）
  },

  // Step 4-5 で抽出
  engagement: {
    interestedHospitals: [],     // 興味を示した病院ID
    interviewPreference: "",     // 面接形式希望
    availableDates: [],          // 面接可能日
    concerns: [],                // 不安・懸念事項
  },

  // メタデータ
  metadata: {
    extractedAt: [],             // 抽出タイミング記録
    confidence: {},              // 各フィールドの抽出信頼度
  },
};
```

### 3.2 プロファイリング用システムプロンプト拡張

```javascript
function buildSystemPrompt(env) {
  // 既存のSYSTEM_PROMPTをベースに、サーバー側で構築
  return `あなたは「ROBBY THE MATCH」のAI転職相談アシスタントです。
看護師の転職をサポートする、温かく専門的なカウンセラーとして会話してください。

【厳守ルール】
- 条件を断定しないこと。「詳細は担当者が確認します」を必ず添える
- 給与・条件は「目安として」「概算で」の表現を使う
- 「最高」「No.1」「絶対」「必ず」等の断定的・最上級表現は禁止
- 個人情報の取り扱いに注意し、最初に同意を取得する
- 有料職業紹介事業者として職業安定法を遵守する

【会話フロー（5ステップ）】
Step 1 - アイスブレイク（2分）: 挨拶・自己紹介、転職検討の背景を軽く聞く
Step 2 - 現状ヒアリング（5分）: 現在の職場・勤務形態、転職理由、最重視する条件
Step 3 - 希望条件詳細（5分）: 希望給与額、休日数・夜勤頻度、通勤時間・交通手段、病院規模・診療科
Step 4 - マッチング提案（5分）: 条件に合う提携病院の紹介、各病院の特徴・メリット、見学・面接の意向確認
Step 5 - 面接調整（3分）: 希望面接日程（第3希望まで）、面接形式の希望、次のステップ説明

【提携病院情報】
${getHospitalInfo(env)}

【プロファイリング指示】
会話の中から以下の情報を自然に抽出し、profileフィールドに格納してください:
- 転職理由、現在の職場情報、経験・専門分野
- 給与・休日・夜勤・通勤などの希望条件
- 興味を示した病院、面接希望
新しい情報が得られたステップのみ、該当フィールドを更新してください。

【重要】
- 1回の返答は3〜5文程度に収める
- 質問は1つずつ聞く
- 相手の言葉に共感してから次の質問に進む
- 現在のステップを把握し、自然に次のステップへ移行する

返答のJSON形式:
{
  "reply": "返答テキスト",
  "step": 1-5,
  "score": "A/B/C/D/null",
  "done": false,
  "summary": null,
  "profile": {
    "transferReason": "...",
    "currentFacility": "...",
    ...変更があったフィールドのみ
  }
}`;
}
```

### 3.3 温度感スコアリング強化

現在のA-Dシステムを、AIが会話内容から多次元的に判定する方式に強化。

```
【温度感スコアリング基準（AIへの指示に含める）】

A（即対応）: 以下の2つ以上に該当
  - 「すぐにでも」「来月から」等の明確な時期表現
  - 具体的な希望条件を複数提示
  - 面接日程の具体的提案
  - 現職への強い不満・退職済み

B（積極検討中）: 以下の2つ以上に該当
  - 「1-2ヶ月以内」程度の時期感
  - 条件の優先順位が明確
  - 紹介病院に具体的な質問
  - 他社比較中の言及

C（情報収集段階）: 以下に該当
  - 「いい条件があれば」等の条件付き表現
  - 条件がまだ曖昧
  - 質問が一般的（業界全体の傾向など）

D（長期検討）: 以下に該当
  - 「まだ先の話」「いつかは」等
  - 現職に大きな不満なし
  - 情報収集目的のみ
```

### 3.4 マルチターンコンテキスト管理

```javascript
// クライアント側（chat.js）のメッセージ管理
// 既存の chatState.apiMessages をそのまま活用

// サーバー側: コンテキストウィンドウ管理
function prepareMessagesForAPI(messages, systemPrompt) {
  // 1. システムプロンプト + 全メッセージのトークン数を推定
  const estimatedTokens = estimateTokens(systemPrompt, messages);

  // 2. 上限（入力4,000トークン）を超える場合、古いメッセージを要約
  if (estimatedTokens > 4000) {
    const oldMessages = messages.slice(0, -10);  // 直近10往復は保持
    const summary = summarizeOldMessages(oldMessages);
    return [
      { role: "user", content: `[過去の会話要約] ${summary}` },
      { role: "assistant", content: "承知しました。続けましょう。" },
      ...messages.slice(-10),
    ];
  }

  return messages;
}
```

---

## 4. マッチングエンジン

### 4.1 病院要件データモデル

```javascript
// 病院データ（Cloudflare D1 または KVに格納）
const HospitalRequirement = {
  id: "hospital_a",
  displayName: "A病院（小田原市・163床）",
  type: "混合型（慢性期・回復期・療養型）",
  beds: 163,

  // 求人条件
  openPositions: [
    {
      department: "混合病棟",
      workStyle: "常勤",
      salary: { min: 280000, max: 350000 },
      nightShift: "応相談",
      holidays: 110,
      requirements: {
        minExperience: 1,           // 最低経験年数
        requiredCertifications: ["正看護師"],
        preferredSpecialties: ["慢性期", "回復期"],
        preferredExperience: 3,     // 希望経験年数
      },
    },
  ],

  // アクセス情報
  access: {
    nearestStation: "小田原駅",
    commuteMethod: "バス",
    commuteMinutes: 15,
    parkingAvailable: true,
  },

  // 職場環境
  environment: {
    averageAge: 38,
    staffCount: 85,
    turnoverRate: 0.08,            // 離職率8%
    features: ["100年以上の歴史", "地域密着型", "教育体制充実"],
    culture: "アットホーム",
  },

  // マッチング重み（病院側の重視ポイント）
  matchWeights: {
    experience: 0.3,
    specialty: 0.25,
    availability: 0.25,
    cultureFit: 0.2,
  },
};
```

### 4.2 マッチングスコアリングアルゴリズム

```javascript
function calculateMatchScore(nurseProfile, hospital) {
  let totalScore = 0;
  let maxScore = 0;
  const breakdown = {};

  // --- 1. 給与マッチ（重み: 25%） ---
  const salaryScore = scoreSalaryMatch(
    nurseProfile.preferences.desiredSalary,
    hospital.openPositions[0].salary
  );
  breakdown.salary = salaryScore;
  totalScore += salaryScore * 0.25;
  maxScore += 0.25;

  // --- 2. 通勤マッチ（重み: 20%） ---
  const commuteScore = scoreCommuteMatch(
    nurseProfile.preferences.maxCommuteTime,
    nurseProfile.preferences.commuteMethod,
    hospital.access
  );
  breakdown.commute = commuteScore;
  totalScore += commuteScore * 0.20;
  maxScore += 0.20;

  // --- 3. 勤務条件マッチ（重み: 20%） ---
  const conditionScore = scoreConditionMatch(
    nurseProfile.preferences,
    hospital.openPositions[0]
  );
  breakdown.conditions = conditionScore;
  totalScore += conditionScore * 0.20;
  maxScore += 0.20;

  // --- 4. 経験・スキルマッチ（重み: 20%） ---
  const skillScore = scoreSkillMatch(
    nurseProfile.basic,
    hospital.openPositions[0].requirements
  );
  breakdown.skills = skillScore;
  totalScore += skillScore * 0.20;
  maxScore += 0.20;

  // --- 5. カルチャーフィット（重み: 15%） ---
  const cultureScore = scoreCultureFit(
    nurseProfile,
    hospital.environment
  );
  breakdown.culture = cultureScore;
  totalScore += cultureScore * 0.15;
  maxScore += 0.15;

  return {
    totalScore: Math.round((totalScore / maxScore) * 100),
    breakdown,
    recommendation: totalScore / maxScore >= 0.7 ? "strong" :
                    totalScore / maxScore >= 0.5 ? "moderate" : "weak",
  };
}

// 給与マッチの詳細
function scoreSalaryMatch(desired, offered) {
  if (!desired || !desired.min) return 0.5; // 情報不足は中立

  // 希望最低額が提供レンジ内: 1.0
  if (desired.min >= offered.min && desired.min <= offered.max) return 1.0;
  // 希望最低額が提供最高額を少し上回る（10%以内）: 0.6
  if (desired.min <= offered.max * 1.1) return 0.6;
  // 大幅に乖離: 0.2
  return 0.2;
}

// 通勤マッチの詳細
function scoreCommuteMatch(maxTime, method, access) {
  if (!maxTime) return 0.5;

  if (access.commuteMinutes <= maxTime) return 1.0;
  if (access.commuteMinutes <= maxTime * 1.2) return 0.7;
  return 0.3;
}
```

### 4.3 レコメンデーションランキング

```javascript
function rankHospitals(nurseProfile, hospitals) {
  const results = hospitals.map(hospital => {
    const matchResult = calculateMatchScore(nurseProfile, hospital);
    return {
      hospital,
      ...matchResult,
    };
  });

  // スコア降順でソート
  results.sort((a, b) => b.totalScore - a.totalScore);

  // AIに渡すマッチング結果（Step 4 で使用）
  return results.map((r, index) => ({
    rank: index + 1,
    hospitalId: r.hospital.id,
    displayName: r.hospital.displayName,
    totalScore: r.totalScore,
    recommendation: r.recommendation,
    breakdown: r.breakdown,
    highlights: generateHighlights(r),  // 「通勤20分以内」「希望給与レンジ内」等
    concerns: generateConcerns(r),      // 「夜勤あり（応相談）」等
  }));
}
```

### 4.4 AI連携マッチング（Step 4 での活用）

```javascript
// Step 4 に入る際、システムプロンプトにマッチング結果を注入
function enrichSystemPromptWithMatching(basePrompt, nurseProfile, env) {
  const hospitals = getHospitalData(env);
  const rankings = rankHospitals(nurseProfile, hospitals);

  const matchingSection = `
【マッチング結果（この情報をもとに提案してください）】
${rankings.map(r => `
${r.rank}位: ${r.displayName}（適合度 ${r.totalScore}%）
  強み: ${r.highlights.join("、")}
  注意点: ${r.concerns.join("、")}
`).join("")}

マッチング結果が良い順に紹介してください。
適合度70%以上の病院を中心に紹介し、それ以下の場合は
「ご希望に完全に合う求人は現在調整中ですが、近い条件の病院として」と前置きしてください。`;

  return basePrompt + matchingSection;
}
```

---

## 5. 安全性・コンプライアンス

### 5.1 職業安定法（有料職業紹介事業）準拠

```
【法令遵守チェックリスト】

1. 求人情報の正確性（職安法第5条の4）
   - 給与は「目安」「概算」表記を徹底
   - 「詳細は担当者が確認します」を必ず付記
   - 労働条件の明示義務に準拠

2. 差別的取扱いの禁止（職安法第3条）
   - 年齢・性別・出身地等による差別的な応答をしない
   - AIの応答をフィルタリング

3. 個人情報保護（職安法第5条の5、個人情報保護法）
   - 会話開始前に同意取得（実装済み）
   - データは転職支援目的のみに使用
   - 保持期間の明示と期限後の削除

4. 手数料に関する表示（職安法第32条の3）
   - 手数料率の明確な表示
   - 求職者からの手数料徴収禁止の遵守
```

### 5.2 AIレスポンスのガードレール

```javascript
// サーバー側でAIレスポンスを検証するフィルタ

function validateAIResponse(response) {
  const violations = [];

  // 1. 禁止表現チェック
  const bannedPatterns = [
    /必ず|絶対|確実|保証/,          // 断定的表現
    /最高|No\.?1|業界一/,           // 最上級表現
    /年収\d+万円(?!.*目安|概算)/,   // 具体的金額の断定
    /採用されます|内定/,             // 採用保証
  ];

  for (const pattern of bannedPatterns) {
    if (pattern.test(response.reply)) {
      violations.push({
        type: "banned_expression",
        pattern: pattern.toString(),
        severity: "high",
      });
    }
  }

  // 2. 安全表現の確認（Step 4以降で条件提示時）
  if (response.step >= 4 && /万円|給与|月給|年収/.test(response.reply)) {
    if (!/目安|概算|担当者.*確認|詳細.*確認/.test(response.reply)) {
      violations.push({
        type: "missing_disclaimer",
        message: "給与情報に目安表記または担当者確認の言及がない",
        severity: "medium",
      });
    }
  }

  // 3. 個人情報の過度な収集チェック
  const sensitiveQuestions = /マイナンバー|銀行口座|戸籍|病歴/;
  if (sensitiveQuestions.test(response.reply)) {
    violations.push({
      type: "sensitive_data_request",
      severity: "critical",
    });
  }

  return {
    valid: violations.filter(v => v.severity === "critical").length === 0,
    violations,
    sanitized: violations.length > 0 ? sanitizeResponse(response, violations) : response,
  };
}

function sanitizeResponse(response, violations) {
  let sanitized = { ...response };

  for (const v of violations) {
    if (v.severity === "critical") {
      // 重大な違反は安全な応答に差し替え
      sanitized.reply = "申し訳ございません。その点については、専門エージェントが直接ご説明いたします。他にご質問はありますか？";
    } else if (v.type === "missing_disclaimer") {
      // 免責表現を追加
      sanitized.reply += "\n\n※上記は目安です。詳細な条件は担当エージェントが確認いたします。";
    }
  }

  return sanitized;
}
```

### 5.3 プライバシー安全な会話処理

```javascript
// データ保存時のPII（個人識別情報）マスキング

function maskPIIForStorage(messages) {
  return messages.map(msg => ({
    ...msg,
    content: msg.role === "user"
      ? maskSensitiveData(msg.content)
      : msg.content,
  }));
}

function maskSensitiveData(text) {
  return text
    .replace(/\d{2,4}-\d{2,4}-\d{3,4}/g, "[電話番号]")     // 電話番号
    .replace(/[\w.-]+@[\w.-]+\.\w+/g, "[メール]")            // メールアドレス
    .replace(/\d{3}-\d{4}/g, "[郵便番号]")                    // 郵便番号
    // 氏名は文脈依存のため、会話ログ保存時のみマスク
    ;
}
```

### 5.4 AIフォールバック戦略

```javascript
// AIが利用不可の場合のフォールバック

async function handleChatWithFallback(request, env) {
  try {
    // 1. まずClaude APIを試行
    return await handleChat(request, env);
  } catch (apiError) {
    console.error("[Chat] Claude API error:", apiError);

    // 2. リトライ（最大2回、指数バックオフ）
    for (let i = 0; i < 2; i++) {
      await sleep(1000 * Math.pow(2, i));
      try {
        return await handleChat(request, env);
      } catch (retryError) {
        console.error(`[Chat] Retry ${i + 1} failed:`, retryError);
      }
    }

    // 3. フォールバック: 簡易応答モード
    return jsonResponse({
      reply: "申し訳ございません。現在AIアシスタントに一時的な問題が発生しています。" +
             "お手数ですが、下記のフォームからご登録いただければ、" +
             "専門エージェントが24時間以内にご連絡いたします。",
      step: null,
      score: null,
      done: false,
      fallback: true,  // クライアント側でフォーム誘導UIを表示
    });
  }
}
```

---

## 6. リクルーターダッシュボード強化

### 6.1 Slack通知の強化

```javascript
// AI生成の候補者サマリー付きSlack通知

async function sendEnhancedSlackNotification(sessionData, env) {
  const { profile, score, summary, messages, conversationDuration } = sessionData;

  const urgencyEmoji = { A: "\uD83D\uDD34", B: "\uD83D\uDFE1", C: "\uD83D\uDFE2", D: "\u26AA" };
  const channelNotify = score === "A" ? "<!channel> " : "";

  // マッチング結果も含める
  const matchResults = sessionData.matchResults || [];
  const topMatch = matchResults[0];

  const slackMessage = {
    blocks: [
      {
        type: "header",
        text: {
          type: "plain_text",
          text: `${urgencyEmoji[score] || "\u26AA"} AIチャット完了 - 温度感 ${score || "未判定"}`,
        },
      },
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: `${channelNotify}*候補者サマリー*\n${summary || "サマリーなし"}`,
        },
      },
      {
        type: "section",
        fields: [
          {
            type: "mrkdwn",
            text: `*転職理由*\n${profile?.transferReason || "未取得"}`,
          },
          {
            type: "mrkdwn",
            text: `*経験*\n${profile?.currentFacility || "未取得"}`,
          },
          {
            type: "mrkdwn",
            text: `*希望給与*\n${formatSalary(profile?.desiredSalary) || "未取得"}`,
          },
          {
            type: "mrkdwn",
            text: `*夜勤*\n${profile?.nightShiftPreference || "未取得"}`,
          },
          {
            type: "mrkdwn",
            text: `*通勤*\n${profile?.maxCommuteTime ? profile.maxCommuteTime + "分以内" : "未取得"}`,
          },
          {
            type: "mrkdwn",
            text: `*会話時間*\n${conversationDuration || "不明"}`,
          },
        ],
      },
      // マッチング結果セクション
      ...(topMatch ? [{
        type: "section",
        text: {
          type: "mrkdwn",
          text: `*推奨マッチング*\n:hospital: ${topMatch.displayName}（適合度 ${topMatch.totalScore}%）`,
        },
      }] : []),
      {
        type: "section",
        text: {
          type: "mrkdwn",
          text: "*要対応*\n" +
            ":white_square: 24時間以内に架電\n" +
            ":white_square: 希望条件に合う求人確認\n" +
            ":white_square: 面接日程調整",
        },
      },
      {
        type: "context",
        elements: [
          {
            type: "mrkdwn",
            text: `メッセージ数: ${messages?.length || 0} | 完了日時: ${new Date().toLocaleString("ja-JP")}`,
          },
        ],
      },
    ],
  };

  await fetchWithRetry(env.SLACK_WEBHOOK_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(slackMessage),
  });
}
```

### 6.2 構造化データ抽出

```javascript
// 会話完了時にAIが生成する構造化サマリー

const SUMMARY_EXTRACTION_PROMPT = `
以下の会話履歴から、リクルーター向けの構造化データを抽出してください。

出力JSON形式:
{
  "candidateSummary": "1-2文の候補者要約",
  "profile": {
    "transferReason": "転職理由",
    "currentPosition": "現在のポジション",
    "experience": "経験年数・専門",
    "keyStrengths": ["強み1", "強み2"],
    "concerns": ["懸念事項1"]
  },
  "conditions": {
    "salary": "希望給与",
    "workStyle": "勤務形態",
    "nightShift": "夜勤可否",
    "commute": "通勤条件",
    "holidays": "休日希望",
    "otherRequirements": ["その他条件"]
  },
  "matchingNotes": "マッチングの際に考慮すべき特記事項",
  "followUpActions": ["フォローアップアクション1", "アクション2"],
  "urgencyAssessment": {
    "score": "A/B/C/D",
    "rationale": "判定根拠"
  }
}
`;
```

### 6.3 Google Sheets連携の拡張

```javascript
// チャットデータもGoogle Sheetsに記録

async function saveToSheetsFromChat(sessionData, env) {
  const { profile, score, summary, matchResults } = sessionData;
  const topMatch = matchResults?.[0];

  const values = [[
    new Date().toLocaleString("ja-JP"),          // 登録日時
    "AIチャット",                                  // 登録経路
    profile?.transferReason || "",                 // 転職理由
    profile?.currentFacility || "",                // 現職
    profile?.yearsOfExperience || "",              // 経験年数
    formatSalary(profile?.desiredSalary),          // 希望給与
    profile?.nightShiftPreference || "",           // 夜勤
    profile?.maxCommuteTime ? `${profile.maxCommuteTime}分` : "",  // 通勤
    topMatch?.displayName || "",                   // 推奨病院
    topMatch?.totalScore ? `${topMatch.totalScore}%` : "",  // 適合度
    score || "",                                   // 温度感
    summary || "",                                 // サマリー
    "",                                            // 担当者
    "",                                            // メモ
  ]];

  // 既存の sendToSheets ロジックを流用
  await appendToSheet("AIチャット台帳", values, env);
}
```

---

## 7. 実装ロードマップ

### Phase 2a: Claude API接続（デモモード置換）

**目標:** 固定レスポンスをリアルClaude API応答に置換

**期間:** 1-2週間

**タスク:**

| # | タスク | ファイル | 詳細 |
|---|--------|----------|------|
| 1 | Workers チャットエンドポイント追加 | `api/worker.js` | `/api/chat` ルート追加、Claude API呼び出し |
| 2 | システムプロンプトをサーバー側に移動 | `api/worker.js` | クライアントの `SYSTEM_PROMPT` をサーバーで管理 |
| 3 | chat.js のAPI呼び出し改修 | `chat.js` | `callAPI()` を新エンドポイントに接続 |
| 4 | レスポンス検証フィルタ | `api/worker.js` | 禁止表現チェック・免責表現追加 |
| 5 | フォールバック実装 | `chat.js`, `api/worker.js` | API障害時のデモモード切り替え |
| 6 | config.js に workerEndpoint 設定 | `config.js` | 実際のWorkers URLを設定 |
| 7 | チャットレート制限追加 | `api/worker.js` | 既存のレート制限ロジックを流用 |

**変更点（chat.js）:**

```javascript
// 変更前: SYSTEM_PROMPT をクライアントに持つ
const SYSTEM_PROMPT = `あなたは...`;

// 変更後: システムプロンプトはサーバー側で管理
// chat.js からは SYSTEM_PROMPT を削除
// callAPI() は messages のみを送信

async function callAPI(messages) {
  try {
    const response = await fetch(CHAT_CONFIG.workerEndpoint + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: messages,
        sessionId: chatState.sessionId,  // 新規追加
      }),
    });
    // ...
  } catch (err) {
    // フォールバック: デモモードに切り替え
    return getDemoResponse();
  }
}
```

### Phase 2b: スマートマッチング（プロファイリング統合）

**目標:** 会話から看護師プロファイルを抽出し、最適な病院を提案

**期間:** 2-3週間

**タスク:**

| # | タスク | 詳細 |
|---|--------|------|
| 1 | プロファイリング用プロンプト拡張 | profile フィールドの抽出指示追加 |
| 2 | 病院データベース構築 | Cloudflare D1 or KV に病院詳細データ格納 |
| 3 | マッチングスコアリング実装 | `calculateMatchScore()` をWorker内に実装 |
| 4 | Step 4 動的プロンプト注入 | マッチング結果をAIの文脈に注入 |
| 5 | プロファイル蓄積・保存 | セッション内プロファイルデータの永続化 |
| 6 | Slack通知拡張 | Block Kit形式でリッチ通知 |
| 7 | chat.js プロファイル表示 | ステップ進行に応じたUI拡張 |

### Phase 2c: リクルーターツール＆分析

**目標:** リクルーターの業務効率化、データ駆動の意思決定

**期間:** 3-4週間

**タスク:**

| # | タスク | 詳細 |
|---|--------|------|
| 1 | 構造化サマリー自動生成 | 会話完了時にAIが構造化データ抽出 |
| 2 | ストリーミングレスポンス | SSE対応でリアルタイム応答表示 |
| 3 | Google Sheets チャット台帳 | チャットデータの自動記録 |
| 4 | 分析ダッシュボード基盤 | 会話数・スコア分布・変換率の可視化 |
| 5 | A/Bテスト基盤 | プロンプトバリエーションの効果測定 |
| 6 | 月次コストレポート | API使用量・コスト自動レポート |

---

## 付録

### A. 技術スタック

| レイヤー | 技術 | 用途 |
|----------|------|------|
| フロントエンド | Vanilla JS (chat.js) | チャットUI |
| APIプロキシ | Cloudflare Workers | APIキー保護、リクエスト処理 |
| AI | Claude Sonnet 4.5 (API) | 会話応答、プロファイリング |
| データ永続化 | Cloudflare KV / D1 | セッション、病院データ |
| 通知 | Slack Incoming Webhooks | リクルーター通知 |
| データ記録 | Google Sheets API | 候補者台帳 |

### B. 環境変数一覧

```
# Cloudflare Workers Secrets（wrangler secret put で設定）
ANTHROPIC_API_KEY=sk-ant-...           # Claude APIキー
SLACK_WEBHOOK_URL=https://hooks...      # 既存
GOOGLE_SHEETS_ID=1abc...                # 既存
GOOGLE_SERVICE_ACCOUNT_JSON={...}       # 既存
ALLOWED_ORIGIN=https://robby-the-match.com  # 既存
SESSION_ENCRYPTION_KEY=...              # セッション暗号化キー（新規）

# Cloudflare Workers KV Namespaces
SESSIONS_KV=...                         # セッションストア
HOSPITALS_KV=...                        # 病院データキャッシュ

# config.js（クライアント側）
API.workerEndpoint=https://robby-the-match-api.xxx.workers.dev
```

### C. API仕様サマリー

| エンドポイント | メソッド | 用途 | Phase |
|----------------|----------|------|-------|
| `/api/health` | GET | ヘルスチェック | 既存 |
| `/api/register` | POST | フォーム登録 | 既存 |
| `/api/chat` | POST | チャットメッセージ | 2a |
| `/api/chat/stream` | POST | ストリーミングチャット | 2c |
| `/api/notify` | POST | Slack通知 | 2a（拡張） |

### D. コスト試算

| 項目 | 単価 | 月間想定量 | 月額 |
|------|------|------------|------|
| Claude Sonnet 4.5 入力 | $3/MTok | 1.5M tok | $4.50 |
| Claude Sonnet 4.5 出力 | $15/MTok | 0.75M tok | $11.25 |
| Cloudflare Workers | 無料枠内 | 100K req | $0 |
| Cloudflare KV | 無料枠内 | 10K reads | $0 |
| **合計** | | | **約$16/月** |

※月間500会話想定。実際の利用量に応じて変動

### E. セキュリティチェックリスト

- [ ] APIキーがクライアントコードに含まれていないことを確認
- [ ] CORS設定が本番ドメインのみを許可
- [ ] レート制限が適切に機能
- [ ] AIレスポンスのバリデーションフィルタが稼働
- [ ] 個人情報の暗号化保存
- [ ] ログに個人情報が出力されないことを確認
- [ ] 月間コストアラートの設定
- [ ] フォールバック動作の確認

---

**作成:** AI Architecture Agent
**最終更新:** 2026-02-16
