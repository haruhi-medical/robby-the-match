#!/usr/bin/env python3
"""
Slack指示受け付けスクリプト — ROBBY THE MATCH
Slackチャンネルからのメッセージを監視し、コマンドに反応する。

対応コマンド:
  !status  → 現在のプロジェクト状態をSlackに報告
  !kpi     → KPIダッシュボードを送信
  !content → 今日のコンテンツ生成状態を報告
  !seo     → SEOページの状態を報告
  !deploy  → デプロイ手順を案内
  !help    → コマンド一覧を表示

使い方:
  python3 slack_commander.py              # 通常起動（WebSocket）
  python3 slack_commander.py --poll       # ポーリングモード（Socket Mode不要）
  python3 slack_commander.py --poll --interval 5  # 5秒間隔ポーリング
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
import requests

# プロジェクトルート
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

# Slack設定
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID", "C08SKJBLW7A")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")  # Socket Mode用（任意）

if not SLACK_BOT_TOKEN:
    print("エラー: SLACK_BOT_TOKEN が.envに設定されていません")
    sys.exit(1)


# ===================================================================
# Slack API ヘルパー
# ===================================================================

def post_message(channel: str, text: str = "", blocks: list = None) -> bool:
    """Slackにメッセージを送信"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {"channel": channel}
    if blocks:
        payload["blocks"] = blocks
        payload["text"] = text or "ROBBY THE MATCH"
    else:
        payload["text"] = text

    try:
        resp = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers=headers,
            json=payload,
            timeout=15,
        )
        data = resp.json()
        if data.get("ok"):
            return True
        else:
            print(f"Slack APIエラー: {data.get('error')}")
            return False
    except Exception as e:
        print(f"送信エラー: {e}")
        return False


def get_conversation_history(channel: str, oldest: str = None, limit: int = 10) -> list:
    """チャンネルの直近メッセージを取得"""
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    params = {"channel": channel, "limit": limit}
    if oldest:
        params["oldest"] = oldest

    try:
        resp = requests.get(
            "https://slack.com/api/conversations.history",
            headers=headers,
            params=params,
            timeout=10,
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("messages", [])
        else:
            print(f"conversations.history エラー: {data.get('error')}")
            return []
    except Exception as e:
        print(f"取得エラー: {e}")
        return []


# ===================================================================
# コマンドハンドラー
# ===================================================================

def handle_status(channel: str):
    """!status — 現在のプロジェクト状態を報告"""
    # slack_report.py を呼び出す
    report_script = project_root / "scripts" / "slack_report.py"
    if report_script.exists():
        result = subprocess.run(
            [sys.executable, str(report_script), "--report", "daily"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return  # slack_report.py が直接Slackに送信済み
        else:
            post_message(channel, text=f"レポート生成エラー:\n```{result.stderr[:500]}```")
            return

    # フォールバック: 簡易ステータス
    progress_file = project_root / "PROGRESS.md"
    if progress_file.exists():
        raw = progress_file.read_text(encoding="utf-8")
        today_str = date.today().strftime("%Y-%m-%d")
        pattern = rf"## {re.escape(today_str)}.*?(?=\n---|\n## \d|\Z)"
        match = re.search(pattern, raw, re.DOTALL)
        section = match.group(0)[:2500] if match else "今日のエントリはありません。"
    else:
        section = "PROGRESS.md が見つかりません。"

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "プロジェクト状態"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": section},
        },
    ]
    post_message(channel, blocks=blocks, text="プロジェクト状態")


def handle_kpi(channel: str):
    """!kpi — KPIダッシュボードを送信"""
    report_script = project_root / "scripts" / "slack_report.py"
    if report_script.exists():
        result = subprocess.run(
            [sys.executable, str(report_script), "--report", "kpi"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return
        else:
            post_message(channel, text=f"KPIレポート生成エラー:\n```{result.stderr[:500]}```")
            return

    post_message(channel, text="slack_report.py が見つかりません。")


def handle_content(channel: str):
    """!content — 今日のコンテンツ生成状態を報告"""
    report_script = project_root / "scripts" / "slack_report.py"
    if report_script.exists():
        result = subprocess.run(
            [sys.executable, str(report_script), "--report", "content"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return
        else:
            post_message(channel, text=f"コンテンツレポート生成エラー:\n```{result.stderr[:500]}```")
            return

    post_message(channel, text="slack_report.py が見つかりません。")


def handle_seo(channel: str):
    """!seo — SEOページの状態を報告"""
    report_script = project_root / "scripts" / "slack_report.py"
    if report_script.exists():
        result = subprocess.run(
            [sys.executable, str(report_script), "--report", "seo"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return
        else:
            post_message(channel, text=f"SEOレポート生成エラー:\n```{result.stderr[:500]}```")
            return

    post_message(channel, text="slack_report.py が見つかりません。")


def handle_deploy(channel: str):
    """!deploy — デプロイ手順を案内"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "デプロイ手順ガイド"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*1. LP (Cloudflare Pages)*\n"
                    "```\n"
                    "cd ~/robby-the-match\n"
                    "git add -A && git commit -m 'deploy: LP更新'\n"
                    "git push origin main\n"
                    "# Cloudflare Pages が自動デプロイ\n"
                    "```\n\n"
                    "*2. 手動デプロイ確認*\n"
                    "```\n"
                    "# Cloudflare ダッシュボードでビルドステータスを確認\n"
                    "# https://dash.cloudflare.com/ > Pages\n"
                    "```\n\n"
                    "*3. 確認項目*\n"
                    "  - LP-A (求職者向け) 表示確認\n"
                    "  - LP-B (施設向け) 表示確認\n"
                    "  - LINE登録ボタンの動作確認\n"
                    "  - モバイル表示確認\n"
                    "  - GA4タグの発火確認 (Chrome DevTools > Network > collect)"
                ),
            },
        },
    ]
    post_message(channel, blocks=blocks, text="デプロイ手順ガイド")


def handle_help(channel: str):
    """!help — コマンド一覧を表示"""
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "ROBBY Commander コマンド一覧"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "*利用可能なコマンド:*\n\n"
                    "`!status`  — 現在のプロジェクト状態を報告\n"
                    "`!kpi`     — KPIダッシュボードを送信\n"
                    "`!content` — 今日のコンテンツ生成状態を報告\n"
                    "`!seo`     — SEOページの状態を報告\n"
                    "`!deploy`  — デプロイ手順を案内\n"
                    "`!help`    — このコマンド一覧を表示\n"
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "ROBBY THE MATCH Slack Commander v1.0",
                }
            ],
        },
    ]
    post_message(channel, blocks=blocks, text="コマンド一覧")


# コマンドマップ
COMMANDS = {
    "!status": handle_status,
    "!kpi": handle_kpi,
    "!content": handle_content,
    "!seo": handle_seo,
    "!deploy": handle_deploy,
    "!help": handle_help,
}


# ===================================================================
# メッセージ処理
# ===================================================================

def process_message(message: dict, channel: str):
    """メッセージを解析してコマンドを実行"""
    text = message.get("text", "").strip()

    # Bot自身のメッセージは無視
    if message.get("bot_id") or message.get("subtype") == "bot_message":
        return

    # コマンド検出
    for cmd, handler in COMMANDS.items():
        if text.lower().startswith(cmd):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] コマンド検出: {cmd}")
            handler(channel)
            return


# ===================================================================
# ポーリングモード
# ===================================================================

def run_polling(channel: str, interval: int = 3):
    """
    conversations.history をポーリングしてコマンドを検出する。
    Socket Mode (websocket) が使えない場合のフォールバック。
    """
    print(f"ROBBY Commander 起動 (ポーリングモード, {interval}秒間隔)")
    print(f"監視チャンネル: {channel}")
    print("終了: Ctrl+C")
    print("---")

    last_ts = str(time.time())
    processed_ts = set()

    while True:
        try:
            messages = get_conversation_history(channel, oldest=last_ts, limit=5)
            for msg in reversed(messages):
                ts = msg.get("ts", "")
                if ts in processed_ts:
                    continue
                processed_ts.add(ts)
                process_message(msg, channel)

            # 古い処理済みTSをクリーンアップ（メモリ節約）
            if len(processed_ts) > 1000:
                processed_ts.clear()

            if messages:
                last_ts = messages[0].get("ts", last_ts)

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\nCommander 終了")
            break
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(interval * 2)


# ===================================================================
# Socket Mode (slack_bolt)
# ===================================================================

def run_socket_mode():
    """
    Slack Socket Mode で起動する。
    slack_bolt がインストールされている場合に使用。
    SLACK_APP_TOKEN (xapp-...) が必要。
    """
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        print("slack_bolt が未インストールです。")
        print("  pip install slack-bolt")
        print("または --poll オプションでポーリングモードを使用してください。")
        sys.exit(1)

    if not SLACK_APP_TOKEN:
        print("エラー: SLACK_APP_TOKEN が.envに設定されていません。")
        print("Socket Modeを使用するには xapp- で始まるApp-Level Tokenが必要です。")
        print("または --poll オプションでポーリングモードを使用してください。")
        sys.exit(1)

    app = App(token=SLACK_BOT_TOKEN)

    @app.message(re.compile(r"^!(status|kpi|content|seo|deploy|help)", re.IGNORECASE))
    def handle_command(message, say):
        text = message.get("text", "").strip().lower()
        channel = message.get("channel", SLACK_CHANNEL_ID)

        for cmd, handler in COMMANDS.items():
            if text.startswith(cmd):
                print(f"[{datetime.now().strftime('%H:%M:%S')}] コマンド検出: {cmd}")
                handler(channel)
                return

    print("ROBBY Commander 起動 (Socket Mode)")
    print("終了: Ctrl+C")
    print("---")

    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()


# ===================================================================
# メイン
# ===================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ROBBY THE MATCH Slack Commander — チャンネル監視 & コマンド応答"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="ポーリングモードで起動 (Socket Mode不要)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3,
        help="ポーリング間隔（秒）(default: 3)",
    )
    parser.add_argument(
        "--channel",
        default=SLACK_CHANNEL_ID,
        help=f"監視するチャンネルID (default: {SLACK_CHANNEL_ID})",
    )

    args = parser.parse_args()

    if args.poll:
        run_polling(channel=args.channel, interval=args.interval)
    else:
        run_socket_mode()


if __name__ == "__main__":
    main()
