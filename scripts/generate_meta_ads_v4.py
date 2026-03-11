#!/usr/bin/env python3
"""
Meta広告画像v4生成（Instagram native版）
- テキスト最小限（Meta 20%ルール対応）
- 明るい背景 + 人間味のあるデザイン
- 3パターン × feed(1080x1080) + story(1080x1920) = 6枚
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "content" / "meta_ads" / "v4"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W6.otf",
]
FONT_PATHS_W3 = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W3.otf",
]


def font(size, bold=True):
    paths = FONT_PATHS if bold else FONT_PATHS_W3
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    print("No Japanese font found")
    sys.exit(1)


def text_center_x(draw, text, f, canvas_width):
    bbox = draw.textbbox((0, 0), text, font=f)
    return (canvas_width - (bbox[2] - bbox[0])) // 2


def draw_gradient(img, color_top, color_bottom):
    """Vertical gradient fill"""
    w, h = img.size
    for y in range(h):
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * y / h)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * y / h)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * y / h)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))


def draw_circle(draw, cx, cy, radius, fill):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=fill)


# ===== AD1: 年収診断型（好奇心フック） =====
def gen_ad1(size, suffix):
    w, h = size
    img = Image.new("RGB", size)
    # Warm gradient: soft mint to white
    draw_gradient(img, (230, 247, 243), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Accent circle (decorative)
    draw_circle(draw, int(w * 0.85), int(h * 0.15), int(w * 0.12), (91, 120, 125, 30))
    draw_circle(draw, int(w * 0.1), int(h * 0.85), int(w * 0.08), (200, 230, 220))

    # Main hook text — minimal, curiosity-driven
    y_start = int(h * 0.25) if suffix == "feed" else int(h * 0.2)

    line1 = "看護師5年目"
    line2 = "平均年収 480万円"
    line3 = "あなたは？"

    f_small = font(int(w * 0.055), bold=False)
    f_big = font(int(w * 0.085))
    f_hook = font(int(w * 0.1))

    x = text_center_x(draw, line1, f_small, w)
    draw.text((x, y_start), line1, fill="#666666", font=f_small)

    y2 = y_start + int(h * 0.08)
    x = text_center_x(draw, line2, f_big, w)
    draw.text((x, y2), line2, fill="#5B787D", font=f_big)

    y3 = y2 + int(h * 0.12)
    x = text_center_x(draw, line3, f_hook, w)
    draw.text((x, y3), line3, fill="#333333", font=f_hook)

    # CTA button
    y_btn = y3 + int(h * 0.15)
    btn_text = "30秒で年収診断 →"
    f_btn = font(int(w * 0.045))
    bbox = draw.textbbox((0, 0), btn_text, font=f_btn)
    btn_w = bbox[2] - bbox[0] + 60
    btn_h = bbox[3] - bbox[1] + 36
    btn_x = (w - btn_w) // 2
    draw.rounded_rectangle(
        [btn_x, y_btn, btn_x + btn_w, y_btn + btn_h],
        radius=btn_h // 2, fill="#06C755"
    )
    tx = text_center_x(draw, btn_text, f_btn, w)
    draw.text((tx, y_btn + 10), btn_text, fill="white", font=f_btn)

    # Footer
    f_footer = font(int(w * 0.028), bold=False)
    footer = "神奈川ナース転職 ｜ 相談無料・電話なし"
    x = text_center_x(draw, footer, f_footer, w)
    draw.text((x, int(h * 0.88)), footer, fill="#999999", font=f_footer)

    img.save(OUTPUT_DIR / f"ad1_salary_{suffix}.png")
    print(f"  ✅ ad1_salary_{suffix}.png")


# ===== AD2: 共感型（感情フック） =====
def gen_ad2(size, suffix):
    w, h = size
    img = Image.new("RGB", size)
    # Warm peachy gradient
    draw_gradient(img, (255, 245, 238), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Decorative elements
    draw_circle(draw, int(w * 0.9), int(h * 0.1), int(w * 0.06), (255, 220, 200))
    draw_circle(draw, int(w * 0.05), int(h * 0.5), int(w * 0.04), (255, 230, 215))

    y_start = int(h * 0.2) if suffix == "feed" else int(h * 0.15)

    # Quote mark
    f_quote = font(int(w * 0.15))
    draw.text((int(w * 0.08), y_start - int(h * 0.05)), "\u201C", fill="#DDCCBB", font=f_quote)

    # Hook
    line1 = "前にも言ったよね"
    f_hook = font(int(w * 0.08))
    x = text_center_x(draw, line1, f_hook, w)
    draw.text((x, y_start + int(h * 0.05)), line1, fill="#333333", font=f_hook)

    # Sub
    line2 = "この言葉、何回聞いた？"
    f_sub = font(int(w * 0.045), bold=False)
    x = text_center_x(draw, line2, f_sub, w)
    draw.text((x, y_start + int(h * 0.17)), line2, fill="#888888", font=f_sub)

    # Divider
    y_div = y_start + int(h * 0.26)
    draw.line([(w // 2 - 40, y_div), (w // 2 + 40, y_div)], fill="#DDCCBB", width=2)

    # Positive message
    line3 = "環境を変えるだけで"
    line4 = "解決するかも。"
    f_msg = font(int(w * 0.055))
    x = text_center_x(draw, line3, f_msg, w)
    draw.text((x, y_div + int(h * 0.04)), line3, fill="#5B787D", font=f_msg)
    x = text_center_x(draw, line4, f_msg, w)
    draw.text((x, y_div + int(h * 0.1)), line4, fill="#5B787D", font=f_msg)

    # CTA
    y_btn = y_div + int(h * 0.2)
    btn_text = "まずは話を聞いてみる →"
    f_btn = font(int(w * 0.04))
    bbox = draw.textbbox((0, 0), btn_text, font=f_btn)
    btn_w = bbox[2] - bbox[0] + 60
    btn_h = bbox[3] - bbox[1] + 36
    btn_x = (w - btn_w) // 2
    draw.rounded_rectangle(
        [btn_x, y_btn, btn_x + btn_w, y_btn + btn_h],
        radius=btn_h // 2, fill="#06C755"
    )
    tx = text_center_x(draw, btn_text, f_btn, w)
    draw.text((tx, y_btn + 10), btn_text, fill="white", font=f_btn)

    # Footer
    f_footer = font(int(w * 0.028), bold=False)
    footer = "神奈川ナース転職 ｜ しつこい電話なし"
    x = text_center_x(draw, footer, f_footer, w)
    draw.text((x, int(h * 0.88)), footer, fill="#999999", font=f_footer)

    img.save(OUTPUT_DIR / f"ad2_empathy_{suffix}.png")
    print(f"  ✅ ad2_empathy_{suffix}.png")


# ===== AD3: 数字インパクト型 =====
def gen_ad3(size, suffix):
    w, h = size
    img = Image.new("RGB", size)
    # Light blue-white gradient
    draw_gradient(img, (235, 245, 255), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Accent
    draw_circle(draw, int(w * 0.85), int(h * 0.8), int(w * 0.1), (220, 235, 250))

    y_start = int(h * 0.18) if suffix == "feed" else int(h * 0.15)

    # Hook: Big number
    f_num = font(int(w * 0.2))
    num_text = "80万円"
    x = text_center_x(draw, num_text, f_num, w)
    draw.text((x, y_start), num_text, fill="#E65100", font=f_num)

    # Explanation
    f_sub = font(int(w * 0.045), bold=False)
    line1 = "転職エージェントが"
    line2 = "病院から取る手数料の差額"
    y2 = y_start + int(h * 0.18)
    x = text_center_x(draw, line1, f_sub, w)
    draw.text((x, y2), line1, fill="#666666", font=f_sub)
    x = text_center_x(draw, line2, f_sub, w)
    draw.text((x, y2 + int(h * 0.05)), line2, fill="#666666", font=f_sub)

    # Comparison
    f_comp = font(int(w * 0.04))
    y3 = y2 + int(h * 0.14)
    draw.rounded_rectangle(
        [int(w * 0.1), y3, int(w * 0.9), y3 + int(h * 0.12)],
        radius=12, fill="#F5F5F5"
    )
    comp1 = "大手: 年収の25%（=120万円）"
    comp2 = "神奈川ナース転職: 10%（=40万円）"
    draw.text((int(w * 0.15), y3 + int(h * 0.015)), comp1, fill="#999999", font=f_comp)
    f_comp_b = font(int(w * 0.04))
    draw.text((int(w * 0.15), y3 + int(h * 0.06)), comp2, fill="#5B787D", font=f_comp_b)

    # Message
    f_msg = font(int(w * 0.05))
    y4 = y3 + int(h * 0.17)
    msg = "だからあなたの内定が出やすい"
    x = text_center_x(draw, msg, f_msg, w)
    draw.text((x, y4), msg, fill="#333333", font=f_msg)

    # CTA
    y_btn = y4 + int(h * 0.1)
    btn_text = "無料で相談する →"
    f_btn = font(int(w * 0.04))
    bbox = draw.textbbox((0, 0), btn_text, font=f_btn)
    btn_w = bbox[2] - bbox[0] + 60
    btn_h = bbox[3] - bbox[1] + 36
    btn_x = (w - btn_w) // 2
    draw.rounded_rectangle(
        [btn_x, y_btn, btn_x + btn_w, y_btn + btn_h],
        radius=btn_h // 2, fill="#06C755"
    )
    tx = text_center_x(draw, btn_text, f_btn, w)
    draw.text((tx, y_btn + 10), btn_text, fill="white", font=f_btn)

    # Footer
    f_footer = font(int(w * 0.028), bold=False)
    footer = "神奈川ナース転職 ｜ 手数料10%の看護師転職"
    x = text_center_x(draw, footer, f_footer, w)
    draw.text((x, int(h * 0.88)), footer, fill="#999999", font=f_footer)

    img.save(OUTPUT_DIR / f"ad3_number_{suffix}.png")
    print(f"  ✅ ad3_number_{suffix}.png")


if __name__ == "__main__":
    print("🎨 Meta広告画像 v4 生成中...")
    print("\n📐 AD1: 年収診断型（好奇心フック）")
    gen_ad1((1080, 1080), "feed")
    gen_ad1((1080, 1920), "story")

    print("\n📐 AD2: 共感型（感情フック）")
    gen_ad2((1080, 1080), "feed")
    gen_ad2((1080, 1920), "story")

    print("\n📐 AD3: 数字インパクト型")
    gen_ad3((1080, 1080), "feed")
    gen_ad3((1080, 1920), "story")

    print(f"\n✅ 6枚生成完了 → {OUTPUT_DIR}/")
