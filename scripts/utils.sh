#!/bin/bash
# ROBBY THE MATCH 共通関数
# 全PDCAスクリプトはこれをsourceして使う

PROJECT_DIR="$HOME/robby-the-match"
cd "$PROJECT_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$PATH"

# cron環境用: gh CLIのトークンをgit認証に使う
if command -v gh &>/dev/null; then
  export GH_TOKEN=$(gh auth token 2>/dev/null || true)
  if [ -n "$GH_TOKEN" ]; then
    git config --local credential.helper "!f() { echo username=haruhi-medical; echo password=$GH_TOKEN; }; f"
  fi
fi

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M:%S)
DOW=$(date +%u)
WEEK_NUM=$(date +%V)

init_log() {
  local name=$1
  LOG="logs/${name}_${TODAY}.log"
  mkdir -p logs
  echo "=== [$TODAY $NOW] $name 開始 ===" >> "$LOG"
}

git_sync() {
  local msg=$1
  cd "$PROJECT_DIR"
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "$msg"
    git push origin main 2>> "$LOG" || echo "[WARN] git push失敗" >> "$LOG"
  else
    echo "[INFO] 変更なし" >> "$LOG"
  fi
}

slack_notify() {
  local message=$1
  python3 "$PROJECT_DIR/scripts/notify_slack.py" --message "$message" 2>> "$LOG" \
    || echo "[WARN] Slack通知失敗" >> "$LOG"
}

slack_report_structured() {
  local report_type=${1:-"daily"}
  python3 "$PROJECT_DIR/scripts/slack_report.py" --report "$report_type" 2>> "$LOG" \
    || echo "[WARN] Slack構造化レポート失敗" >> "$LOG"
}

update_state() {
  local section=$1
  python3 -c "
import re
with open('STATE.md', 'r') as f: text = f.read()
text = re.sub(r'# 最終更新:.*', '# 最終更新: $(date "+%Y-%m-%d %H:%M") by ${section}', text)
with open('STATE.md', 'w') as f: f.write(text)
" 2>> "$LOG" || echo "[WARN] STATE.md更新失敗" >> "$LOG"
}

update_progress() {
  local cycle=$1
  local content=$2
  if ! grep -q "## ${TODAY}" PROGRESS.md 2>/dev/null; then
    echo -e "\n## ${TODAY}\n" >> PROGRESS.md
  fi
  echo "### ${cycle}（${NOW}）" >> PROGRESS.md
  echo "$content" >> PROGRESS.md
  echo "" >> PROGRESS.md
}

run_claude() {
  local prompt=$1
  local max_minutes=${2:-30}
  local max_seconds=$((max_minutes * 60))

  # macOS互換: timeout → gtimeout → perl fallback
  local timeout_cmd=""
  if command -v gtimeout &>/dev/null; then
    timeout_cmd="gtimeout"
  elif command -v timeout &>/dev/null; then
    timeout_cmd="timeout"
  fi

  if [ -n "$timeout_cmd" ]; then
    $timeout_cmd "${max_seconds}s" claude -p "$prompt" \
      --dangerously-skip-permissions \
      --max-turns 40 \
      >> "$LOG" 2>&1
  else
    # timeout系コマンドなし → バックグラウンド+waitで代替
    claude -p "$prompt" \
      --dangerously-skip-permissions \
      --max-turns 40 \
      >> "$LOG" 2>&1 &
    local pid=$!
    local elapsed=0
    while kill -0 $pid 2>/dev/null; do
      sleep 10
      elapsed=$((elapsed + 10))
      if [ $elapsed -ge $max_seconds ]; then
        kill $pid 2>/dev/null
        wait $pid 2>/dev/null
        echo "[TIMEOUT] ${max_minutes}分超過" >> "$LOG"
        slack_notify "⏰ タイムアウト（${max_minutes}分）"
        return 124
      fi
    done
    wait $pid
  fi

  local exit_code=$?
  if [ $exit_code -eq 124 ]; then
    echo "[TIMEOUT] ${max_minutes}分超過" >> "$LOG"
    slack_notify "⏰ タイムアウト（${max_minutes}分）"
  fi
  return $exit_code
}

handle_error() {
  local step=$1
  echo "[ERROR] $step" >> "$LOG"
  slack_notify "⚠️ エラー: $step"
}
