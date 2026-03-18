#!/usr/bin/env python3
"""
TikTok Analytics Collection Script v3.0
=======================================
upload_verification.json を正規データソースとして投稿を追跡し、
Playwright ブラウザ経由でプロフィール・動画のパフォーマンスデータを取得する。

curl によるスクレイピングは TikTok の bot 検知で安定しないため、
Playwright (headless Chromium) を主力とし、curl を軽量フォールバックとする。

使い方:
  python3 tiktok_analytics.py --status        # プロフィール情報を表示
  python3 tiktok_analytics.py --update        # posting_queue.json更新 + KPI追記
  python3 tiktok_analytics.py --daily-kpi     # KPI CSVのみ追記
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
QUEUE_FILE = PROJECT_DIR / "data" / "posting_queue.json"
VERIFICATION_FILE = PROJECT_DIR / "data" / "upload_verification.json"
KPI_FILE = PROJECT_DIR / "data" / "kpi_log.csv"
COOKIE_JSON = PROJECT_DIR / "data" / ".tiktok_cookies.json"
COOKIE_TXT = PROJECT_DIR / "data" / ".tiktok_cookies.txt"
LOG_DIR = PROJECT_DIR / "logs"
ENV_FILE = PROJECT_DIR / ".env"
VENV_PYTHON = PROJECT_DIR / ".venv" / "bin" / "python3"
TIKTOK_USERNAME = "nurse_robby"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

MAX_RETRIES = 3
BACKOFF_BASE = 5  # seconds; retry waits: 5, 10, 20


# ============================================================
# Atomic JSON write (same pattern as tiktok_post.py)
# ============================================================

def atomic_json_write(filepath, data, indent=2):
    """Atomic JSON write: tempfile + fsync + os.replace to prevent corruption."""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix='.tmp',
            prefix=filepath.stem + '_'
        )
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, filepath)
    except Exception:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except (OSError, UnboundLocalError):
                pass
        raise


# ============================================================
# Utilities
# ============================================================

def load_env():
    """Load .env file.

    Called at module level AND in main() to ensure env vars are available
    even in cron environments where .zshrc is not sourced.
    """
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


# Load .env at module level for cron compatibility
load_env()


def slack_notify(message):
    """Slack notification (best-effort)."""
    try:
        subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "notify_slack.py"),
             "--message", message],
            capture_output=True, timeout=30
        )
    except Exception as e:
        print(f"[WARN] Slack notification failed: {e}")


def log_event(event_type, data):
    """Write event to daily log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"tiktok_analytics_{datetime.now().strftime('%Y%m%d')}.log"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data
    }
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================
# Upload Verification data source
# ============================================================

def load_verification_data():
    """Load upload_verification.json as primary data source for tracked posts.

    Returns a list of upload records (dicts with timestamp, content_id, success, method, etc.)
    """
    if not VERIFICATION_FILE.exists():
        print("[WARN] upload_verification.json not found")
        return []
    try:
        with open(VERIFICATION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        uploads = data.get("uploads", [])
        # Filter to only successful uploads
        successful = [u for u in uploads if u.get("success")]
        print(f"  Loaded {len(successful)} successful uploads from upload_verification.json")
        return successful
    except Exception as e:
        print(f"[WARN] Failed to load upload_verification.json: {e}")
        return []


def load_queue_data():
    """Load posting_queue.json."""
    if not QUEUE_FILE.exists():
        print("[WARN] posting_queue.json not found")
        return None
    try:
        with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load posting_queue.json: {e}")
        return None


def get_posted_content_ids():
    """Get a set of content_ids that were successfully uploaded.

    Uses upload_verification.json as the primary source,
    cross-references with posting_queue.json for status.
    """
    verification = load_verification_data()
    verified_ids = {u["content_id"] for u in verification if u.get("content_id")}

    queue = load_queue_data()
    if queue:
        for post in queue.get("posts", []):
            if post.get("status") in ("posted", "deleted_from_tiktok"):
                verified_ids.add(post.get("content_id", ""))

    verified_ids.discard("")
    return verified_ids


# ============================================================
# Cookie handling
# ============================================================

def build_cookie_args():
    """Build curl cookie arguments from the best available cookie source."""
    if COOKIE_TXT.exists():
        return ["-b", str(COOKIE_TXT)]

    if COOKIE_JSON.exists():
        try:
            with open(COOKIE_JSON, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            pairs = []
            for c in cookies:
                name = c.get("name", "")
                value = c.get("value", "")
                if name and value:
                    pairs.append(f"{name}={value}")
            if pairs:
                return ["-b", "; ".join(pairs)]
        except Exception:
            pass

    return []


def load_playwright_cookies():
    """Load cookies from JSON file for Playwright browser context."""
    if COOKIE_JSON.exists():
        try:
            with open(COOKIE_JSON, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            # Playwright expects cookies with specific fields
            pw_cookies = []
            for c in cookies:
                cookie = {
                    "name": c.get("name", ""),
                    "value": c.get("value", ""),
                    "domain": c.get("domain", ".tiktok.com"),
                    "path": c.get("path", "/"),
                }
                if c.get("expires"):
                    cookie["expires"] = c["expires"]
                if c.get("httpOnly") is not None:
                    cookie["httpOnly"] = c["httpOnly"]
                if c.get("secure") is not None:
                    cookie["secure"] = c["secure"]
                if c.get("sameSite"):
                    ss = c["sameSite"]
                    if ss in ("Strict", "Lax", "None"):
                        cookie["sameSite"] = ss
                pw_cookies.append(cookie)
            return pw_cookies
        except Exception as e:
            print(f"  [WARN] Failed to load cookies for Playwright: {e}")
    return []


# ============================================================
# Fetch profile via curl (lightweight fallback)
# ============================================================

def fetch_profile_html_curl():
    """Curl the TikTok profile page and return the HTML string."""
    cookie_args = build_cookie_args()
    cmd = [
        "curl", "-s", "-L",
        "--max-time", "30",
        "-H", f"User-Agent: {USER_AGENT}",
        "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "Accept-Language: ja,en-US;q=0.9,en;q=0.8",
    ] + cookie_args + [
        f"https://www.tiktok.com/@{TIKTOK_USERNAME}"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            print(f"  [CURL] curl returned exit code {result.returncode}")
            return None
        html = result.stdout
        if not html or len(html) < 500:
            print(f"  [CURL] Response too short ({len(html) if html else 0} bytes)")
            return None
        return html
    except subprocess.TimeoutExpired:
        print("  [CURL] curl timed out (45s)")
        return None
    except Exception as e:
        print(f"  [CURL] Exception: {e}")
        return None


# ============================================================
# Fetch profile via Playwright browser (primary method)
# ============================================================

def fetch_profile_html_browser():
    """Use Playwright via .venv to render the TikTok profile page with JavaScript.

    Returns the fully-rendered HTML string or None on failure.
    TikTok requires JS rendering for most data; this is the primary fetch method.
    """
    if not VENV_PYTHON.exists():
        print("  [BROWSER] .venv/bin/python3 not found, cannot use Playwright")
        return None

    # Build the Playwright script inline
    cookies_json_str = "[]"
    pw_cookies = load_playwright_cookies()
    if pw_cookies:
        cookies_json_str = json.dumps(pw_cookies, ensure_ascii=False)

    script_content = f'''
import json, sys
try:
    from playwright.sync_api import sync_playwright
    cookies = json.loads({repr(cookies_json_str)})
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="{USER_AGENT}",
            viewport={{"width": 1280, "height": 720}},
            locale="ja-JP",
        )
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        page.goto(
            "https://www.tiktok.com/@{TIKTOK_USERNAME}",
            wait_until="networkidle",
            timeout=45000
        )
        # Wait for content to load
        page.wait_for_timeout(5000)
        # Scroll down slightly to trigger lazy-loaded video data
        page.evaluate("window.scrollBy(0, 500)")
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()
        # Use markers to reliably extract HTML from stdout
        print("__HTML_START__")
        print(html)
        print("__HTML_END__")
except Exception as e:
    print(f"BROWSER_ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
'''

    # Write temp script
    script_path = PROJECT_DIR / "content" / "temp_videos" / "_analytics_browser.py"
    script_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        result = subprocess.run(
            [str(VENV_PYTHON), str(script_path)],
            capture_output=True, text=True, timeout=90,
            env={**os.environ, "DISPLAY": ":0"}
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if stderr:
            # Filter out common non-error Playwright/Chromium messages
            real_errors = [
                line for line in stderr.strip().split('\n')
                if line and "BROWSER_ERROR" in line
            ]
            if real_errors:
                print(f"  [BROWSER] stderr: {real_errors[0][:200]}")

        if "__HTML_START__" in stdout and "__HTML_END__" in stdout:
            start = stdout.index("__HTML_START__") + len("__HTML_START__")
            end = stdout.index("__HTML_END__")
            html = stdout[start:end].strip()
            if len(html) > 1000:
                print(f"  [BROWSER] Got {len(html):,} bytes of HTML")
                return html
            else:
                print(f"  [BROWSER] HTML too short ({len(html)} bytes)")
                return None

        print("  [BROWSER] Could not extract HTML from Playwright output")
        return None

    except subprocess.TimeoutExpired:
        print("  [BROWSER] Playwright timed out (90s)")
        return None
    except Exception as e:
        print(f"  [BROWSER] Exception: {e}")
        return None
    finally:
        try:
            script_path.unlink(missing_ok=True)
        except Exception:
            pass


# ============================================================
# Parse TikTok HTML (rehydration JSON extraction)
# ============================================================

def extract_rehydration_json(html):
    """Extract and parse __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON blob from HTML."""
    pattern = r'<script\s+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>\s*(.*?)\s*</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        pattern2 = r'__UNIVERSAL_DATA_FOR_REHYDRATION__\s*=\s*(\{.*?\})\s*;?\s*</script>'
        match = re.search(pattern2, html, re.DOTALL)
        if not match:
            return None

    json_str = match.group(1).strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"  [PARSE] Failed to parse rehydration JSON: {e}")
        return None


def extract_profile_data(rehydration_data):
    """Extract profile-level metrics from the rehydration JSON.

    Returns a dict with keys: followers, following, video_count, heart_count, nickname, signature
    or None on failure.
    """
    if not rehydration_data:
        return None

    default_scope = rehydration_data.get("__DEFAULT_SCOPE__", {})

    user_detail = default_scope.get("webapp.user-detail", {})
    if not user_detail:
        for key in default_scope:
            if "user-detail" in key or "user_detail" in key:
                user_detail = default_scope[key]
                break

    if not user_detail:
        print("  [PARSE] Could not find user-detail in rehydration data")
        available = list(default_scope.keys())[:10]
        print(f"  [PARSE] Available keys: {available}")
        return None

    user_info = user_detail.get("userInfo", {})
    user = user_info.get("user", {})
    stats = user_info.get("stats", {})

    profile = {
        "nickname": user.get("nickname", ""),
        "signature": user.get("signature", ""),
        "unique_id": user.get("uniqueId", TIKTOK_USERNAME),
        "followers": stats.get("followerCount", 0),
        "following": stats.get("followingCount", 0),
        "video_count": stats.get("videoCount", 0),
        "heart_count": (
            stats.get("heartCount", 0)
            or stats.get("heart", 0)
            or stats.get("diggCount", 0)
        ),
    }

    return profile


def extract_video_list(rehydration_data):
    """Extract per-video metrics from the rehydration JSON.

    Returns a list of dicts with keys:
    id, desc, views, likes, comments, shares, create_time, cover_url
    """
    if not rehydration_data:
        return []

    default_scope = rehydration_data.get("__DEFAULT_SCOPE__", {})

    user_detail = default_scope.get("webapp.user-detail", {})
    if not user_detail:
        for key in default_scope:
            if "user-detail" in key or "user_detail" in key:
                user_detail = default_scope[key]
                break

    if not user_detail:
        return []

    # Video list can be in different locations
    video_list_raw = None

    # Path 1: userInfo.user.videoList
    user_info = user_detail.get("userInfo", {})
    video_list_raw = user_info.get("user", {}).get("videoList", None)

    # Path 2: itemList directly under user-detail
    if not video_list_raw:
        video_list_raw = user_detail.get("itemList", None)

    # Path 3: Check any section with itemList
    if not video_list_raw:
        for key in default_scope:
            section = default_scope[key]
            if isinstance(section, dict):
                if "itemList" in section:
                    video_list_raw = section["itemList"]
                    break
                for subkey, subval in section.items():
                    if isinstance(subval, list) and len(subval) > 0:
                        if isinstance(subval[0], dict) and "id" in subval[0]:
                            video_list_raw = subval
                            break

    if not video_list_raw:
        return []

    videos = []
    for item in video_list_raw:
        if not isinstance(item, dict):
            continue

        stats = item.get("stats", {})
        video = {
            "id": item.get("id", ""),
            "desc": item.get("desc", ""),
            "create_time": item.get("createTime", 0),
            "views": stats.get("playCount", 0),
            "likes": stats.get("diggCount", 0),
            "comments": stats.get("commentCount", 0),
            "shares": stats.get("shareCount", 0),
            "cover_url": item.get("video", {}).get("cover", ""),
        }

        if isinstance(video["create_time"], (int, float)) and video["create_time"] > 0:
            try:
                video["create_time_str"] = datetime.fromtimestamp(
                    video["create_time"]
                ).strftime("%Y-%m-%d %H:%M")
            except (OSError, ValueError):
                video["create_time_str"] = str(video["create_time"])
        else:
            video["create_time_str"] = str(video["create_time"])

        videos.append(video)

    return videos


def fallback_profile_from_html(html):
    """Fallback: scrape profile data directly from HTML using regex."""
    profile = {
        "nickname": "",
        "signature": "",
        "unique_id": TIKTOK_USERNAME,
        "followers": 0,
        "following": 0,
        "video_count": 0,
        "heart_count": 0,
    }

    matches = re.findall(r'videoCount["\':]+\s*(\d+)', html)
    if matches:
        profile["video_count"] = max(int(m) for m in matches)

    matches = re.findall(r'followerCount["\':]+\s*(\d+)', html)
    if matches:
        profile["followers"] = max(int(m) for m in matches)

    matches = re.findall(r'followingCount["\':]+\s*(\d+)', html)
    if matches:
        profile["following"] = max(int(m) for m in matches)

    matches = re.findall(r'(?:heartCount|"heart")["\':]+\s*(\d+)', html)
    if matches:
        profile["heart_count"] = max(int(m) for m in matches)

    match = re.search(r'"nickname"\s*:\s*"([^"]+)"', html)
    if match:
        profile["nickname"] = match.group(1)

    return profile


# ============================================================
# Full data fetch orchestration with retry + fallback
# ============================================================

def fetch_tiktok_data():
    """Fetch and parse all TikTok data with retry + browser/curl fallback.

    Strategy:
    1. Try Playwright browser (primary) -- best chance of getting full data
    2. Fall back to curl (lightweight) if Playwright unavailable/fails
    3. Retry up to MAX_RETRIES times with exponential backoff
    4. Log WARNING (not CRITICAL) on browser failures -- bot detection is expected

    Returns (profile_dict, video_list) or (None, []).
    """
    profile = None
    videos = []

    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            wait = BACKOFF_BASE * (2 ** (attempt - 1))
            print(f"  [RETRY] Attempt {attempt + 1}/{MAX_RETRIES} (waiting {wait}s)")
            time.sleep(wait)

        print(f"\nFetching TikTok profile for @{TIKTOK_USERNAME}... (attempt {attempt + 1}/{MAX_RETRIES})")

        # --- Primary: Playwright browser ---
        print("  [BROWSER] Trying Playwright...")
        html = fetch_profile_html_browser()
        if html:
            rehydration = extract_rehydration_json(html)
            if rehydration:
                profile = extract_profile_data(rehydration)
                videos = extract_video_list(rehydration)
                if profile:
                    print(f"  [BROWSER] Success: profile + {len(videos)} videos")
                    break
                else:
                    print("  [WARN] Rehydration JSON found but no profile data")
            else:
                # Try regex fallback on browser HTML
                profile = fallback_profile_from_html(html)
                if profile and profile.get("video_count", 0) > 0:
                    print(f"  [BROWSER] Regex fallback got profile data")
                    break
                print("  [WARN] Browser returned HTML but no parseable data (bot detection likely)")
        else:
            print("  [WARN] Browser fetch returned no HTML")

        # --- Fallback: curl ---
        print("  [CURL] Trying curl fallback...")
        html = fetch_profile_html_curl()
        if html:
            rehydration = extract_rehydration_json(html)
            if rehydration:
                profile = extract_profile_data(rehydration)
                videos = extract_video_list(rehydration)
                if profile:
                    print(f"  [CURL] Success: profile + {len(videos)} videos")
                    break

            profile = fallback_profile_from_html(html)
            if profile and profile.get("video_count", 0) > 0:
                print(f"  [CURL] Regex fallback got profile data")
                break

        print(f"  [WARN] Attempt {attempt + 1} yielded no data")

    if not profile:
        print("[WARN] All fetch methods failed -- this is likely TikTok bot detection, not a system error")
        log_event("analytics_fetch_failed", {
            "attempts": MAX_RETRIES,
            "browser_tried": True,
            "curl_tried": True,
        })

    return profile, videos


# ============================================================
# --status: Display current profile + verification stats
# ============================================================

def show_status():
    """Display TikTok profile stats, verified uploads, and per-video metrics."""

    # Show verification data first (always available)
    print("\n" + "=" * 60)
    print("  Upload Verification Summary")
    print("=" * 60)

    uploads = load_verification_data()
    queue = load_queue_data()

    if uploads:
        # Group by date
        by_date = {}
        for u in uploads:
            ts = u.get("timestamp", "")[:10]
            by_date.setdefault(ts, []).append(u)

        print(f"  Total successful uploads: {len(uploads)}")
        for date_str in sorted(by_date.keys()):
            items = by_date[date_str]
            ids = [i.get("content_id", "?") for i in items]
            print(f"    {date_str}: {len(items)} uploads ({', '.join(ids[:5])}{'...' if len(ids) > 5 else ''})")

    if queue:
        posts = queue.get("posts", [])
        status_counts = {}
        for p in posts:
            s = p.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1
        print(f"\n  Queue status: {json.dumps(status_counts)}")

        # Show posts with performance data
        with_perf = [
            p for p in posts
            if p.get("performance") and p["performance"].get("views") is not None
        ]
        without_perf = [
            p for p in posts
            if p.get("status") == "posted"
            and (not p.get("performance") or p["performance"].get("views") is None)
        ]
        print(f"  Posts with performance data: {len(with_perf)}")
        print(f"  Posted but no performance data: {len(without_perf)}")

    # Now try to fetch live TikTok data
    print("\n" + "=" * 60)
    print(f"  Live TikTok Profile: @{TIKTOK_USERNAME}")
    print("=" * 60)

    profile, videos = fetch_tiktok_data()

    if not profile:
        print("  [WARN] Could not retrieve live profile data")
        print("  This is common due to TikTok bot detection.")
        print("  Upload verification data above is still reliable.\n")
        return True  # Not a failure -- verification data is available

    print(f"  Nickname:    {profile.get('nickname', 'N/A')}")
    print(f"  Followers:   {profile['followers']:,}")
    print(f"  Following:   {profile['following']:,}")
    print(f"  Videos:      {profile['video_count']:,}")
    print(f"  Total Likes: {profile['heart_count']:,}")
    print("=" * 60)

    if videos:
        print(f"\n  Per-video metrics ({len(videos)} videos found):")
        print(f"  {'ID':<22} {'Date':<18} {'Views':>10} {'Likes':>8} {'Comments':>8} {'Shares':>8}")
        print(f"  {'-'*22} {'-'*18} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")

        total_views = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0

        for v in videos:
            vid = v["id"][:20] if len(v["id"]) > 20 else v["id"]
            print(
                f"  {vid:<22} {v.get('create_time_str', 'N/A'):<18} "
                f"{v['views']:>10,} {v['likes']:>8,} "
                f"{v['comments']:>8,} {v['shares']:>8,}"
            )
            total_views += v["views"]
            total_likes += v["likes"]
            total_comments += v["comments"]
            total_shares += v["shares"]

        print(f"  {'-'*22} {'-'*18} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
        print(
            f"  {'TOTAL':<22} {'':<18} "
            f"{total_views:>10,} {total_likes:>8,} "
            f"{total_comments:>8,} {total_shares:>8,}"
        )
    else:
        print("\n  No per-video data available (TikTok may not expose this via scraping)")

    print()
    return True


# ============================================================
# --update: Update posting_queue.json + append KPI
# ============================================================

def update_queue_performance(videos):
    """Match scraped video data back to posting_queue.json entries and update performance.

    Matching strategy:
    1. Match by tiktok_video_id if already set in queue entry
    2. Match by caption substring similarity (first 30 chars of desc vs caption)
    3. Match by posted_at timestamp vs create_time (within 24 hours)

    Uses atomic_json_write for safe writes.
    """
    queue = load_queue_data()
    if not queue:
        print("  [WARN] posting_queue.json not found, skipping queue update")
        return False

    if not videos:
        print("  No video data to match against queue")
        return False

    posted_entries = [
        p for p in queue.get("posts", [])
        if p.get("status") in ("posted", "deleted_from_tiktok")
    ]
    if not posted_entries:
        print("  No posted entries in queue to update")
        return False

    updated_count = 0

    for entry in posted_entries:
        caption = entry.get("caption", "")
        caption_prefix = re.sub(r'\s+', '', caption)[:30]

        best_match = None
        best_score = 0

        for video in videos:
            score = 0

            # Priority 1: match by tiktok_video_id
            if entry.get("tiktok_video_id") and entry["tiktok_video_id"] == video.get("id"):
                score = 10

            else:
                desc = video.get("desc", "")
                desc_normalized = re.sub(r'\s+', '', desc)

                # Caption prefix match
                if caption_prefix and len(caption_prefix) >= 15 and caption_prefix[:15] in desc_normalized:
                    score = 3
                elif desc_normalized and len(desc_normalized) >= 15 and desc_normalized[:15] in re.sub(r'\s+', '', caption):
                    score = 2

                # Time proximity bonus
                if entry.get("posted_at") and video.get("create_time"):
                    try:
                        posted_dt = datetime.fromisoformat(entry["posted_at"])
                        video_dt = datetime.fromtimestamp(video["create_time"])
                        diff_hours = abs((posted_dt - video_dt).total_seconds()) / 3600
                        if diff_hours < 24:
                            score += 1
                    except (ValueError, OSError, TypeError):
                        pass

            if score > best_score:
                best_score = score
                best_match = video

        if best_match and best_score >= 1:
            entry["performance"] = {
                "views": best_match["views"],
                "likes": best_match["likes"],
                "comments": best_match["comments"],
                "shares": best_match.get("shares", None),
                "saves": None,  # TikTok public page doesn't expose save count
                "last_checked": datetime.now().isoformat(),
            }
            if best_match.get("id"):
                entry["tiktok_video_id"] = best_match["id"]
            updated_count += 1
            cid = entry.get('content_id', entry.get('id', '?'))
            print(f"    Matched {cid} -> views={best_match['views']}, likes={best_match['likes']}")
        else:
            cid = entry.get('content_id', entry.get('id', '?'))
            print(f"    No match for {cid}")

    if updated_count > 0:
        queue["updated"] = datetime.now().isoformat()
        atomic_json_write(QUEUE_FILE, queue)
        print(f"  Updated {updated_count} entries in posting_queue.json (atomic write)")

    return updated_count > 0


def compute_total_views(profile, videos):
    """Sum per-video views for total, or return 0 if no video data."""
    if videos:
        return sum(v.get("views", 0) for v in videos)
    return 0


def append_kpi(profile, videos):
    """Append today's KPI row to data/kpi_log.csv.

    CSV columns: date,tiktok_followers,tiktok_videos,tiktok_total_views,tiktok_total_likes,lp_visitors,line_registrations
    """
    if not profile:
        print("  [WARN] No profile data, cannot append KPI")
        return False

    KPI_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    total_views = compute_total_views(profile, videos)

    # Read existing data
    existing_rows = []
    today_index = -1

    if KPI_FILE.exists():
        with open(KPI_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                existing_rows.append(row)
                if row and row[0] == today:
                    today_index = i

    new_row = [
        today,
        str(profile.get("followers", 0)),
        str(profile.get("video_count", 0)),
        str(total_views),
        str(profile.get("heart_count", 0)),
        "0",  # lp_visitors
        "0",  # line_registrations
    ]

    if today_index >= 0:
        old_row = existing_rows[today_index]
        if len(old_row) >= 6 and old_row[5] != "0":
            new_row[5] = old_row[5]
        if len(old_row) >= 7 and old_row[6] != "0":
            new_row[6] = old_row[6]
        existing_rows[today_index] = new_row

        # Atomic write for CSV
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=KPI_FILE.parent, suffix='.tmp', prefix='kpi_log_'
            )
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for row in existing_rows:
                    writer.writerow(row)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, KPI_FILE)
        except Exception:
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            raise
        print(f"  Updated KPI for {today} in {KPI_FILE.name}")
    else:
        with open(KPI_FILE, 'a', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(new_row)
        print(f"  Appended KPI for {today} to {KPI_FILE.name}")

    print(f"    followers={profile.get('followers', 0)}, "
          f"videos={profile.get('video_count', 0)}, "
          f"total_views={total_views}, "
          f"total_likes={profile.get('heart_count', 0)}")

    return True


def cmd_update():
    """--update: Full update cycle.

    1. Load upload_verification.json to confirm which posts exist
    2. Fetch live TikTok data (Playwright -> curl, with retries)
    3. Update posting_queue.json with performance data
    4. Append KPI row
    """
    # Step 0: Show verification summary
    uploads = load_verification_data()
    posted_ids = get_posted_content_ids()
    print(f"\n  Tracked posts (from verification + queue): {len(posted_ids)}")
    if posted_ids:
        for cid in sorted(posted_ids):
            print(f"    - {cid}")

    # Step 1: Fetch live data
    profile, videos = fetch_tiktok_data()

    if profile:
        print(f"\n  Profile: @{profile.get('unique_id', TIKTOK_USERNAME)}")
        print(f"  Followers: {profile['followers']}, Videos: {profile['video_count']}, "
              f"Hearts: {profile['heart_count']}")
        print(f"  Videos scraped: {len(videos)}")
    else:
        print("\n  [WARN] Could not retrieve live profile data")
        print("  Skipping performance update (no live data to match)")
        print("  Upload verification data confirms posts were uploaded successfully.")
        log_event("analytics_update_partial", {
            "reason": "profile_fetch_failed",
            "tracked_posts": len(posted_ids),
        })
        # Still log something useful
        _log_verification_summary(uploads)
        return True  # Not a hard failure

    # Step 2: Update posting_queue.json
    print(f"\n  Updating posting_queue.json...")
    queue_updated = update_queue_performance(videos)

    # Step 3: Append KPI
    print(f"\n  Appending to kpi_log.csv...")
    kpi_updated = append_kpi(profile, videos)

    # Log the event
    log_event("analytics_update", {
        "profile": profile,
        "videos_found": len(videos),
        "queue_updated": queue_updated,
        "kpi_updated": kpi_updated,
        "tracked_posts": len(posted_ids),
    })

    # Slack summary
    total_views = compute_total_views(profile, videos)
    slack_notify(
        f"*TikTok Analytics Update*\n"
        f"Followers: {profile['followers']:,}\n"
        f"Videos: {profile['video_count']}\n"
        f"Total Views: {total_views:,}\n"
        f"Total Likes: {profile['heart_count']:,}\n"
        f"Videos scraped: {len(videos)}\n"
        f"Tracked uploads: {len(posted_ids)}"
    )

    print("\nDone.")
    return True


def _log_verification_summary(uploads):
    """Log a summary of verification data when live fetch fails."""
    if not uploads:
        return
    latest = uploads[-1] if uploads else {}
    not_deleted = [
        u for u in uploads
        if not u.get("note", "").startswith("user deleted")
    ]
    print(f"\n  Verification summary:")
    print(f"    Total uploads: {len(uploads)}")
    print(f"    Active (not user-deleted): {len(not_deleted)}")
    if latest:
        print(f"    Latest: {latest.get('content_id')} at {latest.get('timestamp', '?')[:19]}")


def cmd_daily_kpi():
    """--daily-kpi: Just fetch profile and append KPI row."""
    profile, videos = fetch_tiktok_data()

    if not profile:
        print("[WARN] Could not retrieve profile data for KPI")
        print("  This is expected if TikTok bot detection is active.")
        return True  # Not a hard failure

    print(f"\n  Profile: followers={profile['followers']}, "
          f"videos={profile['video_count']}, hearts={profile['heart_count']}")

    result = append_kpi(profile, videos)

    log_event("daily_kpi", {
        "profile": profile,
        "videos_found": len(videos),
    })

    print("\nDone.")
    return result


# ============================================================
# Main
# ============================================================

def main():
    load_env()

    parser = argparse.ArgumentParser(
        description="TikTok Analytics Collection v3.0 - @nurse_robby"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Show TikTok profile stats, verification data, and per-video metrics"
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Update posting_queue.json performance data + append KPI to CSV"
    )
    parser.add_argument(
        "--daily-kpi", action="store_true",
        help="Just append today's KPI row to kpi_log.csv"
    )

    args = parser.parse_args()

    if args.status:
        success = show_status()
        sys.exit(0 if success else 1)
    elif args.update:
        success = cmd_update()
        sys.exit(0 if success else 1)
    elif args.daily_kpi:
        success = cmd_daily_kpi()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
