#!/usr/bin/env python3
"""
SEO効果 7日間レポート (2026-04-13 〜 2026-04-19)
オーガニック流入の把握 + 前週比 + SC連携 + LINE CV
"""
import os, sys, json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID")
GA4_CREDENTIALS_PATH = os.getenv("GA4_CREDENTIALS_PATH")
SC_SITE_URL = os.getenv("SC_SITE_URL", "https://quads-nurse.com/")

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Metric, Dimension, OrderBy,
    FilterExpression, Filter, FilterExpressionList,
)
from google.oauth2.service_account import Credentials

creds = Credentials.from_service_account_file(GA4_CREDENTIALS_PATH)
client = BetaAnalyticsDataClient(credentials=creds)
prop = f"properties/{GA4_PROPERTY_ID}"

CUR_START, CUR_END = "2026-04-13", "2026-04-19"
PREV_START, PREV_END = "2026-04-06", "2026-04-12"

# Organic filter: sessionSource == google AND sessionMedium == organic
# GA4 も sessionDefaultChannelGroup == "Organic Search" が安全
organic_filter = FilterExpression(
    filter=Filter(
        field_name="sessionDefaultChannelGroup",
        string_filter=Filter.StringFilter(value="Organic Search",
                                          match_type=Filter.StringFilter.MatchType.EXACT),
    )
)

def totals(start, end, dim_filter=None):
    req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="screenPageViews"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        dimension_filter=dim_filter,
    )
    resp = client.run_report(req)
    if not resp.rows:
        return {k: 0 for k in ("sessions","users","pv","bounce","dur")}
    r = resp.rows[0]
    return {
        "sessions": int(float(r.metric_values[0].value)),
        "users": int(float(r.metric_values[1].value)),
        "pv": int(float(r.metric_values[2].value)),
        "bounce": float(r.metric_values[3].value),
        "dur": float(r.metric_values[4].value),
    }

def by_channel(start, end):
    req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=10,
    )
    resp = client.run_report(req)
    return [(r.dimension_values[0].value,
             int(float(r.metric_values[0].value)),
             int(float(r.metric_values[1].value))) for r in resp.rows]

def top_landing(start, end, dim_filter=None, limit=15):
    req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[Metric(name="sessions"),
                 Metric(name="activeUsers"),
                 Metric(name="bounceRate"),
                 Metric(name="screenPageViews")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
        dimension_filter=dim_filter,
    )
    resp = client.run_report(req)
    return [{
        "page": r.dimension_values[0].value,
        "sessions": int(float(r.metric_values[0].value)),
        "users": int(float(r.metric_values[1].value)),
        "bounce": float(r.metric_values[2].value),
        "pv": int(float(r.metric_values[3].value)),
    } for r in resp.rows]

def line_events(start, end, dim_filter=None):
    """LINE click系イベント数"""
    req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount"), Metric(name="totalUsers")],
        dimension_filter=dim_filter,
    )
    resp = client.run_report(req)
    result = {}
    for r in resp.rows:
        ev = r.dimension_values[0].value
        if "line" in ev.lower() or "shindan_complete" in ev or "chat_" in ev:
            result[ev] = {
                "count": int(float(r.metric_values[0].value)),
                "users": int(float(r.metric_values[1].value)),
            }
    return result

print("=" * 70)
print(f"  SEO効果レポート  {CUR_START} 〜 {CUR_END}（7日間）")
print("=" * 70)

# 1. 全体 vs オーガニック
all_cur = totals(CUR_START, CUR_END)
org_cur = totals(CUR_START, CUR_END, organic_filter)
all_prev = totals(PREV_START, PREV_END)
org_prev = totals(PREV_START, PREV_END, organic_filter)

def delta(c, p):
    if p == 0: return "N/A" if c == 0 else "+∞%"
    return f"{(c-p)/p*100:+.1f}%"

print("\n■ 全体サマリ（当週 / 前週 / 増減）")
print(f"  全セッション  : {all_cur['sessions']:>6} / {all_prev['sessions']:>6} / {delta(all_cur['sessions'], all_prev['sessions'])}")
print(f"  全PV          : {all_cur['pv']:>6} / {all_prev['pv']:>6} / {delta(all_cur['pv'], all_prev['pv'])}")
print(f"  全ユーザー    : {all_cur['users']:>6} / {all_prev['users']:>6} / {delta(all_cur['users'], all_prev['users'])}")

print("\n■ オーガニック流入（Organic Search, 当週 / 前週 / 増減）")
print(f"  セッション    : {org_cur['sessions']:>6} / {org_prev['sessions']:>6} / {delta(org_cur['sessions'], org_prev['sessions'])}")
print(f"  PV            : {org_cur['pv']:>6} / {org_prev['pv']:>6} / {delta(org_cur['pv'], org_prev['pv'])}")
print(f"  ユーザー      : {org_cur['users']:>6} / {org_prev['users']:>6} / {delta(org_cur['users'], org_prev['users'])}")
print(f"  直帰率        : {org_cur['bounce']*100:>5.1f}% / {org_prev['bounce']*100:>5.1f}% / {delta(org_cur['bounce'], org_prev['bounce'])}")
print(f"  平均滞在秒    : {org_cur['dur']:>5.1f}s / {org_prev['dur']:>5.1f}s / {delta(org_cur['dur'], org_prev['dur'])}")

# 2. チャネル別
print("\n■ チャネル別セッション（当週）")
for name, s, u in by_channel(CUR_START, CUR_END):
    print(f"  {name:<25} {s:>5}セッション / {u:>5}ユーザー")

# 3. オーガニック LP TOP15
print("\n■ オーガニックLP TOP15（当週）")
org_lps = top_landing(CUR_START, CUR_END, organic_filter, 15)
for i, lp in enumerate(org_lps, 1):
    page = lp["page"][:55]
    print(f"  {i:>2}. {page:<55}  {lp['sessions']:>4}session  直帰{lp['bounce']*100:>4.0f}%")

# 4. SEOカテゴリ別（area / guide / blog / index）
print("\n■ SEOカテゴリ別オーガニック流入（当週）")
cats = {"area": 0, "guide": 0, "blog": 0, "lp": 0, "top/index": 0, "other": 0}
# 大きめに取得
all_org_lps = top_landing(CUR_START, CUR_END, organic_filter, 200)
for lp in all_org_lps:
    p = lp["page"]
    s = lp["sessions"]
    if "/area/" in p: cats["area"] += s
    elif "/guide/" in p: cats["guide"] += s
    elif "/blog/" in p: cats["blog"] += s
    elif "/lp/" in p: cats["lp"] += s
    elif p in ("/", "/index.html", ""): cats["top/index"] += s
    else: cats["other"] += s
total_cat = sum(cats.values()) or 1
for k, v in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {k:<12} {v:>5}session  ({v/total_cat*100:>4.1f}%)")

# 5. LINE CV (SEO経由)
print("\n■ LINE CV / ファネルイベント（当週 全チャネル vs オーガニックのみ）")
ev_all = line_events(CUR_START, CUR_END)
ev_org = line_events(CUR_START, CUR_END, organic_filter)
all_events = set(ev_all.keys()) | set(ev_org.keys())
for ev in sorted(all_events):
    a = ev_all.get(ev, {"count":0, "users":0})
    o = ev_org.get(ev, {"count":0, "users":0})
    print(f"  {ev:<25} 全体={a['count']:>4}回/{a['users']:>4}人  オーガニック={o['count']:>4}回/{o['users']:>4}人")

# 6. SEO CV率
line_cv_org = sum(v['count'] for k,v in ev_org.items() if 'line' in k.lower())
if org_cur['sessions']:
    print(f"\n■ オーガニック→LINE click率: {line_cv_org}/{org_cur['sessions']} = {line_cv_org/org_cur['sessions']*100:.2f}%")

# 7. Search Console
print("\n" + "=" * 70)
print("  Search Console 7日間")
print("=" * 70)
try:
    from googleapiclient.discovery import build
    sc_creds = Credentials.from_service_account_file(
        GA4_CREDENTIALS_PATH,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    sc = build("searchconsole", "v1", credentials=sc_creds)

    # SCは2-3日遅延 → 04-16あたりが最新
    sc_start, sc_end = "2026-04-10", "2026-04-16"
    prev_sc_start, prev_sc_end = "2026-04-03", "2026-04-09"

    summary = sc.searchanalytics().query(
        siteUrl=SC_SITE_URL,
        body={"startDate": sc_start, "endDate": sc_end, "dimensions": []},
    ).execute()
    prev_summary = sc.searchanalytics().query(
        siteUrl=SC_SITE_URL,
        body={"startDate": prev_sc_start, "endDate": prev_sc_end, "dimensions": []},
    ).execute()

    def sc_row(d):
        rs = d.get("rows", [{}])
        r = rs[0] if rs else {}
        return {
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0) * 100,
            "position": r.get("position", 0),
        }
    s_cur, s_prev = sc_row(summary), sc_row(prev_summary)
    print(f"\n■ SC サマリ ({sc_start} 〜 {sc_end}) / 前週（{prev_sc_start}〜{prev_sc_end}） / 増減")
    print(f"  クリック  : {s_cur['clicks']:>6} / {s_prev['clicks']:>6} / {delta(s_cur['clicks'], s_prev['clicks'])}")
    print(f"  表示回数  : {s_cur['impressions']:>6} / {s_prev['impressions']:>6} / {delta(s_cur['impressions'], s_prev['impressions'])}")
    print(f"  CTR       : {s_cur['ctr']:>5.2f}% / {s_prev['ctr']:>5.2f}% / {delta(s_cur['ctr'], s_prev['ctr'])}")
    print(f"  平均順位  : {s_cur['position']:>5.1f} / {s_prev['position']:>5.1f} / {delta(s_cur['position'], s_prev['position'])}")

    # Top queries
    qs = sc.searchanalytics().query(
        siteUrl=SC_SITE_URL,
        body={"startDate": sc_start, "endDate": sc_end,
              "dimensions": ["query"], "rowLimit": 15,
              "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]},
    ).execute()
    print("\n■ SC 検索クエリ TOP15")
    for r in qs.get("rows", []):
        q = r["keys"][0][:40]
        print(f"  {q:<40}  {r.get('clicks',0):>3}click / {r.get('impressions',0):>5}imp / CTR{r.get('ctr',0)*100:>4.1f}% / 順位{r.get('position',0):>4.1f}")

    # Top pages (SC)
    ps = sc.searchanalytics().query(
        siteUrl=SC_SITE_URL,
        body={"startDate": sc_start, "endDate": sc_end,
              "dimensions": ["page"], "rowLimit": 10,
              "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]},
    ).execute()
    print("\n■ SC ページ TOP10")
    for r in ps.get("rows", []):
        p = r["keys"][0].replace("https://quads-nurse.com", "")[:50]
        print(f"  {p:<50}  {r.get('clicks',0):>3}click / {r.get('impressions',0):>5}imp / 順位{r.get('position',0):>4.1f}")

except Exception as e:
    print(f"[SC ERROR] {e}")

print("\n" + "=" * 70)
print("  完了")
print("=" * 70)
