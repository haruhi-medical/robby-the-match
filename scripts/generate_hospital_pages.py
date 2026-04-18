#!/usr/bin/env python3
"""
神奈川県の主要病院 30件のパイロットページ生成（Editorial Calm 外装）

入力: data/hospitals_top30.json（D1 facilities から抽出）
出力: lp/job-seeker/hospitals/<slug>.html

掲載方針（docs/hospital_page_copyright_memo.md 準拠）:
- 公表情報のみ（病床数・住所・最寄駅・診療科・看護師数）
- 病院のロゴ・写真は使わない
- 治療成果や病院の優劣比較は書かない
- 出典: 厚労省 e-Gov 医療情報ネット 明記
- 許可番号 23-ユ-302928 フッター明示

実行:
  python3 -m scripts.generate_hospital_pages --apply
"""

import argparse
import html
import json
import pathlib
import re
import sys

from scripts.apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOSPITALS_DIR = ROOT / "lp/job-seeker/hospitals"
DATA_JSON = ROOT / "data/hospitals_top30.json"
TEMPLATE_SRC = ROOT / "lp/job-seeker/area/yokohama-naka.html"  # v2適用済み
BASE_URL = "https://quads-nurse.com"
SOURCE_URL = "https://www.iryou.teikyouseido.mhlw.go.jp/"


def load_v2_style():
    m = re.search(r"<style>(.*?)</style>", TEMPLATE_SRC.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


def slugify(h):
    """id ベースの slug（日本語ローマ字化ライブラリ不要）"""
    return f"hospital-kana-{h['id']}"


def format_departments(raw, limit=10):
    if not raw:
        return "—"
    deps = [d.strip() for d in raw.split(",") if d.strip()]
    if len(deps) > limit:
        return "・".join(deps[:limit]) + f" 他{len(deps)-limit}診療科"
    return "・".join(deps)


HEADER = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">

<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '2326210157891886');
fbq('track', 'PageView');
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id=2326210157891886&ev=PageView&noscript=1"/></noscript>
<!-- End Meta Pixel Code -->

<link rel="icon" type="image/x-icon" href="/favicon.ico">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#F6F2E8">

<title>{title}</title>
<meta name="description" content="{description}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="article">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="https://quads-nurse.com/assets/ogp.png">
<meta property="og:site_name" content="ナースロビー">
<meta property="og:locale" content="ja_JP">
<meta name="robots" content="index, follow, max-snippet:-1, max-image-preview:large">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{description}">
<meta name="twitter:image" content="https://quads-nurse.com/assets/ogp.png">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@400;500;600&family=Noto+Sans+JP:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<script async src="https://www.googletagmanager.com/gtag/js?id=G-X4G2BYW13B"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-X4G2BYW13B');</script>

<script type="application/ld+json">{bc_json}</script>
<script type="application/ld+json">{faq_json}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"神奈川ナース転職","alternateName":"ナースロビー","url":"https://quads-nurse.com/"}}</script>

<style>
{v2_style}
{compat_css}
.hospital-info {{
  background: var(--bg-card);
  border: 1px solid var(--rule);
  padding: 24px 22px;
  margin: 24px 0;
}}
.hospital-info dl {{ display: grid; gap: 12px; }}
.hospital-info dt {{
  font-family: var(--font-mono);
  font-size: 0.68rem;
  letter-spacing: 0.14em;
  color: var(--ink-quiet);
  text-transform: uppercase;
  margin-bottom: 2px;
}}
.hospital-info dd {{
  font-size: 0.95rem;
  color: var(--ink);
  line-height: 1.75;
}}
.hospital-disclaimer {{
  font-size: 0.82rem;
  color: var(--ink-quiet);
  padding: 16px 0 0;
  border-top: 1px solid var(--rule);
  margin-top: 24px;
  line-height: 1.9;
}}
</style>
</head>
<body>

<nav class="site-nav" role="navigation" aria-label="メインナビゲーション">
  <div class="site-nav__inner">
    <a href="/" class="brand" aria-label="ナースロビー トップ">
      <span>ナースロビー</span>
      <span class="brand-tagline">Nurse Robby</span>
    </a>
    <a href="https://lin.ee/oUgDB3x" class="nav-cta" aria-label="LINEで求人を見る" rel="noopener">LINEで求人を見る →</a>
  </div>
</nav>

<nav class="breadcrumb" aria-label="パンくずリスト">
  <a href="/">TOP</a>
  <span class="breadcrumb__sep">/</span>
  <a href="/lp/job-seeker/hospitals/">主要病院</a>
  <span class="breadcrumb__sep">/</span>
  <span aria-current="page">{hospital_name}</span>
</nav>

<header class="hero">
  <div class="container">
    <h1>{h1}</h1>
    <p class="subtitle">{subtitle}</p>
    <a href="https://lin.ee/oUgDB3x" class="cta-button" rel="noopener">LINEで求人を見る →</a>
  </div>
</header>

<div class="container">
  <section>
    <div class="container">
      <h2>{hospital_name} の基本情報</h2>
      <div class="hospital-info">
        <dl>
          <div><dt>所在地</dt><dd>{address}</dd></div>
          <div><dt>最寄駅</dt><dd>{station}</dd></div>
          <div><dt>病床数</dt><dd>{bed_count}床</dd></div>
          <div><dt>看護師数（常勤）</dt><dd>{nurse_count}</dd></div>
          <div><dt>機能</dt><dd>{sub_type}</dd></div>
          <div><dt>標榜診療科</dt><dd>{departments}</dd></div>
        </dl>
      </div>
      <p class="hospital-disclaimer">※ 出典: 厚生労働省「医療情報ネット」公表データ（2026-03 時点）。個別条件は求人により異なります。本ページは公表情報に基づく情報提供であり、病院の広告ではありません。</p>
    </div>
  </section>

  <section>
    <div class="container">
      <h2>{hospital_name} で看護師として働く</h2>
      <p>{hospital_name}は{city}にある{type_desc}です。{bed_count}床の規模と{nurse_count_p}名規模の看護体制から、幅広いキャリアを積める環境が期待できます。急性期の経験を積みたい方、専門性を高めたい方、チーム医療を学びたい方にとって、選択肢の一つとして検討に値します。</p>
      <p>ナースロビーでは、{hospital_name}を含む{city}周辺の看護師求人を LINE で静かにご案内しています。名前もメールも不要、5問タップするだけ。気になる病院だけ担当者経由で詳細確認も可能です。</p>
    </div>
  </section>

  <section>
    <div class="container">
      <h2>周辺エリアの看護師求人</h2>
      <p>{city}エリアには{hospital_name}以外にも多くの医療機関があります。地域中核病院・回復期病院・クリニック・訪問看護ステーションまで、キャリアや生活スタイルに合わせて選べます。</p>
      <div class="related-links">
        <a href="/lp/job-seeker/area/{area_link}.html">{city}の看護師求人</a>
        <a href="/lp/job-seeker/area/{area_link}-nikkin.html">{city}の日勤求人</a>
        <a href="/lp/job-seeker/area/{area_link}-yakin.html">{city}の夜勤求人</a>
        <a href="/lp/job-seeker/guide/fee-comparison.html">手数料10%について</a>
      </div>
    </div>
  </section>

  <section>
    <div class="container">
      <h2>よくある質問</h2>
      <div class="faq-list">
        <details class="faq-item">
          <summary>{hospital_name}の求人を紹介してもらえますか？</summary>
          <div class="faq-body">ナースロビーでは非公開求人を含め、担当者が病院側と連携して求人情報をご案内します。LINEでエリアと希望条件をお伝えいただければ、該当する求人があるか確認します。</div>
        </details>
        <details class="faq-item">
          <summary>病院の口コミや評判は教えてもらえますか？</summary>
          <div class="faq-body">公的な公表情報（病床機能、職員数、受入体制）をもとに中立的な情報提供をしています。主観的な評判や未確認の噂については、ご本人が面接で直接質問される方が確実です。</div>
        </details>
        <details class="faq-item">
          <summary>病院への応募はナースロビー経由でないとできませんか？</summary>
          <div class="faq-body">いいえ、直接応募も可能です。ナースロビーは手数料10%で病院側の負担を抑え、電話営業なしでLINE完結する「静かな転職」をお手伝いしているだけです。比較検討用にお使いください。</div>
        </details>
      </div>
    </div>
  </section>
</div>

<section class="cta-band">
  <h2>まずはLINEで、静かに始める</h2>
  <p>名前もメールも不要。5問タップするだけで、{city}の看護師求人が届きます。</p>
  <a href="https://lin.ee/oUgDB3x" class="cta-button" rel="noopener">LINEで求人を見る →</a>
</section>

<footer class="footer" role="contentinfo">
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
</footer>

</body>
</html>
"""

# 市 → 既存 area slug（ロングテールとのリンク）
CITY_TO_AREA = {
    "横浜市": "yokohama", "川崎市": "kawasaki", "相模原市": "sagamihara",
    "藤沢市": "fujisawa", "小田原市": "odawara", "横須賀市": "yokosuka",
    "茅ヶ崎市": "chigasaki", "厚木市": "atsugi", "大和市": "yamato",
    "平塚市": "hiratsuka", "鎌倉市": "kamakura", "海老名市": "ebina",
    "伊勢原市": "isehara", "秦野市": "hadano",
}


def build_page(h, v2_style, compat_css):
    slug = slugify(h)
    canonical = f"{BASE_URL}/lp/job-seeker/hospitals/{slug}.html"
    title = f"{h['name']}の看護師求人・基本情報｜ナースロビー"
    description = f"{h['name']}（{h['city']} / {h['bed_count']}床）の公表情報と、周辺エリアの看護師求人をLINEで静かにご案内。手数料10%・電話なし・完全無料。"
    h1 = f"{h['name']}"
    city = h["city"] or "神奈川県"
    area_link = CITY_TO_AREA.get(city, "yokohama")
    subtitle = f"{city}・{h['bed_count']}床の医療機関の基本情報と周辺求人。"

    bc_payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "主要病院", "item": f"{BASE_URL}/lp/job-seeker/hospitals/"},
            {"@type": "ListItem", "position": 3, "name": h["name"], "item": canonical},
        ],
    }
    faq_payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"{h['name']}の求人を紹介してもらえますか？",
             "acceptedAnswer": {"@type": "Answer", "text": f"ナースロビーでは非公開求人を含め、担当者が病院側と連携して求人情報をご案内します。LINEでエリアと希望条件をお伝えいただければ、該当する求人があるか確認します。"}},
            {"@type": "Question", "name": "病院の口コミや評判は教えてもらえますか？",
             "acceptedAnswer": {"@type": "Answer", "text": "公的な公表情報をもとに中立的な情報提供をしています。主観的な評判や未確認の噂については、ご本人が面接で直接質問される方が確実です。"}},
            {"@type": "Question", "name": "病院への応募はナースロビー経由でないとできませんか？",
             "acceptedAnswer": {"@type": "Answer", "text": "いいえ、直接応募も可能です。ナースロビーは手数料10%で病院側の負担を抑え、電話営業なしでLINE完結する「静かな転職」をお手伝いしているだけです。"}},
        ],
    }

    station = h.get("nearest_station") or "—"
    if h.get("station_minutes"):
        station = f"{station}（徒歩約{h['station_minutes']}分）"

    sub_type = h.get("sub_type") or "総合病院"
    nurse_count = h.get("nurse_fulltime") or 0
    nurse_count_display = f"{nurse_count}名" if nurse_count else "公表なし"
    nurse_count_p = f"{int(nurse_count/50)*50}" if nurse_count >= 100 else "100"

    # 種別説明（sub_type ベース）
    type_desc_map = {
        "急性期": "急性期病院",
        "回復期": "回復期リハビリ病院",
        "慢性期": "療養型病院",
        "総合病院": "総合病院",
    }
    type_desc = type_desc_map.get(sub_type, "総合病院")

    departments_display = format_departments(h.get("departments"))

    content = HEADER.format(
        title=html.escape(title, quote=True),
        description=html.escape(description, quote=True),
        canonical=html.escape(canonical, quote=True),
        bc_json=json.dumps(bc_payload, ensure_ascii=False),
        faq_json=json.dumps(faq_payload, ensure_ascii=False),
        hospital_name=html.escape(h["name"]),
        h1=html.escape(h1),
        subtitle=html.escape(subtitle),
        address=html.escape(h.get("address") or "—"),
        station=html.escape(station),
        bed_count=h.get("bed_count") or "—",
        nurse_count=html.escape(nurse_count_display),
        nurse_count_p=nurse_count_p,
        sub_type=html.escape(sub_type),
        departments=html.escape(departments_display),
        city=html.escape(city),
        type_desc=html.escape(type_desc),
        area_link=area_link,
        v2_style=v2_style,
        compat_css=compat_css,
    )
    return slug, content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.apply:
        print("--apply を指定してください", file=sys.stderr)
        sys.exit(1)

    if not DATA_JSON.exists():
        print(f"データ不在: {DATA_JSON}", file=sys.stderr)
        sys.exit(1)

    hospitals = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    HOSPITALS_DIR.mkdir(parents=True, exist_ok=True)

    v2_style = load_v2_style()
    generated = []
    for h in hospitals:
        slug, content = build_page(h, v2_style, GUIDE_COMPAT_CSS)
        path = HOSPITALS_DIR / f"{slug}.html"
        path.write_text(content, encoding="utf-8")
        print(f"  ✓ {slug}.html {h['name']} ({h['city']} / {h['bed_count']}床)")
        generated.append(slug)

    # index ページ
    idx_items = []
    for h in hospitals:
        slug = slugify(h)
        idx_items.append(
            f'<article class="facility"><span class="facility__num">{h["bed_count"]}床</span>'
            f'<div><h3 class="facility__name"><a href="/lp/job-seeker/hospitals/{slug}.html">{html.escape(h["name"])}</a></h3>'
            f'<div class="facility__sub">{html.escape(h.get("city") or "")} / {html.escape(h.get("sub_type") or "総合病院")}</div></div>'
            f'<span class="facility__tag">{html.escape(h.get("sub_type") or "総合")}</span></article>'
        )
    idx_html = HEADER.format(
        title=html.escape("神奈川県の主要病院一覧｜ナースロビー", quote=True),
        description=html.escape("神奈川県の病床数上位30病院の基本情報を一覧で。住所・最寄駅・病床数・看護師数・標榜診療科。厚労省公表データに基づく。", quote=True),
        canonical=f"{BASE_URL}/lp/job-seeker/hospitals/",
        bc_json=json.dumps({"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{"@type":"ListItem","position":1,"name":"トップ","item":f"{BASE_URL}/"},{"@type":"ListItem","position":2,"name":"主要病院","item":f"{BASE_URL}/lp/job-seeker/hospitals/"}]}, ensure_ascii=False),
        faq_json=json.dumps({"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{"@type":"Question","name":"どの病院を掲載していますか？","acceptedAnswer":{"@type":"Answer","text":"神奈川県の病床数上位30件（公的データ）の基本情報を掲載しています。順次拡充予定です。"}}]}, ensure_ascii=False),
        hospital_name="神奈川県の主要病院",
        h1="神奈川県の主要病院一覧",
        subtitle="病床数100床以上 / 公表データ準拠。",
        address="—", station="—", bed_count="—", nurse_count="—", nurse_count_p="100",
        sub_type="—", departments="—", city="神奈川県", type_desc="主要病院",
        area_link="yokohama",
        v2_style=v2_style, compat_css=GUIDE_COMPAT_CSS,
    )
    # index 本文だけ差し替え
    idx_html = re.sub(
        r'<div class="hospital-info">.+?</div>\s*<p class="hospital-disclaimer">[^<]+</p>',
        '<div class="facility-list">' + "".join(idx_items) + '</div>',
        idx_html, flags=re.DOTALL, count=1,
    )
    # 「この病院で看護師として働く」section を削除
    idx_html = re.sub(
        r'<section>\s*<div class="container">\s*<h2>神奈川県の主要病院 で看護師として働く</h2>.+?</section>',
        "",
        idx_html, flags=re.DOTALL, count=1,
    )

    (HOSPITALS_DIR / "index.html").write_text(idx_html, encoding="utf-8")
    print(f"  ✓ index.html (主要病院一覧)")

    print(f"\n合計 {len(generated)+1} ページ (hospitals/ 配下)")


if __name__ == "__main__":
    main()
