# 管理ダッシュボード v0 設計書（レビュー用ドラフト）

> 2026-04-28 起案 / レビュー後 v1 として確定
> 起案: Claude / レビュー: 3エージェント並列

## 1. 目的

社長が**スマホで看護師の状況を一覧 → 必要な時だけ自分で返信**できるようにする。
LINE公式アプリ（chat.line.biz）の代替。

## 2. 要件

### 機能要件
- F1: 今日の状況サマリ（友だち追加/AI相談中/応募意思表明/緊急）
- F2: 会話一覧（タイムライン、状態アイコン、最終活動順）
- F3: ユーザー詳細（プロフィール+会話履歴+キャリアシート）
- F4: BOT ON/OFF切替（個別ユーザー）
- F5: 返信送信（直接LINE Push）
- F6: 監査ログ閲覧（全admin操作の履歴）

### 非機能要件
- N1: スマホファースト（PWA対応）
- N2: 認証3層（HMAC + IP + Basic）
- N3: 全admin操作は監査ログに記録（**改竄不可・追記専用**）
- N4: 応答時間 < 2秒（KVから直接読み取り）
- N5: 同時接続1名（社長のみ）

## 3. データモデル

### 既存KV（読み取りのみ）
| キー | 内容 |
|------|------|
| `line:${userId}` | エントリ全体（phase, messages, aica系, profile） |
| `member:${userId}` | 登録会員 |
| `member:${userId}:career_sheet` | AIキャリアシート |
| `handoff:${userId}` | ハンドオフ状態 |

### 新規KV（書き込みあり）
| キー | 内容 | TTL |
|------|------|-----|
| `admin:bot_off:${userId}` | BOT停止フラグ（存在=停止） | 30日 |
| `admin:audit:${ts}:${random}` | 監査ログエントリ | 90日 |
| `admin:session:${token}` | 管理者セッション | 12時間 |

### 監査ログのスキーマ
```json
{
  "ts": 1698765432000,
  "actor": "admin",
  "ip": "1.2.3.4",
  "action": "reply_sent",
  "target": "U3dac5c67f5cbaa77a580cc377b77f93e",
  "payload": { "messageHash": "sha256...", "messageLen": 42 },
  "result": "ok"
}
```
- `messageHash` のみ記録（本文は記録しない、PII保護）
- `payload`は actionごとに最小限

## 4. API仕様

ベースパス: `/api/admin/`
全エンドポイント: 認証必須（`Authorization: Bearer <session-token>`）

### POST /api/admin/login
- body: `{ password: string }`
- env.ADMIN_PASSWORD と比較
- 成功 → セッショントークン発行 → `admin:session:${token}` に12h保存
- IP + User-Agent も記録

### GET /api/admin/dashboard
- 今日のメトリクス
- response: `{ today: {newFollowers, aiConsulting, applyIntent, emergency}, recentActions: [...] }`

### GET /api/admin/conversations?limit=50&phase=...
- LINE_SESSIONS の `line:` プレフィックスを全件list
- updatedAt降順
- response: `{ items: [{userId, displayName, phase, lastMessage, updatedAt, status}] }`

### GET /api/admin/user/:userId
- entry + member + careerSheet を統合返却
- 直近20メッセージのみ（既存の messages 上限）
- response: `{ entry, member, careerSheet, botEnabled }`

### POST /api/admin/user/:userId/bot-toggle
- body: `{ enabled: boolean, reason?: string }`
- enabled=false → `admin:bot_off:${userId}` を put
- enabled=true → 削除
- 監査ログ: `bot_toggle`

### POST /api/admin/user/:userId/reply
- body: `{ text: string }`
- LINE Push API で送信
- entry.humanRepliedAt = now でBOT沈黙ガード起動
- 監査ログ: `reply_sent` + メッセージハッシュ
- 必須: textLength <= 5000

### GET /api/admin/audit-log?limit=100&action=...
- 監査ログ閲覧（読み取り専用）
- 自分自身も改竄不可（KVは追記のみ、削除APIなし）

### POST /api/admin/logout
- セッショントークン削除

## 5. 認証3層

### 層1: Basic Auth（Workerレベル）
- 全 `/api/admin/*` と `/admin/*` でチェック
- env.ADMIN_BASIC_USER / env.ADMIN_BASIC_PASS

### 層2: アプリレベル ログイン
- `/admin/login.html` でパスワード認証
- セッショントークン発行（crypto.randomUUID）
- KVに保存（12h TTL）
- LocalStorageに保存

### 層3: HMAC署名（書き込み系のみ）
- POST系リクエストは `X-Admin-Sig: HMAC-SHA256(env.ADMIN_HMAC_KEY, body+ts)`
- ts は `X-Admin-Ts` ヘッダ（5分以内）
- リプレイ攻撃防止

### Worker側の sensitive endpoint ガード
BOT本体（line-webhook）は `admin:bot_off:${userId}` をチェックし、存在すれば応答スキップ。

## 6. フロントエンド

### ファイル配置
- `/admin/index.html` — SPA本体（ログイン+全画面）
- `/admin/sw.js` — Service Worker（PWA）
- `/admin/manifest.json` — PWAマニフェスト
- 配信: GitHub Pages（auth は API側で実施）

### 画面遷移
```
[未ログイン]
  ↓ パスワード入力
[ダッシュボード]
  ├→ 会話一覧
  │    └→ ユーザー詳細
  │         ├→ BOT切替
  │         ├→ 返信
  │         └→ キャリアシート
  └→ 監査ログ
```

### 技術選定
- HTML/CSS/JS バニラ（ビルドステップなし）
- 約500行を1ファイルに集約
- ポーリング: 30秒間隔（会話一覧の更新）

## 7. セキュリティ脅威モデル

| 脅威 | 対策 |
|------|------|
| パスワード総当たり | 5回失敗で15分ロック（IPベース） |
| トークン盗難 | 12hで自動失効、ログアウトで即削除 |
| CSRF | HMAC署名で書き込みリクエスト保護 |
| 管理者なりすまし | IP + UA を監査ログに記録、異常時アラート |
| 看護師PII漏洩 | 監査ログに本文を記録しない（hashのみ） |
| 削除攻撃 | 監査ログKVは追記のみ、Worker側で削除APIを実装しない |
| BOT toggle悪用 | 全切替操作を監査ログ。理由必須 |

## 8. 品質ゲート（このゲートを全部PASSしないと完了不可）

### G1: セキュリティ
- [ ] 認証なしで `/api/admin/*` が叩けない（401返す）
- [ ] パスワード総当たり防御（5回失敗ロック）
- [ ] HMAC検証が動く（署名なしPOST→403）
- [ ] 監査ログKVに削除APIが存在しない

### G2: 機能
- [ ] ダッシュボード4指標が実データで表示
- [ ] 会話一覧が更新時刻順に並ぶ
- [ ] BOT OFFにすると本当にwebhookが応答しない（実LINEで確認）
- [ ] 返信が実際にLINEで届く（実ユーザーで確認）
- [ ] BOT再ONで通常応答に復帰

### G3: 監査ログ
- [ ] login/logout/bot_toggle/reply_sent が全部記録される
- [ ] 監査ログ閲覧で時系列に表示される
- [ ] 本文がハッシュ化されている（生メッセージなし）

### G4: UX
- [ ] スマホで読める（375px幅）
- [ ] PWAでホーム画面追加できる
- [ ] 返信送信から3秒以内にLINE到達

### G5: ログ完全性
- [ ] curlで全エンドポイント確認、ログ全公開
- [ ] 実ユーザー（社長自身）でE2Eテスト
- [ ] スクショ3枚以上（ダッシュボード/詳細/監査ログ）

## 9. 工数見積

- 設計レビュー: 30分（並列）
- Worker API実装: 90分
- フロントエンド実装: 90分
- コードレビュー: 30分
- デプロイ+E2Eテスト: 30分
- 品質ゲート再修正バッファ: 60分

**合計: 約5時間（5日見積から大幅短縮、ただし最小機能セット）**

## 10. レビュー観点（エージェント向け）

### Agent A: セキュリティ専門
- 認証3層は十分か？追加すべきか？
- HMAC実装は安全か？タイミング攻撃は？
- 監査ログの改竄防止は本当に効くか？
- KV TTL設定は適切か？

### Agent B: UX/データモデル
- entry構造（line:userId）の使い方は正しいか？
- 既存BOTフローを壊さないか？humanRepliedAt連携は？
- スマホUXとして実用に耐えるか？
- ポーリング30秒は妥当か？

### Agent C: 一気通貫の現実性
- 5時間で本当に終わるか？
- 工数見積の盲点は？
- 品質ゲートG1-G5は十分か？甘いところは？
- "ずる" の余地はないか？
