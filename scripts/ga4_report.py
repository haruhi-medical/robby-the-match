#!/usr/bin/env python3
"""
GA4 + Search Console 日次レポート v1.0
GA4 Data API でサイトデータを取得し、Slackに送信。
cron: 5 8 * * * (毎朝08:05)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from slack_utils import (
    send_message, SLACK_CHANNEL_REPORT,
    format_number, format_percent, trend_emoji,
)

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GA4_CREDENTIALS_PATH = os.getenv("GA4_CREDENTIALS_PATH", "")
SC_SITE_URL = os.getenv("SC_SITE_URL", "https://quads-nurse.com/")


def fetch_ga4(yesterday: str, day_before: str) -> dict:
    """GA4 Data APIでデータ取得"""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension, OrderBy,
        )
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("[WARN] google-analytics-data未インストール", file=sys.stderr)
        return {}

    if not GA4_PROPERTY_ID or not GA4_CREDENTIALS_PATH:
        print("[WARN] GA4_PROPERTY_ID / GA4_CREDENTIALS_PATH 未設定", file=sys.stderr)
        return {}

    creds = Credentials.from_service_account_file(GA4_CREDENTIALS_PATH)
    client = BetaAnalyticsDataClient(credentials=creds)
    property_id = f"properties/{GA4_PROPERTY_ID}"

    # 基本メトリクス（前日 + 前々日）
    basic_metrics = [
        Metric(name="activeUsers"),
        Metric(name="sessions"),
        Metric(name="screenPageViews"),
        Metric(name="newUsers"),
        Metric(name="averageSessionDuration"),
        Metric(name="bounceRate"),
    ]

    def _run_basic(date_str):
        req = RunReportRequest(
            property=property_id,
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            metrics=basic_metrics,
        )
        resp = client.run_report(req)
        if resp.rows:
            row = resp.rows[0]
            return {m.name: float(v.value) for m, v in zip(basic_metrics, row.metric_values)}
        return {}

    today_data = _run_basic(yesterday)
    prev_data = _run_basic(day_before)

    # 流入元TOP5
    source_req = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
        dimensions=[Dimension(name="sessionSource")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=5,
    )
    source_resp = client.run_report(source_req)
    sources = []
    for row in source_resp.rows:
        sources.append({
            "source": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
            "users": int(row.metric_values[1].value),
        })

    # LP TOP5
    lp_req = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=5,
    )
    lp_resp = client.run_report(lp_req)
    landing_pages = []
    for row in lp_resp.rows:
        landing_pages.append({
            "page": row.dimension_values[0].value,
            "sessions": int(row.metric_values[0].value),
        })

    # モバイルのみ（実ユーザー推定）
    from google.analytics.data_v1beta.types import FilterExpression, Filter
    mobile_filter = FilterExpression(
        filter=Filter(
            field_name="deviceCategory",
            string_filter=Filter.StringFilter(value="mobile", match_type=Filter.StringFilter.MatchType.EXACT),
        )
    )

    mobile_req = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="screenPageViews")],
        dimension_filter=mobile_filter,
    )
    mobile_resp = client.run_report(mobile_req)
    mobile_data = {}
    if mobile_resp.rows:
        row = mobile_resp.rows[0]
        mobile_data = {
            "sessions": int(float(row.metric_values[0].value)),
            "users": int(float(row.metric_values[1].value)),
            "pv": int(float(row.metric_values[2].value)),
        }

    # 診断ファネルイベント（モバイルのみ）
    funnel_events = ["shindan_start", "shindan_q1", "shindan_complete", "shindan_line_click",
                     "chat_open", "chat_line_click", "line_click"]
    funnel_req = RunReportRequest(
        property=property_id,
        date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
        metrics=[Metric(name="eventCount"), Metric(name="totalUsers")],
        dimensions=[Dimension(name="eventName")],
        dimension_filter=mobile_filter,
    )
    funnel_resp = client.run_report(funnel_req)
    funnel = {}
    for row in funnel_resp.rows:
        ev = row.dimension_values[0].value
        if ev in funnel_events:
            funnel[ev] = {
                "count": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
            }

    return {
        "today": today_data,
        "prev": prev_data,
        "sources": sources,
        "landing_pages": landing_pages,
        "mobile": mobile_data,
        "funnel": funnel,
    }


def fetch_search_console() -> dict:
    """Search Console APIでデータ取得（3日前のデータ）"""
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("[WARN] googleapiclient未インストール", file=sys.stderr)
        return {}

    if not GA4_CREDENTIALS_PATH:
        return {}

    creds = Credentials.from_service_account_file(
        GA4_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=creds)

    # 3日前のデータ（SC はデータ遅延あり）
    target_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")

    # サマリー
    try:
        summary = service.searchanalytics().query(
            siteUrl=SC_SITE_URL,
            body={"startDate": target_date, "endDate": target_date, "dimensions": []},
        ).execute()
    except Exception as e:
        print(f"[WARN] SC API error: {e}", file=sys.stderr)
        return {}

    summary_row = summary.get("rows", [{}])[0] if summary.get("rows") else {}

    # クエリTOP10
    try:
        queries_resp = service.searchanalytics().query(
            siteUrl=SC_SITE_URL,
            body={
                "startDate": target_date,
                "endDate": target_date,
                "dimensions": ["query"],
                "rowLimit": 10,
                "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
            },
        ).execute()
    except Exception:
        queries_resp = {}

    queries = []
    for row in queries_resp.get("rows", []):
        queries.append({
            "query": row["keys"][0],
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "position": round(row.get("position", 0), 1),
        })

    return {
        "date": target_date,
        "summary": {
            "clicks": summary_row.get("clicks", 0),
            "impressions": summary_row.get("impressions", 0),
            "ctr": summary_row.get("ctr", 0) * 100,
            "position": round(summary_row.get("position", 0), 1),
        },
        "queries": queries,
    }


def build_blocks(ga4: dict, sc: dict, date_str: str) -> list:
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"📈 サイトレポート {date_str}"}},
    ]

    # GA4セクション
    t = ga4.get("today", {})
    p = ga4.get("prev", {})
    if t:
        ga4_fields = [
            {"type": "mrkdwn", "text": f"*アクティブユーザー*\n{format_number(t.get('activeUsers', 0))}{trend_emoji(t.get('activeUsers'), p.get('activeUsers'))}"},
            {"type": "mrkdwn", "text": f"*セッション*\n{format_number(t.get('sessions', 0))}{trend_emoji(t.get('sessions'), p.get('sessions'))}"},
            {"type": "mrkdwn", "text": f"*PV*\n{format_number(t.get('screenPageViews', 0))}{trend_emoji(t.get('screenPageViews'), p.get('screenPageViews'))}"},
            {"type": "mrkdwn", "text": f"*新規ユーザー*\n{format_number(t.get('newUsers', 0))}{trend_emoji(t.get('newUsers'), p.get('newUsers'))}"},
            {"type": "mrkdwn", "text": f"*平均滞在*\n{t.get('averageSessionDuration', 0):.0f}秒{trend_emoji(t.get('averageSessionDuration'), p.get('averageSessionDuration'))}"},
            {"type": "mrkdwn", "text": f"*直帰率*\n{format_percent(t.get('bounceRate', 0))}{trend_emoji(t.get('bounceRate'), p.get('bounceRate'))}"},
        ]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*📊 GA4 (前日)*"}})
        blocks.append({"type": "section", "fields": ga4_fields})

    # 流入元TOP5
    sources = ga4.get("sources", [])
    if sources:
        src_lines = [f"• *{s['source']}*: {s['sessions']}セッション / {s['users']}ユーザー" for s in sources]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*流入元TOP5*\n" + "\n".join(src_lines)}})

    # LP TOP5
    lps = ga4.get("landing_pages", [])
    if lps:
        lp_lines = [f"• `{l['page'][:50]}`: {l['sessions']}セッション" for l in lps]
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*LP TOP5*\n" + "\n".join(lp_lines)}})

    # モバイル実ユーザー
    mobile = ga4.get("mobile", {})
    if mobile:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
            f"*📱 実ユーザー（モバイルのみ）*\n"
            f"ユーザー: *{mobile.get('users', 0)}人* | セッション: {mobile.get('sessions', 0)} | PV: {mobile.get('pv', 0)}"
        }})

    # 診断ファネル
    funnel = ga4.get("funnel", {})
    if funnel:
        funnel_lines = []
        for ev, label in [
            ("shindan_start", "診断開始"),
            ("shindan_q1", "Q1回答"),
            ("shindan_complete", "診断完了"),
            ("shindan_line_click", "LINE click（診断）"),
            ("chat_open", "チャット開封"),
            ("chat_line_click", "LINE click（チャット）"),
            ("line_click", "LINE click（その他）"),
        ]:
            if ev in funnel:
                d = funnel[ev]
                funnel_lines.append(f"• *{label}*: {d['count']}回 ({d['users']}人)")
        if funnel_lines:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
                "*🔄 診断ファネル（モバイル実ユーザー）*\n" + "\n".join(funnel_lines)
            }})

    # Search Console セクション
    if sc:
        blocks.append({"type": "divider"})
        s = sc.get("summary", {})
        sc_text = (
            f"*🔍 Search Console ({sc.get('date', '?')})*\n"
            f"クリック: {s.get('clicks', 0)} | 表示: {format_number(s.get('impressions', 0))} | "
            f"CTR: {format_percent(s.get('ctr', 0))} | 平均順位: {s.get('position', '-')}"
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": sc_text}})

        queries = sc.get("queries", [])
        if queries:
            q_lines = [f"• *{q['query']}*: {q['clicks']}click / {q['impressions']}imp / 順位{q['position']}" for q in queries[:10]]
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "*検索クエリTOP10*\n" + "\n".join(q_lines)}})

    return blocks


def main():
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    day_before = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")

    print(f"[INFO] サイトレポート取得: {yesterday}")

    ga4_data = fetch_ga4(yesterday, day_before)
    sc_data = fetch_search_console()

    if not ga4_data.get("today") and not sc_data:
        send_message(SLACK_CHANNEL_REPORT, f"📈 サイトレポート {yesterday}: データ取得失敗（認証情報を確認してください）")
        print("[WARN] データなし")
        return

    blocks = build_blocks(ga4_data, sc_data, yesterday)
    fallback = f"📈 サイトレポート {yesterday}"
    if ga4_data.get("today"):
        t = ga4_data["today"]
        fallback += f": {t.get('activeUsers', 0):.0f}ユーザー / {t.get('sessions', 0):.0f}セッション"

    result = send_message(SLACK_CHANNEL_REPORT, fallback, blocks=blocks)
    print(f"[{'OK' if result['ok'] else 'ERROR'}] Slack送信")


if __name__ == "__main__":
    main()
