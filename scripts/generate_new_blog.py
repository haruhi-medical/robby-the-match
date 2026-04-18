#!/usr/bin/env python3
"""
blog 新規記事 3本 一括生成（Editorial Calm 外装 + BlogPosting JSON-LD）

実行:
  python3 -m scripts.generate_new_blog --apply
"""

import argparse
import html
import json
import pathlib
import re
import sys

from scripts.apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
TEMPLATE_SRC = ROOT / "lp/job-seeker/area/yokohama-naka.html"  # v2適用済み
BASE_URL = "https://quads-nurse.com"


def load_v2_style():
    m = re.search(r"<style>(.*?)</style>", TEMPLATE_SRC.read_text(encoding="utf-8"), re.DOTALL)
    return m.group(1) if m else ""


BLOG_POSTS = [
    {
        "slug": "denwa-vs-line",
        "title": "電話営業とLINE転職サポートの違い — 看護師が「静かに転職」できる仕組み",
        "description": "従来型の電話営業ゼロでLINEだけで完結する看護師転職サポート。電話・営業・プレッシャーに疲れた看護師が選ぶ新しい転職体験と、その裏側にある手数料10%の仕組みを解説。",
        "h1": "電話営業とLINE転職サポートの違い",
        "subtitle": "「静かに転職」を可能にする仕組みと、その裏側にある経済構造。",
        "bc_name": "電話営業とLINEサポートの違い",
        "sections": [
            ("従来の看護師転職エージェント — 電話営業が多い理由", "従来の看護師転職エージェントは、成約すると病院から**採用者年収の20〜30%**を成功報酬として受け取るビジネスモデル。高い手数料を回収するため、エージェント側は短期決戦で成約させたい動機が強く、結果として電話・メール・LINEでの追い込み営業が日常化してきました。看護師の側からは「もう疲れた」「夜勤明けに電話がしつこい」という声が絶えません。"),
            ("ナースロビーが電話しない理由 — 手数料10%という選択", "ナースロビーは手数料を**業界平均の約1/3（10%）**まで下げています。病院側の負担が軽くなる一方、エージェント側の粗利も縮小するため、電話営業で回収するビジネスモデルが成立しません。代わりに、LINE完結の匿名相談・求人提案にフォーカスし、看護師が「気が向いたときだけ返信」する静かな関係性を前提に設計しています。"),
            ("LINE完結で実現できること・できないこと", "できること: 匿名のまま求人10件+を閲覧／担当者に希望条件を伝える／面接日程調整／職務経歴書のドラフト相談。できないこと: 給与交渉や最終面接調整の一部は電話連絡が必要な場面もあります（ただし看護師側が希望する時間帯のみ）。ナースロビーでは**電話可否と希望時間帯**を最初にLINEで確認し、不要なら最後まで電話ゼロで完結できます。"),
            ("看護師が主導権を持てる仕組み", "電話営業は「エージェントがペースを作る」関係性でした。LINE完結は「看護師がペースを作る」関係性です。返信のタイミング・頻度・内容を看護師が決められます。合わないと感じたら、いつでもブロックで終了できます。主導権が看護師にあることが、長期的な信頼関係の前提だと考えています。"),
        ],
        "faq": [
            ("本当に最後まで電話なしで転職できますか？", "応募〜面接調整までLINEで完結可能です。最終的な面接日程の調整だけ、病院側の都合で電話になるケースがあります。その場合も希望時間帯を指定してもらえます。"),
            ("LINEのレスポンスが遅くても大丈夫？", "大丈夫です。数日返信がなくても催促の追撃はしません。気が向いたときに再開していただければ、同じ担当者が対応します。"),
            ("他のエージェントと併用できますか？", "可能です。比較検討する看護師も歓迎しています。ナースロビー一本で完結する必要はありません。"),
        ],
    },
    {
        "slug": "nurse-salary-trend-2026",
        "title": "2026年 看護師の給与動向レポート — 神奈川県を中心に",
        "description": "2026年の看護師給与トレンドを神奈川県のデータと全国平均で比較。経験年数別・施設タイプ別の年収レンジ、夜勤手当の相場、昇給カーブの実態を厚労省データをベースに整理。",
        "h1": "2026年 看護師の給与動向レポート",
        "subtitle": "神奈川県のデータと全国平均から読み解く、今の相場。",
        "bc_name": "2026年 看護師給与動向",
        "sections": [
            ("全国の看護師平均年収", "厚生労働省「令和5年 賃金構造基本統計調査」によると、看護師の全国平均年収は**約520万円**。2021年比で+20万円の上昇傾向にあります。背景には、コロナ禍を経て看護師の社会的重要性が再評価されたことと、医療機関間の人材獲得競争が激化していることがあります。ただし施設規模・地域・経験年数で大きな差があり、同じ県内でも年収レンジは200〜300万円の幅があります。"),
            ("神奈川県の看護師年収 — 経験年数別", "神奈川県の看護師年収レンジ（2026年目安）: 新卒〜3年 = 420〜470万円／3〜5年 = 460〜510万円／5〜10年 = 500〜580万円／10年以上 = 550〜650万円／管理職 = 650万円〜。全国平均より若干高水準ですが、家賃・物価も高いため、可処分所得の実態は都道府県ランキング中位レベルです。"),
            ("施設タイプ別の給与レンジ", "病院（急性期）が最も高水準で年収500〜650万円レンジ、夜勤手当込み。回復期・慢性期病院は450〜550万円。クリニックは400〜500万円（日勤中心）。訪問看護ステーションは450〜550万円（オンコール手当込みで+50〜80万円）。企業看護師・保育園看護師は380〜500万円（夜勤なし）。"),
            ("昇給カーブの実態と対策", "多くの病院で5〜7年目から昇給が鈍化し、月2,000〜5,000円の微増が続きます。給与を上げる現実的な手段は: ①夜勤回数を増やす（体力勝負）／②規模の大きい病院へ転職／③認定・専門看護師資格取得／④管理職登用／⑤美容クリニックなど高歩合施設への転身。ナースロビーでは個別条件に応じた給与交渉サポートも対応しています。"),
        ],
        "faq": [
            ("ボーナス込みの年収相場は？", "神奈川県の看護師の年間賞与は平均3.5〜4.5ヶ月分。月給×16〜17ヶ月 が年収目安になります。"),
            ("夜勤手当の相場は？", "2交代で1回12,000〜18,000円、3交代で深夜勤5,000〜10,000円が神奈川県内の相場です。"),
            ("転職で年収が上がる人の特徴は？", "夜勤可・急性期経験3年以上・特定の診療科スキルを持つ方は、転職で年収+30〜80万円のレンジが見込めます。"),
        ],
    },
    {
        "slug": "tenshoku-1week-model",
        "title": "看護師の転職 1週間モデル — 夜勤明けでも進める具体手順",
        "description": "看護師が夜勤明けや休みの日だけで転職活動を進める1週間モデル。LINE完結・匿名・電話なしの手順を、実際のタイムラインに沿って解説。在職中に無理なく進めたい人向け。",
        "h1": "看護師の転職 1週間モデル",
        "subtitle": "夜勤明け・休日だけで、在職中に無理なく進める。",
        "bc_name": "看護師の転職 1週間モデル",
        "sections": [
            ("Day 1（休日）— 条件整理と求人閲覧", "まず自分の転職条件を5つだけ書き出します: ①エリア ②施設タイプ（病院/クリニック/訪問看護） ③働き方（日勤のみ/夜勤あり/パート） ④希望年収 ⑤絶対避けたいこと。ナースロビーのLINEを友だち追加し、5問タップするだけで該当する求人が5件届きます。所要15〜30分。名前・電話・メール不要、匿名で進められます。"),
            ("Day 2〜3（夜勤明け）— 気になる病院だけ詳細確認", "届いた求人の中で気になるものを1〜3件に絞り、LINEで「この病院の看護体制を詳しく知りたい」と伝えます。担当者が病院側から情報を収集して返信します。返信までの間に、このブログや area ページで周辺エリアの相場を確認しておくと判断材料が揃います。夜勤明けの10〜20分で十分進められます。"),
            ("Day 4〜5（休日）— 職務経歴書の準備", "面接に進みたい病院が決まったら、職務経歴書を準備します。ナースロビーではAIが下書きを作成する機能も提供しています。過去の勤務先・担当科・学んだスキル・エピソードを伝えれば、下書きが返ってきます。自分で仕上げる時間は30〜60分程度。"),
            ("Day 6〜7（休日）— 面接日程調整と当日", "面接日程はLINEで調整。希望時間帯を伝えれば、病院側と担当者間で調整されます。最終候補の病院と面接、というのが一般的な流れ。面接後は「合う・合わない」の率直なフィードバックをLINEで担当者に送ります。その上で辞退または内定受諾を判断。1週間で内定確定する必要はなく、複数病院を比較して納得できる1件を選べます。"),
        ],
        "faq": [
            ("1週間で本当に転職できますか？", "1週間で内定まで進む方もいれば、2〜3ヶ月かけて比較する方もいます。重要なのは自分のペースで進められることです。"),
            ("在職中に面接に行く時間がありません。", "有給を半日単位で取得、夜勤明けの午後を使う、遅番の前の午前中を使うなどで対応できます。面接は1件30〜60分程度です。"),
            ("途中でやめたくなったらどうなりますか？", "LINEをブロックするだけで活動終了できます。連絡が来ることはありません。"),
        ],
    },
]


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

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@400;500;600&family=Noto+Sans+JP:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<script async src="https://www.googletagmanager.com/gtag/js?id=G-X4G2BYW13B"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','G-X4G2BYW13B');</script>

<script type="application/ld+json">{bc_json}</script>
<script type="application/ld+json">{faq_json}</script>
<script type="application/ld+json">{blog_json}</script>
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
  <a href="/blog/">ブログ</a>
  <span class="breadcrumb__sep">/</span>
  <span aria-current="page">{bc_name}</span>
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
  <p>名前もメールも不要。5問タップするだけで、神奈川の看護師求人が届きます。</p>
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


def build(post, v2_style, compat_css):
    canonical = f"{BASE_URL}/blog/{post['slug']}.html"
    bc = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"トップ","item":f"{BASE_URL}/"},
        {"@type":"ListItem","position":2,"name":"ブログ","item":f"{BASE_URL}/blog/"},
        {"@type":"ListItem","position":3,"name":post["bc_name"],"item":canonical},
    ]}
    faq = {"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}}
        for q,a in post["faq"]
    ]}
    blog_jsonld = {"@context":"https://schema.org","@type":"BlogPosting","headline":post["h1"],"description":post["description"],"author":{"@type":"Organization","name":"神奈川ナース転職編集部"},"publisher":{"@type":"Organization","name":"ナースロビー","logo":{"@type":"ImageObject","url":f"{BASE_URL}/assets/ogp.png"}},"datePublished":"2026-04-19","dateModified":"2026-04-19","mainEntityOfPage":canonical}

    sections_html = "\n".join(
        f"  <section>\n    <div class=\"container\">\n      <h2>{html.escape(h)}</h2>\n      <p>{html.escape(b)}</p>\n    </div>\n  </section>"
        for h, b in post["sections"]
    )
    faq_html = "\n".join(
        f"      <details class=\"faq-item\">\n        <summary>{html.escape(q)}</summary>\n        <div class=\"faq-body\">{html.escape(a)}</div>\n      </details>"
        for q, a in post["faq"]
    )

    return HEADER.format(
        title=html.escape(post["title"], quote=True),
        description=html.escape(post["description"], quote=True),
        canonical=html.escape(canonical, quote=True),
        bc_json=json.dumps(bc, ensure_ascii=False),
        faq_json=json.dumps(faq, ensure_ascii=False),
        blog_json=json.dumps(blog_jsonld, ensure_ascii=False),
        bc_name=html.escape(post["bc_name"]),
        h1=html.escape(post["h1"]),
        subtitle=html.escape(post["subtitle"]),
        sections_html=sections_html,
        faq_html=faq_html,
        v2_style=v2_style,
        compat_css=compat_css,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    if not args.apply:
        print("--apply を指定してください", file=sys.stderr)
        sys.exit(1)

    v2_style = load_v2_style()
    for post in BLOG_POSTS:
        out = BLOG / f"{post['slug']}.html"
        if out.exists():
            print(f"  [skip] {post['slug']}.html 既存")
            continue
        out.write_text(build(post, v2_style, GUIDE_COMPAT_CSS), encoding="utf-8")
        print(f"  ✓ {post['slug']}.html")


if __name__ == "__main__":
    main()
