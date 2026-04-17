#!/usr/bin/env python3
"""
generate_sitemap.py — sitemap.xml を全HTMLファイルから動的生成

動作:
  - lp/job-seeker/area/*.html, lp/job-seeker/guide/*.html, blog/*.html,
    top-level pages (index, salary-check, about), area/guide index をスキャン
  - lastmod は git log の最終 commit 日付（取得できない場合は ファイル mtime）
  - noindex ページ（privacy/terms/proposal/dashboard/404/shindan-preview）除外
  - priority は階層で自動設定（トップ=1.0 / area主要=0.9 / guide/blog=0.7 等）

Usage:
  python3 scripts/generate_sitemap.py
  python3 scripts/generate_sitemap.py --dry-run
  python3 scripts/generate_sitemap.py --index-priority-out docs/seo/index_priority.md
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
BASE_URL = "https://quads-nurse.com"

# 除外: noindex or 非公開ページ
EXCLUDE_PATHS = {
    "privacy.html",
    "terms.html",
    "proposal.html",
    "dashboard.html",
    "404.html",
    "_upload_helper.html",
    "lp/job-seeker/index-preview.html",
    "blog/success-story-template.html",
}

# 主要エリア（priority 0.9）
PRIMARY_AREAS = {
    "yokohama", "kawasaki", "sagamihara", "yokosuka", "fujisawa", "odawara",
}


def get_git_lastmod(file_path: Path) -> Optional[str]:
    """git log 最終コミット日を YYYY-MM-DD で返す。失敗時 None。"""
    try:
        rel = str(file_path.relative_to(REPO_ROOT))
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ad", "--date=short", "--", rel],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        date_str = result.stdout.strip()
        if date_str and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            return date_str
    except Exception:
        pass
    return None


def get_mtime_lastmod(file_path: Path) -> str:
    """ファイル mtime を YYYY-MM-DD で返す。"""
    return datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d")


def resolve_lastmod(file_path: Path) -> str:
    """git > mtime の優先順位で lastmod を決定。"""
    git_date = get_git_lastmod(file_path)
    if git_date:
        return git_date
    return get_mtime_lastmod(file_path)


def classify_priority(rel_path: str) -> Tuple[float, str]:
    """相対パスから (priority, changefreq) を決定。"""
    if rel_path == "index.html":
        return (1.0, "weekly")
    if rel_path == "lp/job-seeker/index.html":
        return (1.0, "weekly")
    if rel_path.startswith("lp/job-seeker/area/"):
        slug = rel_path.split("/")[-1].replace(".html", "")
        if slug == "index":
            return (0.8, "weekly")
        if slug in PRIMARY_AREAS:
            return (0.9, "weekly")
        return (0.8, "weekly")
    if rel_path.startswith("lp/job-seeker/guide/"):
        return (0.7, "weekly")
    if rel_path.startswith("blog/"):
        if rel_path == "blog/index.html":
            return (0.8, "weekly")
        return (0.7, "weekly")
    if rel_path.startswith("salary-check/"):
        return (0.8, "monthly")
    if rel_path.startswith("about"):
        return (0.5, "monthly")
    return (0.5, "monthly")


def to_url(rel_path: str) -> str:
    """相対パスを公開URLに変換（/index.html → /）。"""
    if rel_path.endswith("/index.html"):
        dir_path = rel_path[:-len("index.html")]
        return f"{BASE_URL}/{dir_path}"
    if rel_path == "index.html":
        return f"{BASE_URL}/"
    return f"{BASE_URL}/{rel_path}"


def collect_files() -> List[Path]:
    """公開対象HTMLファイルを収集。"""
    files: List[Path] = []
    # トップレベル
    for name in ["index.html", "salary-check/index.html"]:
        p = REPO_ROOT / name
        if p.exists():
            files.append(p)
    # lp/job-seeker 配下
    for sub in ["lp/job-seeker", "lp/job-seeker/area", "lp/job-seeker/guide"]:
        d = REPO_ROOT / sub
        if d.exists():
            for f in sorted(d.glob("*.html")):
                files.append(f)
    # blog
    blog = REPO_ROOT / "blog"
    if blog.exists():
        for f in sorted(blog.glob("*.html")):
            files.append(f)
    # 重複排除 + 除外
    seen = set()
    out: List[Path] = []
    for f in files:
        rel = str(f.relative_to(REPO_ROOT))
        if rel in EXCLUDE_PATHS:
            continue
        if rel.endswith("-preview.html"):
            continue
        if rel in seen:
            continue
        seen.add(rel)
        out.append(f)
    return out


def build_sitemap(files: List[Path]) -> Tuple[str, List[dict]]:
    """sitemap XML文字列 + URL情報リストを返す。"""
    urls = []
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for f in files:
        rel = str(f.relative_to(REPO_ROOT))
        url = to_url(rel)
        lastmod = resolve_lastmod(f)
        priority, freq = classify_priority(rel)
        urls.append({
            "rel": rel, "url": url, "lastmod": lastmod,
            "priority": priority, "changefreq": freq,
        })
        xml_parts.extend([
            "  <url>",
            f"    <loc>{url}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            f"    <changefreq>{freq}</changefreq>",
            f"    <priority>{priority:.1f}</priority>",
            "  </url>",
        ])
    xml_parts.append("</urlset>")
    return "\n".join(xml_parts) + "\n", urls


def write_index_priority(urls: List[dict], output_path: Path) -> None:
    """Search Console手動インデックスリクエスト用URL一覧を Markdown で出力。

    優先度順: priority 高 × lastmod 新しい順。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # priority降順 → lastmod降順
    sorted_urls = sorted(urls, key=lambda u: (-u["priority"], u["lastmod"]), reverse=False)
    sorted_urls = sorted(urls, key=lambda u: (u["priority"], u["lastmod"]), reverse=True)

    # トップ優先 20 URL
    top = sorted_urls[:20]

    lines = [
        "# Search Console 手動インデックスリクエスト優先リスト",
        "",
        f"> 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> 生成元: `scripts/generate_sitemap.py`",
        "",
        "## 運用ガイド",
        "",
        "1. [Search Console](https://search.google.com/search-console) を開く",
        "2. 上部検索バーに以下のURLを1件ずつ入力",
        "3. 「インデックス登録をリクエスト」をクリック",
        "4. 1日15件までが目安（超過するとレート制限）",
        "",
        "## Tier 1 優先URL（Priority ≥ 0.8、更新日新しい順 最大20件）",
        "",
        "| # | URL | Priority | Lastmod |",
        "|---|-----|----------|---------|",
    ]
    for i, u in enumerate(top, 1):
        lines.append(f"| {i} | {u['url']} | {u['priority']:.1f} | {u['lastmod']} |")

    # Tier 2: guide / blog（残り）
    tier2 = [u for u in sorted_urls if u not in top and u["priority"] >= 0.7][:30]
    if tier2:
        lines += ["", "## Tier 2（Priority 0.7 / 2週目以降に投入）", "",
                  "| # | URL | Priority | Lastmod |", "|---|-----|----------|---------|"]
        for i, u in enumerate(tier2, 1):
            lines.append(f"| {i} | {u['url']} | {u['priority']:.1f} | {u['lastmod']} |")

    lines += [
        "",
        "## 全URL統計",
        "",
        f"- 総URL数: {len(urls)}",
        f"- Priority 1.0: {sum(1 for u in urls if u['priority'] == 1.0)}",
        f"- Priority 0.9: {sum(1 for u in urls if u['priority'] == 0.9)}",
        f"- Priority 0.8: {sum(1 for u in urls if u['priority'] == 0.8)}",
        f"- Priority 0.7: {sum(1 for u in urls if u['priority'] == 0.7)}",
        f"- Priority 0.5以下: {sum(1 for u in urls if u['priority'] <= 0.5)}",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="sitemap.xml を全HTMLファイルから動的生成")
    parser.add_argument("--dry-run", action="store_true", help="ファイル書き換えせず標準出力に表示")
    parser.add_argument(
        "--index-priority-out",
        default="docs/seo/index_priority.md",
        help="Search Console 手動インデックスリクエスト用URL一覧の出力先",
    )
    args = parser.parse_args()

    files = collect_files()
    xml_str, urls = build_sitemap(files)

    if args.dry_run:
        print(xml_str)
        print(f"\n[INFO] total URLs: {len(urls)}", file=sys.stderr)
        return 0

    SITEMAP_PATH.write_text(xml_str, encoding="utf-8")
    print(f"[OK] sitemap.xml written: {SITEMAP_PATH} ({len(urls)} URLs)")

    # index priority リスト
    if args.index_priority_out:
        out_path = REPO_ROOT / args.index_priority_out
        write_index_priority(urls, out_path)
        print(f"[OK] index priority list written: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
