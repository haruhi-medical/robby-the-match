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

# === 週次SEO改善チケット集計 ===
echo "[INFO] SEO改善チケット週次サマリ生成" >> "$LOG"
python3 -c "
import json, os, re
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_DIR = Path(os.path.expanduser('~/robby-the-match'))

# 直近7日分のSEOバッチログから改善提案を抽出
issues = set()
now = datetime.now()
for i in range(7):
    d = (now - timedelta(days=i)).strftime('%Y-%m-%d')
    log_path = PROJECT_DIR / 'logs' / f'pdca_seo_batch_{d}.log'
    if log_path.exists():
        content = log_path.read_text(encoding='utf-8', errors='ignore')
        # 改善が必要なファイル名を抽出
        for m in re.finditer(r'(area/\S+\.html|guide/\S+\.html|blog/\S+\.html)', content):
            issues.add(m.group(1))

if issues:
    msg = '📋 *週次SEO改善チケット*\n\n'
    msg += '自動修正不可の項目（要手動対応）:\n'
    for issue in sorted(issues):
        msg += f'- {issue}\n'
    msg += '\n詳細: logs/pdca_seo_batch_*.log'

    # Slack通知
    import subprocess
    subprocess.run(
        ['python3', str(PROJECT_DIR / 'scripts' / 'notify_slack.py'), '--message', msg],
        capture_output=True, timeout=30
    )
    print(f'SEO週次チケット: {len(issues)}件をSlack通知')
else:
    print('SEO週次チケット: 未対応項目なし')
" >> "$LOG" 2>&1 || echo "[WARN] SEO週次チケット集計失敗" >> "$LOG"

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
