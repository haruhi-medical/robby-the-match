#!/usr/bin/env python3
"""
競合ベンチマーク取得（Phase 3 #58） v1.0

レバウェル / マイナビ看護師 / ナース人材バンク の公開情報を月1回収集して
data/competitor_benchmark.json に保存する。

原則: 架空データ禁止。取得不可の項目は status="not_available" で "手動確認" リストに
      回す。SimilarWeb や Ahrefs の有料APIは使わない（月3万円超禁止）。

取得ソース（全て公開・無料）:
  1) Google 検索件数: `site:domain.com` の検索結果ヒット数（HTML scraping）
  2) サイトの公開情報（許可番号／会社概要ページの fetch → テキスト抽出）
  3) robots.txt / sitemap.xml の存在確認（SEOポリシー指標）

cron: 月1回  0 4 1 * *  （毎月1日 04:00）

使い方:
  python3 scripts/competitor_benchmark.py           # 実行＋JSON保存
  python3 scripts/competitor_benchmark.py --print   # 結果を stdout にも出す
  python3 scripts/competitor_benchmark.py --cron    # Slack要約も送信
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

OUTPUT_FILE = PROJECT_ROOT / "data" / "competitor_benchmark.json"
MANUAL_QUEUE_FILE = PROJECT_ROOT / "data" / "competitor_manual_check.md"

# 競合一覧（ナース専門に絞る）
COMPETITORS = [
    {
        "name": "レバウェル看護",
        "domain": "kango-oshigoto.jp",
        "url": "https://kango-oshigoto.jp/",
        "category": "major_agent",
    },
    {
        "name": "マイナビ看護師",
        "domain": "kango.mynavi.jp",
        "url": "https://kango.mynavi.jp/",
        "category": "major_agent",
    },
    {
        "name": "ナース人材バンク",
        "domain": "nursejinzaibank.com",
        "url": "https://www.nursejinzaibank.com/",
        "category": "major_agent",
    },
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
TIMEOUT = 20


def _http_get(url: str) -> tuple[int, str]:
    """HTTP GET。失敗時は (status_code, '')"""
    if requests is None:
        return 0, ""
    try:
        r = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "ja,en;q=0.8"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        return r.status_code, r.text or ""
    except Exception:
        return 0, ""


def fetch_site_index_count(domain: str) -> dict:
    """Google の `site:domain` 検索結果ヒット数を推定する。
    GoogleのUIはしばしば変わるため、取得できない場合は status='not_available' を返す。
    """
    query = f"site:{domain}"
    url = f"https://www.google.com/search?q={query}&hl=ja"
    status, html = _http_get(url)
    if status != 200 or not html:
        return {"status": "not_available", "reason": f"http_{status}"}
    # Google の「約 XXX,XXX 件」表記を抽出
    m = re.search(r"約?\s*([\d,]+)\s*件", html)
    if not m:
        # 英語UIフォールバック
        m = re.search(r"About\s*([\d,]+)\s*results", html)
    if not m:
        return {"status": "not_available", "reason": "pattern_not_found"}
    try:
        count = int(m.group(1).replace(",", ""))
    except ValueError:
        return {"status": "not_available", "reason": "parse_error"}
    return {"status": "ok", "count": count, "query": query}


def fetch_robots_sitemap(base_url: str) -> dict:
    """robots.txt と sitemap.xml の存在確認。
    ドメインレーティング代替として SEO衛生度を測る。"""
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    robots_status, robots_body = _http_get(root + "/robots.txt")
    sitemap_status, sitemap_body = _http_get(root + "/sitemap.xml")
    result = {
        "robots_txt": {
            "status_code": robots_status,
            "exists": robots_status == 200 and len(robots_body) > 0,
            "size_bytes": len(robots_body) if robots_status == 200 else 0,
        },
        "sitemap_xml": {
            "status_code": sitemap_status,
            "exists": sitemap_status == 200 and len(sitemap_body) > 0,
            "url_count_estimate": None,
        },
    }
    if sitemap_status == 200 and sitemap_body:
        # <loc> タグ or <sitemap> タグ数（簡易カウント）
        loc_count = sitemap_body.count("<loc>")
        result["sitemap_xml"]["url_count_estimate"] = loc_count
    return result


def fetch_homepage_signals(url: str) -> dict:
    """トップページを取得して、タイトル・メタ・有料許可番号を拾う。"""
    status, html = _http_get(url)
    if status != 200 or not html:
        return {"status": "not_available", "reason": f"http_{status}"}

    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    desc_match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
        html, re.I,
    )
    permit_match = re.search(r"\d{2}[-ーー][ユー][-ーー]\d{6}", html)
    return {
        "status": "ok",
        "http_status": status,
        "html_size_bytes": len(html),
        "title": (title_match.group(1).strip()[:200] if title_match else ""),
        "description": (desc_match.group(1).strip()[:300] if desc_match else ""),
        "permit_number_on_top": permit_match.group(0) if permit_match else None,
    }


def run(verbose: bool = False) -> dict:
    results: list[dict] = []
    manual_queue: list[str] = []

    for comp in COMPETITORS:
        if verbose:
            print(f"[fetch] {comp['name']} ({comp['domain']})")
        row = {
            "name": comp["name"],
            "domain": comp["domain"],
            "url": comp["url"],
            "category": comp["category"],
            "fetched_at": datetime.now().isoformat(timespec="seconds"),
            "site_index_count": fetch_site_index_count(comp["domain"]),
            "seo_hygiene": fetch_robots_sitemap(comp["url"]),
            "homepage": fetch_homepage_signals(comp["url"]),
        }
        # 取得失敗があれば手動確認キューに追加
        if row["site_index_count"].get("status") != "ok":
            manual_queue.append(
                f"- {comp['name']} — Google site:検索件数（手動で `site:{comp['domain']}` を検索）"
            )
        if row["homepage"].get("status") != "ok":
            manual_queue.append(
                f"- {comp['name']} — トップページ取得不可（{comp['url']} を手動確認）"
            )
        results.append(row)
        time.sleep(2)  # Google bot避け（礼儀）

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "competitors": results,
        "notes": [
            "SimilarWeb / Ahrefs 相当のデータは有料APIのため取得していない。",
            "ドメインレーティング相当の指標は未取得 = not_available で明記。",
            "Google `site:` 検索件数は日/時間で揺らぐ参考値。トレンド比較にのみ使うこと。",
        ],
        "manual_check_queue": manual_queue,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    if manual_queue:
        MANUAL_QUEUE_FILE.write_text(
            "# 競合ベンチマーク — 手動確認リスト\n\n"
            f"> 生成: {summary['generated_at']}\n\n"
            "自動取得できなかった項目。必要に応じて手動で確認すること。\n"
            "結果は data/competitor_benchmark.json に追記してよい。\n\n"
            + "\n".join(manual_queue)
            + "\n"
        )
    return summary


def build_slack_summary(summary: dict) -> str:
    lines = ["📊 *競合ベンチマーク（月次）*"]
    for row in summary.get("competitors", []):
        idx = row.get("site_index_count", {})
        idx_s = (
            f"{idx.get('count'):,}ページ" if idx.get("status") == "ok"
            else "取得失敗（手動確認）"
        )
        sm = row.get("seo_hygiene", {}).get("sitemap_xml", {})
        sm_s = (
            f"sitemap {sm.get('url_count_estimate') or '?'}件"
            if sm.get("exists") else "sitemap無し"
        )
        lines.append(f"• {row['name']}: {idx_s} / {sm_s}")
    if summary.get("manual_check_queue"):
        lines.append(f"\n⚠️ 手動確認 {len(summary['manual_check_queue'])}件 "
                     "(data/competitor_manual_check.md)")
    lines.append("\n_注: Google site:検索件数は参考値。ドメインレーティングは未取得。_")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(description="競合ベンチマーク取得（月次）")
    p.add_argument("--print", dest="do_print", action="store_true")
    p.add_argument("--cron", action="store_true", help="Slackに要約送信")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    if requests is None:
        sys.stderr.write("requests モジュールが無いため実行不可\n")
        return 2

    summary = run(verbose=args.verbose)
    if args.do_print:
        print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.cron:
        try:
            from slack_utils import send_message, SLACK_CHANNEL_REPORT
            send_message(SLACK_CHANNEL_REPORT, build_slack_summary(summary))
        except Exception as e:
            sys.stderr.write(f"Slack送信失敗: {e}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
