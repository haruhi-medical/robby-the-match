#!/usr/bin/env python3
"""
unify_header_footer.py — LP TOP に合わせてヘッダー/フッターを全ページ統一

対象:
- blog/*.html (index.html 含む)
- lp/job-seeker/area/*.html
- lp/job-seeker/guide/*.html (career-change.html は済み)

対象外:
- lp/job-seeker/index.html (LP本体)
- terms/privacy/proposal/about (法的ページ、別のヘッダー構造)

使い方:
  python3 scripts/unify_header_footer.py --dry-run  # 確認のみ
  python3 scripts/unify_header_footer.py            # 実行
"""
import argparse
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

HEADER_HTML = '''<!-- Header (LP統一 2026-04-20) -->
<header class="site-header" id="site-header">
<a href="/lp/job-seeker/" class="header-logo"><img src="/assets/logo-nursrobby.png" alt="ナースロビー" height="48"></a>
<nav class="header-nav">
<a href="/lp/job-seeker/area/">地域別求人</a>
<a href="/lp/job-seeker/guide/">転職ガイド</a>
<a href="/blog/">ブログ</a>
</nav>
<button class="hamburger" aria-label="メニュー" onclick="document.getElementById('mobileNav').classList.add('open')">&#9776;</button>
</header>

<!-- Mobile Navigation -->
<div id="mobileNav" class="mobile-nav" onclick="this.classList.remove('open')">
<div class="mobile-nav-inner" onclick="event.stopPropagation()">
<button class="mobile-nav-close" onclick="document.getElementById('mobileNav').classList.remove('open')">&times;</button>
<a href="/lp/job-seeker/area/">地域別求人</a>
<a href="/lp/job-seeker/guide/">転職ガイド</a>
<a href="/blog/">ブログ</a>
<a href="/about.html">会社概要</a>
</div>
</div>'''

FOOTER_HTML = '''<!-- Footer (LP統一 2026-04-20) -->
<footer class="site-footer">
<div class="footer-brand"><img src="/assets/logo-nursrobby.png" alt="ナースロビー" style="height:72px;width:auto;"></div>
<p class="footer-permit">有料職業紹介事業許可番号: 23-ユ-302928</p>
<p style="font-size:0.65rem;color:var(--text-muted);margin-top:6px;">施設データ出典: 厚生労働省 医療情報ネット / 病床機能報告（令和6年度）/ ハローワーク求人</p>
<div class="footer-links">
<a href="/privacy.html">プライバシーポリシー</a>
<a href="/terms.html">利用規約</a>
<a href="/about/editorial-policy.html">編集方針</a>
<a href="/blog/">ブログ</a>
<a href="/lp/job-seeker/area/">地域別求人</a>
<a href="/lp/job-seeker/guide/">転職ガイド</a>
</div>
<p class="footer-editorial">執筆: <a href="/about/editorial-policy.html">神奈川ナース転職編集部</a> / 厚生労働省許可 23-ユ-302928</p>
<p class="footer-copy"><a href="https://haruhi-medical.com/pages/about" rel="nofollow" target="_blank" style="color:inherit;text-decoration:underline;">会社概要</a></p>
<p class="footer-copy">&copy; 2026 ナースロビー All Rights Reserved.</p>
</footer>

<!-- Mobile Sticky CTA (LP統一) -->
<div class="mobile-sticky-cta" id="mobile-sticky-cta">
<a href="https://line.me/R/ti/p/@174cxnev" target="_blank" rel="noopener" class="mobile-sticky-line">LINEで求人を相談する →</a>
</div>'''

SCROLL_JS = '''<script>
(function(){
    var header = document.getElementById('site-header');
    var mobileCta = document.getElementById('mobile-sticky-cta');
    function onScroll() {
        var y = window.pageYOffset;
        if (header) { if (y > 10) { header.classList.add('scrolled'); } else { header.classList.remove('scrolled'); } }
        if (mobileCta) { if (y > 300) { mobileCta.classList.add('visible'); } else { mobileCta.classList.remove('visible'); } }
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
})();
</script>'''

LINK_CSS = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link href="/assets/design-tokens.css" rel="stylesheet">'''


def process(path: Path, dry: bool):
    content = path.read_text(encoding="utf-8")
    original = content
    changes = []

    # 1. design-tokens.css 未link → </head> 直前に追加
    if '/assets/design-tokens.css' not in content:
        content = content.replace('</head>', LINK_CSS + '\n</head>', 1)
        changes.append('link-css')

    # 2. 既存 <nav class="site-nav">...</nav> を LP header に置換 (area/guide)
    if re.search(r'<nav[^>]*class="site-nav"', content):
        content = re.sub(
            r'<nav[^>]*class="site-nav"[^>]*>[\s\S]*?</nav>',
            HEADER_HTML,
            content,
            count=1,
        )
        changes.append('replace-site-nav')

    # 3. 既存 <div class="site-header" style="..."> ... </div> (blog の inline) を置換
    #    手早い: 1行<div class="site-header" style="...">...</div> 形式のみ対応
    elif re.search(r'<div\s+class="site-header"\s+style=', content):
        # div タグだが内部に nested div や a が多い構造
        # 最初の <div class="site-header"...> から最初の </div> ではなく、対応する </div> を探す
        # 単純化: <div class="site-header" ...>...</div> までを1行で書いてる blog の構造を想定
        # 実構造: <div class="site-header" style=...><a>ロゴ</a><nav><a>...</a></nav></div>
        # 内部の </a></nav></div> まで含めて置換する
        content = re.sub(
            r'<div\s+class="site-header"\s+style="[^"]*">[\s\S]*?</div>\s*(?=\n|\s*<)',
            HEADER_HTML + '\n',
            content,
            count=1,
        )
        changes.append('replace-div-site-header')

    # 4. 既存 <footer class="footer" ...>...</footer> を置換 (area/guide)
    if re.search(r'<footer[^>]*class="footer"', content):
        content = re.sub(
            r'<footer[^>]*class="footer"[^>]*>[\s\S]*?</footer>',
            FOOTER_HTML,
            content,
            count=1,
        )
        changes.append('replace-footer-class')

    # 5. 既存 <footer style="..."> ...</footer> (blog inline) を置換
    elif re.search(r'<footer\s+style="[^"]*">', content):
        content = re.sub(
            r'<footer\s+style="[^"]*">[\s\S]*?</footer>',
            FOOTER_HTML,
            content,
            count=1,
        )
        changes.append('replace-footer-inline')

    # 6. display:none !important で site-header を隠す行を無効化
    if re.search(r'\.site-header[^{]*\{\s*display:\s*none\s*!important', content):
        content = re.sub(
            r'(\.site-header[^{]*\{\s*display:\s*none\s*!important[^}]*\})',
            r'/* removed: \1 */',
            content,
        )
        changes.append('unblock-site-header')

    # 7. スクロールJSが未追加なら </body> 直前に追加
    if 'mobile-sticky-cta' in content and "getElementById('site-header')" not in content:
        content = content.replace('</body>', SCROLL_JS + '\n</body>', 1)
        changes.append('scroll-js')

    if content == original:
        return False, ['no-change']
    if not dry:
        path.write_text(content, encoding="utf-8")
    return True, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    targets = []
    targets.extend((REPO / 'blog').glob('*.html'))
    targets.extend((REPO / 'lp/job-seeker/area').glob('*.html'))
    targets.extend((REPO / 'lp/job-seeker/guide').glob('*.html'))

    # 除外
    excluded = {
        REPO / 'lp/job-seeker/index.html',
        REPO / 'lp/job-seeker/guide/career-change.html',
    }
    targets = [p for p in targets if p not in excluded and '_backup' not in str(p)]

    changed = 0
    for t in sorted(targets):
        updated, notes = process(t, args.dry_run)
        if updated:
            changed += 1
            print(f"{'[DRY]' if args.dry_run else '[OK] '} {t.relative_to(REPO)}  [{','.join(notes)}]")
        else:
            print(f"[SKIP] {t.relative_to(REPO)}")

    print(f"\n{'Would update' if args.dry_run else 'Updated'}: {changed}/{len(targets)}")


if __name__ == '__main__':
    main()
