#!/usr/bin/env python3
"""
Editorial Calm Japan 外装を guide 全ページに適用。

既存本文を完全保持、以下のみ差し替え:
- <style>: v2デザイントークン + 既存guide要素互換レイヤー
- <header class="site-header">: v2 .site-nav
- <div id="mobileNav">: 削除
- <footer class="site-footer">: v2 .footer
- Google Fonts: Shippori Mincho B1 / Noto Sans JP / JetBrains Mono
- chat.css 参照: 削除（guide ページでは不要）

実行:
  python3 scripts/apply_editorial_guide.py --dry-run    # 1ページだけ出力して停止
  python3 scripts/apply_editorial_guide.py --apply      # 本番: 全ページ上書き + バックアップ
"""

import argparse
import pathlib
import re
import shutil
import sys

from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
GUIDE = ROOT / "lp/job-seeker/guide"
BLOG = ROOT / "blog"
TEMPLATE_SRC = ROOT / "lp/job-seeker/area/yokohama-naka-v2.html"
SKIP = {"index.html"}

TARGET_DIRS = {"guide": GUIDE, "blog": BLOG}


def load_v2_style() -> str:
    """v2 テンプレの最初の <style>...</style> 中身を抽出"""
    src = TEMPLATE_SRC.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", src, re.DOTALL)
    if not m:
        raise RuntimeError("v2 template style not found")
    return m.group(1)


GUIDE_COMPAT_CSS = """
/* ====== guide 既存要素 互換レイヤー ====== */
.site-header, .mobile-nav, .mobile-nav-inner, .mobile-nav-close, .hamburger, .site-footer { display: none !important; }

/* Hero (既存 guide の大型緑バナー) */
header.hero {
  background: linear-gradient(135deg, var(--teal) 0%, #2f5e75 100%);
  color: #fff;
  padding: 64px 24px 72px;
  text-align: center;
  border-bottom: 1px solid var(--rule);
  position: relative;
  z-index: 2;
}
header.hero h1 {
  color: #fff;
  font-family: var(--font-display);
  font-size: clamp(1.7rem, 5vw, 2.5rem);
  font-weight: 500;
  margin-bottom: 18px;
  line-height: 1.5;
  letter-spacing: 0.02em;
}
header.hero .subtitle {
  font-size: 1rem;
  opacity: 0.95;
  margin-bottom: 26px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.92);
}

/* CTA button （既存 guide の .cta-button → LINE緑維持） */
.cta-button {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  background: var(--line);
  color: #fff !important;
  padding: 16px 32px;
  border-radius: 999px;
  text-decoration: none;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  box-shadow: 0 10px 28px rgba(6, 199, 85, 0.22);
  transition: transform 0.25s ease, box-shadow 0.3s ease;
}
.cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgba(6, 199, 85, 0.28);
}

/* 本文 section */
main section,
body > section,
.container > section {
  padding: clamp(56px, 8vw, 96px) 0;
  position: relative;
  z-index: 2;
}
main section:nth-child(even),
body > section:nth-child(even),
.container > section:nth-child(even) {
  background: var(--bg-card);
}

/* h2/h3 再定義 (本文内) */
main h2, .container h2, section h2 {
  font-family: var(--font-display);
  font-size: clamp(1.4rem, 3vw, 2rem);
  color: var(--ink);
  font-weight: 500;
  letter-spacing: 0.02em;
  border-left: 3px solid var(--teal);
  padding-left: 14px;
  margin-bottom: 24px;
  line-height: 1.45;
}
main h3, .container h3, section h3 {
  font-family: var(--font-display);
  font-size: 1.15rem;
  color: var(--ink);
  font-weight: 500;
  margin: 24px 0 12px;
}
main p, .container p, section p {
  font-size: 0.95rem;
  color: var(--ink-soft);
  line-height: 1.95;
  margin-bottom: 16px;
}
main p strong, .container p strong { font-weight: 600; color: var(--ink); }

/* data-table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  margin: 24px 0;
  background: var(--bg-card);
  box-shadow: none;
  border-radius: 0;
  overflow: visible;
  border-top: 1px solid var(--rule);
  font-size: 0.9rem;
}
.data-table th, .data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid var(--rule);
  text-align: left;
}
.data-table th {
  background: var(--bg-deep);
  color: var(--ink-quiet);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 500;
}

/* card (既存 guide の .card) */
.card {
  background: var(--bg-card);
  border-radius: 0;
  border: 1px solid var(--rule);
  padding: 26px 22px;
  margin: 20px 0;
  box-shadow: none;
  border-left: 3px solid var(--teal);
}
.card h3 { margin-top: 0; }
.card p:last-child { margin-bottom: 0; }

/* info-box */
.info-box {
  background: var(--bg-deep);
  border: 1px solid var(--rule);
  border-left: 3px solid var(--gold);
  border-radius: 0;
  padding: 22px;
  margin: 22px 0;
}
.info-box h4 {
  color: var(--gold);
  font-family: var(--font-display);
  font-size: 1rem;
  margin-bottom: 10px;
  font-weight: 500;
}

/* related-links chip */
.related-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin: 22px 0;
}
.related-links a {
  display: inline-block;
  padding: 8px 16px;
  background: var(--bg);
  color: var(--teal);
  border: 1px solid var(--teal-soft);
  border-radius: 999px;
  text-decoration: none;
  font-size: 0.85rem;
  transition: all 0.2s;
}
.related-links a:hover { background: var(--teal); color: #fff; }

/* cta-band （既存 guide の 末尾帯 CTA → v2 final-cta 風） */
.cta-band {
  background: #181A20;
  color: var(--bg);
  padding: clamp(64px, 9vw, 96px) 20px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
.cta-band::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(124, 163, 182, 0.14) 0%, transparent 55%),
    radial-gradient(circle at 80% 70%, rgba(158, 122, 63, 0.12) 0%, transparent 50%);
  pointer-events: none;
}
.cta-band h2 {
  color: #fff;
  border-left: none;
  text-align: center;
  padding-left: 0;
  font-size: clamp(1.5rem, 3.8vw, 2.3rem);
  font-weight: 400;
  letter-spacing: 0.04em;
  line-height: 1.55;
  position: relative;
  z-index: 2;
}
.cta-band p {
  color: rgba(255, 255, 255, 0.72);
  font-size: 0.95rem;
  margin-bottom: 32px;
  position: relative;
  z-index: 2;
}

/* point-list */
ul.point-list { padding-left: 20px; margin-bottom: 16px; }
ul.point-list li {
  margin-bottom: 8px;
  font-size: 0.9rem;
  color: var(--ink-soft);
  line-height: 1.9;
}
ul.point-list li strong { color: var(--ink); font-weight: 600; }

/* 既存 breadcrumb の互換 */
.breadcrumb a { color: var(--ink-quiet); border-bottom: 1px solid transparent; transition: border-color 0.2s; }
.breadcrumb a:hover { border-color: var(--teal); }

/* FAQ: guide の既存 .faq-item がある場合の互換 */
.faq-item {
  background: transparent;
  padding: 0;
  margin-bottom: 0;
  border-radius: 0;
  border-left: none;
  border-bottom: 1px solid var(--rule);
}
.faq-item summary {
  cursor: pointer;
  padding: 26px 0;
  list-style: none;
  display: flex;
  align-items: baseline;
  gap: 18px;
  font-family: var(--font-display);
  font-size: 1.02rem;
  color: var(--ink);
  font-weight: 500;
  position: relative;
  line-height: 1.5;
}
.faq-item summary::-webkit-details-marker { display: none; }
.faq-item summary::before {
  content: 'Q';
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: var(--teal);
  font-weight: 500;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}
.faq-item summary::after {
  content: '+';
  margin-left: auto;
  font-size: 1.3rem;
  color: var(--ink-quiet);
  transition: transform 0.3s ease;
  font-weight: 300;
  line-height: 1;
}
.faq-item[open] summary::after { transform: rotate(45deg); color: var(--teal); }
.faq-item[open] summary { color: var(--teal); }

/* Mobile fine-tuning */
@media (max-width: 699px) {
  header.hero { padding: 48px 20px 60px; }
  header.hero h1 { font-size: 1.45rem; line-height: 1.5; }
  header.hero .subtitle { font-size: 0.9rem; }
  main h2, .container h2, section h2 { font-size: 1.3rem; }
  .cta-button { padding: 14px 26px; font-size: 0.95rem; }
  .card { padding: 22px 18px; margin: 16px 0; }
  .data-table { font-size: 0.82rem; display: block; overflow-x: auto; }
  .related-links a { font-size: 0.8rem; padding: 7px 14px; }
}
"""

V2_NAV_HTML = """<nav class="site-nav" role="navigation" aria-label="メインナビゲーション">
  <div class="site-nav__inner">
    <a href="/" class="brand" aria-label="ナースロビー トップ">
      <span>ナースロビー</span>
      <span class="brand-tagline">Nurse Robby</span>
    </a>
    <a href="https://lin.ee/oUgDB3x" class="nav-cta" aria-label="LINEで求人を見る" rel="noopener">LINEで求人を見る →</a>
  </div>
</nav>"""

V2_FOOTER_HTML = """<footer class="footer" role="contentinfo">
  <div class="container">
    <div class="footer__grid">
      <div>
        <div class="brand" style="font-size: 1.15rem;"><span>ナースロビー</span><span class="brand-tagline">Nurse Robby</span></div>
        <p style="margin-top: 16px; font-size: 0.85rem; color: var(--ink-soft); max-width: 380px; line-height: 1.85;">神奈川県の看護師転職を、LINE で静かに完結させる AI コンシェルジュ。手数料 10% で、電話営業ゼロの転職体験を。</p>
      </div>
      <nav aria-label="エリア"><div class="footer__label">Areas</div><div class="footer__links"><a href="/lp/job-seeker/area/yokohama.html">横浜市</a><a href="/lp/job-seeker/area/kawasaki.html">川崎市</a><a href="/lp/job-seeker/area/sagamihara.html">相模原市</a><a href="/lp/job-seeker/area/">全エリア</a></div></nav>
      <nav aria-label="ガイド"><div class="footer__label">Guides</div><div class="footer__links"><a href="/lp/job-seeker/guide/">転職ガイド</a><a href="/lp/job-seeker/guide/career-change.html">キャリアチェンジ</a><a href="/lp/job-seeker/guide/fee-comparison.html">手数料について</a></div></nav>
    </div>
    <div class="legal"><div><span class="permit"><span class="permit__dot"></span>有料職業紹介事業許可 23-ユ-302928</span></div><div>© 2026 神奈川ナース転職 All Rights Reserved.</div></div>
  </div>
</footer>"""

FONTS_LINK = '<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@400;500;600&family=Noto+Sans+JP:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">'


def process_page(src: str, v2_style: str) -> str:
    soup = BeautifulSoup(src, "html.parser")

    # 1) <style> 書き換え
    style_tag = soup.find("style")
    if style_tag:
        style_tag.clear()
        style_tag.append(v2_style + "\n" + GUIDE_COMPAT_CSS)

    # 2) chat.css link 削除
    for link in soup.find_all("link", href=re.compile(r"chat\.css")):
        link.decompose()

    # 3) 既存 Google Fonts (Noto Sans JP のみ) link 削除
    for link in list(soup.find_all("link")):
        href = link.get("href") or ""
        if "fonts.googleapis.com" in href and "Shippori" not in href:
            link.decompose()
        if "fonts.gstatic.com" in href and link.get("rel") == ["preconnect"]:
            # preconnect は保持
            continue

    # 4) 新 Google Fonts link を head 末尾に追加
    fonts_soup = BeautifulSoup(FONTS_LINK, "html.parser")
    if soup.head:
        soup.head.append(fonts_soup)

    # 5) <header class="site-header"> 置換
    old_header = soup.find("header", class_="site-header")
    if old_header:
        nav_soup = BeautifulSoup(V2_NAV_HTML, "html.parser")
        old_header.replace_with(nav_soup)

    # 6) <div id="mobileNav"> 削除
    mobile_nav = soup.find("div", id="mobileNav")
    if mobile_nav:
        mobile_nav.decompose()

    # 7) <footer class="site-footer"> 置換
    old_footer = soup.find("footer", class_="site-footer")
    if old_footer:
        footer_soup = BeautifulSoup(V2_FOOTER_HTML, "html.parser")
        old_footer.replace_with(footer_soup)

    # 8) body に viewport theme-color 追加（<head>に未設定なら）
    if soup.head and not soup.find("meta", attrs={"name": "theme-color"}):
        theme_tag = soup.new_tag("meta", attrs={"name": "theme-color", "content": "#F6F2E8"})
        soup.head.append(theme_tag)

    return str(soup)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="1ページ出力、差分のみ")
    ap.add_argument("--apply", action="store_true", help="全ページ書き換え + バックアップ")
    ap.add_argument("--sample", default="career-change.html", help="dry-run 対象")
    ap.add_argument("--target", choices=list(TARGET_DIRS.keys()), default="guide", help="対象ディレクトリ")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        print("--dry-run または --apply を指定してください", file=sys.stderr)
        sys.exit(1)

    target_dir = TARGET_DIRS[args.target]
    backup_dir = target_dir / "_backup_20260418"
    v2_style = load_v2_style()

    if args.dry_run:
        path = target_dir / args.sample
        if not path.exists():
            print(f"not found: {path}", file=sys.stderr)
            sys.exit(1)
        src = path.read_text(encoding="utf-8")
        out = process_page(src, v2_style)
        out_path = target_dir / (path.stem + "-v2preview.html")
        out_path.write_text(out, encoding="utf-8")
        print(f"preview written: {out_path}")
        print(f"  input: {len(src)} bytes / output: {len(out)} bytes")
        return

    # apply
    backup_dir.mkdir(exist_ok=True)
    pages = sorted([p for p in target_dir.glob("*.html") if p.name not in SKIP and not p.name.startswith("_") and "v2preview" not in p.name])
    print(f"対象: {args.target} | {len(pages)} ページ")
    ok = err = 0
    for p in pages:
        try:
            src = p.read_text(encoding="utf-8")
            out = process_page(src, v2_style)
            shutil.copy2(p, backup_dir / p.name)
            p.write_text(out, encoding="utf-8")
            print(f"  ✓ {p.name}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {p.name}: {e}")
            err += 1
    print(f"\n完了: {ok}/{len(pages)} | エラー: {err}")


if __name__ == "__main__":
    main()
