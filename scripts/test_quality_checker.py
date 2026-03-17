#!/usr/bin/env python3
"""
test_quality_checker.py — FactChecker / AppealChecker 統合テスト

quality_checker.py の FactChecker / AppealChecker の実APIに対するテスト。
実際のposting_queue.jsonデータを使ってリグレッションを防ぐ。

使い方:
  python3 scripts/test_quality_checker.py
  python3 scripts/test_quality_checker.py --verbose
  python3 scripts/test_quality_checker.py --suite fact       # FactCheckerのみ
  python3 scripts/test_quality_checker.py --suite appeal     # AppealCheckerのみ
  python3 scripts/test_quality_checker.py --suite integration # キューデータのみ
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

# ============================================================
# パス設定
# ============================================================

REPO_ROOT = Path(__file__).parent.parent
QUEUE_PATH = REPO_ROOT / "data" / "posting_queue.json"
SCRIPTS_DIR = REPO_ROOT / "scripts"

# sys.path にスクリプトディレクトリを追加（import用）
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from quality_checker import (  # type: ignore
    FactChecker,
    AppealChecker,
    FactIssue,
    FactCheckResult,
    AppealScore,
    AppealResult,
)


# ============================================================
# テスト結果クラス
# ============================================================

@dataclass
class TestResult:
    name: str
    passed: bool
    expected: str
    actual: str
    detail: str = ""


class TestRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []

    def run(self, name: str, expected_pass: bool, result_obj: Any, detail: str = "") -> TestResult:
        """テストを実行して結果を記録する"""
        if hasattr(result_obj, "passed"):
            actual_pass = result_obj.passed
        elif hasattr(result_obj, "pass_fail"):
            actual_pass = result_obj.pass_fail
        elif isinstance(result_obj, bool):
            actual_pass = result_obj
        else:
            actual_pass = bool(result_obj)

        ok = (actual_pass == expected_pass)
        tr = TestResult(
            name=name,
            passed=ok,
            expected="PASS" if expected_pass else "FAIL",
            actual="PASS" if actual_pass else "FAIL",
            detail=detail,
        )
        self.results.append(tr)

        symbol = "✓" if ok else "✗"
        status_label = "OK" if ok else "MISMATCH"
        print(f"  [{symbol}] {name} — {status_label}")
        if self.verbose or not ok:
            print(f"       expected={tr.expected}, actual={tr.actual}")
            if detail:
                for line in detail.splitlines():
                    print(f"       {line}")
        return tr

    def summary(self) -> None:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        print()
        print("=" * 60)
        print(f"  テスト結果: {passed}/{total} 通過  ({failed} 失敗)")
        print("=" * 60)
        if failed:
            print()
            print("  失敗したテスト:")
            for r in self.results:
                if not r.passed:
                    print(f"    - {r.name}")
                    print(f"      期待={r.expected}, 実際={r.actual}")

    def exit_code(self) -> int:
        return 0 if all(r.passed for r in self.results) else 1


# ============================================================
# ヘルパー
# ============================================================

def _fact_issues_detail(issues: List[FactIssue]) -> str:
    """FactIssue リストを読みやすい文字列に変換"""
    lines = []
    for i in issues:
        tag = "[ERROR]" if i.severity == "error" else "[WARN] "
        lines.append(f"{tag} [{i.field}] {i.claim} (expected: {i.expected}, source: {i.source})")
    return "\n".join(lines) if lines else "(no issues)"


def _fact_result_detail(result: FactCheckResult) -> str:
    """FactCheckResult を読みやすい文字列に変換"""
    lines = [f"passed={result.passed}, score={result.score}"]
    for i in result.issues:
        tag = "[ERROR]" if i.severity == "error" else "[WARN] "
        lines.append(f"  {tag} [{i.field}] {i.claim}")
    return "\n".join(lines)


def _appeal_score_detail(result: AppealScore) -> str:
    """AppealScore を読みやすい文字列に変換"""
    lines = [f"dimension={result.dimension}, score={result.score}/10"]
    for i in result.issues:
        lines.append(f"  [ISSUE] {i}")
    for s in result.suggestions:
        lines.append(f"  [SUG]   {s}")
    return "\n".join(lines)


def _appeal_result_detail(result: AppealResult) -> str:
    """AppealResult を読みやすい文字列に変換"""
    lines = [
        f"composite_score={result.composite_score}, pass_fail={result.pass_fail}",
        f"  hook_power={result.hook_power.score}",
        f"  body_structure={result.body_structure.score}",
        f"  cta_effectiveness={result.cta_effectiveness.score}",
        f"  brand_voice={result.brand_voice.score}",
        f"  target_resonance={result.target_resonance.score}",
    ]
    if result.blocking_issues:
        lines.append(f"  blocking: {result.blocking_issues}")
    return "\n".join(lines)


def _load_queue_posts(n: int = 3) -> List[dict]:
    """posting_queue.json から posted / ready を混ぜて n 件取得"""
    if not QUEUE_PATH.exists():
        print(f"  WARNING: {QUEUE_PATH} が見つかりません。キューテストをスキップします。")
        return []

    with open(QUEUE_PATH, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("posts") or data.get("items") or []
    else:
        return []

    posted = [p for p in items if p.get("status") == "posted"]
    ready = [p for p in items if p.get("status") == "ready"]

    result = []
    for pool in [posted, ready]:
        result.extend(pool[:2])
        if len(result) >= n:
            break

    return result[:n]


# ============================================================
# FactChecker テストスイート
#
# FactChecker API:
#   fc.check_salary_claims(text, field_name) -> List[FactIssue]
#   fc.check_statistics(text, field_name)    -> List[FactIssue]
#   fc.check_consistency(text, field_name)   -> List[FactIssue]
#   fc.fact_check_post(post_dict)            -> FactCheckResult
#
# Regex requires exact prefix format:
#   時給\s*(?:約\s*)?(\d...)  年収\s*(?:約\s*)?(\d+)万円
#   夜勤手当\s*(?:約\s*)?([\d,]+)\s*円
#
# Salary ranges (SALARY_RANGES):
#   正看護師パート時給: 1,800-2,500円  (±20%=error, ±10%=warning)
#   神奈川看護師年収:   500-550万円
#   夜勤手当(二交替):   10,000-15,000円
#   夜勤手当(三交替):   4,000-8,000円
# ============================================================

def run_fact_checker_tests(runner: TestRunner) -> None:
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  FactChecker テスト")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    fc = FactChecker()

    # ------------------------------------------------------------------
    # T-F01: 時給が低すぎる → check_salary_claims がエラーを返す
    # Range: 1,800-2,500  ±20% error → 1,200 is far below → error
    # Regex: 時給1,200円 (直接「時給」+数字+「円」の形式)
    # ------------------------------------------------------------------
    text_salary_too_low = "時給1,200円のパート看護師"
    issues = fc.check_salary_claims(text_salary_too_low, "test")
    has_error = any(i.severity == "error" for i in issues)
    runner.run(
        "T-F01: 時給1,200円 → check_salary_claims がエラーを返す",
        expected_pass=True,
        result_obj=has_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F02: 時給が妥当な範囲 → エラーなし
    # Range: 1,800-2,500  ±20% → 2,000 is within range
    # ------------------------------------------------------------------
    text_salary_ok = "時給2,000円のパート看護師"
    issues = fc.check_salary_claims(text_salary_ok, "test")
    no_error = not any(i.severity == "error" for i in issues)
    runner.run(
        "T-F02: 時給2,000円 → エラーなし",
        expected_pass=True,
        result_obj=no_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F03: 年収が低すぎる → check_salary_claims がエラーを返す
    # Range: 500-550万  ±20% error → 324万 is far below → error
    # Regex: 年収324万円
    # ------------------------------------------------------------------
    text_income_wrong = "年収324万円の看護師"
    issues = fc.check_salary_claims(text_income_wrong, "test")
    has_error = any(i.severity == "error" for i in issues)
    runner.run(
        "T-F03: 年収324万円 → check_salary_claims がエラーを返す",
        expected_pass=True,
        result_obj=has_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F04: 年収が妥当な範囲 → エラーなし
    # Range: 500-550万  ±10% warning → 500万 is exact match
    # ------------------------------------------------------------------
    text_income_ok = "年収約500万円の神奈川看護師"
    issues = fc.check_salary_claims(text_income_ok, "test")
    no_error = not any(i.severity == "error" for i in issues)
    runner.run(
        "T-F04: 年収500万円 → エラーなし",
        expected_pass=True,
        result_obj=no_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F05: 夜勤手当が低すぎる（二交替想定）→ エラーあり
    # Range(二交替): 10,000-15,000  ±20% error → 4,000 is far below
    # Regex: 夜勤手当4,000円
    # ------------------------------------------------------------------
    text_allowance_low = "夜勤手当4,000円しかもらえない"
    issues = fc.check_salary_claims(text_allowance_low, "test")
    has_error = any(i.severity == "error" for i in issues)
    runner.run(
        "T-F05: 夜勤手当4,000円（二交替）→ エラーあり",
        expected_pass=True,
        result_obj=has_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F06: 夜勤手当が妥当（三交替として文脈に明記）→ エラーなし
    # Range(三交替): 4,000-8,000  → 5,000 is within range
    # ------------------------------------------------------------------
    text_allowance_3shift = "三交替の準夜勤で夜勤手当5,000円"
    issues = fc.check_salary_claims(text_allowance_3shift, "test")
    no_error = not any(i.severity == "error" for i in issues)
    runner.run(
        "T-F06: 夜勤手当5,000円（三交替・文脈に明記）→ エラーなし",
        expected_pass=True,
        result_obj=no_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F07: fact_check_post でスライド間矛盾検出
    # 「高い」と「コンビニと同じ」が混在 → consistency check
    # ------------------------------------------------------------------
    post_contradictory = {
        "hook": "時給2,200円って高すぎ？",
        "slides": [
            "時給2,200円って高すぎ？",
            "実はコンビニバイトと同じ時給なんだ",
        ],
    }
    result = fc.fact_check_post(post_contradictory)
    has_any_issue = len(result.issues) > 0
    runner.run(
        "T-F07: スライド間の矛盾（高い/コンビニと同じ）→ issues が空でない",
        expected_pass=True,
        result_obj=has_any_issue,
        detail=_fact_result_detail(result),
    )

    # ------------------------------------------------------------------
    # T-F08: 妥当な数字でパス
    # 時給2,100円(range内) + 年収520万円(range内)
    # ------------------------------------------------------------------
    post_ok = {
        "hook": "時給2,100円の病棟看護師",
        "slides": [
            "時給2,100円の病棟看護師",
            "年収520万円が神奈川の相場なんだよね",
        ],
    }
    result = fc.fact_check_post(post_ok)
    runner.run(
        "T-F08: 時給2,100円 + 年収520万円 → fact_check_post がパス",
        expected_pass=True,
        result_obj=result,
        detail=_fact_result_detail(result),
    )

    # ------------------------------------------------------------------
    # T-F09: 数字なしのテキスト → エラーなしでパス
    # ------------------------------------------------------------------
    post_no_numbers = {
        "hook": "神奈川の看護師さん、転職を考えてる？",
        "slides": ["転職を考えてる看護師さんに伝えたいこと"],
    }
    result = fc.fact_check_post(post_no_numbers)
    runner.run(
        "T-F09: 数字なしテキスト → fact_check_post パス",
        expected_pass=True,
        result_obj=result,
        detail=_fact_result_detail(result),
    )

    # ------------------------------------------------------------------
    # T-F10: check_statistics — 有効な統計
    # ------------------------------------------------------------------
    text_stats_ok = "神奈川県の看護師は77,188人"
    issues = fc.check_statistics(text_stats_ok, "test")
    no_error = not any(i.severity == "error" for i in issues)
    runner.run(
        "T-F10: 看護師77,188人 → check_statistics エラーなし",
        expected_pass=True,
        result_obj=no_error,
        detail=_fact_issues_detail(issues),
    )

    # ------------------------------------------------------------------
    # T-F11: check_consistency — 矛盾テキスト
    # ------------------------------------------------------------------
    text_contradict = "時給2,200円は高すぎる。でもコンビニバイトと同じ時給なんだよ"
    issues = fc.check_consistency(text_contradict, "test")
    has_any = len(issues) > 0
    runner.run(
        "T-F11: 矛盾テキスト（高い+コンビニと同じ）→ check_consistency が issues を返す",
        expected_pass=True,
        result_obj=has_any,
        detail=_fact_issues_detail(issues),
    )


# ============================================================
# AppealChecker テストスイート
#
# AppealChecker API:
#   ac.check_hook_power(hook)              -> AppealScore (0-10)
#   ac.check_body_structure(slides)        -> AppealScore
#   ac.check_cta_effectiveness(cta, type)  -> AppealScore
#   ac.check_brand_voice(text)             -> AppealScore
#   ac.check_target_resonance(text)        -> AppealScore
#   ac.evaluate_post(post_dict)            -> AppealResult
#
# AppealScore has: dimension, label, score, issues, suggestions, detail
# AppealResult has: hook_power, body_structure, cta_effectiveness,
#                   brand_voice, target_resonance,
#                   composite_score, pass_fail, blocking_issues
# ============================================================

def run_appeal_checker_tests(runner: TestRunner) -> None:
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  AppealChecker テスト")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    ac = AppealChecker()

    # ------------------------------------------------------------------
    # T-A01: 良いフック（高スコア期待）
    # 25字以内、オープンループ（…）、現場語（夜勤、申し送り）、5W1H要素あり
    # ------------------------------------------------------------------
    good_hook = "夜勤明け、申し送りで泣いた理由…"
    r = ac.check_hook_power(good_hook)
    high_score = r.score >= 5
    runner.run(
        "T-A01: 良いフック → check_hook_power スコア5以上",
        expected_pass=True,
        result_obj=high_score,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A02: 悪いフック（低スコア期待）— 具体性ゼロ
    # ------------------------------------------------------------------
    bad_hook = "転職で人生変わります！"
    r = ac.check_hook_power(bad_hook)
    low_score = r.score <= 4
    runner.run(
        "T-A02: 悪いフック → check_hook_power スコア4以下",
        expected_pass=True,
        result_obj=low_score,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A03: ブランドボイス違反 — 敬語
    # ------------------------------------------------------------------
    formal_text = "転職をご検討ください。神奈川の看護師の皆様をサポートします。"
    r = ac.check_brand_voice(formal_text)
    has_voice_issues = len(r.issues) > 0
    runner.run(
        "T-A03: 敬語テキスト → check_brand_voice に issues あり",
        expected_pass=True,
        result_obj=has_voice_issues,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A04: 禁止ワード — 陳腐表現（AI臭い語）
    # ------------------------------------------------------------------
    banned_text = "さまざまな求人を包括的にご紹介"
    r = ac.check_brand_voice(banned_text)
    has_issues = len(r.issues) > 0
    runner.run(
        "T-A04: 禁止ワード「さまざまな」 → check_brand_voice に issues あり",
        expected_pass=True,
        result_obj=has_issues,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A05: ロビー口調 OK — タメ口テキスト
    # ------------------------------------------------------------------
    robby_text = "実はこういう仕組みなんだよね。ロビーが調べたから、間違いないよ。"
    r = ac.check_brand_voice(robby_text)
    decent_score = r.score >= 5
    runner.run(
        "T-A05: ロビー口調テキスト → check_brand_voice スコア5以上",
        expected_pass=True,
        result_obj=decent_score,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A06: フック文字数超過 → issues に記録される
    # ------------------------------------------------------------------
    long_hook = "神奈川で働く20代の看護師が転職前に必ず確認すべき3つのこと"
    r = ac.check_hook_power(long_hook)
    has_length_issue = any("文字" in i or "25" in i for i in r.issues)
    runner.run(
        "T-A06: フック文字数超過（25字超）→ check_hook_power の issues に文字数違反が記録",
        expected_pass=True,
        result_obj=has_length_issue,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A07: ターゲット共鳴チェック — 看護師ワードあり
    # ------------------------------------------------------------------
    nurse_text = "夜勤明けの看護師が手取りを見て驚いた話"
    r = ac.check_target_resonance(nurse_text)
    decent_resonance = r.score >= 4
    runner.run(
        "T-A07: 看護師ワード豊富なテキスト → check_target_resonance スコア4以上",
        expected_pass=True,
        result_obj=decent_resonance,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A08: ボディ構造チェック — 適切なスライド数
    # ------------------------------------------------------------------
    slides = [
        "夜勤明け、手取り見て泣いた…",
        "神奈川の看護師の平均年収は500万円",
        "でも手取りにすると350万くらいなんだよね",
        "ロビーが調べたら、夜勤手当の差が大きかった",
        "同じ病棟でも病院で年収50万違うことも",
        "気になったらプロフのリンクから相談してね",
    ]
    r = ac.check_body_structure(slides)
    decent_body = r.score >= 4
    runner.run(
        "T-A08: 6枚スライド構成 → check_body_structure スコア4以上",
        expected_pass=True,
        result_obj=decent_body,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A09: CTA効果チェック
    # ------------------------------------------------------------------
    cta_text = "気になったらプロフのリンクから相談してね"
    r = ac.check_cta_effectiveness(cta_text, "soft")
    runner.run(
        "T-A09: ソフトCTA → check_cta_effectiveness がクラッシュなく返る",
        expected_pass=True,
        result_obj=True,
        detail=_appeal_score_detail(r),
    )

    # ------------------------------------------------------------------
    # T-A10: evaluate_post — 全体評価がクラッシュなく返る
    # ------------------------------------------------------------------
    post_dict = {
        "hook": "夜勤明け、手取り見て泣いた…",
        "slides": [
            "夜勤明け、手取り見て泣いた…",
            "神奈川の看護師の平均年収は500万円",
            "でも手取りにすると350万くらいなんだよね",
            "ロビーが調べたら、夜勤手当の差が大きかった",
            "同じ病棟でも病院で年収50万違うことも",
            "気になったらプロフのリンクから相談してね",
        ],
    }
    result = ac.evaluate_post(post_dict)
    runner.run(
        "T-A10: evaluate_post → AppealResult が正常に返る",
        expected_pass=True,
        result_obj=True,
        detail=_appeal_result_detail(result),
    )

    # ------------------------------------------------------------------
    # T-A11: evaluate_post — composite_score が数値として返る
    # ------------------------------------------------------------------
    is_numeric = isinstance(result.composite_score, (int, float))
    runner.run(
        "T-A11: evaluate_post → composite_score が数値",
        expected_pass=True,
        result_obj=is_numeric,
        detail=f"composite_score={result.composite_score} (type={type(result.composite_score).__name__})",
    )


# ============================================================
# 統合テスト（実際のキューデータ）
# ============================================================

def run_integration_tests(runner: TestRunner) -> None:
    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  統合テスト — posting_queue.json の実データ")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    posts = _load_queue_posts(n=3)

    if not posts:
        print("  (投稿データなし — キューテストをスキップ)")
        return

    fc = FactChecker()
    ac = AppealChecker()

    for post in posts:
        pid = post.get("id", "?")
        content_id = post.get("content_id", "unknown")
        status = post.get("status", "?")

        label = f"Post#{pid} [{content_id}] status={status}"
        print(f"\n  --- {label} ---")

        # ---- FactChecker: クラッシュなく動作するか ----
        try:
            f_result = fc.fact_check_post(post)
            no_crash_fact = True
        except Exception as e:
            no_crash_fact = False
            f_result = None
            print(f"    FactChecker クラッシュ: {e}")

        runner.run(
            f"T-I-{pid}a: {content_id} FactChecker がクラッシュしない",
            expected_pass=True,
            result_obj=no_crash_fact,
            detail=_fact_result_detail(f_result) if f_result else "例外が発生",
        )

        # ---- AppealChecker: クラッシュなく動作するか ----
        try:
            a_result = ac.evaluate_post(post)
            no_crash_appeal = True
        except Exception as e:
            no_crash_appeal = False
            a_result = None
            print(f"    AppealChecker クラッシュ: {e}")

        runner.run(
            f"T-I-{pid}b: {content_id} AppealChecker がクラッシュしない",
            expected_pass=True,
            result_obj=no_crash_appeal,
            detail=_appeal_result_detail(a_result) if a_result else "例外が発生",
        )

        # ---- スコアのサマリーを表示 ----
        if f_result and a_result:
            errors = sum(1 for i in f_result.issues if i.severity == "error")
            warnings = sum(1 for i in f_result.issues if i.severity == "warning")
            print(f"    FactCheck: score={f_result.score}, errors={errors}, warnings={warnings}")
            print(f"    AppealCheck: composite={a_result.composite_score}, pass_fail={a_result.pass_fail}")


# ============================================================
# メイン
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="FactChecker / AppealChecker 統合テスト"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="全テストの詳細ログを表示"
    )
    parser.add_argument(
        "--suite", choices=["fact", "appeal", "integration", "all"],
        default="all",
        help="実行するテストスイートを選択（デフォルト: all）"
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  神奈川ナース転職 — 品質チェッカー 統合テスト")
    print(f"  queue={QUEUE_PATH.name}")
    print("=" * 60)

    runner = TestRunner(verbose=args.verbose)

    suite = args.suite
    if suite in ("fact", "all"):
        run_fact_checker_tests(runner)
    if suite in ("appeal", "all"):
        run_appeal_checker_tests(runner)
    if suite in ("integration", "all"):
        run_integration_tests(runner)

    runner.summary()
    sys.exit(runner.exit_code())


if __name__ == "__main__":
    main()
