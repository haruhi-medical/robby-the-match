# UptimeRobot セットアップ手順（Phase 3 #59）

> 無料で Worker / GitHub Pages の5分おき監視を追加する手順。
> 所要時間: 15分。費用: ¥0（無料プラン 50モニターまで）。

## 監視対象

| 種別 | URL | ステータス期待値 | HTTPメソッド | キーワード検知 |
|------|-----|----------------|-------------|--------------|
| Worker API Health | `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health` | 200 | GET | `"status":"ok"` |
| LP (GitHub Pages) | `https://quads-nurse.com/` | 200 | GET | なし |
| LP (求職者LP) | `https://quads-nurse.com/lp/job-seeker/` | 200 | GET | なし |

## セットアップ手順（社長手動）

### Step 1: アカウント作成
1. https://uptimerobot.com/signUp にアクセス
2. Email: `robby.the.robot.2026@gmail.com`（既存Google）でサインアップ
3. Free Plan を選択（50モニター、5分間隔）

### Step 2: Worker API Health モニター追加
1. Dashboard → `+ Add New Monitor`
2. Monitor Type: **Keyword Monitor**（HTTPではなくKeyword）
3. Friendly Name: `Nurserobby Worker API Health`
4. URL: `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health`
5. Keyword Type: **Exists**
6. Keyword: `"status":"ok"`
7. Monitoring Interval: **5 minutes**（無料プラン最短）
8. Alert Contacts: Slack Webhook（下記）

### Step 3: LP モニター追加（2つ）
1. Monitor Type: **HTTP(s)**
2. Friendly Name: `Nurserobby LP Root` / `Nurserobby Job-Seeker LP`
3. URL: https://quads-nurse.com/ / https://quads-nurse.com/lp/job-seeker/
4. Monitoring Interval: **5 minutes**

### Step 4: Slack通知設定
1. My Settings → Alert Contacts → `+ Add Alert Contact`
2. Type: **Slack**
3. Slack Incoming Webhook URL を取得:
   - Slack Workspace → `ロビー小田原人材紹介` チャンネル
   - `#ロビー小田原人材紹介` を Incoming Webhook に追加
   - https://api.slack.com/apps → Your App → Incoming Webhooks
4. Channel: `#ロビー小田原人材紹介`
5. 全モニターに紐付け

### Step 5: ダウンタイム検知テスト
1. Worker を一時的に誤URL に切り替えるか、健康チェックを失敗させる
2. 5-10分待って Slack に通知が来ることを確認

## 運用ルール

- ダウン通知が来たら `docs/runbook.md` の「Worker障害」「GitHub Pages障害」セクションを参照
- UptimeRobot 自体のステータス: https://status.uptimerobot.com/

## 他の監視ツール（比較、採用しない）

| ツール | 月額 | 理由 |
|--------|------|------|
| Pingdom | $10〜 | 有料 |
| Checkly | $17〜 | 高機能すぎ |
| Datadog | $15〜 | オーバーキル |
| Cloudflare Workers Analytics | 無料 | 自前監視ができない（Worker自体が死んだら何も分からない） |

## 連動: 既存 watchdog.py との関係

- `scripts/watchdog.py`（30分おき）: Worker内部ロジックの健全性を自己診断
- UptimeRobot（5分おき）: 外部からの到達性を確認

両方あることで「Worker自体がデプロイ失敗で落ちた場合」も検知できる。
