#!/usr/bin/env python3
"""
D1にバッチSQLを順次投入する（--file 認証エラー回避用）

OAuth scopeに r2 が無いため `--file` だとAuthentication error。
`--command` なら通るので、SQLを小バッチに分割してsubprocessで順次実行。

使い方:
  python3 scripts/d1_batch_invoke.py [--start-from N]
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = PROJECT_ROOT / "data" / "hellowork_jobs_d1_batches"
WRANGLER_CONFIG = PROJECT_ROOT / "api" / "wrangler.toml"
D1_DB_NAME = "nurse-robby-db"


def run_batch(sql_text, idx, total):
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)
    cmd = [
        "npx", "wrangler", "d1", "execute", D1_DB_NAME,
        "--config", str(WRANGLER_CONFIG),
        "--remote",
        "--command", sql_text,
    ]
    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT / "api"), env=env,
                            capture_output=True, text=True, timeout=180)
    dt = time.time() - t0
    if result.returncode != 0:
        print(f"  ❌ batch {idx}/{total} failed ({dt:.1f}s)")
        print(f"     stderr: {result.stderr[:500]}")
        return False
    print(f"  ✅ batch {idx}/{total} ({dt:.1f}s, {len(sql_text)} bytes)")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-from", type=int, default=0)
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args()

    files = sorted(BATCH_DIR.glob("batch_*.sql"))
    if not files:
        print(f"❌ バッチファイルが見つかりません: {BATCH_DIR}")
        sys.exit(1)
    # header.sql は別途実行済みなので除外

    print(f"📦 {len(files)}バッチ投入開始（start_from={args.start_from}）")
    success = 0
    failed = 0
    for i, f in enumerate(files):
        if i < args.start_from:
            continue
        sql = f.read_text()
        if run_batch(sql, i, len(files) - 1):
            success += 1
        else:
            failed += 1
            if args.stop_on_error:
                print(f"❌ stop-on-error: {f.name}")
                sys.exit(1)

    print(f"\n=== 完了 ===")
    print(f"成功: {success} / 失敗: {failed}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
