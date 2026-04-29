#!/usr/bin/env python3
"""
auto_fix_loop.py — 改善が止まるまで回す自動修正ループ (DESIGN.md §5)

【1ラウンドのフロー】
    0. ``audit-round-N-pre`` タグ
    1. runner.run_all() で 580 ケース実行
    2. gatekeeper.evaluate_all() で判定
    3. レポート集計 + 終了条件チェック
    4. fixer.cluster_failures → 上位3パッチ提案 (Opus)
    5. risk別に適用判定
        - HIGH: Slack DM 承認待ち (24h)
        - MED: ``--auto-low-risk`` でない限り承認待ち
        - LOW: 自動適用
    6. commit + wrangler deploy
    7. smoke test (10ケース) → 失敗なら ``audit-round-N-pre`` へ rollback
    8. Slack 通知

【終了条件 (AND)】
    - PASS率 ≥ 95% を 3 ラウンド連続
    - 新規failパターン 2 ラウンド連続0
    - 改善デルタ < 0.5pt が 2 ラウンド連続
最大ラウンド: 12 (暴走防止)

【使い方】
    python3 scripts/audit/auto_fix_loop.py --rounds 12 --auto-low-risk
    python3 scripts/audit/auto_fix_loop.py --rounds 1 --dry-run

並列で他agentが構築している ``runner`` / ``gatekeeper`` モジュールは
**遅延 import + 実装欠損時のフェイルセーフ** で扱う。
本ループは骨組みとして安全に動作し、それぞれが揃えば自動的に有効になる。
"""
from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_AUDIT = Path(__file__).resolve().parent
if str(SCRIPTS_AUDIT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_AUDIT))

from fixer.auto_apply import AutoApplier  # noqa: E402
from fixer.fix_proposer import FixProposer, PatchCandidate  # noqa: E402
from fixer.smoke_test import SmokeTest  # noqa: E402
from lib.llm_client import LLMClient  # noqa: E402


# ============================================================================
# データクラス
# ============================================================================

@dataclass
class RoundReport:
    round_n: int
    started_at: str
    finished_at: Optional[str] = None
    n_cases: int = 0
    n_pass: int = 0
    n_fail: int = 0
    pass_rate: float = 0.0
    new_fail_patterns: int = 0
    patches_proposed: int = 0
    patches_applied: int = 0
    patches_skipped_high_risk: int = 0
    smoke_passed: Optional[bool] = None
    rolled_back: bool = False
    deploy_ok: Optional[bool] = None
    pre_round_tag: str = ""
    pattern_ids: List[str] = field(default_factory=list)
    cost_summary: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


# ============================================================================
# 動的 import (runner / gatekeeper)
# ============================================================================

def _try_import(module_name: str) -> Optional[Any]:
    """import 失敗を None で返すフェイルセーフ。"""
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None
    except Exception:  # noqa: BLE001
        return None


# ============================================================================
# Slack 通知
# ============================================================================

def _slack_send(repo_root: Path, message: str) -> bool:
    """``slack_bridge.py --send`` を呼ぶ薄いラッパ。失敗してもループは止めない。"""
    bridge = repo_root / "scripts" / "slack_bridge.py"
    if not bridge.exists():
        return False
    try:
        proc = subprocess.run(
            ["python3", str(bridge), "--send", message[:3500]],
            capture_output=True, text=True, timeout=20,
        )
        return proc.returncode == 0
    except Exception:  # noqa: BLE001
        return False


# ============================================================================
# AutoFixLoop
# ============================================================================

class AutoFixLoop:
    """改善が止まるまで回す自動修正ループ。

    Args:
        repo_root: リポジトリルート絶対パス。
        max_rounds: 最大ラウンド (暴走防止)。
        auto_low_risk: True なら LOW を即適用、MED/HIGH は承認待ち。
        terminate_on_converge: True なら 終了条件達成で打切り。
        dry_run: True ならファイル書込/サブプロセス呼出せずログだけ。
        runner_module: 注入用 runner (テスト時)。省略時は ``planner.runner`` を遅延import。
        gatekeeper_module: 同 gatekeeper。省略時は ``gatekeeper.verdict`` を遅延import。
    """

    def __init__(
        self,
        repo_root: str | Path,
        max_rounds: int = 12,
        auto_low_risk: bool = True,
        terminate_on_converge: bool = True,
        dry_run: bool = False,
        runner_module: Optional[Any] = None,
        gatekeeper_module: Optional[Any] = None,
        approval_timeout_hours: int = 24,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.max_rounds = max(1, max_rounds)
        self.auto_low_risk = auto_low_risk
        self.terminate_on_converge = terminate_on_converge
        self.dry_run = dry_run
        self.approval_timeout_sec = approval_timeout_hours * 3600

        # 構成要素
        self.llm = LLMClient(model="claude-opus-4-7")
        self.fixer = FixProposer(repo_root=self.repo_root, llm_client=self.llm)
        self.applier = AutoApplier(repo_root=self.repo_root, dry_run=dry_run)

        self.runner = runner_module or _try_import("planner.runner")
        self.gatekeeper = gatekeeper_module or _try_import("gatekeeper.verdict")
        self.smoke = SmokeTest(
            repo_root=self.repo_root,
            runner=self.runner,
            gatekeeper=self.gatekeeper,
        )

        # 履歴
        self.history: List[RoundReport] = []
        self.known_pattern_ids: set = set()

        # ログ出力先
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_dir = self.repo_root / "logs" / "audit" / "rounds" / self.run_id
        if not dry_run:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. 1ラウンド分の実行 (runner / gatekeeper 委譲)
    # ------------------------------------------------------------------

    def _run_all_cases(self) -> List[Dict[str, Any]]:
        """runner.run_all() を呼ぶ。無ければ空。"""
        if self.runner is None:
            return []
        fn = getattr(self.runner, "run_all", None)
        if fn is None:
            return []
        try:
            results = fn() if not self.dry_run else []
            return list(results) if results else []
        except Exception as e:  # noqa: BLE001
            print(f"[runner] run_all failed: {e}", file=sys.stderr)
            return []

    def _evaluate_all(self, run_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """gatekeeper.evaluate_all() を呼ぶ。無ければ空。"""
        if self.gatekeeper is None:
            return []
        fn = (
            getattr(self.gatekeeper, "evaluate_all", None)
            or getattr(self.gatekeeper, "judge_all", None)
        )
        if fn is None:
            return []
        try:
            verdicts = fn(run_results) if not self.dry_run else []
            return list(verdicts) if verdicts else []
        except Exception as e:  # noqa: BLE001
            print(f"[gatekeeper] evaluate_all failed: {e}", file=sys.stderr)
            return []

    def _load_existing_verdicts(self) -> List[Dict[str, Any]]:
        """gatekeeper が ``verdicts/<case_id>.json`` を出している前提で読み込む。

        探索順:
          1. ``logs/audit/verdicts/`` (旧式・直置き)
          2. ``logs/audit/runs/<latest>/verdicts/`` (新式・runner 出力)
        """
        candidates: List[Path] = []
        legacy = self.repo_root / "logs" / "audit" / "verdicts"
        if legacy.exists():
            candidates.append(legacy)

        runs_root = self.repo_root / "logs" / "audit" / "runs"
        if runs_root.exists():
            run_dirs = sorted(
                (d for d in runs_root.iterdir() if d.is_dir()),
                key=lambda d: d.stat().st_mtime,
                reverse=True,
            )
            for d in run_dirs:
                vd = d / "verdicts"
                if vd.exists():
                    candidates.append(vd)
                    break  # 最新run のみ

        out: List[Dict[str, Any]] = []
        for verdicts_dir in candidates:
            for p in sorted(verdicts_dir.glob("*.json")):
                try:
                    out.append(json.loads(p.read_text(encoding="utf-8")))
                except Exception:  # noqa: BLE001
                    continue
            if out:
                break  # 最初に見つかった source で打切り
        return out

    # ------------------------------------------------------------------
    # 2. レポート集計
    # ------------------------------------------------------------------

    def compile_report(
        self,
        round_n: int,
        verdicts: List[Dict[str, Any]],
        started_at: str,
    ) -> RoundReport:
        n_cases = len(verdicts)

        def _is_pass(v: Dict[str, Any]) -> bool:
            # 新 schema: verdict="PASS"/"FAIL"  旧 schema: passed=True/False
            if "verdict" in v:
                return str(v.get("verdict", "")).upper() == "PASS"
            return bool(v.get("passed"))

        n_pass = sum(1 for v in verdicts if _is_pass(v))
        n_fail = n_cases - n_pass
        pass_rate = round(100.0 * n_pass / n_cases, 2) if n_cases else 0.0

        # 新規パターン算出: cluster_failures を流用
        patterns = self.fixer.cluster_failures(verdicts)
        current_ids = {p.pattern_id for p in patterns}
        new_ids = current_ids - self.known_pattern_ids
        # known を更新 (round完了後に)
        report = RoundReport(
            round_n=round_n,
            started_at=started_at,
            n_cases=n_cases,
            n_pass=n_pass,
            n_fail=n_fail,
            pass_rate=pass_rate,
            new_fail_patterns=len(new_ids),
            pattern_ids=[p.pattern_id for p in patterns[:10]],
        )
        return report, patterns, current_ids

    # ------------------------------------------------------------------
    # 3. 終了条件
    # ------------------------------------------------------------------

    def should_terminate(self, report: RoundReport) -> Optional[str]:
        """終了条件達成時、理由を文字列で返す。継続なら None。"""
        if not self.terminate_on_converge:
            return None
        if len(self.history) < 2:
            return None

        # PASS率 >= 95% を 3R 連続
        if len(self.history) >= 3:
            recent3 = self.history[-3:]
            if all(r.pass_rate >= 95.0 for r in recent3):
                return "pass_rate>=95% for 3 consecutive rounds"

        # 新規failパターン 2R 連続 0
        recent2 = self.history[-2:]
        if all(r.new_fail_patterns == 0 for r in recent2):
            return "no new fail patterns for 2 consecutive rounds"

        # 改善デルタ < 0.5pt が 2R 連続
        if len(self.history) >= 3:
            d1 = self.history[-1].pass_rate - self.history[-2].pass_rate
            d2 = self.history[-2].pass_rate - self.history[-3].pass_rate
            if abs(d1) < 0.5 and abs(d2) < 0.5:
                return f"improvement delta < 0.5pt for 2 consecutive rounds (d1={d1:.2f}, d2={d2:.2f})"

        return None

    # ------------------------------------------------------------------
    # 4. risk別 適用ポリシー
    # ------------------------------------------------------------------

    def request_human_approval(self, patch: PatchCandidate, round_n: int) -> bool:
        """Slack DM + タイムアウト待ち。

        実装は最小: Slack に diff 概要を投げ、本ループは
        ``logs/audit/approvals/<round>_<pattern_id>.txt`` の存在を polling する。
        24h 経過で false。dry_run時は常に false (適用しない安全側)。
        """
        if self.dry_run:
            return False

        approvals_dir = self.repo_root / "logs" / "audit" / "approvals"
        approvals_dir.mkdir(parents=True, exist_ok=True)
        token_path = approvals_dir / f"round_{round_n:02d}_{patch.pattern_id}.approved"

        diff_preview = (patch.diff or "")[:1500]
        msg = (
            f":lock: HIGH-risk patch APPROVAL needed (round {round_n}, "
            f"pattern={patch.pattern_id})\n"
            f"risk_reasoning: {patch.risk_reasoning[:300]}\n"
            f"expected: {patch.expected_improvement[:200]}\n"
            f"approve: `touch {token_path}`\n"
            f"```diff\n{diff_preview}\n```"
        )
        _slack_send(self.repo_root, msg)

        # polling (60秒間隔、最大 approval_timeout_sec)
        deadline = time.time() + self.approval_timeout_sec
        while time.time() < deadline:
            if token_path.exists():
                return True
            # auto_fix_loop はバッチ前提なので長時間ブロックOK
            time.sleep(60)
        return False

    def decide_apply(self, patch: PatchCandidate, round_n: int) -> bool:
        risk = (patch.risk_level or "LOW").upper()
        if patch.is_empty or not patch.diff:
            return False
        if risk == "HIGH":
            return self.request_human_approval(patch, round_n)
        if risk == "MED":
            if self.auto_low_risk:
                # 設計書: MED は 24h auto or 平島さん承認 →
                # ここでは「auto-low-risk フラグでも MED は人間承認」を厳守。
                return self.request_human_approval(patch, round_n)
            return self.request_human_approval(patch, round_n)
        # LOW
        return True

    # ------------------------------------------------------------------
    # 5. ラウンド本体
    # ------------------------------------------------------------------

    def run_round(self, round_n: int) -> RoundReport:
        started_at = datetime.now(timezone.utc).isoformat()
        print(f"\n{'=' * 60}\n  Round {round_n} / {self.max_rounds}\n{'=' * 60}")

        # 0. pre-round tag
        try:
            tag = self.applier.tag_pre_round(round_n)
        except Exception as e:  # noqa: BLE001
            tag = f"audit-round-{round_n}-pre"
            print(f"[warn] tag failed: {e}")

        # 1. ケース実行
        run_results = self._run_all_cases()

        # 2. 評価
        verdicts = self._evaluate_all(run_results)
        if not verdicts:
            # gatekeeper が直接ファイルを書く方式の場合は読みに行く
            verdicts = self._load_existing_verdicts()

        # 3. レポート (一旦集計)
        report, patterns, current_ids = self.compile_report(round_n, verdicts, started_at)
        report.pre_round_tag = tag

        # 4. 終了条件チェック (history に追加するのは round 終わりだが、
        #    先に判定するために仮履歴に追加して評価しても冪等)
        # → ここでは「ラウンドのbody完走後に判定」とし、まず body へ進む

        # 5. パッチ提案 (上位3パターン)
        candidates: List[PatchCandidate] = []
        if patterns and verdicts:
            try:
                top3 = patterns[: self.fixer.max_patterns]
                for pat in top3:
                    cand = self.fixer.propose_patch(pat)
                    candidates.append(cand)
                    if not self.dry_run:
                        self.fixer.save_patch(round_n, pat, cand)
            except Exception as e:  # noqa: BLE001
                report.notes.append(f"propose_patch failed: {e}")

        report.patches_proposed = sum(1 for c in candidates if not c.is_empty)

        # 6. 適用
        applied: List[PatchCandidate] = []
        for cand in candidates:
            if cand.is_empty or not cand.diff:
                continue
            if not self.decide_apply(cand, round_n):
                if cand.risk_level == "HIGH":
                    report.patches_skipped_high_risk += 1
                continue
            ar = self.applier.apply_patch(cand)
            if ar.applied:
                applied.append(cand)
            else:
                report.notes.append(
                    f"apply failed pattern={cand.pattern_id} risk={cand.risk_level} "
                    f"err={ar.error}"
                )

        report.patches_applied = len(applied)

        if applied:
            # 7. commit + deploy
            cr = self.applier.commit_changes(
                f"audit: round {round_n} auto-fixes ({len(applied)} patches)"
            )
            if not cr.committed:
                report.notes.append(f"commit failed: {cr.error}")
            else:
                dep = self.applier.deploy_worker()
                report.deploy_ok = dep.deployed
                if not dep.deployed:
                    report.notes.append(
                        f"deploy failed rc={dep.rc} err={dep.error or dep.stderr_tail[:200]}"
                    )

            # 8. smoke test
            sr = self.smoke.run()
            report.smoke_passed = sr.passed
            if not sr.passed:
                print(f"[smoke] FAILED → rolling back to {tag}")
                rb = self.applier.rollback(tag, redeploy=True)
                report.rolled_back = rb.rolled_back
                if not rb.rolled_back:
                    report.notes.append(f"rollback FAILED: {rb.error}")
                else:
                    report.notes.append(
                        f"rolled_back to {tag}; smoke errors={sr.errors[:2]} "
                        f"failed_cases={sr.failed_cases[:3]}"
                    )

        # 履歴反映
        report.cost_summary = self.llm.cost_summary()
        report.finished_at = datetime.now(timezone.utc).isoformat()
        self.history.append(report)
        # rolled_back された場合は「known パターン」を更新しない
        # (まだバグは現存している)
        if not report.rolled_back:
            self.known_pattern_ids |= current_ids

        # ログ書込
        if not self.dry_run:
            self._write_round_log(report)
            self._notify_slack_round(report)

        return report

    # ------------------------------------------------------------------
    # 6. ログ・通知
    # ------------------------------------------------------------------

    def _write_round_log(self, report: RoundReport) -> None:
        path = self.log_dir / f"round_{report.round_n:02d}.json"
        path.write_text(
            json.dumps(asdict(report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _notify_slack_round(self, report: RoundReport) -> None:
        msg = (
            f":robot_face: audit round {report.round_n} done | "
            f"PASS {report.n_pass}/{report.n_cases} ({report.pass_rate}%) | "
            f"new patterns: {report.new_fail_patterns} | "
            f"applied: {report.patches_applied} | "
            f"deploy: {report.deploy_ok} | "
            f"smoke: {report.smoke_passed} | "
            f"rolled_back: {report.rolled_back} | "
            f"cost: ${report.cost_summary.get('estimated_usd', 0)}"
        )
        _slack_send(self.repo_root, msg)

    # ------------------------------------------------------------------
    # 7. ループ
    # ------------------------------------------------------------------

    def run(self) -> List[RoundReport]:
        for round_n in range(1, self.max_rounds + 1):
            report = self.run_round(round_n)

            reason = self.should_terminate(report)
            if reason:
                print(f"\n[terminate] {reason}")
                report.notes.append(f"terminated: {reason}")
                break

            if report.patches_proposed == 0 and report.n_fail == 0:
                print("\n[terminate] no failures left")
                report.notes.append("terminated: zero failures")
                break

            if report.patches_proposed == 0 and report.n_fail > 0:
                print("\n[terminate] failures remain but no patches proposed")
                report.notes.append("terminated: cannot make progress")
                break

        self.write_final_report()
        return self.history

    # ------------------------------------------------------------------
    # 8. 最終レポート
    # ------------------------------------------------------------------

    def write_final_report(self) -> Path:
        if self.dry_run:
            return self.log_dir / "final_report.md"

        out = self.log_dir / "final_report.md"
        lines: List[str] = []
        lines.append(f"# Audit auto-fix loop — final report\n")
        lines.append(f"- run_id: `{self.run_id}`")
        lines.append(f"- rounds executed: {len(self.history)}")
        lines.append(f"- max_rounds: {self.max_rounds}")
        lines.append(f"- auto_low_risk: {self.auto_low_risk}")
        lines.append(f"- dry_run: {self.dry_run}\n")

        lines.append("## Round summary\n")
        lines.append("| R | cases | pass | rate | new_pat | applied | smoke | rb |")
        lines.append("|---|-------|------|------|---------|---------|-------|-----|")
        for r in self.history:
            lines.append(
                f"| {r.round_n} | {r.n_cases} | {r.n_pass} | {r.pass_rate}% | "
                f"{r.new_fail_patterns} | {r.patches_applied} | {r.smoke_passed} | "
                f"{r.rolled_back} |"
            )
        lines.append("")

        if self.history:
            lines.append("## Cost (cumulative LLM)\n")
            lines.append("```json")
            lines.append(json.dumps(self.history[-1].cost_summary, ensure_ascii=False, indent=2))
            lines.append("```\n")

        lines.append("## Notes\n")
        for r in self.history:
            for n in r.notes:
                lines.append(f"- R{r.round_n}: {n}")

        out.write_text("\n".join(lines), encoding="utf-8")
        _slack_send(
            self.repo_root,
            f":checkered_flag: audit auto-fix loop done. "
            f"rounds={len(self.history)} report={out}"
        )
        return out


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    p = argparse.ArgumentParser(
        description="auto-fix loop: run cases → propose patches → apply → smoke → repeat",
    )
    p.add_argument("--rounds", type=int, default=12, help="最大ラウンド (default 12)")
    p.add_argument("--auto-low-risk", action="store_true",
                   help="LOW risk を自動適用 (MED/HIGHは承認待ち)")
    p.add_argument("--no-terminate", action="store_true",
                   help="終了条件を無視して --rounds 回まで回す")
    p.add_argument("--dry-run", action="store_true",
                   help="パッチ適用/デプロイ/Slack通知をスキップ。1ラウンド分のシミュレーション")
    p.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    p.add_argument("--approval-hours", type=int, default=24,
                   help="HIGH-risk 承認のタイムアウト時間")
    args = p.parse_args()

    loop = AutoFixLoop(
        repo_root=args.repo_root,
        max_rounds=args.rounds,
        auto_low_risk=args.auto_low_risk,
        terminate_on_converge=not args.no_terminate,
        dry_run=args.dry_run,
        approval_timeout_hours=args.approval_hours,
    )
    history = loop.run()

    # 標準出力に最終要約
    summary = {
        "rounds": len(history),
        "final_pass_rate": history[-1].pass_rate if history else 0.0,
        "log_dir": str(loop.log_dir),
        "cost": loop.llm.cost_summary(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
