#!/usr/bin/env python3
"""
Computer Use フォールバック用メトリクス取得スクリプト。
API取得に失敗したプラットフォームを記録し、
Claude Desktop の Computer Use で画面取得すべき対象を返す。

Usage:
  python3 scripts/computer_use/fallback_metrics.py check
  python3 scripts/computer_use/fallback_metrics.py save --platform tiktok --data '{"views": 12345}'
  python3 scripts/computer_use/fallback_metrics.py screenshot-path --name before_tiktok
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = ROOT / "data" / "metrics"
SCREENSHOTS_DIR = ROOT / "data" / "screenshots"
TODAY = datetime.now().strftime("%Y%m%d")

PLATFORMS = ["tiktok", "instagram", "ga4", "line", "meta"]

def check_missing():
    """APIで取得できなかったプラットフォームを返す"""
    missing = []
    for p in PLATFORMS:
        filepath = METRICS_DIR / f"{p}_{TODAY}.json"
        if not filepath.exists():
            missing.append(p)
        else:
            try:
                data = json.loads(filepath.read_text())
                if data.get("error"):
                    missing.append(p)
            except (json.JSONDecodeError, KeyError):
                missing.append(p)

    if missing:
        print(f"Computer Use フォールバック対象: {', '.join(missing)}")
        urls = {
            "tiktok": "https://www.tiktok.com/tiktokstudio/analytics",
            "instagram": "https://www.instagram.com/robby.for.nurse/ → プロフェッショナルダッシュボード",
            "ga4": "https://analytics.google.com/",
            "line": "https://manager.line.biz/ → 分析",
            "meta": "https://business.facebook.com/latest/insights",
        }
        for p in missing:
            print(f"  → {p}: {urls.get(p, '不明')}")
    else:
        print("全プラットフォームAPI取得成功。Computer Use不要。")

    return missing

def save_screen_data(platform, data_str):
    """Computer Useで取得したデータを保存"""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = METRICS_DIR / f"{platform}_{TODAY}.json"

    try:
        data = json.loads(data_str)
    except json.JSONDecodeError:
        data = {"raw_text": data_str}

    data["source"] = "computer_use"
    data["timestamp"] = datetime.now().isoformat()

    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"保存完了: {filepath}")

def save_screenshot(name):
    """スクショ保存パスを返す"""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOTS_DIR / f"{name}_{ts}.png"
    print(str(path))
    return str(path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["check", "save", "screenshot-path"])
    parser.add_argument("--platform", default=None)
    parser.add_argument("--data", default=None)
    parser.add_argument("--name", default="screen")
    args = parser.parse_args()

    if args.command == "check":
        check_missing()
    elif args.command == "save":
        if not args.platform or not args.data:
            print("--platform と --data が必要")
            sys.exit(1)
        save_screen_data(args.platform, args.data)
    elif args.command == "screenshot-path":
        save_screenshot(args.name)
