#!/usr/bin/env python3
"""
背景画像に日本語テキストを合成
slide_prompts.jsonのtext_overlayを使用
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ディレクトリ設定
project_dir = Path("/Users/robby2/robby_content/post_001")
backgrounds_dir = project_dir / "backgrounds"
output_dir = project_dir / "final_slides"
output_dir.mkdir(exist_ok=True)

# slide_prompts.jsonを読み込み
with open(project_dir / "slide_prompts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 日本語フォントを探す
font_paths = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

japanese_font_path = None
for path in font_paths:
    if Path(path).exists():
        japanese_font_path = path
        print(f"✅ 日本語フォント検出: {path}")
        break

if not japanese_font_path:
    print("❌ エラー: 日本語フォントが見つかりません")
    exit(1)

print("=" * 60)
print("テキストオーバーレイ合成スタート")
print("=" * 60)
print()

# 各スライドを処理
for slide in data["slides"]:
    slide_num = slide["slide_number"]
    text_overlay = slide["text_overlay"]

    print(f"[{slide_num}/6] スライド{slide_num}を処理中...")

    # 背景画像を読み込み
    bg_file = backgrounds_dir / f"slide_{slide_num:02d}_bg.png"
    if not bg_file.exists():
        print(f"  ❌ 背景画像が見つかりません: {bg_file}")
        continue

    img = Image.open(bg_file)
    draw = ImageDraw.Draw(img)

    # 画像サイズ
    width, height = img.size

    # フォントサイズを計算（画面幅の1/8 ≈ 128px）
    font_size = width // 8
    try:
        font = ImageFont.truetype(japanese_font_path, font_size)
    except Exception as e:
        print(f"  ⚠️ フォント読み込み失敗: {e}")
        font = ImageFont.load_default()

    # テキストを行ごとに分割
    lines = text_overlay.split("\n")

    # 半透明の黒帯を描画（中央〜やや下）
    overlay_height = len(lines) * font_size * 1.5
    overlay_y_start = int(height * 0.4)  # 画面の40%の位置から
    overlay_y_end = overlay_y_start + int(overlay_height)

    # 半透明黒帯用の一時レイヤー
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rectangle(
        [(0, overlay_y_start), (width, overlay_y_end)],
        fill=(0, 0, 0, 180)  # 半透明黒 (alpha=180)
    )

    # 画像に合成
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, overlay)
    img = img.convert('RGB')
    draw = ImageDraw.Draw(img)

    # テキストを描画
    y_offset = overlay_y_start + 20
    for line in lines:
        # 空行はスキップ
        if not line.strip():
            y_offset += font_size // 2
            continue

        # テキストの幅を取得
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(line) * font_size // 2

        # 中央寄せ
        x = (width - text_width) // 2

        # テキストを描画（白色）
        draw.text((x, y_offset), line, font=font, fill=(255, 255, 255))

        y_offset += int(font_size * 1.2)

    # 保存
    output_file = output_dir / f"slide_{slide_num:02d}_final.png"
    img.save(output_file, "PNG")

    print(f"  ✅ 保存完了: {output_file.name}")
    print()

print("=" * 60)
print("✅ テキストオーバーレイ合成完了！")
print("=" * 60)
print(f"保存先: {output_dir}")
