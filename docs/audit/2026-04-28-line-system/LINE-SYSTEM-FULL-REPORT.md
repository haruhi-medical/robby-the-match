# ナースロビー LINEシステム 全体レポート

**作成日**: 2026-04-28
**対象**: ナースロビー LINE Bot 全システム（Cloudflare Worker + Slack連携 + マイページ + LIFF + 自動化）
**ベース**: `api/worker.js` (12,915行) + `scripts/slack_*.py` + `mypage/` + `lp/job-seeker/liff.html`

---

## 0. 1ページサマリ（経営判断用）

| 項目 | 現状 |
|------|------|
| **本体** | Cloudflare Worker `robby-the-match-api` 単一バンドル（12,915行） |
| **状態保存** | KV `LINE_SESSIONS`（フェーズ・会話履歴・会員・気になる求人・waitlist・新着通知 全部） |
| **求人DB** | Cloudflare D1 `jobs` テーブル（毎朝06:30ハローワーク同期） |
| **施設DB** | Cloudflare D1 `facilities`（84,613件、47都道府県） |
| **人間返信窓口** | Slack `!reply` （worker→KV更新あり） / chat.line.biz （worker未経由・KV更新なし） |
| **ユーザー導線** | LP（quads-nurse.com）→LIFF→LINE公式 / 直接友だち追加 / Meta広告 / SNS |
| **重大リスク** | ①chat.line.biz経由の手動返信がKV更新しない（**Ayako事案根本原因**） ②エリア外ユーザーがhandoffに行かず`nurture_warm`に流れる ③`nurture_warm`/`nurture_subscribed`で自由テキスト送信→「読み取れません」誤発火 |
| **稼働中cron（Worker側）** | 新着求人Push / handoff SLA監視（2h・24h） / 失敗Push再送 |
| **稼働中cron（Mac側）** | ハローワーク取得（06:30） / ヘルスチェック / メタ広告レポート / Clarityレポート / SNS投稿 |

---

## 1. 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│ ユーザー導線                                                     │
│ ・LP(quads-nurse.com) ─診断─→ LIFF ─→ LINE公式                  │
│ ・直接 友だち追加（リッチメニュー or QR）                       │
│ ・Meta広告 ─→ /api/line-start ─→ LINE公式                       │
│ ・SNS（TikTok/Instagram）プロフィールリンク                     │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ LINE Messaging API (Webhook)                                     │
│  follow / message(text/sticker/image/loc) / postback / unfollow  │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ Cloudflare Worker `robby-the-match-api` (worker.js)             │
│ ┌────────────────────────────────────────────────────────────┐  │
│ │ ・署名検証（HMAC-SHA256）                                  │  │
│ │ ・Phase State Machine（30+ phase）                         │  │
│ │ ・自由テキスト解析 handleFreeTextInput                     │  │
│ │ ・マッチング generateLineMatching + scoreFacilities        │  │
│ │ ・ハンドオフ sendHandoffNotification                       │  │
│ │ ・AI相談 OpenAI→Claude→Gemini フォールバック              │  │
│ │ ・リッチメニュー switchRichMenu (4状態)                    │  │
│ │ ・Push linePushWithFallback（失敗キュー）                  │  │
│ │ ・スケジュール: 新着Push / handoff SLA / 再送              │  │
│ └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
       ↓ 通知                   ↓ KV/DB読み書き              ↓ Push
┌─────────────────┐  ┌─────────────────────────┐  ┌─────────────────┐
│ Slack           │  │ KV LINE_SESSIONS        │  │ LINE Push API   │
│ #ロビー小田原…   │  │ ・LINE entry            │  │ ・Reply         │
│ #claudecode     │  │ ・session: (LP)         │  │ ・Push          │
│                 │  │ ・liff:                 │  │ ・RichMenu link │
│ slack_commander │  │ ・member:               │  │                 │
│  → !reply検知   │  │ ・member:.*:resume      │  │                 │
│  → /api/line-   │  │ ・member:.*:favorites   │  │                 │
│    push 呼出    │  │ ・newjobs_notify:       │  │                 │
│                 │  │ ・waitlist:             │  │                 │
│ chat.line.biz   │  │ ・handoff:              │  │                 │
│  → 手動返信     │  │ ・failedPush:           │  │                 │
│  → KV更新なし   │  └─────────────────────────┘  └─────────────────┘
└─────────────────┘
                      ┌─────────────────────────┐
                      │ Cloudflare D1            │
                      │ ・jobs (求人21,149件)   │
                      │ ・facilities (84,613件) │
                      │ ・confidential_jobs     │
                      │ ・phase_transitions     │
                      └─────────────────────────┘
```

---

## 2. LINE Webhook受信処理

### 2.1 イベントタイプ別

| イベント | 行 | 処理概要 |
|---------|---|---------|
| `follow` | worker.js:8131-8358 | KV作成/復元、リッチメニュー設定、newjobs_notify自動optin、Slack通知 |
| `message` (text) | worker.js:9329-10087 | UUID検出→セッション復元、handleFreeTextInput、フォールバック段階制 |
| `message` (非テキスト) | worker.js:10107以降 | スタンプ=Quick Reply再表示、画像/動画/位置=Slack転送＋誘導 |
| `postback` | worker.js:8384-9328 | data文字列パース、handleLinePostback呼出 |
| `unfollow` | worker.js:8362-8381 | 4つのKV削除（nurture / newjobs_notify / waitlist / handoff）+ Slack通知 |
| `accountLink` `memberJoined` 等 | — | 未実装 |

### 2.2 follow時の自動処理

1. **再フォロー判定**：既存entryあれば`phase="welcome"`にリセット
2. **セッション復元（2段階）**：
   - LIFF経由 → KV `liff:{userId}` から復元
   - dm_text経由 → 同POST内のmessage eventからUUID抽出 → KV `session:{uuid}` 復元
3. **リッチメニュー**：`RICH_MENU_STATES.default` 設定
4. **newjobs_notify自動optin**（**opt-out設計** — ユーザーが明示停止しない限り全員登録）
5. **Slack通知**：名前・一言・流入元 → `#ロビー小田原人材紹介`

---

## 3. フェーズステートマシン（30+phase）

### 3.1 PHASE_GROUPS定義（worker.js:262-280）

```js
ONBOARDING:   ["welcome"]
INTAKE:       ["il_area", "il_subarea", "il_facility_type", "il_department",
               "il_workstyle", "il_urgency"]
MATCHING:     ["matching_preview", "matching_browse", "matching", "condition_change"]
AI_CONSULT:   ["ai_consultation_waiting", "ai_consultation_reply",
               "ai_consultation_extend"]
INFO_DETOUR:  ["info_detour"]
APPLY:        ["apply_info", "apply_consent", "apply_confirm"]
INTERVIEW:    ["interview_prep"]
HANDOFF:      ["handoff", "handoff_silent", "handoff_phone_check",
               "handoff_phone_time", "handoff_phone_number"]
NURTURE:      ["nurture_warm", "nurture_subscribed", "nurture_stay",
               "area_notify_optin"]
FAQ:          ["faq_salary", "faq_nightshift", "faq_timing",
               "faq_stealth", "faq_holiday"]
```

### 3.2 Intake Lightフロー（メイン導線）

```
welcome
  ↓
il_area  （都道府県: tokyo/kanagawa/chiba/saitama/other）
  ↓
il_subarea  （細分化: yokohama_kawasaki, shonan_kamakura...）
  ↓
il_facility_type  （急性期/回復期/慢性期/クリニック/訪問/介護）
  ├─ 病院系 → il_department（診療科）→ il_workstyle
  └─ その他 → il_workstyle
  ↓
il_workstyle  （日勤/二交代/夜勤専従/パート）
  ↓
il_urgency  （urgent/good/info）
  ↓
[generateLineMatching実行]
matching_preview  （Flexカルーセル5件 + Quick Reply）
  ├─ more → matching_browse（次5件）
  ├─ detail → matching（個別詳細）
  ├─ deep → ai_consultation
  ├─ change → condition_change
  └─ later → nurture_warm
```

**各フェーズで何が保存されるか**（KV `entry`オブジェクト）

| フェーズ | 入力種別 | 保存先 |
|---------|---------|-------|
| il_area | postback `il_pref=` | `entry.prefecture` |
| il_subarea | postback `il_area=` | `entry.area` (e.g. "yokohama_kawasaki_il") |
| il_facility_type | postback `il_ft=` | `entry.facilityType`, `entry.hospitalSubType` |
| il_department | postback `il_dept=` | `entry.department` |
| il_workstyle | postback `il_ws=` | `entry.workStyle` (day/twoshift/night/part) |
| il_urgency | postback `il_urg=` | `entry.urgency` (urgent/good/info) |

### 3.3 マッチングロジック（generateLineMatching: worker.js:6457-6750）

**5段階の検索フォールバック:**

1. D1 `jobs` SQL検索（エリア+働き方+診療科でフィルタ、score DESC、LIMIT 15）
2. 0件 → `EXTERNAL_JOBS[profession][areaKey]` フォールバック
3. 0件 → 隣接エリア自動拡大
4. 同一事業所重複制限（最大2件）
5. 上位5件を `entry.matchingResults` に保存

**スコアリング（scoreFacilities: worker.js:1260-1450）:**

| 項目 | 加点 | 条件 |
|------|------|------|
| 除外タイプ | -50 | preferences.excludeTypes一致 |
| 夜勤なし希望×日勤施設 | +25 | 一致 |
| 施設タイプ一致 | +15 | preferences.facilityTypes |
| 給与マッチ | +15 | salaryMax >= preferences.salaryMin |
| 教育体制 | +5〜+20 | educationLevel === "充実" |
| 救急レベル | +5〜+10 | emergencyLevel >= 2 |
| 看護配置 | +5 | "7:1"基準 |
| 休日数 | +5〜+10 | annualHolidays >= 120 |

**ランク判定:**
- score >= 5 → A
- score >= 3 → B
- score >= 1 → C
- それ以下 → D（15件以上時除外）

---

## 4. 自由テキスト処理（handleFreeTextInput: worker.js:7822-8053）

### 4.1 優先度順処理

| 優先度 | パターン | 処理 |
|--------|---------|------|
| 1 | `/^(.{1,30})について相談したい$/` | `entry.interestedFacility` 保存 → `handoff_phone_check` |
| 2 | 履歴書入力フェーズ（rm_cv_q3/q5/q6/q8） | 文字数検証 → 次フェーズ |
| 3 | reverse_nomination_input | 2-80文字検証 → `handoff_phone_check` |
| 4 | handoff_phone_number | `/^0[0-9]{9,10}$/` 検証 → `handoff` |
| 5 | il_area/il_subarea/welcome | 都市名/都道府県名検出（prefMap/cityMap） |
| 6 | apply_info | 氏名2文字以上検証 → `apply_consent` |
| 7 | その他フェーズ | nullを返す → unexpectedTextCountインクリメント |

### 4.2 unexpectedTextCount 段階制（worker.js:10003-10038）

```
unexpectedTextCount === 1 → 「すみません、うまく読み取れませんでした。下のボタンから…」+ 現フェーズQR
unexpectedTextCount === 2 → 「うまくいかないですよね、すみません」+ フォールバック3択
unexpectedTextCount === 3 → 強制 handoff へ + Slack通知
```

### 4.3 nullを返す（=「読み取れません」発火）条件

- `apply_consent`/`apply_confirm`/`interview_prep` で自由テキスト
- `matching` で自由テキスト（preview/browseはAI相談へ）
- `handoff` で自由テキスト → `handoff_silent`
- intake_light（il_*）フェーズで postback以外のテキスト
- **nurture_warm/nurture_subscribed フェーズ全般**（Ayako事案の発火点）

---

## 5. リッチメニューシステム

### 5.1 v3画像（2026-04-23デプロイ）

- ファイル: `assets/richmenu/richmenu_v3_20260423.png` (2500×1686, 753KB)
- richMenuId: `richmenu-51903fc26a2da8f99bb7ae769c285b35`
- 5タイル:
  1. 大バナー(1648×884) **お仕事探しをスタート** → postback `rm=start`
  2. 小バナー(852×884) **本日の新着求人** → postback `rm=new_jobs`
  3. タイル(832×802) **マイページ** → postback `rm=mypage`
  4. タイル(809×802) **担当に相談する** → postback `rm=contact`
  5. タイル(859×802) **履歴書作成** → postback `rm=resume`

### 5.2 4状態切り替え

```
RICH_MENU_STATES = {
  default:  RICH_MENU_DEFAULT,    // welcome
  hearing:  RICH_MENU_HEARING,    // intake_light/AI相談中
  matched:  RICH_MENU_MATCHED,    // マッチング後〜apply_*
  handoff:  RICH_MENU_HANDOFF,    // 担当者対応中
}
```

`getMenuStateForPhase(phase)` で自動判定 → `switchRichMenu(userId, state, env)` で切替。

**注**: `hearing/matched/handoff` の専用画像は未作成。当面 `default` 流用。

### 5.3 登録手順（scripts/richmenu_register.py）

```bash
# Step1: 既存メニュー一覧
# Step2: 新規作成（JSON定義）→ richMenuId取得
# Step3: 画像アップロード
# Step4: デフォルト設定
# Step5: ID出力 → wrangler secret put RICH_MENU_DEFAULT
```

---

## 6. ハンドオフシステム（最重要）

### 6.1 発火条件

**自動トリガー:**
| トリガー | 行 |
|---------|---|
| `entry.urgency === "urgent"` | il_urgency選択時 |
| 緊急キーワード8語検出 | worker.js:9578-9614 |
| `messageCount >= 5` | worker.js:7079 |
| `unexpectedTextCount >= 3` | worker.js:10003-10010 |
| 求人詳細タップ | postback `match=detail` |
| 逆指名 | reverse_nomination_input |
| 「○○について相談したい」 | worker.js:7825-7841 |
| 「担当者に相談」postback | rm=contact |

### 6.2 サブフェーズ

| サブフェーズ | 役割 |
|-------------|------|
| `handoff_phone_check` | LINE only / 電話OK 二択 |
| `handoff_phone_time` | 電話可能時間帯（午前/午後/夜/週末） |
| `handoff_phone_number` | 電話番号入力（`/^0[0-9]{9,10}$/`） |
| `handoff` | 最終確認（「24時間以内に担当からLINE」） |
| `handoff_silent` | LINE応答せずSlack転送のみ（既ハンドオフ後） |

### 6.3 sendHandoffNotification（worker.js:7032-7163）

**Slack通知に含まれる情報:**
- 温度感（🔴A/🟡B/🟢C）
- 連絡方法（LINEのみ/電話OK）+ 希望時間帯 + マスク済電話番号
- ハンドオフ理由（複数列挙）
- 求職者サマリー（資格/経験年数/現職場/転職理由/不安）
- 希望条件（エリア/働き方/得意なこと）
- 直近5件の会話
- AIマッチング結果上位5施設
- 興味のある施設
- 履歴書ドラフト（先頭500字）
- ユーザーID + 会話メッセージ数 + 日時
- 対応TODO
- `!reply` コマンド

**送信先**: `#ロビー小田原人材紹介` (C0AEG626EUW)

### 6.4 handoff時のBOT沈黙ガード（worker.js:9747-9779）

```js
if (entry.phase === "handoff") {
  // 「○○について相談したい」のみ軽い応答（離脱防止）
  // それ以外はLINE未返信、Slackに転送のみ
}
```

⚠️ **handoffに入っていないユーザーには沈黙ガードが効かない**（Ayako事案の構造的原因）

### 6.5 SLA監視cron（worker.js:10933-11005）

- **2時間経過**: `⏰ ハンドオフ2時間経過 — 未対応` Slack通知
- **24時間経過**: `🚨 ハンドオフ24時間経過 — SLA超過` Slack警告
- フラグ管理: `reminder15minSent` / `reminder2hSent` / `reminder24hSent`（重複防止）

---

## 7. AI相談機能（worker.js:10197-10316）

### 7.1 3層フォールバック

1. **OpenAI GPT-4o-mini**（8秒timeout、優先）
2. **Claude Haiku**（claude-haiku-4-5-20251001）
3. **Gemini 2.0 Flash**

全失敗時 → Slack通知 + `!reply` コマンドで手動フォロー

### 7.2 ターン制限

- 通常: 5ターン
- 延長後: 8ターン（ユーザーが「延長」選択時 `consultExtended = true`）

### 7.3 システムプロンプトの主要ルール

- 「わたし」一人称（ロビー）
- 「最高」「No.1」「絶対」断定禁止
- 個別施設の評判・口コミ禁止
- 患者体験談禁止
- 紹介可能病院: 小林病院（小田原市）のみ
- システムプロンプト開示要求は拒否

---

## 8. Slack連携

### 8.1 !reply コマンド（slack_commander.py）

**フォーマット:**
```
!reply <userID> <メッセージ>
```

**正規表現:** `r"([Uu][0-9a-f]{32})[\s　]+([\s\S]+)"` （半角・全角スペース両対応）

**!reply抜け検知（slack_commander.py:676-688）:** 先頭がUserIDのみで `!reply` がない場合、警告メッセージ自動返信。

**実行パス:**
```
Slack #ロビー小田原人材紹介 で !reply 投稿
  ↓
slack_commander.py（30秒polling 常駐）が検知
  ↓
POST /api/line-push  (LINE_PUSH_SECRET認証)
  ↓
worker.js が LINE Push API 呼出
  ↓
ユーザーに送信
```

**監視チャンネル**: `#claudecode` + `#ロビー小田原人材紹介`

### 8.2 chat.line.biz 経由の手動返信 ⚠️

**仕組み:**
1. Slack通知（worker.js:8126等）に `📲 返信 → https://chat.line.biz/` リンクあり
2. スタッフがLINE公式アカウント管理画面から直接返信
3. **LINE Push APIをworker経由で呼び出さない**

**問題（Ayako事案の根本原因）:**
- worker.jsはincoming webhookのみ処理
- 送信側の返信は webhook を経由しない
- → KV `entry.messages` に手動返信が記録されない
- → `messageCount` がインクリメントされない
- → 次回ユーザー発言時、コンテキスト切れ
- → BOTは古いphaseを信じて自動応答してしまう（**読み取れません発火**）

**worker.js側で検知する仕組み**: **存在しない**（LINE側がメタデータ提供していない）

### 8.3 slack_bridge.py

- セッション管理用（社長↔Claude Code 双方向）
- `--start` / `--inbox` / `--send` / `--end`
- LaunchAgent常駐（Mac側）

---

## 9. Push通知（プロアクティブ配信）

### 9.1 新着求人通知（newjobs_notify）

- **対象**: KV `newjobs_notify:{userId}` 登録済（friendsの大半）
- **配信時刻**: 毎朝10時JST（cron `0 1 * * *` UTC）
- **配信内容**: エリア別「本日初出」のS/A/Bランク求人 最大3件
- **0件時**: 何も送らない（うざくしない設計）
- **エリア優先順**: 最後のユーザー選択を優先（LP→郵便番号→「エリアを変える」→新着エリア選択全て上書き）

### 9.2 waitlist Push（管理API）

- **エンドポイント**: `POST /api/admin/trigger-waitlist-push`
- **secret必須** + **fallbackDays optional**
- **対象**: KV `waitlist:{userId}` 登録済（エリア外通知希望者）
- **完了通知**: `🌏 waitlist Push 配信完了` を Slackへ

### 9.3 linePushWithFallback（worker.js:3308-3375）

```
Push試行 (api.line.me/v2/bot/message/push)
  ├─ 成功 → ログ出力
  ├─ 400/403 (ブロック) → 再送スキップ（不可逆）
  └─ その他エラー
       ├─ KV `failedPush:{userId}:{ts}` に1時間TTLで保存
       │    値: {userId, messages, tag, attempts, lastError, lastStatus}
       ├─ Slack通知（🚨 LINE Push失敗）
       └─ cron（30分毎）で拾って再送
            ├─ 成功 → KV削除
            └─ maxAttempts(3)超過 → Slack通知 + 削除
```

---

## 10. 会員制マイページ

### 10.1 構成

| ファイル | 役割 |
|---------|------|
| `mypage/index.html` | メインダッシュボード |
| `mypage/resume/index.html` | 履歴書表示 |
| `mypage/resume/edit.html` | 履歴書編集（学歴/職歴） |
| `mypage/preferences/index.html` | 希望条件 |
| `mypage/favorites/index.html` | 気になる求人 |
| `mypage/auth.html` | 認証失敗フォールバック |

### 10.2 HMAC認証（worker.js:11905-11957）

- **トークン形式**: `base64url(payload).base64url(HMAC-SHA256(payload, CHAT_SECRET_KEY))`
- **payload**: `{userId, exp: Date.now() + 24h}`
- **署名検証**: timingSafeEqual

### 10.3 会員判定

```js
const memberRaw = await env.LINE_SESSIONS.get(`member:${userId}`);
const m = JSON.parse(memberRaw);
isMember = m.status === "active" || m.status === "lite";
```

### 10.4 主要API

| エンドポイント | 機能 |
|--------------|------|
| `POST /api/mypage-init` | sessionToken発行 |
| `GET /api/mypage-resume` | 履歴書HTML取得 |
| `GET /api/mypage-resume-data` | 履歴書JSON取得 |
| `POST /api/mypage-resume-edit` | 履歴書更新 |
| `DELETE /api/mypage-resume-delete` | 履歴書削除 |
| `GET /api/mypage-preferences-get` | 希望条件取得 |
| `POST /api/mypage-preferences-save` | 希望条件保存 |
| `GET /api/mypage-favorites-get` | 気になる求人一覧 |
| `POST /api/mypage-favorites-add` | 追加 |
| `DELETE /api/mypage-favorites-delete` | 削除 |

### 10.5 リッチメニュー rm=mypage導線

```js
if (dataStr === "rm=mypage") {
  if (isMember) {
    const entryToken = await generateMypageSessionToken(userId, env);
    const url = `https://quads-nurse.com/mypage/?t=${entryToken}`;
  } else {
    const liteToken = crypto.randomUUID();
    const url = `https://quads-nurse.com/resume/member-lite/?token=${liteToken}`;
  }
}
```

---

## 11. LIFF（LINE Front-end Framework）

### 11.1 構成

- **LIFF ID**: `2009683996-7pCYfOP7`
- **ファイル**: `lp/job-seeker/liff.html`

### 11.2 セッション引き継ぎフロー

```
LP（Mini診断5問完了）
  ↓ answers + session_id + fbp/fbc
LIFF（liff.html）
  ↓ liff.init() → userId取得
  ↓ POST /api/link-session → KV `liff:{userId}` 保存
  ↓ liff.sendText() で要約テキスト送信
LINE公式（follow event）
  ↓ KV `liff:{userId}` から復元
  ↓ entry.area/answers/intent 引き継ぎ
  ↓ intake_lightスキップ → matching直行
```

### 11.3 関連API

- `handleLineStart` (worker.js:3448-3530): LP→Worker→LINE公式リダイレクト + CAPI Lead送信
- `handleLinkSession` (worker.js:3641-3720): LIFF bridge→KV保存

---

## 12. 履歴書ビルダー & キャリアシート

### 12.1 履歴書フェーズ進行

```
apply_info（氏名入力）
  → apply_consent（同意）
  → career_sheet（匿名プロフィール表示）
  → apply_confirm（最終確認）
  → interview_prep（面接対策）
```

### 12.2 履歴書KV

| キー | 内容 |
|------|------|
| `member:{userId}:resume` | 履歴書HTML（印刷用） |
| `member:{userId}:resume_data` | JSON（学歴/職歴配列） |

**resume_data例:**
```json
{
  "fullName": "...", "birthDate": "...", "phone": "...",
  "qualification": "正看護師", "experience": 10,
  "educations": [{period, school, note}],
  "careers": [{period, workplace, department}],
  "updatedAt": 1682000000000
}
```

### 12.3 匿名プロフィール（career_sheet）

`generateAnonymousProfile(entry)` (worker.js:4846-4899) — 静的Mustacheテンプレート。AIではない。

**含まれる項目:**
- 資格・経験年数
- 得意分野・スキル
- 転職理由
- 希望条件（エリア/働き方/重視事項）
- 懸念事項
- ナースロビー許可番号 23-ユ-302928

**含まれない**: 氏名、連絡先（意図的に非開示）

⚠️ **Note**: STATE.mdに記載のある「キャリアシート自動生成 Layer 1」「`/career-sheet/:serial`エンドポイント」「`POST /admin/career-sheet/generate` 管理API」「禁止語検出→リトライ→伏せ字マスク」は**現コードには存在しない**。Layer1機能は未デプロイorロールバックされている可能性大。要確認。

---

## 13. 「気になる求人」（旧お気に入り）

### 13.1 fav_add postbackハンドラ（worker.js:8501-8613）

**3段検索:**
1. `entry.matchingResults`
2. `entry.lastShownJobs`
3. D1 jobs SQL直引き（id一致）

**KV保存:**
- キー: `member:{userId}:favorites`
- 値: 配列（最大50件、FIFO）
- 各要素: `{jobId, savedAt, snapshot: {title, facility, area, salaryMin, salaryMax}}`

**非会員時**: 30分有効の `liteToken` 発行 → 会員登録誘導URL

---

## 14. cron / 自動化

### 14.1 Worker側cron（Cloudflare内蔵）

| ジョブ | 実装 | 頻度 |
|-------|------|------|
| 新着求人Push | handleScheduledNewJobsNotify (worker.js:10548) | 毎朝10時JST |
| handoff SLA監視 | handleScheduledHandoffFollowup (worker.js:10933) | 定期 |
| 失敗Push再送 | handleScheduledFailedPushRetry (worker.js:11007+) | 30分毎 |

### 14.2 Mac側cron（社長Mac Mini M4で稼働）

```
0  4 * * 1-6  pdca_seo_batch.sh           # SEO改善
0  6 * * 1-6  pdca_ai_marketing.sh        # AI日次PDCA
0  7 * * 1-6  pdca_healthcheck.sh         # 障害監視
30 7 * * 1-6  cron_carousel_render.sh     # カルーセル画像生成
0 10 * * 1-6  pdca_competitor.sh          # 競合分析
0 12 * * 1-6  instagram_engage.py
0 12,17,18,20,21 * * 1-6 pdca_sns_post.sh # SNS投稿
0 15 * * 1-6  pdca_content.sh             # コンテンツ生成
0 16 * * 1-6  pdca_quality_gate.sh        # 品質ゲート
0 19 * * 1-6  post_preview.py
30 19 * * 1-6 slack_reply_check.py
0  20 * * 1-6 slack_reply_check.py
30 20 * * 1-6 slack_reply_check.py
0 21 * * 1-6  cron_ig_post.sh             # Instagram投稿
0 23 * * 1-6  pdca_review.sh              # 日次レビュー
0  5 * * 0    pdca_weekly_content.sh      # 週次バッチ
0  6 * * 0    pdca_weekly.sh              # 週次総括
0  2 * * *    autoresearch
0  3 * * *    log_rotate.sh
30 6 * * *    pdca_hellowork.sh           # ハローワーク取得
0  8 * * *    meta_ads_report.py
5  8 * * *    ga4_report.py
*/30 * * * *  watchdog.py
```

### 14.3 pdca_hellowork.sh（毎朝06:30）

1. ハローワークAPI取得（47都道府県、看護師求人）
2. 差分分析 → Slack報告
3. ランク付け（hellowork_rank.py）
4. D1 `jobs` テーブル投入（hellowork_to_d1.py）
5. サイトHTML生成
6. git commit & push
7. Slack完了通知

---

## 15. 緊急時通知

### 15.1 EMERGENCY_KEYWORDS（8語）— 🚨即handoff

「死にたい」「自殺」「もう無理」「パワハラ」「いじめ」「セクハラ」「暴力」「被災」

→ `entry.phase = "handoff"` + ホットライン案内（よりそいホットライン 0120-279-338）+ Slack 🚨

### 15.2 URGENT_KEYWORDS（6語）— ⚠️ Slack通知のみ

「辞めたい」「退職したい」「今すぐ辞めたい」「明日から行けない」「体調崩した」「限界」

→ Slack ⚠️ 通知 + 会話継続

---

## 16. 構造的問題リスト（重大度順）

### 🔴 R1. chat.line.biz 経由の手動返信が KV を更新しない（Ayako事案根本原因）

**影響:**
- 人間がchat.line.bizから返信してもworker.js側でphase=handoffに切替わらない
- BOTは古いphaseを信じて自動応答 → 「読み取れません」誤発火 → ユーザー激怒・離脱

**現状の対策**: なし

**検討すべき修正方向:**
1. `!reply` を必須化し、chat.line.biz 使用禁止（運用ルール）
2. worker側で「人間が一度でも応答したら N時間 BOT沈黙」フラグ導入（KVに `humanRepliedAt`）
3. LINE Operator機能（β）を使ってStandby/Active切替制御 — 開発工数高

### 🔴 R2. エリア外ユーザーが handoff に行かず nurture_warm に流れる

**影響:** 大阪等で登録 → `area_notify_optin` → `nurture_warm` → 自由テキストで「読み取れません」

**現状の対策**: なし（4/26の全国対応で改善されたが、それ以前のKVは旧stateのまま）

**検討すべき修正方向:**
1. エリア外ユーザーは即 `handoff` に飛ばす（順番待ちなら `waitlist:` KV併用）
2. KVマイグレーションで旧 `nurture_warm` → 新 `handoff` 移行

### 🟡 R3. nurture_warm/nurture_subscribed フェーズで「読み取れません」が出る

**影響:** 既ナーチャリング中ユーザーが詳細メッセージを送ると不快応答

**現状の対策**: unexpectedTextCount=3でhandoffには行く（が3回も出させる時点でNG）

**検討すべき修正方向:**
1. nurture_*系はAI相談に誘導（matching_browseと同様）
2. 「読み取れません」を即「担当者に転送します」に置換

### 🟡 R4. キャリアシートLayer 1 機能の実装不一致

**影響:** STATE.md記載とコードが乖離。`/career-sheet/:serial` も `POST /admin/career-sheet/generate` も存在しない

**検討事項:** 
- ロールバックされたか、別ブランチに残っているか確認
- Phase 14（病院推薦文送付準備）も未実装

### 🟡 R5. リッチメニュー hearing/matched/handoff専用画像未作成

**影響:** 4状態切替実装済みだが、画像が default 流用

**検討事項:** 専用画像を作るか、4状態運用をやめるか

### 🟢 R6. 逆指名「24時間以内回答」のタイムトラッキング機構なし

**影響:** Slack通知のみ。経過時刻管理なし

### 🟢 R7. AI相談ターン延長UX

**影響:** 5ターン制限の説明が不十分

---

## 17. 主要ファイル / 関数マップ

### 17.1 ファイル構成

```
api/
├─ worker.js              ★12,915行 LINE Bot本体
├─ worker_facilities.js   施設DB配列（212施設）
├─ wrangler.toml          設定（KV/D1バインディング、cron）
└─ schema.sql             D1スキーマ

scripts/
├─ slack_commander.py     ★!reply検知・LINE送信
├─ slack_bridge.py        セッション管理（Claude Code↔Slack）
├─ slack_reply_check.py   投稿承認確認
├─ slack_report.py        日次/週次レポート
├─ richmenu_register.py   リッチメニュー登録
├─ test_line_flow.py      LINE Bot E2Eテスト
└─ test_member_resume.py  履歴書テスト

mypage/
├─ index.html             ダッシュボード
├─ resume/{index,edit}.html
├─ preferences/index.html
├─ favorites/index.html
├─ auth.html              認証フォールバック
├─ mypage.css
└─ mypage.js

lp/job-seeker/
└─ liff.html              LIFF bridge

assets/richmenu/
└─ richmenu_v3_20260423.png   リッチメニュー画像
```

### 17.2 worker.js 主要関数（行番号）

| 関数 | 役割 | 行 |
|------|------|---|
| `handleLineWebhook` | Webhook受信エントリ | 8055 |
| `handleFreeTextInput` | 自由テキスト解析 | 7822 |
| `handleLinePostback` | postback解析 | 7166 |
| `buildPhaseMessage` | フェーズ別メッセージ生成 | 4964 |
| `generateLineMatching` | マッチング生成 | 6457 |
| `scoreFacilities` | スコア計算 | 1260 |
| `buildMatchingMessages` | マッチング表示 | 6960 |
| `buildFacilityFlexBubble` | 求人カードFlex | 6857 |
| `sendHandoffNotification` | ハンドオフSlack通知 | 7032 |
| `handleLineAIConsultation` | AI相談 | 10197 |
| `linePushWithFallback` | Push失敗時フォールバック | 3308 |
| `switchRichMenu` | リッチメニュー切替 | 4575 |
| `getMenuStateForPhase` | フェーズ→メニュー判定 | 4559 |
| `handleLineStart` | LP→Worker入口 | 3448 |
| `handleLinkSession` | LIFF bridge | 3641 |
| `generateMypageSessionToken` | HMAC発行 | 11905 |
| `verifyMypageSessionToken` | HMAC検証 | 11920+ |
| `generateAnonymousProfile` | 匿名プロフィール | 4846 |
| `cleanExpiredWebSessions` | セッションGC | 3388 |
| `verifyLineSignature` | LINE署名検証 | 3247 |
| `lineReply` | Reply API | 3276 |

### 17.3 KVキー一覧

| プレフィックス | TTL | 用途 |
|--------------|-----|------|
| `line:{userId}` | なし | LINE entry本体（phase, history, profile, ...） |
| `session:{sessionId}` | 24h | LP診断セッション |
| `liff:{userId}` | なし | LIFF bridge引き継ぎ |
| `member:{userId}` | なし | 会員ステータス |
| `member:{userId}:resume` | なし | 履歴書HTML |
| `member:{userId}:resume_data` | なし | 履歴書JSON |
| `member:{userId}:favorites` | なし | 気になる求人（最大50） |
| `member:{userId}:preferences` | なし | 希望条件 |
| `newjobs_notify:{userId}` | なし | 新着求人配信登録（opt-out） |
| `waitlist:{userId}` | なし | エリア外順番待ち |
| `handoff:{userId}` | なし | ハンドオフセッション |
| `failedPush:{userId}:{ts}` | 1h | Push失敗キュー |
| `resume_token:{token}` | 30m | 非会員→履歴書誘導 |

---

## 18. 環境変数（Worker secrets）

必須（全て `.env` にも保存）:
- `LINE_CHANNEL_SECRET`
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_PUSH_SECRET`
- `SLACK_BOT_TOKEN`
- `SLACK_CHANNEL_ID` = `C0AEG626EUW`
- `OPENAI_API_KEY`
- `CHAT_SECRET_KEY` (HMAC署名用)
- `RICH_MENU_DEFAULT` / `RICH_MENU_HEARING` / `RICH_MENU_MATCHED` / `RICH_MENU_HANDOFF`
- `ANTHROPIC_API_KEY` (option / Claude Haiku fallback)
- `GOOGLE_AI_KEY` (option / Gemini fallback)
- `META_PIXEL_ID` `META_ACCESS_TOKEN` (CAPI用)

⚠️ **wrangler deployで全secretsが消えることがある** → デプロイ後 `wrangler secret list --config wrangler.toml` 必ず確認。

---

## 19. デプロイコマンド（絶対遵守）

```bash
cd api && unset CLOUDFLARE_API_TOKEN && npx wrangler deploy --config wrangler.toml
```

⚠️ `--config wrangler.toml` を**省略するな**（ルートのwrangler.jsoncが優先されて誤Workerにデプロイされる）

---

## 20. 既知のテスト

- `scripts/test_line_flow.py` — LINE Bot E2Eテスト
- `scripts/test_member_resume.py` — 履歴書テスト
- `scripts/test_richmenu_personas.py` — リッチメニュー7ペルソナ静的解析（14項目PASS）
- `scripts/test_mypage_full_e2e.py` — マイページE2E
- `scripts/test_mypage_token.py` — HMAC認証

---

**END OF REPORT**
