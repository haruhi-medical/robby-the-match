#!/usr/bin/env python3
"""
#51 Phase 3: LINE Bot フェーズ遷移 週次レポート

Worker が D1 phase_transitions に書き込んだ遷移ログを週次で集計し Slack 送信。
- どの phase で離脱が多いか（遷移元の件数 vs 遷移先が同一のまま＝離脱とみなす）
- ファネルステージ別の流入/流出比率
- 温度帯別（urgency）の進行

wrangler d1 execute で SELECT を実行し、結果を JSON で受け取って整形。

実行:
  python3 scripts/phase_transition_weekly_report.py [--days 7]
cron 推奨: 日曜 09:30 JST
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_DIR = PROJECT_ROOT / "api"
D1_NAME = "nurse-robby-db"

# ファネルステージ分類（監査 DESIGN.md と整合）
STAGE_MAP = {
    "onboarding": {"welcome", "follow"},
    "intake":     {"il_area", "il_subarea", "il_facility_type", "il_workstyle", "il_urgency", "il_department"},
    "matching":   {"matching_preview", "matching_browse", "matching", "condition_change"},
    "detour":     {"info_detour"},
    "ai_consult": {"ai_consultation", "ai_consultation_waiting", "ai_consultation_reply", "ai_consultation_extend"},
    "apply":      {"apply_info", "apply_consent", "apply_confirm", "career_sheet", "interview_prep"},
    "handoff":    {"handoff", "handoff_silent", "handoff_phone_check", "handoff_phone_time", "handoff_phone_number"},
    "nurture":    {"nurture_warm", "nurture_subscribed", "nurture_stay", "area_notify_optin"},
    "faq":        {"faq_salary", "faq_nightshift", "faq_timing", "faq_stealth", "faq_holiday"},
}


def _phase_to_stage(phase: str | None) -> str:
    if not phase:
        return "unknown"
    for stage, phases in STAGE_MAP.items():
        if phase in phases:
            return stage
    return "other"


def run_d1_query(sql: str) -> list[dict]:
    """wrangler d1 execute --remote --json で SELECT 結果を取得。"""
    env = {**os.environ}
    # CLOUDFLARE_API_TOKEN は権限不足で失敗することがあるため unset（deploy_worker.sh と同様）
    env.pop("CLOUDFLARE_API_TOKEN", None)

    result = subprocess.run(
        [
            "npx", "wrangler", "d1", "execute", D1_NAME,
            "--command", sql,
            "--remote",
            "--json",
            "--config", "wrangler.toml",
        ],
        cwd=str(API_DIR),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "")[-500:]
        print(f"[WARN] wrangler d1 execute failed: {stderr}", file=sys.stderr)
        return []

    try:
        parsed = json.loads(result.stdout or "[]")
        # 形式: [{"results": [ ... ]}] または {"results": [...]}]
        if isinstance(parsed, list) and parsed:
            first = parsed[0]
            if isinstance(first, dict) and "results" in first:
                return first["results"] or []
            # 古い形式: そのまま list of rows
            return parsed
        if isinstance(parsed, dict) and "results" in parsed:
            return parsed["results"] or []
    except json.JSONDecodeError:
        print(f"[WARN] JSON decode error from wrangler d1 execute", file=sys.stderr)

    return []


def aggregate(rows: list[dict]) -> dict:
    total = len(rows)
    unique_users = len({r.get("user_hash") for r in rows if r.get("user_hash")})

    next_phase_counter = Counter()
    prev_phase_counter = Counter()
    edge_counter = Counter()  # (prev, next) エッジ
    stage_in = Counter()
    stage_out = Counter()
    urgency_counter = Counter()
    source_counter = Counter()

    # ユーザー最終phase（離脱推定用）
    last_phase_per_user: dict[str, tuple[str, str]] = {}
    for r in rows:
        uh = r.get("user_hash")
        ts = r.get("created_at") or ""
        np = r.get("next_phase")
        pp = r.get("prev_phase")
        if np:
            next_phase_counter[np] += 1
            stage_in[_phase_to_stage(np)] += 1
        if pp:
            prev_phase_counter[pp] += 1
            stage_out[_phase_to_stage(pp)] += 1
        if pp and np:
            edge_counter[(pp, np)] += 1
        if r.get("urgency"):
            urgency_counter[r["urgency"]] += 1
        if r.get("source"):
            source_counter[r["source"]] += 1
        if uh:
            prev = last_phase_per_user.get(uh)
            if not prev or ts > prev[1]:
                last_phase_per_user[uh] = (np or "", ts)

    abandon_phases = Counter()
    for uh, (last_phase, _) in last_phase_per_user.items():
        if last_phase:
            abandon_phases[last_phase] += 1

    return {
        "total_transitions": total,
        "unique_users": unique_users,
        "top_next_phases": next_phase_counter.most_common(10),
        "top_prev_phases": prev_phase_counter.most_common(10),
        "top_edges": edge_counter.most_common(15),
        "stage_in": dict(stage_in),
        "stage_out": dict(stage_out),
        "top_abandon_phases": abandon_phases.most_common(10),
        "urgency_counts": dict(urgency_counter),
        "source_counts": dict(source_counter),
    }


def format_slack_text(summary: dict, days: int) -> str:
    lines = []
    lines.append(f"*📊 LINE Bot フェーズ遷移 週次レポート（過去{days}日）*")
    lines.append("")
    lines.append(f"*概要*")
    lines.append(f"• 遷移イベント総数: `{summary['total_transitions']:,}` 件")
    lines.append(f"• ユニーク参加ユーザー: `{summary['unique_users']:,}` 人")
    lines.append("")

    if summary["stage_in"]:
        lines.append("*ステージ別 流入*")
        for stage, cnt in sorted(summary["stage_in"].items(), key=lambda x: -x[1]):
            lines.append(f"• {stage}: `{cnt:,}`")
        lines.append("")

    if summary["top_abandon_phases"]:
        lines.append("*離脱（最後のphaseトップ10）*")
        for phase, cnt in summary["top_abandon_phases"]:
            lines.append(f"• `{phase}`: {cnt:,} 人 最後で停止")
        lines.append("")

    if summary["top_edges"]:
        lines.append("*遷移エッジ（prev → next, トップ15）*")
        for (prev, nxt), cnt in summary["top_edges"]:
            lines.append(f"• `{prev or '∅'}` → `{nxt}`: {cnt:,}")
        lines.append("")

    if summary["urgency_counts"]:
        lines.append("*温度帯（urgency）*")
        for urg, cnt in summary["urgency_counts"].items():
            lines.append(f"• {urg}: `{cnt:,}`")
        lines.append("")

    if summary["source_counts"]:
        lines.append("*流入元（welcomeSource）*")
        for src, cnt in summary["source_counts"].items():
            lines.append(f"• {src}: `{cnt:,}`")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="集計対象の日数（デフォルト7日）")
    parser.add_argument("--dry-run", action="store_true", help="Slack送信せずローカル出力のみ")
    parser.add_argument("--output", type=str, default="", help="レポートJSONを書き出すパス（任意）")
    args = parser.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    # SELECT（SQL文字列注入は固定値のためリスクなし）
    sql = (
        "SELECT user_hash, prev_phase, next_phase, event_type, area, prefecture, "
        "urgency, work_style, facility_type, source, created_at "
        f"FROM phase_transitions WHERE created_at >= '{since}' ORDER BY created_at ASC"
    )

    print(f"[Info] Querying phase_transitions since {since}")
    rows = run_d1_query(sql)
    print(f"[Info] Retrieved {len(rows)} rows")

    summary = aggregate(rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2)[:2000])

    slack_text = format_slack_text(summary, args.days)

    if args.output:
        try:
            Path(args.output).write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"[Info] Wrote summary to {args.output}")
        except Exception as e:
            print(f"[WARN] Failed to write summary: {e}", file=sys.stderr)

    if args.dry_run:
        print("---SLACK PAYLOAD (dry-run)---")
        print(slack_text)
        return 0

    # Slack 送信（slack_utils の send_message を利用）
    try:
        from slack_utils import send_message, SLACK_CHANNEL_REPORT
    except ImportError:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from slack_utils import send_message, SLACK_CHANNEL_REPORT

    res = send_message(SLACK_CHANNEL_REPORT, slack_text)
    if not res or not res.get("ok"):
        print(f"[WARN] Slack send failed: {res}", file=sys.stderr)
        return 1
    print(f"[Info] Sent Slack report (ts={res.get('ts')})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
