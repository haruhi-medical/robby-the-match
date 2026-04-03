#!/bin/bash
# kill_zombie_chrome.sh — Playwright Chrome for Testing ゾンビプロセス自動kill
# 30分以上生存しているChrome for Testingプロセスを強制終了する
# cron: 毎時実行推奨

LOG="/tmp/kill_zombie_chrome.log"
THRESHOLD_SEC=1800  # 30分

now=$(date +%s)
killed=0

# Chrome for Testing の親プロセス（--no-startup-window付き）のPIDを取得
for pid in $(pgrep -f "Google Chrome for Testing.*--no-startup-window"); do
    # プロセス起動時刻を取得（macOS: ps -o lstart）
    start_time=$(ps -o lstart= -p "$pid" 2>/dev/null)
    if [ -z "$start_time" ]; then
        continue
    fi

    start_epoch=$(date -j -f "%a %b %d %T %Y" "$start_time" +%s 2>/dev/null)
    if [ -z "$start_epoch" ]; then
        continue
    fi

    age=$(( now - start_epoch ))
    if [ "$age" -gt "$THRESHOLD_SEC" ]; then
        # 親プロセスのuser-data-dirを特定
        user_data_dir=$(ps -o args= -p "$pid" | grep -o 'user-data-dir=[^ ]*' | head -1)
        echo "$(date '+%Y-%m-%d %H:%M:%S') Killing zombie Chrome for Testing (PID=$pid, age=${age}s, $user_data_dir)" >> "$LOG"

        # 親プロセスのプロセスグループごとkill
        kill -TERM "$pid" 2>/dev/null

        # 同じuser-data-dirの子プロセスもkill
        if [ -n "$user_data_dir" ]; then
            dir_path=$(echo "$user_data_dir" | sed 's/user-data-dir=//')
            for child in $(pgrep -f "$dir_path"); do
                kill -TERM "$child" 2>/dev/null
            done
        fi

        killed=$((killed + 1))
    fi
done

# tmpのplaywright profileディレクトリも掃除（1時間以上古いもの）
find /tmp -maxdepth 1 -name "playwright_chromiumdev_profile-*" -type d -mmin +60 -exec rm -rf {} \; 2>/dev/null

if [ "$killed" -gt 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Killed $killed zombie Chrome for Testing instance(s)" >> "$LOG"
fi
