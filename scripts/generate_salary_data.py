#!/usr/bin/env python3
"""
神奈川ナース転職 — 年収診断用統計データ生成スクリプト
hellowork_nurse_jobs.json → salary-check/salary-data.json

エリア x 働き方 x 施設タイプ のクロス集計を行う。
"""

import json
import re
import statistics
import math
from pathlib import Path
from datetime import datetime

# ===== 定数 =====

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "hellowork_nurse_jobs.json"
OUTPUT_FILE = BASE_DIR / "salary-check" / "salary-data.json"

# エリア分類: エリアキー → 市区町村キーワードリスト
AREA_MAP = {
    "yokohama_kawasaki": ["横浜市", "川崎市"],
    "shonan": ["藤沢市", "茅ヶ崎市", "平塚市", "鎌倉市", "大磯町", "二宮町"],
    "sagamihara_kenoh": [
        "相模原市", "厚木市", "大和市", "海老名市", "座間市",
        "秦野市", "伊勢原市", "綾瀬市"
    ],
    "yokosuka_miura": ["横須賀市", "三浦市", "逗子市", "葉山町"],
    "kensai": [
        "小田原市", "南足柄市", "箱根町", "湯河原町", "真鶴町",
        "松田町", "開成町", "山北町", "中井町", "大井町"
    ],
}

# エリア表示名
AREA_NAMES = {
    "yokohama_kawasaki": "横浜市・川崎市",
    "shonan": "湘南エリア",
    "sagamihara_kenoh": "相模原・県央エリア",
    "yokosuka_miura": "横須賀・三浦エリア",
    "kensai": "県西エリア",
}

# 施設タイプ分類
FACILITY_NAMES = {
    "hospital": "病院",
    "clinic": "クリニック・診療所",
    "visiting_nurse": "訪問看護",
    "care_facility": "介護・福祉施設",
    "all": "全施設",
}

# 夜勤判定キーワード
NIGHT_KEYWORDS = [
    "夜勤", "交替制", "交代制", "二交替", "二交代",
    "三交替", "三交代", "当直", "夜勤手当",
]
DAY_KEYWORDS = ["日勤のみ", "日勤常勤", "日勤帯のみ", "日勤帯"]


def load_jobs():
    """JSONから求人データを読み込む"""
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["jobs"], data.get("fetched_at", "")


def extract_location_text(job):
    """work_location または work_address から所在地テキストを取得"""
    loc = job.get("work_location", "")
    if loc:
        return loc
    # work_locationが空の場合、work_addressから抽出
    addr = job.get("work_address", "")
    if addr and "神奈川県" in addr:
        return addr
    return ""


def classify_area(job):
    """求人のエリアを判定。該当なしはNone"""
    loc = extract_location_text(job)
    if not loc or "神奈川県" not in loc:
        return None
    for area_key, cities in AREA_MAP.items():
        for city in cities:
            if city in loc:
                return area_key
    return None


def classify_workstyle(job):
    """
    働き方を判定:
    - part_time: パート（時給表記）
    - with_night: 常勤で夜勤あり
    - day_only: 常勤で日勤のみ
    - None: 判定不能
    """
    full_part = job.get("full_part", "")
    salary_form = job.get("salary_form", "")

    # パートタイム判定（時給のみ。月給の「正社員以外」はパートに含めない）
    if salary_form == "時給":
        return "part_time"
    if full_part == "パート" or salary_form == "日給":
        if salary_form == "日給":
            # 日給パートも時給換算が難しいのでpart_timeとして扱うが、
            # 統計は時給で出すので日給は除外
            return None
        else:
            return None

    # フルタイム判定
    if full_part == "フルタイム":
        # 月給 or 年俸制のみ対象
        if salary_form not in ("月給", "年俸制"):
            return None

        # テキスト全体を結合して判定
        text = " ".join([
            job.get("job_title", ""),
            job.get("job_description", ""),
            job.get("work_hours", ""),
            job.get("shift1", ""),
            job.get("shift2", ""),
            job.get("shift3", ""),
            job.get("salary_text", ""),
        ])

        has_day = any(k in text for k in DAY_KEYWORDS)
        has_night = any(k in text for k in NIGHT_KEYWORDS)

        # シフトに深夜帯（22時以降 or 5時以前）があるか
        time_matches = re.findall(r'(\d{1,2})時(\d{2})分', text)
        has_late_hour = any(
            int(h) >= 22 or int(h) <= 5
            for h, _ in time_matches
        )

        if has_day and not has_night and not has_late_hour:
            return "day_only"
        elif has_night or has_late_hour:
            return "with_night"
        else:
            # 判定不能 → 日勤のみにもしない（不明は除外）
            return None

    return None


def classify_facility(job):
    """
    施設タイプを判定:
    - hospital: 病院
    - clinic: 一般診療所 or job_title/employerに「クリニック」「診療所」を含む
    - visiting_nurse: 助産・看護業 or job_title/employerに「訪問看護」を含む
    - care_facility: 老人福祉・介護事業 / 障害者福祉事業 / 児童福祉事業
    - other: 上記以外
    """
    industry = job.get("industry", "")
    job_title = job.get("job_title", "")
    employer = job.get("employer", "")
    text = job_title + " " + employer

    # hospital
    if industry == "病院":
        return "hospital"

    # clinic
    if industry == "一般診療所":
        return "clinic"
    if "クリニック" in text or "診療所" in text:
        return "clinic"

    # visiting_nurse
    if industry == "助産・看護業":
        return "visiting_nurse"
    if "訪問看護" in text:
        return "visiting_nurse"

    # care_facility
    if industry in ("老人福祉・介護事業", "障害者福祉事業", "児童福祉事業"):
        return "care_facility"

    return "other"


def get_salary_value(job, workstyle):
    """
    給与の下限値を数値で返す。
    part_time: 時給（円）
    with_night / day_only: 月給（円）
    年俸制は月額換算。
    """
    try:
        low = int(job.get("salary_low", "0"))
        high = int(job.get("salary_high", "0"))
    except (ValueError, TypeError):
        return None, None

    if low <= 0:
        return None, None

    salary_form = job.get("salary_form", "")

    if workstyle == "part_time":
        # 時給
        if salary_form != "時給":
            return None, None
        # 時給なのに10,000円超は月給混入 → 除外
        if low > 10000:
            return None, None
        return low, high if high > 0 else low

    # フルタイム: 月給 or 年俸制
    if salary_form == "年俸制":
        # 年俸の月額表記（salary_textが月額の場合もある）
        # salary_lowが月額っぽい（10万〜80万）ならそのまま使う
        if 100000 <= low <= 800000:
            return low, high if high > 0 else low
        # 年額っぽい場合は12で割る
        if low > 800000:
            low = low // 12
            high = high // 12 if high > 0 else low
            return low, high
        return None, None

    if salary_form == "月給":
        # 妥当性チェック（月給10万〜80万の範囲）
        if 100000 <= low <= 800000:
            return low, high if high > 0 else low
        return None, None

    return None, None


def compute_stats(salaries, is_part_time=False):
    """統計値を計算"""
    if not salaries:
        return None

    n = len(salaries)
    unit = "時給" if is_part_time else "月給"

    result = {
        "count": n,
        "unit": unit,
        "min": min(salaries),
        "max": max(salaries),
        "median": int(statistics.median(salaries)),
        "avg": int(statistics.mean(salaries)),
    }

    if n >= 5:
        # パーセンタイル計算（10%, 20%, ..., 90%）
        sorted_s = sorted(salaries)
        percentiles = {}
        for p in range(10, 100, 10):
            idx = (p / 100) * (n - 1)
            lower = int(math.floor(idx))
            upper = int(math.ceil(idx))
            if lower == upper:
                val = sorted_s[lower]
            else:
                val = sorted_s[lower] + (sorted_s[upper] - sorted_s[lower]) * (idx - lower)

            if is_part_time:
                # 時給は円単位
                percentiles[f"p{p}"] = int(round(val))
            else:
                # 月給は千円単位
                percentiles[f"p{p}"] = round(val / 1000, 1)

        result["percentiles"] = percentiles
    else:
        result["insufficient_data"] = True

    return result


def get_sample_jobs(jobs_with_salary, n=3):
    """上位3件の具体求人を取得（給与上限が高い順）"""
    sorted_jobs = sorted(
        jobs_with_salary,
        key=lambda x: x[1][1],  # salary_high
        reverse=True
    )
    samples = []
    seen_employers = set()
    for job, (sal_low, sal_high) in sorted_jobs:
        employer = job.get("employer", "").strip()
        if employer in seen_employers:
            continue  # 同一雇用主の重複を排除
        seen_employers.add(employer)
        samples.append({
            "employer": employer,
            "salary_range": f"{sal_low:,}円～{sal_high:,}円",
            "employment_type": job.get("employment_type", ""),
            "work_hours": job.get("work_hours", ""),
        })
        if len(samples) >= n:
            break
    return samples


def main():
    jobs, fetched_at = load_jobs()
    print(f"[INFO] 読み込み求人数: {len(jobs)}")
    print(f"[INFO] データ取得日: {fetched_at}")

    # 分類集計: (area, workstyle, facility) → [(job, (sal_low, sal_high)), ...]
    classified = {}
    area_counts = {}
    workstyle_counts = {}
    facility_counts = {}
    skipped_area = 0
    skipped_workstyle = 0
    skipped_salary = 0

    for job in jobs:
        area = classify_area(job)
        if area is None:
            skipped_area += 1
            continue

        workstyle = classify_workstyle(job)
        if workstyle is None:
            skipped_workstyle += 1
            continue

        sal_low, sal_high = get_salary_value(job, workstyle)
        if sal_low is None:
            skipped_salary += 1
            continue

        facility = classify_facility(job)

        key = (area, workstyle, facility)
        if key not in classified:
            classified[key] = []
        classified[key].append((job, (sal_low, sal_high)))

        area_counts[area] = area_counts.get(area, 0) + 1
        workstyle_counts[workstyle] = workstyle_counts.get(workstyle, 0) + 1
        facility_counts[facility] = facility_counts.get(facility, 0) + 1

    # 施設タイプ一覧（other含む全タイプ）
    facility_types = ["hospital", "clinic", "visiting_nurse", "care_facility", "other"]

    # 統計データ生成
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "ハローワーク求人API（神奈川県看護師）",
        "source_fetched_at": fetched_at,
        "total_analyzed": sum(len(v) for v in classified.values()),
        "facility_names": FACILITY_NAMES,
        "areas": {},
    }

    total_cells = 0
    insufficient_cells = 0

    for area_key in AREA_MAP:
        area_data = {
            "name": AREA_NAMES[area_key],
            "total_count": area_counts.get(area_key, 0),
            "workstyles": {},
        }

        for ws in ["with_night", "day_only", "part_time"]:
            is_pt = (ws == "part_time")
            ws_data = {"facility_types": {}}

            # 各施設タイプ別の統計
            for ft in facility_types:
                key = (area_key, ws, ft)
                job_list = classified.get(key, [])
                salaries = [s[0] for _, s in job_list]
                stats = compute_stats(salaries, is_part_time=is_pt)

                if stats is None:
                    ws_data["facility_types"][ft] = {"count": 0, "insufficient_data": True}
                    insufficient_cells += 1
                else:
                    stats["sample_jobs"] = get_sample_jobs(job_list)
                    ws_data["facility_types"][ft] = stats
                    if stats.get("insufficient_data"):
                        insufficient_cells += 1

                total_cells += 1

            # "all"（全施設合計）
            all_jobs = []
            for ft in facility_types:
                key = (area_key, ws, ft)
                all_jobs.extend(classified.get(key, []))

            all_salaries = [s[0] for _, s in all_jobs]
            all_stats = compute_stats(all_salaries, is_part_time=is_pt)

            if all_stats is None:
                ws_data["facility_types"]["all"] = {"count": 0, "insufficient_data": True}
                insufficient_cells += 1
            else:
                all_stats["sample_jobs"] = get_sample_jobs(all_jobs)
                ws_data["facility_types"]["all"] = all_stats
                if all_stats.get("insufficient_data"):
                    insufficient_cells += 1

            total_cells += 1

            area_data["workstyles"][ws] = ws_data

        output["areas"][area_key] = area_data

    # 出力
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # サマリ表示
    print(f"\n{'='*60}")
    print(f" 年収診断統計データ生成完了")
    print(f"{'='*60}")
    print(f" 入力: {INPUT_FILE}")
    print(f" 出力: {OUTPUT_FILE}")
    print(f"")
    print(f" 総求人数: {len(jobs)}")
    print(f" 分析対象: {output['total_analyzed']}件")
    print(f" スキップ:")
    print(f"   エリア外/不明: {skipped_area}件")
    print(f"   働き方不明: {skipped_workstyle}件")
    print(f"   給与データ不正: {skipped_salary}件")
    print(f"")
    print(f" エリア別集計:")
    for area_key in AREA_MAP:
        count = area_counts.get(area_key, 0)
        print(f"   {AREA_NAMES[area_key]}: {count}件")
    print(f"")
    print(f" 働き方別集計:")
    ws_names = {"with_night": "夜勤あり常勤", "day_only": "日勤のみ常勤", "part_time": "パートタイム"}
    for ws_key, ws_name in ws_names.items():
        count = workstyle_counts.get(ws_key, 0)
        print(f"   {ws_name}: {count}件")
    print(f"")
    print(f" 施設タイプ別集計:")
    for ft_key in facility_types:
        ft_name = FACILITY_NAMES.get(ft_key, ft_key)
        count = facility_counts.get(ft_key, 0)
        print(f"   {ft_name}: {count}件")
    print(f"")
    print(f" クロス集計セル: {total_cells}セル（うちN<5: {insufficient_cells}セル）")
    print(f"")

    # 各セルのサマリ
    print(f" 【セル詳細】")
    for area_key in AREA_MAP:
        area_data = output["areas"][area_key]
        print(f"  ■ {AREA_NAMES[area_key]}")
        for ws_key, ws_name in ws_names.items():
            ws_data = area_data["workstyles"].get(ws_key, {})
            for ft_key in facility_types + ["all"]:
                ft_name = FACILITY_NAMES.get(ft_key, ft_key)
                ft_data = ws_data.get("facility_types", {}).get(ft_key, {})
                n = ft_data.get("count", 0)
                if n == 0:
                    print(f"    {ws_name} / {ft_name}: 0件")
                elif ft_data.get("insufficient_data"):
                    print(f"    {ws_name} / {ft_name}: {n}件 (N<5)")
                else:
                    unit = ft_data.get("unit", "月給")
                    med = ft_data.get("median", 0)
                    if unit == "時給":
                        print(f"    {ws_name} / {ft_name}: {n}件 | 中央値 {med:,}円/時")
                    else:
                        print(f"    {ws_name} / {ft_name}: {n}件 | 中央値 {med:,}円/月")
    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
