# /slack-report — Slackにレポート送信

指定した内容をSlackに送信する。

## 引数
- 指定なし: 日次レポート送信
- `daily`: 日次レポート
- `kpi`: KPIサマリ
- `deploy [メッセージ]`: デプロイ通知
- `[自由文]`: そのまま送信

## 手順

1. 引数を解析
2. レポートタイプに応じて情報を収集:
   - **daily**: STATE.mdのKPI + git log今日分 + cron稼働状態
   - **kpi**: STATE.mdのKPIテーブルをフォーマット
   - **deploy**: コミット情報 + 変更ファイル一覧
   - **自由文**: そのまま送信
3. `python3 scripts/slack_bridge.py --send "メッセージ"` で送信
4. 送信結果を表示
