#!/usr/bin/env python3
"""
unify_root_palette.py

LP(TOP)統一: 全下層ページの :root 変数値と直書きカラーを LP 配色に一括置換。

参考実装: lp/job-seeker/guide/career-change.html（統一済み）

対象:
- blog/*.html (直書き色多数)
- lp/job-seeker/area/*.html (:root変数の値のみ)
- lp/job-seeker/guide/*.html (:root変数の値のみ, career-change除く)

置換パターン:
1. :root{} の旧色 → LP色
2. 直書きカラーコード (blog要対応)
3. 明朝フォント → Noto Sans JP
4. grain texture → display:none

使い方:
  python3 scripts/unify_root_palette.py --dry-run  # 変更なし、件数表示
  python3 scripts/unify_root_palette.py            # 実行
"""
import argparse
import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["blog", "lp/job-seeker/area", "lp/job-seeker/guide"]
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# ===========================================================================
# 置換ルール (優先順)
# ===========================================================================

# A) :root 変数値の置換 (コメント保持)
ROOT_VAR_REPLACEMENTS = [
    (r"(--bg:\s*)#F6F2E8", r"\1#ffffff"),
    (r"(--bg-card:\s*)#FAF8F1", r"\1#f0f8fc"),
    (r"(--bg-deep:\s*)#EDE6D2", r"\1#e6f4fb"),
    (r"(--ink:\s*)#181A20", r"\1#2a2a3e"),
    (r"(--ink-soft:\s*)#484D58", r"\1#4a4a5e"),
    (r"(--ink-quiet:\s*)#8A8D94", r"\1#7a7a8e"),
    (r"(--teal:\s*)#3E7388", r"\1#1a9de0"),
    (r"(--teal-soft:\s*)#7CA3B6", r"\1#50c8a0"),
    (r"(--gold:\s*)#9E7A3F", r"\1#1080c0"),
    (r"(--rule:\s*)rgba\(24,\s*26,\s*32,\s*0\.1\)", r"\1rgba(42, 42, 62, 0.08)"),
    (r"(--rule-soft:\s*)rgba\(24,\s*26,\s*32,\s*0\.05\)", r"\1rgba(42, 42, 62, 0.04)"),
    # フォント: 明朝→ゴシック
    (
        r'--font-display:\s*"Shippori Mincho B1"[^;]+;',
        '--font-display: "Noto Sans JP", -apple-system, BlinkMacSystemFont, "Hiragino Sans", sans-serif;',
    ),
    # 粒子テクスチャ無効化
    (
        r"body::before\s*\{[^}]*fractalNoise[^}]*\}",
        "body::before { display: none; }",
    ),
]

# B) 直書きカラー置換 (blog 向け、大文字小文字両対応)
DIRECT_COLOR_REPLACEMENTS = [
    # 優先度: より濃い色から薄い色へ
    (re.compile(r"#181a20", re.IGNORECASE), "#2a2a3e"),  # near-black → text-primary
    (re.compile(r"#1a1a2e", re.IGNORECASE), "#2a2a3e"),  # 紺 → text-primary
    (re.compile(r"#2d5a3d", re.IGNORECASE), "#2a2a3e"),  # 濃緑 → text-primary
    (re.compile(r"#1a7f64", re.IGNORECASE), "#1a9de0"),  # 濃ミント → primary
    (re.compile(r"#a8dadc", re.IGNORECASE), "#50c8a0"),  # pale-cyan → accent
    (re.compile(r"#f6f2e8", re.IGNORECASE), "#e6f4fb"),  # cream → primary-light
    (re.compile(r"#faf8f1", re.IGNORECASE), "#f0f8fc"),  # light-cream → bg-tint
    (re.compile(r"#ede6d2", re.IGNORECASE), "#e6f4fb"),  # sand → primary-light
    (re.compile(r"#e8e6e3", re.IGNORECASE), "#f0f8fc"),  # 薄ベージュ → bg-tint
    (re.compile(r"#7ca3b6", re.IGNORECASE), "#50c8a0"),  # teal-soft-old → accent
    (re.compile(r"#484d58", re.IGNORECASE), "#4a4a5e"),  # ink-soft-old → text-secondary
    (re.compile(r"#8a8d94", re.IGNORECASE), "#7a7a8e"),  # ink-quiet-old → text-muted
    (re.compile(r"#3e7388", re.IGNORECASE), "#1a9de0"),  # editorial teal → primary
    (re.compile(r"#9e7a3f", re.IGNORECASE), "#1080c0"),  # gold → primary-dark
    (re.compile(r"#eef7f4", re.IGNORECASE), "#e6f4fb"),  # 薄緑背景 → primary-light
]

# C) 監査用: 残存していたらフラグを立てる色
DEVIATION_COLORS_LOWER = {
    "#3e7388", "#9e7a3f", "#f6f2e8", "#181a20", "#faf8f1",
    "#ede6d2", "#7ca3b6", "#484d58", "#8a8d94", "#a8dadc",
    "#1a7f64", "#1a1a2e", "#2d5a3d", "#e8e6e3", "#eef7f4",
}


def process(path: Path, dry: bool) -> dict:
    html = path.read_text(encoding="utf-8")
    original = html

    # A) :root 変数値
    for pat, rep in ROOT_VAR_REPLACEMENTS:
        html = re.sub(pat, rep, html, flags=re.DOTALL)

    # B) 直書き色
    for pat, rep in DIRECT_COLOR_REPLACEMENTS:
        html = pat.sub(rep, html)

    if html == original:
        return {"path": str(path.relative_to(ROOT)), "changed": False}

    if not dry:
        path.write_text(html, encoding="utf-8")

    # 残存チェック
    lower = html.lower()
    residual = [c for c in sorted(DEVIATION_COLORS_LOWER) if c in lower]

    return {
        "path": str(path.relative_to(ROOT)),
        "changed": True,
        "residual": residual,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    paths = []
    for sub in TARGETS:
        paths.extend((ROOT / sub).glob("*.html"))
    paths = [p for p in paths if "_backup" not in str(p)]

    # career-change は触らない（既に統一済み、再処理不要）
    paths = [p for p in paths if not str(p).endswith("guide/career-change.html")]

    results = [process(p, args.dry_run) for p in sorted(paths)]
    changed = sum(1 for r in results if r["changed"])
    with_residual = [r for r in results if r.get("residual")]

    print(f"{'[DRY RUN]' if args.dry_run else '[APPLIED]'} changed: {changed}/{len(results)}")
    if with_residual:
        print(f"\n⚠️ 残存色あり: {len(with_residual)} 件")
        for r in with_residual[:10]:
            print(f"  {r['path']}  residual={r['residual']}")


if __name__ == "__main__":
    main()
