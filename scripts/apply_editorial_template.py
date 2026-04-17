#!/usr/bin/env python3
"""
Editorial Calm Japan テンプレを area 全ページに適用。

- yokohama-naka-v2.html を雛形とし、各ページのtitle/description/canonical/og/h1/FAQ/BreadcrumbListを抽出
- 本文は汎用テンプレ（地名だけ差し替え）で統一。既存ページは _backup_20260418/ に退避
- FAQ/BCが既存ページに無い場合は汎用版を生成

実行:
  python3 scripts/apply_editorial_template.py --dry-run   # 出力先のみ、上書きしない
  python3 scripts/apply_editorial_template.py --apply      # 本番: 上書き + バックアップ
"""

import argparse
import html
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREA = ROOT / "lp/job-seeker/area"
BACKUP = AREA / "_backup_20260418"
TEMPLATE_SRC = AREA / "yokohama-naka-v2.html"

SKIP_NAMES = {"index.html", "yokohama-naka-v2.html"}
BASE_URL = "https://quads-nurse.com"


# ============ 抽出 ============
def extract_meta(src: str) -> dict:
    def r(pat, default=""):
        m = re.search(pat, src, re.DOTALL)
        return m.group(1) if m else default

    title = r(r"<title>([^<]+)</title>", "")
    description = r(r'name="description"\s+content="([^"]+)"', "")
    canonical = r(r'<link rel="canonical"\s+href="([^"]+)"', "")
    og_title = r(r'property="og:title"\s+content="([^"]+)"', title)
    og_description = r(r'property="og:description"\s+content="([^"]+)"', description)
    h1 = r(r"<h1[^>]*>([^<]+)</h1>", "").strip()

    # 地名抽出（h1 from "○○の看護師求人..."）
    area_ja = re.sub(r"の看護師.*$", "", h1).strip() if h1 else title.split("｜")[0]

    # BreadcrumbList JSON
    bc = None
    bc_match = re.search(r'\{\s*"@context"\s*:\s*"https://schema\.org"\s*,\s*"@type"\s*:\s*"BreadcrumbList".+?\]\s*\}',
                        src, re.DOTALL)
    if bc_match:
        bc = bc_match.group(0)

    # FAQPage JSON
    faq = None
    faq_match = re.search(r'\{\s*"@context"\s*:\s*"https://schema\.org"\s*,\s*"@type"\s*:\s*"FAQPage".+?\]\s*\}',
                        src, re.DOTALL)
    if faq_match:
        faq = faq_match.group(0)

    # FAQ Q&A抽出
    faq_pairs = []
    if faq:
        pairs = re.findall(r'"name"\s*:\s*"([^"]+)"[^}]+?"text"\s*:\s*"([^"]+)"', faq)
        faq_pairs = pairs[:5]

    return {
        "title": title,
        "description": description,
        "canonical": canonical,
        "og_title": og_title,
        "og_description": og_description,
        "h1": h1,
        "area_ja": area_ja,
        "bc_json": bc,
        "faq_json": faq,
        "faq_pairs": faq_pairs,
    }


# ============ 汎用FAQ生成（FAQ無しページ用） ============
def default_faq(area_ja: str) -> list[tuple[str, str]]:
    return [
        (f"{area_ja}で看護師の求人は見つかりますか？",
         f"{area_ja}および近隣エリアの看護師求人を、ハローワーク公開求人と非公開求人の両方から提案します。LINEで5問タップするだけで、あなたに合う5件をお届けします。"),
        ("電話営業は本当にありませんか？",
         "はい。ナースロビーは手数料10%で病院側の負担が軽いため、こちらから強引に電話でせかす必要がありません。連絡はすべてLINEで完結し、返信も気が向いたときで大丈夫です。"),
        (f"{area_ja}の看護師の平均年収はいくらですか？",
         "神奈川県の看護師平均としておおよそ480〜560万円が目安です。高度急性期病院では夜勤手当や特殊業務手当が上乗せされ、さらに高い水準も期待できます。"),
        ("匿名のまま相談できますか？",
         "LINE友だち追加だけで、名前・電話番号・メールアドレスは最後まで要りません。エリア・施設タイプ・働き方など最低限の条件のみ伺い、求人を提案します。"),
        ("いつでも辞められますか？",
         "いつでもLINEをブロックしていただいて大丈夫です。追撃の電話やメールは一切ありません。今すぐ転職しない方の情報収集にもお使いいただけます。"),
    ]


def default_breadcrumb(area_ja: str, canonical: str) -> list[tuple[str, str]]:
    return [
        ("トップ", f"{BASE_URL}/"),
        ("地域別求人", f"{BASE_URL}/lp/job-seeker/area/"),
        (area_ja, canonical or f"{BASE_URL}/lp/job-seeker/area/"),
    ]


def build_faq_jsonld(pairs: list[tuple[str, str]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            } for q, a in pairs
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


def build_bc_jsonld(items: list[tuple[str, str]]) -> str:
    payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": url}
            for i, (name, url) in enumerate(items)
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


# ============ テンプレ側の差し込み ============
def render(tpl: str, data: dict, fallback: dict) -> str:
    out = tpl

    # Meta
    out = out.replace(
        "<title>横浜市中区の看護師求人・転職情報｜ナースロビー</title>",
        f"<title>{html.escape(data['title'], quote=False)}</title>",
    )
    out = out.replace(
        '<meta name="description" content="横浜市中区の看護師求人・転職情報。関内・元町・本牧を擁する横浜の中心地。横浜市立大学附属市民総合医療センターなど高度医療機関が集積。LINE完結・電話なし・手数料10%。">',
        f'<meta name="description" content="{html.escape(data["description"], quote=True)}">',
    )
    out = out.replace(
        '<link rel="canonical" href="https://quads-nurse.com/lp/job-seeker/area/yokohama-naka.html">',
        f'<link rel="canonical" href="{html.escape(data["canonical"], quote=True)}">',
    )
    # OG
    out = out.replace(
        '<meta property="og:title" content="横浜市中区の看護師求人・転職情報｜ナースロビー">',
        f'<meta property="og:title" content="{html.escape(data["og_title"], quote=True)}">',
    )
    out = out.replace(
        '<meta property="og:description" content="横浜市中区の看護師求人・転職情報。関内・元町・本牧エリアで看護師として働く。LINE完結・電話なし・手数料10%。">',
        f'<meta property="og:description" content="{html.escape(data["og_description"], quote=True)}">',
    )
    out = out.replace(
        '<meta property="og:url" content="https://quads-nurse.com/lp/job-seeker/area/yokohama-naka.html">',
        f'<meta property="og:url" content="{html.escape(data["canonical"], quote=True)}">',
    )
    # Twitter
    out = out.replace(
        '<meta name="twitter:title" content="横浜市中区の看護師求人・転職情報｜ナースロビー">',
        f'<meta name="twitter:title" content="{html.escape(data["og_title"], quote=True)}">',
    )
    out = out.replace(
        '<meta name="twitter:description" content="横浜市中区の看護師求人・転職情報。関内・元町・本牧エリアで看護師として働く。LINE完結・電話なし・手数料10%。">',
        f'<meta name="twitter:description" content="{html.escape(data["og_description"], quote=True)}">',
    )

    # JSON-LD Breadcrumb (line-based find)
    bc_json = data["bc_json"] or fallback["bc_json"]
    out = re.sub(
        r'<!-- JSON-LD: BreadcrumbList -->\s*<script type="application/ld\+json">\s*\{[^<]+?\}\s*</script>',
        f'<!-- JSON-LD: BreadcrumbList -->\n<script type="application/ld+json">\n{bc_json}\n</script>',
        out, flags=re.DOTALL,
    )

    # JSON-LD FAQPage
    faq_json = data["faq_json"] or fallback["faq_json"]
    out = re.sub(
        r'<!-- JSON-LD: FAQPage -->\s*<script type="application/ld\+json">\s*\{[^<]+?\}\s*</script>',
        f'<!-- JSON-LD: FAQPage -->\n<script type="application/ld+json">\n{faq_json}\n</script>',
        out, flags=re.DOTALL,
    )

    # Breadcrumb HTML（動的生成）
    bc_items = data.get("bc_items") or fallback["bc_items"]
    bc_html = '<nav class="breadcrumb" aria-label="パンくずリスト">\n'
    for i, (name, url) in enumerate(bc_items):
        if i == len(bc_items) - 1:
            bc_html += f'  <span aria-current="page">{html.escape(name)}</span>\n'
        else:
            bc_html += f'  <a href="{html.escape(url, quote=True)}">{html.escape(name)}</a>\n'
            bc_html += '  <span class="breadcrumb__sep">/</span>\n'
    bc_html += "</nav>"

    out = re.sub(
        r'<nav class="breadcrumb" aria-label="パンくずリスト">.+?</nav>',
        bc_html, out, flags=re.DOTALL, count=1,
    )

    # Hero masthead number/area
    area_ja = data["area_ja"]
    out = re.sub(
        r'<span class="hero-masthead__num">[^<]+</span>',
        f'<span class="hero-masthead__num">{html.escape(area_ja)} — 看護師求人</span>',
        out, count=1,
    )

    # Hero H1（汎用化: 「〇〇で、静かに次の白衣を選ぶ。」）
    new_h1 = (
        '<h1 class="hero-title fade-up d-1">\n'
        f'          <span class="line">{html.escape(area_ja)}で、静かに、</span>\n'
        '          <span class="line">次の<span class="mark">白衣</span>を選ぶ。</span>\n'
        "        </h1>"
    )
    out = re.sub(
        r'<h1 class="hero-title fade-up d-1">.+?</h1>',
        new_h1, out, flags=re.DOTALL, count=1,
    )

    # Hero lead
    new_lead = (
        '<p class="hero-lead fade-up d-2">\n'
        f'          {html.escape(area_ja)}の看護師求人を、LINE で完結。<br>\n'
        "          電話営業は一切なし。名前もメールアドレスも、最後まで要りません。\n"
        "        </p>"
    )
    out = re.sub(
        r'<p class="hero-lead fade-up d-2">.+?</p>',
        new_lead, out, flags=re.DOTALL, count=1,
    )

    # Hero card
    sub_area = re.sub(r"^(横浜市|川崎市|相模原市)", "", area_ja) or area_ja
    if sub_area == area_ja:  # 市単位
        sub_area_display = "県内広域"
    else:
        sub_area_display = sub_area
    out = re.sub(
        r'<dl>\s*<div><dt>エリア</dt><dd>[^<]+</dd></div>\s*<div><dt>主要病院</dt><dd>[^<]+</dd></div>\s*<div><dt>平均年収</dt><dd>[^<]+</dd></div>\s*<div><dt>手数料</dt><dd>[^<]+</dd></div>\s*</dl>',
        (
            "<dl>\n"
            f"          <div><dt>エリア</dt><dd>{html.escape(sub_area_display)}</dd></div>\n"
            "          <div><dt>主要施設</dt><dd>LINEで提案</dd></div>\n"
            "          <div><dt>平均年収</dt><dd>480〜560万</dd></div>\n"
            "          <div><dt>手数料</dt><dd>業界平均の1/3</dd></div>\n"
            "        </dl>"
        ),
        out, flags=re.DOTALL, count=1,
    )

    # Chapter 01 head
    out = re.sub(
        r'<h2 class="section-head" id="ch01">[^<]+</h2>',
        f'<h2 class="section-head" id="ch01">{html.escape(area_ja)}の医療、その全体像。</h2>',
        out, count=1,
    )

    # Chapter 01 body（汎用化）
    out = re.sub(
        r'<div class="reading">\s*<p>\s*横浜市中区は、<strong>関内・元町・本牧・山下町</strong>.+?市内全域からのアクセスも良好です。\s*</p>\s*</div>',
        (
            '<div class="reading">\n'
            "      <p>\n"
            f"        <strong>{html.escape(area_ja)}</strong>は、神奈川県の医療・介護の現場が集まるエリア。\n"
            "        高度急性期から回復期・慢性期、クリニック、訪問看護ステーションまで、\n"
            "        看護師のキャリアの選択肢は多彩です。\n"
            "      </p>\n"
            '      <p style="margin-top: 20px;">\n'
            "        通勤圏内の主要駅からのアクセスも良好で、子育てと両立できる日勤求人から、\n"
            "        夜勤手当が厚い二交代制まで、働き方の幅も広く選べます。\n"
            "        ナースロビーでは、あなたの希望条件に合う求人を LINE で静かにお届けします。\n"
            "      </p>\n"
            "    </div>"
        ),
        out, flags=re.DOTALL, count=1,
    )

    # Chapter 03 head
    out = re.sub(
        r'<h2 class="section-head" id="ch03">[^<]+</h2>',
        f'<h2 class="section-head" id="ch03">{html.escape(area_ja)}の主な選択肢。</h2>',
        out, count=1,
    )

    # Chapter 03 facility list（汎用化）
    generic_facilities = (
        '<article class="facility">\n'
        '        <span class="facility__num">01</span>\n'
        '        <div>\n'
        '          <h3 class="facility__name">高度急性期・急性期病院</h3>\n'
        '          <div class="facility__sub">救急・専門外来・病棟 / 夜勤手当厚め</div>\n'
        '        </div>\n'
        '        <span class="facility__tag">急性期</span>\n'
        '      </article>\n'
        '      <article class="facility">\n'
        '        <span class="facility__num">02</span>\n'
        '        <div>\n'
        '          <h3 class="facility__name">回復期・慢性期病院</h3>\n'
        '          <div class="facility__sub">リハビリ / 病棟看護 / 夜勤ペースを選びやすい</div>\n'
        '        </div>\n'
        '        <span class="facility__tag">回復期</span>\n'
        '      </article>\n'
        '      <article class="facility">\n'
        '        <span class="facility__num">03</span>\n'
        '        <div>\n'
        '          <h3 class="facility__name">クリニック / 外来</h3>\n'
        '          <div class="facility__sub">日勤中心 / 外来・専門外来 / オンコールなし</div>\n'
        '        </div>\n'
        '        <span class="facility__tag">クリニック</span>\n'
        '      </article>\n'
        '      <article class="facility">\n'
        '        <span class="facility__num">04</span>\n'
        '        <div>\n'
        '          <h3 class="facility__name">訪問看護ステーション</h3>\n'
        '          <div class="facility__sub">在宅医療 / オンコール条件で選べる / 一対一のケア</div>\n'
        '        </div>\n'
        '        <span class="facility__tag">訪問看護</span>\n'
        '      </article>'
    )
    out = re.sub(
        r'<div class="facility-list">.+?</div>\s*</div>\s*</section>\s*<!-- 04\.',
        f'<div class="facility-list">\n      {generic_facilities}\n    </div>\n  </div>\n</section>\n\n<!-- 04.',
        out, flags=re.DOTALL, count=1,
    )

    # FAQ items (HTML <details>)
    faq_pairs = data["faq_pairs"] or fallback["faq_pairs"]
    faq_html_items = []
    for q, a in faq_pairs:
        faq_html_items.append(
            '      <details class="faq-item">\n'
            f'        <summary>{html.escape(q)}</summary>\n'
            f'        <div class="faq-body">{html.escape(a)}</div>\n'
            "      </details>"
        )
    faq_html = "\n".join(faq_html_items)

    out = re.sub(
        r'<div class="faq-list">\s*<details class="faq-item">.+?</div>\s*</div>\s*</section>',
        f'<div class="faq-list">\n{faq_html}\n    </div>\n  </div>\n</section>',
        out, flags=re.DOTALL, count=1,
    )

    # Final CTA — エリア名差し替え
    out = re.sub(
        r'<p>名前もメールも不要。5 問タップするだけで、[^<]+の求人が届きます。</p>',
        f'<p>名前もメールも不要。5 問タップするだけで、{html.escape(area_ja)}の求人が届きます。</p>',
        out, count=1,
    )

    return out


# ============ メイン ============
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="既存ファイル変更なし、ログのみ")
    ap.add_argument("--apply", action="store_true", help="本番: 上書き + バックアップ")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        print("--dry-run または --apply を指定してください")
        sys.exit(1)

    tpl = TEMPLATE_SRC.read_text(encoding="utf-8")

    if args.apply:
        BACKUP.mkdir(exist_ok=True)

    pages = sorted([p for p in AREA.glob("*.html") if p.name not in SKIP_NAMES and not p.name.startswith("_")])
    print(f"対象: {len(pages)} ページ")

    stats = {"ok": 0, "faq_fallback": 0, "bc_fallback": 0}

    for p in pages:
        try:
            src = p.read_text(encoding="utf-8")
            data = extract_meta(src)

            # Fallback 構築
            faq_pairs = data["faq_pairs"] or default_faq(data["area_ja"])
            bc_items_fallback = default_breadcrumb(data["area_ja"], data["canonical"])

            # BC items も既存から抜き出す（ただしJSONに"name"+"item"が対応してる）
            bc_items_existing = []
            if data["bc_json"]:
                bc_items_existing = re.findall(r'"name"\s*:\s*"([^"]+)"\s*,\s*"item"\s*:\s*"([^"]+)"', data["bc_json"])
            data["bc_items"] = bc_items_existing or bc_items_fallback

            fallback = {
                "faq_json": build_faq_jsonld(faq_pairs),
                "bc_json": build_bc_jsonld(bc_items_existing or bc_items_fallback),
                "faq_pairs": faq_pairs,
                "bc_items": bc_items_existing or bc_items_fallback,
            }

            if not data["faq_json"]:
                stats["faq_fallback"] += 1
            if not data["bc_json"]:
                stats["bc_fallback"] += 1

            # faq_pairs が空の場合は fallback で埋める（dataに反映）
            if not data["faq_pairs"]:
                data["faq_pairs"] = faq_pairs

            result = render(tpl, data, fallback)

            if args.apply:
                shutil.copy2(p, BACKUP / p.name)
                p.write_text(result, encoding="utf-8")
                print(f"  ✓ {p.name} ({data['area_ja']})")
            else:
                print(f"  [dry] {p.name} ({data['area_ja']}) | FAQ {'既存' if data['faq_json'] else '汎用'} | BC {'既存' if data['bc_json'] else '汎用'}")

            stats["ok"] += 1
        except Exception as e:
            print(f"  ✗ {p.name}: {e}")

    print(f"\n完了: {stats['ok']}/{len(pages)} | FAQ汎用: {stats['faq_fallback']} | BC汎用: {stats['bc_fallback']}")


if __name__ == "__main__":
    main()
