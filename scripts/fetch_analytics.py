#!/usr/bin/env python3
"""神奈川ナース転職 アクセス解析集約スクリプト
GitHub Traffic API + 自前KVトラッキング + SNSデータを集約してレポート出力。
Slack送信オプション付き。

使い方:
  python3 scripts/fetch_analytics.py              # ターミナル表示
  python3 scripts/fetch_analytics.py --slack       # Slack送信
  python3 scripts/fetch_analytics.py --json        # JSON出力
"""

import json
import os
import sys
import subprocess
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"

def load_env():
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def fetch_json(url, headers=None):
    h = headers or {}
    h.setdefault("User-Agent", "NurseRobbyAnalytics/1.0")
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f"  [WARN] {url}: {e}", file=sys.stderr)
        return None

def get_github_traffic():
    """GitHub Traffic API (直近14日)"""
    token_result = subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True
    )
    token = token_result.stdout.strip() if token_result.returncode == 0 else None
    headers = {"Authorization": f"token {token}"} if token else {}

    views = fetch_json(
        "https://api.github.com/repos/Quads-Inc/robby-the-match/traffic/views",
        headers
    )
    referrers = fetch_json(
        "https://api.github.com/repos/Quads-Inc/robby-the-match/traffic/popular/referrers",
        headers
    )
    paths = fetch_json(
        "https://api.github.com/repos/Quads-Inc/robby-the-match/traffic/popular/paths",
        headers
    )

    return {
        "total_views": views.get("count", 0) if views else 0,
        "unique_visitors": views.get("uniques", 0) if views else 0,
        "daily": [
            {"date": v["timestamp"][:10], "views": v["count"], "uniques": v["uniques"]}
            for v in (views.get("views", []) if views else [])
            if v["count"] > 0
        ],
        "referrers": referrers or [],
        "paths": paths or [],
    }

def get_kv_analytics(env):
    """自前KVトラッキング（Cloudflare Worker）"""
    secret = env.get("LINE_PUSH_SECRET", "")
    if not secret:
        return None

    url = f"https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/analytics?secret={secret}&days=14"
    return fetch_json(url)

def get_sns_stats():
    """SNS投稿データ（ローカルファイル）"""
    result = {"instagram": 0, "tiktok_posted": 0, "tiktok_queued": 0, "engagement_days": 0}

    post_log = ROOT / "data" / "post_log.json"
    if post_log.exists():
        logs = json.loads(post_log.read_text())
        result["instagram"] = len([
            l for l in logs
            if isinstance(l, dict) and l.get("platform") == "instagram" and l.get("status") == "success"
        ])

    queue = ROOT / "data" / "posting_queue.json"
    if queue.exists():
        q = json.loads(queue.read_text())
        items = q.get("items", []) if isinstance(q, dict) else []
        result["tiktok_posted"] = len([i for i in items if isinstance(i, dict) and i.get("status") == "posted"])
        result["tiktok_queued"] = len([i for i in items if isinstance(i, dict) and i.get("status") in ("ready", "pending")])

    eng_log = ROOT / "data" / "engagement_log.json"
    if eng_log.exists():
        eng = json.loads(eng_log.read_text())
        result["engagement_days"] = len(eng) if isinstance(eng, list) else 0
        result["total_likes"] = sum(e.get("total_likes", 0) for e in eng if isinstance(e, dict))
        result["total_comments"] = sum(e.get("total_comments", 0) for e in eng if isinstance(e, dict))

    return result

def format_report(github, kv, sns):
    lines = []
    lines.append("=" * 50)
    lines.append("神奈川ナース転職 アクセス解析レポート")
    lines.append(f"生成: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 50)

    # GitHub Traffic
    lines.append("\n📊 サイトトラフィック（GitHub Pages・過去14日）")
    lines.append(f"  合計PV: {github['total_views']} / ユニーク: {github['unique_visitors']}人")
    if github["daily"]:
        lines.append("  日別:")
        for d in github["daily"]:
            lines.append(f"    {d['date']}: {d['views']} PV ({d['uniques']}人)")
    if github["referrers"]:
        lines.append("  流入元:")
        for r in github["referrers"]:
            lines.append(f"    {r['referrer']}: {r['count']} PV ({r['uniques']}人)")

    # KV Analytics
    if kv and kv.get("totals"):
        t = kv["totals"]
        lines.append(f"\n🔍 自前トラッキング（過去14日）")
        lines.append(f"  合計PV: {t['views']} / ユニーク: {t['unique_visitors']}人")
        lines.append(f"  チャット開封: {t['chat_opens']}回 / LINEクリック: {t['line_clicks']}回")
        if kv.get("daily"):
            lines.append("  日別:")
            for d in kv["daily"][:7]:
                lines.append(f"    {d['date']}: {d['views']} PV ({d['unique_visitors']}人) chat:{d['chat_opens']} LINE:{d['line_clicks']}")
                if d.get("top_pages"):
                    for p, c in d["top_pages"][:3]:
                        lines.append(f"      {p}: {c}")
    else:
        lines.append("\n🔍 自前トラッキング: データなし（デプロイ直後のため明日から蓄積開始）")

    # SNS
    lines.append(f"\n📱 SNS状況")
    lines.append(f"  Instagram: {sns['instagram']}本投稿済み")
    lines.append(f"  TikTok: {sns['tiktok_posted']}本投稿済み / {sns['tiktok_queued']}本キュー待ち")
    lines.append(f"  IGエンゲージメント: {sns['engagement_days']}日分 / {sns.get('total_likes',0)}いいね / {sns.get('total_comments',0)}コメント")

    # Summary
    lines.append(f"\n⚠️ 課題")
    if github["total_views"] < 10:
        lines.append("  - サイトトラフィックがほぼゼロ。SEOインデックス未完了の可能性。")
    google_refs = [r for r in github["referrers"] if r["referrer"] == "Google"]
    if not google_refs or google_refs[0]["count"] < 5:
        lines.append("  - Google検索からの流入がほぼない。インデックス促進が急務。")

    lines.append("")
    return "\n".join(lines)

def format_slack_blocks(github, kv, sns):
    text = f"*📊 神奈川ナース転職日次レポート* ({datetime.now().strftime('%Y-%m-%d')})\n\n"
    text += f"*サイト（過去14日）:* {github['total_views']} PV / {github['unique_visitors']}人\n"

    if kv and kv.get("totals"):
        t = kv["totals"]
        text += f"*自前トラッキング:* {t['views']} PV / chat {t['chat_opens']}回 / LINE {t['line_clicks']}回\n"

    text += f"*SNS:* IG {sns['instagram']}本 / TikTok {sns['tiktok_posted']}本 / エンゲ{sns.get('total_likes',0)}いいね\n"

    google_refs = [r for r in github["referrers"] if r["referrer"] == "Google"]
    google_count = google_refs[0]["count"] if google_refs else 0
    text += f"*Google流入:* {google_count}回"

    return text

def send_slack(text, env):
    token = env.get("SLACK_BOT_TOKEN", "")
    channel = env.get("SLACK_CHANNEL_ID", "C09A7U4TV4G")
    if not token:
        print("SLACK_BOT_TOKEN not set", file=sys.stderr)
        return

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps({"channel": channel, "text": text}).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
    )
    urllib.request.urlopen(req, timeout=10)
    print("Slack送信完了")

def main():
    env = load_env()

    print("GitHub Traffic取得中...", file=sys.stderr)
    github = get_github_traffic()

    print("自前KVトラッキング取得中...", file=sys.stderr)
    kv = get_kv_analytics(env)

    print("SNSデータ取得中...", file=sys.stderr)
    sns = get_sns_stats()

    if "--json" in sys.argv:
        print(json.dumps({"github": github, "kv": kv, "sns": sns}, indent=2, ensure_ascii=False))
    elif "--slack" in sys.argv:
        text = format_slack_blocks(github, kv, sns)
        send_slack(text, env)
        print(text)
    else:
        print(format_report(github, kv, sns))

if __name__ == "__main__":
    main()
