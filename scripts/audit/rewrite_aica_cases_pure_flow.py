#!/usr/bin/env python3
"""scripts/audit/rewrite_aica_cases_pure_flow.py

aica_4turn / aica_condition のテストケースを「純AICAフロー」に書き換える。

【背景】
case generator は `rm=start` postback で AICA を起動する想定で設計したが、
実 worker は `rm=start` で **IL flow (il_area→…→il_urgency)** を起動する。
AICA は **follow event** でしか起動しない (preloadedCtx 無し時)。
よって AICA系 115 ケースは IL flow に落ちて、F=0 / E=1 (事務的応答) と評価され
「AICA 寄り添い品質」ではなく「IL flow 内で感情テキストを受けた時の品質」
を測ってしまっていた。

【修正方針】
- preconditions.follow_first: true / reset_kv: true は維持 (AICA 自動起動)
- 先頭の `rm=start` / `il_area=...` postback ステップを削除
- text ステップだけ残す (元1〜複数件)
- expect_phase / expect_keywords は維持

冪等。既に postback steps が無いケース (例: _aica_pure_001) は素通り。
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml


CASES_DIR = Path(__file__).resolve().parent / "cases"
TARGET_CATEGORIES = ("aica_4turn", "aica_condition")

# 削除対象 postback step. data 値で判定。
_POSTBACK_TRASH_DATA = {
    "rm=start",
}


def _is_il_area_postback(step: Dict[str, Any]) -> bool:
    """il_area=… / il_pref=… / il_subarea=… 系のIL flowへ誘導する postback か。"""
    if step.get("kind") != "postback":
        return False
    data = (step.get("data") or "")
    if not isinstance(data, str):
        return False
    return data.startswith(("il_area=", "il_pref=", "il_subarea=", "il_ft=", "il_ws=", "il_dept=", "il_urg="))


def _should_drop(step: Dict[str, Any]) -> bool:
    if step.get("kind") != "postback":
        return False
    data = step.get("data")
    if data in _POSTBACK_TRASH_DATA:
        return True
    if _is_il_area_postback(step):
        return True
    return False


def rewrite_file(path: Path) -> bool:
    """1ファイル書換。変更があれば True。"""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [skip] yaml parse error: {path.name}: {e}", file=sys.stderr)
        return False
    if not isinstance(data, dict):
        return False

    steps: List[Dict[str, Any]] = list(data.get("steps") or [])
    if not steps:
        return False

    # 先頭の rm=start / il_area= postback を **連続** している分だけ削除する
    # (途中の postback は意味ある場合がある—e.g. 緊急 postback の検証等)
    while steps and _should_drop(steps[0]):
        steps.pop(0)

    if steps == data.get("steps"):
        return False  # 変化なし

    if not steps:
        # 全削除されると text 0件のテストになるので、元の1件目を text 起こしする
        # 通常は起こりえない (元 case には必ず text があるため)
        print(f"  [warn] all steps dropped, leaving original: {path.name}", file=sys.stderr)
        return False

    data["steps"] = steps
    # preconditions の follow_first: true を確実に
    pre = data.get("preconditions") or {}
    pre.setdefault("follow_first", True)
    pre.setdefault("reset_kv", True)
    pre.setdefault("liff_session", None)
    data["preconditions"] = pre

    # metadata
    md = data.get("metadata") or {}
    md["rewritten_to_pure_aica_flow"] = "2026-04-29"
    data["metadata"] = md

    # YAML 保存。block style + utf-8 + sort_keys=False
    out = yaml.safe_dump(
        data,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )
    path.write_text(out, encoding="utf-8")
    return True


def main() -> int:
    if not CASES_DIR.exists():
        print(f"cases dir not found: {CASES_DIR}", file=sys.stderr)
        return 1

    targets: List[Path] = []
    for cat in TARGET_CATEGORIES:
        cat_dir = CASES_DIR / cat
        if not cat_dir.exists():
            continue
        targets.extend(sorted(cat_dir.glob("*.yaml")))

    n_changed = 0
    for p in targets:
        if rewrite_file(p):
            n_changed += 1
            print(f"  + {p.relative_to(CASES_DIR)}")

    print()
    print(f"Total: {n_changed}/{len(targets)} cases rewritten to pure-AICA flow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
