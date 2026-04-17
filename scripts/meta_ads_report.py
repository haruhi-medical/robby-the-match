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
        # Slack通知（API障害時に担当者が気づけるようにする）
        try:
            from slack_utils import send_message, SLACK_CHANNEL_REPORT
            send_message(SLACK_CHANNEL_REPORT, f"🚨 Meta広告レポート API失敗: {e.code} {msg[:100]}")
        except Exception:
            pass
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


def _cron_daily_report():
    """毎朝08:00 cron用: 前日データ取得→前々日比較→Block Kit送信"""
    sys.path.insert(0, str(BASE_DIR / "scripts"))
    from slack_utils import (
        send_message, SLACK_CHANNEL_REPORT,
        format_number, format_currency, format_percent, trend_emoji,
    )

    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    account = f"act_{META_AD_ACCOUNT_ID}"

    def _fetch_day(date_str):
        params = {
            "fields": "impressions,clicks,ctr,spend,actions,cost_per_action_type",
            "time_range": json.dumps({"since": date_str, "until": date_str}),
            "level": "account",
        }
        data = api_get(f"{account}/insights", params)
        rows = data.get("data", [])
        return rows[0] if rows else {}

    def _extract_cv(row):
        for a in row.get("actions", []):
            if a.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                return int(a.get("value", 0))
        return 0

    def _parse(row):
        if not row:
            return {}
        imp = int(row.get("impressions", 0))
        clk = int(row.get("clicks", 0))
        sp = float(row.get("spend", 0))
        ctr = float(row.get("ctr", 0))
        cv = _extract_cv(row)
        cpa = sp / cv if cv > 0 else None
        return {"impressions": imp, "clicks": clk, "spend": sp, "ctr": ctr, "conversions": cv, "cpa": cpa}

    print(f"[INFO] Meta cron report: {yesterday}")
    t = _parse(_fetch_day(yesterday))
    y = _parse(_fetch_day(day_before))

    if not t:
        send_message(SLACK_CHANNEL_REPORT, f"📊 Meta広告レポート {yesterday}: データなし")
        return

    fields = [
        {"type": "mrkdwn", "text": f"*費用*\n{format_currency(t['spend'])}{trend_emoji(t['spend'], y.get('spend'))}"},
        {"type": "mrkdwn", "text": f"*インプレッション*\n{format_number(t['impressions'])}{trend_emoji(t['impressions'], y.get('impressions'))}"},
        {"type": "mrkdwn", "text": f"*クリック*\n{format_number(t['clicks'])}{trend_emoji(t['clicks'], y.get('clicks'))}"},
        {"type": "mrkdwn", "text": f"*CTR*\n{format_percent(t['ctr'])}{trend_emoji(t['ctr'], y.get('ctr'))}"},
        {"type": "mrkdwn", "text": f"*CV (LINE登録)*\n{format_number(t['conversions'])}{trend_emoji(t['conversions'], y.get('conversions'))}"},
        {"type": "mrkdwn", "text": f"*CPA*\n{format_currency(t['cpa']) if t['cpa'] else '-'}{trend_emoji(t.get('cpa'), y.get('cpa'))}"},
    ]
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📊 Meta広告レポート {yesterday}"}},
        {"type": "section", "fields": fields},
    ]

    # キャンペーン別
    camp_params = {
        "fields": "campaign_name,impressions,clicks,spend,actions",
        "time_range": json.dumps({"since": yesterday, "until": yesterday}),
        "level": "campaign", "limit": 20,
    }
    camp_data = api_get(f"{account}/insights", camp_params).get("data", [])
    if camp_data:
        lines = []
        for c in camp_data:
            cn = c.get("campaign_name", "?")
            cs = float(c.get("spend", 0))
            ci = int(c.get("impressions", 0))
            cc = int(c.get("clicks", 0))
            ccv = _extract_cv(c)
            lines.append(f"• *{cn}*: ¥{cs:,.0f} | {ci:,}imp | {cc}click | {ccv}CV")
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*キャンペーン別内訳*\n" + "\n".join(lines)}})

    # ── 深掘り分析 ──

    # 年齢×性別
    age_params = {
        "fields": "impressions,clicks,spend,ctr",
        "time_range": json.dumps({"since": yesterday, "until": yesterday}),
        "breakdowns": "age,gender", "level": "account",
    }
    age_data = api_get(f"{account}/insights", age_params).get("data", [])
    if age_data:
        age_lines = []
        for r in sorted(age_data, key=lambda x: int(x.get("impressions", 0)), reverse=True):
            g = "♀" if r.get("gender") == "female" else "♂"
            age = r.get("age", "?")
            imp = int(r.get("impressions", 0))
            clk = int(r.get("clicks", 0))
            sp = float(r.get("spend", 0))
            ctr = float(r.get("ctr", 0))
            reliable = "✅" if imp >= 100 else "⚠️" if imp >= 30 else "❌"
            age_lines.append(f"{reliable} {g}{age}: {imp}imp / {clk}click / CTR{ctr:.1f}% / ¥{sp:,.0f}")
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*👥 年齢×性別（信憑性付き）*\n" + "\n".join(age_lines)}})

    # 配置別
    place_params = {
        "fields": "impressions,clicks,spend,ctr",
        "time_range": json.dumps({"since": yesterday, "until": yesterday}),
        "breakdowns": "publisher_platform,platform_position", "level": "account",
    }
    place_data = api_get(f"{account}/insights", place_params).get("data", [])
    if place_data:
        place_lines = []
        for r in sorted(place_data, key=lambda x: int(x.get("impressions", 0)), reverse=True):
            plat = r.get("publisher_platform", "?")
            pos = r.get("platform_position", "?")
            imp = int(r.get("impressions", 0))
            clk = int(r.get("clicks", 0))
            sp = float(r.get("spend", 0))
            ctr = float(r.get("ctr", 0))
            reliable = "✅" if imp >= 100 else "⚠️" if imp >= 30 else "❌"
            place_lines.append(f"{reliable} {plat}/{pos}: {imp}imp / {clk}click / CTR{ctr:.1f}% / ¥{sp:,.0f}")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*📍 配置別*\n" + "\n".join(place_lines[:8])}})

    # 広告別 動画視聴
    video_params = {
        "fields": "ad_name,impressions,clicks,spend,ctr,video_p25_watched_actions,video_p50_watched_actions,video_p75_watched_actions,video_p100_watched_actions",
        "time_range": json.dumps({"since": yesterday, "until": yesterday}),
        "level": "ad",
    }
    video_data = api_get(f"{account}/insights", video_params).get("data", [])
    if video_data:
        video_lines = []
        for r in video_data:
            name = r.get("ad_name", "?")
            imp = int(r.get("impressions", 0))
            clk = int(r.get("clicks", 0))
            ctr = float(r.get("ctr", 0))
            p25 = sum(int(v.get("value", 0)) for v in r.get("video_p25_watched_actions", []))
            p50 = sum(int(v.get("value", 0)) for v in r.get("video_p50_watched_actions", []))
            p75 = sum(int(v.get("value", 0)) for v in r.get("video_p75_watched_actions", []))
            p100 = sum(int(v.get("value", 0)) for v in r.get("video_p100_watched_actions", []))
            completion = f"{p100/p25*100:.0f}%" if p25 > 0 else "-"
            dropout_25_50 = f"{(p25-p50)/p25*100:.0f}%" if p25 > 0 else "-"
            video_lines.append(f"*{name}*: {imp}imp CTR{ctr:.1f}%")
            video_lines.append(f"  視聴: 25%={p25} → 50%={p50} → 75%={p75} → 完走={p100} (完走率{completion})")
            video_lines.append(f"  最大離脱: 25%→50%で{dropout_25_50}離脱")
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*🎬 動画視聴分析*\n" + "\n".join(video_lines)}})

    # 信憑性・判断の注意
    total_imp = t.get("impressions", 0)
    total_clk = t.get("clicks", 0)
    credibility = "🟢 判断可能" if total_imp >= 1000 and total_clk >= 30 else "🟡 傾向のみ" if total_imp >= 300 else "🔴 データ不足（判断不可）"
    blocks.append({"type": "divider"})
    blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
        f"*📐 データ信憑性: {credibility}*\n"
        f"表示{total_imp:,} / クリック{total_clk} — 統計的に有意な判断には表示1,000+/クリック30+が必要\n"
        f"_各行の ✅=100imp以上(信頼可) ⚠️=30-99(傾向のみ) ❌=30未満(判断不可)_"
    }})

    # ── 自動判定（閾値ベース警告）──
    alerts = _auto_judge(account, yesterday)
    if alerts:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
            "*🤖 自動判定アラート*\n" + "\n".join(alerts)
        }})

    fb = f"📊 Meta広告 {yesterday}: ¥{t['spend']:,.0f} / {t['impressions']:,}imp / CTR {t['ctr']:.2f}%"
    result = send_message(SLACK_CHANNEL_REPORT, fb, blocks=blocks)
    print(f"[{'OK' if result['ok'] else 'ERROR'}] Slack送信")


def _auto_judge(account, yesterday):
    """自動判定: CPA異常/クリエイティブ疲労/配信異常を検知してアラート返す

    閾値設計（CLAUDE.md準拠）:
      CPA > ¥69,200: 🔴 停止推奨
      CPA > ¥10,000: 🟡 要確認
      CPA < ¥2,000 (3日連続): 🟢 増額候補
      CTR 14日 → 7日で -20%以上: 🟡 クリエイティブ疲労
      Lead (CompleteRegistration) 0件が3日連続: 🔴 計測 or 配信異常
    """
    alerts = []

    # 過去7日と過去14日の CPA/CTR を比較
    def _fetch_range(start, end, level='account', extra_fields=None):
        fields = ['impressions', 'clicks', 'spend', 'ctr', 'actions']
        if extra_fields:
            fields.extend(extra_fields)
        params = {
            'fields': ','.join(fields),
            'time_range': json.dumps({'since': start, 'until': end}),
            'level': level,
        }
        return api_get(f'{account}/insights', params).get('data', [])

    def _extract_reg(row):
        """CompleteRegistration (本物のLINE登録) 取得"""
        for a in row.get('actions', []):
            if a.get('action_type') in ('complete_registration', 'offsite_conversion.fb_pixel_complete_registration'):
                return int(a.get('value', 0))
        return 0

    def _extract_lead(row):
        for a in row.get('actions', []):
            if a.get('action_type') in ('lead', 'offsite_conversion.fb_pixel_lead'):
                return int(a.get('value', 0))
        return 0

    end_7d = yesterday
    start_7d = (datetime.strptime(yesterday, '%Y-%m-%d') - timedelta(days=6)).strftime('%Y-%m-%d')
    end_14d = (datetime.strptime(yesterday, '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')
    start_14d = (datetime.strptime(yesterday, '%Y-%m-%d') - timedelta(days=13)).strftime('%Y-%m-%d')

    try:
        d7 = _fetch_range(start_7d, end_7d)
        d14 = _fetch_range(start_14d, end_14d)
    except Exception as e:
        return [f'⚠️ 自動判定エラー: {e}']

    # 7日サマリ
    if d7:
        r7 = d7[0]
        imp7 = int(r7.get('impressions', 0))
        clk7 = int(r7.get('clicks', 0))
        sp7 = float(r7.get('spend', 0))
        reg7 = _extract_reg(r7)
        lead7 = _extract_lead(r7)
        cpa_reg = sp7 / reg7 if reg7 > 0 else None
        cpa_lead = sp7 / lead7 if lead7 > 0 else None
        ctr7 = float(r7.get('ctr', 0))

        # CPA判定 (本物Lead = CompleteRegistration優先)
        if cpa_reg is not None:
            if cpa_reg > 69200:
                alerts.append(f'🔴 CPA(登録) ¥{cpa_reg:,.0f} > ¥69,200 — 停止推奨ライン')
            elif cpa_reg > 10000:
                alerts.append(f'🟡 CPA(登録) ¥{cpa_reg:,.0f} > ¥10,000 — 要確認')
            elif cpa_reg < 2000:
                alerts.append(f'🟢 CPA(登録) ¥{cpa_reg:,.0f} < ¥2,000 — 増額候補')
        else:
            if sp7 >= 10000 and reg7 == 0:
                alerts.append(f'🔴 7日間 ¥{sp7:,.0f} 消化で登録0件 — 計測 or 配信異常')
            elif reg7 == 0 and sp7 > 0:
                alerts.append(f'🟡 CompleteRegistration イベント未観測 (¥{sp7:,.0f} 消化)')

        # Pixel Lead (CTAクリック) も参考表示
        if cpa_lead is not None:
            alerts.append(f'ℹ️ CPL(Pixel Lead = CTAクリック) ¥{cpa_lead:,.0f} / {lead7}件 — 参考値')

        # CTR疲労検知
        if d14:
            r14 = d14[0]
            ctr14 = float(r14.get('ctr', 0))
            if ctr14 > 0 and ctr7 < ctr14 * 0.8:
                drop_pct = (1 - ctr7 / ctr14) * 100
                alerts.append(f'🟡 CTR疲労検知 7日 {ctr7:.2f}% < 先週 {ctr14:.2f}% ({drop_pct:.0f}%↓) — クリエイティブ差し替え検討')

    # 直近3日連続でCompleteRegistration 0件か確認
    zero_days = 0
    for i in range(3):
        d = (datetime.strptime(yesterday, '%Y-%m-%d') - timedelta(days=i)).strftime('%Y-%m-%d')
        try:
            rows = _fetch_range(d, d)
            if rows and _extract_reg(rows[0]) == 0 and float(rows[0].get('spend', 0)) > 500:
                zero_days += 1
        except Exception:
            pass
    if zero_days >= 3:
        alerts.append('🔴 3日連続 CompleteRegistration=0 (¥500以上消化) — 計測壊れ or ターゲティング破綻の可能性')

    if not alerts:
        alerts.append('✅ 閾値内 — 現状維持でOK')

    return alerts


def main():
    parser = argparse.ArgumentParser(description="Meta広告パフォーマンスレポート")
    parser.add_argument("--days", type=int, default=7, help="取得日数（デフォルト7日）")
    parser.add_argument("--daily", action="store_true", help="日別ブレイクダウン")
    parser.add_argument("--slack", action="store_true", help="Slackに送信")
    parser.add_argument("--cron", action="store_true", help="cron用: 前日レポートをBlock Kit送信")
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

    if args.cron:
        _cron_daily_report()
        return

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
