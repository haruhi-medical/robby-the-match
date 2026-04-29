#!/usr/bin/env python3
"""
smoke_test.py — パッチ適用後の最小限スモークテスト (10ケース)

設計書 §5 (DESIGN.md):
    - 10ケースで素早く検証 → 1件でも FAIL なら自動 rollback
    - 加えて critical paths (worker.js syntax / /api/health) を確認

【10ケースの内訳 (デフォルト)】
    - regression 固定枠: 3件 (過去発見バグの再発防止)
    - 各カテゴリから1件ずつ: 6件 (現在のカテゴリ数)
    - 過去成功率の高いケース: 残り (基本機能 sanity check)

regression 枠は ``logs/audit/regression_cases.txt`` に case_id を1行ずつ書く。
無ければ単に skip。

【依存】
    - runner / gatekeeper モジュールの呼出は **遅延 import + ベストエフォート**
      (並列開発中なので互いの実装が一時的に欠けていても import 失敗しない)
    - 呼出失敗時は ``SmokeResult.errors`` に詳細を残し False を返す
"""
from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

SCRIPTS_AUDIT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_AUDIT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_AUDIT))


# ============================================================================
# データクラス
# ============================================================================

@dataclass
class CriticalPathResult:
    syntax_ok: bool = False
    syntax_message: str = ""
    health_ok: bool = False
    health_message: str = ""
    health_url: str = ""

    def all_pass(self) -> bool:
        return self.syntax_ok and self.health_ok


@dataclass
class SmokeResult:
    passed: bool = False
    n_cases: int = 0
    n_pass: int = 0
    n_fail: int = 0
    failed_cases: List[str] = field(default_factory=list)
    selected_cases: List[str] = field(default_factory=list)
    critical: CriticalPathResult = field(default_factory=CriticalPathResult)
    errors: List[str] = field(default_factory=list)
    duration_sec: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["critical"] = asdict(self.critical)
        return d


# ============================================================================
# SmokeTest
# ============================================================================

DEFAULT_HEALTH_URL = "https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health"
DEFAULT_REGRESSION_FILE = Path("logs/audit/regression_cases.txt")
DEFAULT_CASES_DIR = Path("scripts/audit/cases")


class SmokeTest:
    """パッチ適用後の最小スモーク。

    Args:
        repo_root: リポジトリルート。
        runner: ``runner.run_one(case_path) -> dict`` を持つオブジェクト。省略可。
        gatekeeper: ``evaluate(run_result) -> dict`` を持つオブジェクト。省略可。
        n_cases: 実行するケース数 (デフォルト10)。
        health_url: ``/api/health`` のフルURL。
        cases_dir: ケースYAMLが置かれたディレクトリ。
        regression_file: regression case_id 一覧ファイル。
        seed: 選定の再現性を保つための乱数seed。
    """

    def __init__(
        self,
        repo_root: str | Path,
        runner: Any = None,
        gatekeeper: Any = None,
        n_cases: int = 10,
        health_url: str = DEFAULT_HEALTH_URL,
        cases_dir: Optional[str | Path] = None,
        regression_file: Optional[str | Path] = None,
        seed: int = 42,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runner = runner
        self.gatekeeper = gatekeeper
        self.n_cases = max(1, n_cases)
        self.health_url = health_url
        self.cases_dir = Path(cases_dir) if cases_dir else self.repo_root / DEFAULT_CASES_DIR
        self.regression_file = (
            Path(regression_file) if regression_file else self.repo_root / DEFAULT_REGRESSION_FILE
        )
        self._rng = random.Random(seed)

    # ------------------------------------------------------------------
    # 1. ケース選定
    # ------------------------------------------------------------------

    def _list_all_cases(self) -> List[Path]:
        if not self.cases_dir.exists():
            return []
        return sorted(self.cases_dir.glob("**/*.yaml"))

    def _read_regression_ids(self) -> List[str]:
        if not self.regression_file.exists():
            return []
        ids: List[str] = []
        for line in self.regression_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            ids.append(line)
        return ids

    @staticmethod
    def _case_id_from_path(p: Path) -> str:
        """YAMLヘッダの ``id:`` を読む。読めなければファイル名 stem。"""
        try:
            for line in p.read_text(encoding="utf-8").splitlines()[:8]:
                m = re.match(r"^id:\s*(\S+)\s*$", line)
                if m:
                    return m.group(1)
        except Exception:  # noqa: BLE001
            pass
        return p.stem

    def select_smoke_cases(self) -> List[Path]:
        """10ケース選定。regression固定枠 → 各カテゴリ1件 → 残りランダム。"""
        all_cases = self._list_all_cases()
        if not all_cases:
            return []

        path_by_id: Dict[str, Path] = {self._case_id_from_path(p): p for p in all_cases}
        chosen: List[Path] = []
        chosen_set: set = set()

        # 1) regression 固定枠
        for cid in self._read_regression_ids():
            p = path_by_id.get(cid)
            if p and p not in chosen_set:
                chosen.append(p)
                chosen_set.add(p)
            if len(chosen) >= 3:
                break

        # 2) 各カテゴリから1件
        by_category: Dict[str, List[Path]] = {}
        for p in all_cases:
            # cases/<category>/<file>.yaml を想定
            try:
                cat = p.relative_to(self.cases_dir).parts[0]
            except ValueError:
                cat = "_root"
            by_category.setdefault(cat, []).append(p)

        for cat, files in sorted(by_category.items()):
            if len(chosen) >= self.n_cases:
                break
            # 既選択されてないものから先頭
            for f in files:
                if f not in chosen_set:
                    chosen.append(f)
                    chosen_set.add(f)
                    break

        # 3) 残りはランダム
        remaining = [p for p in all_cases if p not in chosen_set]
        self._rng.shuffle(remaining)
        for p in remaining:
            if len(chosen) >= self.n_cases:
                break
            chosen.append(p)
            chosen_set.add(p)

        return chosen[: self.n_cases]

    # ------------------------------------------------------------------
    # 2. critical paths
    # ------------------------------------------------------------------

    def verify_critical_paths(self) -> CriticalPathResult:
        """worker.js の構文 + デプロイ済みWorkerの /api/health。"""
        result = CriticalPathResult(health_url=self.health_url)

        # 1) node --check api/worker.js
        worker = self.repo_root / "api" / "worker.js"
        if not shutil.which("node"):
            result.syntax_ok = False
            result.syntax_message = "node not in PATH"
        elif not worker.exists():
            result.syntax_ok = False
            result.syntax_message = f"worker.js not found: {worker}"
        else:
            try:
                proc = subprocess.run(
                    ["node", "--check", str(worker)],
                    capture_output=True, text=True, timeout=30,
                )
                result.syntax_ok = proc.returncode == 0
                result.syntax_message = (proc.stderr or proc.stdout or "ok").strip()[:500]
            except subprocess.TimeoutExpired:
                result.syntax_ok = False
                result.syntax_message = "node --check timeout"
            except Exception as e:  # noqa: BLE001
                result.syntax_ok = False
                result.syntax_message = f"node --check exception: {e}"

        # 2) /api/health
        try:
            req = urllib.request.Request(self.health_url, method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")[:500]
                ok_code = 200 <= resp.status < 300
                # status:"ok" が JSON にあれば望ましいが、200ならOKとする
                result.health_ok = ok_code
                result.health_message = f"http={resp.status} body={body[:200]}"
        except Exception as e:  # noqa: BLE001
            result.health_ok = False
            result.health_message = f"health request failed: {e}"

        return result

    # ------------------------------------------------------------------
    # 3. ケース実行 (runner / gatekeeper への薄い委譲)
    # ------------------------------------------------------------------

    def _run_one_case(self, case_path: Path) -> Tuple[bool, str]:
        """1ケース実行 → (passed, message)。

        runner / gatekeeper が無い場合は ``(False, "skipped")``。
        """
        if self.runner is None or self.gatekeeper is None:
            return False, "runner/gatekeeper not provided"

        run_fn: Optional[Callable] = (
            getattr(self.runner, "run_one", None)
            or getattr(self.runner, "run_case", None)
        )
        if run_fn is None:
            return False, "runner has no run_one/run_case"

        eval_fn: Optional[Callable] = (
            getattr(self.gatekeeper, "evaluate", None)
            or getattr(self.gatekeeper, "evaluate_one", None)
            or getattr(self.gatekeeper, "judge", None)
        )
        if eval_fn is None:
            return False, "gatekeeper has no evaluate/evaluate_one/judge"

        try:
            run_result = run_fn(str(case_path))
            verdict = eval_fn(run_result)
            passed = bool(verdict.get("passed")) if isinstance(verdict, dict) else False
            reasons = verdict.get("blocking_reasons") if isinstance(verdict, dict) else []
            return passed, "ok" if passed else f"fail: {(reasons or ['?'])[:1]}"
        except Exception as e:  # noqa: BLE001
            return False, f"exception: {e!r}"

    # ------------------------------------------------------------------
    # 4. 一括実行
    # ------------------------------------------------------------------

    def run(self) -> SmokeResult:
        """スモークテスト実行: critical → 10ケース → 全部PASSなら True。"""
        import time
        t0 = time.time()

        result = SmokeResult()
        cases = self.select_smoke_cases()
        result.selected_cases = [self._case_id_from_path(p) for p in cases]
        result.n_cases = len(cases)

        # 1) critical paths を最優先
        crit = self.verify_critical_paths()
        result.critical = crit
        if not crit.all_pass():
            result.passed = False
            result.errors.append(
                f"critical_path_fail syntax_ok={crit.syntax_ok} health_ok={crit.health_ok} "
                f"({crit.syntax_message[:120]} | {crit.health_message[:120]})"
            )
            result.duration_sec = round(time.time() - t0, 2)
            return result

        # 2) ケース実行
        for p in cases:
            cid = self._case_id_from_path(p)
            ok, msg = self._run_one_case(p)
            if ok:
                result.n_pass += 1
            else:
                result.n_fail += 1
                result.failed_cases.append(f"{cid}: {msg[:120]}")

        result.passed = (result.n_fail == 0 and result.n_cases > 0)
        result.duration_sec = round(time.time() - t0, 2)
        return result


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Run smoke test (critical + N cases)")
    p.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    p.add_argument("--n", type=int, default=10)
    p.add_argument("--health-url", default=DEFAULT_HEALTH_URL)
    p.add_argument("--critical-only", action="store_true",
                   help="ケース実行スキップ。syntax+health のみ")
    p.add_argument("--list-only", action="store_true",
                   help="選定ケース一覧だけ出して終わる")
    args = p.parse_args()

    smoke = SmokeTest(
        repo_root=args.repo_root,
        n_cases=args.n,
        health_url=args.health_url,
    )

    if args.list_only:
        cases = smoke.select_smoke_cases()
        print(json.dumps(
            {"count": len(cases),
             "case_ids": [smoke._case_id_from_path(p) for p in cases]},
            ensure_ascii=False, indent=2,
        ))
        return 0

    if args.critical_only:
        crit = smoke.verify_critical_paths()
        print(json.dumps(asdict(crit), ensure_ascii=False, indent=2))
        return 0 if crit.all_pass() else 2

    result = smoke.run()
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.passed else 2


if __name__ == "__main__":
    sys.exit(main())
