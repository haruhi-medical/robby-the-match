#!/usr/bin/env python3
"""Generate a lightweight JSON summary of job data for the LP diagnostic UI.

Input:  data/hellowork_ranked.json
Output: lp/job-seeker/jobs-summary.json
"""

import json
import os
import re
import sys
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_PATH = os.path.join(PROJECT_ROOT, "data", "hellowork_ranked.json")
OUTPUT_PATH = os.path.join(PROJECT_ROOT, "lp", "job-seeker", "jobs-summary.json")

# Area grouping: area string -> group key
AREA_GROUPS = {
    "yokohama_kawasaki": {
        "name": "横浜・川崎",
        "areas": ["横浜", "川崎"],
    },
    "shonan_kamakura": {
        "name": "湘南・鎌倉",
        "areas": ["藤沢", "茅ヶ崎", "鎌倉", "平塚", "大磯"],
    },
    "odawara_seisho": {
        "name": "小田原・県西",
        "areas": ["小田原", "南足柄・開成"],
    },
    "sagamihara_kenoh": {
        "name": "相模原・県央",
        "areas": ["相模原", "厚木", "海老名", "大和", "秦野", "伊勢原"],
    },
    "yokosuka_miura": {
        "name": "横須賀・三浦",
        "areas": ["横須賀"],
    },
}

# Reverse lookup: area string -> group key
AREA_TO_GROUP = {}
for group_key, group_info in AREA_GROUPS.items():
    for area in group_info["areas"]:
        AREA_TO_GROUP[area] = group_key

QUALIFIED_RANKS = {"S", "A", "B"}
RANK_PRIORITY = {"S": 0, "A": 1, "B": 2}


def parse_int(val):
    """Extract integer from a string like '250000' or '38.0万円'."""
    if val is None:
        return None
    val = str(val).strip()
    if not val:
        return None
    # Try direct int parse
    try:
        return int(val)
    except ValueError:
        pass
    # Extract digits
    digits = re.sub(r"[^\d]", "", val)
    if digits:
        return int(digits)
    return None


def parse_holidays(val):
    """Extract holiday count from string like '121日'."""
    if val is None:
        return None
    m = re.search(r"(\d+)", str(val))
    return int(m.group(1)) if m else None


def normalize_to_monthly(value, salary_form):
    """Convert salary value to monthly equivalent based on salary_form."""
    if value is None:
        return None
    form = str(salary_form or "").strip()
    if form == "時給":
        # Hourly: assume 160 hours/month (8h * 20 days)
        return value * 160
    elif form == "年俸制":
        # Annual: divide by 12
        return value // 12
    else:
        # Monthly (default)
        return value


def has_bonus(bonus_detail):
    """Check if bonus exists based on bonus_detail field."""
    if not bonus_detail:
        return False
    s = str(bonus_detail).strip()
    if not s:
        return False
    # Check for explicit "なし" or zero
    if "なし" in s or s == "0":
        return False
    return True


def truncate(text, max_len=20):
    """Truncate text to max_len characters."""
    if not text:
        return ""
    text = str(text).strip()
    # Remove decorative chars
    text = re.sub(r"[◆★●■▲▼◎○※☆♪♥]+", "", text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len]


def main():
    # Load input
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    jobs = data["jobs"]

    # Filter to B rank and above
    qualified = [j for j in jobs if j.get("rank") in QUALIFIED_RANKS]
    print(f"Total jobs: {len(jobs)}, Qualified (S/A/B): {len(qualified)}")

    # Group jobs by area group
    grouped = {key: [] for key in AREA_GROUPS}
    ungrouped_areas = set()

    for job in qualified:
        area = job.get("area", "")
        group_key = AREA_TO_GROUP.get(area)
        if group_key:
            grouped[group_key].append(job)
        else:
            ungrouped_areas.add(area)

    if ungrouped_areas:
        print(f"Warning: areas not mapped to any group: {ungrouped_areas}")

    # Build output
    areas_output = {}

    all_salary_mins = []
    all_salary_maxs = []
    all_holidays = []
    all_count = 0
    all_seishain = 0
    all_part = 0
    all_best_sample = None
    all_best_score = -1

    for group_key, group_info in AREA_GROUPS.items():
        group_jobs = grouped[group_key]
        if not group_jobs:
            areas_output[group_key] = {
                "name": group_info["name"],
                "count": 0,
                "salary_min": None,
                "salary_max": None,
                "holidays_avg": None,
                "sample": None,
            }
            continue

        count = len(group_jobs)
        all_count += count

        # Salary calculations
        salary_lows = []
        salary_highs = []
        holidays_list = []
        seishain = 0
        part = 0

        best_sample_job = None
        best_score = -1
        top_jobs = []  # For blurred teaser cards

        for job in group_jobs:
            salary_form = job.get("salary_form", "月給")
            sl = normalize_to_monthly(parse_int(job.get("salary_low")), salary_form)
            sh = normalize_to_monthly(parse_int(job.get("salary_high")), salary_form)
            # Sanity check: reasonable monthly range 10万〜80万円
            if sl and 100000 <= sl <= 800000:
                salary_lows.append(sl)
            if sh and 100000 <= sh <= 800000:
                salary_highs.append(sh)

            h = parse_holidays(job.get("annual_holidays"))
            if h:
                holidays_list.append(h)

            emp = str(job.get("employment_type", ""))
            if "正社員" in emp:
                seishain += 1
            elif "パート" in emp:
                part += 1

            # Track best sample (S/A rank, highest score)
            rank = job.get("rank", "")
            score = job.get("score", 0)
            if rank in ("S", "A"):
                top_jobs.append((score, job))
            if rank in ("S", "A") and score > best_score:
                best_score = score
                best_sample_job = job

        all_seishain += seishain
        all_part += part

        # Annual salary estimates: low*12 for min, high*16 for max (万円)
        salary_min = round(min(salary_lows) * 12 / 10000) if salary_lows else None
        salary_max = round(max(salary_highs) * 16 / 10000) if salary_highs else None

        if salary_lows:
            all_salary_mins.append(min(salary_lows))
        if salary_highs:
            all_salary_maxs.append(max(salary_highs))
        all_holidays.extend(holidays_list)

        holidays_avg = round(sum(holidays_list) / len(holidays_list)) if holidays_list else None

        # Sample job
        sample = None
        if best_sample_job:
            j = best_sample_job
            sf = j.get("salary_form", "月給")
            sl = normalize_to_monthly(parse_int(j.get("salary_low")), sf)
            sh = normalize_to_monthly(parse_int(j.get("salary_high")), sf)
            salary_str = ""
            if sl and sh:
                salary_str = f"月給{sl // 10000}〜{sh // 10000}万円"
            elif sl:
                salary_str = f"月給{sl // 10000}万円〜"

            sample = {
                "title": truncate(j.get("job_title", ""), 20),
                "salary": salary_str,
                "holidays": str(parse_holidays(j.get("annual_holidays")) or "") + "日" if parse_holidays(j.get("annual_holidays")) else "",
                "bonus": has_bonus(j.get("bonus_detail")),
                "type": j.get("employment_type", ""),
            }

            if best_score > all_best_score:
                all_best_score = best_score
                all_best_sample = sample

        # Blurred teaser cards — #39 guarantee 3 cards minimum
        # 上位4件を取り sample(=1位)を除いた2,3,4位を blurred とする。
        # グループに十分な件数がない場合は group_jobs 全体から S/A/B を補充して3枚埋める。
        blurred = []
        top_jobs.sort(key=lambda x: -x[0])
        seen_titles = set()
        if best_sample_job:
            seen_titles.add(truncate(best_sample_job.get("job_title", ""), 20))
        # まず top_jobs（S/A）から採用
        for _, bj in top_jobs[1:]:
            if len(blurred) >= 3:
                break
            t = truncate(bj.get("job_title", ""), 20)
            if not t or t in seen_titles:
                continue
            seen_titles.add(t)
            bsf = bj.get("salary_form", "月給")
            bsl = normalize_to_monthly(parse_int(bj.get("salary_low")), bsf)
            bsh = normalize_to_monthly(parse_int(bj.get("salary_high")), bsf)
            bs = ""
            if bsl and bsh:
                bs = f"月給{bsl // 10000}〜{bsh // 10000}万円"
            elif bsl:
                bs = f"月給{bsl // 10000}万円〜"
            blurred.append({
                "title": t,
                "salary": bs,
                "holidays": str(parse_holidays(bj.get("annual_holidays")) or "") + "日" if parse_holidays(bj.get("annual_holidays")) else "",
                "bonus": has_bonus(bj.get("bonus_detail")),
                "type": bj.get("employment_type", ""),
            })
        # 不足時: group_jobs全体から B/C も含めて補充（#39 最低3枚保証）
        if len(blurred) < 3:
            by_score = sorted(group_jobs, key=lambda j: -(j.get("score", 0) or 0))
            for bj in by_score:
                if len(blurred) >= 3:
                    break
                t = truncate(bj.get("job_title", ""), 20)
                if not t or t in seen_titles:
                    continue
                seen_titles.add(t)
                bsf = bj.get("salary_form", "月給")
                bsl = normalize_to_monthly(parse_int(bj.get("salary_low")), bsf)
                bsh = normalize_to_monthly(parse_int(bj.get("salary_high")), bsf)
                bs = ""
                if bsl and bsh:
                    bs = f"月給{bsl // 10000}〜{bsh // 10000}万円"
                elif bsl:
                    bs = f"月給{bsl // 10000}万円〜"
                blurred.append({
                    "title": t,
                    "salary": bs,
                    "holidays": str(parse_holidays(bj.get("annual_holidays")) or "") + "日" if parse_holidays(bj.get("annual_holidays")) else "",
                    "bonus": has_bonus(bj.get("bonus_detail")),
                    "type": bj.get("employment_type", ""),
                })

        areas_output[group_key] = {
            "name": group_info["name"],
            "count": count,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "holidays_avg": holidays_avg,
            "sample": sample,
            "blurred": blurred if blurred else None,
        }

        print(f"  {group_info['name']}: {count} jobs, salary {salary_min}〜{salary_max}万円, holidays avg {holidays_avg}")

    # All areas combined
    all_salary_min = round(min(all_salary_mins) * 12 / 10000) if all_salary_mins else None
    all_salary_max = round(max(all_salary_maxs) * 16 / 10000) if all_salary_maxs else None
    all_holidays_avg = round(sum(all_holidays) / len(all_holidays)) if all_holidays else None

    # Collect blurred for "all" — #39 集約して3枚保証
    # 全エリアの blurred をマージし、ユニーク化して先頭3件を使う
    all_blurred = []
    seen_all_titles = set()
    for gk in areas_output:
        for b in (areas_output[gk].get("blurred") or []):
            t = b.get("title", "")
            if t and t not in seen_all_titles:
                seen_all_titles.add(t)
                all_blurred.append(b)
            if len(all_blurred) >= 3:
                break
        if len(all_blurred) >= 3:
            break
    # 補充: 全求人からさらに埋める
    if len(all_blurred) < 3:
        combined = []
        for group_jobs_list in grouped.values():
            combined.extend(group_jobs_list)
        combined.sort(key=lambda j: -(j.get("score", 0) or 0))
        for bj in combined:
            if len(all_blurred) >= 3:
                break
            t = truncate(bj.get("job_title", ""), 20)
            if not t or t in seen_all_titles:
                continue
            seen_all_titles.add(t)
            bsf = bj.get("salary_form", "月給")
            bsl = normalize_to_monthly(parse_int(bj.get("salary_low")), bsf)
            bsh = normalize_to_monthly(parse_int(bj.get("salary_high")), bsf)
            bs = ""
            if bsl and bsh:
                bs = f"月給{bsl // 10000}〜{bsh // 10000}万円"
            elif bsl:
                bs = f"月給{bsl // 10000}万円〜"
            all_blurred.append({
                "title": t,
                "salary": bs,
                "holidays": str(parse_holidays(bj.get("annual_holidays")) or "") + "日" if parse_holidays(bj.get("annual_holidays")) else "",
                "bonus": has_bonus(bj.get("bonus_detail")),
                "type": bj.get("employment_type", ""),
            })
    if not all_blurred:
        all_blurred = None

    areas_output["all"] = {
        "name": "神奈川県全域",
        "count": all_count,
        "salary_min": all_salary_min,
        "salary_max": all_salary_max,
        "holidays_avg": all_holidays_avg,
        "sample": all_best_sample,
        "blurred": all_blurred,
    }

    output = {
        "updated": str(date.today()),
        "total_qualified": all_count,
        "areas": areas_output,
    }

    # Write output
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput written to {OUTPUT_PATH}")
    print(f"Total qualified: {all_count}")


if __name__ == "__main__":
    main()
