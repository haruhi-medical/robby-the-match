#!/usr/bin/env python3
"""
求人DB検索CLI — ナースロビー社内用

Cloudflare D1 jobs テーブルを wrangler d1 execute で検索する。
47都道府県の看護師求人（ハローワーク経由、派遣・保育園等除外済）から
条件指定で絞り込み、テーブル形式で表示する。

使い方:
  python3 scripts/search_jobs.py --pref 神奈川県                      # 神奈川全件
  python3 scripts/search_jobs.py --pref 大阪府 --salary-min 250000   # 大阪・月給25万以上
  python3 scripts/search_jobs.py --pref 東京都 --emp 常勤 --rank S A # 東京・常勤・SA
  python3 scripts/search_jobs.py --keyword 訪問看護 --limit 50        # キーワード検索
  python3 scripts/search_jobs.py --city 横浜市                         # 市区町村検索
  python3 scripts/search_jobs.py --stats                              # 全体統計
  python3 scripts/search_jobs.py --kjno 12090-07190061                # 1件詳細

  全オプション同時指定可。--detail で詳細表示、--json でJSON出力
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WRANGLER_CONFIG = PROJECT_ROOT / "api" / "wrangler.toml"
D1_DB_NAME = "nurse-robby-db"


def d1_query(sql, timeout=60):
    """wrangler d1 execute --command で SELECT実行 → results配列を返す"""
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)
    cmd = [
        "npx", "wrangler", "d1", "execute", D1_DB_NAME,
        "--config", str(WRANGLER_CONFIG),
        "--remote",
        "--command", sql,
        "--json",
    ]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT / "api"), env=env,
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        print(f"❌ D1クエリ失敗: {result.stderr[:500]}", file=sys.stderr)
        sys.exit(1)
    try:
        data = json.loads(result.stdout)
        return data[0]["results"]
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"❌ レスポンス解析失敗: {e}", file=sys.stderr)
        print(result.stdout[:500], file=sys.stderr)
        sys.exit(1)


def escape_like(s):
    """LIKE用エスケープ（基本的なケースのみ）"""
    return s.replace("'", "''").replace("%", r"\%").replace("_", r"\_")


def build_query(args):
    """args から WHERE 句を組み立てる"""
    where = []
    if args.pref:
        where.append(f"prefecture = '{args.pref.replace(chr(39), chr(39)*2)}'")
    if args.city:
        where.append(f"work_location LIKE '%{escape_like(args.city)}%'")
    if args.emp:
        # 「常勤」「パート」「派遣」など部分一致
        where.append(f"emp_type LIKE '%{escape_like(args.emp)}%'")
    if args.salary_min:
        # salary_min は月給ベースで投入されている前提
        where.append(f"salary_min >= {args.salary_min}")
    if args.salary_max:
        where.append(f"salary_max <= {args.salary_max}")
    if args.rank:
        ranks = "','".join(args.rank)
        where.append(f"rank IN ('{ranks}')")
    if args.keyword:
        kw = escape_like(args.keyword)
        where.append(
            f"(employer LIKE '%{kw}%' OR title LIKE '%{kw}%' "
            f"OR description LIKE '%{kw}%' OR work_location LIKE '%{kw}%')"
        )
    if args.kjno:
        where.append(f"kjno = '{args.kjno.replace(chr(39), chr(39)*2)}'")
    if args.exclude_keyword:
        kw = escape_like(args.exclude_keyword)
        where.append(
            f"NOT (employer LIKE '%{kw}%' OR title LIKE '%{kw}%' "
            f"OR description LIKE '%{kw}%')"
        )
    if args.holidays_min:
        where.append(f"holidays >= {args.holidays_min}")
    where_clause = "WHERE " + " AND ".join(where) if where else ""

    order = "ORDER BY score DESC, salary_max DESC"
    limit = f"LIMIT {args.limit}"
    select = ("SELECT kjno, prefecture, area, work_location, employer, title, "
              "rank, score, emp_type, salary_form, salary_display, "
              "holidays, station_text, first_seen_at "
              "FROM jobs ")
    return f"{select}{where_clause} {order} {limit};"


def show_stats():
    """全体統計"""
    print("📊 D1 jobs テーブル統計\n")

    # 総件数
    r = d1_query("SELECT COUNT(*) AS cnt, COUNT(DISTINCT prefecture) AS pref_cnt FROM jobs;")
    if r:
        print(f"総件数: {r[0]['cnt']:,}件 / 都道府県数: {r[0]['pref_cnt']}\n")

    # 都道府県別
    print("【都道府県別件数】")
    r = d1_query("SELECT prefecture, COUNT(*) AS cnt FROM jobs GROUP BY prefecture ORDER BY cnt DESC LIMIT 50;")
    for row in r:
        p = row.get("prefecture") or "(空)"
        print(f"  {p:8s} {row['cnt']:5d}件")

    # ランク別
    print("\n【ランク別件数】")
    r = d1_query("SELECT rank, COUNT(*) AS cnt FROM jobs GROUP BY rank ORDER BY rank;")
    for row in r:
        rk = row.get("rank") or "(空)"
        print(f"  {rk}: {row['cnt']:5d}件")

    # 雇用形態別
    print("\n【雇用形態別件数 TOP10】")
    r = d1_query("SELECT emp_type, COUNT(*) AS cnt FROM jobs GROUP BY emp_type ORDER BY cnt DESC LIMIT 10;")
    for row in r:
        et = row.get("emp_type") or "(空)"
        print(f"  {et:30s} {row['cnt']:5d}件")


def show_detail(kjno):
    """1件詳細表示"""
    sql = (f"SELECT * FROM jobs WHERE kjno = '{kjno.replace(chr(39), chr(39)*2)}';")
    r = d1_query(sql)
    if not r:
        print(f"❌ kjno={kjno} の求人が見つかりません")
        return
    job = r[0]
    print(f"\n{'='*70}")
    print(f"求人番号: {job.get('kjno')}")
    print(f"事業所:   {job.get('employer')}")
    print(f"職種:     {job.get('title')}")
    print(f"勤務地:   {job.get('work_location')}")
    print(f"駅:       {job.get('station_text','')}")
    print(f"雇用形態: {job.get('emp_type')}")
    print(f"給与:     {job.get('salary_display','')} ({job.get('salary_form','')})")
    print(f"賞与:     {job.get('bonus_text','')}")
    print(f"年休:     {job.get('holidays')}日")
    print(f"勤務時間: {job.get('shift1','')} / {job.get('shift2','')}")
    print(f"ランク:   {job.get('rank')} (score={job.get('score')})")
    print(f"  内訳: 給与{job.get('score_sal')} 休{job.get('score_hol')} "
          f"賞{job.get('score_bon')} 雇{job.get('score_emp')} "
          f"福{job.get('score_wel')} 立地{job.get('score_loc')}")
    print(f"\n【仕事内容】")
    desc = job.get('description') or ''
    print(desc[:500] + ('...' if len(desc) > 500 else ''))
    print(f"\n【福利厚生】")
    print(job.get('welfare', ''))
    print(f"\n初出: {job.get('first_seen_at')} / 同期: {job.get('synced_at')}")
    print(f"{'='*70}\n")


def truncate(s, n):
    """日本語幅2バイト換算で n文字以内に切り詰め"""
    if not s:
        return ""
    s = str(s)
    out = ""
    width = 0
    for ch in s:
        w = 2 if ord(ch) > 0x7F else 1
        if width + w > n:
            out += "…"
            break
        out += ch
        width += w
    return out


def render_table(rows):
    """rowsをテーブル風に表示"""
    if not rows:
        print("(0件)")
        return
    print(f"\n{len(rows)}件\n")
    print(f"{'番号':14} {'県':6} {'勤務地':12} {'事業所':30} {'職種':25} {'雇用':6} {'ランク':4} {'給与':6} {'駅':12}")
    print("-" * 140)
    for r in rows:
        kjno = (r.get("kjno") or "")[:13]
        pref = truncate(r.get("prefecture", ""), 6)
        loc = truncate(r.get("work_location") or r.get("area", ""), 12)
        emp = truncate(r.get("employer", ""), 30)
        title = truncate(r.get("title", ""), 25)
        et = truncate(r.get("emp_type", ""), 6)
        rk = (r.get("rank") or "?")[:1]
        sal_form = (r.get("salary_form") or "")[:2]
        st = truncate(r.get("station_text", ""), 12)
        print(f"{kjno:13} {pref:<6} {loc:<12} {emp:<30} {title:<25} {et:<6} {rk:<2} {sal_form:<2} {st:<12}")


def main():
    p = argparse.ArgumentParser(description="D1 jobs テーブル検索CLI")
    p.add_argument("--pref", help="都道府県（完全一致、例: 神奈川県）")
    p.add_argument("--city", help="市区町村（部分一致、例: 横浜市）")
    p.add_argument("--emp", help="雇用形態（部分一致、例: 常勤/パート）")
    p.add_argument("--rank", nargs="+", choices=["S", "A", "B", "C", "D"],
                   help="ランクフィルタ（複数指定可、例: --rank S A）")
    p.add_argument("--salary-min", type=int, help="給与下限（円）")
    p.add_argument("--salary-max", type=int, help="給与上限（円）")
    p.add_argument("--holidays-min", type=int, help="年間休日下限（日）")
    p.add_argument("--keyword", help="事業所名/職種/仕事内容/勤務地に部分一致")
    p.add_argument("--exclude-keyword", help="除外キーワード")
    p.add_argument("--kjno", help="求人番号で1件検索")
    p.add_argument("--limit", type=int, default=20, help="最大表示件数（デフォ20）")
    p.add_argument("--json", action="store_true", help="JSON出力")
    p.add_argument("--detail", action="store_true", help="詳細表示（kjno指定時のみ）")
    p.add_argument("--stats", action="store_true", help="全体統計のみ表示")
    args = p.parse_args()

    if args.stats:
        show_stats()
        return

    if args.kjno and args.detail:
        show_detail(args.kjno)
        return

    sql = build_query(args)
    rows = d1_query(sql)

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        render_table(rows)


if __name__ == "__main__":
    main()
