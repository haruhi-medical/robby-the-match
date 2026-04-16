#!/usr/bin/env python3
"""
広告パフォーマンス日次レポート v1.0
Meta広告の実績データ + ClarityリンクをまとめてSlackに送信

cron: 10 8 * * * (毎朝08:10、GA4レポートの後)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
import requests

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL_ID", "C0AEG626EUW")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT = "act_907937825198755"
CLARITY_PROJECT = "vmaobifgm0"


def fetch_meta_ads(date_str: str) -> dict:
    """Meta広告のインサイトを取得"""
    if not META_ACCESS_TOKEN:
        return {"error": "META_ACCESS_TOKEN not set"}

    # アクティブなキャンペーンを取得
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{META_AD_ACCOUNT}/insights",
        params={
            "access_token": META_ACCESS_TOKEN,
            "fields": "impressions,clicks,spend,cpc,ctr,reach,actions,cost_per_action_type",
            "time_range": json.dumps({"since": date_str, "until": date_str}),
            "level": "account",
        },
        timeout=15,
    )
    if r.status_code != 200:
        return {"error": f"API {r.status_code}"}

    data = r.json().get("data", [])
    if not data:
        return {"no_data": True}

    d = data[0]
    actions = {a["action_type"]: int(a["value"]) for a in d.get("actions", [])}
    costs = {a["action_type"]: float(a["value"]) for a in d.get("cost_per_action_type", [])}

    return {
        "impressions": int(d.get("impressions", 0)),
        "clicks": int(d.get("clicks", 0)),
        "spend": int(float(d.get("spend", 0))),
        "reach": int(d.get("reach", 0)),
        "cpc": round(float(d.get("cpc", 0))),
        "ctr": round(float(d.get("ctr", 0)), 2),
        "link_clicks": actions.get("link_click", 0),
        "lp_views": actions.get("landing_page_view", 0),
        "leads": actions.get("lead", 0),
        "video_views": actions.get("video_view", 0),
        "cpa_lead": round(costs.get("lead", 0)) if costs.get("lead") else None,
    }


def fetch_meta_ads_by_ad(date_str: str) -> list:
    """広告別のインサイト"""
    if not META_ACCESS_TOKEN:
        return []

    # アクティブキャンペーンのIDを取得
    r = requests.get(
        f"https://graph.facebook.com/v19.0/{META_AD_ACCOUNT}/campaigns",
        params={
            "access_token": META_ACCESS_TOKEN,
            "fields": "name,status",
            "filtering": json.dumps([{"field": "status", "operator": "EQUAL", "value": "ACTIVE"}]),
        },
        timeout=15,
    )
    campaigns = r.json().get("data", [])
    if not campaigns:
        return []

    campaign_id = campaigns[0]["id"]

    r = requests.get(
        f"https://graph.facebook.com/v19.0/{campaign_id}/insights",
        params={
            "access_token": META_ACCESS_TOKEN,
            "fields": "ad_name,impressions,clicks,spend,cpc,ctr,actions",
            "level": "ad",
            "time_range": json.dumps({"since": date_str, "until": date_str}),
        },
        timeout=15,
    )
    ads = []
    for ad in r.json().get("data", []):
        actions = {a["action_type"]: int(a["value"]) for a in ad.get("actions", [])}
        ads.append({
            "name": ad.get("ad_name", "?"),
            "imp": int(ad.get("impressions", 0)),
            "clicks": int(ad.get("clicks", 0)),
            "spend": int(float(ad.get("spend", 0))),
            "ctr": round(float(ad.get("ctr", 0)), 2),
            "leads": actions.get("lead", 0),
        })
    return ads


def check_line_users() -> int:
    """KVのLINE登録ユーザー数を確認（wrangler経由）"""
    try:
        import subprocess
        env = os.environ.copy()
        env.pop("CLOUDFLARE_API_TOKEN", None)
        result = subprocess.run(
            ["npx", "wrangler", "kv", "key", "list",
             "--namespace-id=c523fb0833e2482cbfc58eef8824c7b0",
             "--config", "wrangler.toml", "--remote", "--prefix=line:U"],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT / "api"), env=env,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return len(data)
    except Exception:
        pass
    return -1


def send_slack(text: str):
    """Slackに送信"""
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}", "Content-Type": "application/json"},
        json={"channel": SLACK_CHANNEL, "text": text},
        timeout=10,
    )


def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    today = datetime.now().strftime("%Y-%m-%d")

    # Meta広告データ取得
    meta = fetch_meta_ads(yesterday)
    ads = fetch_meta_ads_by_ad(yesterday)
    line_users = check_line_users()

    # レポート組み立て
    lines = [
        f"📊 *広告日次レポート* ({yesterday})",
        "━━━━━━━━━━━━━━━",
    ]

    if "error" in meta:
        lines.append(f"⚠️ Meta API: {meta['error']}")
    elif meta.get("no_data"):
        lines.append("📭 昨日の広告データなし（配信停止中？）")
    else:
        lines.append(f"💰 消化: ¥{meta['spend']:,}")
        lines.append(f"👀 リーチ: {meta['reach']:,}人 / imp: {meta['impressions']:,}")
        lines.append(f"🖱 クリック: {meta['clicks']} (CTR {meta['ctr']}%)")
        lines.append(f"💵 CPC: ¥{meta['cpc']}")
        lines.append(f"📄 LP閲覧: {meta['lp_views']}")
        lines.append(f"🎯 Lead: {meta['leads']}件" + (f" (CPA ¥{meta['cpa_lead']:,})" if meta['cpa_lead'] else ""))
        lines.append(f"🎬 動画視聴: {meta['video_views']}")

        if ads:
            lines.append("")
            lines.append("📋 *広告別*")
            for ad in ads:
                lead_str = f" 🎯{ad['leads']}" if ad['leads'] else ""
                lines.append(f"  {ad['name'][:20]}: {ad['imp']}imp / {ad['clicks']}click / ¥{ad['spend']}{lead_str}")

    lines.append("")
    lines.append(f"👥 LINE登録: {line_users}人" if line_users >= 0 else "👥 LINE登録: 確認不可")
    lines.append("")
    lines.append(f"🔍 Clarity: https://clarity.microsoft.com/projects/view/{CLARITY_PROJECT}/dashboard")
    lines.append(f"📹 録画: https://clarity.microsoft.com/projects/view/{CLARITY_PROJECT}/impressions")

    report = "\n".join(lines)
    print(report)
    send_slack(report)
    print(f"\n✅ Slack送信完了")


if __name__ == "__main__":
    main()
