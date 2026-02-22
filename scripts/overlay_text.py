#!/usr/bin/env python3
"""
テキスト焼き込みスクリプト（プロ品質版）
日本語テキストをベース画像に焼き込む（TikTok 9:16対応）

改善: 自動フォントサイズ調整、TikTok安全領域対応、ドロップシャドウ
"""

import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# フォント検索パス
FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W6.otf",
    "/Library/Fonts/NotoSansJP-Bold.otf",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
]

SAFE_TOP = 180
SAFE_BOTTOM = 120
SIDE_MARGIN = 60


def find_japanese_font(size):
    for font_path in FONT_PATHS:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    print("❌ 日本語フォントが見つかりません。")
    sys.exit(1)


def wrap_text(text, font, max_width):
    lines = []
    current_line = ""
    for char in text:
        if char == "\n":
            if current_line:
                lines.append(current_line)
            current_line = ""
            continue
        test_line = current_line + char
        bbox = font.getbbox(test_line)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char
    if current_line:
        lines.append(current_line)
    return lines


def auto_fit_fontsize(text, max_width, max_height, start_size=80, min_size=36):
    """テキストが領域に収まる最大フォントサイズを自動計算"""
    for size in range(start_size, min_size - 1, -2):
        font = find_japanese_font(size)
        line_height = int(size * 1.3)
        lines = wrap_text(text, font, max_width - SIDE_MARGIN * 2)
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines, size, line_height

    font = find_japanese_font(min_size)
    line_height = int(min_size * 1.3)
    lines = wrap_text(text, font, max_width - SIDE_MARGIN * 2)
    return font, lines, min_size, line_height


def overlay_text(input_path, text, output_path, position="center", fontsize=None):
    img = Image.open(input_path).convert('RGB')
    width, height = img.size

    available_height = height - SAFE_TOP - SAFE_BOTTOM
    max_text_height = int(available_height * 0.75)

    if fontsize:
        font = find_japanese_font(fontsize)
        line_height = int(fontsize * 1.3)
        lines = wrap_text(text, font, width - SIDE_MARGIN * 2)
        total_text_height = line_height * len(lines)
        # はみ出しチェック: 収まらなければ自動縮小
        if total_text_height > max_text_height:
            font, lines, fontsize, line_height = auto_fit_fontsize(
                text, width, max_text_height, start_size=fontsize, min_size=36
            )
            total_text_height = line_height * len(lines)
    else:
        font, lines, fontsize, line_height = auto_fit_fontsize(
            text, width, max_text_height, start_size=80, min_size=36
        )
        total_text_height = line_height * len(lines)

    # 位置決定
    if position == "top":
        y_start = SAFE_TOP + 20
    elif position == "bottom":
        y_start = height - SAFE_BOTTOM - total_text_height - 20
    else:
        y_start = SAFE_TOP + (available_height - total_text_height) // 2

    # 半透明黒帯
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    bg_y_start = max(0, y_start - 30)
    bg_y_end = min(height, y_start + total_text_height + 30)
    overlay_draw.rectangle([(0, bg_y_start), (width, bg_y_end)], fill=(0, 0, 0, 150))

    img_rgba = img.convert('RGBA')
    img_with_overlay = Image.alpha_composite(img_rgba, overlay)
    draw = ImageDraw.Draw(img_with_overlay)

    current_y = y_start
    shadow_offset = 3 if fontsize >= 60 else 2
    for line in lines:
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x + shadow_offset, current_y + shadow_offset), line,
                  fill=(0, 0, 0, 200), font=font)
        draw.text((x, current_y), line, fill="white", font=font)
        current_y += line_height

    final_img = img_with_overlay.convert('RGB')
    final_img.save(output_path, "PNG", quality=95)
    print(f"✅ 保存完了: {output_path} (fontsize={fontsize}px, {len(lines)}行)")


def main():
    parser = argparse.ArgumentParser(description="画像にテキストを焼き込む（プロ品質版）")
    parser.add_argument("--input", required=True, help="入力画像パス")
    parser.add_argument("--text", required=True, help="焼き込むテキスト")
    parser.add_argument("--output", required=True, help="出力画像パス")
    parser.add_argument("--position", choices=["top", "center", "bottom"], default="center")
    parser.add_argument("--fontsize", type=int, default=None,
                        help="フォントサイズ（未指定で自動調整）")

    args = parser.parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"❌ エラー: 入力画像が見つかりません: {input_path}")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_text(input_path, args.text, output_path, args.position, args.fontsize)


if __name__ == "__main__":
    main()
