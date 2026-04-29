#!/usr/bin/env python3
"""
verify_chain.py — 監査ログ整合性検証 (cron 毎時実行用)

【使い方】
    # 今日のログを検証
    python3 scripts/audit/verify_chain.py --since today

    # 特定日付
    python3 scripts/audit/verify_chain.py --date 2026-04-29

    # 任意ディレクトリ
    python3 scripts/audit/verify_chain.py --log-dir logs/audit/2026-04-29

    # Slack通知をdry-run
    python3 scripts/audit/verify_chain.py --since today --no-slack

【cron 例（毎時 :05）】
    5 * * * * cd ~/robby-the-match && /usr/bin/env python3 \
        scripts/audit/verify_chain.py --since today >> logs/audit/cron.log 2>&1

【動作】
- ChainLogger.verify_chain() を実行
- ok=True → silent (cron運用のためstdout最小)
- ok=False → Slack #claudecode に 🚨 通知 + exit 1
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

# パス解決: scripts/audit/verify_chain.py から見て repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.audit.lib.chain_logger import ChainLogger, ChainLoggerError  # noqa: E402


DEFAULT_LOG_BASE = REPO_ROOT / "logs" / "audit"
SLACK_BRIDGE = REPO_ROOT / "scripts" / "slack_bridge.py"


def _resolve_log_dir(args: argparse.Namespace) -> Path:
    if args.log_dir:
        return Path(args.log_dir).expanduser()
    if args.date:
        return DEFAULT_LOG_BASE / args.date
    if args.since == "today":
        today = date.today().isoformat()
        return DEFAULT_LOG_BASE / today
    raise SystemExit("provide one of --since today / --date / --log-dir")


def _slack_notify(message: str) -> None:
    """Slack通知。slack_bridge.py が無ければ stderr にfallback。"""
    if not SLACK_BRIDGE.exists():
        print(f"[no-slack-bridge] {message}", file=sys.stderr)
        return
    try:
        subprocess.run(
            ["python3", str(SLACK_BRIDGE), "--send", message],
            check=False,
            timeout=15,
            capture_output=True,
        )
    except Exception as e:
        print(f"[slack notify failed] {e}: {message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ChainLogger 整合性検証 (cron用)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--since", choices=["today"], help="本日のログを検証")
    parser.add_argument("--date", help="検証対象日 (YYYY-MM-DD)")
    parser.add_argument("--log-dir", help="ログディレクトリを直接指定")
    parser.add_argument(
        "--no-slack", action="store_true", help="Slack通知を抑止 (dry-run)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="正常時もstdoutに結果出力"
    )
    parser.add_argument(
        "--priv-key", help="Ed25519私有鍵パス (省略時 ~/.config/audit/ed25519_priv.pem)"
    )
    parser.add_argument(
        "--pub-key", help="Ed25519公開鍵パス (省略時 ~/.config/audit/ed25519_pub.pem)"
    )
    args = parser.parse_args()

    if not (args.since or args.date or args.log_dir):
        parser.print_help()
        return 2

    log_dir = _resolve_log_dir(args)

    if not log_dir.exists() or not (log_dir / "chain.jsonl").exists():
        if args.verbose:
            print(f"[skip] no chain.jsonl in {log_dir}")
        return 0  # ログがまだ無いのは正常

    try:
        logger = ChainLogger(
            log_dir,
            private_key_path=args.priv_key,
            public_key_path=args.pub_key,
            auto_generate_key=False,
        )
        result = logger.verify_chain()
    except ChainLoggerError as e:
        msg = f"🚨 audit chain verify failed (init): {log_dir}\n{e}"
        if not args.no_slack:
            _slack_notify(msg)
        print(msg, file=sys.stderr)
        return 1

    if result["ok"]:
        if args.verbose:
            print(
                f"[ok] {log_dir} verified: total={result['total']} latest={logger.latest_hash()[:12]}..."
            )
        return 0

    msg = (
        f"🚨 *audit chain BROKEN* — {log_dir.name}\n"
        f"• broken_at seq: {result['broken_at']}\n"
        f"• reason: {result['reason']}\n"
        f"• total: {result['total']}\n"
        f"• checked_at: {datetime.utcnow().isoformat()}Z"
    )
    if not args.no_slack:
        _slack_notify(msg)
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
