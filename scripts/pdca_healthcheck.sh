#!/bin/bash
# ===========================================
# ROBBY THE MATCH ヘルスチェック + ハートビート v2.0
# cron: 0 7 * * *（毎日07:00）
# ===========================================
source ~/robby-the-match/scripts/utils.sh
init_log "healthcheck"

YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
ISSUES=""

# === 既存のPDCAジョブ監視 ===
for cycle in pdca_seo_batch pdca_content pdca_review pdca_sns_post; do
  if [ -f "logs/${cycle}_${YESTERDAY}.log" ]; then
    if grep -q "ERROR\|TIMEOUT\|FAILED" "logs/${cycle}_${YESTERDAY}.log"; then
      ISSUES="${ISSUES}\n⚠️ ${cycle} にエラー"
    fi
  fi
done

# === サイト死活監視 ===
PUBLIC_URL="https://haruhi-medical.github.io/robby-the-match/lp/job-seeker/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC_URL" 2>/dev/null)
[ "$HTTP_CODE" != "200" ] && ISSUES="${ISSUES}\n❌ サイト応答異常(${HTTP_CODE})"

# === ログ容量チェック ===
LOG_SIZE=$(du -sm logs/ 2>/dev/null | awk '{print $1}')
[ "${LOG_SIZE:-0}" -gt 500 ] && ISSUES="${ISSUES}\n⚠️ logs/ ${LOG_SIZE}MB"

# === TikTokハートビート（v2.0追加）===
echo "[INFO] TikTokハートビート実行" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_post.py" --heartbeat >> "$LOG" 2>&1

# 投稿検証（キューとTikTok実投稿数の整合性チェック）
python3 "$PROJECT_DIR/scripts/tiktok_post.py" --verify >> "$LOG" 2>&1

# === レポート送信 ===
if [ -n "$ISSUES" ]; then
  slack_notify "🏥 ヘルスチェック問題あり:\n$(echo -e "$ISSUES")" "alert"
else
  echo "[OK] 全システム正常" >> "$LOG"
fi

echo "[$TODAY] healthcheck完了" >> "$LOG"
