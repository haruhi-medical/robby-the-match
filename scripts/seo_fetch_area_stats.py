#!/usr/bin/env python3
"""D1からエリア別統計を取得してarea-stats.jsonに保存する。

各エリア（市区町村）ごとに:
- facility_count: 施設総数
- active_facility_count: 求人ある施設数
- job_count: 求人数
- salary_avg_min / salary_avg_max: 平均給与帯
- top_facilities: 代表施設上位5
- top_stations: よく登録される駅上位5
- category_counts: 施設タイプ別内訳

出力: data/area_stats.json

実行:
    python3 scripts/seo_fetch_area_stats.py
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "area_stats.json"

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


def d1(sql: str) -> list:
    """wranglerでD1を実行してJSON結果を返す。"""
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)
    cmd = [
        "npx", "wrangler", "d1", "execute", "nurse-robby-db",
        "--remote", "--config", "wrangler.toml",
        "--json", "--command", sql,
    ]
    proc = subprocess.run(
        cmd, cwd=ROOT / "api", env=env, capture_output=True, text=True, timeout=60
    )
    if proc.returncode != 0:
        print(f"[D1 ERROR] {proc.stderr[:300]}")
        return []
    out = proc.stdout.strip()
    try:
        data = json.loads(out)
        if isinstance(data, list) and data:
            return data[0].get("results", [])
    except Exception as e:
        print(f"[parse error] {e}: {out[:200]}")
    return []


def city_stats(city_jp: str) -> dict:
    """1市区町村ぶんの統計を取得。"""
    like = f"%{city_jp}%"
    result = {"city": city_jp}

    # facilities総数 + アクティブ求人持ち施設数
    rows = d1(
        f"SELECT COUNT(*) AS total, SUM(has_active_jobs) AS active "
        f"FROM facilities WHERE city LIKE '{like}'"
    )
    if rows:
        result["facility_count"] = int(rows[0].get("total") or 0)
        result["active_facility_count"] = int(rows[0].get("active") or 0)

    # 求人数（全件）
    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM jobs WHERE work_location LIKE '{like}'"
    )
    if rows:
        result["job_count"] = int(rows[0].get("cnt") or 0)

    # 平均月給（月給形式のみ） → 年収換算用
    rows = d1(
        f"SELECT AVG(salary_min) AS smin, AVG(salary_max) AS smax "
        f"FROM jobs WHERE work_location LIKE '{like}' "
        f"AND salary_form = '月給' AND salary_min > 150000 AND salary_max < 800000"
    )
    if rows:
        smin = rows[0].get("smin")
        smax = rows[0].get("smax")
        result["monthly_min"] = int(smin) if smin else None
        result["monthly_max"] = int(smax) if smax else None
        # 年収換算（ボーナス2ヶ月想定で14倍）
        result["annual_min"] = int(smin * 14) if smin else None
        result["annual_max"] = int(smax * 14) if smax else None

    # 求人形態別内訳
    rows = d1(
        f"SELECT emp_type, COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{like}' AND emp_type IS NOT NULL "
        f"GROUP BY emp_type ORDER BY cnt DESC LIMIT 5"
    )
    result["emp_type_counts"] = {
        r.get("emp_type"): int(r.get("cnt") or 0) for r in rows if r.get("emp_type")
    }

    # カテゴリ別
    rows = d1(
        f"SELECT category, COUNT(*) AS cnt FROM facilities "
        f"WHERE city LIKE '{like}' GROUP BY category ORDER BY cnt DESC"
    )
    result["category_counts"] = {
        r.get("category") or "その他": int(r.get("cnt") or 0) for r in rows
    }

    # 代表施設上位5（規模・駅近優先、徒歩30分以上は除外してUX改善）
    rows = d1(
        f"SELECT name, nearest_station, station_minutes, bed_count, sub_type, category "
        f"FROM facilities WHERE city LIKE '{like}' "
        f"AND (station_minutes IS NULL OR station_minutes <= 30) "
        f"ORDER BY bed_count DESC NULLS LAST LIMIT 5"
    )
    result["top_facilities"] = [
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

    # 主要駅上位5
    rows = d1(
        f"SELECT nearest_station, COUNT(*) AS cnt FROM facilities "
        f"WHERE city LIKE '{like}' AND nearest_station IS NOT NULL AND nearest_station != '' "
        f"GROUP BY nearest_station ORDER BY cnt DESC LIMIT 5"
    )
    result["top_stations"] = [
        {"station": r.get("nearest_station"), "count": int(r.get("cnt") or 0)}
        for r in rows
    ]

    # === 2026-04-20 追加: 重複率削減用の拡張統計 ===

    # 特定機能病院 / 地域医療支援病院（承認制の客観的事実のみ）
    rows = d1(
        f"SELECT COUNT(*) AS tokutei FROM facilities "
        f"WHERE city LIKE '{like}' AND is_tokutei = 1"
    )
    result["tokutei_count"] = int(rows[0].get("tokutei") or 0) if rows else 0

    rows = d1(
        f"SELECT COUNT(*) AS shien FROM facilities "
        f"WHERE city LIKE '{like}' AND is_chiiki_shien = 1"
    )
    result["chiiki_shien_count"] = int(rows[0].get("shien") or 0) if rows else 0

    # 病床規模帯（小規模<100 / 中規模100-299 / 大規模300+）
    rows = d1(
        f"SELECT "
        f"  SUM(CASE WHEN bed_count > 0 AND bed_count < 100 THEN 1 ELSE 0 END) AS small, "
        f"  SUM(CASE WHEN bed_count >= 100 AND bed_count < 300 THEN 1 ELSE 0 END) AS medium, "
        f"  SUM(CASE WHEN bed_count >= 300 THEN 1 ELSE 0 END) AS large "
        f"FROM facilities WHERE city LIKE '{like}'"
    )
    if rows:
        result["bed_size"] = {
            "small": int(rows[0].get("small") or 0),
            "medium": int(rows[0].get("medium") or 0),
            "large": int(rows[0].get("large") or 0),
        }

    # sub_type 別内訳（急性期/慢性期/回復期/精神科 等）
    rows = d1(
        f"SELECT sub_type, COUNT(*) AS cnt FROM facilities "
        f"WHERE city LIKE '{like}' AND sub_type IS NOT NULL AND sub_type != '' "
        f"GROUP BY sub_type ORDER BY cnt DESC LIMIT 5"
    )
    result["sub_type_counts"] = {
        r.get("sub_type"): int(r.get("cnt") or 0) for r in rows if r.get("sub_type")
    }

    # 診療科偏在（departments から頻出キーワード抽出）
    # departments はカンマ区切りなので SQLite 関数で分解が難しい→
    # 各施設の departments を取得してPython側で集計
    rows = d1(
        f"SELECT departments FROM facilities "
        f"WHERE city LIKE '{like}' AND departments IS NOT NULL AND departments != '' "
        f"LIMIT 300"
    )
    dept_counter = {}
    for r in rows:
        depts = (r.get("departments") or "").split(",")
        for d in depts:
            d = d.strip()
            if not d:
                continue
            dept_counter[d] = dept_counter.get(d, 0) + 1
    # 上位7診療科
    top_depts = sorted(dept_counter.items(), key=lambda x: -x[1])[:7]
    result["top_departments"] = [{"name": k, "count": v} for k, v in top_depts]

    # 条件別求人件数（日勤/パート/訪問看護）
    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{like}' AND emp_type LIKE '%正社員%' "
        f"AND (shift1 LIKE '%日勤%' OR shift2 LIKE '%日勤%' OR title LIKE '%日勤%')"
    )
    result["job_count_day"] = int(rows[0].get("cnt") or 0) if rows else 0

    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{like}' AND emp_type LIKE '%パート%'"
    )
    result["job_count_part"] = int(rows[0].get("cnt") or 0) if rows else 0

    rows = d1(
        f"SELECT COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{like}' "
        f"AND (employer LIKE '%訪問看護%' OR title LIKE '%訪問看護%' OR description LIKE '%訪問看護%')"
    )
    result["job_count_houmon"] = int(rows[0].get("cnt") or 0) if rows else 0

    # 主要法人（employer）上位3 — 同エリアの求人を多く抱える法人
    rows = d1(
        f"SELECT employer, COUNT(*) AS cnt FROM jobs "
        f"WHERE work_location LIKE '{like}' AND employer IS NOT NULL "
        f"GROUP BY employer ORDER BY cnt DESC LIMIT 3"
    )
    result["top_employers"] = [
        {"name": r.get("employer"), "count": int(r.get("cnt") or 0)}
        for r in rows if r.get("employer")
    ]

    return result


def main():
    out = {}
    for slug, city_jp in AREAS:
        print(f"[{slug}] fetching…", flush=True)
        s = city_stats(city_jp)
        out[slug] = s
        print(
            f"  facility={s.get('facility_count', 0)} active={s.get('active_facility_count', 0)} "
            f"jobs={s.get('job_count', 0)} salary=¥{(s.get('salary_avg_min') or 0)}〜¥{(s.get('salary_avg_max') or 0)}"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Saved: {OUT} ({len(out)} areas)")


if __name__ == "__main__":
    main()
