#!/usr/bin/env python3
"""
verdict.py — ゲートキーパー オーケストレータ

run_dir 内の各 ``case_id.json`` (runner出力) と ``cases/`` の YAML を突き合わせ、
``RubricEvaluator`` を全件適用して ``verdicts/<case_id>.json`` と
``summary.md`` を生成する。

【ディレクトリ構造】
    logs/audit/runs/<datetime>/
    ├── <case_id>.json            ← runner出力 (input)
    ├── verdicts/
    │   └── <case_id>.json        ← gatekeeper出力 (このスクリプト)
    ├── summary.md                ← 集計レポート
    └── chain.jsonl               ← chain_logger 出力（オプション）

【使い方】
    # 単一runディレクトリの判定
    python3 scripts/audit/gatekeeper/verdict.py \\
        --run-dir logs/audit/runs/2026-04-29_120000/

    # オプション
    --cases-dir scripts/audit/cases/    # YAML テストケース root
    --no-llm                            # LLM評価をスキップ（CI動作確認用）
    --max-cases 10                      # デバッグ用 件数制限
    --concurrency 4                     # 並列LLM呼出数
    --sample-rate 0.2                   # 人間レビュー抜き取り率
    --pubkey-id auditor-2026-04         # chain_logger署名鍵ID

【chain_logger 連携】
    --enable-chain-log がある場合、各verdictをhash chainに記録（改ざん耐性）
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ローカル import (sys.path で repo root を解決)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.audit.gatekeeper.rubric_eval import (  # noqa: E402
    RubricEvaluator,
    RubricResult,
)
from scripts.audit.lib.llm_client import (  # noqa: E402
    LLMClient,
    LLMClientConfigError,
)


# ============================================================================
# YAML ローダ
# ============================================================================

def _load_yaml(path: Path) -> Dict[str, Any]:
    import yaml  # type: ignore
    return yaml.safe_load(path.read_text(encoding="utf-8"))


# ============================================================================
# Mock LLM (CI/オフライン用)
# ============================================================================

class MockLLM:
    """LLM呼出をskipしてデフォルトスコアで応答するスタブ。"""

    total_calls = 0
    total_input_tokens = 0
    total_output_tokens = 0
    provider = "mock"
    model = "mock"

    def generate(self, prompt: str, **kw) -> str:
        return '{"score": 4, "reasoning": "mock"}'

    def generate_json(self, prompt: str, **kw) -> Dict[str, Any]:
        return {"consistent": True, "score": 4, "reasoning": "mock"}

    def generate_json_n(self, prompt: str, n: int = 3, **kw) -> List[Dict[str, Any]]:
        return [{"score": 4, "reasoning": "mock"}] * n

    def cost_summary(self) -> Dict[str, Any]:
        return {"provider": "mock", "calls": 0, "estimated_usd": 0.0}


# ============================================================================
# GatekeeperOrchestrator
# ============================================================================

class GatekeeperOrchestrator:
    """テスト結果フォルダから verdict 一括生成。

    Args:
        run_dir: runner出力ルート (``<case_id>.json`` が並ぶ)。
        cases_dir: YAML ケース root（カテゴリ別サブディレクトリ）。
        evaluator: ``RubricEvaluator`` インスタンス。
        chain_logger: 任意の ``ChainLogger`` インスタンス（None で無効）。
        concurrency: LLM評価の並列度。
        max_cases: 検査件数上限（デバッグ用）。
    """

    def __init__(
        self,
        run_dir: Path,
        cases_dir: Path,
        evaluator: RubricEvaluator,
        chain_logger=None,
        concurrency: int = 4,
        max_cases: Optional[int] = None,
    ) -> None:
        self.run_dir = Path(run_dir)
        self.cases_dir = Path(cases_dir)
        self.evaluator = evaluator
        self.chain_logger = chain_logger
        self.concurrency = max(1, concurrency)
        self.max_cases = max_cases

        self.verdicts_dir = self.run_dir / "verdicts"
        self.verdicts_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 公開エントリ
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        """全ケースの評価 → verdict 出力 → summary.md。

        Returns:
            ``{"total": int, "pass": int, "fail": int, "skip": int, "elapsed_sec": float}``
        """
        pairs = self._collect_pairs()
        if self.max_cases:
            pairs = pairs[: self.max_cases]

        if not pairs:
            print(f"[gatekeeper] no run results found in {self.run_dir}")
            return {"total": 0, "pass": 0, "fail": 0, "skip": 0, "elapsed_sec": 0}

        print(f"[gatekeeper] evaluating {len(pairs)} cases (concurrency={self.concurrency})")
        start = time.time()
        results: List[RubricResult] = []

        with cf.ThreadPoolExecutor(max_workers=self.concurrency) as ex:
            futs = {
                ex.submit(self._evaluate_one, case, run_obj): case.get("id")
                for (case, run_obj) in pairs
            }
            done = 0
            for fut in cf.as_completed(futs):
                case_id = futs[fut]
                try:
                    r = fut.result()
                    results.append(r)
                except Exception as e:  # noqa: BLE001
                    print(f"  [{case_id}] EVAL ERROR: {e}", file=sys.stderr)
                done += 1
                if done % 10 == 0:
                    print(f"  ...{done}/{len(pairs)}")

        elapsed = time.time() - start

        # 集計
        total = len(results)
        n_pass = sum(1 for r in results if r.verdict == "PASS")
        n_fail = sum(1 for r in results if r.verdict == "FAIL")
        n_skip = sum(1 for r in results if r.verdict == "SKIP")

        # summary.md 生成 (lazy import)
        from scripts.audit.gatekeeper.summary import (  # noqa: WPS433
            generate_summary,
            generate_human_review_list,
        )
        summary_md = generate_summary(self.verdicts_dir, run_dir=self.run_dir)
        (self.run_dir / "summary.md").write_text(summary_md, encoding="utf-8")
        review_md = generate_human_review_list(self.verdicts_dir)
        (self.run_dir / "human_review.md").write_text(review_md, encoding="utf-8")

        summary_out = {
            "run_dir": str(self.run_dir),
            "total": total,
            "pass": n_pass,
            "fail": n_fail,
            "skip": n_skip,
            "pass_rate": round(n_pass / total, 3) if total else 0.0,
            "elapsed_sec": round(elapsed, 1),
            "llm_cost": getattr(self.evaluator.llm, "cost_summary", lambda: {})(),
        }
        (self.run_dir / "verdict_summary.json").write_text(
            json.dumps(summary_out, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # chain log: verdict_run completed
        if self.chain_logger:
            try:
                self.chain_logger.append(
                    "gatekeeper",
                    "verdict_run_completed",
                    summary_out,
                )
            except Exception as e:  # noqa: BLE001
                print(f"[gatekeeper] chain_logger append failed: {e}", file=sys.stderr)

        print(
            f"[gatekeeper] done: PASS={n_pass} FAIL={n_fail} SKIP={n_skip} "
            f"pass_rate={summary_out['pass_rate']*100:.1f}% elapsed={elapsed:.1f}s"
        )
        return summary_out

    # ------------------------------------------------------------------
    # ペア収集
    # ------------------------------------------------------------------

    def _collect_pairs(self) -> List[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """run_dir 内の <case_id>.json に対応する case YAML を見つける。"""
        run_files = sorted(p for p in self.run_dir.glob("*.json"))
        # verdicts/ 配下や verdict_summary.json は除外
        run_files = [
            p for p in run_files
            if p.name not in ("verdict_summary.json",) and not p.name.endswith(".meta.json")
        ]

        # YAMLインデックス: id → path
        yaml_index: Dict[str, Path] = {}
        for ypath in self.cases_dir.rglob("*.yaml"):
            try:
                obj = _load_yaml(ypath)
                cid = obj.get("id")
                if cid:
                    yaml_index[cid] = ypath
            except Exception as e:  # noqa: BLE001
                print(f"[gatekeeper] yaml load failed: {ypath}: {e}", file=sys.stderr)

        pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        for rp in run_files:
            try:
                run_obj = json.loads(rp.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                print(f"[gatekeeper] run json broken: {rp}: {e}", file=sys.stderr)
                continue
            case_id = run_obj.get("case_id") or rp.stem
            ypath = yaml_index.get(case_id)
            if not ypath:
                # case YAML不在 → ダミーcase で評価続行（functional=skip相当）
                case = {"id": case_id, "steps": [], "expectations": {}}
            else:
                case = _load_yaml(ypath)
            pairs.append((case, run_obj))
        return pairs

    # ------------------------------------------------------------------
    # 1ケース評価
    # ------------------------------------------------------------------

    def _evaluate_one(
        self,
        case: Dict[str, Any],
        run_obj: Dict[str, Any],
    ) -> RubricResult:
        result = self.evaluator.evaluate(case, run_obj)
        # verdict ファイル書き出し
        out_path = self.verdicts_dir / f"{result.case_id}.json"
        out_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # chain_logger 連携
        if self.chain_logger:
            try:
                self.chain_logger.append(
                    "gatekeeper",
                    "verdict",
                    {
                        "case_id": result.case_id,
                        "verdict": result.verdict,
                        "scores": result.scores,
                        "blocking_reasons": result.blocking_reasons[:5],
                        "human_review_flag": result.human_review_flag,
                    },
                )
            except Exception as e:  # noqa: BLE001
                print(
                    f"[gatekeeper] chain_logger append failed for {result.case_id}: {e}",
                    file=sys.stderr,
                )
        return result


# ============================================================================
# CLI
# ============================================================================

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="verdict.py",
        description=(
            "ナースロビーQAゲートキーパー: runner出力を8軸ルーブリックで判定。"
            " F/C/S/H = 5/5必須、U/E/L ≥ 4、K は警告のみ。"
        ),
    )
    p.add_argument(
        "--run-dir",
        required=True,
        help="runner出力ディレクトリ (例: logs/audit/runs/2026-04-29_120000/)",
    )
    p.add_argument(
        "--cases-dir",
        default=str(_REPO_ROOT / "scripts" / "audit" / "cases"),
        help="YAMLテストケース root (default: scripts/audit/cases/)",
    )
    p.add_argument(
        "--evaluator-model",
        default="claude-opus-4-7",
        help="ゲートキーパー評価モデル (default: claude-opus-4-7)",
    )
    p.add_argument(
        "--consistency-model",
        default="gpt-4o-mini",
        help="QR整合性チェック軽量LLM (default: gpt-4o-mini)",
    )
    p.add_argument("--no-llm", action="store_true", help="LLM評価をskip（CI動作確認）")
    p.add_argument("--max-cases", type=int, default=None, help="検査件数上限")
    p.add_argument("--concurrency", type=int, default=4, help="並列度")
    p.add_argument(
        "--sample-rate", type=float, default=0.2,
        help="人間目視抜き取り率 (default: 0.2)",
    )
    p.add_argument("--seed", type=int, default=None, help="抜き取り抽選seed")
    p.add_argument(
        "--enable-chain-log", action="store_true",
        help="ChainLogger に verdict を記録 (hash chain + Ed25519署名)",
    )
    p.add_argument(
        "--pubkey-id", default="auditor-2026-04",
        help="chain_logger 署名鍵ID",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    run_dir = Path(args.run_dir).expanduser().resolve()
    cases_dir = Path(args.cases_dir).expanduser().resolve()
    if not run_dir.exists():
        print(f"[gatekeeper] run_dir not found: {run_dir}", file=sys.stderr)
        return 2
    if not cases_dir.exists():
        print(f"[gatekeeper] cases_dir not found: {cases_dir}", file=sys.stderr)
        return 2

    # LLM client（or mock）
    if args.no_llm:
        eval_llm = MockLLM()
        consistency_llm = MockLLM()
    else:
        try:
            eval_llm = LLMClient(model=args.evaluator_model)
            print(
                f"[gatekeeper] evaluator: provider={eval_llm.provider} "
                f"model={eval_llm.model}"
            )
            try:
                consistency_llm = LLMClient(
                    model=args.consistency_model, prefer="openai",
                )
                print(
                    f"[gatekeeper] consistency: provider={consistency_llm.provider} "
                    f"model={consistency_llm.model}"
                )
            except LLMClientConfigError as e:
                print(f"[gatekeeper] no consistency LLM: {e}", file=sys.stderr)
                consistency_llm = None
        except LLMClientConfigError as e:
            print(
                f"[gatekeeper] LLM init failed ({e}); falling back to --no-llm",
                file=sys.stderr,
            )
            eval_llm = MockLLM()
            consistency_llm = MockLLM()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    evaluator = RubricEvaluator(
        eval_llm,
        consistency_llm_client=consistency_llm,
        sample_rate_for_human=args.sample_rate,
        rng=rng,
    )

    chain_logger = None
    if args.enable_chain_log:
        from scripts.audit.lib.chain_logger import ChainLogger
        chain_logger = ChainLogger(
            log_dir=run_dir,
            pubkey_id=args.pubkey_id,
        )

    orch = GatekeeperOrchestrator(
        run_dir=run_dir,
        cases_dir=cases_dir,
        evaluator=evaluator,
        chain_logger=chain_logger,
        concurrency=args.concurrency,
        max_cases=args.max_cases,
    )
    summary = orch.run()
    # 終了コード: 失敗が1件以上で 1
    return 1 if summary.get("fail", 0) > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
