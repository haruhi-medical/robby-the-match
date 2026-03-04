#!/usr/bin/env python3
"""
generate_meta_ads.py v2.0 -- Meta広告クリエイティブ生成（データドリブン版）

デザイン根拠:
  - カラー: 医療系85%がブルー系。白ベース70% + ティール25% + オレンジ5%
  - フォント: 丸ゴシック（温かみ+プロ感。看護roo!等大手も採用）
  - サイズ: 1080x1350（4:5）= Instagramフィード最大面積
  - テキスト: 画像面積の20%以下（アルゴリズムペナルティ回避）
  - CTA: オレンジ（+32.5%コンバージョン）+ 不安軽減マイクロコピー
  - 競合差別化: 地域特化（大手は全国。神奈川ローカルは競合ゼロ）

出力: 1080x1350（フィード4:5）+ 1080x1920（ストーリー9:16）

Sources:
  - ThinkPod Agency: Healthcare Branding Colors 2025
  - Instagram Carousel Strategy 2026
  - Japanese CTA optimization: 70:25:5 color ratio
  - Meta Ads platform-specs.md: Feed preferred 4:5
  - Orange CTA +32.5% conversion (libera-inc.co.jp)
"""

import argparse
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# ===========================================================================
# Design System (Research-Backed)
# ===========================================================================

SIZES = {
    "feed": (1080, 1350),   # 4:5 vertical (Meta preferred, max feed area)
    "story": (1080, 1920),  # 9:16 (stories/reels)
}

# === Color Palette ===
# 70% base (white) : 25% main (teal) : 5% accent (orange)
# Source: Healthcare branding 85% blue/teal, Japanese CTA guide 70:25:5

WHITE = (255, 255, 255)
OFF_WHITE = (248, 249, 250)
LIGHT_GRAY = (240, 242, 245)
MID_GRAY = (160, 170, 180)
DARK_TEXT = (35, 45, 55)       # Near-black for readability
SUB_TEXT = (100, 110, 125)     # Secondary text

# Main brand: Healthcare teal
TEAL = (98, 186, 196)          # #62bac4 - trust, calm, healing
TEAL_DARK = (72, 137, 145)     # #488991
TEAL_LIGHT = (220, 242, 245)   # Light teal background

# Accent: Orange (CTA conversion +32.5%)
ORANGE = (243, 115, 54)        # #F37336 - action, warmth
ORANGE_DARK = (220, 95, 40)

# Support colors
LINE_GREEN = (6, 199, 85)      # LINE brand
CORAL = (244, 167, 187)        # #F4A7BB - nursing warmth (sakura pink)
SOFT_RED = (220, 80, 80)       # For "bad" comparison
EMERALD = (40, 175, 100)       # For "good" comparison
GOLD = (245, 190, 50)

# === Fonts ===
# 丸ゴシック = rounded sans-serif → warmth + professionalism
# Source: anagrams.jp font guide, Japanese nursing recruitment best practice

FONT_MARU = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"
FONT_BOLD = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_HEAVY = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"
FONT_REGULAR = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"

_font_cache = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        try:
            _font_cache[key] = ImageFont.truetype(path, size)
        except OSError:
            _font_cache[key] = ImageFont.truetype(FONT_REGULAR, size)
    return _font_cache[key]


# ===========================================================================
# Drawing Helpers
# ===========================================================================

def fill_white(img: Image.Image):
    """Fill image with off-white base."""
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), img.size], fill=OFF_WHITE)


def draw_teal_header(draw: ImageDraw.Draw, w: int, h: int):
    """Draw a teal accent bar at the top."""
    draw.rectangle([(0, 0), (w, 6)], fill=TEAL)


def center_text(draw: ImageDraw.Draw, text: str, y: int, f, fill, w: int) -> int:
    """Draw centered text. Returns the bottom y position."""
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (w - tw) // 2
    draw.text((x, y), text, fill=fill, font=f)
    return y + th


def draw_pill_badge(draw: ImageDraw.Draw, text: str, cx: int, y: int, f,
                    bg_color, text_color, pad_x=24, pad_y=8):
    """Draw a pill-shaped badge centered at cx."""
    bbox = draw.textbbox((0, 0), text, font=f)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x1 = cx - tw // 2 - pad_x
    x2 = cx + tw // 2 + pad_x
    y2 = y + th + pad_y * 2
    draw.rounded_rectangle([(x1, y), (x2, y2)], radius=(y2 - y) // 2,
                           fill=bg_color)
    draw.text((cx - tw // 2, y + pad_y), text, fill=text_color, font=f)
    return y2


def draw_cta_button(draw: ImageDraw.Draw, w: int, y: int,
                    main_text: str, sub_text: str = None,
                    bg_color=ORANGE, text_color=WHITE, btn_w=560):
    """Draw CTA button with optional microcopy below."""
    btn_h = 72
    btn_x = (w - btn_w) // 2
    draw.rounded_rectangle([(btn_x, y), (btn_x + btn_w, y + btn_h)],
                           radius=36, fill=bg_color)
    f = font(FONT_BOLD, 30)
    center_text(draw, main_text, y + 18, f, text_color, w)

    if sub_text:
        sf = font(FONT_MARU, 18)
        center_text(draw, sub_text, y + btn_h + 12, sf, MID_GRAY, w)
    return y + btn_h + (40 if sub_text else 10)


def draw_brand_footer(draw: ImageDraw.Draw, w: int, h: int):
    """Draw subtle brand footer."""
    # Thin teal line
    line_y = h - 60
    lw = 200
    draw.line([(w // 2 - lw, line_y), (w // 2 + lw, line_y)],
              fill=TEAL_LIGHT, width=1)
    f = font(FONT_MARU, 20)
    center_text(draw, "ナースロビー  |  手数料10%の看護師転職", h - 42, f, MID_GRAY, w)


# ===========================================================================
# AD1: 地域密着型 (v2 - white base, teal accent)
# ===========================================================================

def generate_ad1_local(size_name: str = "feed") -> Image.Image:
    w, h = SIZES[size_name]
    img = Image.new("RGB", (w, h), OFF_WHITE)
    draw = ImageDraw.Draw(img)
    draw_teal_header(draw, w, h)

    pad = 70
    is_feed = size_name == "feed"

    # --- Top section: Badge + Headline ---
    y = 50 if is_feed else 120

    badge_f = font(FONT_MARU, 22 if is_feed else 24)
    y = draw_pill_badge(draw, "神奈川県西部エリア", w // 2, y, badge_f,
                        TEAL, WHITE) + 30

    # Main headline
    h1_size = 62 if is_feed else 70
    h1 = font(FONT_HEAVY, h1_size)
    for line in ["小田原・平塚の", "看護師さんへ"]:
        center_text(draw, line, y, h1, DARK_TEXT, w)
        y += h1_size + 20

    # Teal underline
    y += 10
    draw.rounded_rectangle([(w // 2 - 60, y), (w // 2 + 60, y + 4)],
                           radius=2, fill=TEAL)
    y += 30

    # Sub message
    sub_f = font(FONT_MARU, 30 if is_feed else 34)
    center_text(draw, "あなたの地元で", y, sub_f, SUB_TEXT, w)
    y += 42
    center_text(draw, "理想の職場、見つかります", y, sub_f, SUB_TEXT, w)
    y += 60

    # --- Feature cards ---
    features = [
        ("地元密着", "小田原・平塚・秦野\n南足柄・箱根エリア", TEAL),
        ("手数料10%", "業界平均の1/3\n病院も安心の低コスト", EMERALD),
        ("AI × 人", "AIが条件マッチング\n人間が面談サポート", ORANGE),
    ]

    card_w = (w - pad * 2 - 30) // 3
    card_h = 170 if is_feed else 190

    for i, (title, desc, accent) in enumerate(features):
        cx = pad + i * (card_w + 15)

        # Card with light background + colored top accent
        draw.rounded_rectangle([(cx, y), (cx + card_w, y + card_h)],
                               radius=16, fill=WHITE, outline=LIGHT_GRAY)
        draw.rounded_rectangle([(cx, y), (cx + card_w, y + 5)],
                               radius=0, fill=accent)

        # Title
        tf = font(FONT_BOLD, 24 if is_feed else 26)
        tbbox = draw.textbbox((0, 0), title, font=tf)
        ttw = tbbox[2] - tbbox[0]
        draw.text((cx + (card_w - ttw) // 2, y + 22), title, fill=accent, font=tf)

        # Description
        df = font(FONT_MARU, 17 if is_feed else 19)
        dy = y + 60
        for dline in desc.split("\n"):
            dbbox = draw.textbbox((0, 0), dline, font=df)
            dtw = dbbox[2] - dbbox[0]
            draw.text((cx + (card_w - dtw) // 2, dy), dline, fill=SUB_TEXT, font=df)
            dy += 26

    y += card_h + 40

    # --- CTA ---
    draw_cta_button(draw, w, y,
                    "LINEで無料相談する  →",
                    "30秒で登録完了・営業電話なし",
                    bg_color=ORANGE)

    # --- Footer ---
    draw_brand_footer(draw, w, h)

    return img


# ===========================================================================
# AD2: 手数料比較型 (v2 - clean white, data-driven)
# ===========================================================================

def generate_ad2_comparison(size_name: str = "feed") -> Image.Image:
    w, h = SIZES[size_name]
    img = Image.new("RGB", (w, h), OFF_WHITE)
    draw = ImageDraw.Draw(img)
    draw_teal_header(draw, w, h)

    pad = 70
    is_feed = size_name == "feed"

    y = 50 if is_feed else 120

    # Headline
    h1 = font(FONT_HEAVY, 44 if is_feed else 50)
    center_text(draw, "知ってた？この差。", y, h1, DARK_TEXT, w)
    y += 70

    sub_f = font(FONT_MARU, 24 if is_feed else 28)
    center_text(draw, "看護師の転職エージェント手数料", y, sub_f, SUB_TEXT, w)
    y += 50

    # --- Comparison boxes ---
    box_w = (w - pad * 2 - 30) // 2
    box_h = 280 if is_feed else 320
    left_x = pad
    right_x = pad + box_w + 30

    # Left: 大手 30% (light red tint)
    draw.rounded_rectangle([(left_x, y), (left_x + box_w, y + box_h)],
                           radius=20, fill=(255, 240, 240), outline=(230, 200, 200))

    lf = font(FONT_BOLD, 22)
    center_text(draw, "大手エージェント", y + 20, lf, SOFT_RED, left_x * 2 + box_w)

    big = font(FONT_HEAVY, 90 if is_feed else 100)
    center_text(draw, "30%", y + 65, big, SOFT_RED, left_x * 2 + box_w)

    detail_f = font(FONT_MARU, 20)
    center_text(draw, "年収400万の場合", y + box_h - 85, detail_f, SUB_TEXT,
                left_x * 2 + box_w)
    cost_f = font(FONT_BOLD, 28)
    center_text(draw, "→ 120万円", y + box_h - 55, cost_f, SOFT_RED,
                left_x * 2 + box_w)

    # Right: ナースロビー 10% (light green tint)
    draw.rounded_rectangle([(right_x, y), (right_x + box_w, y + box_h)],
                           radius=20, fill=(235, 250, 240), outline=(190, 230, 200))

    center_text(draw, "ナースロビー", y + 20, lf, EMERALD, right_x * 2 + box_w)
    center_text(draw, "10%", y + 65, big, EMERALD, right_x * 2 + box_w)
    center_text(draw, "年収400万の場合", y + box_h - 85, detail_f, SUB_TEXT,
                right_x * 2 + box_w)
    center_text(draw, "→ 40万円", y + box_h - 55, cost_f, EMERALD,
                right_x * 2 + box_w)

    # VS circle
    vs_cx = w // 2
    vs_cy = y + box_h // 2
    r = 32
    draw.ellipse([(vs_cx - r, vs_cy - r), (vs_cx + r, vs_cy + r)], fill=GOLD)
    vs_f = font(FONT_HEAVY, 28)
    center_text(draw, "VS", vs_cy - 15, vs_f, WHITE, w)

    y += box_h + 30

    # Bottom explanation
    hl_f = font(FONT_BOLD, 28 if is_feed else 32)
    center_text(draw, "差額80万円 ＝ 病院のコスト負担", y, hl_f, TEAL_DARK, w)
    y += 45

    exp_f = font(FONT_MARU, 22 if is_feed else 24)
    for line in ["手数料が安い → 病院が積極的に採用",
                 "→ あなたの給与交渉が有利に"]:
        center_text(draw, line, y, exp_f, SUB_TEXT, w)
        y += 35

    y += 25

    # CTA
    draw_cta_button(draw, w, y,
                    "詳しくはLINEで  →  相談無料",
                    "営業電話なし・いつでもブロックOK",
                    bg_color=ORANGE)

    draw_brand_footer(draw, w, h)
    return img


# ===========================================================================
# AD3: 共感型 (v2 - white base, warm coral accent)
# ===========================================================================

def generate_ad3_empathy(size_name: str = "feed") -> Image.Image:
    w, h = SIZES[size_name]
    img = Image.new("RGB", (w, h), OFF_WHITE)
    draw = ImageDraw.Draw(img)

    pad = 70
    is_feed = size_name == "feed"

    # Coral accent bar at top (warmer than teal for empathy)
    draw.rectangle([(0, 0), (w, 6)], fill=CORAL)

    y = 50 if is_feed else 120

    # Hook headline
    h1_size = 58 if is_feed else 66
    h1 = font(FONT_HEAVY, h1_size)
    for line in ["人間関係、", "疲れてない？"]:
        center_text(draw, line, y, h1, DARK_TEXT, w)
        y += h1_size + 18

    # Sub
    y += 5
    sub_f = font(FONT_MARU, 26 if is_feed else 30)
    center_text(draw, "それ、環境を変えるだけで", y, sub_f, SUB_TEXT, w)
    y += 38
    center_text(draw, "解決するかも。", y, sub_f, SUB_TEXT, w)
    y += 55

    # Pain points with checkmarks
    pains = [
        "「前にも言ったよね」が口癖の先輩",
        "残業が当たり前の空気",
        "夜勤明けでも呼び出される",
        "頑張っても給料が上がらない",
    ]
    check_f = font(FONT_MARU, 24 if is_feed else 27)
    for pain in pains:
        # Teal checkmark + text
        draw.text((pad, y), "✓", fill=TEAL, font=check_f)
        draw.text((pad + 35, y), pain, fill=DARK_TEXT, font=check_f)
        y += 42 if is_feed else 48

    # Divider
    y += 15
    draw.line([(pad, y), (w - pad, y)], fill=LIGHT_GRAY, width=2)
    y += 25

    # Solution
    sol_f = font(FONT_BOLD, 30 if is_feed else 34)
    center_text(draw, "神奈川西部で、あなたに合う職場", y, sol_f, DARK_TEXT, w)
    y += 45
    sol2_f = font(FONT_BOLD, 26 if is_feed else 30)
    center_text(draw, "AI × 人の寄り添いサポート", y, sol2_f, TEAL, w)
    y += 50

    # Stats row
    stats = [("97施設", "の求人データ"), ("手数料10%", "で病院も安心"), ("相談無料", "LINEでOK")]
    stat_w = (w - pad * 2) // 3
    for i, (num, label) in enumerate(stats):
        sx = pad + i * stat_w
        cx = sx + stat_w // 2

        nf = font(FONT_BOLD, 30 if is_feed else 34)
        bbox = draw.textbbox((0, 0), num, font=nf)
        draw.text((cx - (bbox[2] - bbox[0]) // 2, y), num, fill=TEAL_DARK, font=nf)

        lf_ = font(FONT_MARU, 17 if is_feed else 19)
        bbox2 = draw.textbbox((0, 0), label, font=lf_)
        draw.text((cx - (bbox2[2] - bbox2[0]) // 2, y + 38), label, fill=MID_GRAY, font=lf_)

    y += 85

    # CTA
    draw_cta_button(draw, w, y,
                    "まずはLINEで相談する  →",
                    "30秒で登録・営業電話なし",
                    bg_color=ORANGE)

    draw_brand_footer(draw, w, h)
    return img


# ===========================================================================
# Main
# ===========================================================================

AD_GENERATORS = {
    "ad1_local": generate_ad1_local,
    "ad2_comparison": generate_ad2_comparison,
    "ad3_empathy": generate_ad3_empathy,
}


def main():
    parser = argparse.ArgumentParser(description="Meta広告クリエイティブ生成 v2.0")
    parser.add_argument("--output", default="content/meta_ads/v2/", help="出力ディレクトリ")
    parser.add_argument("--ad", choices=list(AD_GENERATORS.keys()) + ["all"],
                        default="all")
    parser.add_argument("--size", choices=["feed", "story", "all"], default="all")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ads = list(AD_GENERATORS.keys()) if args.ad == "all" else [args.ad]
    sizes = list(SIZES.keys()) if args.size == "all" else [args.size]

    timestamp = datetime.now().strftime("%Y%m%d")
    generated = []

    for ad_name in ads:
        for size_name in sizes:
            img = AD_GENERATORS[ad_name](size_name)
            filename = f"{timestamp}_{ad_name}_{size_name}.png"
            filepath = output_dir / filename
            img.save(str(filepath), "PNG", optimize=True)
            generated.append(str(filepath))
            print(f"✅ {filename} ({img.size[0]}x{img.size[1]})")

    print(f"\n生成完了: {len(generated)}枚 → {output_dir}/")


if __name__ == "__main__":
    main()
