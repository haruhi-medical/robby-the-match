#!/usr/bin/env python3
"""scripts/audit/fix_case_postback_data.py

580 ケース YAML の postback `data` 値を実機 worker.js の規約に合わせて一括修正。

理由: planner の case generator が worker の URLSearchParams 規約 (`il_area=value`)
を `il_area_value` という独自スネーク形式で出していた。worker側はマッチせず
"もう一度お選びください👇" のフォールバックを返すため F=0 が 492件と大量発生していた。

このスクリプトは **冪等** で、テキスト置換のみ。AICA等の意味的な修正は別途。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# data: "OLD"  →  data: "NEW"
REPLACEMENTS = {
    # il_area: 神奈川県内
    "il_area_yokohama": "il_area=yokohama_kawasaki",
    "il_area_kawasaki": "il_area=yokohama_kawasaki",
    "il_area_sagamihara": "il_area=sagamihara_kenoh",
    "il_area_yokosuka": "il_area=yokosuka_miura",
    "il_area_shonan": "il_area=shonan_kamakura",
    "il_area_odawara": "il_area=odawara_kensei",

    # 県外: 神奈川以外を選ぶケース → il_pref=<pref> 経由
    # (run flow: rm=start → il_area picker → "東京" など → il_pref=tokyo)
    "il_area_tama": "il_pref=tokyo",
    "il_area_23ku_east": "il_pref=tokyo",
    "il_area_23ku_west": "il_pref=tokyo",
    "il_area_osaka": "il_pref=other",
    "il_area_chiba_chuo": "il_pref=chiba",
    "il_area_kashiwa": "il_pref=chiba",
    "il_area_funabashi": "il_pref=chiba",
    "il_area_kawagoe": "il_pref=saitama",
    "il_area_saitama_chuo": "il_pref=saitama",
    "il_area_omiya": "il_pref=saitama",

    # il_pref: 県跨ぎ
    "il_pref_kanagawa": "il_pref=kanagawa",
    "il_pref_tokyo": "il_pref=tokyo",
    "il_pref_chiba": "il_pref=chiba",
    "il_pref_saitama": "il_pref=saitama",

    # 働き方: il_workstyle 画面の選択肢
    "worktype=nikkin": "il_ws=day",
    "worktype=nikoutai": "il_ws=twoshift",
    "worktype=yakin": "il_ws=twoshift",
    "worktype=yakin_senju": "il_ws=night",
    # 派遣 / 業務委託 / freelance はworker 側に該当無し → part(パート)に丸める
    "worktype=haken": "il_ws=part",
    "worktype=weekly_1": "il_ws=part",
    "worktype=weekly_2": "il_ws=part",
    "worktype=freelance": "il_ws=part",

    # 施設タイプ
    "facility_type=clinic": "il_ft=clinic",
    "facility_type=acute": "il_ft=hospital_acute",
    "facility_type=visit_nursing": "il_ft=visiting",

    # 新着求人エリア通知 (newjobs_area_*=通知エリア指定)
    "newjobs_area_yokohama": "newjobs_area=yokohama_kawasaki",
    "newjobs_area_kawasaki": "newjobs_area=yokohama_kawasaki",
}


def fix_file(path: Path) -> int:
    """1ファイル内の data: "OLD" を data: "NEW" に置換し変更件数を返す。"""
    src = path.read_text(encoding="utf-8")
    new = src
    n_changes = 0
    for old, new_v in REPLACEMENTS.items():
        # data: "OLD" を data: "NEW" に。クォートは " のみ想定
        pattern = f'data: "{re.escape(old)}"'
        replacement = f'data: "{new_v}"'
        if pattern in new:
            count = new.count(pattern)
            new = new.replace(pattern, replacement)
            n_changes += count
    if new != src:
        path.write_text(new, encoding="utf-8")
    return n_changes


def main() -> int:
    cases_dir = Path(__file__).resolve().parent / "cases"
    if not cases_dir.exists():
        print(f"cases dir not found: {cases_dir}", file=sys.stderr)
        return 1

    yaml_files = sorted(cases_dir.rglob("*.yaml"))
    total_changes = 0
    files_changed = 0
    for p in yaml_files:
        n = fix_file(p)
        if n > 0:
            files_changed += 1
            total_changes += n
            print(f"  {p.relative_to(cases_dir)}: {n} change(s)")

    print()
    print(f"Total: {total_changes} replacements in {files_changed}/{len(yaml_files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
