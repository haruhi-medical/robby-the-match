#!/usr/bin/env python3
"""
ハローワーク求人JSON → worker.js EXTERNAL_JOBS 変換スクリプト

hellowork_fetch.py → hellowork_rank.py の後に実行。
data/hellowork_ranked.json → api/worker.js の EXTERNAL_JOBS を更新する。

EXTERNAL_JOBSはオブジェクト配列形式:
  { n: "事業所名", t: "職種", r: "S", s: 85, d: {sal:30, hol:20, bon:15, emp:15, wel:5, loc:0},
    sal: "月給35万円", sta: "横須賀中央", hol: "126日", bon: "3ヶ月", emp: "正社員", wel: "託児所" }

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
RANKED_FILE = PROJECT_ROOT / "data" / "hellowork_ranked.json"
INPUT_FILE = PROJECT_ROOT / "data" / "hellowork_nurse_jobs.json"
WORKER_JS = PROJECT_ROOT / "api" / "worker.js"

AREA_ORDER = [
    # 神奈川
    "横浜", "川崎", "相模原", "横須賀", "鎌倉", "藤沢",
    "茅ヶ崎", "平塚", "大磯", "秦野", "伊勢原", "厚木",
    "大和", "海老名", "小田原", "南足柄・開成",
    # 東京
    "23区", "多摩",
    # 埼玉
    "さいたま", "川口・戸田", "所沢・入間", "川越・東松山", "越谷・草加", "埼玉その他",
    # 千葉
    "千葉", "船橋・市川", "柏・松戸", "千葉その他",
]


def build_job_object(rj):
    """ランク済み求人データ → worker.js用オブジェクトを生成"""
    details = rj.get("details", {})

    # 給与テキスト整形
    sal = details.get("salary", "不明")

    # 駅名（短縮）
    sta = rj.get("work_station_text", "")
    if len(sta) > 25:
        sta = sta[:22] + "..."

    # 休日
    hol = details.get("holidays", "不明")

    # 賞与
    bon = details.get("bonus", "なし")

    # 雇用形態
    emp = details.get("emp_type", "")

    # 福利厚生（拡充）
    welfare_parts = []
    wel_text = details.get("welfare", "")
    if wel_text and wel_text != "特記なし":
        welfare_parts.append(wel_text)
    if rj.get("childcare"):
        welfare_parts.append("託児所あり")
    if rj.get("retirement"):
        welfare_parts.append("退職金あり")
    wel = "、".join(welfare_parts) if welfare_parts else ""

    # 仕事内容（150文字に拡大）
    desc = rj.get("job_description", "")
    if len(desc) > 150:
        desc = desc[:147] + "..."

    # 勤務地（work_locationが空ならwork_address/employer_addressからフォールバック）
    loc = rj.get("work_location", "")
    if not loc:
        loc = rj.get("work_address", "") or rj.get("employer_address", "")

    # 勤務時間
    shift = rj.get("shift1", "")
    if rj.get("shift2"):
        shift += " / " + rj.get("shift2", "")

    # 契約期間
    ctr = rj.get("contract_period", "") or rj.get("details", {}).get("contract_period", "")

    # 加入保険
    ins = rj.get("insurance", "") or rj.get("details", {}).get("insurance", "")

    # スコア内訳 (details内のスコアは再計算が必要 → ranked.jsonのscoreを使う)
    # hellowork_rank.pyのscore_job()の配点に基づいてdetailsから再構成
    # → ranked.jsonにはスコア合計のみ保存されているので、ここで内訳も出す
    # → 簡略化: detailsの値から逆算する
    # スコア内訳 (breakdown: sal/hol/bon/emp/wel/loc)
    bd = rj.get("breakdown", {})

    obj = {
        "n": rj.get("employer", "").strip(),
        "t": rj.get("job_title", "").strip(),
        "r": rj.get("rank", ""),
        "s": rj.get("score", 0),
        "d": {
            "sal": bd.get("sal", 0),
            "hol": bd.get("hol", 0),
            "bon": bd.get("bon", 0),
            "emp": bd.get("emp", 0),
            "wel": bd.get("wel", 0),
            "loc": bd.get("loc", 0),
        },
        "sal": sal,
        "sta": sta,
        "hol": hol,
        "bon": bon,
        "emp": emp,
        "wel": wel,
        "desc": desc,
        "loc": loc,
        "shift": shift,
        "ctr": ctr,
        "ins": ins,
    }
    return obj


def format_js_object(obj):
    """Pythonの辞書をJSオブジェクトリテラル文字列に変換"""
    def js_val(v):
        if isinstance(v, str):
            escaped = v.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'
        elif isinstance(v, (int, float)):
            return str(v)
        elif isinstance(v, dict):
            inner = ",".join(f"{k}:{js_val(v2)}" for k, v2 in v.items())
            return f"{{{inner}}}"
        return '""'

    parts = []
    for k, v in obj.items():
        parts.append(f'{k}:{js_val(v)}')
    return "{" + ", ".join(parts) + "}"


def main():
    parser = argparse.ArgumentParser(description="ハローワーク→EXTERNAL_JOBS変換")
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ")
    parser.add_argument("--json", action="store_true", help="JSON出力のみ")
    parser.add_argument("--max-per-area", type=int, default=8, help="エリアあたり最大件数")
    args = parser.parse_args()

    # ランクデータ読み込み
    if not RANKED_FILE.exists():
        print("❌ hellowork_ranked.json が見つかりません。先に hellowork_rank.py を実行してください。")
        sys.exit(1)

    with open(RANKED_FILE, encoding="utf-8") as f:
        ranked_data = json.load(f)

    ranked_jobs = ranked_data.get("jobs", [])
    print(f"📦 入力: {len(ranked_jobs)}件のランク済み看護師求人")

    # エリア別に分類
    area_jobs = {}  # area → [job_objects]
    unclassified = 0
    for rj in ranked_jobs:
        area = rj.get("area")
        if not area:
            unclassified += 1
            continue
        if area not in area_jobs:
            area_jobs[area] = []
        area_jobs[area].append(rj)

    # エリアごとにスコア順ソート → 事業所重複除去 → 上位N件
    area_output = {}  # area → [job_object_dicts]
    for area in area_jobs:
        sorted_jobs = sorted(area_jobs[area], key=lambda j: -j.get("score", 0))
        seen = set()
        selected = []
        for rj in sorted_jobs:
            employer = rj.get("employer", "").strip()
            if employer in seen:
                continue
            seen.add(employer)
            obj = build_job_object(rj)
            selected.append(obj)
            if len(selected) >= args.max_per_area:
                break
        area_output[area] = selected

    # サマリー表示
    print(f"📊 エリア別:")
    total = 0
    for area in sorted(area_output.keys(), key=lambda a: -len(area_output[a])):
        count = len(area_output[area])
        total += count
        ranks = {}
        for j in area_output[area]:
            r = j["r"]
            ranks[r] = ranks.get(r, 0) + 1
        rank_str = " ".join(f"{r}:{c}" for r, c in sorted(ranks.items()))
        print(f"   {area}: {count}件 ({rank_str})")
    print(f"   分類不能: {unclassified}件")
    print(f"   合計: {total}件")

    if args.json:
        print(json.dumps(area_output, ensure_ascii=False, indent=2))
        return

    if args.dry_run:
        print("\n--- プレビュー（先頭3件/エリア）---")
        for area in AREA_ORDER:
            if area not in area_output:
                continue
            print(f"\n  【{area}】")
            for j in area_output[area][:3]:
                print(f"    [{j['r']}ランク {j['s']}点] {j['n']}")
                print(f"      {j['t']} | {j['sal']} | 賞与{j['bon']} | 休日{j['hol']} | {j['emp']}")
                if j['wel']:
                    print(f"      福利: {j['wel']}")
        return

    # worker.js の EXTERNAL_JOBS を更新
    if not WORKER_JS.exists():
        print(f"❌ {WORKER_JS} が見つかりません")
        sys.exit(1)

    worker_content = WORKER_JS.read_text(encoding="utf-8")

    # EXTERNAL_JOBS ブロックを検索して置換
    pattern = r'// ---------- 外部公開求人データ.*?\n.*?const EXTERNAL_JOBS = \{.*?\n\};\n'
    match = re.search(pattern, worker_content, re.DOTALL)
    if not match:
        print("❌ EXTERNAL_JOBS ブロックが見つかりません")
        sys.exit(1)

    # 新しい EXTERNAL_JOBS を生成（オブジェクト配列形式）
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f'// ---------- 外部公開求人データ（ハローワークAPI {today}更新） ----------']
    lines.append('// 各求人: n=事業所名, t=職種, r=ランク(S/A/B/C/D), s=スコア(100点満点),')
    lines.append('//   sal=給与, sta=最寄り駅, hol=年間休日, bon=賞与, emp=雇用形態, wel=福利厚生,')
    lines.append('//   desc=仕事内容(80字), loc=勤務地, shift=勤務時間, ctr=契約期間, ins=加入保険')
    lines.append('// スコア配点: 年収30点 + 休日20点 + 賞与15点 + 雇用安定15点 + 福利10点 + 立地10点')
    lines.append('const EXTERNAL_JOBS = {')
    lines.append('  nurse: {')

    for area in AREA_ORDER:
        if area not in area_output or not area_output[area]:
            continue
        lines.append(f'    "{area}": [')
        for obj in area_output[area]:
            js_str = format_js_object(obj)
            lines.append(f'      {js_str},')
        lines.append('    ],')

    lines.append('  },')

    # PT求人は既存のまま維持
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
    print(f"   nurse: {total}件 ({len(area_output)}エリア)")


if __name__ == "__main__":
    main()
