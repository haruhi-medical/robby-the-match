#!/usr/bin/env python3
"""D1 facilities から上位100施設（神奈川県）を取得して data/hospitals_top100.json に保存。

並び順: bed_count DESC NULLS LAST（大規模病院優先）
出力各項目: id / name / category / sub_type / prefecture / city / address /
           nearest_station / station_minutes / bed_count / departments /
           nurse_fulltime / nurse_parttime / is_tokutei / is_chiiki_shien
"""
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "hospitals_top100.json"


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
        print(f"[D1 ERROR] {proc.stderr[:300]}")
        return []
    try:
        data = json.loads(proc.stdout.strip())
        if isinstance(data, list) and data:
            return data[0].get("results", [])
    except Exception as e:
        print(f"parse error: {e}")
    return []


def main():
    rows = d1(
        "SELECT id, name, category, sub_type, prefecture, city, address, "
        "nearest_station, station_minutes, bed_count, departments, "
        "nurse_fulltime, nurse_parttime, is_tokutei, is_chiiki_shien "
        "FROM facilities "
        "WHERE prefecture = '神奈川県' AND bed_count > 0 "
        "ORDER BY bed_count DESC LIMIT 100"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Saved: {OUT} ({len(rows)} hospitals)")
    # サンプル3件
    for r in rows[:3]:
        print(f"  - {r['name']} ({r['bed_count']}床 / {r.get('sub_type') or 'N/A'} / {r['city']})")


if __name__ == "__main__":
    main()
