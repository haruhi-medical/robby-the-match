#!/usr/bin/env python3
"""
auto_post.py — ナースロビー SNS自動投稿エンジン v2.1

Instagram/TikTokへの自動投稿。AI検出回避 + 行動パターン擬態。
cron駆動で完全自動化。

v2.1 改善:
  - Instagram carousel optimization: 1080x1350 4:5 portrait, pre-sharpen,
    progressive JPEG with 4:4:4 chroma subsampling
  - optimize_for_instagram(): dedicated image optimization for IG carousels
  - validate_instagram_slides(): pre-upload dimension/mode validation
  - prepare_instagram_slides(): generate IG-specific slides from content JSON
  - image_humanizer "carousel" mode: no noise/rotation/dimension change for
    designed graphics (only metadata strip + subtle JPEG quality variation)
  - Proper JPEG conversion & temp file cleanup after upload

v2.0 改善:
  - image_humanizer統合（EXIF偽装+ノイズ+ビネット）
  - 投稿前ウォームアップ（フィード閲覧+いいね）
  - デバイスプロフィール3種ローテーション
  - 投稿後エンゲージメント（自然な滞在行動）
  - コンテンツ形式ローテーション（カルーセル/リール/単画像/ストーリー）
  - 投稿間隔ランダム化（180-600秒）

使い方:
  python3 scripts/auto_post.py --instagram
  python3 scripts/auto_post.py --instagram --format reel
  python3 scripts/auto_post.py --all
  python3 scripts/auto_post.py --status
  python3 scripts/auto_post.py --retry
  python3 scripts/auto_post.py --instagram --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# Constants
# ============================================================

PROJECT_DIR = Path(__file__).parent.parent
QUEUE_FILE = PROJECT_DIR / "data" / "posting_queue.json"
READY_DIR = PROJECT_DIR / "content" / "ready"
TEMP_DIR = PROJECT_DIR / "content" / "temp_instagram"
SESSION_FILE = PROJECT_DIR / "data" / ".instagram_session.json"
POST_LOG_FILE = PROJECT_DIR / "data" / "post_log.json"
ENV_FILE = PROJECT_DIR / ".env"

# Randomized intervals for anti-detection
POST_INTERVAL_MIN = 180   # 3 minutes minimum between posts
POST_INTERVAL_MAX = 600   # 10 minutes maximum
PLATFORM_INTERVAL = 30

# Day-of-week content format schedule for Instagram
# 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
INSTAGRAM_FORMAT_SCHEDULE = {
    0: "carousel",   # 月: カルーセル
    1: "reel",       # 火: リール（TikTok動画流用）
    2: "single",     # 水: 単画像
    3: "carousel",   # 木: カルーセル
    4: "reel",       # 金: リール
    5: "story",      # 土: ストーリーのみ
    6: None,         # 日: 休み
}

# Device profiles for session rotation
DEVICE_PROFILES = [
    {
        "user_agent": "Instagram 302.1.0.36.111 Android (34/14; 420dpi; 1080x2400; Google/google; Pixel 8; shiba; shiba; en_JP; 533450710)",
        "device_name": "Pixel 8",
    },
    {
        "user_agent": "Instagram 302.1.0.36.111 Android (34/14; 480dpi; 1080x2340; samsung; SM-S921B; e1s; s5e9945; en_JP; 533450710)",
        "device_name": "Galaxy S24",
    },
    {
        "user_agent": "Instagram 302.1.0.36.111 Android (33/13; 440dpi; 1080x2340; Sony; XQ-DQ72; pdx245; qcom; en_JP; 533450710)",
        "device_name": "Xperia 1 VI",
    },
]


# ============================================================
# Utilities
# ============================================================

def _get_dominant_color(img) -> tuple:
    """Get the dominant edge color for padding background."""
    from PIL import Image
    small = img.resize((1, 1), Image.LANCZOS)
    return small.getpixel((0, 0))


def atomic_json_write(filepath, data, indent=2):
    """アトミックJSON書き込み（書き込み中クラッシュによるデータ破損を防止）"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Write to temp file in same directory (same filesystem for atomic rename)
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix='.tmp',
            prefix=filepath.stem + '_'
        )
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Atomic rename
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass
        raise


def load_env():
    """Load .env file.

    Called at module level AND in main() to ensure env vars are available
    even in cron environments where .zshrc is not sourced.
    """
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


# Load .env at module level for cron compatibility
load_env()


def slack_notify(message: str):
    """Send Slack notification."""
    try:
        subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "notify_slack.py"),
             "--message", message],
            capture_output=True, timeout=30
        )
    except Exception as e:
        print(f"[WARN] Slack notify failed: {e}")


def load_post_log() -> List[Dict]:
    """Load post log."""
    if POST_LOG_FILE.exists():
        try:
            with open(POST_LOG_FILE) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[WARN] post_log.json破損: {e}")
            return []
    return []


def save_post_log(log: List[Dict]):
    """Save post log（アトミック書き込み）."""
    atomic_json_write(POST_LOG_FILE, log)


def get_ready_dirs() -> List[Path]:
    """Get all content/ready/ directories sorted by name."""
    if not READY_DIR.exists():
        return []
    return sorted([d for d in READY_DIR.iterdir() if d.is_dir()])


def get_next_unposted(platform: str) -> Optional[Path]:
    """Get next unposted content directory for given platform."""
    log = load_post_log()
    posted_dirs = {
        entry["dir"]
        for entry in log
        if entry.get("platform") == platform and entry.get("status") == "success"
    }

    for d in get_ready_dirs():
        if d.name not in posted_dirs:
            return d
    return None


# ============================================================
# Instagram Image Optimization
# ============================================================

def optimize_for_instagram(img_path: str, output_path: str) -> str:
    """Optimize image for Instagram carousel upload.

    Ensures correct dimensions (1080x1350, 4:5 portrait), RGB mode,
    pre-sharpens to compensate for Instagram compression, and saves
    as an optimized progressive JPEG with 4:4:4 chroma subsampling
    (better for text-heavy carousel slides).
    """
    from PIL import Image, ImageFilter

    img = Image.open(img_path)

    # Ensure RGB (no alpha channel)
    if img.mode in ('RGBA', 'P'):
        if img.mode == 'RGBA':
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert('RGB')

    # Validate/enforce 1080x1350 (4:5 portrait)
    target_w, target_h = 1080, 1350
    if img.size != (target_w, target_h):
        w, h = img.size
        # If TikTok 9:16 (1080x1920), crop center instead of resize to avoid text distortion
        if w == target_w and h > target_h:
            # Center crop vertically (keep text area, trim top/bottom safe zones)
            crop_top = (h - target_h) // 3  # Bias toward top (content is usually upper-center)
            img = img.crop((0, crop_top, w, crop_top + target_h))
        elif h == target_h and w > target_w:
            # Center crop horizontally
            crop_left = (w - target_w) // 2
            img = img.crop((crop_left, 0, crop_left + target_w, h))
        else:
            # Different aspect ratio: fit within target, pad with background color
            img.thumbnail((target_w, target_h), Image.LANCZOS)
            bg = Image.new("RGB", (target_w, target_h), _get_dominant_color(img))
            paste_x = (target_w - img.width) // 2
            paste_y = (target_h - img.height) // 2
            bg.paste(img, (paste_x, paste_y))
            img = bg

    # Pre-sharpen to compensate for Instagram compression
    img = img.filter(ImageFilter.UnsharpMask(radius=1.0, percent=50, threshold=2))

    # Save as optimized JPEG
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(
        output_path,
        format="JPEG",
        quality=85,
        optimize=True,
        progressive=True,
        subsampling=0,  # 4:4:4 chroma (better for text)
    )
    return output_path


def validate_instagram_slides(slide_paths: List[Path]) -> List[str]:
    """Validate all slides are correct size for Instagram carousel.

    Returns a list of issue strings. Empty list means all slides are valid.
    """
    from PIL import Image

    issues = []
    for path in slide_paths:
        try:
            img = Image.open(path)
            w, h = img.size
            if w != 1080 or h != 1350:
                issues.append(f"{path}: {w}x{h} (expected 1080x1350)")
            if img.mode not in ('RGB', 'L'):
                issues.append(f"{path}: mode={img.mode} (expected RGB)")
        except Exception as e:
            issues.append(f"{path}: failed to open ({e})")
    return issues


def prepare_instagram_slides(content_dir: Path) -> Optional[List[Path]]:
    """Generate Instagram-optimized slides from content directory.

    Attempts to call generate_carousel.py with --platform instagram.
    Falls back to None if generation fails (caller should use existing slides).
    """
    # Look for content JSON files
    json_files = list(content_dir.glob("*.json"))
    if not json_files:
        print("[IG-PREP] No JSON content file found, skipping IG slide generation")
        return None

    carousel_script = PROJECT_DIR / "scripts" / "generate_carousel.py"
    if not carousel_script.exists():
        print("[IG-PREP] generate_carousel.py not found, skipping IG slide generation")
        return None

    ig_dir = content_dir / "instagram"
    ig_dir.mkdir(exist_ok=True)

    try:
        result = subprocess.run(
            [sys.executable, str(carousel_script),
             "--single-json", str(json_files[0]),
             "--platform", "instagram",
             "--output", str(ig_dir)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            print(f"[IG-PREP] generate_carousel.py failed (exit={result.returncode})")
            if result.stderr:
                print(f"[IG-PREP] stderr: {result.stderr[:300]}")
            return None
    except Exception as e:
        print(f"[IG-PREP] generate_carousel.py error: {e}")
        return None

    if ig_dir.exists():
        # generate_carousel.py outputs to a subdirectory (carousel_YYYYMMDD_ID/)
        slides = sorted(ig_dir.glob("*.png")) or sorted(ig_dir.glob("*.jpg"))
        if not slides:
            # Search subdirectories
            slides = sorted(ig_dir.glob("**/*.png")) or sorted(ig_dir.glob("**/*.jpg"))
        if slides:
            print(f"[IG-PREP] Generated {len(slides)} Instagram-optimized slides")
            return slides

    print("[IG-PREP] No slides generated in instagram/ directory")
    return None


# ============================================================
# Instagram Posting
# ============================================================

def get_device_profile() -> Dict:
    """Get device profile based on day of year (rotates daily)."""
    day_of_year = datetime.now().timetuple().tm_yday
    return DEVICE_PROFILES[day_of_year % len(DEVICE_PROFILES)]


def get_today_format() -> Optional[str]:
    """Get today's Instagram content format."""
    weekday = datetime.now().weekday()
    return INSTAGRAM_FORMAT_SCHEDULE.get(weekday, "carousel")


def instagram_login():
    """Login to Instagram with device rotation and session reuse."""
    from instagrapi import Client

    cl = Client()
    cl.delay_range = [2, 5]

    device = get_device_profile()
    print(f"[IG] Device: {device['device_name']}")

    # Try loading existing session
    if SESSION_FILE.exists():
        try:
            cl.load_settings(str(SESSION_FILE))
            cl.login(
                os.environ.get("INSTAGRAM_USERNAME", "robby.for.nurse"),
                os.environ.get("INSTAGRAM_PASSWORD", "")
            )
            print(f"[IG] Session loaded. User: {cl.username}")
            return cl
        except Exception as e:
            print(f"[IG] Session expired, re-logging in: {e}")

    # Fresh login with rotated device profile
    cl.set_settings({
        "user_agent": device["user_agent"],
        "country": "JP",
        "country_code": 81,
        "locale": "ja_JP",
        "timezone_offset": 32400,
    })

    cl.login(
        os.environ.get("INSTAGRAM_USERNAME", "robby.for.nurse"),
        os.environ.get("INSTAGRAM_PASSWORD", "")
    )
    cl.dump_settings(str(SESSION_FILE))
    print(f"[IG] Fresh login. User: {cl.username}")
    return cl


def warm_up_session(cl, dry_run: bool = False):
    """Simulate human behavior before posting (anti-bot detection)."""
    print("[IG] Warm-up: simulating human browsing...")

    if dry_run:
        print("[IG] Warm-up: DRY RUN — skipping actual API calls")
        return

    try:
        # 1. View own profile
        cl.user_info_by_username(cl.username)
        time.sleep(random.uniform(2, 5))

        # 2. Browse timeline feed
        cl.get_timeline_feed()
        time.sleep(random.uniform(3, 8))

        # 3. Like 1-2 posts from nursing hashtags
        nursing_tags = ["看護師あるある", "ナース", "看護師転職", "夜勤あるある", "看護師の日常"]
        tag = random.choice(nursing_tags)
        try:
            medias = cl.hashtag_medias_recent(tag, amount=5)
            like_count = random.randint(1, 2)
            for media in medias[:like_count]:
                cl.media_like(media.id)
                print(f"[IG] Warm-up: liked post from #{tag}")
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            print(f"[IG] Warm-up: hashtag browse failed (non-critical): {e}")

    except Exception as e:
        print(f"[IG] Warm-up: error (non-critical): {e}")


def post_engagement(cl, media_id: str, dry_run: bool = False):
    """Post-posting behavior to appear human."""
    if dry_run:
        return

    try:
        time.sleep(random.uniform(5, 15))
        # Check own post
        cl.media_info(media_id)
        time.sleep(random.uniform(10, 30))
        # Browse feed briefly
        cl.get_timeline_feed()
    except Exception:
        pass  # Non-critical


def convert_to_jpeg(png_paths: List[Path], humanize: bool = True,
                    for_carousel: bool = False) -> List[str]:
    """Convert PNG slides to JPEG with optional humanization for anti-AI detection.

    Args:
        png_paths: List of PNG image paths to convert.
        humanize: Whether to apply humanization.
        for_carousel: If True, use Instagram carousel optimization instead of
                      full humanization. This preserves exact dimensions and
                      clean text rendering. image_humanizer's "carousel" mode
                      is used (metadata strip + subtle JPEG quality variation only).
    """
    TEMP_DIR.mkdir(exist_ok=True)
    jpeg_paths = []

    for png in png_paths:
        jpeg_path = TEMP_DIR / png.name.replace(".png", ".jpg").replace(".PNG", ".jpg")

        if for_carousel:
            # Instagram carousel: optimize without degrading designed graphics
            optimize_for_instagram(str(png), str(jpeg_path))
            print(f"  [IG-OPT] {png.name}: optimized for Instagram (1080x1350, JPEG q85)")
        elif humanize:
            try:
                from image_humanizer import humanize_image
                info = humanize_image(str(png), str(jpeg_path), intensity="medium")
                print(f"  [HUM] {png.name}: noise={info['noise_sigma']}, exif={info['exif_injected']}")
            except ImportError:
                print("[WARN] image_humanizer not available, using basic conversion")
                from PIL import Image
                img = Image.open(png).convert("RGB")
                img.save(str(jpeg_path), "JPEG", quality=random.randint(89, 93))
        else:
            from PIL import Image
            img = Image.open(png).convert("RGB")
            img.save(str(jpeg_path), "JPEG", quality=95)

        jpeg_paths.append(str(jpeg_path))

    return jpeg_paths


def post_to_instagram(content_dir: Path, dry_run: bool = False,
                      format_override: Optional[str] = None) -> Dict:
    """Post to Instagram with format rotation + anti-detection.

    Slide preparation flow:
    1. Try to generate Instagram-specific slides (1080x1350) via generate_carousel.py
    2. Fall back to existing TikTok-format slides in content_dir
    3. Convert all slides to optimized JPEG (no destructive humanization for carousels)
    4. Validate dimensions before upload
    """
    # --- Step 1: Prepare Instagram-optimized slides ---
    # Try to generate Instagram-specific slides from content JSON
    ig_slides = prepare_instagram_slides(content_dir)

    if ig_slides:
        slides = ig_slides
        print(f"[IG] Using Instagram-optimized slides ({len(slides)} slides)")
    else:
        # Fall back to existing slides in content_dir (may be TikTok format)
        slides = sorted(content_dir.glob("slide_*.png"))
        if not slides:
            # Also check for jpg slides
            slides = sorted(content_dir.glob("slide_*.jpg"))
        if slides:
            print(f"[IG] Using existing slides from {content_dir.name} ({len(slides)} slides)")
        else:
            return {"status": "error", "error": "No slides found"}

    caption_file = content_dir / "caption.txt"
    hashtags_file = content_dir / "hashtags.txt"

    caption = caption_file.read_text().strip() if caption_file.exists() else ""
    hashtags = hashtags_file.read_text().strip() if hashtags_file.exists() else ""
    full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption

    # Determine format
    post_format = format_override or get_today_format()
    if post_format is None:
        print("[IG] Today is a rest day (Sunday). Skipping.")
        return {"status": "skipped", "reason": "rest_day"}

    print(f"[IG] Content: {content_dir.name}")
    print(f"[IG] Format: {post_format}")
    print(f"[IG] Slides: {len(slides)}")
    print(f"[IG] Caption: {full_caption[:80]}...")

    if dry_run:
        print("[IG] DRY RUN - skipping actual upload")
        return {"status": "dry_run", "slides": len(slides), "format": post_format}

    try:
        cl = instagram_login()

        # Pre-posting warm-up (anti-bot)
        warm_up_session(cl, dry_run)

        # --- Step 2: Convert slides to optimized JPEG ---
        # Use carousel optimization for carousel/single formats (designed graphics).
        # Use full humanization only for reel thumbnails (AI-generated photographs).
        is_carousel_format = post_format in ("carousel", "single", "story")
        jpeg_paths = convert_to_jpeg(slides, humanize=not is_carousel_format,
                                     for_carousel=is_carousel_format)

        # --- Step 3: Validate slides before upload ---
        validation_issues = validate_instagram_slides(
            [Path(p) for p in jpeg_paths]
        )
        if validation_issues:
            print(f"[IG] Validation issues found ({len(validation_issues)}):")
            for issue in validation_issues:
                print(f"  [WARN] {issue}")
            # Try to fix by re-optimizing (resize to correct dimensions)
            print("[IG] Attempting to fix dimensions...")
            fixed_paths = []
            for jp in jpeg_paths:
                optimize_for_instagram(jp, jp)  # Re-optimize in place
                fixed_paths.append(jp)
            jpeg_paths = fixed_paths
            # Re-validate
            remaining_issues = validate_instagram_slides(
                [Path(p) for p in jpeg_paths]
            )
            if remaining_issues:
                print(f"[IG] {len(remaining_issues)} issues remain after fix attempt")
                for issue in remaining_issues:
                    print(f"  [ERR] {issue}")
                # Continue anyway — Instagram may accept slightly off dimensions

        # --- Step 4: Upload based on format ---
        media = None
        if post_format == "carousel":
            media = cl.album_upload(paths=jpeg_paths, caption=full_caption)

        elif post_format == "single":
            # Post just the hook slide (first slide)
            media = cl.photo_upload(path=jpeg_paths[0], caption=full_caption)

        elif post_format == "reel":
            # Look for video file (TikTok reuse)
            video_dir = PROJECT_DIR / "content" / "temp_videos"
            videos = sorted(video_dir.glob("*.mp4")) if video_dir.exists() else []
            if videos:
                media = cl.clip_upload(path=str(videos[-1]), caption=full_caption)
            else:
                # Fallback to carousel if no video available
                print("[IG] No video for Reel. Falling back to carousel.")
                media = cl.album_upload(paths=jpeg_paths, caption=full_caption)

        elif post_format == "story":
            # Post hook slide as story
            cl.photo_upload_to_story(path=jpeg_paths[0])
            print("[IG] Story posted (no permalink)")
            cl.dump_settings(str(SESSION_FILE))
            _cleanup_temp_jpegs(jpeg_paths)
            return {"status": "success", "format": "story"}

        if media is None:
            _cleanup_temp_jpegs(jpeg_paths)
            return {"status": "error", "error": "Upload returned None"}

        url = f"https://www.instagram.com/p/{media.code}/"
        print(f"[IG] SUCCESS: {url}")

        # Post-posting engagement (appear human)
        post_engagement(cl, str(media.id), dry_run)

        cl.dump_settings(str(SESSION_FILE))

        # Cleanup temporary JPEG files
        _cleanup_temp_jpegs(jpeg_paths)

        return {
            "status": "success",
            "media_id": str(media.id),
            "code": media.code,
            "url": url,
            "format": post_format,
        }
    except Exception as e:
        error_msg = str(e)
        print(f"[IG] FAILED: {error_msg}")

        # Rate limit retry
        if "inactive" in error_msg.lower() or "429" in error_msg:
            wait_time = random.randint(120, 300)
            print(f"[IG] Rate limited. Waiting {wait_time}s and retrying...")
            time.sleep(wait_time)
            try:
                cl = instagram_login()
                jpeg_paths = convert_to_jpeg(slides, humanize=False,
                                             for_carousel=True)
                media = cl.album_upload(paths=jpeg_paths, caption=full_caption)
                url = f"https://www.instagram.com/p/{media.code}/"
                print(f"[IG] RETRY SUCCESS: {url}")
                cl.dump_settings(str(SESSION_FILE))
                _cleanup_temp_jpegs(jpeg_paths)
                return {
                    "status": "success",
                    "media_id": str(media.id),
                    "code": media.code,
                    "url": url,
                    "format": post_format,
                }
            except Exception as retry_e:
                return {"status": "error", "error": str(retry_e)}

        return {"status": "error", "error": error_msg}


def _cleanup_temp_jpegs(jpeg_paths: List[str]):
    """Remove temporary JPEG files after upload."""
    for jp in jpeg_paths:
        try:
            Path(jp).unlink(missing_ok=True)
        except Exception:
            pass


# ============================================================
# TikTok Posting (Slack通知 + 手動アップ待ち)
# ============================================================

def post_to_tiktok(content_dir: Path, dry_run: bool = False) -> Dict:
    """Prepare TikTok carousel and notify via Slack."""
    slides = sorted(content_dir.glob("slide_*.png"))
    if not slides:
        return {"status": "error", "error": "No slides found"}

    caption_file = content_dir / "caption.txt"
    hashtags_file = content_dir / "hashtags.txt"

    caption = caption_file.read_text().strip() if caption_file.exists() else ""
    hashtags = hashtags_file.read_text().strip() if hashtags_file.exists() else ""
    full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption

    print(f"[TT] Content: {content_dir.name}")
    print(f"[TT] Slides: {len(slides)}")

    if dry_run:
        print("[TT] DRY RUN - skipping")
        return {"status": "dry_run"}

    # Notify Slack with caption and instructions
    msg = (
        f"📱 *TikTok投稿準備完了*\n"
        f"フォルダ: `content/ready/{content_dir.name}/`\n"
        f"スライド: {len(slides)}枚\n\n"
        f"*キャプション:*\n{full_caption}\n\n"
        f"👉 TikTokアプリでカルーセル投稿してください\n"
        f"投稿後: `python3 scripts/auto_post.py --mark-posted {content_dir.name} tiktok`"
    )
    slack_notify(msg)
    print("[TT] Slack notification sent")

    return {"status": "notified", "message": "Slack notification sent for manual upload"}


# ============================================================
# Main Logic
# ============================================================

def post_next(platforms: List[str], dry_run: bool = False,
              format_override: Optional[str] = None) -> List[Dict]:
    """Post next unposted content to specified platforms."""
    results = []
    log = load_post_log()

    for platform in platforms:
        content_dir = get_next_unposted(platform)
        if not content_dir:
            print(f"[{platform.upper()}] No unposted content available")
            results.append({
                "platform": platform,
                "status": "no_content",
            })
            continue

        if platform == "instagram":
            result = post_to_instagram(content_dir, dry_run, format_override)
        elif platform == "tiktok":
            result = post_to_tiktok(content_dir, dry_run)
        else:
            result = {"status": "error", "error": f"Unknown platform: {platform}"}

        # Log the result
        entry = {
            "platform": platform,
            "dir": content_dir.name,
            "timestamp": datetime.now().isoformat(),
            **result,
        }
        log.append(entry)
        results.append(entry)

        # Randomized wait between platforms (anti-detection)
        if len(platforms) > 1:
            wait = random.randint(PLATFORM_INTERVAL, PLATFORM_INTERVAL * 3)
            print(f"[WAIT] {wait}s between platforms...")
            time.sleep(wait)

    save_post_log(log)
    return results


def retry_failed(dry_run: bool = False) -> List[Dict]:
    """Retry all failed posts."""
    log = load_post_log()
    failed = [e for e in log if e.get("status") == "error"]

    if not failed:
        print("No failed posts to retry")
        return []

    results = []
    for entry in failed:
        content_dir = READY_DIR / entry["dir"]
        if not content_dir.exists():
            print(f"Content dir not found: {entry['dir']}")
            continue

        platform = entry["platform"]
        print(f"\nRetrying: {entry['dir']} on {platform}")

        if platform == "instagram":
            result = post_to_instagram(content_dir, dry_run)
        elif platform == "tiktok":
            result = post_to_tiktok(content_dir, dry_run)
        else:
            continue

        new_entry = {
            "platform": platform,
            "dir": entry["dir"],
            "timestamp": datetime.now().isoformat(),
            "retry": True,
            **result,
        }
        log.append(new_entry)
        results.append(new_entry)
        time.sleep(random.randint(POST_INTERVAL_MIN, POST_INTERVAL_MAX))

    save_post_log(log)
    return results


def mark_posted(dir_name: str, platform: str):
    """Manually mark a post as completed (for TikTok manual uploads)."""
    log = load_post_log()
    log.append({
        "platform": platform,
        "dir": dir_name,
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "manual": True,
    })
    save_post_log(log)
    print(f"Marked {dir_name} as posted on {platform}")


def show_status():
    """Show posting status."""
    log = load_post_log()
    dirs = get_ready_dirs()

    print(f"\n{'='*60}")
    print(f"SNS投稿ステータス ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    print(f"{'='*60}")
    print(f"準備済みコンテンツ: {len(dirs)}")

    for d in dirs:
        ig_status = "⬜"
        tt_status = "⬜"
        for entry in log:
            if entry.get("dir") == d.name:
                if entry["platform"] == "instagram":
                    if entry["status"] == "success":
                        ig_status = f"✅ {entry.get('url', '')}"
                    elif entry["status"] == "error":
                        ig_status = "❌"
                elif entry["platform"] == "tiktok":
                    if entry["status"] == "success":
                        tt_status = "✅"
                    elif entry["status"] == "notified":
                        tt_status = "📱待ち"
                    elif entry["status"] == "error":
                        tt_status = "❌"

        print(f"\n  {d.name}:")
        print(f"    IG: {ig_status}")
        print(f"    TT: {tt_status}")

    print(f"\n{'='*60}")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="ナースロビー SNS自動投稿")
    parser.add_argument("--instagram", action="store_true", help="Post to Instagram")
    parser.add_argument("--tiktok", action="store_true", help="Post to TikTok")
    parser.add_argument("--all", action="store_true", help="Post to all platforms")
    parser.add_argument("--retry", action="store_true", help="Retry failed posts")
    parser.add_argument("--status", action="store_true", help="Show posting status")
    parser.add_argument("--mark-posted", nargs=2, metavar=("DIR", "PLATFORM"),
                       help="Mark a post as completed")
    parser.add_argument("--format", choices=["carousel", "reel", "single", "story"],
                       help="Override Instagram content format")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no actual posting)")

    args = parser.parse_args()

    load_env()

    # Add scripts dir to path for image_humanizer import
    sys.path.insert(0, str(PROJECT_DIR / "scripts"))

    if args.status:
        show_status()
        return

    if args.mark_posted:
        mark_posted(args.mark_posted[0], args.mark_posted[1])
        return

    if args.retry:
        results = retry_failed(args.dry_run)
        for r in results:
            print(f"  [{r['platform']}] {r['dir']}: {r['status']}")
        return

    platforms = []
    if args.all:
        platforms = ["instagram", "tiktok"]
    else:
        if args.instagram:
            platforms.append("instagram")
        if args.tiktok:
            platforms.append("tiktok")

    if not platforms:
        parser.print_help()
        return

    results = post_next(platforms, args.dry_run, args.format)

    # Summary
    success = sum(1 for r in results if r.get("status") == "success")
    failed = sum(1 for r in results if r.get("status") == "error")
    print(f"\n=== Summary: {success} success, {failed} failed ===")

    # Slack summary
    if success > 0:
        urls = [r.get("url", "") for r in results if r.get("url")]
        slack_notify(
            f"✅ SNS自動投稿完了: {success}件成功\n" +
            "\n".join(urls)
        )


if __name__ == "__main__":
    main()
