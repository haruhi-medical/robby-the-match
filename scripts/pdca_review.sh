#!/bin/bash
set -euo pipefail
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_review"
update_agent_state "daily_reviewer" "running"
check_instructions "daily_reviewer"

# === TikTok分析データ収集 ===
echo "[INFO] TikTok分析データ収集中..." >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_analytics.py" --update >> "$LOG" 2>&1 || echo "[WARN] TikTok分析失敗" >> "$LOG"

# === パフォーマンス分析 ===
echo "[INFO] パフォーマンス分析実行中..." >> "$LOG"
python3 "$PROJECT_DIR/scripts/analyze_performance.py" --analyze >> "$LOG" 2>&1 || echo "[WARN] パフォーマンス分析失敗" >> "$LOG"

# Cloudflare Workers AI認証確認
ensure_cf_env || {
  echo "[ABORT] Cloudflare認証エラーのためスキップ" >> "$LOG"
  update_agent_state "daily_reviewer" "config_error"
  write_heartbeat "review" $EXIT_CONFIG_ERROR
  exit $EXIT_CONFIG_ERROR
}

# CF AI で日次レビュー
python3 "$PROJECT_DIR/scripts/pdca_ai_engine.py" --job review >> "$LOG" 2>&1
JOB_EXIT=$?

if [ "$JOB_EXIT" -eq "$EXIT_CONFIG_ERROR" ]; then
  echo "[ABORT] Cloudflare認証エラー (exit=$JOB_EXIT)" >> "$LOG"
  update_agent_state "daily_reviewer" "config_error"
  write_heartbeat "review" $JOB_EXIT
  exit $EXIT_CONFIG_ERROR
fi

# === sharedContext更新（他エージェント向け） ===
echo "[INFO] sharedContext更新中..." >> "$LOG"
python3 -c "
import json
from pathlib import Path
try:
    project = Path('$PROJECT_DIR')

    # Read analysis
    analysis = {}
    ap = project / 'data' / 'performance_analysis.json'
    if ap.exists():
        with open(ap) as f:
            analysis = json.load(f)

    # Read queue
    pending = 0
    qp = project / 'data' / 'posting_queue.json'
    if qp.exists():
        with open(qp) as f:
            q = json.load(f)
        pending = sum(1 for p in q['posts'] if p['status'] == 'pending')

    # Update shared context
    with open('$AGENT_STATE_FILE') as f:
        state = json.load(f)
    ctx = state.setdefault('sharedContext', {})
    ctx['lastAnalysis'] = analysis.get('analyzed_at', '')
    ctx['recommendations'] = analysis.get('recommendations', [])
    ctx['topPerformingTags'] = [
        p.get('content_id')
        for p in analysis.get('content_performance', {}).get('best_performing', [])
    ]
    ctx['queueRemaining'] = pending
    ctx['totalPostsThisWeek'] = sum(
        1 for p in q.get('posts', [])
        if p.get('status') == 'posted'
    ) if qp.exists() else 0

    with open('$AGENT_STATE_FILE', 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f'[OK] sharedContext更新: queue={pending}, recommendations={len(ctx[\"recommendations\"])}')
except Exception as e:
    print(f'[WARN] sharedContext更新失敗: {e}')
" >> "$LOG" 2>&1

git_sync "review: ${TODAY} 日次レビュー" "true"
update_state "日次レビュー"

TODAY_REPORT=$(sed -n "/## ${TODAY}/,/## [0-9]/p" PROGRESS.md 2>/dev/null | head -50)
update_agent_state "daily_reviewer" "completed"
write_heartbeat "review" $JOB_EXIT
echo "[$TODAY] pdca_review完了 (exit=$JOB_EXIT)" >> "$LOG"
