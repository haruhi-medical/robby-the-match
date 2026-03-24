#!/usr/bin/env python3
"""
hellowork_diff.py — ハローワーク求人 日次差分分析
前日データと比較して新着・終了・変動をSlack報告する。

Usage:
  python3 scripts/hellowork_diff.py              # 差分分析 + Slack送信
  python3 scripts/hellowork_diff.py --dry-run     # 分析のみ（送信しない）
  python3 scripts/hellowork_diff.py --days 7      # 7日間のトレンド表示
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
HISTORY_DIR = DATA_DIR / "hellowork_history"
CURRENT_FILE = DATA_DIR / "hellowork_nurse_jobs.json"
RANKED_FILE = DATA_DIR / "hellowork_ranked.json"

sys.path.insert(0, str(PROJECT_DIR / "scripts"))
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_DIR / ".env")
except ImportError:
    pass

try:
    from slack_utils import send_message, SLACK_CHANNEL_REPORT
except ImportError:
    SLACK_CHANNEL_REPORT = os.getenv("SLACK_CHANNEL_ID", "")
    def send_message(ch, text, **kw):
        print(f"[Slack stub] {text[:200]}")


def save_snapshot():
    """現在のデータをhistoryに日次スナップショットとして保存"""
    if not CURRENT_FILE.exists():
        print("⚠️ hellowork_nurse_jobs.json が存在しません")
        return None

    data = json.loads(CURRENT_FILE.read_text())
    jobs = data.get("jobs", [])
    if not jobs:
        print("⚠️ 求人データが空です")
        return None

    today = datetime.now().strftime("%Y-%m-%d")
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    # 全フィールド保存（新着の詳細表示に使う）
    snapshot = {
        "date": today,
        "fetched_at": data.get("fetched_at", ""),
        "total_all": data.get("total_all", 0),
        "total_nurse": len(jobs),
        "jobs": jobs,  # 全フィールドそのまま保存
    }

    snapshot_file = HISTORY_DIR / f"{today}.json"
    snapshot_file.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2))
    print(f"📸 スナップショット保存: {snapshot_file} ({len(jobs)}件)")
    return snapshot


def load_snapshot(date_str):
    """指定日のスナップショットを読み込み"""
    f = HISTORY_DIR / f"{date_str}.json"
    if f.exists():
        return json.loads(f.read_text())
    return None


def find_previous_snapshot(before_date=None):
    """直前のスナップショットを探す"""
    if before_date is None:
        before_date = datetime.now().strftime("%Y-%m-%d")

    for i in range(1, 30):
        d = (datetime.strptime(before_date, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
        snap = load_snapshot(d)
        if snap:
            return snap
    return None


def diff_snapshots(today, yesterday):
    """2つのスナップショットを比較して差分を返す"""
    today_kjnos = {j["kjno"] for j in today["jobs"]}
    yesterday_kjnos = {j["kjno"] for j in yesterday["jobs"]}

    new_kjnos = today_kjnos - yesterday_kjnos
    removed_kjnos = yesterday_kjnos - today_kjnos
    continuing_kjnos = today_kjnos & yesterday_kjnos

    today_map = {j["kjno"]: j for j in today["jobs"]}
    yesterday_map = {j["kjno"]: j for j in yesterday["jobs"]}

    new_jobs = [today_map[k] for k in new_kjnos]
    removed_jobs = [yesterday_map[k] for k in removed_kjnos]

    # エリア別集計
    def area_counts(jobs):
        areas = {}
        for j in jobs:
            loc = j.get("work_location", "不明")
            city = loc.replace("神奈川県", "") if "神奈川" in loc else loc
            for suffix in ["市", "区", "町", "村"]:
                idx = city.find(suffix)
                if idx >= 0:
                    city = city[:idx + 1]
                    break
            areas[city] = areas.get(city, 0) + 1
        return areas

    return {
        "today_date": today["date"],
        "yesterday_date": yesterday["date"],
        "today_total": len(today_kjnos),
        "yesterday_total": len(yesterday_kjnos),
        "new_count": len(new_kjnos),
        "removed_count": len(removed_kjnos),
        "continuing_count": len(continuing_kjnos),
        "new_jobs": sorted(new_jobs, key=lambda x: x.get("employer", ""))[:20],
        "removed_jobs": sorted(removed_jobs, key=lambda x: x.get("employer", ""))[:20],
        "new_areas": area_counts(new_jobs),
        "removed_areas": area_counts(removed_jobs),
        "total_areas": area_counts(today["jobs"]),
    }


def _format_salary(j):
    """給与をフォーマット"""
    low = j.get("salary_low", "")
    high = j.get("salary_high", "")
    form = j.get("salary_form", "")
    text = j.get("salary_text", "")
    if low and high:
        try:
            return f"{int(low):,}〜{int(high):,}円（{form}）"
        except ValueError:
            pass
    if text:
        return text
    if low:
        try:
            return f"{int(low):,}円〜（{form}）"
        except ValueError:
            return low
    return "記載なし"


def _format_job_detail(j):
    """1求人の全詳細をSlack表示用に整形"""
    lines = []
    emp = j.get("employer", "不明")
    title = j.get("job_title", j.get("sksu", ""))
    kjno = j.get("kjno", "")

    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"*🏥 {emp}*")
    hw_url = f"https://www.hellowork.mhlw.go.jp/kensaku/GECA110010.do?screenId=GECA110010&action=kyujinNoSearch&kjNo={kjno}" if kjno else ""
    kjno_text = f"<{hw_url}|{kjno}>" if hw_url else kjno
    lines.append(f"*職種:* {title}　|　*求人番号:* {kjno_text}")

    # 勤務地
    loc = j.get("work_location", "")
    addr = j.get("work_address", "")
    station = j.get("work_station_text", "")
    loc_parts = [loc or addr]
    if station:
        loc_parts.append(f"🚃{station}")
    lines.append(f"*勤務地:* {' / '.join(filter(None, loc_parts))}")

    # 雇用形態
    emp_type = j.get("employment_type", "")
    full_part = j.get("full_part", "")
    permanent = j.get("permanent_hire", "")
    emp_parts = [emp_type, full_part]
    if permanent and "あり" in permanent:
        emp_parts.append("正社員登用あり")
    lines.append(f"*雇用形態:* {' / '.join(filter(None, emp_parts))}")

    # 給与
    lines.append(f"*給与:* {_format_salary(j)}")
    bonus = j.get("bonus", "")
    bonus_detail = j.get("bonus_detail", "")
    if bonus:
        lines.append(f"*賞与:* {bonus} {bonus_detail}".strip())
    raise_info = j.get("raise", "")
    if raise_info:
        lines.append(f"*昇給:* {raise_info}")

    # 勤務時間
    shifts = []
    for key in ["shift1", "shift2", "shift3"]:
        s = j.get(key, "")
        if s:
            shifts.append(s)
    if shifts:
        lines.append(f"*勤務時間:* {' / '.join(shifts)}")
    overtime = j.get("overtime", "")
    overtime_avg = j.get("overtime_avg", "")
    if overtime:
        ot_text = overtime
        if overtime_avg:
            ot_text += f"（月平均{overtime_avg}）"
        lines.append(f"*残業:* {ot_text}")

    # 休日
    holidays = j.get("holidays", "")
    annual = j.get("annual_holidays", "")
    weekdays = j.get("weekdays_off", "")
    hol_parts = []
    if annual:
        hol_parts.append(f"年間{annual}日")
    if weekdays:
        hol_parts.append(weekdays)
    if holidays:
        hol_parts.append(holidays[:40])
    if hol_parts:
        lines.append(f"*休日:* {' / '.join(hol_parts)}")

    # 資格
    licenses = [j.get(f"license{i}", "") for i in range(1, 4)]
    licenses = [l for l in licenses if l]
    if licenses:
        lines.append(f"*必要資格:* {', '.join(licenses)}")

    # 仕事内容
    desc = j.get("job_description", "")
    if desc:
        # 長すぎる場合は切り詰め
        if len(desc) > 200:
            desc = desc[:200] + "..."
        lines.append(f"*仕事内容:* {desc}")

    # 福利厚生
    benefits = []
    ins = j.get("insurance", "")
    if ins:
        benefits.append(f"保険:{ins}")
    ret = j.get("retirement", "")
    if ret and "あり" in ret:
        benefits.append("退職金あり")
    child = j.get("childcare", "")
    if child and "あり" in child:
        benefits.append("託児所あり")
    car = j.get("car_commute", "")
    if car and "可" in car:
        benefits.append("マイカー通勤可")
    if benefits:
        lines.append(f"*福利厚生:* {' / '.join(benefits)}")

    # HP
    url = j.get("employer_url", "")
    if url:
        lines.append(f"*HP:* {url}")

    # 受付日・有効期限
    ukt = j.get("uktkymd", "")
    yuko = j.get("kjyukoymd", "")
    if ukt or yuko:
        lines.append(f"*受付:* {ukt}　*期限:* {yuko}")

    return lines


def format_slack_report(diff, ranked_data=None):
    """Slack Block Kit形式のレポートを生成"""
    d = diff
    delta = d["today_total"] - d["yesterday_total"]
    delta_str = f"+{delta}" if delta > 0 else str(delta)
    emoji = "📈" if delta > 0 else ("📉" if delta < 0 else "➡️")

    lines = [
        f"*🏥 ハローワーク求人レポート {d['today_date']}*",
        f"",
        f"*総数:* {d['today_total']}件 ({delta_str}) {emoji}",
        f"*新着:* {d['new_count']}件 | *終了:* {d['removed_count']}件 | *継続:* {d['continuing_count']}件",
    ]

    # 新着求人（10件まで全詳細、それ以上はサマリ）
    MAX_DETAIL = 10
    if d["new_jobs"]:
        lines.append("")
        lines.append(f"*🆕 新着求人（{d['new_count']}件）*")
        for j in d["new_jobs"][:MAX_DETAIL]:
            lines.extend(_format_job_detail(j))
            lines.append("")
        if d["new_count"] > MAX_DETAIL:
            lines.append(f"*...他{d['new_count'] - MAX_DETAIL}件（詳細はdata/hellowork_history参照）*")
            # 残りは1行サマリで表示
            for j in d["new_jobs"][MAX_DETAIL:30]:
                loc = j.get("work_location", "").replace("神奈川県", "")[:10]
                sal = ""
                if j.get("salary_low"):
                    try:
                        sal = f" {int(j['salary_low']):,}円〜"
                    except ValueError:
                        pass
                lines.append(f"  • {j.get('employer', '?')[:25]} ({loc}){sal}")
            if d["new_count"] > 30:
                lines.append(f"  ...他{d['new_count'] - 30}件")

    # 終了求人
    if d["removed_jobs"]:
        lines.append("")
        lines.append(f"*🔚 終了求人（{d['removed_count']}件）*")
        for j in d["removed_jobs"][:10]:
            loc = j.get("work_location", "").replace("神奈川県", "")
            lines.append(f"  • {j.get('employer', '?')[:30]} ({loc[:15]})")
        if d["removed_count"] > 10:
            lines.append(f"  ...他{d['removed_count'] - 10}件")

    # エリア別新着
    if d["new_areas"]:
        lines.append("")
        lines.append("*📍 新着エリア別*")
        for area, cnt in sorted(d["new_areas"].items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {area}: {cnt}件")

    # ランク情報
    if ranked_data:
        rc = ranked_data.get("rank_counts", {})
        if rc:
            lines.append("")
            lines.append(f"*⭐ ランク分布:* S:{rc.get('S',0)} A:{rc.get('A',0)} B:{rc.get('B',0)} C:{rc.get('C',0)}")

    return "\n".join(lines)


def _split_report(report, max_len=2800):
    """長いレポートを区切り線で分割"""
    sections = report.split("━━━━━━━━━━━━━━━━━━━━")
    if len(sections) <= 1:
        # 区切り線がない場合は行数で分割
        lines = report.split("\n")
        chunks = []
        current = []
        for line in lines:
            current.append(line)
            if len("\n".join(current)) > max_len:
                chunks.append("\n".join(current))
                current = []
        if current:
            chunks.append("\n".join(current))
        return chunks

    # 最初のセクション（サマリ）は必ず含める
    chunks = [sections[0]]
    current = ""
    for section in sections[1:]:
        candidate = current + "━━━━━━━━━━━━━━━━━━━━" + section
        if len(candidate) > max_len and current:
            chunks.append(current)
            current = "━━━━━━━━━━━━━━━━━━━━" + section
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def trend_report(days=7):
    """直近N日間のトレンドを表示"""
    today = datetime.now()
    records = []
    for i in range(days):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        snap = load_snapshot(d)
        if snap:
            records.append((d, snap["total_nurse"]))

    if not records:
        print("📊 トレンドデータなし（スナップショットが未蓄積）")
        return

    print(f"\n📊 直近{days}日間トレンド")
    print("-" * 40)
    for date, count in reversed(records):
        bar = "█" * (count // 50)
        print(f"  {date}: {count:>5}件 {bar}")
    if len(records) >= 2:
        first = records[-1][1]
        last = records[0][1]
        delta = last - first
        print(f"\n  変動: {first} → {last} ({'+' if delta >= 0 else ''}{delta})")


def main():
    parser = argparse.ArgumentParser(description="ハローワーク求人 日次差分分析")
    parser.add_argument("--dry-run", action="store_true", help="Slack送信しない")
    parser.add_argument("--days", type=int, default=0, help="トレンド表示（日数指定）")
    parser.add_argument("--no-save", action="store_true", help="スナップショットを保存しない")
    args = parser.parse_args()

    if args.days > 0:
        trend_report(args.days)
        return

    # Step 1: 今日のスナップショット保存
    if not args.no_save:
        today_snap = save_snapshot()
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_snap = load_snapshot(today_str)

    if not today_snap:
        print("❌ 今日のデータがありません")
        sys.exit(1)

    # Step 2: 前回のスナップショットを探す
    prev_snap = find_previous_snapshot(today_snap["date"])
    if not prev_snap:
        print("📝 初回実行：比較対象なし。明日から差分レポートが出ます。")
        # 初回はサマリだけ送信
        msg = (
            f"*🏥 ハローワーク求人レポート {today_snap['date']}*\n"
            f"*総数:* {today_snap['total_nurse']}件（初回取得・明日から差分表示）"
        )
        if not args.dry_run:
            send_message(SLACK_CHANNEL_REPORT, msg)
        else:
            print(msg)
        return

    # Step 3: 差分分析
    diff = diff_snapshots(today_snap, prev_snap)

    # ランクデータ読み込み
    ranked = None
    if RANKED_FILE.exists():
        ranked = json.loads(RANKED_FILE.read_text())

    # Step 4: レポート生成
    report = format_slack_report(diff, ranked)
    print(report)

    # Step 5: Slack送信（3000文字超は分割）
    if not args.dry_run:
        if len(report) <= 3000:
            send_message(SLACK_CHANNEL_REPORT, report)
        else:
            # サマリ部分と詳細部分を分けて送信
            chunks = _split_report(report)
            for i, chunk in enumerate(chunks):
                send_message(SLACK_CHANNEL_REPORT, chunk)
                if i < len(chunks) - 1:
                    import time; time.sleep(1)
        print("\n✅ Slack送信完了")
    else:
        print("\n[dry-run] Slack送信スキップ")


if __name__ == "__main__":
    main()
