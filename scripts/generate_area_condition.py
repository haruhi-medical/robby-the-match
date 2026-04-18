#!/usr/bin/env python3
"""
area × 条件 ロングテールページ生成（Editorial Calm 外装）

主要エリア5 × 条件4 = 20ページ:
エリア: yokohama / kawasaki / sagamihara / fujisawa / odawara
条件:   day (日勤) / night (夜勤) / part (パート) / visit (訪問看護)

実行:
  python3 -m scripts.generate_area_condition --apply
"""

import argparse
import html
import json
import pathlib
import re
import sys

from scripts.apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREA_DIR = ROOT / "lp/job-seeker/area"
TEMPLATE_SRC = ROOT / "lp/job-seeker/area/yokohama-naka.html"  # v2適用済み
BASE_URL = "https://quads-nurse.com"


def load_v2_style():
    m = re.search(r"<style>(.*?)</style>", TEMPLATE_SRC.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


AREAS = [
    # Phase 1 (既存)
    ("yokohama", "横浜市", "関内・元町・みなとみらい", "横浜市立大学附属市民総合医療センター"),
    ("kawasaki", "川崎市", "川崎駅・溝の口", "川崎市立川崎病院"),
    ("sagamihara", "相模原市", "橋本・町田境", "北里大学病院"),
    ("fujisawa", "藤沢市", "藤沢駅・湘南台", "藤沢市民病院"),
    ("odawara", "小田原市", "小田原駅周辺", "小田原市立病院"),
    # Phase 2 (新規: 残り26エリア)
    ("atsugi", "厚木市", "本厚木駅周辺", "厚木市立病院"),
    ("chigasaki", "茅ヶ崎市", "茅ヶ崎駅周辺", "茅ヶ崎市立病院"),
    ("ebina", "海老名市", "海老名駅周辺", "海老名総合病院"),
    ("hadano", "秦野市", "秦野駅周辺", "秦野赤十字病院"),
    ("hakone", "箱根町", "箱根湯本駅周辺", "神奈川県立足柄上病院"),
    ("hiratsuka", "平塚市", "平塚駅周辺", "平塚市民病院"),
    ("isehara", "伊勢原市", "伊勢原駅周辺", "東海大学医学部付属病院"),
    ("kaisei", "開成町", "開成駅周辺", "神奈川県立足柄上病院"),
    ("kamakura", "鎌倉市", "鎌倉駅周辺", "湘南鎌倉総合病院"),
    ("matsuda", "松田町", "松田駅周辺", "神奈川県立足柄上病院"),
    ("minamiashigara", "南足柄市", "大雄山駅周辺", "神奈川県立足柄上病院"),
    ("ninomiya", "二宮町", "二宮駅周辺", "平塚市民病院"),
    ("oiso", "大磯町", "大磯駅周辺", "東海大学医学部付属大磯病院"),
    ("yamakita", "山北町", "山北駅周辺", "神奈川県立足柄上病院"),
    ("yamato", "大和市", "大和駅周辺", "大和市立病院"),
    ("yokosuka", "横須賀市", "横須賀中央駅周辺", "横須賀共済病院"),
    ("yokohama-aoba", "横浜市青葉区", "あざみ野駅周辺", "昭和大学横浜市北部病院"),
    ("yokohama-asahi", "横浜市旭区", "二俣川駅周辺", "聖マリアンナ医科大学横浜市西部病院"),
    ("yokohama-kanagawa", "横浜市神奈川区", "東神奈川駅周辺", "神奈川県警友会けいゆう病院"),
    ("yokohama-kohoku", "横浜市港北区", "新横浜駅周辺", "新横浜記念病院"),
    ("yokohama-konan", "横浜市港南区", "上大岡駅周辺", "横浜市立市民病院"),
    ("yokohama-minami", "横浜市南区", "弘明寺駅周辺", "横浜市立大学附属市民総合医療センター"),
    ("yokohama-naka", "横浜市中区", "関内・元町・本牧", "横浜市立大学附属市民総合医療センター"),
    ("yokohama-nishi", "横浜市西区", "横浜駅周辺", "横浜市立みなと赤十字病院"),
    ("yokohama-totsuka", "横浜市戸塚区", "戸塚駅周辺", "横浜市立戸塚病院"),
    ("yokohama-tsurumi", "横浜市鶴見区", "鶴見駅周辺", "済生会横浜市東部病院"),
]

CONDITIONS = {
    "day": {
        "label_ja": "日勤",
        "label_slug": "nikkin",
        "title_suffix": "の日勤看護師求人",
        "subtitle": "夜勤なしで働ける看護師求人を、LINEで静かに。",
        "sections": [
            ("日勤のみ求人が多い施設タイプ", "日勤のみで働ける看護師求人は、クリニック・外来・健診センター・訪問看護（オンコールなし条件）・企業看護室・保育園看護師・介護施設（日勤帯のみ）などに多く存在します。病棟勤務に比べて夜勤手当がない分、基本給の交渉や休日数の条件で総合的に判断することが大切です。"),
            ("日勤看護師の年収目安", "神奈川県で日勤のみのフルタイム看護師の年収は、おおよそ380〜470万円が目安です。夜勤手当がないため病棟勤務より60〜120万円低くなる傾向がありますが、身体的負担は大きく軽減されます。時短勤務や週4日勤務など柔軟な働き方も選びやすくなります。"),
            ("探すときに確認したいこと", "求人票の「シフト」欄を必ず確認し、日勤のみ固定か変則日勤（早番・遅番あり）かを見分けます。土日祝休も条件に加えるなら、クリニックか健診センターが有力候補。LINEで希望を5つタップするだけで、ナースロビーが該当条件の求人を届けます。"),
        ],
        "faq": [
            ("日勤のみで年収500万は可能ですか？", "管理職や経験年数10年以上の看護師、または訪問看護ステーション管理者なら達成可能なレンジです。クリニック勤務のみでは難しいため、役職や専門スキルが鍵になります。"),
            ("土日祝休の日勤求人はありますか？", "企業看護室・保育園看護師・健診センター・一部クリニックに多数あります。LINE で土日祝休を条件に指定してください。"),
            ("日勤のみでブランクから復帰できますか？", "クリニック・訪問看護・介護施設はブランクOKの求人が多いです。研修制度が整った施設を優先提案します。"),
        ],
    },
    "night": {
        "label_ja": "夜勤あり",
        "label_slug": "yakin",
        "title_suffix": "の夜勤看護師求人",
        "subtitle": "夜勤手当で年収アップを狙う看護師求人。",
        "sections": [
            ("夜勤のある施設タイプ", "夜勤のある看護師求人は急性期病院・回復期病院・療養型病院・有床クリニック・一部の介護施設（特養など）に多く存在します。2交代制（日勤+16時間夜勤）と3交代制（日勤+準夜+深夜）で身体負担が大きく異なるため、自分の生活リズムに合う方を選ぶことが重要です。"),
            ("夜勤看護師の年収目安", "神奈川県で夜勤ありのフルタイム看護師の年収は、おおよそ480〜580万円が目安です。夜勤1回あたりの手当は2交代で約12,000〜18,000円、3交代で深夜5,000〜10,000円。月4〜5回の夜勤で年収が60〜100万円上乗せされます。"),
            ("体に負担をかけない夜勤シフトの選び方", "夜勤の頻度は月4〜5回が目安。それを超えると健康への影響が大きくなります。インターバル（勤務間休息）が11時間以上確保されているか、夜勤明けの翌日は必ず休日になっているか、を面接で確認してください。ナースロビーでは担当者経由で詳細確認できます。"),
        ],
        "faq": [
            ("夜勤専従の求人はありますか？", "神奈川県内でも夜勤専従（深夜勤のみ）の求人はあります。週2〜3回の出勤で月収30〜40万円超も可能ですが、体力的負担が大きいので年齢・健康状態と相談を。"),
            ("2交代と3交代、どちらが楽ですか？", "人によります。2交代は1回の拘束時間が長いが休みが取りやすい、3交代は短時間勤務だが生活リズムが乱れやすい、という特徴があります。"),
            ("夜勤回数を減らす交渉は可能ですか？", "育児・介護・持病を理由に減らす交渉は十分可能です。ナースロビーの担当者が条件調整します。"),
        ],
    },
    "part": {
        "label_ja": "パート",
        "label_slug": "part",
        "title_suffix": "のパート看護師求人",
        "subtitle": "週2〜4日で働ける看護師求人。",
        "sections": [
            ("パート看護師の勤務形態", "パート看護師は週2〜4日、1日4〜6時間からの勤務が一般的。クリニック・外来・訪問看護・介護施設に求人が多く、扶養内（年103万/130万以下）で働きたいママナースにも人気の働き方です。時給は1,600〜2,200円が神奈川県の相場です。"),
            ("扶養内と扶養外の判断", "世帯収入や配偶者の税制・社会保険を踏まえて決めます。103万円までなら所得税非課税、130万円までなら社会保険の扶養内。超えると世帯手取りが一時的に減ることもあるため、シミュレーションが大切です。ナースロビーでは詳細相談にも対応します。"),
            ("子育てとの両立求人の探し方", "「保育園の送迎時間」「学校行事で休める」「子の看護休暇あり」という条件で探すと、実質的なママナース歓迎の施設が見つかります。院内保育所があるかも重要な判断材料です。"),
        ],
        "faq": [
            ("週1日のパートもありますか？", "クリニック・訪問看護で週1日の求人も少数あります。ただし選択肢は限られるので、LINE で希望を伝えて相談ください。"),
            ("パートでもボーナスは出ますか？", "支給する施設とそうでない施設が混在します。支給があれば年間0.5〜2ヶ月分の水準。求人票と面接で確認を。"),
            ("扶養内で働きたいのですが相談できますか？", "ナースロビー担当者が勤務時間・時給・月上限の調整まで対応します。"),
        ],
    },
    "visit": {
        "label_ja": "訪問看護",
        "label_slug": "houmon",
        "title_suffix": "の訪問看護ステーション求人",
        "subtitle": "在宅医療の現場で、一対一のケアを。",
        "sections": [
            ("訪問看護ステーションの仕事", "訪問看護ステーションの看護師は、利用者宅を訪問して医療ケアを提供します。病棟と違い一対一で向き合える時間が長く、看護の原点に近い働き方。1日4〜6件の訪問が一般的で、移動時間も勤務時間に含まれます。"),
            ("オンコール条件を必ず確認", "訪問看護で最も重要なのがオンコール（夜間・休日の緊急電話対応）。月4〜8回のオンコール当番が一般的で、手当は1回2,000〜5,000円。オンコールなしの求人もあるため、生活スタイルに合わせて選びましょう。"),
            ("訪問看護の年収と未経験可否", "神奈川県の訪問看護師の年収は450〜550万円が目安。オンコール手当込みで550〜650万円の水準も。病棟経験3年以上がある看護師は未経験でも採用されやすく、研修制度も整ってきています。"),
        ],
        "faq": [
            ("車の運転が苦手でも訪問看護はできますか？", "神奈川県内では自転車・電動自転車のみで訪問可能なステーションも多数あります。都市部ほど車不要の求人が多いです。"),
            ("訪問看護は一人で判断が難しくないですか？", "初回半年は先輩と同行訪問が基本。不安な症例は電話で相談できる体制が整った事業所を選ぶと安心です。"),
            ("未経験でも採用されますか？", "病棟経験3年以上あれば歓迎される事業所が多いです。研修制度が整った大手・医療法人系を優先提案します。"),
        ],
    },
}


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
<link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
<link rel="apple-touch-icon" sizes="180x180" href="/assets/apple-touch-icon.png">
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
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
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
<script type="application/ld+json">{article_json}</script>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"Organization","name":"神奈川ナース転職","alternateName":"ナースロビー","url":"https://quads-nurse.com/"}}</script>

<style>
{v2_style}
{compat_css}
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
  <a href="/lp/job-seeker/area/">エリア</a>
  <span class="breadcrumb__sep">/</span>
  <a href="/lp/job-seeker/area/{area_slug}.html">{area_ja}</a>
  <span class="breadcrumb__sep">/</span>
  <span aria-current="page">{condition_ja}</span>
</nav>

<header class="hero">
  <div class="container">
    <h1>{h1}</h1>
    <p class="subtitle">{subtitle}</p>
    <a href="https://lin.ee/oUgDB3x" class="cta-button" rel="noopener">LINEで求人を見る →</a>
  </div>
</header>

<div class="container">
{sections_html}
</div>

<section>
  <div class="container">
    <h2>よくある質問</h2>
    <div class="faq-list">
{faq_html}
    </div>
  </div>
</section>

<section class="cta-band">
  <h2>まずはLINEで、静かに始める</h2>
  <p>名前もメールも不要。5問タップするだけで、{area_ja}の{condition_ja}看護師求人が届きます。</p>
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


def build_page(area_tuple, cond_slug, cond, v2_style, compat_css):
    area_slug, area_ja, area_desc, main_hospital = area_tuple
    slug = f"{area_slug}-{cond['label_slug']}"
    canonical = f"{BASE_URL}/lp/job-seeker/area/{slug}.html"
    title = f"{area_ja}{cond['title_suffix']}｜ナースロビー"
    description = f"{area_ja}の{cond['label_ja']}看護師求人を探す。{area_desc}エリアから{main_hospital}まで。LINE完結・電話なし・手数料10%で、静かに次の職場を見つけられます。"
    h1 = f"{area_ja}の{cond['label_ja']}看護師求人"

    bc_payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "地域別求人", "item": f"{BASE_URL}/lp/job-seeker/area/"},
            {"@type": "ListItem", "position": 3, "name": area_ja, "item": f"{BASE_URL}/lp/job-seeker/area/{area_slug}.html"},
            {"@type": "ListItem", "position": 4, "name": cond["label_ja"], "item": canonical},
        ],
    }
    faq_payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in cond["faq"]
        ],
    }
    article_payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": h1,
        "description": description,
        "author": {"@type": "Organization", "name": "神奈川ナース転職編集部"},
        "publisher": {
            "@type": "Organization",
            "name": "ナースロビー",
            "logo": {"@type": "ImageObject", "url": f"{BASE_URL}/assets/ogp.png"},
        },
        "datePublished": "2026-04-18",
        "dateModified": "2026-04-18",
        "mainEntityOfPage": canonical,
    }

    sections_html_parts = []
    for h, body in cond["sections"]:
        intro = body.replace("神奈川県", area_ja, 1) if area_ja != "神奈川県" else body
        sections_html_parts.append(
            "  <section>\n"
            "    <div class=\"container\">\n"
            f"      <h2>{html.escape(h)}</h2>\n"
            f"      <p>{html.escape(intro)}</p>\n"
            "    </div>\n"
            "  </section>"
        )
    sections_html = "\n".join(sections_html_parts)

    faq_html_parts = []
    for q, a in cond["faq"]:
        faq_html_parts.append(
            "      <details class=\"faq-item\">\n"
            f"        <summary>{html.escape(q)}</summary>\n"
            f"        <div class=\"faq-body\">{html.escape(a)}</div>\n"
            "      </details>"
        )
    faq_html = "\n".join(faq_html_parts)

    content = HEADER.format(
        title=html.escape(title, quote=True),
        description=html.escape(description, quote=True),
        canonical=html.escape(canonical, quote=True),
        bc_json=json.dumps(bc_payload, ensure_ascii=False),
        faq_json=json.dumps(faq_payload, ensure_ascii=False),
        article_json=json.dumps(article_payload, ensure_ascii=False),
        area_slug=area_slug,
        area_ja=area_ja,
        condition_ja=cond["label_ja"],
        h1=html.escape(h1),
        subtitle=html.escape(cond["subtitle"]),
        sections_html=sections_html,
        faq_html=faq_html,
        v2_style=v2_style,
        compat_css=compat_css,
    )
    return slug, content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        print("--dry-run または --apply", file=sys.stderr)
        sys.exit(1)

    v2_style = load_v2_style()
    generated = []
    skipped = 0
    for area_tuple in AREAS:
        for cond_slug, cond in CONDITIONS.items():
            slug, content = build_page(area_tuple, cond_slug, cond, v2_style, GUIDE_COMPAT_CSS)
            path = AREA_DIR / f"{slug}.html"
            if path.exists():
                skipped += 1
                continue
            if args.apply:
                path.write_text(content, encoding="utf-8")
                print(f"  ✓ {slug}.html ({len(content)} bytes)")
            else:
                print(f"  [dry] {slug}.html ({len(content)} bytes)")
            generated.append(slug)

    print(f"\n新規生成 {len(generated)} ページ / 既存スキップ {skipped}")


if __name__ == "__main__":
    main()
