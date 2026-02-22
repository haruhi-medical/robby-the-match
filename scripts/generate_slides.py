#!/usr/bin/env python3
"""
TikTokスライド生成スクリプト（プロ品質版）
台本JSONから6枚のスライド画像を生成

改善点:
- テキスト長に応じたフォントサイズ自動調整
- TikTok安全領域（上部150px/下部100px）内にフィット保証
- text/subtextの差別化（メイン太字+サブ細字）
- 文字はみ出しゼロ保証
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

project_root = Path(__file__).parent.parent

# フォント検索パス（太字/標準）
FONT_BOLD_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W6.otf",
    "/Library/Fonts/NotoSansJP-Bold.otf",
]

FONT_REGULAR_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W3.otf",
    "/Library/Fonts/NotoSansJP-Regular.otf",
]

# TikTok安全領域
SAFE_TOP = 180      # 上部UIエリア回避
SAFE_BOTTOM = 120   # 下部UIエリア回避
SIDE_MARGIN = 60    # 左右マージン


def find_font(paths, size):
    """フォントを検索して読み込む"""
    for font_path in paths:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    # フォールバック: 太字パスも試す
    for font_path in FONT_BOLD_PATHS + FONT_REGULAR_PATHS:
        if Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    print("❌ 日本語フォントが見つかりません")
    sys.exit(1)


def wrap_text(text, font, max_width):
    """テキストを自動改行（文字単位）"""
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


def calc_text_block_height(lines, line_height):
    """テキストブロックの総高さを計算"""
    if not lines:
        return 0
    return line_height * len(lines)


def auto_fit_fontsize(text, font_paths, max_width, max_height, start_size=80, min_size=36, line_spacing=1.3, target_max_lines=None):
    """
    テキストが指定領域に収まり、かつ行数を最小化する最適フォントサイズを計算

    戦略: 行数が少ない（読みやすい）ほうを優先し、その中で最大フォントサイズを選ぶ

    Returns:
        (font, lines, fontsize, line_height)
    """
    # テキストの文字数からターゲット行数を推定
    char_count = len(text.replace("\n", ""))
    if target_max_lines is None:
        if char_count <= 10:
            target_max_lines = 1
        elif char_count <= 20:
            target_max_lines = 2
        elif char_count <= 35:
            target_max_lines = 3
        else:
            target_max_lines = 4

    max_text_width = max_width - SIDE_MARGIN * 2
    best = None

    for size in range(start_size, min_size - 1, -2):
        font = find_font(font_paths, size)
        line_height = int(size * line_spacing)
        lines = wrap_text(text, font, max_text_width)
        total_height = calc_text_block_height(lines, line_height)
        num_lines = len(lines)

        if total_height > max_height:
            continue

        # 最後の行が1文字だけ（孤立文字）のペナルティ
        has_orphan = num_lines > 1 and len(lines[-1]) <= 2

        if best is None:
            best = (font, lines, size, line_height, num_lines, has_orphan)
            continue

        _, _, best_size, _, best_lines, best_orphan = best

        # 行数がターゲット以下になった最初のサイズを優先
        if num_lines <= target_max_lines and best_lines > target_max_lines:
            best = (font, lines, size, line_height, num_lines, has_orphan)
        # 同じ行数なら孤立文字がないほうを優先
        elif num_lines == best_lines and has_orphan and not best_orphan:
            pass  # bestのほうが良い
        elif num_lines == best_lines and not has_orphan and best_orphan:
            best = (font, lines, size, line_height, num_lines, has_orphan)
        # 行数が減る場合（読みやすさ向上）はフォントが小さくても採用
        elif num_lines < best_lines and num_lines >= 1:
            best = (font, lines, size, line_height, num_lines, has_orphan)

    if best:
        return best[0], best[1], best[2], best[3]

    # フォールバック
    font = find_font(font_paths, min_size)
    line_height = int(min_size * line_spacing)
    lines = wrap_text(text, font, max_text_width)
    return font, lines, min_size, line_height


def draw_text_with_shadow(draw, x, y, text, font, fill="white", shadow_color=(0, 0, 0, 200), shadow_offset=3):
    """テキストをドロップシャドウ付きで描画"""
    # シャドウ
    draw.text((x + shadow_offset, y + shadow_offset), text, fill=shadow_color, font=font)
    # メインテキスト
    draw.text((x, y), text, fill=fill, font=font)


def create_slide(base_image_path, text, output_path, slide_num=1, is_hook=False):
    """
    1枚のスライドを作成（プロ品質版）

    - テキスト長に応じたフォントサイズ自動調整
    - TikTok安全領域内にフィット保証
    - text/subtextの差別化
    - ドロップシャドウ付きテキスト
    """
    img = Image.open(base_image_path).convert('RGB')
    width, height = img.size

    # 利用可能な描画領域
    available_height = height - SAFE_TOP - SAFE_BOTTOM
    max_text_width = width - SIDE_MARGIN * 2

    # text/subtextの分離（\nで区切られている場合）
    parts = text.split("\n")
    has_subtext = len(parts) > 1

    if has_subtext:
        main_text = parts[0].strip()
        sub_text = "\n".join(parts[1:]).strip()
    else:
        main_text = text.strip()
        sub_text = ""

    # フォントサイズ計算
    # 1枚目（フック）: 大きめ、2-6枚目: 標準
    if is_hook:
        main_start_size = 88
        sub_start_size = 56
    else:
        main_start_size = 76
        sub_start_size = 52

    # テキスト全体が利用可能領域に収まるよう自動調整
    if has_subtext:
        # メインテキスト: 利用可能領域の40%
        # サブテキスト: 利用可能領域の50%
        # ギャップ: 残り10%
        main_max_h = int(available_height * 0.38)
        sub_max_h = int(available_height * 0.48)
        gap = int(available_height * 0.06)

        main_font, main_lines, main_size, main_lh = auto_fit_fontsize(
            main_text, FONT_BOLD_PATHS, width, main_max_h,
            start_size=main_start_size, min_size=40, line_spacing=1.25
        )
        sub_font, sub_lines, sub_size, sub_lh = auto_fit_fontsize(
            sub_text, FONT_REGULAR_PATHS, width, sub_max_h,
            start_size=sub_start_size, min_size=32, line_spacing=1.3
        )

        main_block_h = calc_text_block_height(main_lines, main_lh)
        sub_block_h = calc_text_block_height(sub_lines, sub_lh)
        total_h = main_block_h + gap + sub_block_h

        # 全体を垂直中央配置
        y_start = SAFE_TOP + (available_height - total_h) // 2
        main_y = y_start
        sub_y = main_y + main_block_h + gap

        # 黒帯の範囲
        bg_y_start = y_start - 30
        bg_y_end = sub_y + sub_block_h + 30

    else:
        # テキストのみ: 利用可能領域の80%まで使用
        text_max_h = int(available_height * 0.75)

        main_font, main_lines, main_size, main_lh = auto_fit_fontsize(
            main_text, FONT_BOLD_PATHS, width, text_max_h,
            start_size=main_start_size, min_size=40, line_spacing=1.3
        )

        main_block_h = calc_text_block_height(main_lines, main_lh)

        # 垂直中央配置
        y_start = SAFE_TOP + (available_height - main_block_h) // 2
        main_y = y_start

        bg_y_start = y_start - 30
        bg_y_end = main_y + main_block_h + 30

    # 半透明黒帯を描画
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # 黒帯が画像範囲内に収まるようクランプ
    bg_y_start = max(0, bg_y_start)
    bg_y_end = min(height, bg_y_end)
    overlay_draw.rectangle(
        [(0, bg_y_start), (width, bg_y_end)],
        fill=(0, 0, 0, 150)
    )

    # 合成
    img_rgba = img.convert('RGBA')
    img_with_overlay = Image.alpha_composite(img_rgba, overlay)
    draw = ImageDraw.Draw(img_with_overlay)

    # メインテキスト描画
    current_y = main_y
    for line in main_lines:
        bbox = main_font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw_text_with_shadow(draw, x, current_y, line, main_font,
                              shadow_offset=3 if main_size >= 60 else 2)
        current_y += main_lh

    # サブテキスト描画
    if has_subtext and sub_lines:
        current_y = sub_y
        for line in sub_lines:
            bbox = sub_font.getbbox(line)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw_text_with_shadow(draw, x, current_y, line, sub_font,
                                  fill=(240, 240, 240, 255),
                                  shadow_offset=2)
            current_y += sub_lh

    # 保存
    final_img = img_with_overlay.convert('RGB')
    final_img.save(output_path, "PNG", quality=95)


def normalize_slides(data):
    """異なるJSONフォーマットのスライドテキストを統一形式に変換"""
    slides = data.get("slides", [])
    if not slides:
        return []

    # 形式1: ["text1", "text2", ...] — シンプル文字列リスト
    if isinstance(slides[0], str):
        return slides

    # 形式2: [{"slide": 1, "text": "...", "subtext": "..."}, ...] — 構造化形式
    result = []
    for s in slides:
        text = s.get("text", "")
        subtext = s.get("subtext", "")
        if subtext:
            result.append(f"{text}\n{subtext}")
        else:
            result.append(text)
    return result


def generate_slides(json_path, output_dir_override=None):
    """台本JSONから6枚のスライドを一括生成"""
    print(f"\n📦 台本読み込み: {json_path.name}")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    content_id = data.get("content_id", data.get("id", "UNKNOWN"))
    slides_text = normalize_slides(data)
    base_image = data.get("base_image", "base_nurse_station.png")

    if not slides_text:
        print(f"⚠️ スライドテキストが空です")
        return None

    slide_count = len(slides_text)
    print(f"   ID: {content_id}")
    print(f"   ベース画像: {base_image}")
    print(f"   スライド数: {slide_count}枚")

    # ベース画像パス
    base_image_path = project_root / "content" / "base-images" / base_image
    if not base_image_path.exists():
        print(f"❌ エラー: ベース画像が見つかりません: {base_image_path}")
        sys.exit(1)

    # 出力ディレクトリ
    if output_dir_override:
        output_dir = output_dir_override
    else:
        today = datetime.now().strftime("%Y%m%d")
        output_dir = project_root / "content" / "generated" / f"{today}_{content_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        print(f"   出力先: {output_dir.relative_to(project_root)}")
    except ValueError:
        print(f"   出力先: {output_dir}")
    print()

    for i, text in enumerate(slides_text, start=1):
        output_path = output_dir / f"slide_{i}.png"
        text = text.strip()

        print(f"   🎨 slide_{i}.png: {text[:40]}{'...' if len(text) > 40 else ''}")

        create_slide(
            base_image_path=base_image_path,
            text=text,
            output_path=output_path,
            slide_num=i,
            is_hook=(i == 1),
        )

        print(f"      ✅ 完了")

    print(f"\n✅ {slide_count}枚のスライド生成完了: {output_dir}")
    return output_dir


def batch_generate(batch_dir):
    """バッチディレクトリ内の全JSONからスライドを一括生成"""
    json_files = sorted(batch_dir.glob("*.json"))
    if not json_files:
        print(f"❌ JSONファイルが見つかりません: {batch_dir}")
        return

    print(f"=== バッチ生成: {batch_dir.name} ({len(json_files)}ファイル) ===")
    success = 0
    for json_file in json_files:
        if json_file.suffix != ".json":
            continue
        out_dir = (batch_dir / json_file.stem).resolve()
        result = generate_slides(json_file, output_dir_override=out_dir)
        if result:
            success += 1

    print(f"\n=== バッチ完了: {success}/{len(json_files)} セット生成 ===")


def main():
    parser = argparse.ArgumentParser(description="台本JSONからスライドを生成（プロ品質版）")
    parser.add_argument("--json", help="台本JSONファイルパス")
    parser.add_argument("--batch", help="バッチディレクトリパス")

    args = parser.parse_args()

    if args.batch:
        batch_dir = Path(args.batch)
        if not batch_dir.is_dir():
            print(f"❌ エラー: ディレクトリが見つかりません: {batch_dir}")
            sys.exit(1)
        batch_generate(batch_dir)
    elif args.json:
        json_path = Path(args.json)
        if not json_path.exists():
            print(f"❌ エラー: JSONファイルが見つかりません: {json_path}")
            sys.exit(1)
        generate_slides(json_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
