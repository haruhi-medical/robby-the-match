#!/usr/bin/env python3
"""
Meta広告画像v3生成スクリプト（神奈川県全域版）
Pillowで3パターン × feed(1080x1080) + story(1080x1920) = 6枚生成
"""

import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = Path(__file__).parent.parent / "content" / "meta_ads" / "v3"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# フォント
FONT_PATHS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
    "/System/Library/Fonts/ヒラギノ角ゴ ProN W6.otf",
    "/Library/Fonts/NotoSansJP-Bold.otf",
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
    # fallback to bold
    for p in FONT_PATHS:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    print("No Japanese font found")
    sys.exit(1)


def text_center_x(draw, text, f, canvas_width):
    bbox = draw.textbbox((0, 0), text, font=f)
    return (canvas_width - (bbox[2] - bbox[0])) // 2


def draw_rounded_rect(draw, xy, fill, radius=12):
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def draw_pill_button(draw, center_x, y, text, bg_color, text_color, f, padding_x=40, padding_y=16):
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x0 = center_x - tw // 2 - padding_x
    x1 = center_x + tw // 2 + padding_x
    y0 = y
    y1 = y + th + padding_y * 2
    draw.rounded_rectangle((x0, y0, x1, y1), radius=(y1 - y0) // 2, fill=bg_color)
    tx = center_x - tw // 2
    ty = y + padding_y
    draw.text((tx, ty), text, fill=text_color, font=f)
    return y1


# ============================================================
# AD1: 地域密着型 → 神奈川県全域版
# ============================================================

def generate_ad1(width, height, filename):
    bg_color = (26, 35, 60)  # dark navy
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    cx = width // 2
    is_story = height > width

    # Scale factor
    s = height / 1080 if not is_story else height / 1920

    # Badge: 神奈川県全域対応
    badge_text = "神奈川県全域対応"
    badge_font = font(int(22 * s))
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    badge_y = int(60 * s) if not is_story else int(100 * s)
    px, py = 24, 10
    draw.rounded_rectangle(
        (cx - bw // 2 - px, badge_y, cx + bw // 2 + px, badge_y + bh + py * 2),
        radius=20, fill=(255, 107, 129)
    )
    draw.text((cx - bw // 2, badge_y + py), badge_text, fill="white", font=badge_font)

    # Main heading
    heading_y = badge_y + bh + py * 2 + int(30 * s)
    h_font = font(int(68 * s) if not is_story else int(62 * s))
    for i, line in enumerate(["神奈川県の", "看護師さんへ"]):
        x = text_center_x(draw, line, h_font, width)
        draw.text((x, heading_y + i * int(80 * s)), line, fill="white", font=h_font)

    # Accent line
    line_y = heading_y + int(175 * s)
    line_w = int(80 * s)
    draw.line([(cx - line_w, line_y), (cx + line_w, line_y)], fill=(91, 120, 125), width=3)

    # Subtitle
    sub_y = line_y + int(25 * s)
    sub_font = font(int(28 * s), bold=False)
    for i, line in enumerate(["あなたの地元で", "理想の職場、見つかります"]):
        x = text_center_x(draw, line, sub_font, width)
        draw.text((x, sub_y + i * int(40 * s)), line, fill=(180, 210, 215), font=sub_font)

    # Feature cards
    card_y = sub_y + int(100 * s)
    card_color = (40, 55, 90)

    if is_story:
        # Vertical card layout for story
        card_margin = int(60 * s)
        card_w = width - card_margin * 2
        card_h = int(70 * s)
        cards = [
            ("神奈川県全域", "横浜・川崎・小田原など"),
            ("手数料10%", "業界平均20-30%の1/3。病院の負担を軽減"),
            ("AI×人のハイブリッド", "AIが条件マッチ → 人が面談サポート"),
        ]
        title_font = font(int(22 * s))
        desc_font = font(int(16 * s), bold=False)
        for i, (title, desc) in enumerate(cards):
            cy = card_y + i * (card_h + int(12 * s))
            draw.rounded_rectangle(
                (card_margin, cy, card_margin + card_w, cy + card_h),
                radius=8, fill=card_color
            )
            draw.text((card_margin + 20, cy + 12), title, fill="white", font=title_font)
            draw.text((card_margin + 20, cy + 40), desc, fill=(160, 180, 200), font=desc_font)
    else:
        # Horizontal card layout for feed
        gap = int(12 * s)
        card_w = (width - int(80 * s) * 2 - gap * 2) // 3
        card_h = int(140 * s)
        cards = [
            ("神奈川県\n全域", "横浜・川崎・\n小田原など"),
            ("手数料10%", "業界平均の1/3\n病院も安心の低コスト"),
            ("AI×人", "AIが条件マッチング\n人間が面談サポート"),
        ]
        title_font = font(int(20 * s))
        desc_font = font(int(14 * s), bold=False)
        for i, (title, desc) in enumerate(cards):
            cx_card = int(80 * s) + i * (card_w + gap)
            draw.rounded_rectangle(
                (cx_card, card_y, cx_card + card_w, card_y + card_h),
                radius=8, fill=card_color
            )
            # Title
            for j, tl in enumerate(title.split("\n")):
                tx = cx_card + (card_w - draw.textbbox((0, 0), tl, font=title_font)[2]) // 2
                draw.text((tx, card_y + 15 + j * int(26 * s)), tl, fill="white", font=title_font)
            # Desc
            title_lines = len(title.split("\n"))
            desc_start = card_y + 15 + title_lines * int(26 * s) + 10
            for j, dl in enumerate(desc.split("\n")):
                dx = cx_card + (card_w - draw.textbbox((0, 0), dl, font=desc_font)[2]) // 2
                draw.text((dx, desc_start + j * int(20 * s)), dl, fill=(160, 180, 200), font=desc_font)

    # CTA Button
    cta_y = card_y + (int(250 * s) if not is_story else int(230 * s))
    btn_font = font(int(26 * s))
    draw_pill_button(draw, cx, cta_y, "LINEで無料相談 →", (76, 191, 114), "white", btn_font, 50, 18)

    # Footer
    footer_font = font(int(16 * s), bold=False)
    footer_text = "神奈川ナース転職｜手数料10%の看護師転職"
    fx = text_center_x(draw, footer_text, footer_font, width)
    draw.text((fx, height - int(50 * s)), footer_text, fill=(120, 140, 160), font=footer_font)

    img.save(OUTPUT_DIR / filename, "PNG")
    print(f"  AD1: {filename} ({width}x{height})")


# ============================================================
# AD2: 手数料比較型（地域テキスト不要、ほぼ変更なし）
# ============================================================

def generate_ad2(width, height, filename):
    bg_color = (30, 40, 30)  # dark green
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    cx = width // 2
    is_story = height > width
    s = height / 1080 if not is_story else height / 1920

    # Title
    title_y = int(50 * s) if not is_story else int(80 * s)
    title_font = font(int(36 * s))
    title = "看護師の転職、こんなに違う"
    draw.text((text_center_x(draw, title, title_font, width), title_y), title, fill="white", font=title_font)

    # Comparison boxes
    box_y = title_y + int(80 * s)
    box_h = int(220 * s) if not is_story else int(200 * s)

    # Left: 大手
    left_w = int(width * 0.42)
    left_x = int(40 * s)
    draw.rounded_rectangle((left_x, box_y, left_x + left_w, box_y + box_h), radius=10, fill=(120, 40, 40))
    # Header bar
    draw.rectangle((left_x, box_y, left_x + left_w, box_y + int(40 * s)), fill=(180, 50, 50))
    lh_font = font(int(20 * s))
    lh_text = "大手エージェント"
    draw.text((left_x + (left_w - draw.textbbox((0, 0), lh_text, font=lh_font)[2]) // 2, box_y + 8), lh_text, fill="white", font=lh_font)
    # 30%
    big_font = font(int(80 * s))
    pct = "30%"
    draw.text((left_x + (left_w - draw.textbbox((0, 0), pct, font=big_font)[2]) // 2, box_y + int(50 * s)), pct, fill=(255, 180, 80), font=big_font)
    # Detail
    det_font = font(int(16 * s), bold=False)
    for i, t in enumerate(["年収400万の場合", "→ 120万円"]):
        draw.text((left_x + (left_w - draw.textbbox((0, 0), t, font=det_font)[2]) // 2, box_y + int(150 * s) + i * int(24 * s)), t, fill=(200, 180, 160), font=det_font)

    # VS circle
    vs_font = font(int(22 * s))
    vs_x = left_x + left_w + int(5 * s)
    vs_y = box_y + box_h // 2 - int(18 * s)
    draw.ellipse((vs_x, vs_y, vs_x + int(40 * s), vs_y + int(40 * s)), fill=(80, 120, 80))
    draw.text((vs_x + int(5 * s), vs_y + int(6 * s)), "VS", fill="white", font=font(int(16 * s)))

    # Right: 神奈川ナース転職
    right_x = vs_x + int(45 * s)
    right_w = width - right_x - int(40 * s)
    draw.rounded_rectangle((right_x, box_y, right_x + right_w, box_y + box_h), radius=10, fill=(30, 80, 50))
    draw.rectangle((right_x, box_y, right_x + right_w, box_y + int(40 * s)), fill=(60, 140, 80))
    rh_text = "神奈川ナース転職"
    draw.text((right_x + (right_w - draw.textbbox((0, 0), rh_text, font=lh_font)[2]) // 2, box_y + 8), rh_text, fill="white", font=lh_font)
    draw.text((right_x + (right_w - draw.textbbox((0, 0), "10%", font=big_font)[2]) // 2, box_y + int(50 * s)), "10%", fill=(100, 220, 130), font=big_font)
    for i, t in enumerate(["年収400万の場合", "→ 40万円"]):
        draw.text((right_x + (right_w - draw.textbbox((0, 0), t, font=det_font)[2]) // 2, box_y + int(150 * s) + i * int(24 * s)), t, fill=(180, 220, 200), font=det_font)

    # Difference callout
    diff_y = box_y + box_h + int(30 * s)
    diff_font = font(int(28 * s))
    diff_text = "差額80万円 ＝ 病院の負担"
    draw.text((text_center_x(draw, diff_text, diff_font, width), diff_y), diff_text, fill=(255, 200, 80), font=diff_font)

    exp_font = font(int(18 * s), bold=False)
    for i, t in enumerate(["手数料が安い → 病院が積極的に採用", "→ あなたの給与交渉が有利に"]):
        draw.text((text_center_x(draw, t, exp_font, width), diff_y + int(45 * s) + i * int(28 * s)), t, fill=(200, 210, 200), font=exp_font)

    # CTA
    cta_y = diff_y + int(120 * s)
    btn_font = font(int(24 * s))
    draw_pill_button(draw, cx, cta_y, "詳しくはLINEで → 相談無料", (76, 191, 114), "white", btn_font, 45, 16)

    # Footer
    footer_font = font(int(16 * s), bold=False)
    footer_text = "神奈川ナース転職｜神奈川県の看護師転職"
    draw.text((text_center_x(draw, footer_text, footer_font, width), height - int(50 * s)), footer_text, fill=(120, 150, 130), font=footer_font)

    img.save(OUTPUT_DIR / filename, "PNG")
    print(f"  AD2: {filename} ({width}x{height})")


# ============================================================
# AD3: 共感型 → 「神奈川西部」→「神奈川県」に変更
# ============================================================

def generate_ad3(width, height, filename):
    bg_color = (60, 25, 35)  # dark wine
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    cx = width // 2
    is_story = height > width
    s = height / 1080 if not is_story else height / 1920

    # Main heading
    head_y = int(50 * s) if not is_story else int(80 * s)
    h_font = font(int(62 * s) if not is_story else int(56 * s))
    for i, line in enumerate(["人間関係、", "疲れてない？"]):
        draw.text((text_center_x(draw, line, h_font, width), head_y + i * int(75 * s)), line, fill="white", font=h_font)

    # Subtitle
    sub_y = head_y + int(170 * s)
    sub_font = font(int(24 * s), bold=False)
    sub_text = "それ、環境を変えるだけで解決するかも。"
    draw.text((text_center_x(draw, sub_text, sub_font, width), sub_y), sub_text, fill=(200, 180, 180), font=sub_font)

    # Checklist
    check_y = sub_y + int(60 * s)
    check_font = font(int(22 * s), bold=False)
    items = [
        "「前にも言ったよね」が口癖の先輩",
        "残業が当たり前の空気",
        "夜勤明けでも呼び出される",
        "頑張っても給料が上がらない",
    ]
    for i, item in enumerate(items):
        y = check_y + i * int(38 * s)
        # Checkbox
        cb_x = int(60 * s)
        cb_size = int(18 * s)
        draw.rectangle((cb_x, y + 3, cb_x + cb_size, y + 3 + cb_size), outline=(180, 160, 160), width=2)
        draw.line([(cb_x + 3, y + 3 + cb_size // 2), (cb_x + cb_size // 2, y + cb_size)], fill=(180, 160, 160), width=2)
        draw.line([(cb_x + cb_size // 2, y + cb_size), (cb_x + cb_size - 2, y + 5)], fill=(180, 160, 160), width=2)
        draw.text((cb_x + cb_size + 12, y), item, fill=(200, 180, 180), font=check_font)

    # Divider
    div_y = check_y + len(items) * int(38 * s) + int(20 * s)
    draw.line([(int(60 * s), div_y), (width - int(60 * s), div_y)], fill=(140, 100, 100), width=2)

    # Bottom message - 「神奈川県で」に変更
    msg_y = div_y + int(20 * s)
    msg_font = font(int(28 * s))
    for i, line in enumerate(["神奈川県で", "あなたに合う職場、見つかる"]):
        draw.text((text_center_x(draw, line, msg_font, width), msg_y + i * int(38 * s)), line, fill="white", font=msg_font)

    # AI×人
    ai_y = msg_y + int(85 * s)
    ai_font = font(int(22 * s))
    ai_text = "AI × 人の寄り添いサポート"
    draw.text((text_center_x(draw, ai_text, ai_font, width), ai_y), ai_text, fill=(80, 200, 180), font=ai_font)

    # Stats row
    stat_y = ai_y + int(45 * s)
    stat_font = font(int(28 * s))
    stat_sub_font = font(int(14 * s), bold=False)
    stats = [("212施設", "の求人データ"), ("手数料10%", "で病院も安心"), ("相談無料", "LINEでOK")]
    stat_w = width // 3
    for i, (val, label) in enumerate(stats):
        sx = stat_w * i + (stat_w - draw.textbbox((0, 0), val, font=stat_font)[2]) // 2
        draw.text((sx, stat_y), val, fill=(80, 200, 180), font=stat_font)
        lx = stat_w * i + (stat_w - draw.textbbox((0, 0), label, font=stat_sub_font)[2]) // 2
        draw.text((lx, stat_y + int(35 * s)), label, fill=(180, 160, 160), font=stat_sub_font)

    # CTA
    cta_y = stat_y + int(75 * s)
    btn_font = font(int(24 * s))
    draw_pill_button(draw, cx, cta_y, "まずはLINEで相談 →", (76, 191, 114), "white", btn_font, 45, 16)

    # Footer
    footer_font = font(int(16 * s), bold=False)
    footer_text = "神奈川ナース転職｜神奈川県の看護師転職サポート"
    draw.text((text_center_x(draw, footer_text, footer_font, width), height - int(50 * s)), footer_text, fill=(140, 110, 120), font=footer_font)

    img.save(OUTPUT_DIR / filename, "PNG")
    print(f"  AD3: {filename} ({width}x{height})")


if __name__ == "__main__":
    print("=" * 50)
    print("Meta広告画像 v3（神奈川県全域版）生成")
    print("=" * 50)
    print(f"出力先: {OUTPUT_DIR}\n")

    # AD1: 地域密着型
    generate_ad1(1080, 1080, "ad1_local_feed.png")
    generate_ad1(1080, 1920, "ad1_local_story.png")

    # AD2: 手数料比較型
    generate_ad2(1080, 1080, "ad2_comparison_feed.png")
    generate_ad2(1080, 1920, "ad2_comparison_story.png")

    # AD3: 共感型
    generate_ad3(1080, 1080, "ad3_empathy_feed.png")
    generate_ad3(1080, 1920, "ad3_empathy_story.png")

    print(f"\n6枚の広告画像を生成しました: {OUTPUT_DIR}")
