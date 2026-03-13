#!/bin/bash
# ===========================================
# 神奈川ナース転職 ヘルスチェック + ハートビート v2.1
# cron: 0 7 * * *（毎日07:00）
# ===========================================

# ロック機構（1時間以内の二重実行を防止）
LOCKFILE="/tmp/pdca_healthcheck.lock"
if [ -f "$LOCKFILE" ]; then
    LOCK_AGE=$(($(date +%s) - $(stat -f %m "$LOCKFILE" 2>/dev/null || stat -c %Y "$LOCKFILE" 2>/dev/null || echo 0)))
    if [ "$LOCK_AGE" -lt 3600 ]; then
        echo "$(date): Already running (lock age: ${LOCK_AGE}s), skipping"; exit 0
    fi
    rm -f "$LOCKFILE"
fi
trap "rm -f $LOCKFILE" EXIT
touch "$LOCKFILE"

source ~/robby-the-match/scripts/utils.sh
init_log "healthcheck"
update_agent_state "health_monitor" "running"

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
PUBLIC_URL="https://quads-nurse.com/lp/job-seeker/"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$PUBLIC_URL" 2>/dev/null)
[ "$HTTP_CODE" != "200" ] && ISSUES="${ISSUES}\n❌ サイト応答異常(${HTTP_CODE})"

# === ログ容量チェック ===
LOG_SIZE=$(du -sm logs/ 2>/dev/null | awk '{print $1}')
[ "${LOG_SIZE:-0}" -gt 500 ] && ISSUES="${ISSUES}\n⚠️ logs/ ${LOG_SIZE}MB"

# === TikTok健全性チェック v3.0 ===
# upload_verification.json を主要指標とする。
# TikTokプロフィールスクレイプはbot検出で頻繁に失敗するため参考情報扱い。

# Step 1: upload_verification.json による主要健全性チェック（高速・確実）
echo "[INFO] TikTokアップロード検証（upload_verification.json基準）" >> "$LOG"
python3 -c "
import json, sys
from datetime import datetime, timedelta

try:
    with open('$PROJECT_DIR/data/upload_verification.json') as f:
        data = json.load(f)
    uploads = data.get('uploads', [])
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    recent = [u for u in uploads if u.get('timestamp', '') >= cutoff]
    recent_ok = sum(1 for u in recent if u.get('success'))
    recent_fail = len(recent) - recent_ok
    last_5 = uploads[-5:] if len(uploads) >= 5 else uploads
    last_5_ok = sum(1 for u in last_5 if u.get('success'))
    total_ok = sum(1 for u in uploads if u.get('success'))

    print(f'[INFO] upload_verification: 全{len(uploads)}件(成功{total_ok}), 直近7日{len(recent)}件(成功{recent_ok}/失敗{recent_fail})')

    if recent_fail >= 3 and last_5_ok < 3:
        print(f'[WARNING] アップロード失敗が多発: 直近7日{recent_fail}件失敗, 直近5件中{last_5_ok}件成功')
        sys.exit(1)
    else:
        print(f'[OK] アップロード健全: 直近5件中{last_5_ok}件成功')
        sys.exit(0)
except FileNotFoundError:
    print('[WARN] upload_verification.json not found')
    sys.exit(0)
except Exception as e:
    print(f'[WARN] upload_verification check failed: {e}')
    sys.exit(0)
" >> "$LOG" 2>&1
UV_EXIT=$?
if [ "$UV_EXIT" -eq 1 ]; then
  ISSUES="${ISSUES}\n⚠️ TikTokアップロード失敗が連続中（upload_verification.json基準）"
fi

# Step 2: ハートビート（Cookie有効期限、venv、キュー状態など）
echo "[INFO] TikTokハートビート実行" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_post.py" --heartbeat >> "$LOG" 2>&1
HEARTBEAT_EXIT=$?

# Step 3: 投稿検証 v2.1（upload_verification.json基準。プロフィール0件はbot検出として処理）
echo "[INFO] TikTok投稿検証実行" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_post.py" --verify >> "$LOG" 2>&1
VERIFY_EXIT=$?

# heartbeat/検証の結果をログ解析してISSUESに追加
# v3.0: upload_verification.json基準のみ。プロフィール取得失敗はINFO扱い
if grep -q "アップロード健全性低下" "$LOG" 2>/dev/null; then
  ISSUES="${ISSUES}\n⚠️ TikTokアップロード健全性低下"
fi

# Step 4: TikTok分析データ収集（オプション — bot検出で失敗しても問題なし）
# tiktok_analytics.py --daily-kpi はPlaywrightでプロフィールをフェッチするため遅い。
# bot検出で失敗することが多いのでWARN扱いで続行する。
echo "[INFO] TikTok分析データ収集（参考・失敗OK）" >> "$LOG"
python3 "$PROJECT_DIR/scripts/tiktok_analytics.py" --daily-kpi >> "$LOG" 2>&1 || echo "[INFO] TikTok分析スキップ（bot検出の可能性。問題なし）" >> "$LOG"

# === Agent Team稼働状態チェック ===
echo "[INFO] Agent Team稼働状態チェック" >> "$LOG"
python3 -c "
import json
from datetime import datetime, timedelta

# Per-agent staleness thresholds (hours)
# Weekly agents get 192h (8 days), daily agents get 48h
THRESHOLDS = {
    'weekly_strategist': 192,
    'weekly_content_planner': 192,
    'seo_optimizer': 48,
    'health_monitor': 48,
    'competitor_analyst': 48,
    'content_creator': 48,
    'daily_reviewer': 48,
    'sns_poster': 48,
    'ai_marketing_orchestrator': 48,
}

try:
    with open('$PROJECT_DIR/data/agent_state.json') as f:
        state = json.load(f)
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f'[ERROR] agent_state.json read failed: {e}')
    exit(0)

now = datetime.now()
for agent, last_run in state.get('lastRun', {}).items():
    threshold = THRESHOLDS.get(agent, 48)
    if last_run:
        last = datetime.fromisoformat(last_run)
        hours_ago = (now - last).total_seconds() / 3600
        if hours_ago > threshold:
            print(f'warning {agent}: {hours_ago:.0f}h since last run (threshold: {threshold}h)')
    else:
        status = state.get('status', {}).get(agent, 'unknown')
        if status == 'pending':
            print(f'info {agent}: not yet executed (pending)')
" >> "$LOG" 2>&1

# === 自己修復アクション ===
echo "[INFO] 自己修復チェック..." >> "$LOG"

# 1. Failed状態のエージェントを24h後にリセット + stale pendingTasks cleanup
python3 -c "
import json
from datetime import datetime, timedelta
try:
    with open('$PROJECT_DIR/data/agent_state.json') as f:
        state = json.load(f)
    now = datetime.now()
    changed = False

    # 1a. Reset failed agents after 24h
    healed = []
    for agent, status in state.get('status', {}).items():
        if status == 'failed':
            last = state.get('lastRun', {}).get(agent)
            if last:
                last_dt = datetime.fromisoformat(last)
                if (now - last_dt).total_seconds() > 86400:
                    state['status'][agent] = 'pending'
                    healed.append(agent)
                    changed = True
    for a in healed:
        print(f'[HEAL] {a}: failed -> pending (>24h)')

    # 1b. Clean up stale pendingTasks (processing > 48h or completed)
    for agent, tasks in state.get('pendingTasks', {}).items():
        cleaned = []
        for t in tasks:
            created = t.get('created', '')
            status = t.get('status', '')
            if status in ('completed', 'done'):
                changed = True
                continue
            if status == 'processing' and created:
                try:
                    created_dt = datetime.fromisoformat(created)
                    if (now - created_dt).total_seconds() > 172800:  # 48h
                        print(f'[HEAL] Removed stale task for {agent}: {t.get(\"type\", \"?\")} (processing >48h)')
                        changed = True
                        continue
                except ValueError:
                    pass
            cleaned.append(t)
        state['pendingTasks'][agent] = cleaned

    if changed:
        with open('$PROJECT_DIR/data/agent_state.json', 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f'[WARN] self-heal failed: {e}')
" >> "$LOG" 2>&1

# 2. キュー枯渇時の緊急タスク作成
python3 -c "
import json
from datetime import datetime
try:
    with open('$PROJECT_DIR/data/posting_queue.json') as f:
        q = json.load(f)
    pending = sum(1 for p in q['posts'] if p['status'] == 'pending')
    if pending < 3:
        with open('$PROJECT_DIR/data/agent_state.json') as f:
            state = json.load(f)
        tasks = state.setdefault('pendingTasks', {}).setdefault('content_creator', [])
        has_pending = any(t['status'] == 'pending' for t in tasks)
        if not has_pending:
            tasks.append({
                'from': 'health_monitor',
                'type': 'emergency_generate',
                'details': f'キュー残り{pending}件。緊急コンテンツ生成必要。',
                'created': datetime.now().isoformat(),
                'status': 'pending'
            })
            with open('$PROJECT_DIR/data/agent_state.json', 'w') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
            print(f'[HEAL] content_creatorに緊急生成タスク作成（残{pending}件）')
except Exception as e:
    print(f'[WARN] キューチェック失敗: {e}')
" >> "$LOG" 2>&1

# 3. ログローテーション
# 3a. 日付入りログ（*_YYYY-MM-DD.log, *_YYYYMMDD.log）は7日で削除
OLD_DATED=$(find "$PROJECT_DIR/logs/" \( -name "*_20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].log" -o -name "*_20[0-9][0-9][0-9][0-9][0-9][0-9].log" \) -mtime +7 2>/dev/null | wc -l | tr -d ' ')
if [ "${OLD_DATED:-0}" -gt 0 ]; then
    find "$PROJECT_DIR/logs/" \( -name "*_20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].log" -o -name "*_20[0-9][0-9][0-9][0-9][0-9][0-9].log" \) -mtime +7 -delete 2>/dev/null
    echo "[HEAL] ${OLD_DATED} dated log files deleted (>7 days)" >> "$LOG"
fi

# 3b. 追記型ログ（slack_commander.log, watchdog.log等）は500KB超で切り詰め
for APPEND_LOG in "$PROJECT_DIR/logs/slack_commander.log" "$PROJECT_DIR/logs/watchdog.log"; do
    if [ -f "$APPEND_LOG" ]; then
        FSIZE=$(wc -c < "$APPEND_LOG" 2>/dev/null | tr -d ' ')
        if [ "${FSIZE:-0}" -gt 512000 ]; then
            ARCHIVE="${APPEND_LOG}.$(date +%Y%m%d).bak"
            cp "$APPEND_LOG" "$ARCHIVE" 2>/dev/null
            tail -200 "$APPEND_LOG" > "${APPEND_LOG}.tmp" && mv "${APPEND_LOG}.tmp" "$APPEND_LOG"
            echo "[HEAL] $(basename "$APPEND_LOG") truncated (was ${FSIZE} bytes)" >> "$LOG"
            # Remove old archives beyond the 3 most recent
            ls -t "${APPEND_LOG}".*.bak 2>/dev/null | tail -n +4 | xargs rm -f 2>/dev/null
        fi
    fi
done

# 3c. その他の古いログ（30日超）
OLD_OTHER=$(find "$PROJECT_DIR/logs/" -name "*.log" -not -name "slack_commander.log" -not -name "watchdog.log" -mtime +30 2>/dev/null | wc -l | tr -d ' ')
if [ "${OLD_OTHER:-0}" -gt 0 ]; then
    find "$PROJECT_DIR/logs/" -name "*.log" -not -name "slack_commander.log" -not -name "watchdog.log" -mtime +30 -delete 2>/dev/null
    echo "[HEAL] ${OLD_OTHER} old log files deleted (>30 days)" >> "$LOG"
fi

# 3d. PNG/スクリーンショット等の非ログファイルを14日で削除
OLD_IMGS=$(find "$PROJECT_DIR/logs/" -name "*.png" -mtime +14 2>/dev/null | wc -l | tr -d ' ')
if [ "${OLD_IMGS:-0}" -gt 0 ]; then
    find "$PROJECT_DIR/logs/" -name "*.png" -mtime +14 -delete 2>/dev/null
    echo "[HEAL] ${OLD_IMGS} old image files deleted (>14 days)" >> "$LOG"
fi

# === レポート送信 ===
if [ -n "$ISSUES" ]; then
  slack_notify "🏥 ヘルスチェック問題あり:\n$(echo -e "$ISSUES")" "alert"
else
  echo "[OK] 全システム正常" >> "$LOG"
  # 正常時も1行サマリーをSlackに送信（沈黙を避ける）
  QUEUE_COUNT=$(python3 -c "import json; d=json.load(open('$PROJECT_DIR/data/posting_queue.json')); print(sum(1 for p in d['posts'] if p['status'] in ('ready','pending')))" 2>/dev/null || echo "?")
  COOKIE_DAYS=$(python3 -c "
import os, time
cookie_file = '$PROJECT_DIR/data/.tiktok_cookies.txt'
if os.path.exists(cookie_file):
    age = time.time() - os.path.getmtime(cookie_file)
    remaining = max(0, 180 - int(age / 86400))
    print(remaining)
else:
    print('?')
" 2>/dev/null || echo "?")
  NOW_MMDD=$(date +%m/%d)
  NOW_HHMM=$(date +%H:%M)
  slack_notify "✅ ${NOW_MMDD} ${NOW_HHMM} ヘルスチェック正常 | キュー: ${QUEUE_COUNT}件 | Cookie残り: ${COOKIE_DAYS}日"
fi

update_agent_state "health_monitor" "completed"
# heartbeat: 0=正常(問題なし), 1=問題検出(ただしスクリプト自体は正常完了)
if [ -n "$ISSUES" ]; then
  write_heartbeat "healthcheck" 1
else
  write_heartbeat "healthcheck" 0
fi
echo "[$TODAY] healthcheck完了" >> "$LOG"
