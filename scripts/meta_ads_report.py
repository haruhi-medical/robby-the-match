#!/usr/bin/env python3
"""
Meta Marketing API — 広告パフォーマンスレポート
Usage:
  python3 scripts/meta_ads_report.py                    # 直近7日のサマリ
  python3 scripts/meta_ads_report.py --days 3            # 直近3日
  python3 scripts/meta_ads_report.py --daily             # 日別ブレイクダウン
  python3 scripts/meta_ads_report.py --slack              # Slackにレポート送信
  python3 scripts/meta_ads_report.py --daily --slack      # 日別レポートをSlackに
  python3 scripts/meta_ads_report.py --setup              # トークン交換（初回セットアップ）
"""
import os
import sys
import json
import argparse
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# .env読み込み
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

BASE_DIR = Path(__file__).parent.parent
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID", "")
META_APP_ID = os.environ.get("META_APP_ID", "")
META_APP_SECRET = os.environ.get("META_APP_SECRET", "")
API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def api_get(endpoint, params=None):
    """Meta Graph API GETリクエスト"""
    import urllib.request
    import urllib.parse

    if params is None:
        params = {}
    params["access_token"] = META_ACCESS_TOKEN

    url = f"{BASE_URL}/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            error_json = json.loads(error_body)
            msg = error_json.get("error", {}).get("message", error_body)
        except Exception:
            msg = error_body
        print(f"❌ API Error ({e.code}): {msg}", file=sys.stderr)
        sys.exit(1)


def get_ad_accounts():
    """広告アカウント一覧取得"""
    data = api_get("me/adaccounts", {"fields": "name,account_id,account_status,currency"})
    return data.get("data", [])


def get_campaigns():
    """キャンペーン一覧取得"""
    account = f"act_{META_AD_ACCOUNT_ID}"
    data = api_get(f"{account}/campaigns", {
        "fields": "name,status,objective,daily_budget,lifetime_budget",
        "limit": 50,
    })
    return data.get("data", [])


def get_insights(days=7, daily=False):
    """パフォーマンスデータ取得"""
    account = f"act_{META_AD_ACCOUNT_ID}"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "fields": ",".join([
            "campaign_name", "adset_name", "ad_name",
            "impressions", "reach", "clicks", "spend",
            "cpc", "cpm", "ctr", "cpp",
            "actions", "cost_per_action_type",
        ]),
        "time_range": json.dumps({"since": start_date, "until": end_date}),
        "level": "ad",
    }

    if daily:
        params["time_increment"] = "1"

    data = api_get(f"{account}/insights", params)
    return data.get("data", [])


def get_ad_level_insights(days=7):
    """広告レベルの詳細データ"""
    account = f"act_{META_AD_ACCOUNT_ID}"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    params = {
        "fields": ",".join([
            "campaign_name", "adset_name", "ad_name",
            "impressions", "reach", "clicks", "spend",
            "cpc", "ctr",
            "actions", "cost_per_action_type",
        ]),
        "time_range": json.dumps({"since": start_date, "until": end_date}),
        "level": "ad",
    }
    data = api_get(f"{account}/insights", params)
    return data.get("data", [])


def format_report(insights, daily=False):
    """レポートをフォーマット"""
    if not insights:
        return "📊 データなし（広告がまだ配信されていないか、期間内にデータがありません）"

    lines = ["📊 *Meta広告パフォーマンスレポート*", ""]

    total_impressions = 0
    total_clicks = 0
    total_spend = 0.0

    for row in insights:
        impressions = int(row.get("impressions", 0))
        clicks = int(row.get("clicks", 0))
        spend = float(row.get("spend", 0))
        ctr = row.get("ctr", "0")
        cpc = row.get("cpc", "0")
        reach = int(row.get("reach", 0))

        total_impressions += impressions
        total_clicks += clicks
        total_spend += spend

        # Leadアクション抽出
        leads = 0
        actions = row.get("actions", [])
        for action in actions:
            if action.get("action_type") in ["lead", "offsite_conversion.fb_pixel_lead"]:
                leads += int(action.get("value", 0))

        date_str = ""
        if daily and "date_start" in row:
            date_str = f"📅 {row['date_start']} | "

        ad_name = row.get("ad_name", row.get("campaign_name", "不明"))
        lines.append(f"{date_str}*{ad_name}*")
        lines.append(f"  表示: {impressions:,} | リーチ: {reach:,} | クリック: {clicks}")
        lines.append(f"  消化: ¥{spend:,.0f} | CPC: ¥{float(cpc):,.1f} | CTR: {float(ctr):.2f}%")
        if leads > 0:
            lines.append(f"  🎯 Lead: {leads}件")
        lines.append("")

    # サマリ
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
    avg_cpc = (total_spend / total_clicks) if total_clicks > 0 else 0

    lines.append("━━━ 合計 ━━━")
    lines.append(f"表示: {total_impressions:,} | クリック: {total_clicks} | 消化: ¥{total_spend:,.0f}")
    lines.append(f"平均CTR: {avg_ctr:.2f}% | 平均CPC: ¥{avg_cpc:,.1f}")

    # 判定
    lines.append("")
    if avg_ctr >= 1.0:
        lines.append("✅ CTR良好（1%以上）")
    elif avg_ctr >= 0.5:
        lines.append("🟡 CTR要改善（0.5-1.0%）")
    elif total_impressions > 0:
        lines.append("🔴 CTR要対策（0.5%未満）")

    return "\n".join(lines)


def send_slack(message):
    """Slackに送信"""
    try:
        subprocess.run(
            ["python3", str(BASE_DIR / "scripts" / "slack_bridge.py"), "--send", message],
            check=True, capture_output=True, timeout=15
        )
        print("✅ Slackに送信完了")
    except Exception as e:
        print(f"⚠️ Slack送信失敗: {e}", file=sys.stderr)


def exchange_token():
    """Short-lived → Long-lived トークン交換"""
    if not META_APP_ID or not META_APP_SECRET:
        print("❌ META_APP_ID と META_APP_SECRET を .env に設定してください")
        sys.exit(1)

    import urllib.request
    import urllib.parse

    params = urllib.parse.urlencode({
        "grant_type": "fb_exchange_token",
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "fb_exchange_token": META_ACCESS_TOKEN,
    })

    url = f"{BASE_URL}/oauth/access_token?{params}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            new_token = data.get("access_token", "")
            expires_in = data.get("expires_in", 0)
            days = expires_in // 86400

            print(f"✅ Long-lived Token取得成功（有効期限: {days}日）")
            print(f"\n以下を .env の META_ACCESS_TOKEN に設定してください:\n")
            print(new_token)
            print(f"\n⚠️ 期限: {(datetime.now() + timedelta(seconds=expires_in)).strftime('%Y-%m-%d')}")
            return new_token
    except Exception as e:
        print(f"❌ トークン交換失敗: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Meta広告パフォーマンスレポート")
    parser.add_argument("--days", type=int, default=7, help="取得日数（デフォルト7日）")
    parser.add_argument("--daily", action="store_true", help="日別ブレイクダウン")
    parser.add_argument("--slack", action="store_true", help="Slackに送信")
    parser.add_argument("--accounts", action="store_true", help="広告アカウント一覧")
    parser.add_argument("--campaigns", action="store_true", help="キャンペーン一覧")
    parser.add_argument("--setup", action="store_true", help="Long-livedトークンに交換")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    args = parser.parse_args()

    if not META_ACCESS_TOKEN:
        print("❌ META_ACCESS_TOKEN が未設定です")
        print("  1. https://developers.facebook.com/tools/explorer/ でトークン生成")
        print("  2. .env に META_ACCESS_TOKEN=xxx を追加")
        sys.exit(1)

    if args.setup:
        exchange_token()
        return

    if args.accounts:
        accounts = get_ad_accounts()
        for acc in accounts:
            status = "✅" if acc.get("account_status") == 1 else "❌"
            print(f"{status} {acc.get('name', 'N/A')} (ID: {acc.get('account_id')}, {acc.get('currency', 'N/A')})")
        return

    if args.campaigns:
        if not META_AD_ACCOUNT_ID:
            print("❌ META_AD_ACCOUNT_ID が未設定です。--accounts で確認してください")
            sys.exit(1)
        campaigns = get_campaigns()
        for c in campaigns:
            budget = int(c.get("daily_budget", 0)) / 100 if c.get("daily_budget") else "N/A"
            print(f"{'🟢' if c.get('status') == 'ACTIVE' else '⏸'} {c.get('name')} | {c.get('objective')} | ¥{budget}/日")
        return

    if not META_AD_ACCOUNT_ID:
        print("❌ META_AD_ACCOUNT_ID が未設定です")
        print("  1. python3 scripts/meta_ads_report.py --accounts でID確認")
        print("  2. .env に META_AD_ACCOUNT_ID=XXXXXXX を追加（act_は不要）")
        sys.exit(1)

    insights = get_insights(days=args.days, daily=args.daily)

    if args.json:
        print(json.dumps(insights, indent=2, ensure_ascii=False))
        return

    report = format_report(insights, daily=args.daily)
    print(report)

    if args.slack:
        send_slack(report)


if __name__ == "__main__":
    main()
