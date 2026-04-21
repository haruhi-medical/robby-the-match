#!/usr/bin/env python3
"""
sync_blog_display_dates.py

blog/各記事の画面表示日付 (<time>, .article-meta) と blog/index.html の
.card-meta を JSON-LD の datePublished と完全同期する。

問題: 2026-04-20 実施の日付分散では JSON-LD のみ更新し、
HTML表示日付は 2026年2月20日/23日 のまま残っていた。

使い方:
  python3 scripts/sync_blog_display_dates.py --dry-run
  python3 scripts/sync_blog_display_dates.py
"""
import argparse
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = ROOT / "blog"

JP_MONTHS = ["", "1月", "2月", "3月", "4月", "5月", "6月",
             "7月", "8月", "9月", "10月", "11月", "12月"]


def to_jp(date_str: str) -> str:
    """2026-02-14 → 2026年2月14日"""
    y, m, d = date_str.split("-")
    return f"{y}年{int(m)}月{int(d)}日"


def to_dot(date_str: str) -> str:
    """2026-02-14 → 2026.02.14"""
    return date_str.replace("-", ".")


def extract_date(html: str) -> Optional[str]:
    """JSON-LD の datePublished を抽出"""
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})"', html)
    return m.group(1) if m else None


def update_article(path: Path, dry: bool) -> bool:
    html = path.read_text(encoding="utf-8")
    pub = extract_date(html)
    if not pub:
        return False
    new = html
    # <time datetime="YYYY-MM-DD">YYYY年M月D日</time> パターン
    new = re.sub(
        r'<time datetime="\d{4}-\d{2}-\d{2}">\d{4}年\d{1,2}月\d{1,2}日</time>',
        f'<time datetime="{pub}">{to_jp(pub)}</time>',
        new,
    )
    # 生テキストの「2026年M月D日」だけのバージョンにも対応
    new = re.sub(
        r'<time>\d{4}年\d{1,2}月\d{1,2}日</time>',
        f'<time datetime="{pub}">{to_jp(pub)}</time>',
        new,
    )
    # card-meta 互換: 2026.02.20 / ナースロビー 形式も記事内にあれば更新
    new = re.sub(
        r'\b\d{4}\.\d{2}\.\d{2}(?=\s*/\s*ナースロビー)',
        to_dot(pub),
        new,
    )
    if new == html:
        return False
    if not dry:
        path.write_text(new, encoding="utf-8")
    return True


def update_index(dry: bool) -> int:
    """blog/index.html の各 <a class="blog-card"> 中 .card-meta を
       リンク先記事の JSON-LD datePublished と同期。"""
    index_path = BLOG_DIR / "index.html"
    html = index_path.read_text(encoding="utf-8")

    # 記事ごとの日付マップ
    dates = {}
    for p in BLOG_DIR.glob("*.html"):
        if p.name == "index.html":
            continue
        t = p.read_text(encoding="utf-8")
        d = extract_date(t)
        if d:
            dates[p.name] = d

    changes = 0
    # <a ... href="xxx.html" class="blog-card">[^</a>]*</a> を捕まえる
    def replace_card(m):
        nonlocal changes
        block = m.group(0)
        href_m = re.search(r'href="([^"]+)"', block)
        if not href_m:
            return block
        slug = href_m.group(1).split("/")[-1]
        if slug not in dates:
            return block
        new_date_dot = to_dot(dates[slug])
        new_block = re.sub(
            r'(<div class="card-meta">)\d{4}\.\d{2}\.\d{2}(\s*/\s*[^<]+?</div>)',
            rf'\g<1>{new_date_dot}\g<2>',
            block,
        )
        if new_block != block:
            changes += 1
        return new_block

    new = re.sub(
        r'<a[^>]*class="blog-card"[^>]*>[\s\S]*?</a>',
        replace_card,
        html,
    )

    if new != html and not dry:
        index_path.write_text(new, encoding="utf-8")
    return changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    articles_changed = 0
    for p in sorted(BLOG_DIR.glob("*.html")):
        if p.name == "index.html":
            continue
        if update_article(p, args.dry_run):
            articles_changed += 1
            print(f"{'[DRY]' if args.dry_run else '[OK] '} {p.name}")

    index_changes = update_index(args.dry_run)
    print(f"\narticles updated: {articles_changed}")
    print(f"index card-meta updates: {index_changes}")


if __name__ == "__main__":
    main()
