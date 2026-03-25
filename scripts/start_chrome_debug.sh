#!/bin/bash
# Chrome をリモートデバッグモードで起動する
# ig_post_meta_suite.py が CDP 経由で投稿するために必要
# 注意: Chrome Remote Desktop（port 9222）とは別ポートを使用

CHROME_APP="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_DEBUG_DIR="$HOME/chrome-debug-profile"
PORT=9223

# CDP接続テスト（既に正しく起動していればスキップ）
if curl -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; then
    echo "Chrome debug CDP already responding on port $PORT"
    exit 0
fi

# 古いデバッグプロファイルのChromeだけ停止（通常Chromeは殺さない）
pkill -f "user-data-dir=$CHROME_DEBUG_DIR" 2>/dev/null
sleep 2

# Start Chrome with debug port（通常Chromeと共存可能）
"$CHROME_APP" \
    --remote-debugging-port=$PORT \
    '--remote-allow-origins=*' \
    --user-data-dir="$CHROME_DEBUG_DIR" \
    --no-first-run \
    > /dev/null 2>&1 &

# CDP起動待ち（最大15秒）
for i in $(seq 1 15); do
    if curl -s "http://127.0.0.1:$PORT/json/version" > /dev/null 2>&1; then
        echo "Chrome debug CDP ready on port $PORT"
        exit 0
    fi
    sleep 1
done

echo "ERROR: Chrome debug failed to start on port $PORT"
exit 1
