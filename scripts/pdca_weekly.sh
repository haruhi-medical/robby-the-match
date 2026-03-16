#!/bin/bash
set -euo pipefail
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_weekly"
update_agent_state "weekly_strategist" "running"
check_instructions "weekly_strategist"

# === 週次パフォーマンス分析（AI実行前にデータ収集） ===
echo "[INFO] 週次パフォーマンス分析実行" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_analytics.py" --update >> "$LOG" 2>&1 || true
python3 "$PROJECT_DIR/scripts/analyze_performance.py" --analyze >> "$LOG" 2>&1 || true

# Cloudflare Workers AI認証確認
ensure_cf_env || {
  echo "[ABORT] Cloudflare認証エラーのためスキップ" >> "$LOG"
  update_agent_state "weekly_strategist" "config_error"
  write_heartbeat "weekly" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

# CF AI で週次総括
python3 "$PROJECT_DIR/scripts/pdca_ai_engine.py" --job weekly >> "$LOG" 2>&1
JOB_EXIT=$?

if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Cloudflare認証エラー (exit=$JOB_EXIT)" >> "$LOG"
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
