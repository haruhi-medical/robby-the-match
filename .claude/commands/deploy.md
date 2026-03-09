# /deploy — ナースロビー デプロイスキル

変更をコミットしてデプロイする。確認なしで即実行。

## 手順

1. `git status -s` で変更ファイルを確認
2. 変更がなければ「変更なし」と報告して終了
3. `git diff --stat` で変更内容を把握
4. `git log --oneline -3` でコミットメッセージスタイルを確認
5. 変更内容に基づいて簡潔な日本語コミットメッセージを作成
6. 変更ファイルを `git add` （.envや機密ファイルは除外）
7. `git commit` 実行
8. `git push origin main && git push origin main:master` でデプロイ
9. Slackにデプロイ通知を送信: `python3 scripts/slack_bridge.py --send "🚀 デプロイ完了: [コミットメッセージ]"`
10. 結果を簡潔に報告

## 注意
- .env、credentials、secretsファイルは絶対にコミットしない
- Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com> をコミットメッセージに付ける
- data/mhlw_data/ 等の大きなデータディレクトリは必要な場合のみ含める
