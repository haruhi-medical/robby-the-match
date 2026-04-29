#!/usr/bin/env python3
"""
summary.py — verdicts/<case_id>.json から集計レポートを生成

【出力】
    - summary.md            ... 全体PASS率/カテゴリ別/失敗パターンTop10/軸別平均
    - human_review.md       ... 人間目視抜き取り対象一覧（20%サンプリング）

【単独使用】
    python3 scripts/audit/gatekeeper/summary.py \\
        --verdicts-dir logs/audit/runs/2026-04-29_120000/verdicts/
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# 内部ヘルパ
# ============================================================================

def _load_verdicts(verdicts_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(verdicts_dir.glob("*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def _category_of(case_id: str) -> str:
    """``aica_career_016`` → ``aica`` / ``edge_005`` → ``edge`` の粗いカテゴリ抽出。"""
    if "_" not in case_id:
        return case_id
    head = case_id.split("_", 1)[0]
    # 既知prefixの正規化
    mapping = {
        "aica": "aica",
        "edge": "edge",
        "richmenu": "richmenu",
        "emergency": "emergency",
        "apply": "apply_intent",
    }
    return mapping.get(head, head)


_REASON_NORMALIZE_RE = re.compile(r"\s+")


def _normalize_reason(reason: str) -> str:
    """類似理由を集約しやすいよう正規化（数値 / 余白）。"""
    r = _REASON_NORMALIZE_RE.sub(" ", reason).strip()
    # 数字を <N> に置換し集約
    r = re.sub(r"\b\d+(\.\d+)?\b", "<N>", r)
    return r


# ============================================================================
# summary.md
# ============================================================================

def generate_summary(
    verdicts_dir: Path,
    run_dir: Optional[Path] = None,
) -> str:
    """全体集計 markdown を生成。

    Args:
        verdicts_dir: ``<case_id>.json`` が並ぶディレクトリ。
        run_dir: 親 run ディレクトリ（任意。タイトルに表示）。

    Returns:
        markdown 文字列。
    """
    verdicts = _load_verdicts(Path(verdicts_dir))
    total = len(verdicts)

    if total == 0:
        return "# Gatekeeper Summary\n\nNo verdicts found in `{}`.\n".format(verdicts_dir)

    n_pass = sum(1 for v in verdicts if v.get("verdict") == "PASS")
    n_fail = sum(1 for v in verdicts if v.get("verdict") == "FAIL")
    n_skip = sum(1 for v in verdicts if v.get("verdict") == "SKIP")
    pass_rate = n_pass / total

    # カテゴリ別
    by_cat: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"total": 0, "pass": 0, "fail": 0, "skip": 0}
    )
    for v in verdicts:
        cat = _category_of(v.get("case_id", ""))
        by_cat[cat]["total"] += 1
        by_cat[cat][v.get("verdict", "SKIP").lower()] += 1

    # 失敗パターンTop10
    reason_counter: Counter = Counter()
    for v in verdicts:
        if v.get("verdict") != "FAIL":
            continue
        for reason in v.get("blocking_reasons", []) or []:
            reason_counter[_normalize_reason(reason)] += 1

    # 軸別平均
    axes = ("F", "U", "E", "C", "L", "S", "K", "H")
    axis_totals: Dict[str, int] = {a: 0 for a in axes}
    axis_counts: Dict[str, int] = {a: 0 for a in axes}
    for v in verdicts:
        scores = v.get("scores", {}) or {}
        for a in axes:
            if a in scores:
                axis_totals[a] += int(scores[a])
                axis_counts[a] += 1
    axis_means = {
        a: (axis_totals[a] / axis_counts[a]) if axis_counts[a] else 0.0
        for a in axes
    }

    # 人間レビュー件数
    n_human = sum(1 for v in verdicts if v.get("human_review_flag"))

    # ----- markdown 組み立て -----
    lines: List[str] = []
    title = f"# Gatekeeper Summary"
    if run_dir:
        title += f" — `{Path(run_dir).name}`"
    lines.append(title)
    lines.append("")
    lines.append(f"- 評価件数: **{total}**")
    lines.append(
        f"- 合否: PASS **{n_pass}** / FAIL **{n_fail}** / SKIP **{n_skip}**  "
        f"(pass率 **{pass_rate*100:.1f}%**)"
    )
    lines.append(f"- 人間レビュー対象: **{n_human}** 件 ({n_human/total*100:.1f}%)")
    lines.append("")

    # 軸別平均
    lines.append("## 軸別平均スコア (各軸 1〜5)")
    lines.append("")
    lines.append("| 軸 | 名称 | 平均 | 必須閾値 |")
    lines.append("|----|------|------|---------|")
    axis_meta = {
        "F": ("機能正確性", "5/5"),
        "U": ("UX",         "≥4"),
        "E": ("寄り添い",   "≥4"),
        "C": ("整合性",     "5/5"),
        "L": ("レイテンシ", "≥4"),
        "S": ("セキュリティ", "5/5"),
        "K": ("コスト",     "警告"),
        "H": ("ハルシネーション", "5/5"),
    }
    for a in axes:
        name, thresh = axis_meta[a]
        mean = axis_means[a]
        warn = " ⚠️" if (
            (a in ("F", "C", "S", "H") and mean < 5.0)
            or (a in ("U", "E", "L") and mean < 4.0)
        ) else ""
        lines.append(f"| {a} | {name} | {mean:.2f}{warn} | {thresh} |")
    lines.append("")

    # カテゴリ別
    lines.append("## カテゴリ別")
    lines.append("")
    lines.append("| カテゴリ | total | PASS | FAIL | SKIP | pass率 |")
    lines.append("|---------|-------|------|------|------|--------|")
    for cat in sorted(by_cat.keys()):
        c = by_cat[cat]
        rate = c["pass"] / c["total"] if c["total"] else 0
        lines.append(
            f"| {cat} | {c['total']} | {c['pass']} | {c['fail']} | {c['skip']} | "
            f"{rate*100:.1f}% |"
        )
    lines.append("")

    # 失敗パターンTop10
    lines.append("## 失敗パターン Top 10")
    lines.append("")
    if not reason_counter:
        lines.append("（失敗なし or 全てSKIP）")
    else:
        lines.append("| # | 件数 | 理由（正規化済） |")
        lines.append("|---|------|------------------|")
        for i, (reason, cnt) in enumerate(reason_counter.most_common(10), 1):
            lines.append(f"| {i} | {cnt} | `{reason}` |")
    lines.append("")

    # 軸別 失敗件数（軸ごとに何件blockされたか）
    axis_block_counter: Counter = Counter()
    for v in verdicts:
        for reason in v.get("blocking_reasons", []) or []:
            # 先頭1文字が軸記号
            m = re.match(r"^([FUECLSKH])", reason.strip())
            if m:
                axis_block_counter[m.group(1)] += 1
    lines.append("## 軸別 ブロック件数")
    lines.append("")
    lines.append("| 軸 | ブロック件数 |")
    lines.append("|----|-------------|")
    for a in axes:
        lines.append(f"| {a} | {axis_block_counter.get(a, 0)} |")
    lines.append("")

    # 失敗ケース全件 (id only)
    fail_ids = [v.get("case_id", "?") for v in verdicts if v.get("verdict") == "FAIL"]
    if fail_ids:
        lines.append("## FAIL ケース ID 一覧")
        lines.append("")
        lines.append("```")
        for cid in fail_ids:
            lines.append(cid)
        lines.append("```")
        lines.append("")

    return "\n".join(lines) + "\n"


# ============================================================================
# human_review.md
# ============================================================================

def generate_human_review_list(verdicts_dir: Path) -> str:
    """20%抜き取り対象 + FAIL全件を人間目視レビュー対象として一覧化。"""
    verdicts = _load_verdicts(Path(verdicts_dir))
    if not verdicts:
        return "# Human Review List\n\nNo verdicts.\n"

    review_targets: List[Dict[str, Any]] = []
    for v in verdicts:
        is_sampled = bool(v.get("human_review_flag"))
        is_failed = v.get("verdict") == "FAIL"
        if is_sampled or is_failed:
            review_targets.append({
                "case_id": v.get("case_id", "?"),
                "verdict": v.get("verdict", "?"),
                "scores": v.get("scores", {}),
                "reason": v.get("blocking_reasons", []),
                "trigger": "sampled" if is_sampled and not is_failed else (
                    "failed" if is_failed and not is_sampled else "both"
                ),
            })

    lines: List[str] = []
    lines.append("# Human Review List")
    lines.append("")
    lines.append(f"- 対象件数: **{len(review_targets)}** / 全{len(verdicts)}件")
    lines.append("- trigger: `sampled`=抜き取り / `failed`=要分析 / `both`=両方")
    lines.append("")
    lines.append("| case_id | verdict | trigger | F | U | E | C | L | S | K | H | reason |")
    lines.append("|---------|---------|---------|---|---|---|---|---|---|---|---|--------|")
    for t in review_targets:
        s = t["scores"] or {}
        reason_short = "; ".join((t.get("reason") or [])[:2])[:80]
        lines.append(
            f"| `{t['case_id']}` | {t['verdict']} | {t['trigger']} | "
            f"{s.get('F','-')} | {s.get('U','-')} | {s.get('E','-')} | {s.get('C','-')} | "
            f"{s.get('L','-')} | {s.get('S','-')} | {s.get('K','-')} | {s.get('H','-')} | "
            f"{reason_short} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


# ============================================================================
# CLI
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="verdicts ディレクトリから summary.md を生成")
    p.add_argument("--verdicts-dir", required=True, help="verdicts/<case_id>.json の親")
    p.add_argument("--out", default=None, help="summary.md 出力先（既定: 親dir/summary.md）")
    p.add_argument(
        "--review-out", default=None, help="human_review.md 出力先（既定: 親dir/human_review.md）",
    )
    args = p.parse_args(argv)

    vdir = Path(args.verdicts_dir).expanduser().resolve()
    if not vdir.exists():
        print(f"verdicts dir not found: {vdir}")
        return 2
    parent = vdir.parent
    out_path = Path(args.out) if args.out else (parent / "summary.md")
    review_out = Path(args.review_out) if args.review_out else (parent / "human_review.md")

    summary_md = generate_summary(vdir, run_dir=parent)
    out_path.write_text(summary_md, encoding="utf-8")
    review_md = generate_human_review_list(vdir)
    review_out.write_text(review_md, encoding="utf-8")

    print(f"wrote: {out_path}")
    print(f"wrote: {review_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
