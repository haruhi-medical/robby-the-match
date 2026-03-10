#!/bin/bash
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_morning"

run_claude "
お前は神奈川ナース転職の経営参謀だ。CLAUDE.mdを読め。

【SEO改善PDCAサイクル】

■ Plan
1. PROGRESS.mdのKPIダッシュボードとSEO施策履歴を確認
2. lp/job-seeker/index.html のSEO診断:
   - title/meta description/h1/h2キーワード最適化
   - JobPosting JSON-LD
   - ローカルキーワード密度（小田原、神奈川県西部、湘南）
   - OGP設定
   - 内部リンク
   - ページ速度（不要なリソースがないか）
3. 改善点を優先順位付きで最大3つリストアップ

■ Do
4. 優先度1の改善を実施
5. 可能なら優先度2も実施
6. sitemap.xmlのlastmodを今日に更新

■ Check
7. git diffで変更内容確認
8. HTML構文にエラーがないか確認
9. 問題があればgit checkout -- で戻す

■ Act
10. PROGRESS.mdに追記（update_progress関数を使え）:
    施策内容、変更ファイル、次回改善候補
11. KPIダッシュボードの「SEO施策数」をインクリメント

完了報告は不要。スクリプト側でSlack通知する。
"

git_sync "seo: ${TODAY} SEO改善"
update_progress "🔍 SEO朝サイクル" "$(git log -1 --pretty=%s 2>/dev/null || echo '変更なし')"
slack_report "🔍 SEO朝サイクル"
echo "[$TODAY] pdca_morning完了" >> "$LOG"
