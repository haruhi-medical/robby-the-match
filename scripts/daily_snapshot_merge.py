#!/usr/bin/env python3
"""
daily_snapshot_merge.py — 日次KPIスナップショット統合ヘルパー (M-02)

目的:
  CLAUDE.md「データドリブン運用方針」にて
  `data/daily_snapshot.json` を全KPI判断の統合先として指定しているが未生成。
  本スクリプトはGA4/Meta広告/ハローワーク/Workerログの各日次データを
  1つのJSONに統合し、週次レポート・実験keep/revert判定の基盤とする。

データソース (実データのみ。架空データ禁止):
  1. GA4      : scripts/ga4_report.py の生データ（GA4 Data API）を再取得
  2. Meta Ads : scripts/daily_ads_report.py と同等のMeta Graph APIをコール
  3. ハローワーク: data/hellowork_history/YYYY-MM-DD.json（既存）
  4. Worker統計 : logs/worker_*.log or api/ ステータス（可能な範囲で）

使い方:
  python3 scripts/daily_snapshot_merge.py                        # 前日分
  python3 scripts/daily_snapshot_merge.py --date 2026-04-16      # 特定日
  python3 scripts/daily_snapshot_merge.py --dry-run              # ファイル書き込み抑止

出力: data/daily_snapshot.json
  既存ファイルがあれば日付キーで追記/上書き。過去35日分を保持してローテート。

cron設定例 (実反映は社長対応):
  15 8 * * * cd ~/robby-the-match && /usr/bin/env python3 scripts/daily_snapshot_merge.py \
    >> logs/daily_snapshot_$(date +\%Y-\%m-\%d).log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

PROJECT_ROOT = Path(__file__).parent.parent
if load_dotenv:
    load_dotenv(PROJECT_ROOT / ".env")

SNAPSHOT_PATH = PROJECT_ROOT / "data" / "daily_snapshot.json"
HELLOWORK_DIR = PROJECT_ROOT / "data" / "hellowork_history"
LOGS_DIR = PROJECT_ROOT / "logs"
RETENTION_DAYS = 35


# ---------- GA4 ----------
def fetch_ga4(date_str: str) -> dict[str, Any]:
    """GA4 Data APIで日次データ取得。認証未設定・APIなしなら {} を返す（架空データ不可）"""
    property_id = os.getenv("GA4_PROPERTY_ID", "")
    creds_path = os.getenv("GA4_CREDENTIALS_PATH", "")
    if not property_id or not creds_path:
        return {"_error": "GA4_PROPERTY_ID / GA4_CREDENTIALS_PATH 未設定"}
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric, Dimension,
        )
        from google.oauth2.service_account import Credentials
    except ImportError:
        return {"_error": "google-analytics-data 未インストール"}

    try:
        creds = Credentials.from_service_account_file(creds_path)
        client = BetaAnalyticsDataClient(credentials=creds)
        metrics = [
            Metric(name="activeUsers"),
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="newUsers"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
        ]
        req = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            metrics=metrics,
        )
        resp = client.run_report(req)
        out: dict[str, Any] = {}
        if resp.rows:
            row = resp.rows[0]
            for m, v in zip(metrics, row.metric_values):
                try:
                    out[m.name] = float(v.value)
                except (TypeError, ValueError):
                    out[m.name] = v.value
        else:
            out["_note"] = "no rows (GA4 returned empty for this date)"

        # 流入元TOP5
        source_req = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
            dimensions=[Dimension(name="sessionSource")],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
            limit=5,
        )
        sresp = client.run_report(source_req)
        out["top_sources"] = [
            {
                "source": r.dimension_values[0].value,
                "sessions": int(float(r.metric_values[0].value)),
                "active_users": int(float(r.metric_values[1].value)),
            }
            for r in sresp.rows
        ]
        return out
    except Exception as e:
        return {"_error": f"GA4 fetch failed: {type(e).__name__}: {e}"}


# ---------- Meta Ads ----------
def fetch_meta_ads(date_str: str) -> dict[str, Any]:
    """Meta Graph APIで日次広告実績取得（アカウントレベル集計）"""
    token = os.getenv("META_ACCESS_TOKEN", "")
    account = os.getenv("META_AD_ACCOUNT_ID", "")
    if not token:
        return {"_error": "META_ACCESS_TOKEN 未設定"}

    try:
        import urllib.parse
        import urllib.request
    except ImportError:
        return {"_error": "urllib 未利用可（想定外）"}

    # 既定アカウント(daily_ads_report.py と合わせる)
    ad_account = f"act_{account}" if account and not account.startswith("act_") else (account or "act_907937825198755")

    params = {
        "access_token": token,
        "fields": "impressions,clicks,spend,cpc,ctr,reach,actions,cost_per_action_type",
        "time_range": json.dumps({"since": date_str, "until": date_str}),
        "level": "account",
    }
    url = f"https://graph.facebook.com/v25.0/{ad_account}/insights?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except Exception as e:
        return {"_error": f"Meta API error: {type(e).__name__}: {e}"}

    rows = payload.get("data", [])
    if not rows:
        return {"_note": "no rows (Meta returned empty for this date)"}
    row = rows[0]
    out: dict[str, Any] = {
        "impressions": int(row.get("impressions", 0) or 0),
        "clicks": int(row.get("clicks", 0) or 0),
        "spend_jpy": float(row.get("spend", 0) or 0),
        "cpc_jpy": float(row.get("cpc", 0) or 0),
        "ctr_pct": float(row.get("ctr", 0) or 0),
        "reach": int(row.get("reach", 0) or 0),
    }
    # actions: Lead等のCV件数
    actions_by_type: dict[str, int] = {}
    for act in row.get("actions", []) or []:
        try:
            actions_by_type[act["action_type"]] = int(float(act["value"]))
        except (KeyError, ValueError, TypeError):
            continue
    out["actions_by_type"] = actions_by_type
    out["leads"] = actions_by_type.get("lead", 0)
    # CPA (リード単価)
    if out["leads"] > 0 and out["spend_jpy"] > 0:
        out["cpa_lead_jpy"] = round(out["spend_jpy"] / out["leads"], 2)
    else:
        out["cpa_lead_jpy"] = None
    return out


# ---------- Hellowork ----------
def load_hellowork(date_str: str) -> dict[str, Any]:
    """ハローワーク日次スナップショット（既存JSON読み込み）"""
    f = HELLOWORK_DIR / f"{date_str}.json"
    if not f.exists():
        return {"_error": f"not found: {f.relative_to(PROJECT_ROOT)}"}
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"parse error: {type(e).__name__}: {e}"}
    # 抜粋（sizeが大きい場合に備えキーを厳選）
    allowed = {"date", "fetched_at", "total_all", "total_nurse",
               "by_area", "by_employment", "by_quality"}
    compact = {k: v for k, v in data.items() if k in allowed}
    # 未マッチキーがあればサイズだけ付記
    compact["_source_file"] = str(f.relative_to(PROJECT_ROOT))
    return compact


# ---------- Worker stats ----------
def load_worker_stats(date_str: str) -> dict[str, Any]:
    """Worker logsから最小限の稼働指標を拾う（完全な集計は別途）"""
    stats: dict[str, Any] = {}
    # ads_reportログ（デプロイ済みsecretsが読めなかった場合のエラー記録などを検出）
    ads_log = LOGS_DIR / f"ads_report_{date_str.replace('-', '')}.log"
    if ads_log.exists():
        try:
            text = ads_log.read_text(encoding="utf-8", errors="replace")
            stats["ads_report_log_bytes"] = ads_log.stat().st_size
            stats["ads_report_ok"] = "[OK]" in text or "success" in text.lower()
        except Exception as e:
            stats["ads_report_log_error"] = f"{type(e).__name__}: {e}"
    # ga4_reportログ
    ga4_log = LOGS_DIR / f"ga4_report_{date_str.replace('-', '')}.log"
    if ga4_log.exists():
        try:
            text = ga4_log.read_text(encoding="utf-8", errors="replace")
            stats["ga4_report_log_bytes"] = ga4_log.stat().st_size
            stats["ga4_report_sc_403"] = "403" in text and "forbidden" in text.lower()
        except Exception as e:
            stats["ga4_report_log_error"] = f"{type(e).__name__}: {e}"
    # worker.js側のAPI健全性(/api/health)のローカルキャッシュは未実装。
    # 現時点ではログの有無のみで信号にする。
    return stats


# ---------- Merge ----------
def build_snapshot(date_str: str) -> dict[str, Any]:
    return {
        "date": date_str,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "ga4": fetch_ga4(date_str),
        "meta_ads": fetch_meta_ads(date_str),
        "hellowork": load_hellowork(date_str),
        "worker": load_worker_stats(date_str),
    }


def load_existing() -> dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        return {"version": 1, "snapshots": {}}
    try:
        data = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except Exception:
        # 破損時は退避
        bak = SNAPSHOT_PATH.with_suffix(".json.corrupt")
        try:
            SNAPSHOT_PATH.rename(bak)
        except Exception:
            pass
        return {"version": 1, "snapshots": {}}
    if "snapshots" not in data or not isinstance(data.get("snapshots"), dict):
        data["snapshots"] = {}
    data.setdefault("version", 1)
    return data


def prune_old(store: dict[str, Any]) -> None:
    if not store.get("snapshots"):
        return
    today = datetime.now().date()
    cutoff = today - timedelta(days=RETENTION_DAYS)
    keep = {}
    for k, v in store["snapshots"].items():
        try:
            d = datetime.strptime(k, "%Y-%m-%d").date()
            if d >= cutoff:
                keep[k] = v
        except ValueError:
            # 不正キーは捨てる
            continue
    store["snapshots"] = keep


def save(store: dict[str, Any]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = SNAPSHOT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SNAPSHOT_PATH)


def main() -> int:
    parser = argparse.ArgumentParser(description="daily snapshot merge")
    parser.add_argument("--date", help="対象日 (YYYY-MM-DD)。既定は前日")
    parser.add_argument("--dry-run", action="store_true", help="ファイル書き込み抑止")
    args = parser.parse_args()

    if args.date:
        try:
            datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print(f"[ERROR] --date は YYYY-MM-DD 形式: {args.date}", file=sys.stderr)
            return 2
        date_str = args.date
    else:
        date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"[snapshot] 対象日: {date_str}", file=sys.stderr)
    snap = build_snapshot(date_str)

    store = load_existing()
    store["snapshots"][date_str] = snap
    store["last_updated"] = datetime.now().isoformat(timespec="seconds")
    prune_old(store)

    if args.dry_run:
        print(json.dumps(snap, ensure_ascii=False, indent=2))
        print(f"[snapshot] dry-run: 書き込みなし", file=sys.stderr)
        return 0

    save(store)
    print(f"[snapshot] wrote {SNAPSHOT_PATH.relative_to(PROJECT_ROOT)} "
          f"(snapshots={len(store['snapshots'])})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
