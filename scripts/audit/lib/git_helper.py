#!/usr/bin/env python3
"""
GitHelper — auto-fix loop が安全に commit / tag / rollback するための薄いラッパ

設計思想 (DESIGN.md §5):
    - Round N の入口で必ず ``audit-round-N-pre`` タグを打つ → 失敗時は確実にロールバック
    - パッチ適用は ``git apply`` を使う。**3-way / index 経由は使わない**
      (worker.js が並列に編集される可能性は無いので素のapplyで十分、競合時は明示エラー)
    - 破壊的操作 (reset --hard) は **`tag_pre_round` で打ったタグへのみ** 許可
      → MEMORY.md の Git Safety Protocol に従う

Auto-fix loop 専用なので CLI からの直叩きは想定しない。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


# ============================================================================
# 例外
# ============================================================================

class GitHelperError(Exception):
    """GitHelper 例外基底クラス"""


class GitApplyError(GitHelperError):
    """``git apply`` 失敗 (コンフリクト/不正なdiff)"""


class GitTagError(GitHelperError):
    """tag 作成 / 解決失敗"""


class GitResetError(GitHelperError):
    """reset --hard 失敗"""


# ============================================================================
# GitHelper
# ============================================================================

# auto-fix-loop が打つタグ名のホワイトリストパターン
SAFE_RESET_TAG_RE = re.compile(r"^audit-round-\d+-pre$")


class GitHelper:
    """auto-fix loop 専用の git ラッパ。

    Args:
        repo_root: リポジトリルートの絶対パス。省略時は CWD を遡って探索。

    使い方:
        >>> git = GitHelper("/Users/robby2/robby-the-match")
        >>> tag = git.tag_pre_round(3)        # → "audit-round-3-pre"
        >>> ok = git.apply_diff("/tmp/p.diff")
        >>> sha = git.commit("audit: round 3 fixes")
        >>> git.reset_hard(tag)               # smoke 失敗時のみ
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        if not (self.repo_root / ".git").exists():
            raise GitHelperError(f"not a git repo: {self.repo_root}")

    # ------------------------------------------------------------------
    # 内部 helper
    # ------------------------------------------------------------------

    def _run(
        self,
        args: List[str],
        check: bool = True,
        capture: bool = True,
        input_text: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        """``git ...`` を実行し ``(rc, stdout, stderr)`` を返す。"""
        cmd = ["git"] + args
        proc = subprocess.run(
            cmd,
            cwd=self.repo_root,
            capture_output=capture,
            text=True,
            input=input_text,
        )
        if check and proc.returncode != 0:
            raise GitHelperError(
                f"git {' '.join(args)} failed (rc={proc.returncode}): "
                f"{(proc.stderr or proc.stdout or '').strip()}"
            )
        return proc.returncode, (proc.stdout or ""), (proc.stderr or "")

    # ------------------------------------------------------------------
    # 状態確認
    # ------------------------------------------------------------------

    def current_hash(self) -> str:
        """``HEAD`` の commit hash (short)。"""
        _, out, _ = self._run(["rev-parse", "--short", "HEAD"])
        return out.strip()

    def current_branch(self) -> str:
        _, out, _ = self._run(["rev-parse", "--abbrev-ref", "HEAD"])
        return out.strip()

    def is_dirty(self) -> bool:
        """untracked + 変更ありなら True。"""
        _, out, _ = self._run(["status", "--porcelain"])
        return bool(out.strip())

    def changed_files(self) -> List[str]:
        """``HEAD`` 比較で変更されたファイル一覧 (staged/unstaged 両方)。"""
        _, out, _ = self._run(["diff", "--name-only", "HEAD"])
        return [line.strip() for line in out.splitlines() if line.strip()]

    # ------------------------------------------------------------------
    # tag
    # ------------------------------------------------------------------

    def tag(self, name: str, force: bool = False) -> str:
        """``HEAD`` にタグを打つ。"""
        args = ["tag"]
        if force:
            args.append("-f")
        args.append(name)
        self._run(args)
        return name

    def tag_pre_round(self, round_n: int) -> str:
        """auto-fix loop の Round N 開始時タグ。

        既存の同名タグがあれば force で上書き (リトライ対応)。
        """
        name = f"audit-round-{round_n}-pre"
        return self.tag(name, force=True)

    def tag_exists(self, name: str) -> bool:
        rc, _, _ = self._run(["rev-parse", "-q", "--verify", f"refs/tags/{name}"], check=False)
        return rc == 0

    # ------------------------------------------------------------------
    # apply / commit
    # ------------------------------------------------------------------

    def apply_diff(self, diff_path: str | Path, check_only: bool = False) -> bool:
        """unified diff ファイルを適用。

        Args:
            diff_path: diff ファイルの絶対パス。
            check_only: True なら ``--check`` で適用可能性のみ検査。

        Returns:
            ``True`` 成功。失敗時は ``GitApplyError``。
        """
        diff_path = Path(diff_path)
        if not diff_path.exists():
            raise GitApplyError(f"diff not found: {diff_path}")
        args = ["apply"]
        if check_only:
            args.append("--check")
        args.append(str(diff_path))
        rc, out, err = self._run(args, check=False)
        if rc != 0:
            raise GitApplyError(
                f"git apply{' --check' if check_only else ''} failed: "
                f"{(err or out).strip()[:500]}"
            )
        return True

    def apply_diff_text(self, diff_text: str, check_only: bool = False) -> bool:
        """diff 文字列を直接 ``git apply`` に流し込む。"""
        if not diff_text.strip():
            raise GitApplyError("empty diff")
        args = ["apply"]
        if check_only:
            args.append("--check")
        rc, out, err = self._run(args, check=False, input_text=diff_text)
        if rc != 0:
            raise GitApplyError(
                f"git apply (stdin){' --check' if check_only else ''} failed: "
                f"{(err or out).strip()[:500]}"
            )
        return True

    def add(self, paths: List[str]) -> None:
        if not paths:
            return
        # MEMORY.md ルール: -A や . は使わない。明示的にパス指定
        self._run(["add", "--"] + paths)

    def commit(self, message: str, allow_empty: bool = False) -> str:
        """``git commit -m message``。 commit hash を返す。"""
        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self._run(args)
        return self.current_hash()

    # ------------------------------------------------------------------
    # rollback
    # ------------------------------------------------------------------

    def reset_hard(self, target: str) -> None:
        """**安全装置付き** ``git reset --hard``。

        - ``audit-round-N-pre`` パターンのタグまたは 7+桁hex commit hash のみ受け付ける
        - それ以外は ``GitResetError``。

        この制約により main や HEAD~1 への暴発を防ぐ。
        """
        if not (SAFE_RESET_TAG_RE.match(target) or re.match(r"^[0-9a-f]{7,40}$", target)):
            raise GitResetError(
                f"unsafe reset target: {target!r} "
                "(only 'audit-round-N-pre' tags or commit hashes allowed)"
            )
        if SAFE_RESET_TAG_RE.match(target) and not self.tag_exists(target):
            raise GitResetError(f"tag not found: {target}")
        self._run(["reset", "--hard", target])


# ============================================================================
# CLI 動作確認
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    p = argparse.ArgumentParser(description="GitHelper smoke test")
    p.add_argument("--repo", default=".")
    p.add_argument("--cmd", choices=["status", "tag-round", "current"], default="status")
    p.add_argument("--round", type=int, default=0)
    args = p.parse_args()

    g = GitHelper(args.repo)
    if args.cmd == "status":
        print(json.dumps({
            "branch": g.current_branch(),
            "head": g.current_hash(),
            "dirty": g.is_dirty(),
            "changed": g.changed_files(),
        }, ensure_ascii=False, indent=2))
    elif args.cmd == "current":
        print(g.current_hash())
    elif args.cmd == "tag-round":
        print(g.tag_pre_round(args.round))
