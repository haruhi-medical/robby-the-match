#!/bin/bash
source ~/robby-the-match/scripts/utils.sh
init_log "healthcheck"

YESTERDAY=$(date -v-1d +%Y-%m-%d 2>/dev/null || date -d "yesterday" +%Y-%m-%d)
ISSUES=""

for cycle in pdca_seo_batch pdca_content pdca_review; do
  if [ ! -f "logs/${cycle}_${YESTERDAY}.log" ]; then
    ISSUES="${ISSUES}\n❌ ${cycle} 未実行"
  elif grep -q "ERROR\|TIMEOUT" "logs/${cycle}_${YESTERDAY}.log"; then
    ISSUES="${ISSUES}\n⚠️ ${cycle} にエラー"
  fi
done

PUBLIC_URL=$(grep "公開URL" STATE.md 2>/dev/null | awk '{print $NF}')
if [ -n "$PUBLIC_URL" ] && [ "$PUBLIC_URL" != "未設定" ]; then
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC_URL" 2>/dev/null)
  [ "$HTTP_CODE" != "200" ] && ISSUES="${ISSUES}\n❌ サイト応答異常(${HTTP_CODE})"
fi

LOG_SIZE=$(du -sm logs/ 2>/dev/null | awk '{print $1}')
[ "${LOG_SIZE:-0}" -gt 500 ] && ISSUES="${ISSUES}\n⚠️ logs/ ${LOG_SIZE}MB"

if [ -n "$ISSUES" ]; then
  slack_notify "🏥 ヘルスチェック問題あり:\n$(echo -e "$ISSUES")" "alert"
else
  echo "[OK] 問題なし" >> "$LOG"
fi
echo "[$TODAY] healthcheck完了" >> "$LOG"
