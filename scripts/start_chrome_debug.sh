#!/bin/bash
# Chrome をリモートデバッグモードで起動する
# ig_post_meta_suite.py が CDP 経由で投稿するために必要

CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_DEBUG_DIR="$HOME/chrome-debug-profile"
PORT=9222

# Already running check
if lsof -nP -iTCP:$PORT -sTCP:LISTEN > /dev/null 2>&1; then
    echo "Chrome debug port $PORT already listening"
    exit 0
fi

# Kill any existing Chrome
pkill -f "Google Chrome" 2>/dev/null
sleep 2

# Start Chrome with debug port
"$CHROME_APP" \
    --remote-debugging-port=$PORT \
    '--remote-allow-origins=*' \
    --user-data-dir="$CHROME_DEBUG_DIR" \
    > /dev/null 2>&1 &

echo "Chrome started with remote debugging on port $PORT"
