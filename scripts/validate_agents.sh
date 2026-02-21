#!/bin/bash
# ===========================================
# ROBBY THE MATCH Agent Team検証スクリプト
# 全8エージェントの動作環境を一括チェック
# ===========================================
source ~/robby-the-match/scripts/utils.sh
init_log "validate_agents"

echo "=== Agent Team 環境検証 ==="
echo "=== Agent Team 環境検証 ===" >> "$LOG"
ISSUES=""

# 1. PATH確認
echo -n "  PATH /opt/homebrew/bin: "
echo "$PATH" | grep -q "/opt/homebrew/bin" && echo "OK" || { echo "MISSING"; ISSUES="${ISSUES}\nPATH missing /opt/homebrew/bin"; }

# 2. gtimeout
echo -n "  gtimeout: "
if command -v gtimeout &>/dev/null; then
    echo "OK ($(gtimeout --version | head -1))"
else
    echo "MISSING — run: brew install coreutils"
    ISSUES="${ISSUES}\ngtimeout missing"
fi

# 3. Claude CLI
echo -n "  claude: "
if command -v claude &>/dev/null; then
    echo "OK ($(which claude))"
else
    echo "MISSING"
    ISSUES="${ISSUES}\nclaude CLI missing"
fi

# 4. Python venv
echo -n "  venv python3: "
if [ -f "$PROJECT_DIR/.venv/bin/python3" ]; then
    echo "OK ($($PROJECT_DIR/.venv/bin/python3 --version))"
else
    echo "MISSING"
    ISSUES="${ISSUES}\nvenv missing"
fi

# 5. ffmpeg
echo -n "  ffmpeg: "
command -v ffmpeg &>/dev/null && echo "OK" || { echo "MISSING"; ISSUES="${ISSUES}\nffmpeg missing"; }

# 6. GH_TOKEN
echo -n "  GH_TOKEN: "
if [ -n "$GH_TOKEN" ]; then
    echo "OK (${GH_TOKEN:0:10}...)"
else
    echo "MISSING — gh auth loginが必要"
    ISSUES="${ISSUES}\nGH_TOKEN missing"
fi

# 7. Slack .env
echo -n "  SLACK_BOT_TOKEN: "
if [ -n "$SLACK_BOT_TOKEN" ]; then
    echo "OK (${SLACK_BOT_TOKEN:0:10}...)"
else
    echo "MISSING — .envを確認"
    ISSUES="${ISSUES}\nSLACK_BOT_TOKEN missing"
fi

# 8. Cron jobs
echo -n "  Cron jobs: "
CRON_COUNT=$(crontab -l 2>/dev/null | grep -c robby)
echo "${CRON_COUNT}件登録"
[ "$CRON_COUNT" -lt 8 ] && ISSUES="${ISSUES}\nCron jobs ${CRON_COUNT}/8"

# 9. agent_state.json
echo -n "  agent_state.json: "
if [ -f "$PROJECT_DIR/data/agent_state.json" ]; then
    echo "OK"
    python3 -c "
import json
with open('$PROJECT_DIR/data/agent_state.json') as f:
    state = json.load(f)
for agent in sorted(state['status'].keys()):
    status = state['status'][agent]
    last = state['lastRun'].get(agent) or 'never'
    icon = '✅' if status == 'completed' else '⏳' if status == 'pending' else '🔄' if status == 'running' else '❌'
    print(f'    {icon} {agent}: {status} (last: {last})')
"
else
    echo "MISSING"
    ISSUES="${ISSUES}\nagent_state.json missing"
fi

# 10. TikTok cookies
echo -n "  TikTok cookies: "
if [ -f "$PROJECT_DIR/TK_cookies_robby15051.json" ]; then
    echo "OK"
else
    echo "MISSING"
    ISSUES="${ISSUES}\nTikTok cookies missing"
fi

# 11. posting_queue
echo -n "  posting_queue: "
if [ -f "$PROJECT_DIR/data/posting_queue.json" ]; then
    python3 -c "
import json
with open('$PROJECT_DIR/data/posting_queue.json') as f:
    q = json.load(f)
posted = sum(1 for p in q['posts'] if p['status'] == 'posted')
pending = sum(1 for p in q['posts'] if p['status'] == 'pending')
total = len(q['posts'])
print(f'OK ({posted} posted / {pending} pending / {total} total)')
"
else
    echo "MISSING"
fi

# 12. ログディレクトリ容量
echo -n "  logs/ size: "
LOG_SIZE=$(du -sm logs/ 2>/dev/null | awk '{print $1}')
echo "${LOG_SIZE:-0}MB"

echo ""
echo "=== 検証結果 ==="
if [ -z "$ISSUES" ]; then
    echo "✅ 全チェック正常！Agent Teamは稼働可能です。"
    slack_notify "✅ Agent Team検証完了 — 全チェック正常"
else
    echo "⚠️ 問題あり:"
    echo -e "$ISSUES"
    slack_notify "⚠️ Agent Team検証 — 問題あり:$(echo -e "$ISSUES")"
fi

echo "=== 検証完了 ===" >> "$LOG"
