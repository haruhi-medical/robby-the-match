# /status — 現在の状態を一目で確認

プロジェクトの全状態を簡潔に表示する。

## 収集する情報（並列実行）

1. `STATE.md` のKPIセクション
2. `git log --oneline -5`（最新の変更）
3. `git status -s`（未コミットの変更）
4. `crontab -l | grep -v "^#"`（稼働中のcronジョブ数）
5. `cat data/posting_queue.json | python3 -c "import json,sys; q=json.load(sys.stdin); print(f'ready:{len([x for x in q if x.get(\"status\")==\"ready\"])}, posted:{len([x for x in q if x.get(\"status\")==\"posted\"])}')"` （投稿キュー状態）
6. `python3 scripts/slack_bridge.py --inbox`（未読Slack）

## 表示フォーマット

```
📊 神奈川ナース転職状態レポート
━━━━━━━━━━━━━━━━━━━━━━━━━━
🏥 施設DB: XXX施設
📱 投稿キュー: ready XX / posted XX
📈 KPI: [STATE.mdから抜粋]
🔄 最新変更: [git log 3行]
⚠️ 未コミット: [あり/なし]
💬 Slack未読: [件数]
⏰ cron: [X個稼働中]
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
