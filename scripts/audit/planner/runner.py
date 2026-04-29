#!/usr/bin/env python3
"""
runner.py — テストケースを Worker に対して並列実行する E2E ランナー

設計書 §1 / §10 (DESIGN.md) の Phase B-4 を担う。
YAMLケースを読み込み、並列8で Worker (live) に webhook 送信し、
結果を ``logs/audit/runs/<datetime>/`` に書き出し、ChainLogger に追記する。

【使い方】
    # ケース読込確認のみ（Worker非接続）
    python3 scripts/audit/planner/runner.py --all --dry-run

    # 1ケースだけ実行
    python3 scripts/audit/planner/runner.py --case-id aica_relationship_001

    # カテゴリ単位
    python3 scripts/audit/planner/runner.py --category emergency_keyword --parallel 4

    # 全件
    python3 scripts/audit/planner/runner.py --all --parallel 8

【出力】
    logs/audit/runs/YYYY-MM-DD_HHMMSS/
        ├── <case_id>.json    # 1ケース実行結果
        ├── ...
        └── summary.json      # 集計統計

    logs/audit/YYYY-MM-DD/chain.jsonl
        runner actor で case_executed / case_error イベント追記

【セキュリティ】
    - テスト用 userId は必ず ``U_TEST_`` prefix（``LineClient.make_test_user_id``）
    - audit-reset は ``U_TEST_`` / ``Utest`` prefix のみ受付（Worker側で強制）
    - Secret は ``AUDIT_SECRET`` 優先、無ければ ``LINE_PUSH_SECRET`` を fallback
"""
from __future__ import annotations

import argparse
import asyncio
import dataclasses
import glob
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# repo root を import path に追加（scripts/audit/planner/ から3階層上）
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.audit.lib.line_client import (  # noqa: E402
    LineClient,
    LineClientConfigError,
    LineClientError,
    LineClientNetworkError,
    _load_env,  # 内部関数だが secret 取得用に再利用
)
from scripts.audit.lib.chain_logger import ChainLogger  # noqa: E402


# ============================================================================
# 定数
# ============================================================================

CASES_ROOT = _REPO_ROOT / "scripts" / "audit" / "cases"
DEFAULT_OUT_ROOT = _REPO_ROOT / "logs" / "audit" / "runs"
DEFAULT_CHAIN_LOG_ROOT = _REPO_ROOT / "logs" / "audit"
DEFAULT_PARALLEL = 8


# ============================================================================
# 結果オブジェクト
# ============================================================================

@dataclass
class StepResult:
    """1ステップの実行結果（軽量。replyTokenは記録しない）。"""
    index: int
    kind: str
    request: Dict[str, Any] = field(default_factory=dict)
    status: int = 0  # HTTP status (0 = no request issued)
    response_summary: Any = None  # truncated response body
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class RunnerResult:
    """1ケース実行結果。``--out`` 配下にJSONとして書き出される。"""
    case_id: str
    category: str
    status: str = "pending"  # "pass" | "fail" | "error" | "skip"
    user_id: str = ""
    steps_total: int = 0
    steps_executed: int = 0
    duration_ms: int = 0
    started_at: str = ""
    finished_at: str = ""
    step_results: List[StepResult] = field(default_factory=list)
    entry_snapshots: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = dataclasses.asdict(self)
        return d


# ============================================================================
# ユーティリティ
# ============================================================================

def _load_secret() -> str:
    """``AUDIT_SECRET`` → ``LINE_PUSH_SECRET`` の順で取得。"""
    env_path = _REPO_ROOT / ".env"
    env = _load_env(env_path)
    secret = (
        os.environ.get("AUDIT_SECRET")
        or env.get("AUDIT_SECRET")
        or os.environ.get("LINE_PUSH_SECRET")
        or env.get("LINE_PUSH_SECRET")
        or ""
    )
    return secret


def _truncate(obj: Any, max_chars: int = 600) -> Any:
    """レスポンス保存時に巨大データを切り詰め。"""
    if obj is None:
        return None
    if isinstance(obj, (dict, list)):
        try:
            s = json.dumps(obj, ensure_ascii=False)
        except Exception:
            s = str(obj)
        if len(s) > max_chars:
            return s[:max_chars] + f"...<truncated {len(s) - max_chars} chars>"
        return obj
    if isinstance(obj, str):
        return obj[:max_chars] + (
            f"...<truncated {len(obj) - max_chars} chars>" if len(obj) > max_chars else ""
        )
    return obj


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


# ============================================================================
# ケース読込
# ============================================================================

def load_case_file(path: Path) -> Dict[str, Any]:
    """1個のYAMLファイルを読み込んで dict 化。"""
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "id" not in data:
        raise ValueError(f"invalid case file: {path} (missing 'id')")
    data.setdefault("category", path.parent.name)
    data["__path"] = str(path)
    return data


def load_cases(args: argparse.Namespace) -> List[Dict[str, Any]]:
    """CLI 引数からケースリストを構築。"""
    paths: List[Path] = []

    if args.cases:
        for pattern in args.cases:
            # glob 解決（絶対 or repo root 起点 or cwd）
            matches = []
            if any(c in pattern for c in "*?["):
                # globパターン
                matches = [Path(p) for p in glob.glob(pattern)]
                if not matches:
                    matches = [Path(p) for p in glob.glob(str(_REPO_ROOT / pattern))]
            else:
                p = Path(pattern)
                if not p.is_absolute():
                    candidate = _REPO_ROOT / pattern
                    if candidate.exists():
                        p = candidate
                if p.exists():
                    matches = [p]
            paths.extend(matches)

    if args.case_id:
        # cases/ 全体から id 一致を探す
        for ypath in CASES_ROOT.rglob("*.yaml"):
            try:
                data = load_case_file(ypath)
                if data.get("id") == args.case_id:
                    paths.append(ypath)
                    break
            except Exception:
                continue

    if args.category:
        cat_dir = CASES_ROOT / args.category
        if not cat_dir.exists():
            raise FileNotFoundError(f"category dir not found: {cat_dir}")
        paths.extend(sorted(cat_dir.glob("*.yaml")))

    if args.all:
        paths.extend(sorted(CASES_ROOT.rglob("*.yaml")))

    # 重複除去（順序維持）
    seen = set()
    unique_paths: List[Path] = []
    for p in paths:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        unique_paths.append(p)

    cases: List[Dict[str, Any]] = []
    for p in unique_paths:
        try:
            cases.append(load_case_file(p))
        except Exception as e:
            print(f"[WARN] failed to load {p}: {e}", file=sys.stderr)
    return cases


# ============================================================================
# CaseRunner
# ============================================================================

class CaseRunner:
    """1ケースを順次実行する。"""

    def __init__(
        self,
        case: Dict[str, Any],
        line_client: LineClient,
        chain_logger: Optional[ChainLogger],
        secret: str,
        step_delay_ms: int = 250,
        per_step_timeout_s: float = 20.0,
    ) -> None:
        self.case = case
        self.client = line_client
        self.chain = chain_logger
        self.secret = secret
        self.step_delay_ms = step_delay_ms
        self.per_step_timeout = per_step_timeout_s

    async def run(self) -> RunnerResult:
        case_id = self.case["id"]
        category = self.case.get("category", "uncategorized")
        steps = self.case.get("steps") or []

        result = RunnerResult(
            case_id=case_id,
            category=category,
            steps_total=len(steps),
            started_at=_now_iso(),
            metadata={
                "persona": self.case.get("persona"),
                "seed": self.case.get("seed"),
                "description": self.case.get("description"),
                "case_path": self.case.get("__path"),
            },
        )

        t0 = time.time()
        user_id = self.client.make_test_user_id(suffix=case_id)
        result.user_id = user_id

        try:
            # 1) 事前条件
            preconds = self.case.get("preconditions") or {}
            if preconds.get("reset_kv"):
                await self._reset(user_id, result)
            if preconds.get("follow_first"):
                await self._follow(user_id, result)

            # 2) ステップ順次実行
            for i, step in enumerate(steps):
                sr = await self._execute_step(step, user_id, i)
                result.step_results.append(sr)
                if sr.error is None:
                    result.steps_executed += 1
                else:
                    # 1stepの失敗で残りスキップせず、なるべく走り切る方針
                    # （gatekeeper側でstep_resultsを見て総合判定）
                    pass
                # スロットル
                if self.step_delay_ms > 0:
                    await asyncio.sleep(self.step_delay_ms / 1000.0)

            # 3) 最終 audit-snapshot
            snap = await self._snapshot(user_id, result)
            if snap is not None:
                result.entry_snapshots.append(snap)

            # 4) 仮判定: 全step が HTTP 200 系で完走したら "pass"（gatekeeperが上書き）
            failed_steps = [s for s in result.step_results if s.error]
            non2xx_steps = [
                s for s in result.step_results
                if s.status and not (200 <= s.status < 300)
            ]
            if not failed_steps and not non2xx_steps:
                result.status = "pass"
            else:
                result.status = "fail"
                if failed_steps:
                    result.errors.append(f"{len(failed_steps)} step(s) raised exception")
                if non2xx_steps:
                    result.errors.append(
                        f"{len(non2xx_steps)} step(s) returned non-2xx"
                    )

            # 5) cleanup
            try:
                await self._reset(user_id, result, log_as="cleanup")
            except Exception as e:
                # cleanup 失敗は警告のみ
                result.errors.append(f"cleanup_failed: {e}")

        except asyncio.CancelledError:
            result.status = "error"
            result.errors.append("cancelled")
            raise
        except Exception as e:
            result.status = "error"
            result.errors.append(f"{type(e).__name__}: {e}")
            result.errors.append(traceback.format_exc(limit=4))
        finally:
            result.duration_ms = int((time.time() - t0) * 1000)
            result.finished_at = _now_iso()

            # ChainLogger に記録
            if self.chain is not None:
                try:
                    last_snap = (
                        result.entry_snapshots[-1] if result.entry_snapshots else {}
                    )
                    entry = (last_snap or {}).get("entry") or {}
                    audit_trail = entry.get("auditTrail") or []
                    summary_payload = {
                        "case_id": case_id,
                        "category": category,
                        "user_id": user_id,
                        "status": result.status,
                        "steps_total": result.steps_total,
                        "steps_executed": result.steps_executed,
                        "duration_ms": result.duration_ms,
                        "errors_head": result.errors[:3],
                        "snapshot_summary": {
                            "phase": entry.get("phase"),
                            "messageCount": entry.get("messageCount"),
                            "auditTrail_count": len(audit_trail) if isinstance(audit_trail, list) else 0,
                        },
                    }
                    if result.status == "error":
                        self.chain.append("runner", "case_error", summary_payload)
                    else:
                        self.chain.append("runner", "case_executed", summary_payload)
                except Exception as e:
                    # ログ書き込み失敗で実行を止めない
                    result.errors.append(f"chain_logger_failed: {e}")

        return result

    # ----- step kinds -----

    async def _execute_step(
        self, step: Dict[str, Any], user_id: str, idx: int
    ) -> StepResult:
        kind = step.get("kind", "")
        sr = StepResult(index=idx, kind=kind, request=dict(step))
        t0 = time.time()
        try:
            if kind == "text":
                res = await asyncio.wait_for(
                    self.client.send_text_async(user_id, step["text"]),
                    timeout=self.per_step_timeout,
                )
                sr.status = res.get("status", 0)
                sr.response_summary = _truncate(res.get("body"))
            elif kind == "postback":
                res = await asyncio.wait_for(
                    self.client.send_postback_async(user_id, step["data"], params=step.get("params")),
                    timeout=self.per_step_timeout,
                )
                sr.status = res.get("status", 0)
                sr.response_summary = _truncate(res.get("body"))
            elif kind == "audio":
                res = await asyncio.wait_for(
                    self.client.send_audio_async(
                        user_id, step["audio_path"], duration_ms=step.get("duration_ms", 3000)
                    ),
                    timeout=self.per_step_timeout,
                )
                sr.status = res.get("status", 0)
                sr.response_summary = _truncate(res.get("body"))
            elif kind == "follow":
                res = await asyncio.wait_for(
                    self.client.send_follow_async(user_id),
                    timeout=self.per_step_timeout,
                )
                sr.status = res.get("status", 0)
                sr.response_summary = _truncate(res.get("body"))
            elif kind == "unfollow":
                res = await asyncio.wait_for(
                    self.client.send_unfollow_async(user_id),
                    timeout=self.per_step_timeout,
                )
                sr.status = res.get("status", 0)
                sr.response_summary = _truncate(res.get("body"))
            elif kind == "wait":
                seconds = float(step.get("seconds", 1))
                await asyncio.sleep(seconds)
                sr.status = 200
                sr.response_summary = f"slept {seconds}s"
            elif kind == "snapshot":
                snap = await asyncio.wait_for(
                    self.client.audit_snapshot_async(user_id, self.secret),
                    timeout=self.per_step_timeout,
                )
                sr.status = snap.get("status", 0)
                # snapshot本体は別途 entry_snapshots に保存するため概要だけ
                sr.response_summary = _truncate(snap.get("body"))
            else:
                sr.error = f"unknown step kind: {kind!r}"
        except asyncio.TimeoutError:
            sr.error = f"timeout after {self.per_step_timeout}s"
        except (LineClientNetworkError, LineClientError) as e:
            sr.error = f"{type(e).__name__}: {e}"
        except Exception as e:
            sr.error = f"{type(e).__name__}: {e}"
        finally:
            sr.duration_ms = int((time.time() - t0) * 1000)
        return sr

    async def _follow(self, user_id: str, result: RunnerResult) -> None:
        try:
            res = await asyncio.wait_for(
                self.client.send_follow_async(user_id), timeout=self.per_step_timeout
            )
            if not (200 <= res.get("status", 0) < 300):
                result.errors.append(f"follow_first non-2xx: {res.get('status')}")
        except Exception as e:
            result.errors.append(f"follow_first_failed: {type(e).__name__}: {e}")

    async def _reset(
        self, user_id: str, result: RunnerResult, log_as: str = "reset"
    ) -> None:
        try:
            res = await asyncio.wait_for(
                self.client.audit_reset_async(user_id, self.secret),
                timeout=self.per_step_timeout,
            )
            status = res.get("status", 0)
            if not (200 <= status < 300) and status != 404:
                # 404 は entry なしで OK 扱い
                result.errors.append(f"{log_as}_non2xx: status={status}")
        except Exception as e:
            result.errors.append(f"{log_as}_failed: {type(e).__name__}: {e}")

    async def _snapshot(
        self, user_id: str, result: RunnerResult
    ) -> Optional[Dict[str, Any]]:
        try:
            res = await asyncio.wait_for(
                self.client.audit_snapshot_async(user_id, self.secret),
                timeout=self.per_step_timeout,
            )
            body = res.get("body")
            if isinstance(body, dict):
                return body
            return {"status": res.get("status"), "raw": _truncate(body)}
        except Exception as e:
            result.errors.append(f"snapshot_failed: {type(e).__name__}: {e}")
            return None


# ============================================================================
# Orchestrator
# ============================================================================

class RunnerOrchestrator:
    """全ケースを Semaphore で並列実行。"""

    def __init__(
        self,
        cases: List[Dict[str, Any]],
        line_client: LineClient,
        chain_logger: Optional[ChainLogger],
        secret: str,
        parallel: int = DEFAULT_PARALLEL,
        progress: bool = True,
    ) -> None:
        self.cases = cases
        self.line_client = line_client
        self.chain_logger = chain_logger
        self.secret = secret
        self.parallel = max(1, parallel)
        self.progress = progress
        self._completed = 0
        self._fail = 0
        self._error = 0
        self._lock = asyncio.Lock()
        self._t_start = 0.0

    async def run_all(self) -> List[RunnerResult]:
        sem = asyncio.Semaphore(self.parallel)
        results: List[RunnerResult] = []
        self._t_start = time.time()

        async def _runner(case: Dict[str, Any]) -> RunnerResult:
            async with sem:
                cr = CaseRunner(
                    case=case,
                    line_client=self.line_client,
                    chain_logger=self.chain_logger,
                    secret=self.secret,
                )
                r = await cr.run()
                async with self._lock:
                    self._completed += 1
                    if r.status == "fail":
                        self._fail += 1
                    elif r.status == "error":
                        self._error += 1
                if self.progress:
                    self._print_progress(r)
                return r

        # 進捗タスク（1秒間隔）と並走
        progress_task = None
        if self.progress:
            progress_task = asyncio.create_task(self._progress_loop())

        try:
            results = await asyncio.gather(
                *[_runner(c) for c in self.cases],
                return_exceptions=False,
            )
        finally:
            if progress_task:
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass

        return results

    def _print_progress(self, r: RunnerResult) -> None:
        total = len(self.cases)
        marker = {
            "pass": "OK",
            "fail": "FAIL",
            "error": "ERR",
            "skip": "SKIP",
        }.get(r.status, "?")
        sys.stdout.write(
            f"  [{self._completed:>3}/{total}] {marker:<4} "
            f"{r.case_id:<40} {r.duration_ms}ms\n"
        )
        sys.stdout.flush()

    async def _progress_loop(self) -> None:
        while True:
            await asyncio.sleep(2.0)
            elapsed = time.time() - self._t_start
            sys.stdout.write(
                f"  ... progress {self._completed}/{len(self.cases)} "
                f"(fail={self._fail} err={self._error}) elapsed={elapsed:.1f}s\n"
            )
            sys.stdout.flush()

    @staticmethod
    def summarize(results: List[RunnerResult]) -> Dict[str, Any]:
        total = len(results)
        n_pass = sum(1 for r in results if r.status == "pass")
        n_fail = sum(1 for r in results if r.status == "fail")
        n_error = sum(1 for r in results if r.status == "error")
        n_skip = sum(1 for r in results if r.status == "skip")
        durations = [r.duration_ms for r in results if r.duration_ms]
        avg = int(sum(durations) / len(durations)) if durations else 0
        mx = max(durations) if durations else 0
        mn = min(durations) if durations else 0

        by_cat: Dict[str, Dict[str, int]] = {}
        for r in results:
            d = by_cat.setdefault(
                r.category, {"total": 0, "pass": 0, "fail": 0, "error": 0, "skip": 0}
            )
            d["total"] += 1
            d[r.status] = d.get(r.status, 0) + 1

        # 失敗詳細トップ10
        failed_brief = [
            {
                "case_id": r.case_id,
                "status": r.status,
                "errors": r.errors[:2],
                "duration_ms": r.duration_ms,
            }
            for r in results
            if r.status in ("fail", "error")
        ][:10]

        return {
            "total": total,
            "pass": n_pass,
            "fail": n_fail,
            "error": n_error,
            "skip": n_skip,
            "pass_rate": round(n_pass / total, 4) if total else 0.0,
            "avg_duration_ms": avg,
            "max_duration_ms": mx,
            "min_duration_ms": mn,
            "by_category": by_cat,
            "failed_brief": failed_brief,
        }


# ============================================================================
# Slack 通知（任意）
# ============================================================================

def notify_slack(summary: Dict[str, Any], out_dir: Path) -> None:
    """大規模runの完了をSlackに通知。``slack_bridge.py --send`` を呼び出す。"""
    try:
        import subprocess

        msg = (
            f"[QA Runner] 完了: pass={summary['pass']}/{summary['total']} "
            f"fail={summary['fail']} error={summary['error']} "
            f"avg={summary['avg_duration_ms']}ms\n"
            f"out: {out_dir}"
        )
        subprocess.run(
            [
                "python3",
                str(_REPO_ROOT / "scripts" / "slack_bridge.py"),
                "--send",
                msg,
            ],
            timeout=10,
            check=False,
        )
    except Exception as e:
        print(f"[WARN] slack notify failed: {e}", file=sys.stderr)


# ============================================================================
# main
# ============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="runner",
        description="ナースロビー LINE Bot 監査システム — テストケース並列ランナー",
    )
    parser.add_argument(
        "--cases", nargs="*", help="ケースYAML（globパターン可、複数指定可）"
    )
    parser.add_argument("--case-id", help="単一ケースID実行（例: aica_relationship_001）")
    parser.add_argument(
        "--category",
        help="カテゴリ単位で実行（cases/<category>/*.yaml）",
    )
    parser.add_argument("--all", action="store_true", help="cases/ 配下全件実行")
    parser.add_argument(
        "--parallel",
        type=int,
        default=DEFAULT_PARALLEL,
        help=f"同時並列数 (default: {DEFAULT_PARALLEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ケース読込のみで Worker への送信はスキップ",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT_ROOT),
        help="結果出力先ルート (default: logs/audit/runs/)",
    )
    parser.add_argument(
        "--chain-log-dir",
        default=None,
        help="ChainLoggerの保存先 (default: logs/audit/YYYY-MM-DD/)",
    )
    parser.add_argument("--quiet", action="store_true", help="進捗表示・Slack通知抑止")
    parser.add_argument(
        "--no-slack", action="store_true", help="Slack通知のみ抑止"
    )
    parser.add_argument(
        "--no-chain",
        action="store_true",
        help="ChainLogger 書き込みをスキップ（CIテスト等）",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="先頭から N 件のみ実行 (default: 全件)"
    )

    args = parser.parse_args(argv)

    # 1) ケース読み込み
    cases = load_cases(args)

    if args.limit and args.limit > 0:
        cases = cases[: args.limit]

    print(f"[runner] {len(cases)} case(s) loaded")

    if not cases:
        print("[runner] no cases matched. Use --all / --category / --case-id / --cases")
        return 2

    # 2) dry-run
    if args.dry_run:
        print("[runner] DRY RUN: ケース概要を表示して終了")
        for c in cases[:30]:
            print(
                f"  - {c.get('id'):<35} [{c.get('category')}] "
                f"steps={len(c.get('steps') or [])} "
                f"{(c.get('description') or '')[:60]}"
            )
        if len(cases) > 30:
            print(f"  ... and {len(cases) - 30} more")
        # カテゴリ別集計
        cats: Dict[str, int] = {}
        for c in cases:
            cats[c.get("category", "?")] = cats.get(c.get("category", "?"), 0) + 1
        print("\n[runner] category breakdown:")
        for k, v in sorted(cats.items()):
            print(f"  {k:<25} {v:>3}")
        return 0

    # 3) Worker 接続準備
    try:
        client = LineClient()
    except LineClientConfigError as e:
        print(f"[runner] LineClient init failed: {e}", file=sys.stderr)
        return 1

    secret = _load_secret()
    if not secret:
        print(
            "[runner] WARN: AUDIT_SECRET / LINE_PUSH_SECRET 未設定 — "
            "audit-snapshot/audit-reset は 401 で失敗します",
            file=sys.stderr,
        )

    # 4) ChainLogger 準備
    chain_logger: Optional[ChainLogger] = None
    if not args.no_chain:
        chain_dir = (
            Path(args.chain_log_dir).expanduser()
            if args.chain_log_dir
            else DEFAULT_CHAIN_LOG_ROOT / datetime.now().strftime("%Y-%m-%d")
        )
        try:
            chain_logger = ChainLogger(chain_dir)
            print(f"[runner] chain log: {chain_dir}/chain.jsonl")
        except Exception as e:
            print(f"[runner] WARN: ChainLogger init failed: {e}", file=sys.stderr)
            chain_logger = None

    # 5) 出力先ディレクトリ
    out_dir = Path(args.out).expanduser() / time.strftime("%Y-%m-%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[runner] output dir: {out_dir}")

    # 6) 実行
    print(
        f"[runner] starting parallel={args.parallel} "
        f"target={client.worker_url}"
    )
    t0 = time.time()
    orch = RunnerOrchestrator(
        cases=cases,
        line_client=client,
        chain_logger=chain_logger,
        secret=secret,
        parallel=args.parallel,
        progress=not args.quiet,
    )
    results: List[RunnerResult] = asyncio.run(orch.run_all())
    elapsed = time.time() - t0

    # 7) 結果保存
    for r in results:
        out_path = out_dir / f"{r.case_id}.json"
        try:
            out_path.write_text(
                json.dumps(r.to_dict(), ensure_ascii=False, indent=2)
            )
        except Exception as e:
            print(f"[runner] WARN: save failed for {r.case_id}: {e}", file=sys.stderr)

    summary = RunnerOrchestrator.summarize(results)
    summary["elapsed_seconds"] = round(elapsed, 2)
    summary["parallel"] = args.parallel
    summary["worker_url"] = client.worker_url
    summary["total_cases_loaded"] = len(cases)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    # 8) サマリ表示
    print("\n[runner] === Summary ===")
    print(f"  total       : {summary['total']}")
    print(f"  pass        : {summary['pass']} ({summary['pass_rate'] * 100:.1f}%)")
    print(f"  fail        : {summary['fail']}")
    print(f"  error       : {summary['error']}")
    print(f"  skip        : {summary['skip']}")
    print(f"  avg duration: {summary['avg_duration_ms']}ms")
    print(f"  max duration: {summary['max_duration_ms']}ms")
    print(f"  elapsed     : {elapsed:.1f}s")
    print(f"  output      : {out_dir}")
    if summary["failed_brief"]:
        print("\n  Failed (top 10):")
        for f in summary["failed_brief"]:
            errs = "; ".join(f["errors"])[:120]
            print(f"    - {f['case_id']:<35} [{f['status']}] {errs}")

    # 9) Slack通知（大規模時のみ）
    if not args.quiet and not args.no_slack and len(cases) >= 50:
        notify_slack(summary, out_dir)

    # 終了コード: pass率100%なら0、それ以外1
    return 0 if summary["fail"] == 0 and summary["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
