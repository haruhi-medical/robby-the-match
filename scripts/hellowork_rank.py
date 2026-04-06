#!/usr/bin/env python3
"""
ハローワーク求人ランク分けスクリプト

求人を S/A/B/C/D ランクに自動分類し、ランク付きJSONを出力する。
hellowork_to_jobs.py から呼び出され、worker.js にランク情報を付与する。

ランク基準（100点満点 → ランク変換）:
  S (80+): 看護師が見て「即応募したい」レベル
  A (65+): 「これは良い」と保存するレベル
  B (50+): 「まあ悪くない」標準的な求人
  C (35+): 条件は物足りないが選択肢にはなる
  D (<35): 魅力に乏しい

使い方:
  python3 scripts/hellowork_rank.py              # ランク付きJSON出力
  python3 scripts/hellowork_rank.py --summary     # ランク分布サマリー
  python3 scripts/hellowork_rank.py --top 20      # 上位N件表示
"""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "hellowork_nurse_jobs.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "hellowork_ranked.json"

# 看護師フィルタ
NURSE_KEYWORDS = ["看護師", "看護職", "ナース", "訪問看護"]
NOISE_KEYWORDS = ["看護助手", "助手", "補助", "事務", "ケアマネ", "理学療法",
                   "作業療法", "動物", "歯科", "介護福祉士", "薬剤"]

# ---------- スコアリング ----------

def parse_salary(job):
    """月給（円）を返す。時給の場合はNone"""
    low = job.get("salary_low", "")
    high = job.get("salary_high", "")
    form = job.get("salary_form", "")

    try:
        low_num = int(low.replace(",", "")) if low else 0
        high_num = int(high.replace(",", "")) if high else 0
    except ValueError:
        return None, None, False

    is_hourly = "時給" in form or "時間給" in form or (
        "その他" in form and low_num > 0 and low_num < 10000
    ) or (low_num > 0 and low_num < 10000)

    return low_num, high_num, is_hourly


def parse_bonus_months(job):
    """賞与月数を返す"""
    detail = job.get("bonus_detail", "")
    m = re.search(r"(\d+\.?\d*)ヶ月", detail)
    if m:
        return float(m.group(1))
    return 0.0


def parse_holidays(job):
    """年間休日数を返す"""
    h = job.get("annual_holidays", "").replace("日", "")
    try:
        return int(h)
    except ValueError:
        return 0


def score_job(job):
    """
    求人を100点満点でスコアリング

    配点:
      年収推定       30点（看護師が最も重視）
      年間休日       20点（ワークライフバランス）
      賞与           15点（安定性の指標）
      雇用安定性     15点（正社員 > パート）
      福利厚生       10点（託児・退職金・住宅）
      勤務地利便性   10点（駅近・人気エリア）
    """
    score = 0
    breakdown = {}  # スコア内訳
    details = {}

    # --- 年収推定 (30点) ---
    sal_score = 0
    low, high, is_hourly = parse_salary(job)
    if is_hourly:
        hourly = high if high else low
        if hourly:
            annual_est = hourly * 8 * 22 * 12
            if annual_est >= 3500000:
                sal_score = 25
            elif annual_est >= 3000000:
                sal_score = 20
            elif annual_est >= 2500000:
                sal_score = 15
            else:
                sal_score = 8
            details["salary"] = f"時給{hourly:,}円"
        else:
            details["salary"] = "不明"
    else:
        monthly = high if high else low
        if monthly:
            if monthly >= 350000:
                sal_score = 30
            elif monthly >= 300000:
                sal_score = 25
            elif monthly >= 270000:
                sal_score = 20
            elif monthly >= 230000:
                sal_score = 15
            elif monthly >= 200000:
                sal_score = 10
            else:
                sal_score = 5
            details["salary"] = f"月給{monthly/10000:.1f}万円"
        else:
            details["salary"] = "不明"
    score += sal_score
    breakdown["sal"] = sal_score

    # --- 年間休日 (20点) ---
    hol_score = 0
    holidays = parse_holidays(job)
    if holidays >= 125:
        hol_score = 20
    elif holidays >= 120:
        hol_score = 17
    elif holidays >= 115:
        hol_score = 14
    elif holidays >= 110:
        hol_score = 10
    elif holidays >= 105:
        hol_score = 7
    elif holidays > 0:
        hol_score = 3
    score += hol_score
    breakdown["hol"] = hol_score
    details["holidays"] = f"{holidays}日" if holidays else "不明"

    # --- 賞与 (15点) ---
    bon_score = 0
    bonus = parse_bonus_months(job)
    bonus_exists = job.get("bonus", "")
    if bonus >= 4.0:
        bon_score = 15
    elif bonus >= 3.0:
        bon_score = 12
    elif bonus >= 2.0:
        bon_score = 9
    elif bonus >= 1.0:
        bon_score = 6
    elif "あり" in bonus_exists:
        bon_score = 4
    score += bon_score
    breakdown["bon"] = bon_score
    details["bonus"] = f"{bonus}ヶ月" if bonus else ("あり" if "あり" in bonus_exists else "なし")

    # --- 雇用安定性 (15点) ---
    emp_score = 0
    emp_type = job.get("employment_type", "")
    full_part = job.get("full_part", "")
    permanent = job.get("permanent_hire", "")

    if emp_type == "正社員":
        emp_score = 15
    elif "正社員以外" in emp_type and "あり" in permanent:
        emp_score = 10
    elif "パート" in full_part:
        emp_score = 5
    else:
        emp_score = 7
    score += emp_score
    breakdown["emp"] = emp_score
    details["emp_type"] = emp_type or full_part

    # --- 福利厚生 (10点) ---
    welfare_score = 0
    welfare_items = []

    childcare = job.get("childcare", "")
    if childcare and "あり" in childcare:
        welfare_score += 4
        welfare_items.append("託児所")

    retirement = job.get("retirement", "")
    if retirement and "あり" in retirement:
        welfare_score += 3
        welfare_items.append("退職金")

    car = job.get("car_commute", "")
    if car and "可" in car:
        welfare_score += 1
        welfare_items.append("車通勤可")

    # 仕事内容から追加福利厚生を検出
    desc = job.get("job_description", "")
    if "住宅" in desc or "寮" in desc:
        welfare_score += 2
        welfare_items.append("住宅手当/寮")

    wel_score = min(welfare_score, 10)
    score += wel_score
    breakdown["wel"] = wel_score
    details["welfare"] = "、".join(welfare_items) if welfare_items else "特記なし"

    # --- 勤務地利便性 (10点) ---
    station = job.get("work_station_text", "") or job.get("work_station", "")
    location = job.get("work_location", "")

    loc_score = 0
    # 人気エリア
    popular = ["横浜", "川崎", "藤沢", "鎌倉"]
    if any(p in location for p in popular):
        loc_score += 3

    # 駅近（徒歩表記あり）
    if "徒歩" in station:
        m = re.search(r"徒歩(\d+)", station)
        if m and int(m.group(1)) <= 5:
            loc_score += 5
        elif m and int(m.group(1)) <= 10:
            loc_score += 3
        else:
            loc_score += 2
    elif station:
        loc_score += 2

    loc_score = min(loc_score, 10)
    score += loc_score
    breakdown["loc"] = loc_score
    details["location"] = location

    return score, details, breakdown


def score_to_rank(score):
    """スコアをランクに変換"""
    if score >= 80:
        return "S"
    elif score >= 65:
        return "A"
    elif score >= 50:
        return "B"
    elif score >= 35:
        return "C"
    else:
        return "D"


RANK_LABELS = {
    "S": "最優良求人（即応募レベル）",
    "A": "優良求人（好条件）",
    "B": "標準的な求人",
    "C": "条件やや物足りない",
    "D": "魅力に乏しい",
}


def is_target_nurse_job(job):
    """看護師本体の求人かフィルタ"""
    title = job.get("job_title", "")
    desc = job.get("job_description", "")
    text = title + " " + desc

    has_nurse = any(kw in title for kw in NURSE_KEYWORDS)
    has_noise = any(kw in title for kw in NOISE_KEYWORDS)

    return has_nurse and not has_noise


# ---------- エリア分類 ----------

AREA_MAP = {
    # 神奈川
    "横浜": ["横浜市"],
    "川崎": ["川崎市"],
    "相模原": ["相模原市"],
    "横須賀": ["横須賀市", "逗子市", "三浦市", "葉山町"],
    "鎌倉": ["鎌倉市"],
    "藤沢": ["藤沢市"],
    "茅ヶ崎": ["茅ヶ崎市", "寒川町"],
    "平塚": ["平塚市"],
    "大磯": ["大磯町", "二宮町"],
    "秦野": ["秦野市"],
    "伊勢原": ["伊勢原市"],
    "厚木": ["厚木市", "愛川町", "清川村"],
    "大和": ["大和市", "綾瀬市"],
    "海老名": ["海老名市", "座間市"],
    "小田原": ["小田原市"],
    "南足柄・開成": ["南足柄市", "開成町", "松田町", "山北町", "大井町", "中井町", "箱根町", "真鶴町", "湯河原町"],
    # 東京
    "23区": ["千代田区", "中央区", "港区", "新宿区", "文京区", "台東区", "墨田区", "江東区", "品川区", "目黒区", "大田区", "世田谷区", "渋谷区", "中野区", "杉並区", "豊島区", "北区", "荒川区", "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区"],
    "多摩": ["八王子市", "立川市", "武蔵野市", "三鷹市", "青梅市", "府中市", "昭島市", "調布市", "町田市", "小金井市", "小平市", "日野市", "東村山市", "国分寺市", "国立市", "福生市", "狛江市", "東大和市", "清瀬市", "東久留米市", "武蔵村山市", "多摩市", "稲城市", "羽村市", "あきる野市", "西東京市"],
    # 埼玉
    "さいたま": ["さいたま市"],
    "川口・戸田": ["川口市", "戸田市", "蕨市", "鳩ヶ谷"],
    "所沢・入間": ["所沢市", "入間市", "狭山市", "飯能市", "日高市"],
    "川越・東松山": ["川越市", "東松山市", "坂戸市", "鶴ヶ島市", "ふじみ野市", "富士見市"],
    "越谷・草加": ["越谷市", "草加市", "春日部市", "三郷市", "八潮市", "吉川市"],
    "埼玉その他": ["熊谷市", "上尾市", "深谷市", "久喜市", "加須市", "本庄市", "行田市", "秩父市", "北本市", "鴻巣市", "桶川市", "朝霞市", "志木市", "和光市", "新座市"],
    # 千葉
    "千葉": ["千葉市"],
    "船橋・市川": ["船橋市", "市川市", "浦安市", "習志野市", "八千代市", "鎌ケ谷市"],
    "柏・松戸": ["柏市", "松戸市", "流山市", "我孫子市", "野田市"],
    "千葉その他": ["市原市", "木更津市", "成田市", "佐倉市", "四街道市", "印西市", "白井市", "銚子市", "茂原市", "東金市", "旭市", "匝瑳市"],
}


def classify_area(job):
    loc = (job.get("work_location") or "") + (job.get("work_address") or "") + (job.get("employer_address") or "")
    if not loc.strip():
        return None
    # 都道府県チェック: 関東4都県以外はスキップ
    valid_prefs = ["東京都", "神奈川県", "千葉県", "埼玉県"]
    if not any(p in loc for p in valid_prefs):
        return None
    # 長い市区町村名から先にマッチ（「東大和市」を「大和市」より先に検出）
    all_entries = []
    for area_name, cities in AREA_MAP.items():
        for city in cities:
            all_entries.append((city, area_name))
    all_entries.sort(key=lambda x: -len(x[0]))  # 長い名前を優先
    for city, area_name in all_entries:
        if city in loc:
            return area_name
    return None


# ---------- メイン ----------

def main():
    parser = argparse.ArgumentParser(description="ハローワーク求人ランク分け")
    parser.add_argument("--summary", action="store_true", help="ランク分布サマリー")
    parser.add_argument("--top", type=int, default=0, help="上位N件表示")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        print("❌ hellowork_nurse_jobs.json が見つかりません")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    ranked = []

    for job in jobs:
        if not is_target_nurse_job(job):
            continue

        score, details, breakdown = score_job(job)
        rank = score_to_rank(score)
        area = classify_area(job)

        ranked.append({
            "kjno": job.get("kjno", ""),
            "rank": rank,
            "score": score,
            "breakdown": breakdown,  # {sal:30, hol:20, bon:15, emp:15, wel:10, loc:10}
            "employer": job.get("employer", ""),
            "job_title": job.get("job_title", ""),
            "area": area,
            "employment_type": job.get("employment_type", ""),
            "details": details,
            # 元データの主要フィールド
            "work_location": job.get("work_location", ""),
            "work_station_text": job.get("work_station_text", "") or job.get("work_station", ""),
            "salary_low": job.get("salary_low", ""),
            "salary_high": job.get("salary_high", ""),
            "salary_form": job.get("salary_form", ""),
            "annual_holidays": job.get("annual_holidays", ""),
            "bonus_detail": job.get("bonus_detail", ""),
            "childcare": job.get("childcare", ""),
            "retirement": job.get("retirement", ""),
            "shift1": job.get("shift1", ""),
            "shift2": job.get("shift2", ""),
            "job_description": job.get("job_description", "")[:150],
        })

    ranked.sort(key=lambda x: -x["score"])

    # サマリー表示
    if args.summary or args.top == 0:
        rank_counts = {}
        for r in ranked:
            rk = r["rank"]
            rank_counts[rk] = rank_counts.get(rk, 0) + 1

        print(f"\n📊 ハローワーク看護師求人ランク分布（全{len(ranked)}件）")
        print("=" * 50)
        for rk in ["S", "A", "B", "C", "D"]:
            count = rank_counts.get(rk, 0)
            pct = count / len(ranked) * 100 if ranked else 0
            bar = "█" * int(pct / 2)
            print(f"  {rk}ランク ({RANK_LABELS[rk]}): {count:3d}件 ({pct:4.1f}%) {bar}")

        # エリア×ランク
        print(f"\n📍 エリア別ランク分布")
        print("-" * 60)
        area_ranks = {}
        for r in ranked:
            a = r["area"] or "分類不能"
            if a not in area_ranks:
                area_ranks[a] = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
            area_ranks[a][r["rank"]] += 1

        area_order = ["横浜", "川崎", "相模原", "横須賀", "鎌倉", "藤沢",
                      "茅ヶ崎", "平塚", "秦野", "厚木", "大和", "海老名",
                      "小田原", "南足柄・開成", "伊勢原", "大磯", "分類不能"]
        print(f"  {'エリア':　<8} {'S':>3} {'A':>3} {'B':>3} {'C':>3} {'D':>3} {'計':>4}")
        for a in area_order:
            if a not in area_ranks:
                continue
            ar = area_ranks[a]
            total = sum(ar.values())
            print(f"  {a:<8} {ar['S']:3d} {ar['A']:3d} {ar['B']:3d} {ar['C']:3d} {ar['D']:3d} {total:4d}")

    # TOP N
    if args.top > 0:
        print(f"\n🏆 TOP {args.top} 求人")
        print("=" * 70)
        for i, r in enumerate(ranked[:args.top]):
            d = r["details"]
            print(f"\n{i+1}. [{r['rank']}ランク {r['score']}点] {r['employer']}")
            print(f"   職種: {r['job_title']}")
            print(f"   エリア: {r['area']} | {r['work_station_text']}")
            print(f"   給与: {d['salary']} | 賞与: {d['bonus']} | 休日: {d['holidays']}")
            print(f"   雇用: {d['emp_type']} | 福利: {d['welfare']}")

    # JSON保存
    output = {
        "ranked_at": data.get("fetched_at", ""),
        "total_scored": len(ranked),
        "rank_counts": {rk: sum(1 for r in ranked if r["rank"] == rk) for rk in "SABCD"},
        "jobs": ranked,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {OUTPUT_FILE} に保存完了（{len(ranked)}件）")


if __name__ == "__main__":
    main()
