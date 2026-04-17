#!/usr/bin/env python3
"""
content/generated/ アーカイブ（Phase 3 #61） v1.0

30日以上前の content/generated/ サブディレクトリ（SNS素材の生成成果物）を
content/archive/YYYY-MM/ に移動して .tar.gz 圧縮する。

背景: content/generated/ は ~530MB。古い PNG/MP4/JSON を残しても価値は低い。
      重要: 「投稿キューから消すこと」はしない。posting_queue.json は触らない。
           あくまで生成済み素材ディレクトリの圧縮・移動のみ。

cron: 月初1日 03:00
  0 3 1 * * cd ~/robby-the-match && python3 scripts/archive_generated.py --cron

Safety:
  - dry-run モード標準: `python3 scripts/archive_generated.py --dry-run`
  - 実行: `python3 scripts/archive_generated.py --apply`
  - posting_queue.json の `posted` 状態でも、物理的には移動するだけなので
    参照が生きていても .tar.gz を展開すれば復元可能。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
GENERATED_DIR = PROJECT_ROOT / "content" / "generated"
ARCHIVE_ROOT = PROJECT_ROOT / "content" / "archive"
DEFAULT_DAYS = 30

# ディレクトリ名の日付を拾うパターン: 20260220_A01 等（先頭 YYYYMMDD）
DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})[_\-]")


def dir_date(name: str) -> datetime | None:
    m = DATE_RE.match(name)
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def iter_candidates(cutoff: datetime):
    """cutoff より古いサブディレクトリを列挙する。"""
    if not GENERATED_DIR.exists():
        return
    for p in sorted(GENERATED_DIR.iterdir()):
        if not p.is_dir():
            continue
        d = dir_date(p.name)
        if d is None:
            # 日付が判定できないディレクトリは mtime で判定
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime >= cutoff:
                continue
            d = mtime
        if d < cutoff:
            yield p, d


def archive_one(path: Path, ymd: datetime, apply: bool) -> dict:
    """対象ディレクトリを content/archive/YYYY-MM/ に .tar.gz 化する。
    return: 実行結果メタ（実apply=False の場合はシミュレーション）
    """
    month_key = ymd.strftime("%Y-%m")
    out_dir = ARCHIVE_ROOT / month_key
    out_path = out_dir / f"{path.name}.tar.gz"

    size_before = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    meta = {
        "name": path.name,
        "ymd": ymd.strftime("%Y-%m-%d"),
        "month": month_key,
        "dir_size_bytes": size_before,
        "tar_path": str(out_path.relative_to(PROJECT_ROOT)),
        "applied": apply,
    }
    if not apply:
        return meta

    out_dir.mkdir(parents=True, exist_ok=True)
    # 既に同名のtar.gzがあればスキップ（再実行安全）
    if out_path.exists():
        meta["skipped"] = "tar_already_exists"
        shutil.rmtree(path)
        return meta

    with tarfile.open(out_path, "w:gz") as tar:
        tar.add(path, arcname=path.name)
    # 圧縮成功 → 元ディレクトリ削除
    shutil.rmtree(path)
    meta["tar_size_bytes"] = out_path.stat().st_size
    return meta


def main() -> int:
    p = argparse.ArgumentParser(description="content/generated/ 月次アーカイブ")
    p.add_argument("--days", type=int, default=DEFAULT_DAYS,
                   help=f"この日数より古いものをアーカイブ (default={DEFAULT_DAYS})")
    p.add_argument("--apply", action="store_true", help="実際に移動・圧縮する")
    p.add_argument("--dry-run", action="store_true", help="シミュレーションのみ")
    p.add_argument("--cron", action="store_true", help="cron用: applyモード+Slack通知")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()

    apply = args.apply or args.cron
    if args.dry_run:
        apply = False

    cutoff = datetime.now() - timedelta(days=args.days)
    cands = list(iter_candidates(cutoff))

    results = []
    total_freed = 0
    for d, ymd in cands:
        try:
            meta = archive_one(d, ymd, apply)
            results.append(meta)
            if meta.get("applied"):
                total_freed += meta.get("dir_size_bytes", 0)
            if args.verbose:
                print(json.dumps(meta, ensure_ascii=False))
        except Exception as e:
            results.append({"name": d.name, "error": str(e)})

    summary = {
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "apply" if apply else "dry-run",
        "cutoff_days": args.days,
        "candidates": len(cands),
        "applied": sum(1 for r in results if r.get("applied")),
        "freed_bytes_approx": total_freed,
        "results": results,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.cron:
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
            from slack_utils import send_message, SLACK_CHANNEL_REPORT  # type: ignore
            mb = summary["freed_bytes_approx"] / 1024 / 1024
            send_message(
                SLACK_CHANNEL_REPORT,
                f"🗂 content/generated/ 月次アーカイブ: "
                f"{summary['applied']}ディレクトリを .tar.gz 化 "
                f"(≈ {mb:.1f} MB 解放)",
            )
        except Exception as e:
            sys.stderr.write(f"Slack通知失敗: {e}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
