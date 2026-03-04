#!/bin/bash
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_weekly"
update_agent_state "weekly_strategist" "running"
check_instructions "weekly_strategist"

# === 週次パフォーマンス分析（Claude実行前にデータ収集） ===
echo "[INFO] 週次パフォーマンス分析実行" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_analytics.py" --update >> "$LOG" 2>&1 || true
python3 "$PROJECT_DIR/scripts/analyze_performance.py" --analyze >> "$LOG" 2>&1 || true

# Claude CLI認証確認（cron環境対策）
ensure_env || {
  echo "[ABORT] Claude CLI 認証エラーのためスキップ" >> "$LOG"
  update_agent_state "weekly_strategist" "config_error"
  write_heartbeat "weekly" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

run_claude "
STATE.mdを読め。CLAUDE.mdも読め。docs/seo_strategy.mdも読め。
data/performance_analysis.jsonも読め（今週のパフォーマンス分析結果）。
data/kpi_log.csvも読め。content/stock.csvも読め（コンテンツ在庫状況）。

【週次高速総括サイクル】サブエージェント最大数で4チーム同時実行。

■ チームA: 週間データ分析
- PROGRESS.mdの今週分を全部読む
- git log --oneline --since='7 days ago'
- data/performance_analysis.json の分析結果を参照
- data/kpi_log.csv のKPIトレンドを確認
- 投稿数、PV、流入KW、SNS再生数を集計
- マイルストーン進捗チェック
- ピーター・ティールの問い:
  今週やったことで1人の看護師の意思決定に影響を与えたか？

■ チームB: 来週コンテンツ一括生成
- content/stock.csv を参照し、不足カテゴリを重点生成
- performance_analysis.jsonの高パフォーマンスパターンを参考に
- TikTok 7本（台本JSON+スライド42枚）
- CTA 8:2ルール、ペルソナチェック
- content/stock.csv に新規コンテンツを追記

■ チームC: SEO子ページ追加
- 新規子ページ5-10本作成（area/ or guide/に追加）
- ロングテールKW開拓
- 内部リンク再構築
- sitemap.xml更新

■ チームD: 自己改善
- CLAUDE.md更新（効いたパターン★、失敗パターン✕）
- STATE.md全面更新（KPI欄をデータで更新）
- スクリプト改善
- MIX比率調整提案（変更はSlack確認必須、勝手に変えるな）
- data/agent_state.json のagentMemory更新

全完了後:
- PROGRESS.mdに週次サマリ
- KPIダッシュボード最新化
" 45
JOB_EXIT=$?

# CONFIG_ERROR(78)の場合はgit_sync等を実行せずに終了
if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Claude CLI 認証エラー (run_claude exit=$JOB_EXIT)" >> "$LOG"
  update_agent_state "weekly_strategist" "config_error"
  write_heartbeat "weekly" $JOB_EXIT
  exit $EXIT_CONFIG_ERROR
fi

git_sync "weekly: Week${WEEK_NUM} 振り返り+来週分生成"
update_state "週次振り返り"

WEEKLY_STATE=$(head -60 STATE.md 2>/dev/null)
update_agent_state "weekly_strategist" "completed"
slack_notify "📈 Week${WEEK_NUM} 週次レポート
━━━━━━━━━━━━━━━━━━
${WEEKLY_STATE:-STATE.md参照}
━━━━━━━━━━━━━━━━━━" "daily"
write_heartbeat "weekly" $JOB_EXIT
echo "[$TODAY] pdca_weekly完了 (exit=$JOB_EXIT)" >> "$LOG"
