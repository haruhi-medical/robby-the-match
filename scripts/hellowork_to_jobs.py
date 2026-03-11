#!/usr/bin/env python3
"""
ハローワーク求人JSON → worker.js EXTERNAL_JOBS 変換スクリプト

hellowork_fetch.py の後に実行。
data/hellowork_nurse_jobs.json → api/worker.js の EXTERNAL_JOBS を更新する。

使い方:
  python3 scripts/hellowork_to_jobs.py           # worker.js を更新
  python3 scripts/hellowork_to_jobs.py --dry-run  # 変更なし、プレビューのみ
  python3 scripts/hellowork_to_jobs.py --json     # JSON出力のみ（worker.js更新なし）
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "hellowork_nurse_jobs.json"
WORKER_JS = PROJECT_ROOT / "api" / "worker.js"

# エリア分類（config.jsの9エリアに対応 + 主要都市）
AREA_MAP = {
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
}


def classify_area(job):
    """求人の勤務地からエリアを判定"""
    loc = job.get("work_location", "") + job.get("work_address", "")
    for area_name, cities in AREA_MAP.items():
        for city in cities:
            # 「横浜市」で始まる or 含むかチェック
            city_base = city.rstrip("市区町村")
            if city in loc or city_base in loc:
                return area_name
    return None


def format_salary(job):
    """給与を読みやすい形式にフォーマット"""
    low = job.get("salary_low", "")
    high = job.get("salary_high", "")
    form = job.get("salary_form", "")

    if not low and not high:
        return ""

    try:
        low_num = int(low.replace(",", "")) if low else 0
        high_num = int(high.replace(",", "")) if high else 0
    except ValueError:
        return ""

    # 時給判定: salary_form or 値が小さい（<10000）
    is_hourly = "時給" in form or "時間給" in form or (
        "その他" in form and low_num > 0 and low_num < 10000
    )

    if is_hourly:
        if low_num and high_num and low_num != high_num:
            return f"時給{low_num:,}〜{high_num:,}円"
        elif high_num:
            return f"時給{high_num:,}円"
        elif low_num:
            return f"時給{low_num:,}円〜"
        return ""

    # 月給（万円単位に変換）
    if low_num and high_num:
        low_man = low_num / 10000
        high_man = high_num / 10000
        if abs(low_man - high_man) < 0.5:
            return f"月給{low_man:.1f}万円"
        return f"月給{low_man:.0f}〜{high_man:.0f}万円"
    elif high_num:
        return f"月給{high_num/10000:.0f}万円"
    elif low_num:
        return f"月給{low_num/10000:.0f}万円〜"
    return ""


def salary_sort_key(job):
    """ソート用: 正社員優先、給与高い順"""
    emp = job.get("employment_type", "")
    type_score = 0 if "正社員" == emp else 1 if "正社員以外" in emp else 2
    low = job.get("salary_low", "0")
    try:
        val = int(low.replace(",", "")) if low else 0
    except ValueError:
        val = 0
    return (type_score, -val)


def format_job_string(job):
    """1件の求人を EXTERNAL_JOBS のテキスト形式に変換"""
    parts = []

    # 事業所名: 給与/条件/勤務地/特徴
    employer = job.get("employer", "").strip()
    if not employer:
        return None

    # 給与
    salary = format_salary(job)

    # 雇用形態
    emp_type = job.get("employment_type", "")
    full_part = job.get("full_part", "")

    # 勤務時間
    shifts = []
    for key in ["shift1", "shift2", "shift3"]:
        s = job.get(key, "")
        if s:
            shifts.append(s)
    shift_text = ""
    if len(shifts) == 1 and "08:" in shifts[0] and "17:" in shifts[0]:
        shift_text = "日勤"
    elif len(shifts) >= 2:
        shift_text = "シフト制"

    # 最寄り駅
    station = job.get("work_station_text", "") or job.get("work_station", "")
    # 長すぎる場合は切り詰め
    if len(station) > 20:
        station = station[:20]

    # 休日（"107日" → "年休107日"、重複"日"防止）
    holidays = job.get("annual_holidays", "").replace("日", "")
    holiday_text = f"年休{holidays}日" if holidays else ""

    # 託児所
    childcare = job.get("childcare", "")
    childcare_text = "託児所あり" if childcare and "あり" in childcare else ""

    # 正社員登用
    permanent = job.get("permanent_hire", "")
    perm_text = "正社員登用あり" if permanent and "あり" in permanent else ""

    # 組み立て
    info_parts = []
    if salary:
        info_parts.append(salary)
    if emp_type and "正社員" not in emp_type:
        info_parts.append(emp_type)
    if shift_text:
        info_parts.append(shift_text)
    if station:
        info_parts.append(station)
    if holiday_text:
        info_parts.append(holiday_text)
    if childcare_text:
        info_parts.append(childcare_text)
    if perm_text and "パート" in emp_type:
        info_parts.append(perm_text)

    if not info_parts:
        return None

    result = f"{employer}: {'/'.join(info_parts)}"
    # 長すぎる場合は100文字で切り詰め
    if len(result) > 120:
        result = result[:117] + "..."
    return result


def main():
    parser = argparse.ArgumentParser(description="ハローワーク→EXTERNAL_JOBS変換")
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ")
    parser.add_argument("--json", action="store_true", help="JSON出力のみ")
    parser.add_argument("--max-per-area", type=int, default=8, help="エリアあたり最大件数")
    args = parser.parse_args()

    if not INPUT_FILE.exists():
        print("❌ hellowork_nurse_jobs.json が見つかりません。先に hellowork_fetch.py を実行してください。")
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print(f"📦 入力: {len(jobs)}件の看護師求人")

    # エリア別に分類（生データで保持）
    area_jobs_raw = {}
    area_jobs = {}
    unclassified = 0
    for job in jobs:
        area = classify_area(job)
        if not area:
            unclassified += 1
            continue
        if area not in area_jobs_raw:
            area_jobs_raw[area] = []
        area_jobs_raw[area].append(job)

    # ソート（正社員優先・給与高い順）→ フォーマット → 重複除去
    for area in area_jobs_raw:
        sorted_jobs = sorted(area_jobs_raw[area], key=salary_sort_key)
        seen_employers = set()
        unique_jobs = []
        for j in sorted_jobs:
            formatted = format_job_string(j)
            if not formatted:
                continue
            employer = formatted.split(":")[0].strip()
            if employer not in seen_employers:
                seen_employers.add(employer)
                unique_jobs.append(formatted)
        area_jobs[area] = unique_jobs[:args.max_per_area]

    print(f"📊 エリア別:")
    total_classified = 0
    for area in sorted(area_jobs.keys(), key=lambda a: -len(area_jobs[a])):
        count = len(area_jobs[area])
        total_classified += count
        print(f"   {area}: {count}件")
    print(f"   分類不能: {unclassified}件")
    print(f"   合計: {total_classified}件")

    if args.json:
        print(json.dumps(area_jobs, ensure_ascii=False, indent=2))
        return

    if args.dry_run:
        print("\n--- プレビュー（先頭3件/エリア）---")
        for area, ajobs in sorted(area_jobs.items(), key=lambda x: -len(x[1])):
            print(f"\n  【{area}】")
            for j in ajobs[:3]:
                print(f"    {j}")
        return

    # worker.js の EXTERNAL_JOBS を更新
    if not WORKER_JS.exists():
        print(f"❌ {WORKER_JS} が見つかりません")
        sys.exit(1)

    worker_content = WORKER_JS.read_text(encoding="utf-8")

    # EXTERNAL_JOBS ブロックを検索して置換
    # パターン: "// ---------- 外部公開求人データ" から "};" + 空行まで
    pattern = r'// ---------- 外部公開求人データ.*?\n.*?const EXTERNAL_JOBS = \{.*?\n\};\n'
    match = re.search(pattern, worker_content, re.DOTALL)
    if not match:
        print("❌ EXTERNAL_JOBS ブロックが見つかりません")
        sys.exit(1)

    # 新しい EXTERNAL_JOBS を生成
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f'// ---------- 外部公開求人データ（ハローワークAPI {today}更新） ----------']
    lines.append('const EXTERNAL_JOBS = {')
    lines.append('  nurse: {')

    # エリア順序を既存の順序に合わせる
    area_order = ["横浜", "川崎", "相模原", "横須賀", "鎌倉", "藤沢",
                  "茅ヶ崎", "平塚", "大磯", "秦野", "伊勢原", "厚木",
                  "大和", "海老名", "小田原", "南足柄・開成"]

    for area in area_order:
        if area not in area_jobs or not area_jobs[area]:
            continue
        lines.append(f'    "{area}": [')
        for j in area_jobs[area]:
            # エスケープ
            escaped = j.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'      "{escaped}",')
        lines.append('    ],')

    lines.append('  },')

    # PT求人はハローワークデータにないので既存のまま維持
    # → 既存のptブロックを抽出
    pt_pattern = r'  pt: \{.*?\n  \},'
    pt_match = re.search(pt_pattern, worker_content, re.DOTALL)
    if pt_match:
        lines.append(pt_match.group())
    else:
        lines.append('  pt: {},')

    lines.append('};')

    new_block = '\n'.join(lines) + '\n'
    new_content = worker_content[:match.start()] + new_block + worker_content[match.end():]

    WORKER_JS.write_text(new_content, encoding="utf-8")
    print(f"\n✅ {WORKER_JS} 更新完了（{today}）")
    print(f"   nurse: {sum(len(v) for v in area_jobs.values())}件 ({len(area_jobs)}エリア)")


if __name__ == "__main__":
    main()
