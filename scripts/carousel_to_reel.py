#!/usr/bin/env python3
"""
カルーセルPNG → Instagram/TikTokリール動画 変換

既存のカルーセル画像（1080x1350）をスライドショー動画（1080x1920）に変換。
Ken Burns効果（ズームパン）+ フェードトランジション + BGM合成。

Usage:
  python3 scripts/carousel_to_reel.py --slide-dir content/generated/html_xxx/
  python3 scripts/carousel_to_reel.py --slide-dir content/generated/html_xxx/ --duration 3 --output out.mp4
"""

import argparse
import subprocess
import random
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
BGM_DIR = PROJECT_DIR / "content" / "bgm"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "content" / "temp_videos"

# BGM options
BGMS = ["bgm_calm.mp3", "bgm_chill.mp3", "bgm_emotional.mp3", "bgm_upbeat.mp3"]


def create_reel(slide_dir: Path, output_path: Path = None,
                slide_duration: float = 3.0, transition_duration: float = 0.5,
                bgm: str = None):
    """Convert carousel PNGs to a reel video with transitions and BGM.

    1. Pad 1080x1350 images to 1080x1920 (center, with gradient fill)
    2. Apply Ken Burns (slow zoom) to each slide
    3. Add crossfade transitions between slides
    4. Add BGM at low volume with fade in/out
    """
    slides = sorted(slide_dir.glob("slide_*.png"))
    if not slides:
        print(f"[Reel] No slides found in {slide_dir}")
        return None

    if output_path is None:
        output_path = DEFAULT_OUTPUT_DIR / f"reel_{slide_dir.name}.mp4"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    n = len(slides)
    total_duration = n * slide_duration - (n - 1) * transition_duration

    # Select BGM
    if bgm is None:
        bgm_file = BGM_DIR / random.choice(BGMS)
    else:
        bgm_file = BGM_DIR / bgm
    has_bgm = bgm_file.exists()

    print(f"[Reel] {n} slides, {slide_duration}s each, {transition_duration}s transition")
    print(f"[Reel] Total duration: {total_duration:.1f}s")
    print(f"[Reel] BGM: {bgm_file.name if has_bgm else 'none'}")

    # Build FFmpeg filter complex
    # Step 1: For each slide, pad to 1080x1920 and apply zoompan
    inputs = []
    filters = []
    fps = 30
    frames_per_slide = int(slide_duration * fps)

    for i, slide in enumerate(slides):
        inputs.extend(["-loop", "1", "-t", str(slide_duration), "-i", str(slide)])

        # Pad 1080x1350 → 1080x1920 centered on gradient background
        # Then apply slow zoom (Ken Burns: 1.0→1.05 over slide_duration)
        filters.append(
            f"[{i}:v]scale=1080:1350,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=#F5E6EF,"
            f"zoompan=z='min(zoom+0.0008,1.05)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames_per_slide}:s=1080x1920:fps={fps},"
            f"setpts=PTS-STARTPTS,format=yuv420p[v{i}]"
        )

    # Step 2: Chain xfade transitions
    if n == 1:
        filters.append(f"[v0]null[vout]")
    else:
        # First pair
        offset = slide_duration - transition_duration
        filters.append(
            f"[v0][v1]xfade=transition=fade:duration={transition_duration}:offset={offset}[xf0]"
        )
        # Subsequent pairs
        for i in range(2, n):
            prev = f"xf{i-2}"
            curr_offset = offset + (slide_duration - transition_duration)
            offset = curr_offset
            if i == n - 1:
                filters.append(
                    f"[{prev}][v{i}]xfade=transition=fade:duration={transition_duration}:offset={curr_offset}[vout]"
                )
            else:
                filters.append(
                    f"[{prev}][v{i}]xfade=transition=fade:duration={transition_duration}:offset={curr_offset}[xf{i-1}]"
                )
        if n == 2:
            # Rename xf0 to vout
            filters[-1] = filters[-1].replace("[xf0]", "[vout]")

    filter_complex = ";\n".join(filters)

    # Build command
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)

    if has_bgm:
        cmd.extend(["-i", str(bgm_file)])
        audio_idx = n
        # Add audio filter: volume down, fade in/out, trim to video length
        filter_complex += (
            f";\n[{audio_idx}:a]volume=0.15,"
            f"afade=t=in:d=1.0,"
            f"afade=t=out:st={total_duration - 1.5}:d=1.5[aout]"
        )
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "[aout]",
            "-shortest",
        ])
    else:
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[vout]",
        ])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ])

    print(f"[Reel] Generating video...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode == 0:
        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"[Reel] Done: {output_path} ({size_mb:.1f}MB)")
        return output_path
    else:
        print(f"[Reel] FFmpeg error: {result.stderr[-500:]}")
        return None


def main():
    parser = argparse.ArgumentParser(description="カルーセルPNG→リール動画変換")
    parser.add_argument("--slide-dir", required=True, help="カルーセル画像フォルダ")
    parser.add_argument("--output", help="出力ファイルパス")
    parser.add_argument("--duration", type=float, default=3.0, help="各スライドの表示時間（秒）")
    parser.add_argument("--transition", type=float, default=0.5, help="トランジション時間（秒）")
    parser.add_argument("--bgm", help="BGMファイル名（content/bgm/内）")
    args = parser.parse_args()

    slide_dir = Path(args.slide_dir)
    output = Path(args.output) if args.output else None

    create_reel(slide_dir, output, args.duration, args.transition, args.bgm)


if __name__ == "__main__":
    main()
