#!/usr/bin/env python3
"""
add_area_crosslinks.py — blog→area / area→blog の内部リンク強化

目的:
  - blogページで area 内部リンクが0-2本の薄いページに、関連エリア3件のリンクを追加
  - area ページの関連ブログリンクセクションを強化（area → blog）

動作:
  - <article> 末尾の footer 直前に関連リンクブロックを挿入
  - 既存の「エリア別求人情報」ヘッダーがあれば追加しない（重複防止）

Usage:
  python3 scripts/add_area_crosslinks.py --dry-run
  python3 scripts/add_area_crosslinks.py
"""

from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
AREA_DIR = REPO_ROOT / "lp" / "job-seeker" / "area"
GUIDE_DIR = REPO_ROOT / "lp" / "job-seeker" / "guide"

# blog → 関連エリア（3件）: 内容ベースで関連性が高いものを選定
BLOG_TO_AREAS = {
    "ai-medical-future.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("sagamihara.html", "相模原市の看護師求人"),
    ],
    "night-shift-health.html": [
        ("yokohama.html", "横浜市の夜勤なし求人"),
        ("kawasaki.html", "川崎市の夜勤なし求人"),
        ("fujisawa.html", "藤沢市の看護師求人"),
    ],
    "nurse-communication.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("yokosuka.html", "横須賀市の看護師求人"),
    ],
    "nurse-money-guide.html": [
        ("yokohama.html", "横浜市の看護師給与相場"),
        ("kawasaki.html", "川崎市の看護師給与相場"),
        ("odawara.html", "小田原市の看護師給与相場"),
    ],
    "nurse-stress-management.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("sagamihara.html", "相模原市の看護師求人"),
    ],
    "agent-comparison.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("fujisawa.html", "藤沢市の看護師求人"),
    ],
    "blank-nurse-return.html": [
        ("yokohama.html", "横浜市の復職支援求人"),
        ("kawasaki.html", "川崎市の復職支援求人"),
        ("sagamihara.html", "相模原市の復職支援求人"),
    ],
    "kosodate-nurse.html": [
        ("fujisawa.html", "藤沢市の子育て両立求人"),
        ("chigasaki.html", "茅ヶ崎市の子育て両立求人"),
        ("odawara.html", "小田原市の子育て両立求人"),
    ],
    "nurse-market-2026.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("sagamihara.html", "相模原市の看護師求人"),
    ],
    "shoukai-tesuuryou.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("odawara.html", "小田原市の看護師求人"),
    ],
    "tenshoku-timing.html": [
        ("yokohama.html", "横浜市の看護師求人"),
        ("kawasaki.html", "川崎市の看護師求人"),
        ("fujisawa.html", "藤沢市の看護師求人"),
    ],
    "yakin-nashi.html": [
        ("yokohama.html", "横浜市の夜勤なし求人"),
        ("kawasaki.html", "川崎市の夜勤なし求人"),
        ("sagamihara.html", "相模原市の夜勤なし求人"),
    ],
    "clinic-tenshoku.html": [
        ("yokohama.html", "横浜市のクリニック求人"),
        ("kawasaki.html", "川崎市のクリニック求人"),
        ("fujisawa.html", "藤沢市のクリニック求人"),
    ],
    "houmon-kango.html": [
        ("yokohama.html", "横浜市の訪問看護求人"),
        ("kawasaki.html", "川崎市の訪問看護求人"),
        ("sagamihara.html", "相模原市の訪問看護求人"),
    ],
}


HEADER_MARK = "エリア別求人情報"
# 挿入するHTMLテンプレート
def build_block(links: list[tuple[str, str]]) -> str:
    items = "\n".join(
        f'        <li><a href="/lp/job-seeker/area/{slug}">{label}</a></li>'
        for slug, label in links
    )
    return (
        '\n<div style="background:#f8fffe;padding:20px;border-radius:12px;margin:30px 0;border-left:4px solid #1a7f64;">\n'
        f'    <h4 style="margin-top:0;color:#1a1a2e;">{HEADER_MARK}</h4>\n'
        '    <ul>\n'
        f'{items}\n'
        '    </ul>\n'
        '</div>\n'
    )


def patch_blog_file(path: Path, links: list, dry_run: bool = False) -> bool:
    """blog ページに エリア別求人情報ブロック を挿入 or 既存ブロックに追加。

    - ブロック未存在 → </article> 直前に新規挿入
    - ブロック存在 & 3件未満 → <ul>内に <li> 追加
    """
    content = path.read_text(encoding="utf-8")

    if HEADER_MARK in content:
        # 既存ブロックに不足分を追加
        # <h4...>エリア別求人情報</h4>\n    <ul>\n ... </ul> にマッチ
        pattern = re.compile(
            r'(<h4[^>]*>' + re.escape(HEADER_MARK) + r'</h4>\s*<ul>)(.*?)(</ul>)',
            re.DOTALL
        )
        m = pattern.search(content)
        if not m:
            return False
        block_body = m.group(2)
        # 既存 <li href=.../area/xxx.html> のスラッグを抽出
        existing_slugs = set(re.findall(r'href="[^"]*/area/([^"]+)"', block_body))
        to_add = [(slug, label) for slug, label in links if slug not in existing_slugs]
        if not to_add:
            return False  # 既に十分
        # 3件未満のみ補強
        current_count = block_body.count("<li")
        needed = max(0, 3 - current_count)
        to_add = to_add[:needed]
        if not to_add:
            return False
        extra = "".join(
            f'\n        <li><a href="/lp/job-seeker/area/{slug}">{label}</a></li>'
            for slug, label in to_add
        )
        new_block_body = block_body.rstrip() + extra + "\n    "
        new_content = content[:m.start(2)] + new_block_body + content[m.end(2):]
        if dry_run:
            print(f"[DRY] would add {len(to_add)} links to: {path.relative_to(REPO_ROOT)}")
            return True
        path.write_text(new_content, encoding="utf-8")
        print(f"[OK] added {len(to_add)} links: {path.relative_to(REPO_ROOT)}")
        return True

    # 既存ブロックなし → 新規挿入
    block = build_block(links)
    marker = "</article>"
    idx = content.rfind(marker)
    if idx < 0:
        marker = "</body>"
        idx = content.rfind(marker)
        if idx < 0:
            return False
    new_content = content[:idx] + block + content[idx:]
    if dry_run:
        print(f"[DRY] would insert block: {path.relative_to(REPO_ROOT)} (+{len(block)} chars)")
        return True
    path.write_text(new_content, encoding="utf-8")
    print(f"[OK] inserted block: {path.relative_to(REPO_ROOT)}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    patched = 0
    skipped = 0
    for fname, links in BLOG_TO_AREAS.items():
        p = BLOG_DIR / fname
        if not p.exists():
            print(f"[WARN] skip missing: {fname}", file=sys.stderr)
            continue
        if patch_blog_file(p, links, dry_run=args.dry_run):
            patched += 1
        else:
            skipped += 1

    print(f"\n[SUMMARY] patched={patched} / skipped={skipped} (dry_run={args.dry_run})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
