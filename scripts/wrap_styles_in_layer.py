#!/usr/bin/env python3
"""
wrap_styles_in_layer.py

全下層ページの内部 <style>...</style> を `@layer page { ... }` でラップし、
design-tokens.css（無名レイヤ=最強）が確実に勝つようにする。

CSS Cascade Layers 仕様:
- 名前付きレイヤ < 無名レイヤ（=外側のCSSルール）
- design-tokens.css は無名レイヤ → 最強
- 各ページ <style> は @layer page → 弱くなる → design-tokens.css のスタイルが勝つ

対象: blog/ + lp/job-seeker/area/ + lp/job-seeker/guide/ の全HTMLの <style> ブロック

使い方:
  python3 scripts/wrap_styles_in_layer.py --dry-run
  python3 scripts/wrap_styles_in_layer.py
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = ["blog", "lp/job-seeker/area", "lp/job-seeker/guide"]

# <style>...</style> ブロック (1個目のみでも複数でも対応)
STYLE_RE = re.compile(r'(<style[^>]*>)(\s*)([\s\S]*?)(\s*)(</style>)', re.IGNORECASE)


def wrap_one_style(match):
    open_tag, ws1, body, ws2, close_tag = match.groups()
    # 既に @layer page が含まれる or 空ブロックならスキップ
    if '@layer page' in body or not body.strip():
        return match.group(0)
    # @charset/@import は @layer 内に置けないので、それらは外に出す
    # 現在のプロジェクトには無いはずだが安全策
    imports = []
    charset = ''
    lines_out = []
    for line in body.splitlines(keepends=True):
        stripped = line.strip()
        if stripped.startswith('@charset'):
            charset += line
        elif stripped.startswith('@import'):
            imports.append(line)
        else:
            lines_out.append(line)
    inner = ''.join(lines_out)
    preamble = charset + ''.join(imports)
    wrapped = f"{open_tag}{ws1}{preamble}@layer page {{\n{inner}\n}}{ws2}{close_tag}"
    return wrapped


def process(path: Path, dry: bool) -> tuple:
    html = path.read_text(encoding="utf-8")
    new_html, n = STYLE_RE.subn(wrap_one_style, html)
    if new_html == html:
        return False, 0
    if not dry:
        path.write_text(new_html, encoding="utf-8")
    # 実際にラップされたstyleブロック数を数える
    actual_wrapped = new_html.count('@layer page {') - html.count('@layer page {')
    return True, actual_wrapped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    paths = []
    for sub in TARGETS:
        paths.extend((ROOT / sub).glob('*.html'))
    paths = [p for p in paths if '_backup' not in str(p)]

    changed = 0
    total_wrapped = 0
    for p in sorted(paths):
        upd, wrapped = process(p, args.dry_run)
        if upd:
            changed += 1
            total_wrapped += wrapped

    print(f"{'[DRY]' if args.dry_run else '[DONE]'} files changed: {changed}/{len(paths)}, style blocks wrapped: {total_wrapped}")


if __name__ == '__main__':
    main()
