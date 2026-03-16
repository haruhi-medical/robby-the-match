#!/bin/bash
set -euo pipefail
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_seo_batch"
update_agent_state "seo_optimizer" "running"
check_instructions "seo_optimizer"

# Cloudflare Workers AI認証確認
ensure_cf_env || {
  echo "[ABORT] Cloudflare認証エラーのためスキップ" >> "$LOG"
  update_agent_state "seo_optimizer" "config_error"
  write_heartbeat "seo_batch" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

# CF AI でSEO診断
python3 "$PROJECT_DIR/scripts/pdca_ai_engine.py" --job seo_batch >> "$LOG" 2>&1
JOB_EXIT=$?

if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Cloudflare認証エラー (exit=$JOB_EXIT)" >> "$LOG"
  update_agent_state "seo_optimizer" "config_error"
  write_heartbeat "seo_batch" $JOB_EXIT
  exit $EXIT_CONFIG_ERROR
fi

git_sync "seo: ${TODAY} SEO改善" "true"
update_state "SEO朝サイクル"
update_progress "🔍 SEO朝サイクル" "$(git log -1 --pretty=%s 2>/dev/null)"
update_agent_state "seo_optimizer" "completed"
write_heartbeat "seo_batch" $JOB_EXIT
echo "[$TODAY] pdca_seo_batch完了 (exit=$JOB_EXIT)" >> "$LOG"
