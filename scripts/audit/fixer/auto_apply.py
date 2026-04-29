#!/usr/bin/env python3
"""
auto_apply.py — パッチ適用 + Cloudflare Worker デプロイ + ロールバック

設計書 §5 (DESIGN.md) + MEMORY.md の運用ルールに準拠:
    - **デプロイコマンド**: ``cd api && unset CLOUDFLARE_API_TOKEN && \
      npx wrangler deploy --config wrangler.toml``
        - ``--config wrangler.toml`` を絶対に省略しない
          (ルートの wrangler.jsonc が優先される事故を防ぐ)
        - ``unset CLOUDFLARE_API_TOKEN`` で OAuth に切り替え
    - rollback: ``GitHelper.reset_hard(audit-round-N-pre タグ)`` のみ許可
    - dry_run: ファイル/コマンドを実行せず計画だけ返す
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_AUDIT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_AUDIT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_AUDIT))

from lib.git_helper import GitApplyError, GitHelper, GitHelperError  # noqa: E402

# fix_proposer.PatchCandidate を参照するが、循環や未生成を避け duck typing で扱う
# (auto_fix_loop からは PatchCandidate を渡すが、最低限 .diff / .risk_level を見れば良い)


# ============================================================================
# データクラス
# ============================================================================

@dataclass
class ApplyResult:
    applied: bool = False
    patch_path: Optional[str] = None
    error: Optional[str] = None


@dataclass
class CommitResult:
    committed: bool = False
    commit_hash: Optional[str] = None
    message: str = ""
    error: Optional[str] = None


@dataclass
class DeployResult:
    deployed: bool = False
    rc: int = -1
    stdout_tail: str = ""
    stderr_tail: str = ""
    duration_sec: float = 0.0
    error: Optional[str] = None
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RollbackResult:
    rolled_back: bool = False
    target_tag: str = ""
    re_deployed: bool = False
    deploy_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================================
# AutoApplier
# ============================================================================

DEFAULT_API_DIR = "api"
DEFAULT_WRANGLER_TOML = "wrangler.toml"
WRANGLER_BIN_DEFAULT = "npx"
WRANGLER_ARGS_DEFAULT = ["wrangler", "deploy", "--config", DEFAULT_WRANGLER_TOML]


class AutoApplier:
    """パッチ適用 → commit → deploy → (失敗時) rollback の窓口。

    Args:
        repo_root: リポジトリルート絶対パス。
        api_dir: ``cd`` してwranglerを叩くディレクトリ (デフォルト ``api``)。
        wrangler_args: 実行するwranglerコマンドの引数。デフォルト
            ``["wrangler", "deploy", "--config", "wrangler.toml"]``。
        dry_run: True なら実際のファイル/サブプロセスを呼ばずログだけ。
    """

    def __init__(
        self,
        repo_root: str | Path,
        api_dir: str = DEFAULT_API_DIR,
        wrangler_args: Optional[List[str]] = None,
        dry_run: bool = False,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.api_dir = self.repo_root / api_dir
        self.wrangler_args = list(wrangler_args or WRANGLER_ARGS_DEFAULT)
        self.dry_run = dry_run
        self.git = GitHelper(self.repo_root)

    # ------------------------------------------------------------------
    # 1. tag
    # ------------------------------------------------------------------

    def tag_pre_round(self, round_n: int) -> str:
        if self.dry_run:
            return f"audit-round-{round_n}-pre"
        return self.git.tag_pre_round(round_n)

    # ------------------------------------------------------------------
    # 2. apply
    # ------------------------------------------------------------------

    def apply_patch(self, patch: Any) -> ApplyResult:
        """``patch.diff`` を ``git apply`` で適用。

        ``patch`` は最低限以下を持っていればよい:
            - ``.diff`` (str)
            - ``.is_empty`` (bool, optional)
            - ``.pattern_id`` (str, optional)
        """
        diff_text = (getattr(patch, "diff", "") or "").strip()
        is_empty = bool(getattr(patch, "is_empty", False)) or not diff_text
        if is_empty:
            return ApplyResult(applied=False, error="empty_diff")

        if self.dry_run:
            return ApplyResult(applied=True, error="dry_run")

        try:
            # 事前 check で落とせれば no-op
            self.git.apply_diff_text(diff_text, check_only=True)
            self.git.apply_diff_text(diff_text, check_only=False)
            return ApplyResult(applied=True)
        except GitApplyError as e:
            return ApplyResult(applied=False, error=str(e))
        except GitHelperError as e:
            return ApplyResult(applied=False, error=f"git_error: {e}")

    # ------------------------------------------------------------------
    # 3. commit
    # ------------------------------------------------------------------

    def commit_changes(self, message: str, paths: Optional[List[str]] = None) -> CommitResult:
        """変更を commit。``paths`` 指定なし時は worker.js のみ add。"""
        if self.dry_run:
            return CommitResult(committed=True, message=message, commit_hash="DRYRUN")

        if not self.git.is_dirty():
            return CommitResult(committed=False, message=message, error="no_changes")

        try:
            target_paths = paths or ["api/worker.js"]
            # 存在するパスのみ add
            existing = [p for p in target_paths if (self.repo_root / p).exists()]
            self.git.add(existing)
            sha = self.git.commit(message)
            return CommitResult(committed=True, commit_hash=sha, message=message)
        except GitHelperError as e:
            return CommitResult(committed=False, message=message, error=str(e))

    # ------------------------------------------------------------------
    # 4. deploy
    # ------------------------------------------------------------------

    def deploy_worker(self, timeout: int = 240) -> DeployResult:
        """``cd api && unset CLOUDFLARE_API_TOKEN && npx wrangler deploy --config wrangler.toml``"""
        import time

        result = DeployResult(dry_run=self.dry_run)

        if self.dry_run:
            result.deployed = True
            result.rc = 0
            result.stdout_tail = (
                f"(dry-run) cd {self.api_dir} && "
                f"unset CLOUDFLARE_API_TOKEN && "
                f"{WRANGLER_BIN_DEFAULT} {' '.join(self.wrangler_args)}"
            )
            return result

        if not self.api_dir.exists():
            result.error = f"api_dir not found: {self.api_dir}"
            return result

        # wrangler.toml チェック
        cfg = self.api_dir / DEFAULT_WRANGLER_TOML
        if not cfg.exists():
            result.error = f"wrangler.toml not found: {cfg}"
            return result

        env = os.environ.copy()
        # MEMORY.md: CLOUDFLARE_API_TOKEN は権限不足 → unset で OAuth
        env.pop("CLOUDFLARE_API_TOKEN", None)

        cmd = [WRANGLER_BIN_DEFAULT] + self.wrangler_args
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.api_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result.rc = proc.returncode
            result.stdout_tail = (proc.stdout or "")[-1500:]
            result.stderr_tail = (proc.stderr or "")[-1500:]
            result.deployed = (proc.returncode == 0)
        except subprocess.TimeoutExpired:
            result.error = f"wrangler deploy timeout after {timeout}s"
        except FileNotFoundError as e:
            result.error = f"npx not found: {e}"
        except Exception as e:  # noqa: BLE001
            result.error = f"deploy exception: {e}"

        result.duration_sec = round(time.time() - t0, 2)
        return result

    # ------------------------------------------------------------------
    # 5. rollback
    # ------------------------------------------------------------------

    def rollback(self, to_tag: str, redeploy: bool = True) -> RollbackResult:
        """``audit-round-N-pre`` タグへ ``reset --hard`` し、必要なら再デプロイ。"""
        result = RollbackResult(target_tag=to_tag)

        if self.dry_run:
            result.rolled_back = True
            result.re_deployed = redeploy
            return result

        try:
            self.git.reset_hard(to_tag)
            result.rolled_back = True
        except GitHelperError as e:
            result.error = f"reset_hard failed: {e}"
            return result

        if redeploy:
            dep = self.deploy_worker()
            result.re_deployed = dep.deployed
            result.deploy_result = dep.to_dict()

        return result


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    import argparse

    p = argparse.ArgumentParser(description="Apply patch, commit, deploy, rollback")
    p.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    p.add_argument("--cmd", required=True,
                   choices=["tag", "apply", "deploy", "rollback", "status"])
    p.add_argument("--round", type=int, default=0)
    p.add_argument("--diff", default=None, help="apply対象 diff ファイル")
    p.add_argument("--message", default=None, help="commit メッセージ")
    p.add_argument("--tag", default=None, help="rollback先タグ")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    aa = AutoApplier(repo_root=args.repo_root, dry_run=args.dry_run)

    if args.cmd == "tag":
        if args.round <= 0:
            print("--round required", file=sys.stderr)
            return 1
        print(aa.tag_pre_round(args.round))
        return 0

    if args.cmd == "apply":
        if not args.diff:
            print("--diff required", file=sys.stderr)
            return 1
        diff_text = Path(args.diff).read_text(encoding="utf-8")

        class _Patch:
            pass
        patch = _Patch()
        patch.diff = diff_text  # type: ignore[attr-defined]
        patch.is_empty = not diff_text.strip()  # type: ignore[attr-defined]
        ar = aa.apply_patch(patch)
        print(json.dumps(asdict(ar), ensure_ascii=False, indent=2))
        if ar.applied and args.message:
            cr = aa.commit_changes(args.message)
            print(json.dumps(asdict(cr), ensure_ascii=False, indent=2))
        return 0 if ar.applied else 2

    if args.cmd == "deploy":
        dr = aa.deploy_worker()
        print(json.dumps(dr.to_dict(), ensure_ascii=False, indent=2))
        return 0 if dr.deployed else 2

    if args.cmd == "rollback":
        if not args.tag:
            print("--tag required", file=sys.stderr)
            return 1
        rr = aa.rollback(args.tag)
        print(json.dumps(asdict(rr), ensure_ascii=False, indent=2))
        return 0 if rr.rolled_back else 2

    if args.cmd == "status":
        print(json.dumps({
            "branch": aa.git.current_branch(),
            "head": aa.git.current_hash(),
            "dirty": aa.git.is_dirty(),
            "api_dir": str(aa.api_dir),
            "wrangler_args": aa.wrangler_args,
        }, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
