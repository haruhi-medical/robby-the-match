#!/bin/bash
set -euo pipefail
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_competitor"
update_agent_state "competitor_analyst" "running"
check_instructions "competitor_analyst"

# Cloudflare Workers AI認証確認
ensure_cf_env || {
  echo "[ABORT] Cloudflare認証エラーのためスキップ" >> "$LOG"
  update_agent_state "competitor_analyst" "config_error"
  write_heartbeat "competitor" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

# CF AI で内部SEOギャップ分析
python3 "$PROJECT_DIR/scripts/pdca_ai_engine.py" --job competitor >> "$LOG" 2>&1
JOB_EXIT=$?

if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Cloudflare認証エラー (exit=$JOB_EXIT)" >> "$LOG"
  update_agent_state "competitor_analyst" "config_error"
  write_heartbeat "competitor" $JOB_EXIT
  exit $EXIT_CONFIG_ERROR
fi

git_sync "competitor: ${TODAY} 競合監視"
update_state "競合監視"
update_progress "🔎 競合監視" "$(tail -5 logs/pdca_competitor_${TODAY}.log 2>/dev/null)"
update_agent_state "competitor_analyst" "completed"
write_heartbeat "competitor" $JOB_EXIT
echo "[$TODAY] pdca_competitor完了 (exit=$JOB_EXIT)" >> "$LOG"
