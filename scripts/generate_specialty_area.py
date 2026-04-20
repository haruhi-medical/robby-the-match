#!/usr/bin/env python3
"""診療科×エリア ロングテールSEOページ生成（Editorial Calm外装）。

5専門科 × 5主要市 = 最大25ページ（薄いコンテンツ回避のため施設数<3は除外）

実行:
    python3 -m scripts.generate_specialty_area --apply
    python3 -m scripts.generate_specialty_area --apply --force
"""
import argparse
import html
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
AREA_DIR = ROOT / "lp/job-seeker/area"
BASE_URL = "https://quads-nurse.com"
STATS_SRC = ROOT / "data" / "specialty_stats.json"

sys.path.insert(0, str(ROOT / "scripts"))
from generate_area_condition import load_v2_style, HEADER  # type: ignore
from apply_editorial_guide import GUIDE_COMPAT_CSS  # type: ignore

# 各専門科の固有テキスト
SPECIALTY_CONTENT = {
    "seishinka": {
        "ja": "精神科",
        "title_suffix": "の精神科看護師求人",
        "subtitle": "心のケアに向き合う看護師の転職を、静かに。",
        "sections": [
            ("精神科看護師の仕事内容", "精神科看護師は、統合失調症・うつ病・認知症・発達障害など、心の病を抱える患者さんの看護を担当します。身体疾患と異なり、コミュニケーションと観察力が重要で、急性期病棟・療養病棟・外来・訪問看護・デイケア・グループホームなど多様な配属先があります。医療行為よりも対話・環境調整・服薬管理の比重が高いのが特徴です。"),
            ("精神科看護の魅力と難しさ", "精神科の魅力は、患者さんの回復を中長期で見守れること、一般科より穏やかな勤務環境（急変が少ない）、夜勤負担が比較的軽いケースが多いこと。一方で難しさは、暴言・暴力のリスク、治療効果が見えにくい、看護観が揺らぎやすい、の3点。入職前に実際の現場を1日見学できる施設を選ぶと失敗が減ります。"),
            ("精神科看護師の年収相場", "精神科病院の看護師年収は神奈川県で約420〜520万円が相場。一般急性期より若干下がりますが、夜勤回数が月4回以下の施設も多く、ワークライフバランスを重視する方に人気です。精神科認定看護師資格を取得すると月3〜5万円の資格手当がつくケースもあります。"),
        ],
        "faq": [
            ("精神科未経験でも転職できますか？", "可能です。多くの精神科病院は未経験者向けの研修制度を持っており、3〜6ヶ月で独り立ちできます。身体合併症ケアもあるため、一般科経験があると重宝されます。"),
            ("暴力リスクが心配です。", "患者さんとの適切な距離の取り方・デエスカレーション技術を研修で学びます。看護師配置に余裕がある施設ほど安全対策が充実しています。"),
            ("夜勤の負担は？", "精神科の夜勤は急変が少ない分、身体負担は軽めです。ただし見守り業務が多く精神的負担は別の形で存在します。月4〜6回が一般的です。"),
        ],
    },
    "seikeigeka": {
        "ja": "整形外科",
        "title_suffix": "の整形外科看護師求人",
        "subtitle": "リハビリと手術、両面から回復を支える。",
        "sections": [
            ("整形外科看護師の仕事内容", "整形外科看護師は、骨折・脊椎疾患・関節疾患・スポーツ障害の患者さんの看護を担当します。手術前後のケア、リハビリテーション支援、ADL自立に向けた生活援助が中心業務。病棟だけでなく外来・手術室・リハビリ科との連携が多く、チーム医療の経験が積めます。"),
            ("整形外科看護の魅力", "患者さんの回復が目に見えやすく、退院時の笑顔を何度も見られる達成感が魅力です。急性期でも急変が比較的少なく、精神的負担が一般急性期より軽め。手術室配属では器械出し・外回り看護師として専門スキルを磨けます。"),
            ("整形外科看護師の年収相場", "神奈川県の整形外科病棟看護師の年収は約450〜560万円。急性期病院の中では標準的なレンジです。手術室配属は手術手当がつくケースもあり、年収+20〜40万円のプラスになることも。整形外科認定看護師資格で専門性を高める道もあります。"),
        ],
        "faq": [
            ("体力的にきついですか？", "患者さんの移乗・体位変換が多く腰への負担はあります。リフトや福祉機器が整った施設を選ぶと負担軽減につながります。"),
            ("手術室と病棟、どちらが先？", "病棟で基礎スキルを積んでから手術室配属が一般的。ただし新卒から手術室配属の施設もあります。どちらも体力と集中力が重要です。"),
            ("整形外科認定看護師の取得は大変？", "6ヶ月〜1年の教育課程＋実務経験5年が必要。資格取得後は月3〜5万円の手当＋転職市場価値UPが期待できます。"),
        ],
    },
    "naika": {
        "ja": "内科",
        "title_suffix": "の内科看護師求人",
        "subtitle": "幅広い疾患に対応する、看護の基本領域。",
        "sections": [
            ("内科看護師の仕事内容", "内科看護師は、生活習慣病・循環器・消化器・呼吸器・腎臓・糖尿病など幅広い疾患の患者さんを担当します。急性期から慢性期、外来まで配属先が多様で、看護師としての基礎スキルを総合的に身につけられる領域です。点滴・採血・検査介助・服薬指導・生活指導が主な業務。"),
            ("内科で身につくスキル", "アセスメント能力（バイタル変化から何を疑うか）、複数疾患を抱える患者さんへの全体観、服薬・栄養・生活指導の実践力が養われます。循環器内科→集中治療室、消化器内科→内視鏡室などへのキャリアパスも広く、次の専門分野への足場として理想的です。"),
            ("内科看護師の年収相場", "神奈川県の内科病棟看護師の年収は約450〜550万円。急性期病院なら夜勤手当込みで550〜600万円レンジ。外来クリニックは年収380〜450万円で日勤固定が中心。ライフステージに応じて急性期から外来へ移行する看護師も多いです。"),
        ],
        "faq": [
            ("内科と外科、どちらが新人に向いていますか？", "内科は観察眼・全体観を養いやすく、外科は処置・手技を早く覚えられる違いがあります。内科は将来他科へ移る際の応用が効きやすいため基礎として人気です。"),
            ("内科から専門科へ転向できますか？", "十分可能です。内科経験3年以上あれば循環器・消化器・腎臓・糖尿病などの専門病棟に移る道が多数開けます。"),
            ("外来内科の需要は？", "クリニック開業数が増えており、外来内科看護師の求人は神奈川県で常時多数あります。土日休・日勤固定を希望する方に人気です。"),
        ],
    },
    "shonika": {
        "ja": "小児科",
        "title_suffix": "の小児科看護師求人",
        "subtitle": "成長する子どもとご家族に寄り添う看護。",
        "sections": [
            ("小児科看護師の仕事内容", "小児科看護師は、新生児から思春期までの子どもの看護を担当します。一般小児科・NICU（新生児集中治療室）・PICU（小児集中治療室）・小児外科病棟など配属先は多様。処置への不安を和らげる関わり、ご家族への支援、成長・発達への配慮が業務の中心です。"),
            ("小児科看護の魅力", "子どもの回復力の高さ、日々の成長を感じられる喜びが最大の魅力。ご家族との長期的な関係構築もやりがいにつながります。一方、重症例や看取りに立ち会う精神的負担、感染症・事故予防の緊張感は常にあります。保育士資格があると配属に有利なケースも。"),
            ("小児科看護師の年収相場", "神奈川県の小児科病棟看護師の年収は約450〜550万円。NICU・PICUは夜勤手当＋特殊手当で年収+30〜60万円のプレミアムがつきます。大学病院の小児専門病棟はキャリア価値が高く、転職市場でも引く手あまたです。"),
        ],
        "faq": [
            ("小児科未経験でも転職できますか？", "一般病棟経験があれば十分歓迎されます。プリセプター制度が手厚い施設を選ぶと安心。新生児・乳幼児ケアの基礎は研修でカバーできます。"),
            ("NICUは倍率が高いですか？", "高めです。新卒よりも一般病棟で基礎を積んでからの応募が有利。配属希望は早めに出し、面接で熱意を伝えることが重要です。"),
            ("子育て中でも働けますか？", "院内保育所がある病院が多く、ママナースが活躍する病棟です。ただし夜勤・オンコール対応の負担があるため、日勤固定求人を選ぶ選択肢もあります。"),
        ],
    },
    "sanfujinka": {
        "ja": "産婦人科",
        "title_suffix": "の産婦人科看護師求人",
        "subtitle": "命の誕生と女性の健康を、そっと支える。",
        "sections": [
            ("産婦人科看護師の仕事内容", "産婦人科看護師は、妊娠・出産・産褥期のケアに加え、婦人科疾患（子宮筋腫・卵巣疾患・更年期障害等）の患者さんも担当します。配属先は産婦人科病棟・外来・分娩室・NICUなど多岐にわたり、助産師資格があると分娩介助の中心的役割を担えます。"),
            ("産婦人科看護の魅力と負担", "出産の瞬間に立ち会える感動、女性のライフステージ全般に関わる奥深さが魅力。一方で夜間・休日の分娩対応、不妊治療や死産への対応、感情労働の負担は大きめ。助産師資格取得による専門性アップで、より中心的な役割を担える道も。"),
            ("産婦人科看護師の年収相場", "神奈川県の産婦人科病棟看護師の年収は約460〜560万円。助産師資格があれば+30〜50万円のプレミアムで500〜610万円に。産科専門病院・大学病院の周産期センターは給与水準が高めで、専門性を評価される環境です。"),
        ],
        "faq": [
            ("助産師資格は必須ですか？", "必須ではありません。看護師でも産婦人科病棟・外来で多くの業務に携われます。分娩介助の中心役割は助産師が担いますが、チームの一員として十分活躍できます。"),
            ("男性看護師でも応募できますか？", "可能です。ただし患者層の関係で病棟内業務に配慮が必要な場面もあります。NICU・婦人科外来などは男女問わず配属されます。"),
            ("夜勤・オンコールは厳しい？", "分娩対応があるため夜間の緊張感は高めです。月4〜5回の夜勤が一般的で、分娩件数の多い病院ほど負担が大きくなります。"),
        ],
    },
}

CITIES = {
    "yokohama": ("横浜市", "関内・みなとみらい", "横浜市立大学附属市民総合医療センター"),
    "kawasaki": ("川崎市", "川崎駅・溝の口", "川崎市立川崎病院"),
    "sagamihara": ("相模原市", "橋本・町田境", "北里大学病院"),
    "fujisawa": ("藤沢市", "藤沢駅・湘南台", "藤沢市民病院"),
    "yokosuka": ("横須賀市", "横須賀中央", "横須賀共済病院"),
}

MIN_FACILITY_COUNT = 3  # これ未満は薄判定リスクで生成しない


def build_stats_section(stats: dict, specialty_ja: str, city_ja: str) -> str:
    """診療科×エリア固有の統計セクションを生成。"""
    parts = [f"      <h2>{html.escape(city_ja)}の{html.escape(specialty_ja)}求人データ</h2>"]

    summary = []
    if stats.get("facility_count"):
        summary.append(f"対象施設数 <strong>{stats['facility_count']}</strong>施設")
    if stats.get("job_count"):
        summary.append(f"現在の関連求人数 <strong>{stats['job_count']}</strong>件")
    if stats.get("annual_min") and stats.get("annual_max"):
        lo = round(stats["annual_min"] / 10000)
        hi = round(stats["annual_max"] / 10000)
        summary.append(f"月給平均からの年収換算 <strong>{lo}〜{hi}万円</strong>")
    if summary:
        parts.append(
            "      <p>" + " / ".join(summary) +
            f"（{specialty_ja}を標榜する施設を厚労省医療機能情報提供制度より抽出、求人はハローワーク公開データの関連キーワード集計）。</p>"
        )

    top = stats.get("top_facilities") or []
    if top:
        parts.append(f"      <h3>{specialty_ja}を標榜する代表施設</h3>")
        parts.append("      <ul>")
        for f in top[:5]:
            name = f.get("name") or ""
            if not name:
                continue
            sfx = []
            if f.get("sub_type"):
                sfx.append(f["sub_type"])
            if f.get("beds"):
                sfx.append(f"{f['beds']}床")
            if f.get("station"):
                st = f["station"]
                if f.get("minutes"):
                    st += f" 徒歩{f['minutes']}分"
                sfx.append(st)
            suf = "（" + " / ".join(sfx) + "）" if sfx else ""
            parts.append(f"        <li>{html.escape(name)}{html.escape(suf)}</li>")
        parts.append("      </ul>")
        parts.append(f"      <p>各施設との契約関係は個別異なります。応募前にナースロビーLINEで取扱い状況をご確認ください。</p>")

    inner = "\n".join(parts)
    return (
        "  <section>\n"
        "    <div class=\"container\">\n"
        f"{inner}\n"
        "    </div>\n"
        "  </section>"
    )


def build_page(city_slug, specialty_slug, stats_all, v2_style, compat_css):
    key = f"{city_slug}-{specialty_slug}"
    stats = stats_all.get(key, {})
    if stats.get("facility_count", 0) < MIN_FACILITY_COUNT:
        return None, None  # 薄判定回避でスキップ

    city_ja, area_desc, main_hospital = CITIES[city_slug]
    spec = SPECIALTY_CONTENT[specialty_slug]
    specialty_ja = spec["ja"]
    slug = f"{city_slug}-{specialty_slug}"
    canonical = f"{BASE_URL}/lp/job-seeker/area/{slug}.html"
    title = f"{city_ja}{spec['title_suffix']}｜ナースロビー"
    description = f"{city_ja}の{specialty_ja}看護師求人を探す。{area_desc}エリアから{main_hospital}まで、{specialty_ja}を標榜する施設のSEOまとめ。LINE完結・電話なし・手数料10%。"
    h1 = f"{city_ja}{spec['title_suffix']}"

    bc_payload = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "トップ", "item": f"{BASE_URL}/"},
            {"@type": "ListItem", "position": 2, "name": "地域別求人", "item": f"{BASE_URL}/lp/job-seeker/area/"},
            {"@type": "ListItem", "position": 3, "name": city_ja, "item": f"{BASE_URL}/lp/job-seeker/area/{city_slug}.html"},
            {"@type": "ListItem", "position": 4, "name": specialty_ja, "item": canonical},
        ],
    }
    faq_payload = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in spec["faq"]
        ],
    }
    article_payload = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": h1,
        "description": description,
        "author": {"@type": "Organization", "name": "神奈川ナース転職編集部"},
        "publisher": {"@type": "Organization", "name": "ナースロビー",
                      "logo": {"@type": "ImageObject", "url": f"{BASE_URL}/assets/ogp.png"}},
        "datePublished": "2026-04-21",
        "dateModified": "2026-04-21",
        "mainEntityOfPage": canonical,
    }

    sections_html_parts = []
    for h, body in spec["sections"]:
        body_local = body.replace("神奈川県", city_ja, 1) if city_ja != "神奈川県" else body
        sections_html_parts.append(
            "  <section>\n"
            "    <div class=\"container\">\n"
            f"      <h2>{html.escape(h)}</h2>\n"
            f"      <p>{html.escape(body_local)}</p>\n"
            "    </div>\n"
            "  </section>"
        )
    sections_html_parts.append(build_stats_section(stats, specialty_ja, city_ja))
    sections_html = "\n".join(sections_html_parts)

    faq_html_parts = []
    for q, a in spec["faq"]:
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
        area_slug=city_slug,
        area_ja=city_ja,
        condition_ja=specialty_ja,
        h1=html.escape(h1),
        subtitle=html.escape(spec["subtitle"]),
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
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.apply):
        print("--dry-run または --apply", file=sys.stderr)
        sys.exit(1)

    v2_style = load_v2_style()
    stats_all = json.loads(STATS_SRC.read_text(encoding="utf-8")) if STATS_SRC.exists() else {}
    if not stats_all:
        print("⚠️ specialty_stats.json が空。seo_fetch_specialty_stats.py を先に実行")
        return

    generated = 0
    skipped_thin = 0
    skipped_exists = 0
    for city_slug in CITIES:
        for spec_slug in SPECIALTY_CONTENT:
            slug, content = build_page(city_slug, spec_slug, stats_all, v2_style, GUIDE_COMPAT_CSS)
            if slug is None:
                skipped_thin += 1
                continue
            path = AREA_DIR / f"{slug}.html"
            if path.exists() and not args.force:
                skipped_exists += 1
                continue
            if args.apply:
                path.write_text(content, encoding="utf-8")
                print(f"  ✓ {slug}.html ({len(content)} bytes)")
            else:
                print(f"  [dry] {slug}.html ({len(content)} bytes)")
            generated += 1

    print(f"\n生成 {generated} / 施設数不足スキップ {skipped_thin} / 既存スキップ {skipped_exists}")


if __name__ == "__main__":
    main()
