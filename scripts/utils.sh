#!/bin/bash
# 神奈川ナース転職 共通関数
# 全PDCAスクリプトはこれをsourceして使う

PROJECT_DIR="$HOME/robby-the-match"
cd "$PROJECT_DIR"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.npm-global/bin:$PATH"

# Prevent nested Claude Code session detection in cron/subprocess
unset CLAUDECODE CLAUDE_CODE_ENTRYPOINT 2>/dev/null || true

# Exit code for configuration errors (auth failures etc.) that should NOT be retried by watchdog
EXIT_CONFIG_ERROR=78

# cron環境用: gh CLIのトークンをgit認証に使う
export GH_CONFIG_DIR="$HOME/.config/gh"
if command -v gh &>/dev/null; then
  export GH_TOKEN=$(gh auth token 2>/dev/null || true)
  if [ -n "$GH_TOKEN" ]; then
    git config --local credential.helper "!f() { echo username=haruhi-medical; echo password=$GH_TOKEN; }; f"
  fi
fi

# .envから環境変数読み込み（Slack Token等）
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

TODAY=$(date +%Y-%m-%d)
NOW=$(date +%H:%M:%S)
DOW=$(date +%u)
WEEK_NUM=$(date +%V)

# ==========================================
# ensure_env: cron環境でのClaude CLI認証確認
# ==========================================
# run_claude()を使うスクリプトは、run_claude呼び出し前にこれを実行する。
# 戻り値:
#   0 = OK（Claude CLIが使える状態）
#   EXIT_CONFIG_ERROR(78) = 認証エラー（リトライ不可）
ensure_env() {
  local log_target="${LOG:-/dev/stderr}"

  # Step 1: .envを再確認（既にsource済みだが念のため）
  if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
  fi

  # Step 2: claude CLIの存在確認
  if ! command -v claude &>/dev/null; then
    echo "[CONFIG_ERROR] claude CLI が見つかりません（PATH=$PATH）" >> "$log_target"
    return $EXIT_CONFIG_ERROR
  fi

  # Step 3: 認証状態の確認
  # claude auth status はJSON出力。loggedIn:true を確認。
  local auth_output
  auth_output=$(claude auth status 2>&1) || true

  if echo "$auth_output" | grep -q '"loggedIn": true'; then
    echo "[ENV_OK] Claude CLI 認証確認済み" >> "$log_target"
    return 0
  fi

  # loggedIn:false の場合
  # ANTHROPIC_API_KEY がセットされていれば claude -p は API key モードで動く可能性がある
  if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[ENV_OK] Claude CLI未ログインだがANTHROPIC_API_KEY設定済み — APIキーモードで続行" >> "$log_target"
    return 0
  fi

  # 認証もAPIキーもない → 設定エラー
  echo "[CONFIG_ERROR] Claude CLI 認証失敗。ログインもAPIキーもありません。" >> "$log_target"
  echo "[CONFIG_ERROR] 手動で 'claude auth login' または .env に ANTHROPIC_API_KEY を設定してください。" >> "$log_target"
  echo "[CONFIG_ERROR] auth status出力: $auth_output" >> "$log_target"

  # Slack通知（可能であれば）
  slack_notify "⚠️ [CONFIG_ERROR] Claude CLI 認証失敗 — cron環境でログインできません。手動で 'claude auth login' を実行するか、.envにANTHROPIC_API_KEYを設定してください。" 2>/dev/null || true

  return $EXIT_CONFIG_ERROR
}

# ==========================================
# ensure_cf_env: Cloudflare Workers AI認証確認
# ==========================================
# run_claudeの代替。CF AIを使うスクリプトはこれを実行する。
ensure_cf_env() {
  local log_target="${LOG:-/dev/stderr}"

  if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
  fi

  if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ] || [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
    echo "[CONFIG_ERROR] CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not set in .env" >> "$log_target"
    slack_notify "⚠️ [CONFIG_ERROR] Cloudflare認証情報が未設定 — .envにCLOUDFLARE_ACCOUNT_IDとCLOUDFLARE_API_TOKENを設定してください" 2>/dev/null || true
    return $EXIT_CONFIG_ERROR
  fi

  echo "[ENV_OK] Cloudflare Workers AI認証確認済み" >> "$log_target"
  return 0
}

init_log() {
  local name=$1
  LOG="logs/${name}_${TODAY}.log"
  mkdir -p logs
  echo "=== [$TODAY $NOW] $name 開始 ===" >> "$LOG"
}

git_sync() {
  local msg=$1
  local do_push="${2:-false}"
  cd "$PROJECT_DIR"
  git add -A
  if ! git diff --cached --quiet; then
    git commit -m "$msg"
    if [ "$do_push" = "true" ]; then
      git push origin main 2>> "$LOG" || echo "[WARN] git push失敗" >> "$LOG"
    else
      echo "[INFO] commit済み（pushは日次レビューで一括）" >> "$LOG"
    fi
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
  _SECTION="$section" \
  _TIMESTAMP="$(date "+%Y-%m-%d %H:%M")" \
  python3 -c "
import re, os
section = os.environ.get('_SECTION', '')
timestamp = os.environ.get('_TIMESTAMP', '')
with open('STATE.md', 'r') as f: text = f.read()
text = re.sub(r'# 最終更新:.*', f'# 最終更新: {timestamp} by {section}', text)
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

  # macOS互換: gtimeout → timeout → background fallback
  local timeout_cmd=""
  if command -v gtimeout &>/dev/null; then
    timeout_cmd="gtimeout"
  elif command -v timeout &>/dev/null; then
    timeout_cmd="timeout"
  fi
  echo "[DEBUG] timeout_cmd=$timeout_cmd, max=${max_minutes}min" >> "$LOG"

  # ログの現在位置を記録（後で新規出力のみチェックするため）
  local log_size_before=0
  if [ -f "$LOG" ]; then
    log_size_before=$(wc -c < "$LOG" 2>/dev/null || echo 0)
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
    return 124
  fi

  # 認証エラー検出: claude CLIの出力に "Not logged in" や "Please run /login" が含まれるか確認
  if [ -f "$LOG" ]; then
    local new_output
    new_output=$(tail -c +"$((log_size_before + 1))" "$LOG" 2>/dev/null || true)
    if echo "$new_output" | grep -qiE "Not logged in|Please run /login|authentication.*failed|auth.*token.*expired"; then
      echo "[CONFIG_ERROR] Claude CLI 認証エラーを検出。exit_code=$exit_code → $EXIT_CONFIG_ERROR に変更" >> "$LOG"
      slack_notify "⚠️ [CONFIG_ERROR] Claude CLI 認証エラー — 手動で 'claude auth login' を実行してください" 2>/dev/null || true
      return $EXIT_CONFIG_ERROR
    fi
  fi

  return $exit_code
}

handle_error() {
  local step=$1
  echo "[ERROR] $step" >> "$LOG"
  slack_notify "⚠️ エラー: $step"
}

# ==========================================
# エージェント状態管理
# ==========================================

AGENT_STATE_FILE="$PROJECT_DIR/data/agent_state.json"

update_agent_state() {
  local agent_name="$1"
  local status="$2"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _AGENT_NAME="$agent_name" \
  _STATUS="$status" \
  python3 -c "
import json, os
from datetime import datetime

state_file = os.environ['_AGENT_STATE_FILE']
agent_name = os.environ['_AGENT_NAME']
status = os.environ['_STATUS']
default_state = {
    'lastRun': {},
    'status': {},
    'pendingTasks': {},
    'sharedContext': {},
    'agentMemory': {}
}

try:
    if os.path.exists(state_file) and os.path.getsize(state_file) > 0:
        with open(state_file, 'r') as f:
            content = f.read().strip()
        try:
            state = json.loads(content)
            if not isinstance(state, dict):
                raise ValueError('state is not a dict')
        except (json.JSONDecodeError, ValueError) as e:
            print(f'[WARN] agent_state.json corrupted, backing up and reinitializing: {e}')
            import shutil
            shutil.copy2(state_file, state_file + '.bak')
            state = default_state
    else:
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        state = default_state

    state.setdefault('lastRun', {})
    state.setdefault('status', {})
    state['lastRun'][agent_name] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    state['status'][agent_name] = status

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f'[WARN] agent_state update failed: {e}')
" 2>> "${LOG:-/dev/null}" || echo "[WARN] agent_state update failed" >> "${LOG:-/dev/null}"
}

handle_failure() {
  local agent_name="$1"
  local error_msg="$2"
  echo "[$agent_name] FAILURE: $error_msg" >> "$LOG"
  update_agent_state "$agent_name" "failed"
  slack_notify "⚠️ $agent_name failed: $error_msg"
}

check_instructions() {
  # Slack指示キューに自分宛の指示があるか確認
  local agent_name="$1"
  _INSTRUCTIONS_FILE="$PROJECT_DIR/data/slack_instructions.json" \
  _AGENT_NAME="$agent_name" \
  python3 -c "
import json, sys, os
try:
    instructions_file = os.environ['_INSTRUCTIONS_FILE']
    agent_name = os.environ['_AGENT_NAME']
    with open(instructions_file, 'r') as f:
        data = json.load(f)
    instructions = data.get('instructions', []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    pending = [i for i in instructions if isinstance(i, dict) and i.get('to') == agent_name and i.get('status') == 'pending']
    if pending:
        print(f'[INFO] {len(pending)}件の指示あり')
        for i in pending:
            print(f'  - {i.get(\"message\", \"\")}')
except FileNotFoundError:
    pass
except json.JSONDecodeError as e:
    print(f'[WARN] 指示キューJSON解析エラー: {e}', file=sys.stderr)
except Exception as e:
    print(f'[WARN] 指示チェック失敗: {e}', file=sys.stderr)
" 2>> "$LOG" || echo "[WARN] check_instructions python実行失敗 (agent=$agent_name)" >> "$LOG"
}

# ==========================================
# ハートビート（自己修復ウォッチドッグ用）
# ==========================================

write_heartbeat() {
  local job_name="$1"
  local exit_code="${2:-0}"
  if ! mkdir -p "$PROJECT_DIR/data/heartbeats" 2>> "$LOG"; then
    echo "[ERROR] heartbeat: data/heartbeats ディレクトリ作成失敗" >> "$LOG"
    return 1
  fi
  _HEARTBEAT_DIR="$PROJECT_DIR/data/heartbeats" \
  _JOB_NAME="$job_name" \
  _EXIT_CODE="$exit_code" \
  python3 -c "
import json, sys, os
from datetime import datetime
try:
    heartbeat_dir = os.environ['_HEARTBEAT_DIR']
    job_name = os.environ['_JOB_NAME']
    exit_code = int(os.environ.get('_EXIT_CODE', '0'))
    hb = {
        'ts': datetime.now().isoformat(),
        'exit_code': exit_code,
        'job': job_name,
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    with open(os.path.join(heartbeat_dir, job_name + '.json'), 'w') as f:
        json.dump(hb, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f'[ERROR] heartbeat書き込み失敗 ({os.environ.get(\"_JOB_NAME\", \"unknown\")}): {e}', file=sys.stderr)
    sys.exit(1)
" 2>> "$LOG" || echo "[WARN] heartbeat書き込み失敗: $job_name (exit_code=$exit_code)" >> "$LOG"
}

# ==========================================
# エージェントメモリ・通信・自己修復
# ==========================================

read_agent_memory() {
  local agent_name="$1"
  local key="$2"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _AGENT_NAME="$agent_name" \
  _KEY="$key" \
  python3 -c "
import json, sys, os
try:
    state_file = os.environ['_AGENT_STATE_FILE']
    agent_name = os.environ['_AGENT_NAME']
    key = os.environ['_KEY']
    with open(state_file) as f:
        state = json.load(f)
    val = state.get('agentMemory', {}).get(agent_name, {}).get(key, '')
    if isinstance(val, (dict, list)):
        print(json.dumps(val, ensure_ascii=False))
    else:
        print(val)
except FileNotFoundError:
    print(f'[WARN] agent_state.json not found', file=sys.stderr)
except Exception as e:
    print(f'[WARN] read_agent_memory failed ({agent_name}/{key}): {e}', file=sys.stderr)
" 2>> "${LOG:-/dev/stderr}"
}

write_agent_memory() {
  local agent_name="$1"
  local key="$2"
  local value="$3"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _AGENT_NAME="$agent_name" \
  _KEY="$key" \
  _VALUE="$value" \
  python3 -c "
import json, sys, os
try:
    state_file = os.environ['_AGENT_STATE_FILE']
    agent_name = os.environ['_AGENT_NAME']
    key = os.environ['_KEY']
    value = os.environ['_VALUE']
    with open(state_file) as f:
        state = json.load(f)
    mem = state.setdefault('agentMemory', {}).setdefault(agent_name, {})
    try:
        mem[key] = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        mem[key] = value
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f'[WARN] write_agent_memory failed: {e}', file=sys.stderr)
" 2>> "$LOG"
}

write_shared_context() {
  local key="$1"
  local value="$2"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _KEY="$key" \
  _VALUE="$value" \
  python3 -c "
import json, sys, os
try:
    state_file = os.environ['_AGENT_STATE_FILE']
    key = os.environ['_KEY']
    value = os.environ['_VALUE']
    with open(state_file) as f:
        state = json.load(f)
    ctx = state.setdefault('sharedContext', {})
    try:
        ctx[key] = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        ctx[key] = value
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
except Exception as e:
    print(f'[WARN] write_shared_context failed: {e}', file=sys.stderr)
" 2>> "$LOG"
}

create_agent_task() {
  local from_agent="$1"
  local to_agent="$2"
  local task_type="$3"
  local details="$4"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _FROM_AGENT="$from_agent" \
  _TO_AGENT="$to_agent" \
  _TASK_TYPE="$task_type" \
  _DETAILS="$details" \
  python3 -c "
import json, os
from datetime import datetime
try:
    state_file = os.environ['_AGENT_STATE_FILE']
    from_agent = os.environ['_FROM_AGENT']
    to_agent = os.environ['_TO_AGENT']
    task_type = os.environ['_TASK_TYPE']
    details = os.environ['_DETAILS']
    with open(state_file) as f:
        state = json.load(f)
    tasks = state.setdefault('pendingTasks', {}).setdefault(to_agent, [])
    tasks.append({
        'from': from_agent,
        'type': task_type,
        'details': details,
        'created': datetime.now().isoformat(),
        'status': 'pending'
    })
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    print(f'[TASK] {from_agent} -> {to_agent}: {task_type}')
except Exception as e:
    print(f'[WARN] create_agent_task failed: {e}')
" 2>> "$LOG"
}

consume_agent_tasks() {
  local agent_name="$1"
  _AGENT_STATE_FILE="$AGENT_STATE_FILE" \
  _AGENT_NAME="$agent_name" \
  python3 -c "
import json, os
try:
    state_file = os.environ['_AGENT_STATE_FILE']
    agent_name = os.environ['_AGENT_NAME']
    with open(state_file) as f:
        state = json.load(f)
    tasks = state.get('pendingTasks', {}).get(agent_name, [])
    pending = [t for t in tasks if t.get('status') == 'pending']
    if pending:
        for t in pending:
            print(f'[TASK] from={t[\"from\"]} type={t[\"type\"]} details={t[\"details\"]}')
            t['status'] = 'processing'
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    else:
        print('[INFO] タスクなし')
except Exception as e:
    print(f'[WARN] consume_agent_tasks failed: {e}')
" 2>> "$LOG"
}
