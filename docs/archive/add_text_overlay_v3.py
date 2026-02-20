#!/usr/bin/env python3
"""
背景画像に日本語テキストを合成 v3.0
文字の見切れを完全防止
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import re

# ディレクトリ設定
project_dir = Path("/Users/robby2/robby_content/post_001")
backgrounds_dir = project_dir / "backgrounds"
output_dir = project_dir / "final_slides_v3"
output_dir.mkdir(exist_ok=True)

# slide_prompts.jsonを読み込み
with open(project_dir / "slide_prompts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 日本語フォントを探す
font_paths = [
    "/Users/robby2/robby_content/fonts/MPLUSRounded1c-Black.ttf",  # 丸ゴシック（女性向け）
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
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

def parse_text_with_highlights(text):
    """強調キーワードを抽出"""
    highlight_keywords = [
        "担当が焦った", "これが限界です", "AIに聞いてみた",
        "▲60-100万円低い", "480-520万円", "1.5万円/回",
        "再確認してみます", "やってくれよ", "プロフのリンクから"
    ]
    number_patterns = [
        r'\d+[-~]\d+万円', r'▲\d+[-~]\d+万円', r'\d+\.\d+万円', r'\d+万',
    ]
    return highlight_keywords, number_patterns

def get_text_width(draw, text, font):
    """テキストの幅を取得"""
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0]
    except:
        return len(text) * font.size // 2

def fit_font_size(draw, text, max_width, initial_size, font_path):
    """テキストが収まる最大のフォントサイズを見つける"""
    font_size = initial_size
    while font_size > 20:  # 最小サイズ20px
        try:
            font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()

        text_width = get_text_width(draw, text, font)
        if text_width <= max_width:
            return font, font_size
        font_size -= 5

    # 最小サイズでも収まらない場合
    try:
        font = ImageFont.truetype(font_path, 20)
    except:
        font = ImageFont.load_default()
    return font, 20

def draw_text_with_highlight(draw, text, x, y, font, default_color=(255, 255, 255),
                              highlight_color=(255, 215, 0), highlight_keywords=None, number_patterns=None):
    """テキストを描画し、キーワードを強調表示"""
    if highlight_keywords is None:
        highlight_keywords = []
    if number_patterns is None:
        number_patterns = []

    is_highlighted = False
    for keyword in highlight_keywords:
        if keyword in text:
            is_highlighted = True
            break

    if not is_highlighted:
        for pattern in number_patterns:
            if re.search(pattern, text):
                is_highlighted = True
                break

    if '✓' in text:
        is_highlighted = True

    color = highlight_color if is_highlighted else default_color
    draw.text((x, y), text, font=font, fill=color)

print("=" * 60)
print("テキストオーバーレイ合成スタート v3.0 (見切れ防止)")
print("=" * 60)
print()

# まずスライド1だけテスト生成
slide = data["slides"][0]
slide_num = slide["slide_number"]
text_overlay = slide["text_overlay"]

print(f"[テスト] スライド{slide_num}を処理中...")

# 背景画像を読み込み
bg_file = backgrounds_dir / f"slide_{slide_num:02d}_bg.png"
if not bg_file.exists():
    print(f"❌ 背景画像が見つかりません: {bg_file}")
    exit(1)

img = Image.open(bg_file)
width, height = img.size

# 安全マージン（左右10%ずつ）
margin = width // 10
max_text_width = width - (margin * 2)

print(f"画像サイズ: {width}x{height}")
print(f"テキスト最大幅: {max_text_width}px (マージン: {margin}px)")

# テキストを行ごとに分割
lines = text_overlay.split("\n")

# 強調キーワードとパターンを取得
highlight_keywords, number_patterns = parse_text_with_highlights(text_overlay)

# 仮の描画オブジェクトでフォントサイズを計算
temp_img = Image.new('RGB', (width, height))
temp_draw = ImageDraw.Draw(temp_img)

# 各行のフォントを決定
line_fonts = []
line_sizes = []

for i, line in enumerate(lines):
    if not line.strip():
        line_fonts.append(None)
        line_sizes.append(0)
        continue

    # 初期フォントサイズ（最初の行はタイトル）
    initial_size = width // 8 if i == 0 else width // 12

    # フォントサイズを調整
    font, font_size = fit_font_size(temp_draw, line, max_text_width, initial_size, japanese_font_path)
    line_fonts.append(font)
    line_sizes.append(font_size)

    print(f"  行{i+1}: フォントサイズ {font_size}px")

# テキストの総高さを計算
total_height = sum(size * 1.5 if size > 0 else 20 for size in line_sizes)

# 半透明の黒帯を描画（中央に配置）
overlay_y_start = (height - int(total_height)) // 2
overlay_y_end = overlay_y_start + int(total_height) + 60

# 半透明黒帯用の一時レイヤー
overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
overlay_draw = ImageDraw.Draw(overlay)
overlay_draw.rectangle(
    [(0, overlay_y_start), (width, overlay_y_end)],
    fill=(0, 0, 0, 150)
)

# 画像に合成
img = img.convert('RGBA')
img = Image.alpha_composite(img, overlay)
img = img.convert('RGB')
draw = ImageDraw.Draw(img)

# テキストを描画
y_offset = overlay_y_start + 30
for i, line in enumerate(lines):
    if not line.strip():
        y_offset += 20
        continue

    font = line_fonts[i]
    font_size = line_sizes[i]

    # テキストの幅を取得
    text_width = get_text_width(draw, line, font)

    # 中央寄せ
    x = (width - text_width) // 2

    # 安全チェック：左右マージンを確保
    if x < margin:
        x = margin
    if x + text_width > width - margin:
        x = width - margin - text_width

    # テキストを描画
    draw_text_with_highlight(
        draw, line, x, y_offset, font,
        default_color=(255, 255, 255),
        highlight_color=(255, 215, 0),
        highlight_keywords=highlight_keywords,
        number_patterns=number_patterns
    )

    y_offset += int(font_size * 1.5)

# 保存
output_file = output_dir / f"slide_{slide_num:02d}_final_v3.png"
img.save(output_file, "PNG")

print(f"✅ 保存完了: {output_file.name}")
print()
print("=" * 60)
print("✅ テスト画像生成完了！(見切れ防止)")
print("=" * 60)
print(f"保存先: {output_file}")
