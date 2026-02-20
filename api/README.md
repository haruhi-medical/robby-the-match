# ROBBY THE MATCH - API (Cloudflare Workers)

フォーム送信を受け取り、Slack通知とGoogle Sheets書き込みを行うサーバーサイドAPI。

## エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/api/register` | 求職者登録（フォームデータ受信） |
| GET | `/api/health` | ヘルスチェック |

## セットアップ

### 1. 前提条件

- [Cloudflare アカウント](https://dash.cloudflare.com/sign-up)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/install-and-update/)

```bash
npm install -g wrangler
wrangler login
```

### 2. シークレット設定

以下のコマンドでシークレット（環境変数）を設定:

```bash
cd api/

# Slack Incoming Webhook URL
wrangler secret put SLACK_WEBHOOK_URL
# → プロンプトに Webhook URL を入力

# Google Sheets スプレッドシートID
wrangler secret put GOOGLE_SHEETS_ID
# → スプレッドシートURLの /d/ と /edit の間のID

# Google サービスアカウント JSON（1行に整形して入力）
wrangler secret put GOOGLE_SERVICE_ACCOUNT_JSON
# → サービスアカウントのJSONキーファイルの内容

# 許可オリジン（CORS）
wrangler secret put ALLOWED_ORIGIN
# → フロントエンドのURL（例: https://robby-the-match.pages.dev）
```

### 3. Google サービスアカウント準備

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Google Sheets API を有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. スプレッドシートをサービスアカウントのメールアドレスに共有（編集者権限）
5. スプレッドシートに「求職者台帳」シートを作成し、以下のヘッダー行を追加:

```
登録日時 | 氏名 | 年齢 | 電話番号 | メールアドレス | 経験年数 | 現在勤務状況 | 希望転職時期 | 希望給与 | 希望条件詳細 | 進捗ステータス | 温度感 | 担当者 | 備考
```

### 4. デプロイ

```bash
cd api/
wrangler deploy
```

デプロイ後に表示されるURLを `config.js` の `API.workerEndpoint` に設定。

### 5. ローカル開発

```bash
cd api/
wrangler dev
```

## セキュリティ

- API キー・Webhook URL はすべて Cloudflare Workers のシークレットとして管理
- CORS でオリジンを制限（`ALLOWED_ORIGIN`）
- レート制限: 同一IP 1分に5回まで
- サーバーサイドバリデーション（フロントエンドと二重チェック）
- 入力値サニタイズ（Slack mrkdwn injection 防止）

## リクエスト例

```bash
curl -X POST https://your-worker.workers.dev/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "lastName": "山田",
    "firstName": "太郎",
    "age": "30",
    "phone": "090-1234-5678",
    "email": "yamada@example.com",
    "experience": "5年以上",
    "currentStatus": "在職中",
    "transferTiming": "すぐにでも",
    "desiredSalary": "月収30万以上",
    "workStyle": "常勤",
    "nightShift": "可",
    "holidays": "週休2日",
    "commuteRange": "30分以内",
    "notes": ""
  }'
```

## レスポンス

成功:
```json
{ "success": true, "message": "登録が完了しました" }
```

バリデーションエラー:
```json
{ "success": false, "error": "入力内容に不備があります", "details": ["姓を入力してください"] }
```

レート制限:
```json
{ "success": false, "error": "リクエスト回数が上限を超えました。しばらくしてから再度お試しください。" }
```
