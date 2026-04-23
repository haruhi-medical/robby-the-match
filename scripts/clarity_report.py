#!/usr/bin/env python3
"""
Microsoft Clarity Data Export API → Slack日次レポート

API docs: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-data-export-api
制約: 10 queries/日・numOfDays 1-3 (直近3日まで)・projectId 紐付け

Usage:
  python3 scripts/clarity_report.py                # 前日ベースで Slack 送信
  python3 scripts/clarity_report.py --days 3       # 直近3日
  python3 scripts/clarity_report.py --stdout       # Slack送らず標準出力
  python3 scripts/clarity_report.py --save         # data/clarity_snapshot.json に保存
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

CLARITY_API_TOKEN = os.getenv("CLARITY_API_TOKEN", "")
CLARITY_PROJECT_ID = os.getenv("CLARITY_PROJECT_ID", "vmaobifgm0")
API_URL = "https://www.clarity.ms/export-data/api/v1/project-live-insights"

# 閾値（判定用）
RAGE_CLICK_ALERT = 10          # 1日10回以上で警告
DEAD_CLICK_ALERT = 20          # 1日20回以上で警告
SCROLL_DEPTH_MIN = 40          # 40%未満で警告（LPは最低ここまで読ませたい）
BOT_RATIO_ALERT = 0.30         # 30%以上で警告
QUICK_BACK_ALERT = 0.15        # 離脱率15%以上で警告


def fetch_clarity(num_days=1, dim1=None, dim2=None, dim3=None):
    """Clarity Data Export API を1回叩く。1日のクエリ上限10回。"""
    if not CLARITY_API_TOKEN:
        print("❌ CLARITY_API_TOKEN 未設定。.env に追加せよ", file=sys.stderr)
        sys.exit(1)

    params = {"numOfDays": max(1, min(3, num_days))}
    for i, d in enumerate([dim1, dim2, dim3], start=1):
        if d:
            params[f"dimension{i}"] = d

    resp = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {CLARITY_API_TOKEN}"},
        params=params,
        timeout=30,
    )
    if resp.status_code == 401:
        print("❌ 401 Unauthorized — トークン期限切れ or 権限不足", file=sys.stderr)
        sys.exit(1)
    if resp.status_code == 429:
        print("❌ 429 Rate Limit — 本日のクエリ10回上限に到達", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp.json()


def _extract_metric(rows, metric_name):
    """Clarityのレスポンスから特定メトリクスの合計値を抽出"""
    for item in rows:
        if item.get("metricName") == metric_name:
            total = 0
            for inf in item.get("information", []):
                val = inf.get("sessionsCount") or inf.get("totalSessionsCount")
                if val is not None:
                    try:
                        total += float(val)
                    except (TypeError, ValueError):
                        pass
                # fallback: 各メトリクス固有の field
                for k in ("pagesViewsCount", "value", "rageClickCount", "deadClickCount",
                         "quickBackClickCount", "excessiveScrollCount", "scriptErrorCount",
                         "errorClickCount", "averageScrollDepth"):
                    if k in inf:
                        try:
                            total += float(inf[k])
                        except (TypeError, ValueError):
                            pass
            return total
    return 0


def summarize(data, num_days):
    """生データから主要指標を集計"""
    result = {}
    # Traffic
    result["sessions"] = _extract_metric(data, "Traffic")
    result["bots"] = _extract_metric(data, "TotalBotSessions")
    result["distinct_users"] = _extract_metric(data, "DistinctUserCount")
    result["pages_per_session"] = _extract_metric(data, "PagesPerSession")
    # Engagement
    result["engagement_time"] = _extract_metric(data, "EngagementTime")
    result["scroll_depth"] = _extract_metric(data, "ScrollDepth")
    result["active_time"] = _extract_metric(data, "ActiveTime")
    # Quality issues
    result["rage_clicks"] = _extract_metric(data, "RageClickCount")
    result["dead_clicks"] = _extract_metric(data, "DeadClickCount")
    result["quick_backs"] = _extract_metric(data, "QuickbackClick")
    result["excessive_scroll"] = _extract_metric(data, "ExcessiveScroll")
    result["script_errors"] = _extract_metric(data, "ScriptErrorCount")
    result["error_clicks"] = _extract_metric(data, "ErrorClickCount")
    # 派生
    total_sess = result["sessions"] + result["bots"]
    result["bot_ratio"] = (result["bots"] / total_sess) if total_sess > 0 else 0
    result["num_days"] = num_days
    return result


def build_blocks(summary, by_page, by_utm):
    """Slack Block Kit レポート構築"""
    nd = summary["num_days"]
    header_text = f"📊 Clarity UXレポート (直近{nd}日)"

    sess = int(summary["sessions"])
    bots = int(summary["bots"])
    du = int(summary["distinct_users"])
    bot_pct = summary["bot_ratio"] * 100
    rage = int(summary["rage_clicks"])
    dead = int(summary["dead_clicks"])
    qb = int(summary["quick_backs"])
    scr_err = int(summary["script_errors"])

    # 判定アイコン
    bot_icon = "🔴" if bot_pct >= BOT_RATIO_ALERT * 100 else "🟢"
    rage_icon = "🔴" if rage >= RAGE_CLICK_ALERT else "🟡" if rage >= RAGE_CLICK_ALERT / 2 else "🟢"
    dead_icon = "🔴" if dead >= DEAD_CLICK_ALERT else "🟡" if dead >= DEAD_CLICK_ALERT / 2 else "🟢"

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header_text}},
        {"type": "section", "fields": [
            {"type": "mrkdwn", "text": f"*セッション*\n{sess:,}"},
            {"type": "mrkdwn", "text": f"*ユニーク*\n{du:,}"},
            {"type": "mrkdwn", "text": f"*Bot*\n{bot_icon} {bots:,} ({bot_pct:.1f}%)"},
            {"type": "mrkdwn", "text": f"*平均スクロール*\n{summary['scroll_depth']:.0f}%"},
            {"type": "mrkdwn", "text": f"*レイジクリック*\n{rage_icon} {rage}"},
            {"type": "mrkdwn", "text": f"*デッドクリック*\n{dead_icon} {dead}"},
            {"type": "mrkdwn", "text": f"*Quick Back*\n{qb}"},
            {"type": "mrkdwn", "text": f"*JSエラー*\n{'🔴' if scr_err > 0 else '🟢'} {scr_err}"},
        ]},
    ]

    # ページ別 Top5 (問題のあるページ)
    if by_page:
        lines = []
        for row in by_page[:5]:
            lines.append(
                f"• `{row['page'][:50]}` — {row['sessions']}sess / scroll {row['scroll']:.0f}% / rage {row['rage']}"
            )
        if lines:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
                "*📄 ページ別（上位5）*\n" + "\n".join(lines)}})

    # UTM別 (広告流入の質)
    if by_utm:
        lines = []
        for row in by_utm[:5]:
            lines.append(
                f"• `{row['utm']}` — {row['sessions']}sess / scroll {row['scroll']:.0f}% / QB {row['qb']}"
            )
        if lines:
            blocks.append({"type": "divider"})
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
                "*🎯 UTM Source別（流入質）*\n" + "\n".join(lines)}})

    # アラート集約
    alerts = []
    if rage >= RAGE_CLICK_ALERT:
        alerts.append(f"🔴 レイジクリック {rage}件 — ユーザーが反応しない要素を連打している。該当ページ要特定")
    if dead >= DEAD_CLICK_ALERT:
        alerts.append(f"🔴 デッドクリック {dead}件 — クリッカブルに見えて反応しない要素がある")
    if scr_err > 0:
        alerts.append(f"🔴 JSエラー {scr_err}件 — LP動作に支障の可能性")
    if bot_pct >= BOT_RATIO_ALERT * 100:
        alerts.append(f"🔴 Bot比率 {bot_pct:.1f}% — 計測汚染の可能性")
    if summary["scroll_depth"] > 0 and summary["scroll_depth"] < SCROLL_DEPTH_MIN:
        alerts.append(f"🟡 平均スクロール {summary['scroll_depth']:.0f}% < {SCROLL_DEPTH_MIN}% — LPのFV離脱が多い")

    if alerts:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
            "*🚨 アラート*\n" + "\n".join(alerts)}})
    else:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text":
            "✅ 主要指標は閾値内"}})

    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text":
        f"_Clarity project `{CLARITY_PROJECT_ID}` / {datetime.now().strftime('%Y-%m-%d %H:%M')} JST_"}]})

    return blocks


def _page_breakdown(data):
    """Page次元の集計結果をリスト化"""
    out = []
    metric = next((m for m in data if m.get("metricName") == "Traffic"), None)
    if not metric:
        return out
    for inf in metric.get("information", []):
        page = inf.get("Page") or inf.get("URL") or "unknown"
        sess = inf.get("totalSessionsCount") or inf.get("sessionsCount") or 0
        # Page次元ではscroll/rageは別クエリが必要。今回は空で。
        out.append({"page": str(page), "sessions": int(sess), "scroll": 0, "rage": 0})
    return sorted(out, key=lambda x: -x["sessions"])[:10]


def _utm_breakdown(data):
    """UTMSource次元の集計"""
    out = []
    metric = next((m for m in data if m.get("metricName") == "Traffic"), None)
    if not metric:
        return out
    for inf in metric.get("information", []):
        utm = inf.get("UTMSource") or inf.get("utmSource") or "(direct)"
        sess = inf.get("totalSessionsCount") or inf.get("sessionsCount") or 0
        qb = inf.get("quickBackClickCount") or 0
        scroll = inf.get("averageScrollDepth") or 0
        out.append({"utm": str(utm), "sessions": int(sess), "scroll": float(scroll), "qb": int(qb)})
    return sorted(out, key=lambda x: -x["sessions"])[:10]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=1)
    parser.add_argument("--stdout", action="store_true", help="Slackへ送らず標準出力")
    parser.add_argument("--save", action="store_true", help="data/clarity_snapshot.jsonに保存")
    args = parser.parse_args()

    # Query 1: 全体指標（次元なし）
    overall = fetch_clarity(num_days=args.days)
    summary = summarize(overall, args.days)

    # Query 2: ページ別（上位）
    by_page = []
    try:
        page_data = fetch_clarity(num_days=args.days, dim1="Page")
        by_page = _page_breakdown(page_data)
    except Exception as e:
        print(f"⚠️ Page breakdown skip: {e}", file=sys.stderr)

    # Query 3: UTM Source別（広告流入の質）
    by_utm = []
    try:
        utm_data = fetch_clarity(num_days=args.days, dim1="UTMSource")
        by_utm = _utm_breakdown(utm_data)
    except Exception as e:
        print(f"⚠️ UTM breakdown skip: {e}", file=sys.stderr)

    blocks = build_blocks(summary, by_page, by_utm)

    if args.save:
        snap_path = BASE_DIR / "data" / "clarity_snapshot.json"
        snap_path.write_text(json.dumps({
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "num_days": args.days,
            "summary": summary,
            "by_page": by_page,
            "by_utm": by_utm,
            "raw": {"overall": overall},
        }, ensure_ascii=False, indent=2))
        print(f"📁 saved: {snap_path}")

    if args.stdout:
        print(json.dumps(blocks, ensure_ascii=False, indent=2))
        return

    sys.path.insert(0, str(BASE_DIR / "scripts"))
    from slack_utils import send_message, SLACK_CHANNEL_REPORT
    text = f"📊 Clarity UXレポート ({args.days}日): sess={int(summary['sessions']):,} rage={int(summary['rage_clicks'])} dead={int(summary['dead_clicks'])}"
    send_message(SLACK_CHANNEL_REPORT, text, blocks=blocks)
    print(f"✅ Slack 送信完了: {text}")


if __name__ == "__main__":
    main()
