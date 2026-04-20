#!/usr/bin/env python3
"""area/index.html に 124 条件別ページへの内部リンクセクションを差し込む。

対象: <!-- AREA_CONDITION_LINKS_START/END --> 間を置換（無ければ既存CTAの直前に挿入）。
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
TARGET = ROOT / "lp/job-seeker/area/index.html"

AREAS = [
    ("yokohama", "横浜市"),
    ("kawasaki", "川崎市"),
    ("sagamihara", "相模原市"),
    ("fujisawa", "藤沢市"),
    ("odawara", "小田原市"),
    ("atsugi", "厚木市"),
    ("chigasaki", "茅ヶ崎市"),
    ("ebina", "海老名市"),
    ("hadano", "秦野市"),
    ("hakone", "箱根町"),
    ("hiratsuka", "平塚市"),
    ("isehara", "伊勢原市"),
    ("kaisei", "開成町"),
    ("kamakura", "鎌倉市"),
    ("matsuda", "松田町"),
    ("minamiashigara", "南足柄市"),
    ("ninomiya", "二宮町"),
    ("oiso", "大磯町"),
    ("yamakita", "山北町"),
    ("yamato", "大和市"),
    ("yokosuka", "横須賀市"),
    ("yokohama-aoba", "横浜市青葉区"),
    ("yokohama-asahi", "横浜市旭区"),
    ("yokohama-kanagawa", "横浜市神奈川区"),
    ("yokohama-kohoku", "横浜市港北区"),
    ("yokohama-konan", "横浜市港南区"),
    ("yokohama-minami", "横浜市南区"),
    ("yokohama-naka", "横浜市中区"),
    ("yokohama-nishi", "横浜市西区"),
    ("yokohama-totsuka", "横浜市戸塚区"),
    ("yokohama-tsurumi", "横浜市鶴見区"),
]

CONDITIONS = [
    ("日勤のみ", "nikkin", "夜勤なし・残業少なめで働きたい方向け"),
    ("夜勤あり", "yakin", "夜勤手当で年収UPを狙う病院勤務"),
    ("パート", "part", "週2〜4日・扶養内OKの短時間勤務"),
    ("訪問看護", "houmon", "1対1の在宅ケア。神奈川県内のST求人"),
]

# 診療科×主要5市の追加エリア（2026-04-21）
SPECIALTIES_WITH_AREAS = [
    ("精神科", "seishinka"),
    ("整形外科", "seikeigeka"),
    ("内科", "naika"),
    ("小児科", "shonika"),
    ("産婦人科", "sanfujinka"),
]
SPECIALTY_CITIES = [
    ("yokohama", "横浜市"),
    ("kawasaki", "川崎市"),
    ("sagamihara", "相模原市"),
    ("fujisawa", "藤沢市"),
    ("yokosuka", "横須賀市"),
]

START_MARKER = "<!-- AREA_CONDITION_LINKS_START -->"
END_MARKER = "<!-- AREA_CONDITION_LINKS_END -->"


def build_section() -> str:
    parts = [START_MARKER]
    parts.append('    <section>')
    parts.append('        <div class="container">')
    parts.append('            <h2>働き方 × エリア（全124ページ）</h2>')
    parts.append('            <p style="color:#666;margin-bottom:24px;font-size:0.95rem;">希望の働き方と勤務地から、看護師求人を直接検索できます。各ページにD1リアルタイム求人統計・代表施設・アクセス駅を掲載。</p>')

    for cond_label, cond_slug, cond_desc in CONDITIONS:
        parts.append('            <h3 style="font-size:1.1rem;color:#2a2a3e;margin:24px 0 8px;padding-left:10px;border-left:3px solid #5a8fa8;">' + cond_label + '</h3>')
        parts.append(f'            <p style="color:#888;font-size:0.85rem;margin-bottom:10px;">{cond_desc}</p>')
        parts.append('            <div style="display:flex;flex-wrap:wrap;gap:6px 10px;margin-bottom:20px;">')
        for slug, ja in AREAS:
            url = f'/lp/job-seeker/area/{slug}-{cond_slug}.html'
            parts.append(
                f'                <a href="{url}" style="display:inline-block;padding:6px 12px;background:#f4f1ea;border-radius:16px;color:#3a3a4e;text-decoration:none;font-size:0.88rem;">{ja}</a>'
            )
        parts.append('            </div>')

    # 診療科×主要市セクション（2026-04-21 追加）
    import pathlib as _pathlib
    AREA_DIR_FOR_CHECK = ROOT / "lp/job-seeker/area"
    parts.append('            <h2 style="margin-top:32px;">診療科 × 主要市</h2>')
    parts.append('            <p style="color:#666;margin-bottom:24px;font-size:0.95rem;">専門科別に主要5市の看護師求人をまとめました。各ページに該当施設・求人統計付き。</p>')
    for spec_label, spec_slug in SPECIALTIES_WITH_AREAS:
        parts.append('            <h3 style="font-size:1.1rem;color:#2a2a3e;margin:24px 0 8px;padding-left:10px;border-left:3px solid #e07b39;">' + spec_label + '</h3>')
        parts.append('            <div style="display:flex;flex-wrap:wrap;gap:6px 10px;margin-bottom:20px;">')
        for city_slug, city_ja in SPECIALTY_CITIES:
            file_slug = f'{city_slug}-{spec_slug}'
            if not (AREA_DIR_FOR_CHECK / f'{file_slug}.html').exists():
                continue  # 薄判定で生成されなかったページはリンクしない
            url = f'/lp/job-seeker/area/{file_slug}.html'
            parts.append(
                f'                <a href="{url}" style="display:inline-block;padding:6px 12px;background:#fff4e6;border-radius:16px;color:#3a3a4e;text-decoration:none;font-size:0.88rem;">{city_ja}</a>'
            )
        parts.append('            </div>')

    parts.append('        </div>')
    parts.append('    </section>')
    parts.append(END_MARKER)
    return "\n".join(parts)


def main():
    html = TARGET.read_text(encoding="utf-8")
    new_section = build_section()

    if START_MARKER in html and END_MARKER in html:
        # 既存ブロック置換
        pattern = re.compile(re.escape(START_MARKER) + ".*?" + re.escape(END_MARKER), re.DOTALL)
        html = pattern.sub(new_section, html)
        action = "updated"
    else:
        # 挿入: <div class="cta-section"> の直前
        insert_marker = '<div class="cta-section">'
        if insert_marker not in html:
            print("⚠️  挿入位置が見つかりませんでした（cta-section直前の想定）", flush=True)
            return
        html = html.replace(insert_marker, new_section + "\n\n    " + insert_marker, 1)
        action = "inserted"

    TARGET.write_text(html, encoding="utf-8")
    print(f"✅ area/index.html {action}: 4 conditions × 31 areas = 124 links")


if __name__ == "__main__":
    main()
