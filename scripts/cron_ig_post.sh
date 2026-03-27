#!/bin/bash
# ============================================
# cron_ig_post.sh — Instagram自動投稿（毎日21:00）
# Chrome Debug Mode + Meta Business Suite経由でカルーセル投稿
# ============================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/instagram_post_$(date +%Y-%m-%d).log"
SLACK_SCRIPT="$SCRIPT_DIR/slack_bridge.py"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

slack_notify() {
    /usr/bin/python3 "$SLACK_SCRIPT" --send "$1" >> "$LOG_FILE" 2>&1 || true
}

log "=== Instagram投稿パイプライン開始 ==="

cd "$PROJECT_DIR"

# Step 1: Chrome Debug Mode起動
log "Chrome Debug Mode起動中..."
if /bin/bash scripts/start_chrome_debug.sh >> "$LOG_FILE" 2>&1; then
    log "Chrome Debug Mode: OK"
else
    log "Chrome Debug Mode起動失敗"
    slack_notify "🚨 [cron] Instagram投稿失敗: Chrome Debug Modeが起動できません"
    exit 1
fi

# Chrome安定化のため少し待つ
sleep 5

# Step 2: ランダム遅延（0〜30分）で投稿時間を自然に分散
DELAY=$((RANDOM % 1800))
log "ランダム遅延: ${DELAY}秒"
sleep $DELAY

# Step 3: 投稿実行
log "ig_post_meta_suite.py実行中..."
if /usr/bin/python3 scripts/ig_post_meta_suite.py >> "$LOG_FILE" 2>&1; then
    log "Instagram投稿成功"
    # ig_post_meta_suite.py内でSlack通知済みだが、cron用に追加ログ
else
    EXIT_CODE=$?
    log "Instagram投稿失敗 (exit: $EXIT_CODE)"
    # ig_post_meta_suite.py内でもSlack通知するが、cron層でも送る
    slack_notify "🚨 [cron] Instagram投稿失敗 (exit: $EXIT_CODE)。手動確認が必要です。ログ: $LOG_FILE"
    exit $EXIT_CODE
fi

log "=== Instagram投稿パイプライン終了 ==="
