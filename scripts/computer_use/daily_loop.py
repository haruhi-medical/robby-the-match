#!/usr/bin/env python3
"""
日次メトリクス収集→判定→Slack報告ループ。

Usage:
  python3 scripts/computer_use/daily_loop.py phase1   # API取得
  python3 scripts/computer_use/daily_loop.py phase3   # 統合・判定・報告
  python3 scripts/computer_use/daily_loop.py full      # 全フェーズ
"""
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
METRICS_DIR = ROOT / "data" / "metrics"
TODAY = datetime.now().strftime("%Y%m%d")
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

def run_script(script_path, *args):
    try:
        result = subprocess.run(
            ["python3", str(ROOT / script_path)] + list(args),
            capture_output=True, text=True, timeout=120, cwd=str(ROOT)
        )
        return result.returncode == 0, result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)

def phase1_api_collection():
    scripts = {
        "tiktok": ("scripts/tiktok_analytics.py",),
        "ga4": ("scripts/ga4_report.py",),
        "meta": ("scripts/meta_ads_report.py",),
    }

    failed = []
    for platform, cmd in scripts.items():
        ok, output = run_script(*cmd)
        status = "✅" if ok else "❌"
        print(f"  {status} {platform}")
        if not ok:
            failed.append(platform)

    if failed:
        print(f"\n⚠️ Computer Use フォールバック対象: {', '.join(failed)}")
    else:
        print("\n✅ 全API取得成功")
    return failed

def phase3_report():
    METRICS_DIR.mkdir(parents=True, exist_ok=True)

    today_data = {}
    for f in METRICS_DIR.glob(f"*_{TODAY}.json"):
        platform = f.stem.replace(f"_{TODAY}", "")
        try:
            today_data[platform] = json.loads(f.read_text())
        except json.JSONDecodeError:
            pass

    report = [f"📊 日次メトリクス（{datetime.now().strftime('%m/%d')}）", "─" * 20]
    for platform, data in today_data.items():
        source = " 🖥️" if data.get("source") == "computer_use" else ""
        report.append(f"{platform}{source}: {json.dumps(data, ensure_ascii=False)[:100]}")

    print("\n".join(report))
    return "\n".join(report)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "full"

    if cmd == "phase1":
        phase1_api_collection()
    elif cmd == "phase3":
        phase3_report()
    elif cmd == "full":
        print("Phase 1: API取得")
        failed = phase1_api_collection()
        if not failed:
            print("\nPhase 3: 報告")
            phase3_report()
        else:
            print(f"\nPhase 2必要: {', '.join(failed)} → Computer Useで取得してから phase3 実行")
