#!/usr/bin/env python3
"""診療科×エリアページ用のD1統計抽出。

対象: 5専門科 × 5主要市 = 25組み合わせ
専門科: 精神科 / 整形外科 / 内科 / 小児科 / 産婦人科
市: 横浜市 / 川崎市 / 相模原市 / 藤沢市 / 横須賀市

各ページに固有のデータを集めて薄いコンテンツを回避する。
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "specialty_stats.json"

SPECIALTIES = [
    ("seishinka", "精神科", "精神科"),
    ("seikeigeka", "整形外科", "整形外科"),
    ("naika", "内科", "内科"),
    ("shonika", "小児科", "小児科"),
    ("sanfujinka", "産婦人科", "産婦人科"),
]

CITIES = [
    ("yokohama", "横浜市"),
    ("kawasaki", "川崎市"),
    ("sagamihara", "相模原市"),
    ("fujisawa", "藤沢市"),
    ("yokosuka", "横須賀市"),
]


def d1(sql: str) -> list:
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)
    cmd = [
        "npx", "wrangler", "d1", "execute", "nurse-robby-db",
        "--remote", "--config", "wrangler.toml",
        "--json", "--command", sql,
    ]
    proc = subprocess.run(
        cmd, cwd=ROOT / "api", env=env, capture_output=True, text=True, timeout=90
    )
    if proc.returncode != 0:
        print(f"[D1 ERROR] {proc.stderr[:200]}")
        return []
    try:
        data = json.loads(proc.stdout.strip())
        if isinstance(data, list) and data:
            return data[0].get("results", [])
    except Exception as e:
        print(f"parse error: {e}")
    return []


def specialty_city_stats(city_ja: str, specialty_dept: str) -> dict:
    city_like = f"%{city_ja}%"
    spec_like = f"%{specialty_dept}%"

    # 施設数（departments に専門科を含む）
    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM facilities "
        f"WHERE city LIKE '{city_like}' AND departments LIKE '{spec_like}'"
    )
    facility_count = int(rows[0].get("cnt") or 0) if rows else 0

    # 代表施設上位5（規模・駅近優先、徒歩30分以内）
    rows = d1(
        f"SELECT name, nearest_station, station_minutes, bed_count, sub_type, category "
        f"FROM facilities "
        f"WHERE city LIKE '{city_like}' AND departments LIKE '{spec_like}' "
        f"AND (station_minutes IS NULL OR station_minutes <= 30) "
        f"ORDER BY bed_count DESC NULLS LAST LIMIT 5"
    )
    top_facilities = [
        {
            "name": r.get("name"),
            "station": r.get("nearest_station"),
            "minutes": r.get("station_minutes"),
            "beds": r.get("bed_count"),
            "sub_type": r.get("sub_type"),
            "category": r.get("category"),
        }
        for r in rows
    ]

    # 求人件数（jobsテーブルの title/description に診療科を含むもの）
    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{city_like}' "
        f"AND (title LIKE '{spec_like}' OR description LIKE '{spec_like}')"
    )
    job_count = int(rows[0].get("cnt") or 0) if rows else 0

    # 平均月給（月給のみ）
    rows = d1(
        f"SELECT AVG(salary_min) AS smin, AVG(salary_max) AS smax FROM jobs "
        f"WHERE work_location LIKE '{city_like}' "
        f"AND (title LIKE '{spec_like}' OR description LIKE '{spec_like}') "
        f"AND salary_form = '月給' AND salary_min > 150000 AND salary_max < 800000"
    )
    monthly_min = int(rows[0].get("smin") or 0) if rows and rows[0].get("smin") else None
    monthly_max = int(rows[0].get("smax") or 0) if rows and rows[0].get("smax") else None

    return {
        "facility_count": facility_count,
        "job_count": job_count,
        "monthly_min": monthly_min,
        "monthly_max": monthly_max,
        "annual_min": int(monthly_min * 14) if monthly_min else None,
        "annual_max": int(monthly_max * 14) if monthly_max else None,
        "top_facilities": top_facilities,
    }


def main():
    out = {}
    for spec_slug, spec_ja, spec_dept in SPECIALTIES:
        for city_slug, city_ja in CITIES:
            key = f"{city_slug}-{spec_slug}"
            print(f"[{key}] fetching…", flush=True)
            s = specialty_city_stats(city_ja, spec_dept)
            s["city_slug"] = city_slug
            s["city_ja"] = city_ja
            s["specialty_slug"] = spec_slug
            s["specialty_ja"] = spec_ja
            out[key] = s
            print(
                f"  facilities={s['facility_count']} jobs={s['job_count']} "
                f"annual=¥{s.get('annual_min') or 0}〜¥{s.get('annual_max') or 0}"
            )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved: {OUT} ({len(out)} combinations)")


if __name__ == "__main__":
    main()
