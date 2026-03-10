#!/usr/bin/env python3
"""
download_bgm.py — BGM管理スクリプト for 神奈川ナース転職 TikTok動画

使い方:
  python3 scripts/download_bgm.py --generate-placeholders   # ffmpegでプレースホルダー生成
  python3 scripts/download_bgm.py --list                     # 現在のBGMファイル一覧
  python3 scripts/download_bgm.py --validate                 # BGMファイルの整合性チェック

プレースホルダーはサイン波ベースのトーン（15秒）。
実際のロイヤリティフリーBGMに差し替えるまでのパイプライン維持用。

ロイヤリティフリーBGM取得先:
  - Pixabay Music: https://pixabay.com/music/
  - FreePD: https://freepd.com/
  - Uppbeat: https://uppbeat.io/
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
BGM_DIR = PROJECT_DIR / "content" / "bgm"

# BGM track definitions
BGM_TRACKS = {
    "bgm_calm.mp3": {
        "style": "Calm lo-fi",
        "frequency": 220,
        "tremolo_freq": 2,
        "tremolo_depth": 0.3,
        "volume": 0.3,
        "fade_in": 1,
        "fade_out": 2,
        "description": "Slow gentle tone for あるある/emotional posts",
        "extra_filters": "",
    },
    "bgm_upbeat.mp3": {
        "style": "Upbeat motivational",
        "frequency": 440,
        "tremolo_freq": 6,
        "tremolo_depth": 0.5,
        "volume": 0.4,
        "fade_in": 0.5,
        "fade_out": 2,
        "description": "Pulsing energetic tone for career success posts",
        "extra_filters": "",
    },
    "bgm_emotional.mp3": {
        "style": "Emotional piano",
        "frequency": 330,
        "tremolo_freq": 1,
        "tremolo_depth": 0.2,
        "volume": 0.25,
        "fade_in": 3,
        "fade_out": 4,
        "description": "Warm low tone for deep empathy/patient stories",
        "extra_filters": "",
    },
    "bgm_chill.mp3": {
        "style": "Chill acoustic",
        "frequency": 262,
        "tremolo_freq": 3,
        "tremolo_depth": 0.4,
        "volume": 0.3,
        "fade_in": 2,
        "fade_out": 3,
        "description": "Soft filtered tone for regional/lifestyle posts",
        "extra_filters": ",lowpass=f=800",
    },
    "bgm_energetic.mp3": {
        "style": "Energetic pop",
        "frequency": 523,
        "tremolo_freq": 8,
        "tremolo_depth": 0.6,
        "volume": 0.35,
        "fade_in": 0.3,
        "fade_out": 2,
        "description": "Fast pulsing tone for trend/buzz posts",
        "extra_filters": "",
    },
}

DURATION = 15  # seconds


def check_ffmpeg():
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def generate_placeholder(filename: str, track: dict, force: bool = False) -> bool:
    """Generate a single placeholder BGM track using ffmpeg."""
    output_path = BGM_DIR / filename

    if output_path.exists() and not force:
        print(f"  [SKIP] {filename} already exists (use --force to overwrite)")
        return True

    fade_out_start = DURATION - track["fade_out"]
    af_filters = (
        f"volume={track['volume']},"
        f"afade=t=in:st=0:d={track['fade_in']},"
        f"afade=t=out:st={fade_out_start}:d={track['fade_out']},"
        f"tremolo=f={track['tremolo_freq']}:d={track['tremolo_depth']}"
        f"{track['extra_filters']}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"sine=frequency={track['frequency']}:duration={DURATION}",
        "-af", af_filters,
        "-b:a", "128k",
        str(output_path),
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            size_kb = output_path.stat().st_size / 1024
            print(f"  [OK] {filename} ({track['style']}, {size_kb:.0f}KB)")
            return True
        else:
            print(f"  [FAIL] {filename}: {result.stderr[-200:]}")
            return False
    except Exception as e:
        print(f"  [FAIL] {filename}: {e}")
        return False


def cmd_generate_placeholders(force: bool = False):
    """Generate all placeholder BGM tracks."""
    if not check_ffmpeg():
        print("[ERROR] ffmpeg not found. Install with: brew install ffmpeg")
        sys.exit(1)

    BGM_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {len(BGM_TRACKS)} placeholder BGM tracks ({DURATION}s each)...")
    success = 0
    for filename, track in BGM_TRACKS.items():
        if generate_placeholder(filename, track, force):
            success += 1

    print(f"\nDone: {success}/{len(BGM_TRACKS)} tracks ready in {BGM_DIR}")
    if success < len(BGM_TRACKS):
        sys.exit(1)


def cmd_list():
    """List all BGM files in the bgm directory."""
    if not BGM_DIR.exists():
        print("BGM directory does not exist yet.")
        return

    mp3_files = sorted(BGM_DIR.glob("*.mp3"))
    if not mp3_files:
        print("No .mp3 files found in content/bgm/")
        print("Run: python3 scripts/download_bgm.py --generate-placeholders")
        return

    print(f"BGM tracks in {BGM_DIR}:\n")
    for f in mp3_files:
        size_kb = f.stat().st_size / 1024
        track_info = BGM_TRACKS.get(f.name, {})
        style = track_info.get("style", "Unknown")
        desc = track_info.get("description", "")
        print(f"  {f.name:25s} {size_kb:6.0f}KB  [{style}] {desc}")

    print(f"\nTotal: {len(mp3_files)} tracks")


def cmd_validate():
    """Validate that all required BGM files exist and are valid."""
    if not BGM_DIR.exists():
        print("[FAIL] BGM directory does not exist")
        sys.exit(1)

    all_ok = True
    for filename in BGM_TRACKS:
        path = BGM_DIR / filename
        if not path.exists():
            print(f"  [MISSING] {filename}")
            all_ok = False
        elif path.stat().st_size < 1000:
            print(f"  [CORRUPT] {filename} (too small: {path.stat().st_size} bytes)")
            all_ok = False
        else:
            # Check if ffprobe can read it
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-show_format", "-of", "json", str(path)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    duration = float(info.get("format", {}).get("duration", 0))
                    if duration < 10:
                        print(f"  [WARN] {filename} is only {duration:.1f}s (expected ~{DURATION}s)")
                    else:
                        print(f"  [OK] {filename} ({duration:.1f}s)")
                else:
                    print(f"  [WARN] {filename} - ffprobe failed")
            except FileNotFoundError:
                size_kb = path.stat().st_size / 1024
                print(f"  [OK] {filename} ({size_kb:.0f}KB, ffprobe not available)")
            except Exception as e:
                print(f"  [WARN] {filename} - validation error: {e}")

    if all_ok:
        print("\nAll BGM tracks validated.")
    else:
        print("\nSome tracks are missing or invalid.")
        print("Run: python3 scripts/download_bgm.py --generate-placeholders")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="BGM management for Nurse Robby TikTok videos"
    )
    parser.add_argument("--generate-placeholders", action="store_true",
                        help="Generate sine-wave placeholder BGM files using ffmpeg")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing files when generating")
    parser.add_argument("--list", action="store_true",
                        help="List all BGM files")
    parser.add_argument("--validate", action="store_true",
                        help="Validate all required BGM files exist")

    args = parser.parse_args()

    if args.generate_placeholders:
        cmd_generate_placeholders(args.force)
    elif args.list:
        cmd_list()
    elif args.validate:
        cmd_validate()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
