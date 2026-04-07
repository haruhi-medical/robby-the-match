#!/usr/bin/env python3
"""
ハローワーク求人 → D1 jobsテーブル 全件INSERT

hellowork_rank.py の出力（data/hellowork_ranked.json）を
Cloudflare D1 の jobs テーブルに全件投入する。

使い方:
  python3 scripts/hellowork_to_d1.py              # 本番D1に投入
  python3 scripts/hellowork_to_d1.py --dry-run     # SQLファイル出力のみ（D1更新なし）
  python3 scripts/hellowork_to_d1.py --local        # ローカルSQLiteに投入（テスト用）
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RANKED_FILE = PROJECT_ROOT / "data" / "hellowork_ranked.json"
SQL_OUTPUT = PROJECT_ROOT / "data" / "hellowork_jobs_d1.sql"
LOCAL_DB = PROJECT_ROOT / "data" / "hellowork_jobs.sqlite"
WRANGLER_CONFIG = PROJECT_ROOT / "api" / "wrangler.toml"
D1_DB_NAME = "nurse-robby-db"


def load_ranked_jobs():
    """ランク済み求人データを読み込み"""
    with open(RANKED_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("jobs", [])


def escape_sql(s):
    """SQL文字列エスケープ"""
    if s is None:
        return "NULL"
    s = str(s).replace("'", "''")
    return f"'{s}'"


def build_sql(jobs):
    """全求人のINSERT文を生成"""
    lines = []
    lines.append("-- ハローワーク求人 D1投入SQL")
    lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 件数: {len(jobs)}")
    lines.append("")

    # テーブル再作成
    lines.append("DROP TABLE IF EXISTS jobs;")
    lines.append("""CREATE TABLE jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kjno TEXT UNIQUE,
  employer TEXT NOT NULL,
  title TEXT,
  rank TEXT,
  score INTEGER,
  area TEXT,
  prefecture TEXT,
  work_location TEXT,
  salary_form TEXT,
  salary_min INTEGER,
  salary_max INTEGER,
  salary_display TEXT,
  bonus_text TEXT,
  holidays INTEGER,
  emp_type TEXT,
  station_text TEXT,
  shift1 TEXT,
  shift2 TEXT,
  description TEXT,
  welfare TEXT,
  score_sal INTEGER,
  score_hol INTEGER,
  score_bon INTEGER,
  score_emp INTEGER,
  score_wel INTEGER,
  score_loc INTEGER,
  synced_at TEXT
);""")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_area ON jobs(area);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_prefecture ON jobs(prefecture);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_rank ON jobs(rank);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_emp_type ON jobs(emp_type);")
    lines.append("")

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for j in jobs:
        details = j.get("details", {})
        bd = j.get("breakdown", {})

        # 都道府県を勤務地から抽出
        loc = j.get("work_location", "") or ""
        pref = ""
        for p in ["東京都", "神奈川県", "千葉県", "埼玉県"]:
            if p in loc:
                pref = p
                break

        # 年間休日数値
        holidays_str = j.get("annual_holidays", "")
        holidays_num = 0
        if holidays_str:
            m = re.search(r"(\d+)", str(holidays_str))
            if m:
                holidays_num = int(m.group(1))

        # 仕事内容（300文字制限）
        desc = (j.get("job_description", "") or "")[:300]

        vals = [
            escape_sql(j.get("kjno", "")),
            escape_sql(j.get("employer", "")),
            escape_sql(j.get("job_title", "")),
            escape_sql(j.get("rank", "")),
            str(j.get("score", 0)),
            escape_sql(j.get("area", "")),
            escape_sql(pref),
            escape_sql(loc),
            escape_sql(j.get("salary_form", "")),
            str(j.get("salary_low", 0) or 0),
            str(j.get("salary_high", 0) or 0),
            escape_sql(details.get("salary", "")),
            escape_sql(details.get("bonus", "")),
            str(holidays_num),
            escape_sql(details.get("emp_type", "")),
            escape_sql(j.get("work_station_text", "")),
            escape_sql(j.get("shift1", "")),
            escape_sql(j.get("shift2", "")),
            escape_sql(desc),
            escape_sql(details.get("welfare", "")),
            str(bd.get("sal", 0)),
            str(bd.get("hol", 0)),
            str(bd.get("bon", 0)),
            str(bd.get("emp", 0)),
            str(bd.get("wel", 0)),
            str(bd.get("loc", 0)),
            escape_sql(synced_at),
        ]

        lines.append(
            "INSERT OR IGNORE INTO jobs (kjno,employer,title,rank,score,area,prefecture,"
            "work_location,salary_form,salary_min,salary_max,salary_display,"
            "bonus_text,holidays,emp_type,station_text,shift1,shift2,"
            "description,welfare,score_sal,score_hol,score_bon,score_emp,"
            "score_wel,score_loc,synced_at) VALUES ("
            + ",".join(vals) + ");"
        )

    return "\n".join(lines)


def deploy_to_d1(sql_file):
    """wrangler d1 execute でリモートD1に投入"""
    cmd = [
        "npx", "wrangler", "d1", "execute", D1_DB_NAME,
        "--config", str(WRANGLER_CONFIG),
        "--remote",
        "--file", str(sql_file),
    ]
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)  # OAuth認証を使う

    print(f"実行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT / "api"), env=env,
                          capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
        return False
    print(result.stdout)
    return True


def deploy_to_local(sql_text):
    """ローカルSQLiteに投入（テスト用）"""
    if LOCAL_DB.exists():
        LOCAL_DB.unlink()
    conn = sqlite3.connect(str(LOCAL_DB))
    conn.executescript(sql_text)
    # 確認
    cnt = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    print(f"ローカルDB: {LOCAL_DB} ({cnt}件)")
    return True


def main():
    parser = argparse.ArgumentParser(description="ハローワーク求人 → D1 jobsテーブル投入")
    parser.add_argument("--dry-run", action="store_true", help="SQLファイル出力のみ")
    parser.add_argument("--local", action="store_true", help="ローカルSQLiteに投入")
    args = parser.parse_args()

    # データ読み込み
    jobs = load_ranked_jobs()
    print(f"入力: {len(jobs)}件のランク済み求人")

    # ランク分布
    rank_counts = {}
    for j in jobs:
        r = j.get("rank", "?")
        rank_counts[r] = rank_counts.get(r, 0) + 1
    for r in ["S", "A", "B", "C", "D"]:
        print(f"  {r}ランク: {rank_counts.get(r, 0)}件")

    # SQL生成
    sql_text = build_sql(jobs)
    with open(SQL_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sql_text)
    print(f"SQL出力: {SQL_OUTPUT}")

    if args.dry_run:
        print("(dry-run: D1更新なし)")
        return

    if args.local:
        deploy_to_local(sql_text)
        return

    # 本番D1に投入
    print("\n=== D1リモート投入 ===")
    success = deploy_to_d1(SQL_OUTPUT)
    if success:
        print("✅ D1 jobsテーブル更新完了")
    else:
        print("❌ D1投入失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
