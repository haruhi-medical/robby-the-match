# ナースロビー AIキャリアアドバイザー

> 新規独立プロダクト。既存ナースロビー LINE Bot（@174cxnev）とは完全分離。
>
> 設計書: [`../docs/new-ai-career-advisor-spec.md`](../docs/new-ai-career-advisor-spec.md)

## プロジェクト構成

```
api-aica/
├── wrangler.toml         # Cloudflare Workers 設定
├── package.json
├── schema.sql            # D1 スキーマ
└── src/
    ├── index.js          # Worker エントリ（webhook + cron）
    ├── prompts.js        # AI プロンプト群（導入4ターン他）
    ├── state-machine.js  # 状態遷移
    ├── lib/
    │   ├── line.js       # LINE API クライアント
    │   ├── openai.js     # OpenAI + マルチプロバイダ フォールバック
    │   └── slack.js      # Slack 通知
    └── phases/
        └── intake.js     # 導入ヒアリング 4ターン実装
```

## セットアップ手順（デプロイ前）

### 1. LINE公式アカウント取得（社長手動）

1. https://manager.line.biz/ で新規作成
   - 名前: `ナースロビー【AIキャリアアドバイザー】`
   - 業種: 人材サービス > 人材紹介
2. https://developers.line.biz/console/ で Messaging API チャネル追加
3. 以下3点を取得:
   - Channel ID
   - Channel Secret
   - Channel Access Token (long-lived)

### 2. Cloudflare リソース作成

```bash
cd api-aica

# D1 データベース作成
npm run db:create
# → 出力された database_id を wrangler.toml の AICA_DB に貼る

# KV namespace 作成
npm run kv:create
# → 出力された id を wrangler.toml の AICA_SESSIONS に貼る

# スキーマ適用
npm run db:migrate
```

### 3. Secrets 設定

```bash
cd api-aica

# LINE (必須)
unset CLOUDFLARE_API_TOKEN
npx wrangler secret put LINE_CHANNEL_SECRET --config wrangler.toml
npx wrangler secret put LINE_CHANNEL_ACCESS_TOKEN --config wrangler.toml

# OpenAI (必須・既存流用可)
npx wrangler secret put OPENAI_API_KEY --config wrangler.toml

# Fallback AI (任意・既存流用推奨)
npx wrangler secret put ANTHROPIC_API_KEY --config wrangler.toml
npx wrangler secret put GEMINI_API_KEY --config wrangler.toml

# Slack (必須)
npx wrangler secret put SLACK_BOT_TOKEN --config wrangler.toml
npx wrangler secret put SLACK_CHANNEL_AICA --config wrangler.toml
npx wrangler secret put SLACK_CHANNEL_URGENT --config wrangler.toml
```

### 4. デプロイ

```bash
npm run deploy
# → Worker URL: https://nurserobby-aica-api.<subdomain>.workers.dev
```

### 5. LINE Webhook 設定

LINE Developers Console で Messaging API 設定:
- Webhook URL: `https://nurserobby-aica-api.<subdomain>.workers.dev/webhook/line`
- Webhookの利用: オン
- 応答メッセージ: オフ
- あいさつメッセージ: オフ（welcomeはWorkerが送信）

## 動作確認

```bash
# ヘルスチェック
curl https://nurserobby-aica-api.<subdomain>.workers.dev/health

# ログ監視
npm run tail
```

## MVP0 範囲

- [x] 4ターン導入ヒアリング（プロンプト実装済）
- [x] 軸判定（人間関係/労働時間/給与/キャリア/家庭/漠然）
- [x] 緊急キーワード検出 + Slack即通知
- [x] AIマルチプロバイダフォールバック（OpenAI→Claude→Gemini→Workers AI）
- [x] 状態管理（D1 candidates + messages）
- [x] 人間引き継ぎ（Slack #aica-handoff）
- [ ] LINE公式アカウント取得（社長手動）
- [ ] デプロイ＋動作確認（社長Credentials受領後）

## MVP1 以降の拡張（設計書参照）

- プロファイル補強5問（経験年数・診療科・希望エリア・希望年収・働き方）
- 既存D1施設DB参照の求人マッチング（Flex Message）
- AI書類生成（履歴書・職務経歴書・志望動機 PDF）
- 病院への推薦文自動生成 + メール送信
- AI面接対策（想定Q&A + 模擬面接）
- Google Calendar 連携（日程調整）
- 条件交渉叩き台生成
- 退職交渉支援
- 入職後5回Push（Day 1/3/7/30/90）

## 既存ナースロビーとの関係

| 項目 | 既存 | 新AICA |
|------|------|--------|
| Worker | `robby-the-match-api` | `nurserobby-aica-api` |
| ディレクトリ | `api/` | `api-aica/` |
| LINE公式 | `@174cxnev` | `@nurserobby_aica`(仮) |
| D1 メイン | `nurse-robby-db` | `nurserobby-aica-db` |
| D1 参照 | — | `nurse-robby-db` (読み取り) |
| Slack | #ロビー小田原人材紹介 | #aica-handoff (新) |
| OpenAI Key | 共通 | 共通 |
