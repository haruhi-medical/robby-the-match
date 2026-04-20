#!/usr/bin/env python3
"""
全HTMLページのフッター著作権行の直前に「会社概要」リンクを挿入。
リンク先: https://haruhi-medical.com/pages/about
rel=nofollow で SEO 評価を遮断。
"""
import os
import re
import glob
import sys

LINK_HTML = '<a href="https://haruhi-medical.com/pages/about" rel="nofollow" target="_blank" style="color:inherit;text-decoration:underline;">会社概要</a>'
MARKER = "haruhi-medical.com/pages/about"

EXCLUDE_DIRS = (
    '/node_modules/', '/.claude/', '/data/', '/logs/',
    '/.git/', '/.worktrees/',
)

# 2パターンのフッター著作権行を検出 + マッチ時スタイルを踏襲
PATTERNS = [
    # <p class="footer-copy">&copy; 2026 ...</p>
    (re.compile(r'(<p\s+class="footer-copy"[^>]*>)(&copy;|©)'),
     r'<p class="footer-copy" style="margin-bottom:6px;">{link}</p>\n        \1\2'),
    # <p style="margin-top:5px;">© 2026 ...</p>
    (re.compile(r'(<p[^>]*style="[^"]*"[^>]*>)(&copy;|©)(\s*2026)'),
     r'<p style="margin-top:5px;font-size:0.75rem;">{link}</p>\n\1\2\3'),
    # plain <p>© 2026 ...</p>
    (re.compile(r'(<p[^>]*>)(&copy;|©)(\s*2026)'),
     r'<p style="font-size:0.75rem;margin-bottom:4px;">{link}</p>\n\1\2\3'),
    # <div ...>© 2026 ... Rights Reserved.</div> — for guide/salary-check
    (re.compile(r'(<div[^>]*>)(&copy;|©)(\s*2026[^<]*Rights Reserved\.?</div>)'),
     r'<div style="font-size:0.72rem;margin-bottom:4px;">{link}</div>\1\2\3'),
]

def process_file(path: str) -> bool:
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    if MARKER in content:
        return False  # 既に追加済み

    if 'Rights Reserved' not in content:
        return False  # 対象外（footerなし）

    for pat, repl_tpl in PATTERNS:
        m = pat.search(content)
        if m:
            new_content = pat.sub(repl_tpl.format(link=LINK_HTML), content, count=1)
            if new_content != content:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                return True
    return False

def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    os.chdir(root)
    files = glob.glob('**/*.html', recursive=True)
    updated = 0
    skipped = 0
    no_match = 0
    for path in files:
        full = os.path.abspath(path)
        if any(d in full for d in EXCLUDE_DIRS):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue
        if 'Rights Reserved' not in content:
            continue
        if MARKER in content:
            skipped += 1
            continue
        if process_file(path):
            updated += 1
        else:
            no_match += 1
            if no_match <= 5:
                print(f'[no-match] {path}', file=sys.stderr)
    print(f'updated: {updated}')
    print(f'already has link: {skipped}')
    print(f'no-match (footer not patched): {no_match}')

if __name__ == '__main__':
    main()
