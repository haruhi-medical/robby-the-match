#!/bin/bash
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_competitor"
update_agent_state "competitor_analyst" "running"
check_instructions "competitor_analyst"

# Claude CLI認証確認（cron環境対策）
ensure_env || {
  echo "[ABORT] Claude CLI 認証エラーのためスキップ" >> "$LOG"
  update_agent_state "competitor_analyst" "config_error"
  write_heartbeat "competitor" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

run_claude "
STATE.mdを読め。docs/seo_strategy.mdも読め。

【競合監視サイクル】
1. 主要KW（神奈川県西部 看護師、小田原 看護師 転職、看護師 紹介料 10%）の競合を推定
2. 自社の子ページ数と競合のページ数を比較
3. 対策が必要なら具体的アクション提案
4. STATE.mdの戦略メモを更新
5. PROGRESS.mdに記録
" 20
JOB_EXIT=$?

# CONFIG_ERROR(78)の場合はgit_sync等を実行せずに終了
if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Claude CLI 認証エラー (run_claude exit=$JOB_EXIT)" >> "$LOG"
  update_agent_state "competitor_analyst" "config_error"
  write_heartbeat "competitor" $JOB_EXIT
  exit $EXIT_CONFIG_ERROR
fi

git_sync "competitor: ${TODAY} 競合監視"
update_state "競合監視"
update_progress "🔎 競合監視" "$(tail -5 logs/pdca_competitor_${TODAY}.log 2>/dev/null)"
update_agent_state "competitor_analyst" "completed"
slack_notify "🔎 競合監視完了。" "seo"
write_heartbeat "competitor" $JOB_EXIT
echo "[$TODAY] pdca_competitor完了 (exit=$JOB_EXIT)" >> "$LOG"
