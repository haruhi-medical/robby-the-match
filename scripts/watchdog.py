#!/usr/bin/env python3
"""
自己修復ウォッチドッグ v3.0
- 全cronジョブのハートビートを監視
- 失敗・未実行を検出してリカバリ試行
- sns_postの投稿スケジュール対応（posting_schedule.json連動）
- instagram_engageの監視追加
- TikTok投稿数の乖離検出（キュー vs プロフィール）
- 時間依存スクリプトの誤リカバリ防止
- Slackにアラート通知

v3.0 改善点:
- 日次リトライカウンタ自動リセット
- スマートリトライ分類（CONFIG_ERROR → リトライしない）
- アラート重複排除（同一ジョブ4時間以内は再通知しない）
- MAX_RETRIES 2→3
- --reset フラグで手動リセット
- Slackメッセージに実際のエラー内容を含める

cron: */30 * * * * python3 ~/robby-the-match/scripts/watchdog.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
HEARTBEAT_DIR = PROJECT_DIR / "data" / "heartbeats"
RECOVERY_LOG = PROJECT_DIR / "data" / "recovery_log.json"
LOG_DIR = PROJECT_DIR / "logs"
ENV_FILE = PROJECT_DIR / ".env"
POSTING_SCHEDULE_FILE = PROJECT_DIR / "data" / "posting_schedule.json"
POSTING_QUEUE_FILE = PROJECT_DIR / "data" / "posting_queue.json"
TIKTOK_DISCREPANCY_FILE = PROJECT_DIR / "data" / "tiktok_discrepancy.json"

# ============================================================
# ジョブ定義
# ============================================================
# 固定時刻ジョブ: (hour, minute, max_duration_min, script_path, safe_to_recover)
# safe_to_recover: Trueなら時刻を問わずリカバリ可能（冪等性がある）
#                  Falseなら特定時刻にしか意味がないためリカバリ制限あり
FIXED_SCHEDULE_JOBS = {
    "seo_batch":     (4,  0,  30, "scripts/pdca_seo_batch.sh",     True),
    "healthcheck":   (7,  0,  15, "scripts/pdca_healthcheck.sh",   True),
    "ai_marketing":  (6,  0,  45, "scripts/pdca_ai_marketing.sh",  True),
    "competitor":    (10, 0,  30, "scripts/pdca_competitor.sh",     True),
    "content":       (15, 0,  45, "scripts/pdca_content.sh",       True),
    "review":        (23, 0,  45, "scripts/pdca_review.sh",        True),
}

# sns_postは動的スケジュール（posting_schedule.json依存）なので別扱い
# instagram_engageはランダム遅延付きなので別扱い

MAX_RETRIES = 3

# アラート重複排除: 同一ジョブのSlackアラートを何秒間抑制するか（4時間）
ALERT_COOLDOWN_SECONDS = 4 * 60 * 60

# エラー分類パターン: ログにこれらの文字列が含まれていれば CONFIG_ERROR（リトライ不要）
CONFIG_ERROR_PATTERNS = [
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
    "authentication failed",
    "auth token expired",
    "API key",
]

# CONFIG_ERRORパターンに対応する人間向けメッセージ
CONFIG_ERROR_MESSAGES = {
    "CLOUDFLARE_ACCOUNT_ID": "認証エラー — CLOUDFLARE_ACCOUNT_IDが未設定",
    "CLOUDFLARE_API_TOKEN": "認証エラー — CLOUDFLARE_API_TOKENが未設定または無効",
    "authentication failed": "認証エラー — APIキーまたはトークンの確認が必要",
    "auth token expired": "認証エラー — トークン期限切れ。再認証が必要",
    "API key": "認証エラー — APIキーの確認が必要",
}

# TikTok投稿数の許容乖離（キュー上のposted数 vs プロフィール公開数）
TIKTOK_DISCREPANCY_THRESHOLD = 3
# TikTok乖離が連続何回検出されたらエスカレーションするか
TIKTOK_ESCALATION_AFTER = 3


def load_env():
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def slack_notify(message):
    try:
        subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "notify_slack.py"),
             "--message", message],
            capture_output=True, timeout=30
        )
    except Exception:
        pass


# ============================================================
# リカバリログ v3.0 フォーマット
# ============================================================
# {
#   "jobs": {
#     "seo_batch": {
#       "date": "2026-03-03",
#       "retries": 2,
#       "status": "retrying" | "retry_exhausted" | "config_error",
#       "last_error": "Not logged in",
#       "last_alert_ts": "2026-03-03T05:30:00.000000"
#     }
#   }
# }

def load_recovery_log():
    if RECOVERY_LOG.exists():
        try:
            data = json.loads(RECOVERY_LOG.read_text())
            # v2 → v3 マイグレーション: 旧フォーマット（フラットなキー）を検出したら
            # 新フォーマットに変換
            if "jobs" not in data:
                # 旧フォーマット: {"seo_batch_2026-03-03": 2, ...}
                # 新フォーマットに変換せず、空で開始（旧データは日付が古いので不要）
                return {"jobs": {}}
            return data
        except Exception:
            return {"jobs": {}}
    return {"jobs": {}}


def save_recovery_log(log):
    RECOVERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    RECOVERY_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def get_job_recovery(recovery, job_name):
    """ジョブのリカバリ状態を取得。日付が変わっていたら自動リセット。"""
    today = datetime.now().strftime("%Y-%m-%d")
    jobs = recovery.setdefault("jobs", {})
    entry = jobs.get(job_name, {})

    # 日付が変わっていたらリセット（日次リセット）
    if entry.get("date") != today:
        entry = {
            "date": today,
            "retries": 0,
            "status": "ok",
            "last_error": "",
            "last_alert_ts": "",
        }
        jobs[job_name] = entry

    return entry


def should_send_alert(recovery, job_name):
    """アラート重複排除: 前回アラートから ALERT_COOLDOWN_SECONDS 以内なら False。"""
    entry = recovery.get("jobs", {}).get(job_name, {})
    last_alert = entry.get("last_alert_ts", "")
    if not last_alert:
        return True
    try:
        last_dt = datetime.fromisoformat(last_alert)
        elapsed = (datetime.now() - last_dt).total_seconds()
        return elapsed >= ALERT_COOLDOWN_SECONDS
    except Exception:
        return True


def mark_alert_sent(recovery, job_name):
    """アラート送信時刻を記録。"""
    entry = recovery.get("jobs", {}).get(job_name, {})
    entry["last_alert_ts"] = datetime.now().isoformat()


def classify_error(job_name):
    """ジョブのログファイルを読み、エラーを分類する。
    Returns: ("config_error", human_message) or ("transient", "")
    """
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")

    # ログファイルの候補（ジョブによって命名パターンが違う）
    log_candidates = [
        LOG_DIR / f"pdca_{job_name}_{today_str}.log",
        LOG_DIR / f"{job_name}_{today_str}.log",
        LOG_DIR / f"{job_name}.log",
    ]

    for log_file in log_candidates:
        if not log_file.exists():
            continue
        try:
            # ログの末尾2000バイトだけ読む（大きなログを全部読まない）
            size = log_file.stat().st_size
            with open(log_file, 'r', errors='replace') as f:
                if size > 2000:
                    f.seek(size - 2000)
                content = f.read()

            for pattern in CONFIG_ERROR_PATTERNS:
                if pattern in content:
                    msg = CONFIG_ERROR_MESSAGES.get(
                        pattern, f"設定エラー ({pattern})")
                    return ("config_error", msg)
        except Exception:
            continue

    # ハートビートのexit_codeも確認
    hb_file = HEARTBEAT_DIR / f"{job_name}.json"
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text())
            if hb.get("date") == today_str and hb.get("exit_code", 0) != 0:
                return ("transient",
                        f"exit_code={hb.get('exit_code')}（一時的エラーの可能性）")
        except Exception:
            pass

    return ("transient", "")


def get_error_detail_for_message(job_name):
    """Slackメッセージ用のエラー詳細を取得。"""
    error_type, error_msg = classify_error(job_name)
    if error_msg:
        return error_msg
    return "原因不明（ログを確認してください）"


# ============================================================
# posting_schedule.json から今日の投稿時間を取得
# ============================================================
def get_today_sns_schedule():
    """posting_schedule.json から今日（曜日）の予定投稿時刻を返す。
    Returns: (hour, minute) or None (休止日)
    """
    if not POSTING_SCHEDULE_FILE.exists():
        return None
    try:
        with open(POSTING_SCHEDULE_FILE) as f:
            data = json.load(f)
        # 曜日名（Mon, Tue, Wed, Thu, Fri, Sat）
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        today_name = day_names[datetime.now().weekday()]
        scheduled = data.get("schedule", {}).get(today_name, "")
        if not scheduled:
            return None
        parts = scheduled.split(":")
        return (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except Exception:
        return None


# ============================================================
# ハートビートチェック
# ============================================================
def check_heartbeat(job_name, expected_hour, expected_min, max_duration_min):
    """ジョブのハートビートを確認"""
    now = datetime.now()
    expected_time = now.replace(hour=expected_hour, minute=expected_min, second=0)

    # まだ実行時刻前なら確認不要
    if now < expected_time:
        return "not_due_yet"

    # 実行中の可能性（実行時刻 + 最大実行時間以内）
    deadline = expected_time + timedelta(minutes=max_duration_min)
    if now < deadline:
        return "possibly_running"

    # ハートビートファイル確認
    hb_file = HEARTBEAT_DIR / f"{job_name}.json"
    if not hb_file.exists():
        return "missing"

    try:
        hb = json.loads(hb_file.read_text())
        hb_date = hb.get("date", "")
        today = now.strftime("%Y-%m-%d")

        if hb_date != today:
            return "stale"

        if hb.get("exit_code", 0) != 0:
            return "failed"

        return "ok"
    except Exception:
        return "error"


def check_sns_post_heartbeat():
    """sns_postの時間対応ハートビートチェック。
    posting_schedule.json に基づいて今日の投稿時刻を特定し、
    その時刻を過ぎているのにハートビートがなければ問題とみなす。
    Returns: (status, detail_str)
      status: "ok" | "not_due_yet" | "possibly_running" | "missing" |
              "stale" | "failed" | "rest_day" | "skipped_ok"
    """
    schedule = get_today_sns_schedule()
    if schedule is None:
        return ("rest_day", "本日は投稿休止日")

    hour, minute = schedule
    now = datetime.now()
    expected_time = now.replace(hour=hour, minute=minute, second=0)

    if now < expected_time:
        return ("not_due_yet", f"投稿予定 {hour:02d}:{minute:02d}")

    # sns_postのmax_duration: 20min
    deadline = expected_time + timedelta(minutes=20)
    if now < deadline:
        return ("possibly_running", f"実行中の可能性 ({hour:02d}:{minute:02d} 開始)")

    # ハートビート確認
    hb_file = HEARTBEAT_DIR / "sns_post.json"
    if not hb_file.exists():
        return ("missing", f"ハートビートなし（予定: {hour:02d}:{minute:02d}）")

    try:
        hb = json.loads(hb_file.read_text())
        hb_date = hb.get("date", "")
        today = now.strftime("%Y-%m-%d")

        if hb_date != today:
            return ("stale", f"古いハートビート（最終: {hb_date}、予定: {hour:02d}:{minute:02d}）")

        # ハートビートが今日のものなら、投稿時刻付近に書かれたかも確認
        hb_ts = hb.get("ts", "")
        if hb_ts:
            try:
                hb_time = datetime.fromisoformat(hb_ts)
                # ハートビートが予定時刻の前後1時間以内に書かれていれば正常
                if abs((hb_time - expected_time).total_seconds()) > 3600:
                    # 別の時間帯の実行結果かもしれない（cron自体は複数時間帯で起動するため）
                    # ただし今日のdate付きで exit_code=0 なら基本OK
                    pass
            except Exception:
                pass

        if hb.get("exit_code", 0) != 0:
            return ("failed", f"投稿失敗（exit_code={hb.get('exit_code')}）")

        return ("ok", f"投稿完了（{hour:02d}:{minute:02d}）")
    except Exception as e:
        return ("error", f"ハートビート読取エラー: {e}")


def check_instagram_engage_heartbeat():
    """instagram_engageのハートビートチェック。
    cronは 0 12 * * 1-6 + RANDOM%3600の遅延付き。
    つまり12:00～13:00の間に実行される。13:00以降を過ぎてもハートビートがなければ問題。
    Returns: (status, detail_str)
    """
    now = datetime.now()
    expected_start = now.replace(hour=12, minute=0, second=0)
    # ランダム遅延で最大1時間、実行自体にも最大30分かかりうる
    deadline = now.replace(hour=13, minute=30, second=0)

    if now < expected_start:
        return ("not_due_yet", "実行予定 12:00-13:00")

    if now < deadline:
        return ("possibly_running", "実行中の可能性（12:00-13:00 + ランダム遅延）")

    # ハートビートファイル確認
    # instagram_engageにはwrite_heartbeat呼び出しがないかもしれない
    # その場合はengagement_logの最終日付で代替判定
    hb_file = HEARTBEAT_DIR / "instagram_engage.json"
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text())
            hb_date = hb.get("date", "")
            today = now.strftime("%Y-%m-%d")
            if hb_date == today:
                if hb.get("exit_code", 0) != 0:
                    return ("failed", f"エンゲージメント失敗（exit_code={hb.get('exit_code')}）")
                return ("ok", "エンゲージメント完了")
            else:
                return ("stale", f"古いハートビート（最終: {hb_date}）")
        except Exception:
            pass

    # ハートビートファイルがない場合、engagement_logで代替チェック
    engage_log = PROJECT_DIR / "data" / "engagement_log.json"
    if engage_log.exists():
        try:
            log = json.loads(engage_log.read_text())
            if log:
                last_entry = log[-1]
                last_date_str = last_entry.get("date", "")
                if last_date_str:
                    last_date = last_date_str[:10]  # YYYY-MM-DD部分
                    today = now.strftime("%Y-%m-%d")
                    if last_date == today:
                        if "error" in last_entry:
                            return ("failed", f"エンゲージメントエラー: {last_entry['error']}")
                        return ("ok", "engagement_log確認 - 本日実行済み")
                    else:
                        return ("stale", f"最終実行: {last_date}")
        except Exception:
            pass

    return ("missing", "ハートビートもengagement_logも見つからない")


# ============================================================
# TikTok投稿数乖離検出
# ============================================================
def check_tiktok_discrepancy():
    """キュー上のposted数 vs TikTokプロフィールの公開投稿数を比較。
    大きな乖離があれば警告する。
    Returns: (has_issue: bool, detail: str, queue_posted: int, profile_count: int)
    """
    queue_posted = 0
    profile_count = -1

    # キューの posted 数
    if POSTING_QUEUE_FILE.exists():
        try:
            queue = json.loads(POSTING_QUEUE_FILE.read_text())
            posts = queue.get("posts", [])
            queue_posted = sum(1 for p in posts if p.get("status") == "posted")
        except Exception:
            pass

    # TikTokプロフィールの公開投稿数を取得
    # tiktok_post.py の get_tiktok_video_count() を呼ぶ
    try:
        result = subprocess.run(
            ["python3", "-c",
             "import sys; sys.path.insert(0, '{}'); "
             "from tiktok_post import get_tiktok_video_count; "
             "print(get_tiktok_video_count())".format(
                 str(PROJECT_DIR / "scripts"))],
            capture_output=True, text=True, timeout=45,
            cwd=str(PROJECT_DIR)
        )
        if result.returncode == 0:
            try:
                profile_count = int(result.stdout.strip())
            except ValueError:
                profile_count = -1
    except Exception:
        profile_count = -1

    if profile_count < 0:
        return (False, "TikTokプロフィール取得不可（ネットワークエラーの可能性）",
                queue_posted, profile_count)

    discrepancy = queue_posted - profile_count

    if profile_count == 0 and queue_posted > 0:
        detail = (f"TikTokプロフィール投稿数0件 / キューposted {queue_posted}件"
                  f" — 投稿が公開されていない可能性")
        return (True, detail, queue_posted, profile_count)

    if discrepancy >= TIKTOK_DISCREPANCY_THRESHOLD:
        detail = (f"キューposted {queue_posted}件 vs プロフィール {profile_count}件"
                  f"（差分 {discrepancy}件）")
        return (True, detail, queue_posted, profile_count)

    return (False,
            f"キュー {queue_posted}件 / プロフィール {profile_count}件 — 正常範囲",
            queue_posted, profile_count)


def load_tiktok_discrepancy_state():
    """TikTok乖離の連続検出回数を追跡するファイルを読み込む"""
    if TIKTOK_DISCREPANCY_FILE.exists():
        try:
            return json.loads(TIKTOK_DISCREPANCY_FILE.read_text())
        except Exception:
            return {"consecutive_alerts": 0, "last_alert": None}
    return {"consecutive_alerts": 0, "last_alert": None}


def save_tiktok_discrepancy_state(state):
    TIKTOK_DISCREPANCY_FILE.parent.mkdir(parents=True, exist_ok=True)
    TIKTOK_DISCREPANCY_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False))


# ============================================================
# リカバリ
# ============================================================
def attempt_recovery(job_name, script_path, safe_to_recover=True):
    """失敗ジョブの再実行を試行。
    safe_to_recover=False のジョブは、現在が適切な実行タイミングでなければスキップ。

    Returns: ("recovered" | "max_retries" | "config_error" | "unsafe_time" |
              "script_not_found" | "retry_failed" | "timeout" | "error: ...",
              error_detail_str)
    """
    recovery = load_recovery_log()
    entry = get_job_recovery(recovery, job_name)

    # エラー分類: CONFIG_ERROR なら即座にリトライ中止
    error_type, error_msg = classify_error(job_name)
    if error_type == "config_error":
        entry["status"] = "config_error"
        entry["last_error"] = error_msg
        save_recovery_log(recovery)
        return ("config_error", error_msg)

    # リトライ上限チェック
    if entry["retries"] >= MAX_RETRIES:
        entry["status"] = "retry_exhausted"
        save_recovery_log(recovery)
        error_detail = get_error_detail_for_message(job_name)
        return ("max_retries", error_detail)

    if not safe_to_recover:
        return ("unsafe_time", "")

    # リトライ実行
    entry["retries"] += 1
    entry["status"] = "retrying"
    save_recovery_log(recovery)

    full_path = PROJECT_DIR / script_path
    if not full_path.exists():
        return ("script_not_found", f"スクリプト未発見: {script_path}")

    try:
        result = subprocess.run(
            ["/bin/bash", str(full_path)],
            capture_output=True, timeout=1800,
            cwd=str(PROJECT_DIR),
            env={**os.environ}
        )
        if result.returncode == 0:
            entry["status"] = "recovered"
            entry["last_error"] = ""
            save_recovery_log(recovery)
            return ("recovered", "")
        else:
            # リトライ後も失敗 — 再分類
            error_type2, error_msg2 = classify_error(job_name)
            if error_type2 == "config_error":
                entry["status"] = "config_error"
                entry["last_error"] = error_msg2
                save_recovery_log(recovery)
                return ("config_error", error_msg2)
            entry["last_error"] = error_msg2 or f"exit_code={result.returncode}"
            save_recovery_log(recovery)
            return ("retry_failed", entry["last_error"])
    except subprocess.TimeoutExpired:
        entry["last_error"] = "タイムアウト（30分）"
        save_recovery_log(recovery)
        return ("timeout", "タイムアウト（30分）")
    except Exception as e:
        entry["last_error"] = str(e)
        save_recovery_log(recovery)
        return (f"error: {e}", str(e))


def attempt_sns_post_recovery():
    """sns_postのリカバリ。現在の時刻がposting_schedule.jsonの予定時刻から
    2時間以内であれば再実行を試行する（スクリプト自体が時刻チェックするため、
    合致しない場合は即exitする＝安全）。
    """
    schedule = get_today_sns_schedule()
    if schedule is None:
        return ("rest_day", "")

    hour, minute = schedule
    now = datetime.now()
    expected_time = now.replace(hour=hour, minute=minute, second=0)
    elapsed = (now - expected_time).total_seconds()

    # 予定時刻から2時間以内ならリカバリ試行
    if 0 <= elapsed <= 7200:
        return attempt_recovery(
            "sns_post", "scripts/pdca_sns_post.sh", safe_to_recover=True)
    else:
        return ("wrong_time", "")


def attempt_instagram_engage_recovery():
    """instagram_engageのリカバリ。12:00-15:00の範囲内なら再実行する。
    それ以降は翌日に回す（アカウント安全性のためアクション時間帯を守る）。
    """
    now = datetime.now()
    if 12 <= now.hour <= 14:
        script_path = "scripts/instagram_engage.py"
        full_path = PROJECT_DIR / script_path
        if not full_path.exists():
            return ("script_not_found", f"スクリプト未発見: {script_path}")

        recovery = load_recovery_log()
        entry = get_job_recovery(recovery, "instagram_engage")

        # エラー分類
        error_type, error_msg = classify_error("instagram_engage")
        if error_type == "config_error":
            entry["status"] = "config_error"
            entry["last_error"] = error_msg
            save_recovery_log(recovery)
            return ("config_error", error_msg)

        if entry["retries"] >= MAX_RETRIES:
            entry["status"] = "retry_exhausted"
            save_recovery_log(recovery)
            error_detail = get_error_detail_for_message("instagram_engage")
            return ("max_retries", error_detail)

        entry["retries"] += 1
        entry["status"] = "retrying"
        save_recovery_log(recovery)

        try:
            result = subprocess.run(
                ["python3", str(full_path), "--daily"],
                capture_output=True, timeout=3600,
                cwd=str(PROJECT_DIR),
                env={**os.environ}
            )
            if result.returncode == 0:
                entry["status"] = "recovered"
                entry["last_error"] = ""
                save_recovery_log(recovery)
                return ("recovered", "")
            else:
                error_type2, error_msg2 = classify_error("instagram_engage")
                if error_type2 == "config_error":
                    entry["status"] = "config_error"
                    entry["last_error"] = error_msg2
                    save_recovery_log(recovery)
                    return ("config_error", error_msg2)
                entry["last_error"] = error_msg2 or f"exit_code={result.returncode}"
                save_recovery_log(recovery)
                return ("retry_failed", entry["last_error"])
        except subprocess.TimeoutExpired:
            entry["last_error"] = "タイムアウト（60分）"
            save_recovery_log(recovery)
            return ("timeout", "タイムアウト（60分）")
        except Exception as e:
            entry["last_error"] = str(e)
            save_recovery_log(recovery)
            return (f"error: {e}", str(e))
    else:
        return ("wrong_time", "")


# ============================================================
# --reset フラグ: 全リトライカウンタをクリア
# ============================================================
def reset_all():
    """全ジョブのリトライカウンタ・ステータスをクリアする。"""
    recovery = {"jobs": {}}
    save_recovery_log(recovery)
    print("リカバリログをリセットしました。")
    print(f"  ファイル: {RECOVERY_LOG}")

    # 現在の内容を表示
    print(f"  内容: {json.dumps(recovery, indent=2, ensure_ascii=False)}")


# ============================================================
# メインウォッチドッグ
# ============================================================
def run_watchdog():
    """全ジョブの健全性チェック + 自己修復"""
    now = datetime.now()
    # 月-土のみ動作（日曜はweekly系のみで通常ジョブは休み）
    if now.weekday() == 6:  # 日曜
        return

    recovery = load_recovery_log()
    issues = []           # Slackに通知する問題
    suppressed = []       # アラート抑制された問題（ログのみ）
    recovered = []
    info = []

    # ─── 1. 固定スケジュールジョブの監視 ───
    for job_name, (hour, minute, max_dur, script, safe) in FIXED_SCHEDULE_JOBS.items():
        status = check_heartbeat(job_name, hour, minute, max_dur)

        if status in ("ok", "not_due_yet", "possibly_running"):
            continue

        if status in ("missing", "stale", "failed"):
            # 既にconfig_errorまたはretry_exhaustedなら再実行しない
            entry = get_job_recovery(recovery, job_name)
            if entry.get("status") in ("config_error", "retry_exhausted"):
                error_detail = entry.get("last_error", "不明")
                if entry["status"] == "config_error":
                    msg = f"{job_name}: {error_detail}（自動リトライ対象外）"
                else:
                    msg = (f"{job_name}: リトライ上限到達"
                           f"（{entry['retries']}/{MAX_RETRIES}）— {error_detail}")

                # アラート重複排除
                if should_send_alert(recovery, job_name):
                    issues.append(msg)
                    mark_alert_sent(recovery, job_name)
                else:
                    suppressed.append(msg)
                save_recovery_log(recovery)
                continue

            result, error_detail = attempt_recovery(
                job_name, script, safe_to_recover=safe)

            if result == "recovered":
                recovered.append(f"{job_name}: 自動復旧成功")
            elif result == "config_error":
                msg = f"{job_name}: {error_detail}（自動リトライ対象外）"
                if should_send_alert(recovery, job_name):
                    issues.append(msg)
                    mark_alert_sent(recovery, job_name)
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "max_retries":
                msg = (f"{job_name}: リトライ上限到達"
                       f"（{MAX_RETRIES}/{MAX_RETRIES}）— {error_detail}")
                if should_send_alert(recovery, job_name):
                    issues.append(msg)
                    mark_alert_sent(recovery, job_name)
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "unsafe_time":
                msg = (f"{job_name}: 失敗検出（{status}）"
                       f"— 時刻不適のためリカバリ保留")
                if should_send_alert(recovery, job_name):
                    issues.append(msg)
                    mark_alert_sent(recovery, job_name)
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            else:
                msg = f"{job_name}: 復旧失敗 ({result}) — {error_detail}"
                if should_send_alert(recovery, job_name):
                    issues.append(msg)
                    mark_alert_sent(recovery, job_name)
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)

    # ─── 2. sns_post（動的スケジュール）の監視 ───
    sns_status, sns_detail = check_sns_post_heartbeat()

    if sns_status in ("ok", "not_due_yet", "possibly_running", "rest_day"):
        if sns_status == "rest_day":
            info.append(f"sns_post: {sns_detail}")
    elif sns_status in ("missing", "stale", "failed"):
        # 既にconfig_errorまたはretry_exhaustedなら再実行しない
        entry = get_job_recovery(recovery, "sns_post")
        if entry.get("status") in ("config_error", "retry_exhausted"):
            error_detail = entry.get("last_error", "不明")
            msg = f"sns_post: {error_detail}（{sns_detail}）"
            if should_send_alert(recovery, "sns_post"):
                issues.append(msg)
                mark_alert_sent(recovery, "sns_post")
                save_recovery_log(recovery)
            else:
                suppressed.append(msg)
        else:
            result, error_detail = attempt_sns_post_recovery()
            if result == "recovered":
                recovered.append(f"sns_post: 自動復旧成功（{sns_detail}）")
            elif result == "wrong_time":
                msg = (f"sns_post: {sns_detail}"
                       f" — 投稿時間帯を過ぎたためリカバリ不可（翌日再試行）")
                if should_send_alert(recovery, "sns_post"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "sns_post")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "config_error":
                msg = f"sns_post: {error_detail}（{sns_detail}）"
                if should_send_alert(recovery, "sns_post"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "sns_post")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "max_retries":
                msg = (f"sns_post: リトライ上限到達"
                       f"（{MAX_RETRIES}/{MAX_RETRIES}）— {error_detail}（{sns_detail}）")
                if should_send_alert(recovery, "sns_post"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "sns_post")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "rest_day":
                info.append("sns_post: 本日休止日")
            else:
                msg = f"sns_post: 復旧失敗 ({result}) — {error_detail}（{sns_detail}）"
                if should_send_alert(recovery, "sns_post"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "sns_post")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
    elif sns_status == "skipped_ok":
        info.append(f"sns_post: {sns_detail}")

    # ─── 3. instagram_engage の監視 ───
    ig_status, ig_detail = check_instagram_engage_heartbeat()

    if ig_status in ("ok", "not_due_yet", "possibly_running"):
        pass
    elif ig_status in ("missing", "stale", "failed"):
        # 既にconfig_errorまたはretry_exhaustedなら再実行しない
        entry = get_job_recovery(recovery, "instagram_engage")
        if entry.get("status") in ("config_error", "retry_exhausted"):
            error_detail = entry.get("last_error", "不明")
            msg = f"instagram_engage: {error_detail}（{ig_detail}）"
            if should_send_alert(recovery, "instagram_engage"):
                issues.append(msg)
                mark_alert_sent(recovery, "instagram_engage")
                save_recovery_log(recovery)
            else:
                suppressed.append(msg)
        else:
            result, error_detail = attempt_instagram_engage_recovery()
            if result == "recovered":
                recovered.append(
                    f"instagram_engage: 自動復旧成功（{ig_detail}）")
            elif result == "wrong_time":
                msg = (f"instagram_engage: {ig_detail}"
                       f" — 適切な時間帯外のためリカバリ不可（翌日再試行）")
                if should_send_alert(recovery, "instagram_engage"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "instagram_engage")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "config_error":
                msg = f"instagram_engage: {error_detail}（{ig_detail}）"
                if should_send_alert(recovery, "instagram_engage"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "instagram_engage")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            elif result == "max_retries":
                msg = (f"instagram_engage: リトライ上限到達"
                       f"（{MAX_RETRIES}/{MAX_RETRIES}）— {error_detail}（{ig_detail}）")
                if should_send_alert(recovery, "instagram_engage"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "instagram_engage")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)
            else:
                msg = (f"instagram_engage: 復旧失敗 ({result})"
                       f" — {error_detail}（{ig_detail}）")
                if should_send_alert(recovery, "instagram_engage"):
                    issues.append(msg)
                    mark_alert_sent(recovery, "instagram_engage")
                    save_recovery_log(recovery)
                else:
                    suppressed.append(msg)

    # ─── 4. TikTok投稿数乖離チェック（1日2回: 09時台と22時台に実行） ───
    if now.hour in (9, 22):
        has_issue, detail, q_count, p_count = check_tiktok_discrepancy()

        disc_state = load_tiktok_discrepancy_state()

        if has_issue:
            disc_state["consecutive_alerts"] = disc_state.get(
                "consecutive_alerts", 0) + 1
            disc_state["last_alert"] = now.isoformat()
            disc_state["last_queue_posted"] = q_count
            disc_state["last_profile_count"] = p_count
            save_tiktok_discrepancy_state(disc_state)

            consecutive = disc_state["consecutive_alerts"]

            if consecutive >= TIKTOK_ESCALATION_AFTER:
                # エスカレーション: より強い警告
                issues.append(
                    f"TikTok投稿乖離 [{consecutive}回連続検出]: {detail}"
                    f" — 手動確認が必要（Cookie期限切れ / アカウント制限の可能性）")
            else:
                issues.append(f"TikTok投稿乖離: {detail}")
        else:
            # 正常に戻ったらカウンタリセット
            if disc_state.get("consecutive_alerts", 0) > 0:
                disc_state["consecutive_alerts"] = 0
                disc_state["resolved_at"] = now.isoformat()
                save_tiktok_discrepancy_state(disc_state)
            info.append(f"TikTok: {detail}")

    # ─── ログ記録 ───
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"watchdog_{now.strftime('%Y%m%d')}.log"
    entry = {
        "ts": now.isoformat(),
        "issues": issues,
        "suppressed": suppressed,
        "recovered": recovered,
        "info": info,
    }
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ─── Slack通知（問題がある場合のみ — 重複排除済み） ───
    if issues:
        slack_notify(
            f"*[Watchdog v3.0] アラート*\n\n"
            + "\n".join(f"- {i}" for i in issues)
            + ("\n\n" + "\n".join(f"+ {r}" for r in recovered)
               if recovered else "")
            + (f"\n\n_（他 {len(suppressed)}件は4時間以内に通知済みのため抑制）_"
               if suppressed else "")
        )
    elif recovered:
        slack_notify(
            f"*[Watchdog v3.0] 自動復旧*\n\n"
            + "\n".join(f"+ {r}" for r in recovered)
        )


if __name__ == "__main__":
    load_env()

    if "--reset" in sys.argv:
        reset_all()
    else:
        run_watchdog()
