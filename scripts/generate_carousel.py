#!/usr/bin/env python3
"""
generate_carousel.py -- TikTok/Instagramカルーセルスライド生成エンジン v4.0

プラットフォーム別にネイティブ解像度でレンダリング:
  - TikTok: 1080x1920 (9:16)
  - Instagram Feed: 1080x1350 (4:5) -- ネイティブ描画、リサイズなし
  - Instagram Story: 1080x1920 (9:16)

v4.0 改善点:
  - 丸ゴシック（ヒラギノ丸ゴ ProN W4）をメインフォントに追加（温かみ＋親しみ）
  - カテゴリ別テンプレート5種（あるある/給与/転職/地域ネタ/サービス紹介）
  - 描画プリミティブ群: 吹き出し、アイコン、棒グラフ、数字強調、スワイプ矢印
  - CTA強化: 保存アイコン、LINE緑ボタン風、信頼バッジ改良
  - スワイプ誘導: スライド1-3に「スワイプ→」三連矢印
  - グラデーション背景のバリエーション拡大
  - --demo-all で全カテゴリ一括デモ生成

v3.1 改善点:
  - Instagram 1080x1350 ネイティブ描画（リサイズによる歪み解消）
  - 禁則処理改善（NO_END_CHARS追加、幅超過時の再測定）

使い方:
  python3 scripts/generate_carousel.py --demo
  python3 scripts/generate_carousel.py --demo-all
  python3 scripts/generate_carousel.py --queue data/posting_queue.json --output content/generated/
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Load CTA template (シン・AI転職)
_cta_template_path = Path(__file__).parent.parent / "content" / "templates" / "cta_shin_ai.json"
CTA_TEMPLATE = {}
if _cta_template_path.exists():
    with open(_cta_template_path) as _f:
        CTA_TEMPLATE = json.load(_f)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from playwright.sync_api import sync_playwright
    from jinja2 import Environment, FileSystemLoader
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ===========================================================================
# ブランドカラーシステム（docs/brand-system.md 準拠）
# ===========================================================================
BRAND_COLORS = {
    "primary": "#1A6B8A",        # ロビーブルー
    "primary_light": "#E8F4F8",  # ソフトブルー
    "secondary": "#E8756D",      # ウォームコーラル
    "secondary_light": "#FFF0EE",# ソフトコーラル
    "accent": "#D4A843",         # マスタード
    "accent_light": "#FFF8E8",   # ソフトイエロー
    "cta": "#2D9F6F",            # ロビーグリーン
    "text": "#2C2C2C",           # チャコール
    "text_sub": "#6B7280",       # グレー
    "bg_light": "#F5F5F5",       # ライトグレー
    "white": "#FFFFFF",
}

CATEGORY_COLORS = {
    "aruaru":    {"bg": "#FFF0EE", "accent": "#E8756D"},
    "kyuyo":     {"bg": "#FFF8E8", "accent": "#D4A843"},
    "gyoukai":   {"bg": "#E8F4F8", "accent": "#1A6B8A"},
    "chiiki":    {"bg": "#E8F4F8", "accent": "#1A6B8A"},
    "tenshoku":  {"bg": "#E8F4F8", "accent": "#1A6B8A"},
    "trend":     {"bg": "#F5F5F5", "accent": "#1A6B8A"},
    "service":   {"bg": "#FFFFFF", "accent": "#2D9F6F"},
}


def _hex_to_rgb(hex_color: str) -> tuple:
    """HEX文字列 (#RRGGBB) を RGB タプルに変換するユーティリティ。"""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ===========================================================================
# Constants
# ===========================================================================

CANVAS_W = 1080
CANVAS_H = 1920

# Instagram native canvas (4:5 feed) -- rendered natively, NOT resized
INSTAGRAM_W = 1080
INSTAGRAM_H = 1350

# Platform-specific dimensions
PLATFORM_SIZES = {
    "tiktok": (1080, 1920),     # 9:16
    "instagram": (1080, 1350),  # 4:5 (feed)
    "instagram_story": (1080, 1920),  # 9:16 (stories/reels)
}

# TikTok UI safe zones (includes +20px buffer for video motion crop at 1.04x scale)
SAFE_TOP = 170
SAFE_BOTTOM = 270
SAFE_RIGHT = 115
SAFE_LEFT = 75

# Instagram safe zones (less restrictive, no UI overlay)
IG_SAFE = {"top": 70, "bottom": 70, "left": 70, "right": 70}

# Platform safe zones lookup
SAFE_ZONES = {
    "tiktok": {"top": 170, "bottom": 270, "left": 75, "right": 115},
    "instagram": IG_SAFE,
    "instagram_story": {"top": 150, "bottom": 250, "left": 60, "right": 100},
}

# Derived safe content area (TikTok)
CONTENT_X = SAFE_LEFT
CONTENT_Y = SAFE_TOP
CONTENT_W = CANVAS_W - SAFE_LEFT - SAFE_RIGHT  # 920
CONTENT_H = CANVAS_H - SAFE_TOP - SAFE_BOTTOM  # 1520

# Derived safe content area (Instagram native)
IG_CONTENT_X = IG_SAFE["left"]                                    # 70
IG_CONTENT_Y = IG_SAFE["top"]                                     # 70
IG_CONTENT_W = INSTAGRAM_W - IG_SAFE["left"] - IG_SAFE["right"]  # 940
IG_CONTENT_H = INSTAGRAM_H - IG_SAFE["top"] - IG_SAFE["bottom"]  # 1210

# Platform watermarks
PLATFORM_WATERMARKS = {
    "tiktok": "@robby15051",
    "instagram": "@robby.for.nurse",
    "instagram_story": "@robby.for.nurse",
}

# Default slide count (Hook + 6 Content + CTA)
DEFAULT_SLIDE_COUNT = 8

# Text constraints
MAX_HOOK_CHARS = 25           # 1枚目は25文字以内
MAX_BODY_CHARS_PER_LINE = 15  # 1行15文字
MAX_BODY_LINES = 3            # 最大3行

LINE_HEIGHT_RATIO = 1.65

# ===========================================================================
# Category Color Themes v3.0
# ===========================================================================
# 看護師に響くカラーパレット: ピンクコーラル系 / クリーンブルー系

CATEGORY_THEMES = {
    "あるある": {
        "bg_primary": (255, 240, 243),       # soft pink
        "bg_secondary": (255, 220, 230),     # warm pink
        "bg_dark_top": (60, 15, 35),         # dark rose
        "bg_dark_bottom": (100, 25, 55),     # deep pink
        "accent": (255, 92, 120),            # vivid coral
        "accent_light": (255, 160, 175),     # light coral
        "accent_dark": (220, 50, 80),        # dark coral
        "card_bg": (255, 255, 255, 245),     # near-white
        "text_primary": (255, 255, 255),
        "text_on_light": (50, 20, 30),
        "text_secondary": (255, 190, 200),
        "gradient_a": (255, 107, 129),       # coral
        "gradient_b": (255, 154, 180),       # light rose
    },
    "あるある×AI": {
        "bg_primary": (255, 240, 243),
        "bg_secondary": (255, 220, 230),
        "bg_dark_top": (60, 15, 35),
        "bg_dark_bottom": (100, 25, 55),
        "accent": (255, 92, 120),
        "accent_light": (255, 160, 175),
        "accent_dark": (220, 50, 80),
        "card_bg": (255, 255, 255, 245),
        "text_primary": (255, 255, 255),
        "text_on_light": (50, 20, 30),
        "text_secondary": (255, 190, 200),
        "gradient_a": (255, 107, 129),
        "gradient_b": (255, 154, 180),
    },
    "転職・キャリア": {
        "bg_primary": (235, 245, 255),       # ice blue
        "bg_secondary": (210, 230, 255),     # soft blue
        "bg_dark_top": (15, 30, 65),         # deep navy
        "bg_dark_bottom": (30, 55, 100),     # navy
        "accent": (50, 130, 255),            # bright blue
        "accent_light": (130, 185, 255),     # sky blue
        "accent_dark": (20, 80, 200),        # deep blue
        "card_bg": (255, 255, 255, 245),
        "text_primary": (255, 255, 255),
        "text_on_light": (20, 35, 70),
        "text_secondary": (170, 210, 255),
        "gradient_a": (50, 130, 255),
        "gradient_b": (100, 200, 255),
    },
    "給与・待遇": {
        "bg_primary": (235, 250, 240),       # mint
        "bg_secondary": (210, 240, 220),     # soft green
        "bg_dark_top": (15, 40, 25),         # dark forest
        "bg_dark_bottom": (30, 65, 35),      # forest green
        "accent": (40, 180, 100),            # emerald
        "accent_light": (120, 210, 160),     # light green
        "accent_dark": (20, 130, 60),        # deep green
        "card_bg": (255, 255, 255, 245),
        "text_primary": (255, 255, 255),
        "text_on_light": (20, 50, 30),
        "text_secondary": (180, 230, 200),
        "gradient_a": (40, 180, 100),
        "gradient_b": (255, 200, 60),        # gold accent
    },
    "サービス紹介": {
        "bg_primary": (235, 245, 255),
        "bg_secondary": (215, 235, 255),
        "bg_dark_top": (12, 35, 70),         # deep navy
        "bg_dark_bottom": (5, 65, 95),       # teal navy
        "accent": (26, 120, 240),            # brand blue
        "accent_light": (100, 175, 255),
        "accent_dark": (15, 85, 190),
        "card_bg": (255, 255, 255, 245),
        "text_primary": (255, 255, 255),
        "text_on_light": (15, 40, 75),
        "text_secondary": (170, 215, 255),
        "gradient_a": (26, 120, 240),
        "gradient_b": (0, 200, 170),         # teal
    },
    # v4.0: 地域ネタ（Location Card テンプレ用）
    "地域ネタ": {
        "bg_primary": (255, 245, 235),       # warm cream
        "bg_secondary": (255, 230, 210),     # peach
        "bg_dark_top": (50, 25, 10),         # dark amber
        "bg_dark_bottom": (80, 40, 15),      # brown
        "accent": (255, 140, 50),            # warm orange
        "accent_light": (255, 190, 120),     # light orange
        "accent_dark": (220, 100, 20),       # deep orange
        "card_bg": (255, 255, 255, 245),
        "text_primary": (255, 255, 255),
        "text_on_light": (50, 30, 15),
        "text_secondary": (255, 200, 160),
        "gradient_a": (255, 140, 50),        # orange
        "gradient_b": (255, 90, 90),         # warm red
    },
}

# Category alias mapping (content_type -> theme key)
CATEGORY_ALIASES = {
    "aruaru": "あるある",
    "salary": "給与・待遇",
    "career": "転職・キャリア",
    "local": "地域ネタ",
    "trend": "あるある",  # トレンドはあるあると同じテーマ
    "service": "サービス紹介",
}

DEFAULT_THEME = CATEGORY_THEMES["あるある"]

# v4.0: Category-specific template types
CATEGORY_TEMPLATE_TYPE = {
    "あるある": "chat_bubble",
    "あるある×AI": "chat_bubble",
    "給与・待遇": "infographic",
    "転職・キャリア": "step",
    "地域ネタ": "location_card",
    "サービス紹介": "default_enhanced",
}

# ===========================================================================
# Instagram Design System — "Warm Coral" palette
# ===========================================================================
# Unique in the nurse recruitment market: competitors use pink/blue.
# This warm coral palette creates a distinctive, trustworthy impression.

INSTAGRAM_COLORS = {
    "primary": (255, 123, 107),        # Warm Coral #FF7B6B
    "primary_dark": (232, 93, 74),     # Deep Coral #E85D4A
    "background": (255, 248, 240),     # Soft Cream #FFF8F0
    "card_bg": (255, 255, 255),        # White card
    "text_primary": (45, 45, 45),      # Charcoal #2D2D2D
    "text_secondary": (107, 107, 107), # Warm Gray #6B6B6B
    "accent": (255, 217, 61),          # Sunny Yellow #FFD93D
    "trust": (46, 196, 182),           # Teal Green #2EC4B6
    "card_shadow": (0, 0, 0, 20),      # Subtle shadow
}

IG_FONTS = {
    "cover_title": 80,       # Cover slide main text
    "slide_title": 52,       # Content slide header
    "body": 38,              # Main content text
    "body_bold": 38,         # Bold body text (same size, different weight)
    "caption": 28,           # Secondary text, source attribution
    "accent_number": 96,     # Large data numbers (e.g., "10%")
    "brand": 24,             # Brand footer text
    "progress": 12,          # Progress dots (size reference)
}

# Instagram canvas: 1080x1350 (4:5 feed post)
IG_CANVAS_W = 1080
IG_CANVAS_H = 1350

# Common colors
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
# ブランドカラー（BRAND_COLORS 参照）
COLOR_BRAND_BLUE = _hex_to_rgb(BRAND_COLORS["primary"])   # #1A6B8A -> (26, 107, 138)
COLOR_BRAND_TEAL = _hex_to_rgb(BRAND_COLORS["cta"])       # #2D9F6F -> (45, 159, 111)

# Font paths
FONT_BOLD_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_REGULAR_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_FALLBACK_PATH = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
# v4.0: Rounded gothic for warm, friendly feel
FONT_ROUND_PATH = "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc"


# ===========================================================================
# Font loading
# ===========================================================================

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def load_font(bold: bool = False, size: int = 36, rounded: bool = False) -> ImageFont.FreeTypeFont:
    """Load a font with caching. Falls back gracefully.

    Args:
        bold: Use bold weight (W6).
        size: Font size in pixels.
        rounded: Use rounded gothic (ヒラギノ丸ゴ ProN W4) for warm feel.
    """
    key = ("round" if rounded else ("bold" if bold else "regular"), size)
    if key in _font_cache:
        return _font_cache[key]

    if rounded:
        paths = [FONT_ROUND_PATH, FONT_REGULAR_PATH, FONT_FALLBACK_PATH]
    elif bold:
        paths = [FONT_BOLD_PATH, FONT_FALLBACK_PATH]
    else:
        paths = [FONT_REGULAR_PATH, FONT_FALLBACK_PATH]

    for p in paths:
        if Path(p).exists():
            try:
                font = ImageFont.truetype(p, size)
                _font_cache[key] = font
                return font
            except Exception:
                continue

    print("FATAL: No Japanese font found. Tried:", paths)
    sys.exit(1)


# ===========================================================================
# Text utilities
# ===========================================================================

_NO_START_CHARS = set("」）】》〉』」、。！？…ー）")
_NO_END_CHARS = set("（〔［｛〈《「『【([{")


def wrap_text_jp(text: str, font: ImageFont.FreeTypeFont, max_width: int, max_chars_hint: int = 20) -> list[str]:
    """Wrap Japanese text to fit within max_width pixels.

    Implements kinsoku shori (禁則処理):
      - _NO_START_CHARS: characters that must not start a line (行頭禁止)
      - _NO_END_CHARS: characters that must not end a line (行末禁止)
    """
    paragraphs = text.split("\n")
    all_lines: list[str] = []

    for para in paragraphs:
        if not para.strip():
            all_lines.append("")
            continue

        current_line = ""
        for i, char in enumerate(para):
            test = current_line + char
            bbox = font.getbbox(test)
            w = bbox[2] - bbox[0]
            if w <= max_width:
                # Check NO_END_CHARS: if this char cannot end a line and
                # the next char would cause a break, we break before this char.
                if char in _NO_END_CHARS and i + 1 < len(para):
                    next_test = test + para[i + 1]
                    next_bbox = font.getbbox(next_test)
                    next_w = next_bbox[2] - next_bbox[0]
                    if next_w > max_width:
                        # Break before this NO_END char
                        if current_line:
                            all_lines.append(current_line)
                        current_line = char
                        continue
                current_line = test
            else:
                if char in _NO_START_CHARS and current_line:
                    # Try to keep the kinsoku char on the current line
                    test_with_char = current_line + char
                    char_bbox = font.getbbox(test_with_char)
                    char_w = char_bbox[2] - char_bbox[0]
                    # Allow slight overflow for kinsoku (up to 1 char width extra)
                    single_char_bbox = font.getbbox(char)
                    # Cap tolerance to prevent right overflow at large font sizes
                    tolerance = min(single_char_bbox[2] - single_char_bbox[0], 20)
                    if char_w <= max_width + tolerance:
                        current_line += char
                        all_lines.append(current_line)
                        current_line = ""
                    else:
                        # Too wide even with tolerance -- force break before the char
                        all_lines.append(current_line)
                        current_line = char
                else:
                    if current_line:
                        all_lines.append(current_line)
                    current_line = char
        if current_line:
            all_lines.append(current_line)

    return all_lines


def measure_text(text: str, font: ImageFont.FreeTypeFont) -> tuple[int, int]:
    """Return (width, height) of a single line of text."""
    bbox = font.getbbox(text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def text_block_height(lines: list[str], font_size: int, line_height_ratio: float = LINE_HEIGHT_RATIO) -> int:
    """Total height of a text block with line spacing."""
    if not lines:
        return 0
    line_h = int(font_size * line_height_ratio)
    return line_h * len(lines)


def _measure_text_block(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> tuple[list[str], int]:
    """Wrap text and measure total pixel height using actual font metrics.

    Returns (wrapped_lines, total_height_px).
    Uses font.getbbox() for accurate measurement instead of character-count heuristics.
    """
    lines = wrap_text_jp(text, font, max_width)
    if not lines:
        return [], 0
    total_height = 0
    for line in lines:
        bbox = font.getbbox(line)
        total_height += bbox[3] - bbox[1]
    line_spacing = int(font.size * 0.4)
    total_height += line_spacing * (len(lines) - 1)
    return lines, total_height


# ===========================================================================
# Drawing primitives
# ===========================================================================

def create_gradient(w: int, h: int, color_top: tuple, color_bottom: tuple, direction: str = "vertical") -> Image.Image:
    """Create a smooth gradient image (RGBA). Uses NumPy when available for speed."""
    if HAS_NUMPY:
        return _create_gradient_np(w, h, color_top, color_bottom, direction)
    return _create_gradient_pil(w, h, color_top, color_bottom, direction)


def _create_gradient_np(w: int, h: int, color_top: tuple, color_bottom: tuple, direction: str) -> Image.Image:
    """NumPy-accelerated gradient generation."""
    ct = np.array(color_top[:3], dtype=np.float32)
    cb = np.array(color_bottom[:3], dtype=np.float32)

    if direction == "vertical":
        ratio = np.linspace(0, 1, h, dtype=np.float32).reshape(-1, 1, 1)
        colors = ct + (cb - ct) * ratio  # (h, 1, 3)
        arr = np.broadcast_to(colors, (h, w, 3)).astype(np.uint8)
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        rgba = np.concatenate([arr, alpha], axis=2)
    elif direction == "diagonal":
        x_ratio = np.linspace(0, 1, w, dtype=np.float32).reshape(1, -1)
        y_ratio = np.linspace(0, 1, h, dtype=np.float32).reshape(-1, 1)
        ratio = (x_ratio * 0.5 + y_ratio * 0.5).reshape(h, w, 1)
        colors = ct + (cb - ct) * ratio
        arr = colors.astype(np.uint8)
        alpha = np.full((h, w, 1), 255, dtype=np.uint8)
        rgba = np.concatenate([arr, alpha], axis=2)
    else:
        # fallback to vertical
        return _create_gradient_np(w, h, color_top, color_bottom, "vertical")

    return Image.fromarray(rgba)


def _create_gradient_pil(w: int, h: int, color_top: tuple, color_bottom: tuple, direction: str) -> Image.Image:
    """Pillow-only gradient (slower but no NumPy required)."""
    img = Image.new("RGBA", (w, h))
    pixels = img.load()

    if direction == "vertical":
        for y in range(h):
            ratio = y / max(h - 1, 1)
            r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
            g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
            b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
            for x in range(w):
                pixels[x, y] = (r, g, b, 255)
    elif direction == "diagonal":
        for y in range(h):
            for x in range(w):
                ratio = (x / max(w - 1, 1) * 0.5 + y / max(h - 1, 1) * 0.5)
                r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
                g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
                b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
                pixels[x, y] = (r, g, b, 255)

    return img


def draw_text_shadow(
    draw: ImageDraw.ImageDraw,
    x: int, y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple = COLOR_WHITE,
    shadow_color: tuple = (0, 0, 0, 100),
    shadow_offset: int = 4,
    outline: bool = True,
    outline_color: tuple = (0, 0, 0, 140),
    outline_width: int = 2,
):
    """Draw text with drop shadow + optional outline for maximum readability."""
    # Shadow
    draw.text((x + shadow_offset, y + shadow_offset), text, fill=shadow_color, font=font)
    # Outline
    if outline:
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.text((x + dx, y + dy), text, fill=outline_color, font=font)
    # Main text
    draw.text((x, y), text, fill=fill, font=font)


def draw_centered_text_block(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    font_size: int,
    center_x: int,
    start_y: int,
    fill: tuple = COLOR_WHITE,
    shadow: bool = False,
    shadow_color: tuple = (0, 0, 0, 100),
    shadow_offset: int = 4,
    line_height_ratio: float = LINE_HEIGHT_RATIO,
) -> int:
    """Draw multiple lines centered. Returns Y after last line."""
    line_h = int(font_size * line_height_ratio)
    cy = start_y
    for line in lines:
        tw, _ = measure_text(line, font)
        tx = center_x - tw // 2
        if shadow:
            draw_text_shadow(draw, tx, cy, line, font, fill=fill,
                             shadow_color=shadow_color, shadow_offset=shadow_offset)
        else:
            draw.text((tx, cy), line, fill=fill, font=font)
        cy += line_h
    return cy


# ===========================================================================
# Decorative elements v3.0
# ===========================================================================

def _draw_dot_grid(draw: ImageDraw.ImageDraw, theme: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H, alpha: int = 15, spacing: int = 60):
    """Draw a subtle dot grid pattern across the canvas."""
    color = (*theme["accent"][:3], alpha)
    for y in range(0, canvas_h, spacing):
        for x in range(0, canvas_w, spacing):
            r = 2
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def _draw_corner_accents(draw: ImageDraw.ImageDraw, theme: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H, alpha: int = 40):
    """Draw decorative corner accent lines."""
    color = (*theme["accent"][:3], alpha)
    length = 120
    thickness = 3
    margin = 40

    # Top-left
    draw.line([(margin, margin), (margin + length, margin)], fill=color, width=thickness)
    draw.line([(margin, margin), (margin, margin + length)], fill=color, width=thickness)

    # Top-right
    draw.line([(canvas_w - margin, margin), (canvas_w - margin - length, margin)], fill=color, width=thickness)
    draw.line([(canvas_w - margin, margin), (canvas_w - margin, margin + length)], fill=color, width=thickness)

    # Bottom-left
    draw.line([(margin, canvas_h - margin), (margin + length, canvas_h - margin)], fill=color, width=thickness)
    draw.line([(margin, canvas_h - margin), (margin, canvas_h - margin - length)], fill=color, width=thickness)

    # Bottom-right
    draw.line([(canvas_w - margin, canvas_h - margin), (canvas_w - margin - length, canvas_h - margin)], fill=color, width=thickness)
    draw.line([(canvas_w - margin, canvas_h - margin), (canvas_w - margin, canvas_h - margin - length)], fill=color, width=thickness)


def _draw_decorative_rings(img: Image.Image, theme: dict, count: int = 3, alpha: int = 12):
    """Draw decorative translucent rings on the image."""
    iw, ih = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    accent = theme["accent"]

    positions = [
        (iw * 0.85, ih * 0.15, 180),
        (iw * 0.1, ih * 0.7, 140),
        (iw * 0.75, ih * 0.85, 100),
    ]

    for i in range(min(count, len(positions))):
        cx, cy, radius = positions[i]
        cx, cy, radius = int(cx), int(cy), int(radius)
        ring_color = (*accent[:3], alpha)
        for t in range(3):  # ring thickness
            r = radius + t * 3
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=ring_color, width=2)

    return Image.alpha_composite(img, overlay)


def _draw_diagonal_stripes(img: Image.Image, theme: dict, alpha: int = 8):
    """Draw subtle diagonal stripe pattern."""
    iw, ih = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    color = (*theme["accent_light"][:3], alpha)
    spacing = 80

    for offset in range(-ih, iw + ih, spacing):
        d.line([(offset, 0), (offset + ih, ih)], fill=color, width=1)

    return Image.alpha_composite(img, overlay)


# ===========================================================================
# v4.0 Drawing primitives — category-specific visual elements
# ===========================================================================

def draw_speech_bubble(
    img: Image.Image,
    x: int, y: int, w: int, h: int,
    text: str,
    is_right: bool = False,
    bg_color: tuple = (255, 255, 255, 240),
    text_color: tuple = (50, 20, 30),
    tail_size: int = 20,
    font_size: int = 48,
) -> Image.Image:
    """Draw a chat-style speech bubble with tail pointer.

    Args:
        is_right: If True, bubble appears on right side (ロビー側). Tail points right.
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    radius = 24

    # Shadow
    d.rounded_rectangle(
        (x + 3, y + 4, x + w + 3, y + h + 4),
        radius=radius, fill=(0, 0, 0, 20),
    )
    # Bubble body
    d.rounded_rectangle(
        (x, y, x + w, y + h),
        radius=radius, fill=bg_color,
    )

    # Tail triangle
    tail_y = y + h - 30
    if is_right:
        # Tail on right side
        tx = x + w
        d.polygon([
            (tx, tail_y), (tx + tail_size, tail_y + tail_size // 2), (tx, tail_y + tail_size)
        ], fill=bg_color)
    else:
        # Tail on left side
        tx = x
        d.polygon([
            (tx, tail_y), (tx - tail_size, tail_y + tail_size // 2), (tx, tail_y + tail_size)
        ], fill=bg_color)

    result = Image.alpha_composite(img, overlay)

    # Draw text - vertically centered within the bubble
    draw = ImageDraw.Draw(result)
    font = load_font(bold=False, size=font_size, rounded=True)
    pad_x = max(30, w // 15)  # Horizontal padding scales with bubble width
    text_max_w = w - pad_x * 2
    lines = wrap_text_jp(text, font, text_max_w)
    line_h = int(font_size * 1.55)
    block_h = line_h * len(lines)
    text_y = y + (h - block_h) // 2
    for line in lines:
        draw.text((x + pad_x, text_y), line, fill=text_color, font=font)
        text_y += line_h

    return result


def draw_icon_stethoscope(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 40, color: tuple = (255, 255, 255)):
    """Draw a simple stethoscope icon using basic shapes."""
    r = size // 2
    # Earpieces (top)
    draw.ellipse((cx - r, cy - r, cx - r + 8, cy - r + 8), fill=color)
    draw.ellipse((cx + r - 8, cy - r, cx + r, cy - r + 8), fill=color)
    # Tubes
    draw.line([(cx - r + 4, cy - r + 4), (cx, cy + r // 2)], fill=color, width=3)
    draw.line([(cx + r - 4, cy - r + 4), (cx, cy + r // 2)], fill=color, width=3)
    # Chest piece (circle at bottom)
    cr = size // 4
    draw.ellipse((cx - cr, cy + r // 2, cx + cr, cy + r // 2 + cr * 2), outline=color, width=3)


def draw_icon_yen(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 40, color: tuple = (255, 200, 60)):
    """Draw a yen sign icon."""
    font = load_font(bold=True, size=size)
    text = "¥"
    tw, th = measure_text(text, font)
    # Circle background
    r = size // 2 + 8
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color[:3], 40))
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(*color[:3], 120), width=2)
    draw.text((cx - tw // 2, cy - th // 2), text, fill=color, font=font)


def draw_icon_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 30, color: tuple = (255, 92, 120)):
    """Draw a simple heart icon."""
    r = size // 4
    # Two circles + triangle to form heart
    draw.ellipse((cx - r * 2, cy - r, cx, cy + r), fill=color)
    draw.ellipse((cx, cy - r, cx + r * 2, cy + r), fill=color)
    draw.polygon([
        (cx - r * 2, cy), (cx + r * 2, cy), (cx, cy + r * 3)
    ], fill=color)


def draw_icon_location_pin(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int = 40, color: tuple = (255, 140, 50)):
    """Draw a location pin icon."""
    r = size // 3
    # Pin body (circle)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # Pin point (triangle)
    draw.polygon([
        (cx - r, cy + r // 2), (cx + r, cy + r // 2), (cx, cy + size)
    ], fill=color)
    # Inner dot (white)
    ir = r // 2
    draw.ellipse((cx - ir, cy - ir, cx + ir, cy + ir), fill=(255, 255, 255))


def draw_bar_chart(
    img: Image.Image,
    x: int, y: int, w: int, h: int,
    data: list[dict],
    bar_color: tuple = (40, 180, 100),
    highlight_idx: int = -1,
    highlight_color: tuple = (255, 200, 60),
) -> Image.Image:
    """Draw a horizontal bar chart.

    Args:
        data: List of {label: str, value: int/float, display: str}.
        highlight_idx: Index of bar to highlight (e.g., 神奈川ナース転職).
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    if not data:
        return img

    max_val = max(item.get("value", 0) for item in data) or 1
    n_bars = len(data)
    label_w = 200
    bar_area_w = w - label_w - 80
    bar_h = min(50, (h - 20) // n_bars - 12)
    gap = 16

    label_font = load_font(bold=False, size=min(28, bar_h - 4), rounded=True)
    value_font = load_font(bold=True, size=min(26, bar_h - 4))

    total_bars_h = n_bars * (bar_h + gap) - gap
    start_y = y + (h - total_bars_h) // 2

    for i, item in enumerate(data):
        by = start_y + i * (bar_h + gap)
        label = item.get("label", "")
        value = item.get("value", 0)
        display = item.get("display", str(value))

        # Label
        d.text((x, by + (bar_h - 20) // 2), label, fill=(255, 255, 255, 220), font=label_font)

        # Bar
        bar_x = x + label_w
        bar_w = int(bar_area_w * (value / max_val))
        bar_w = max(bar_w, 10)
        color = highlight_color if i == highlight_idx else bar_color
        d.rounded_rectangle(
            (bar_x, by, bar_x + bar_w, by + bar_h),
            radius=bar_h // 2, fill=(*color[:3], 220),
        )

        # Value text
        d.text((bar_x + bar_w + 12, by + (bar_h - 20) // 2), display,
               fill=(255, 255, 255, 240), font=value_font)

    return Image.alpha_composite(img, overlay)


def draw_number_callout(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int,
    number: str,
    label: str = "",
    number_color: tuple = (255, 200, 60),
    label_color: tuple = (255, 255, 255, 200),
    number_size: int = 100,
) -> int:
    """Draw a large emphasized number with optional label below. Returns bottom Y."""
    num_font = load_font(bold=True, size=number_size)
    tw, th = measure_text(number, num_font)
    draw.text((cx - tw // 2, cy), number, fill=number_color, font=num_font)
    bottom = cy + int(number_size * 1.2)
    if label:
        label_font = load_font(bold=False, size=28, rounded=True)
        ltw, _ = measure_text(label, label_font)
        draw.text((cx - ltw // 2, bottom), label, fill=label_color, font=label_font)
        bottom += 40
    return bottom


def draw_swipe_indicator(
    img: Image.Image,
    canvas_w: int, canvas_h: int,
    safe_bottom: int,
    style: str = "arrow",
    color: tuple = (255, 255, 255, 140),
) -> Image.Image:
    """Draw a swipe indicator at the bottom of the slide.

    style: "arrow" (three chevrons), "text" (スワイプ→ text)
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)

    y_base = canvas_h - safe_bottom - 60
    cx = canvas_w // 2

    if style == "arrow":
        # Three animated-style chevrons >>>
        for i in range(3):
            alpha = max(40, 140 - i * 40)
            arrow_color = (*color[:3], alpha)
            ax = cx + 60 + i * 35
            # Draw chevron (>)
            d.line([(ax, y_base - 12), (ax + 14, y_base), (ax, y_base + 12)],
                   fill=arrow_color, width=3)
        # "スワイプ" text
        font = load_font(bold=True, size=24, rounded=True)
        text = "スワイプ"
        tw, _ = measure_text(text, font)
        d.text((cx - tw // 2 - 10, y_base - 12), text, fill=color, font=font)
    else:
        font = load_font(bold=True, size=28, rounded=True)
        text = ">>> スワイプ"
        tw, _ = measure_text(text, font)
        d.text((cx - tw // 2, y_base - 14), text, fill=color, font=font)

    return Image.alpha_composite(img, overlay)


def draw_step_number(
    draw: ImageDraw.ImageDraw,
    cx: int, cy: int,
    number: int,
    size: int = 56,
    bg_color: tuple = (50, 130, 255),
    text_color: tuple = (255, 255, 255),
):
    """Draw a circled step number (for step-type template)."""
    r = size // 2
    # Circle
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=bg_color)
    # Number
    font = load_font(bold=True, size=int(size * 0.55))
    text = str(number)
    tw, th = measure_text(text, font)
    draw.text((cx - tw // 2, cy - th // 2 - 2), text, fill=text_color, font=font)


def draw_area_badge(
    draw: ImageDraw.ImageDraw,
    cx: int, y: int,
    area_name: str,
    bg_color: tuple = (255, 140, 50),
    text_color: tuple = (255, 255, 255),
) -> int:
    """Draw an area name badge with location pin. Returns bottom Y."""
    font = load_font(bold=True, size=36, rounded=True)
    tw, th = measure_text(area_name, font)
    pad_x, pad_y = 30, 14
    badge_w = tw + pad_x * 2 + 40  # 40 for pin icon space
    badge_h = th + pad_y * 2
    bx = cx - badge_w // 2

    # Badge background
    draw.rounded_rectangle(
        (bx, y, bx + badge_w, y + badge_h),
        radius=badge_h // 2, fill=bg_color,
    )
    # Location pin icon
    draw_icon_location_pin(draw, bx + 28, y + badge_h // 2, size=24, color=text_color)
    # Text
    draw.text((bx + 50, y + pad_y), area_name, fill=text_color, font=font)
    return y + badge_h


def draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int, y: int, w: int,
    progress: float,
    bar_height: int = 12,
    bg_color: tuple = (255, 255, 255, 40),
    fill_color: tuple = (50, 130, 255),
) -> None:
    """Draw a horizontal progress bar."""
    # Background
    draw.rounded_rectangle(
        (x, y, x + w, y + bar_height),
        radius=bar_height // 2, fill=bg_color,
    )
    # Filled portion
    fill_w = int(w * max(0, min(1, progress)))
    if fill_w > bar_height:
        draw.rounded_rectangle(
            (x, y, x + fill_w, y + bar_height),
            radius=bar_height // 2, fill=fill_color,
        )


# ===========================================================================
# Background builders v3.0
# ===========================================================================

def _build_dark_bg(theme: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> Image.Image:
    """Dark gradient background with glow and decorative elements."""
    bg = create_gradient(canvas_w, canvas_h, theme["bg_dark_top"], theme["bg_dark_bottom"])

    # Radial glow from center-top
    glow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    accent = theme["accent"]
    cx, cy = canvas_w // 2, canvas_h // 4
    for r in range(500, 0, -8):
        a = max(1, int(10 * (1 - r / 500)))
        glow_draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*accent[:3], a))
    bg = Image.alpha_composite(bg, glow)

    # Decorative elements
    bg = _draw_diagonal_stripes(bg, theme, alpha=6)
    bg = _draw_decorative_rings(bg, theme, count=2, alpha=10)

    draw = ImageDraw.Draw(bg)
    _draw_corner_accents(draw, theme, canvas_w=canvas_w, canvas_h=canvas_h, alpha=30)

    return bg


def _build_light_bg(theme: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> Image.Image:
    """Light, clean background with subtle color tint."""
    bg = create_gradient(canvas_w, canvas_h, theme["bg_primary"], theme["bg_secondary"])

    # Top accent strip
    draw = ImageDraw.Draw(bg)
    draw.rectangle([(0, 0), (canvas_w, 5)], fill=(*theme["accent"][:3], 140))

    # Subtle dot grid
    _draw_dot_grid(draw, theme, canvas_w=canvas_w, canvas_h=canvas_h, alpha=12, spacing=80)

    # Corner accents (lighter)
    _draw_corner_accents(draw, theme, canvas_w=canvas_w, canvas_h=canvas_h, alpha=25)

    return bg


def _build_accent_gradient_bg(theme: dict, canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> Image.Image:
    """Bold accent gradient for reveal/emphasis slides."""
    bg = create_gradient(canvas_w, canvas_h, theme["gradient_a"], theme["gradient_b"], direction="diagonal")
    bg = _draw_decorative_rings(bg, theme, count=3, alpha=20)
    return bg


def _build_brand_gradient_bg(canvas_w: int = CANVAS_W, canvas_h: int = CANVAS_H) -> Image.Image:
    """Brand gradient (blue-to-teal) for CTA slide."""
    bg = create_gradient(canvas_w, canvas_h, COLOR_BRAND_BLUE, COLOR_BRAND_TEAL, direction="diagonal")

    # Glow
    glow = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = canvas_w // 2, canvas_h // 2
    for r in range(600, 0, -10):
        a = max(1, int(6 * (1 - r / 600)))
        gd.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, a))
    bg = Image.alpha_composite(bg, glow)

    # Rings
    bg = _draw_decorative_rings(
        bg,
        {"accent": (255, 255, 255), "accent_light": (200, 230, 255)},
        count=3, alpha=15,
    )

    return bg


# ===========================================================================
# Slide indicators v3.0
# ===========================================================================

def _draw_slide_indicator(draw: ImageDraw.ImageDraw, current: int, total: int,
                          light_bg: bool = False, canvas_w: int = CANVAS_W, safe_top: int = SAFE_TOP):
    """Draw slide progress dots at the top."""
    dot_r = 6
    dot_gap = 20
    total_w = total * (dot_r * 2) + (total - 1) * dot_gap
    start_x = (canvas_w - total_w) // 2
    y = safe_top + 30

    for i in range(total):
        cx = start_x + i * (dot_r * 2 + dot_gap) + dot_r
        if i + 1 == current:
            # Active dot (filled, larger)
            if light_bg:
                fill = (*DEFAULT_THEME["accent"][:3], 220)
            else:
                fill = (255, 255, 255, 240)
            draw.ellipse((cx - dot_r - 2, y - dot_r - 2, cx + dot_r + 2, y + dot_r + 2), fill=fill)
        else:
            # Inactive dot
            if light_bg:
                fill = (0, 0, 0, 30)
            else:
                fill = (255, 255, 255, 50)
            draw.ellipse((cx - dot_r, y - dot_r, cx + dot_r, y + dot_r), fill=fill)


def _draw_brand_watermark(draw: ImageDraw.ImageDraw, light_bg: bool = False,
                          platform: str = "tiktok", canvas_w: int = CANVAS_W,
                          canvas_h: int = CANVAS_H, safe_bottom: int = SAFE_BOTTOM):
    """Draw subtle brand watermark with platform-specific handle."""
    font = load_font(bold=False, size=22)
    text = PLATFORM_WATERMARKS.get(platform, "@robby15051")
    tw, _ = measure_text(text, font)
    x = (canvas_w - tw) // 2
    y = canvas_h - safe_bottom + 15
    color = (0, 0, 0, 35) if light_bg else (255, 255, 255, 35)
    draw.text((x, y), text, fill=color, font=font)


# ===========================================================================
# Instagram Design System — Rendering Functions
# ===========================================================================

def _draw_progress_dots(
    draw: ImageDraw.ImageDraw,
    slide_index: int,
    total_slides: int,
    canvas_w: int,
    canvas_h: int,
):
    """Draw Instagram-style progress dots at the bottom center of a slide.

    Args:
        slide_index: 1-based index of the current slide.
        total_slides: Total number of slides in the carousel.
        canvas_w: Width of the canvas (pixels).
        canvas_h: Height of the canvas (pixels).
    """
    dot_diameter = 12
    dot_radius = dot_diameter // 2
    dot_spacing = 16  # gap between dots
    y_center = canvas_h - 48  # 48px from bottom edge

    total_w = total_slides * dot_diameter + (total_slides - 1) * dot_spacing
    start_x = (canvas_w - total_w) // 2

    coral = INSTAGRAM_COLORS["primary"]
    gray_outline = (180, 180, 180)

    for i in range(total_slides):
        cx = start_x + i * (dot_diameter + dot_spacing) + dot_radius
        cy = y_center
        bbox = (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius)

        if i + 1 == slide_index:
            # Current slide: filled coral
            draw.ellipse(bbox, fill=coral)
        else:
            # Other slides: gray outline only
            draw.ellipse(bbox, fill=None, outline=gray_outline, width=2)


def _ig_draw_brand_logo(draw: ImageDraw.ImageDraw, canvas_w: int):
    """Draw the small brand logo text at top-left for Instagram slides."""
    font = load_font(bold=True, size=28)
    text = "神奈川ナース転職"
    draw.text((40, 36), text, fill=INSTAGRAM_COLORS["primary"], font=font)


def _ig_build_cream_bg(canvas_w: int, canvas_h: int) -> Image.Image:
    """Create a flat cream background for Instagram."""
    bg_color = INSTAGRAM_COLORS["background"]
    return Image.new("RGBA", (canvas_w, canvas_h), (*bg_color, 255))


def generate_ig_hook_slide(
    hook_text: str,
    total_slides: int = DEFAULT_SLIDE_COUNT,
) -> Image.Image:
    """Instagram cover slide (Slide 1).

    Layout:
    - Background: Cream (#FFF8F0)
    - Top-left: Small brand logo text (28px, coral)
    - Center: Large title (72-80px, charcoal, max 2 lines)
    - Bottom: Coral bar (80px height) with swipe CTA
    """
    cw, ch = IG_CANVAS_W, IG_CANVAS_H
    bg = _ig_build_cream_bg(cw, ch)
    draw = ImageDraw.Draw(bg)
    colors = INSTAGRAM_COLORS
    center_x = cw // 2

    # -- Brand logo top-left --
    _ig_draw_brand_logo(draw, cw)

    # -- Large centered title --
    max_text_w = cw - 2 * IG_SAFE["left"] - 40  # 70 + 70 safe zone + 40px inner margin = 180px total

    # Try fitting at 80px, fall back to 72px if text wraps beyond 2 lines
    best_size = IG_FONTS["cover_title"]
    best_lines = [hook_text]
    for size in (80, 72):
        font = load_font(bold=True, size=size)
        lines = wrap_text_jp(hook_text, font, max_text_w)
        if len(lines) <= 2:
            best_size = size
            best_lines = lines
            break
    else:
        font = load_font(bold=True, size=72)
        best_size = 72
        best_lines = wrap_text_jp(hook_text, font, max_text_w)[:2]

    font = load_font(bold=True, size=best_size)
    line_h = int(best_size * LINE_HEIGHT_RATIO)
    block_h = line_h * len(best_lines)

    # Vertical center: between brand logo (top ~100px) and coral bar (bottom 80px)
    title_area_top = 100
    title_area_bottom = ch - 80
    text_y = title_area_top + (title_area_bottom - title_area_top - block_h) // 2

    draw_centered_text_block(
        draw, best_lines, font, best_size,
        center_x, text_y,
        fill=colors["text_primary"],
        shadow=False,
    )

    # -- Bottom coral bar (80px height, full width) --
    bar_h = 80
    bar_y = ch - bar_h
    draw.rectangle([(0, bar_y), (cw, ch)], fill=colors["primary"])

    # "スワイプで解説 →" on coral bar
    swipe_font = load_font(bold=True, size=28)
    swipe_text = "スワイプで解説 →"
    stw, _ = measure_text(swipe_text, swipe_font)
    draw.text((center_x - stw // 2, bar_y + 12), swipe_text,
              fill=COLOR_WHITE, font=swipe_font)

    # "神奈川ナース転職 | 神奈川の転職" sub-line
    sub_font = load_font(bold=False, size=24)
    sub_text = "神奈川ナース転職 | 神奈川の転職"
    subtw, _ = measure_text(sub_text, sub_font)
    draw.text((center_x - subtw // 2, bar_y + 46), sub_text,
              fill=(*COLOR_WHITE[:3], 210), font=sub_font)

    # -- Progress dots (positioned above the coral bar) --
    dots_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    dots_draw = ImageDraw.Draw(dots_layer)
    _draw_progress_dots(dots_draw, 1, total_slides, cw, bar_y + 24)
    bg = Image.alpha_composite(bg, dots_layer)

    return bg.convert("RGB")


def generate_ig_content_slide(
    slide_num: int,
    title: str,
    body: str,
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
    total_slides: int = DEFAULT_SLIDE_COUNT,
) -> Image.Image:
    """Instagram content slide (Slides 2 through N-1).

    Layout (v3.2 - variable-height card, vertically centered):
    - Background: Cream (#FFF8F0)
    - Header bar: Coral rectangle (120px), white title text (48-56px bold)
    - Content card: White rounded rectangle, height adapts to text content
    - Card + header are vertically centered in the available space
    - Body text: Charcoal (#2D2D2D), 36-40px
    - Highlight box: Yellow accent background at 30% opacity for key stats
    - Progress dots at bottom center
    """
    cw, ch = IG_CANVAS_W, IG_CANVAS_H
    colors = INSTAGRAM_COLORS
    center_x = cw // 2

    # Layout constants
    header_h = 120
    header_card_gap = 40       # gap between header bar and card
    card_left = 50
    card_right = cw - 50
    card_radius = 16
    card_inner_pad = 45        # internal padding inside card (top/bottom)
    card_inner_pad_side = 40   # internal padding inside card (left/right)
    dots_zone_h = 80           # space reserved for progress dots at bottom
    top_margin = 40            # minimum margin above header bar
    content_max_w = (card_right - card_left) - card_inner_pad_side * 2

    # ============================================================
    # PASS 1: Measure all content to determine card height
    # ============================================================

    # -- Measure title for header bar --
    title_font_size = IG_FONTS["slide_title"]  # 52px
    title_font = load_font(bold=True, size=title_font_size)
    title_max_w = cw - 100  # 50px margin each side
    title_lines = wrap_text_jp(title, title_font, title_max_w)

    if len(title_lines) > 1:
        for try_size in (48, 44, 40):
            title_font = load_font(bold=True, size=try_size)
            title_lines = wrap_text_jp(title, title_font, title_max_w)
            title_font_size = try_size
            block_h = int(title_font_size * LINE_HEIGHT_RATIO) * len(title_lines)
            if block_h <= header_h - 20:
                break
        else:
            title_lines = title_lines[:2]

    # -- Measure highlight section height --
    hl_content_h = 0
    if highlight_number:
        num_font_size = IG_FONTS["accent_number"]  # 96px
        hl_content_h += int(num_font_size * 1.3)
        if highlight_label:
            hl_content_h += 50
        else:
            hl_content_h += 30

    # -- Determine body font size and measure body text height --
    body_font_size = IG_FONTS["body"]  # 38px
    body_paragraphs = body.split("\n")

    # Maximum card height constraint: canvas - top_margin - header - gap - dots - bottom margin
    max_card_h = ch - top_margin - header_h - header_card_gap - dots_zone_h - 20
    max_body_h = max_card_h - card_inner_pad * 2 - hl_content_h

    def _calc_body_height(font_size: int) -> tuple[int, list]:
        """Calculate exact body text height and wrapped lines for each paragraph."""
        test_font = load_font(bold=False, size=font_size)
        test_line_h = int(font_size * LINE_HEIGHT_RATIO)
        h = 0
        para_data = []
        for para in body_paragraphs:
            para = para.strip()
            if not para:
                h += test_line_h // 2
                para_data.append({"type": "blank", "height": test_line_h // 2})
                continue
            is_bullet = para.startswith(("・", "- ", "* "))
            if is_bullet:
                clean = para.lstrip("・- *").strip()
                lines = wrap_text_jp(clean, test_font, content_max_w - 50)
                ph = test_line_h * len(lines) + 10
                h += ph
                para_data.append({"type": "bullet", "lines": lines, "height": ph})
            else:
                lines = wrap_text_jp(para, test_font, content_max_w)
                ph = test_line_h * len(lines) + 8
                h += ph
                para_data.append({"type": "text", "lines": lines, "height": ph})
        return h, para_data

    body_h, para_data = _calc_body_height(body_font_size)

    # Shrink font if body text overflows
    if body_h > max_body_h:
        for try_size in range(36, 26, -2):
            body_h, para_data = _calc_body_height(try_size)
            if body_h <= max_body_h:
                body_font_size = try_size
                break
        else:
            body_font_size = 26
            body_h, para_data = _calc_body_height(26)

    body_font = load_font(bold=False, size=body_font_size)
    line_h = int(body_font_size * LINE_HEIGHT_RATIO)

    # -- Calculate actual card height based on content --
    actual_content_h = hl_content_h + body_h
    card_h = card_inner_pad * 2 + actual_content_h
    # Enforce minimum card height for visual balance (just enough to avoid tiny cards)
    min_card_h = 200
    card_h = max(card_h, min_card_h)
    # Cap at maximum
    card_h = min(card_h, max_card_h)

    # ============================================================
    # PASS 2: Calculate vertical positioning (center the block)
    # ============================================================
    # Total block = header_h + header_card_gap + card_h
    total_block_h = header_h + header_card_gap + card_h
    available_space = ch - dots_zone_h  # space above dots
    # Center the block vertically, but keep a minimum top margin
    block_top = max(top_margin, (available_space - total_block_h) // 2)

    header_top = block_top
    card_top = header_top + header_h + header_card_gap
    card_bottom = card_top + card_h

    # ============================================================
    # PASS 3: Draw everything
    # ============================================================
    bg = _ig_build_cream_bg(cw, ch)
    draw = ImageDraw.Draw(bg)

    # -- Coral header bar --
    draw.rectangle([(0, header_top), (cw, header_top + header_h)], fill=colors["primary"])

    # Title text inside header bar (vertically centered within bar)
    title_line_h = int(title_font_size * LINE_HEIGHT_RATIO)
    title_block_h = title_line_h * len(title_lines)
    title_y = header_top + (header_h - title_block_h) // 2

    draw_centered_text_block(
        draw, title_lines, title_font, title_font_size,
        center_x, title_y,
        fill=COLOR_WHITE,
        shadow=False,
    )

    # -- White content card with drop shadow --
    # Card shadow
    shadow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow_layer)
    sd.rounded_rectangle(
        (card_left + 3, card_top + 4, card_right + 3, card_bottom + 4),
        radius=card_radius, fill=(0, 0, 0, 20),
    )
    bg = Image.alpha_composite(bg, shadow_layer)
    draw = ImageDraw.Draw(bg)

    # Card body
    draw.rounded_rectangle(
        (card_left, card_top, card_right, card_bottom),
        radius=card_radius, fill=colors["card_bg"],
    )

    # -- Content inside card --
    content_x = card_left + card_inner_pad_side
    content_y = card_top + card_inner_pad

    # Highlight number with yellow accent box
    if highlight_number:
        num_font_size = IG_FONTS["accent_number"]  # 96px
        num_font = load_font(bold=True, size=num_font_size)
        ntw, _ = measure_text(highlight_number, num_font)
        nx = center_x - ntw // 2

        # Yellow highlight box behind the number (30% opacity)
        accent_yellow = colors["accent"]  # #FFD93D
        hl_pad_x = 30
        hl_pad_y = 10
        hl_box = (
            nx - hl_pad_x,
            content_y - hl_pad_y,
            nx + ntw + hl_pad_x,
            content_y + int(num_font_size * 1.1) + hl_pad_y,
        )
        hl_overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        hl_draw = ImageDraw.Draw(hl_overlay)
        hl_draw.rounded_rectangle(
            hl_box, radius=12,
            fill=(*accent_yellow[:3], 77),  # ~30% opacity (77/255)
        )
        bg = Image.alpha_composite(bg, hl_overlay)
        draw = ImageDraw.Draw(bg)

        draw.text((nx, content_y), highlight_number,
                  fill=colors["primary"], font=num_font)
        content_y += int(num_font_size * 1.3)

        if highlight_label:
            label_font = load_font(bold=False, size=IG_FONTS["caption"])
            ltw, _ = measure_text(highlight_label, label_font)
            lx = center_x - ltw // 2
            draw.text((lx, content_y), highlight_label,
                      fill=colors["text_secondary"], font=label_font)
            content_y += 50
        else:
            content_y += 30

    # -- Draw body text using pre-measured paragraph data --
    for pd in para_data:
        if pd["type"] == "blank":
            content_y += pd["height"]
            continue

        if pd["type"] == "bullet":
            bullet_indent = 40
            text_start_x = content_x + bullet_indent

            # Coral bullet marker
            marker_y = content_y + body_font_size // 2
            draw.ellipse(
                (content_x + 8, marker_y - 6, content_x + 20, marker_y + 6),
                fill=colors["primary"],
            )

            for line in pd["lines"]:
                draw.text((text_start_x, content_y), line,
                          fill=colors["text_primary"], font=body_font)
                content_y += line_h
            content_y += 10
        else:
            for line in pd["lines"]:
                draw.text((content_x, content_y), line,
                          fill=colors["text_primary"], font=body_font)
                content_y += line_h
            content_y += 8

    # -- Progress dots --
    _draw_progress_dots(draw, slide_num, total_slides, cw, ch)

    return bg.convert("RGB")


def generate_ig_cta_slide(
    cta_type: str = "soft",
    summary_points: Optional[list[str]] = None,
    total_slides: int = DEFAULT_SLIDE_COUNT,
) -> Image.Image:
    """Instagram CTA slide (last slide).

    Layout:
    - Background: Gradient from cream to light coral
    - "まとめ" header (48px, bold)
    - 2-3 bullet points summarizing the carousel (36px)
    - Divider line
    - CTA text for LINE or profile check (40px, bold)
    - Brand footer (32px, coral)
    - "保存・シェアお願いします！" (28px, gray)
    """
    cw, ch = IG_CANVAS_W, IG_CANVAS_H
    colors = INSTAGRAM_COLORS
    center_x = cw // 2

    # -- Background: cream-to-light-coral gradient --
    cream = colors["background"]
    light_coral = (255, 200, 190)
    bg = create_gradient(cw, ch, cream, light_coral, direction="vertical")
    draw = ImageDraw.Draw(bg)

    current_y = 60

    # -- "まとめ" header --
    header_font = load_font(bold=True, size=48)
    header_text = "まとめ"
    htw, _ = measure_text(header_text, header_font)
    draw.text((center_x - htw // 2, current_y), header_text,
              fill=colors["text_primary"], font=header_font)
    current_y += 80

    # -- Summary bullet points --
    if summary_points is None:
        summary_points = [
            "手数料10%で病院の負担を軽減",
            "あなたの転職がもっとスムーズに",
            "神奈川県で看護師の味方",
        ]

    bullet_font = load_font(bold=False, size=36)
    bullet_coral = colors["primary"]
    bullet_line_h = int(36 * LINE_HEIGHT_RATIO)

    for point in summary_points[:3]:
        dot_y = current_y + 18
        draw.ellipse((60, dot_y - 6, 72, dot_y + 6), fill=bullet_coral)

        lines = wrap_text_jp(point, bullet_font, cw - 160)
        for line in lines:
            if current_y > ch - 200:  # Stop if running out of space
                break
            draw.text((90, current_y), line,
                      fill=colors["text_primary"], font=bullet_font)
            current_y += bullet_line_h
        current_y += 12

    current_y += 10

    # -- Divider line --
    ig_max_y = ch - 100  # Safe bottom for Instagram content
    divider_margin = 80
    if current_y < ig_max_y - 160:
        draw.line(
            [(divider_margin, current_y), (cw - divider_margin, current_y)],
            fill=(*colors["primary"][:3], 100), width=2,
        )
        current_y += 40

    # -- CTA text (with wrapping) --
    cta_font = load_font(bold=True, size=40)
    cta_line_h = int(40 * LINE_HEIGHT_RATIO)
    cta_main = CTA_TEMPLATE.get("cta_text", "30秒AI診断であなたの求人がわかる")
    cta_sub = CTA_TEMPLATE.get("cta_sub", "プロフィールのリンクから →")

    for cta_part in [cta_main, cta_sub]:
        cta_lines = wrap_text_jp(cta_part, cta_font, cw - 80)
        for line in cta_lines:
            if current_y > ig_max_y - 80:
                break
            ltw, _ = measure_text(line, cta_font)
            draw.text((center_x - ltw // 2, current_y), line,
                      fill=colors["text_primary"], font=cta_font)
            current_y += cta_line_h

    current_y += 20

    # -- Brand footer (clamped) --
    brand_font = load_font(bold=True, size=32)
    brand_text = CTA_TEMPLATE.get("brand", "シン・AI転職") + " — " + CTA_TEMPLATE.get("tagline", "早い × 簡単 × 24時間")
    brand_lines = wrap_text_jp(brand_text, brand_font, cw - 80)
    for bl in brand_lines:
        if current_y > ig_max_y - 40:
            break
        blw, _ = measure_text(bl, brand_font)
        draw.text((center_x - blw // 2, current_y), bl,
                  fill=colors["primary"], font=brand_font)
        current_y += int(32 * LINE_HEIGHT_RATIO)

    # -- Save/share request (only if space remains) --
    current_y = min(current_y + 10, ig_max_y - 30)
    share_font = load_font(bold=False, size=28)
    share_text = "保存・シェアお願いします！"
    stw, _ = measure_text(share_text, share_font)
    if current_y < ig_max_y:
        draw.text((center_x - stw // 2, current_y), share_text,
                  fill=colors["text_secondary"], font=share_font)

    # -- Progress dots --
    _draw_progress_dots(draw, total_slides, total_slides, cw, ch)

    return bg.convert("RGB")


# ===========================================================================
# Slide generators v3.0
# ===========================================================================

def _get_platform_layout(platform: str) -> dict:
    """Return canvas dimensions and safe zones for a given platform."""
    canvas_w, canvas_h = PLATFORM_SIZES.get(platform, (CANVAS_W, CANVAS_H))
    safe = SAFE_ZONES.get(platform, SAFE_ZONES["tiktok"])
    content_w = canvas_w - safe["left"] - safe["right"]
    content_h = canvas_h - safe["top"] - safe["bottom"]
    return {
        "canvas_w": canvas_w,
        "canvas_h": canvas_h,
        "safe_top": safe["top"],
        "safe_bottom": safe["bottom"],
        "safe_left": safe["left"],
        "safe_right": safe["right"],
        "content_w": content_w,
        "content_h": content_h,
        "content_x": safe["left"],
        "content_y": safe["top"],
    }


def generate_slide_hook(
    hook_text: str,
    theme: dict,
    total_slides: int = DEFAULT_SLIDE_COUNT,
    platform: str = "tiktok",
) -> Image.Image:
    """
    Slide 1 - HOOK: Massive text, center of screen.
    Goal: 3-second stop-scroll. 10 chars max, 120pt+ font.
    Dark bg with accent glow behind text.
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top = layout["safe_top"]
    s_bottom = layout["safe_bottom"]
    s_left = layout["safe_left"]
    c_w = layout["content_w"]
    c_h = layout["content_h"]

    bg = _build_dark_bg(theme, canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)
    accent = theme["accent"]
    center_x = s_left + c_w // 2  # Center within safe zone, not canvas

    # -- Compute font size for hook --
    # For Instagram, center text vertically (no TikTok bottom bar offset)
    if platform == "instagram":
        hook_zone_top = s_top + 100
        hook_zone_height = int(c_h * 0.55)
    else:
        hook_zone_top = s_top + 250
        hook_zone_height = int(c_h * 0.45)
    max_text_width = c_w - 80  # 40px margin each side within safe zone

    # Enforce hook character limit (MAX_HOOK_CHARS is advisory from AI, enforce here)
    if len(hook_text) > 25:
        hook_text = hook_text[:25]

    best_font_size = 60
    best_lines = [hook_text]
    # Account for shadow offset in zone height
    effective_zone_height = hook_zone_height - 10  # shadow_offset + padding
    # Limit max font for long hooks to prevent too many lines
    max_font = 140 if len(hook_text) <= 10 else (110 if len(hook_text) <= 15 else 90)
    for size in range(max_font, 56, -2):
        font = load_font(bold=True, size=size)
        lines = wrap_text_jp(hook_text, font, max_text_width)
        block_h = text_block_height(lines, size)
        if block_h <= effective_zone_height and len(lines) <= 4:
            best_font_size = size
            best_lines = lines
            break
    else:
        font = load_font(bold=True, size=60)
        best_font_size = 60
        best_lines = wrap_text_jp(hook_text, font, max_text_width)
        # Force truncate to 2 lines if still too tall
        if text_block_height(best_lines, 60) > effective_zone_height:
            best_lines = best_lines[:2]

    font = load_font(bold=True, size=best_font_size)
    block_h = text_block_height(best_lines, best_font_size)

    # Center vertically in the hook zone, clamped to safe area
    text_y = hook_zone_top + (effective_zone_height - block_h) // 2
    # Ensure text doesn't extend below safe zone
    max_bottom = ch - s_bottom - 100  # 100px clearance for swipe hint
    if text_y + block_h > max_bottom:
        text_y = max_bottom - block_h

    # -- Accent glow behind text --
    glow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    glow_cy = text_y + block_h // 2
    for r in range(400, 0, -6):
        a = max(1, int(18 * (1 - r / 400)))
        gd.ellipse((center_x - r, glow_cy - r, center_x + r, glow_cy + r),
                    fill=(*accent[:3], a))
    bg = Image.alpha_composite(bg, glow_layer)
    draw = ImageDraw.Draw(bg)

    # -- Draw hook text --
    draw_centered_text_block(
        draw, best_lines, font, best_font_size,
        center_x, text_y,
        fill=COLOR_WHITE,
        shadow=True,
        shadow_offset=5,
        shadow_color=(0, 0, 0, 160),
    )

    # -- Accent underline --
    underline_y = text_y + block_h + 50
    underline_w = min(400, c_w - 100)
    underline_x = center_x - underline_w // 2
    draw.rounded_rectangle(
        (underline_x, underline_y, underline_x + underline_w, underline_y + 6),
        radius=3, fill=(*accent[:3], 180),
    )

    # -- Swipe hint --
    hint_font = load_font(bold=True, size=30)
    hint_text = ">>> スワイプ"
    tw, _ = measure_text(hint_text, hint_font)
    hint_x = center_x - tw // 2
    hint_y = ch - s_bottom - 90
    draw.text((hint_x, hint_y), hint_text, fill=(*accent[:3], 140), font=hint_font)

    # -- Indicators --
    _draw_slide_indicator(draw, 1, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _truncate_line_with_ellipsis(line: str, font: ImageFont.FreeTypeFont, max_width: int) -> str:
    """Truncate a line and append ellipsis, ensuring it fits within max_width."""
    ellipsis = "..."
    if not line:
        return ellipsis
    # Binary search for the longest prefix that fits with ellipsis
    for end in range(len(line), 0, -1):
        candidate = line[:end] + ellipsis
        bbox = font.getbbox(candidate)
        if (bbox[2] - bbox[0]) <= max_width:
            return candidate
    return ellipsis


def generate_slide_content(
    slide_num: int,
    title: str,
    body: str,
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
    dark_theme: bool = True,
    theme: dict = None,
    total_slides: int = DEFAULT_SLIDE_COUNT,
    platform: str = "tiktok",
) -> Image.Image:
    """
    Slides 2-7 - CONTENT: Card-based layout.
    Title at top, body in rounded card with left accent bar.
    Alternating dark/light backgrounds.
    Renders natively at the correct platform dimensions.
    """
    if theme is None:
        theme = DEFAULT_THEME
    accent = theme["accent"]

    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top = layout["safe_top"]
    s_bottom = layout["safe_bottom"]
    s_left = layout["safe_left"]
    s_right = layout["safe_right"]
    c_w = layout["content_w"]
    c_h = layout["content_h"]

    bg = _build_dark_bg(theme, canvas_w=cw, canvas_h=ch) if dark_theme else _build_light_bg(theme, canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)
    light_bg = not dark_theme
    center_x = cw // 2
    max_text_width = c_w - 80

    # ============================================================
    # PASS 1: Pre-calculate total content height for vertical centering
    # ============================================================
    title_font_size = 52
    title_font = load_font(bold=True, size=title_font_size)
    title_lines = wrap_text_jp(title, title_font, max_text_width)
    title_block_h = len(title_lines) * int(title_font_size * 1.5) + 30  # + gap

    hl_block_h = 0
    if highlight_number:
        num_font_size = 96
        hl_block_h += int(num_font_size * 1.3)
        if highlight_label:
            hl_block_h += 55
        else:
            hl_block_h += 35

    # Pre-calculate card dimensions
    card_margin = 25
    card_x0 = s_left + card_margin
    card_x1 = cw - s_right - card_margin
    card_inner_pad = 35

    body_font_size = 48
    body_paragraphs = body.split("\n")

    # Adaptive font sizing using actual pixel measurement
    max_card_height = c_h - title_block_h - hl_block_h - 80  # leave margin
    card_text_max_w = card_x1 - card_x0 - card_inner_pad * 2 - 12

    def _calc_card_content_height(font_size: int) -> int:
        """Calculate exact card content height at a given font size."""
        test_font = load_font(bold=False, size=font_size)
        test_line_h = int(font_size * LINE_HEIGHT_RATIO)
        h = 0
        for para in body_paragraphs:
            para = para.strip()
            if not para:
                h += test_line_h // 2
                continue
            is_bullet = para.startswith(("\u30fb", "- ", "* "))
            if is_bullet:
                clean = para.lstrip("\u30fb- *").strip()
                _, block_h = _measure_text_block(clean, test_font, card_text_max_w - 60)
                lines = wrap_text_jp(clean, test_font, card_text_max_w - 60)
                h += test_line_h * len(lines) + 14
            else:
                lines = wrap_text_jp(para, test_font, card_text_max_w)
                h += test_line_h * len(lines) + 10
        return h

    initial_content_h = _calc_card_content_height(body_font_size)
    initial_card_h = card_inner_pad * 2 + initial_content_h + 10

    if initial_card_h > max_card_height:
        for try_size in range(38, 26, -2):
            test_h = _calc_card_content_height(try_size)
            test_card_h = card_inner_pad * 2 + test_h + 10
            if test_card_h <= max_card_height:
                body_font_size = try_size
                break
        else:
            body_font_size = 28

    body_font = load_font(bold=False, size=body_font_size)
    line_h = int(body_font_size * LINE_HEIGHT_RATIO)

    # Exact card height calculation
    card_content_h = 0
    for para in body_paragraphs:
        para = para.strip()
        if not para:
            card_content_h += line_h // 2
            continue
        is_bullet = para.startswith(("\u30fb", "- ", "* "))
        if is_bullet:
            clean = para.lstrip("\u30fb- *").strip()
            lines = wrap_text_jp(clean, body_font, card_x1 - card_x0 - card_inner_pad * 2 - 60)
            card_content_h += line_h * len(lines) + 14
        else:
            lines = wrap_text_jp(para, body_font, card_x1 - card_x0 - card_inner_pad * 2)
            card_content_h += line_h * len(lines) + 10

    actual_card_h = card_inner_pad * 2 + card_content_h + 10

    # Expand card to fill most of available space (like chat_bubble)
    non_card_h = title_block_h + hl_block_h + 60
    min_card_h = c_h - non_card_h - 120
    actual_card_h = max(actual_card_h, min_card_h)
    # Hard cap: card must not push total content beyond safe zone
    max_total = c_h - 60  # leave 60px margin within safe zone
    actual_card_h = min(actual_card_h, max_total - title_block_h - hl_block_h)

    # Total content height
    total_content_h = title_block_h + hl_block_h + actual_card_h

    # ============================================================
    # PASS 2: Draw everything, vertically centered
    # ============================================================
    # Center the entire content block in the safe area
    start_y = s_top + max(30, (c_h - total_content_h) // 2)
    current_y = start_y

    # -- Section title --
    title_color = COLOR_WHITE if dark_theme else theme["text_on_light"]

    # Accent dot
    dot_y = current_y + title_font_size // 2
    draw.ellipse(
        (s_left + 20, dot_y - 10, s_left + 40, dot_y + 10),
        fill=(*accent[:3], 255),
    )

    # Title text
    title_x = s_left + 55
    for tl in title_lines:
        if dark_theme:
            draw_text_shadow(draw, title_x, current_y, tl, title_font,
                             fill=title_color, shadow_offset=2, outline_width=1)
        else:
            draw.text((title_x, current_y), tl, fill=title_color, font=title_font)
        current_y += int(title_font_size * 1.5)

    current_y += 25

    # -- Highlight number --
    if highlight_number:
        num_font_size = 96
        num_font = load_font(bold=True, size=num_font_size)
        tw, _ = measure_text(highlight_number, num_font)
        nx = center_x - tw // 2

        if dark_theme:
            draw_text_shadow(draw, nx, current_y, highlight_number, num_font,
                             fill=(*accent[:3], 255), shadow_offset=4, outline_width=2)
        else:
            draw.text((nx, current_y), highlight_number, fill=(*accent[:3], 255), font=num_font)

        current_y += int(num_font_size * 1.3)

        if highlight_label:
            label_font = load_font(bold=False, size=28)
            tw2, _ = measure_text(highlight_label, label_font)
            lx = center_x - tw2 // 2
            label_color = theme["text_secondary"] if dark_theme else (120, 120, 120)
            draw.text((lx, current_y), highlight_label, fill=label_color, font=label_font)
            current_y += 55
        else:
            current_y += 35

    # -- Body text in card --
    card_top = current_y
    max_body_y = ch - s_bottom - 70
    card_bottom = min(card_top + actual_card_h, max_body_y)

    # -- Draw card (multi-layer shadow for depth) --
    if dark_theme:
        shadow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle(
            (card_x0 + 8, card_top + 10, card_x1 + 8, card_bottom + 10),
            radius=28, fill=(0, 0, 0, 25),
        )
        sd.rounded_rectangle(
            (card_x0 + 4, card_top + 5, card_x1 + 4, card_bottom + 5),
            radius=28, fill=(0, 0, 0, 35),
        )
        bg = Image.alpha_composite(bg, shadow_layer)
        draw = ImageDraw.Draw(bg)

        card_fill = (255, 255, 255, 20)
    else:
        shadow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle(
            (card_x0 + 5, card_top + 6, card_x1 + 5, card_bottom + 6),
            radius=28, fill=(0, 0, 0, 15),
        )
        bg = Image.alpha_composite(bg, shadow_layer)
        draw = ImageDraw.Draw(bg)

        card_fill = (255, 255, 255, 240)

    # Card body
    draw.rounded_rectangle(
        (card_x0, card_top, card_x1, card_bottom),
        radius=28, fill=card_fill,
    )

    # Card border
    if dark_theme:
        draw.rounded_rectangle(
            (card_x0, card_top, card_x1, card_bottom),
            radius=28, fill=None, outline=(*accent[:3], 35), width=1,
        )

    # Left accent bar
    draw.rounded_rectangle(
        (card_x0, card_top + 28, card_x0 + 7, card_bottom - 28),
        radius=3, fill=(*accent[:3], 200),
    )

    # -- Draw body text, vertically centered within card --
    # Center text block within the expanded card
    inner_card_h = card_bottom - card_top - card_inner_pad * 2
    text_offset_y = max(0, (inner_card_h - card_content_h) // 2)
    current_y = card_top + card_inner_pad + text_offset_y
    body_left = card_x0 + card_inner_pad + 12
    body_max_w = card_x1 - card_x0 - card_inner_pad * 2 - 12
    body_color = COLOR_WHITE if dark_theme else theme["text_on_light"]
    truncated = False

    for para in body_paragraphs:
        para = para.strip()
        if not para:
            current_y += line_h // 2
            continue
        if truncated:
            break
        if current_y >= max_body_y - line_h:
            break

        is_bullet = para.startswith(("\u30fb", "- ", "* "))
        if is_bullet:
            clean_text = para.lstrip("\u30fb- *").strip()
            text_start_x = body_left + 50
            text_max_w = body_max_w - 60

            lines = wrap_text_jp(clean_text, body_font, text_max_w)

            # Bullet marker
            marker_x = body_left + 10
            marker_y = current_y + body_font_size // 2
            draw.ellipse(
                (marker_x, marker_y - 7, marker_x + 14, marker_y + 7),
                fill=(*accent[:3], 220),
            )

            for li, line in enumerate(lines):
                if current_y >= max_body_y - line_h:
                    # Truncate: show ellipsis on this line
                    trunc_line = _truncate_line_with_ellipsis(line, body_font, text_max_w)
                    if dark_theme:
                        draw_text_shadow(draw, text_start_x, current_y, trunc_line, body_font,
                                         fill=body_color, shadow_offset=1, outline_width=1)
                    else:
                        draw.text((text_start_x, current_y), trunc_line, fill=body_color, font=body_font)
                    truncated = True
                    break
                if dark_theme:
                    draw_text_shadow(draw, text_start_x, current_y, line, body_font,
                                     fill=body_color, shadow_offset=1, outline_width=1)
                else:
                    draw.text((text_start_x, current_y), line, fill=body_color, font=body_font)
                current_y += line_h
            current_y += 14
        else:
            lines = wrap_text_jp(para, body_font, body_max_w)
            for li, line in enumerate(lines):
                if current_y >= max_body_y - line_h:
                    # Truncate: show ellipsis on this line
                    trunc_line = _truncate_line_with_ellipsis(line, body_font, body_max_w)
                    if dark_theme:
                        draw_text_shadow(draw, body_left, current_y, trunc_line, body_font,
                                         fill=body_color, shadow_offset=1, outline_width=1)
                    else:
                        draw.text((body_left, current_y), trunc_line, fill=body_color, font=body_font)
                    truncated = True
                    break
                if dark_theme:
                    draw_text_shadow(draw, body_left, current_y, line, body_font,
                                     fill=body_color, shadow_offset=1, outline_width=1)
                else:
                    draw.text((body_left, current_y), line, fill=body_color, font=body_font)
                current_y += line_h
            current_y += 10

    # -- Indicators --
    _draw_slide_indicator(draw, slide_num, total_slides, light_bg=light_bg, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=light_bg, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def generate_slide_cta(
    cta_type: str = "soft",
    theme: dict = None,
    total_slides: int = DEFAULT_SLIDE_COUNT,
    platform: str = "tiktok",
) -> Image.Image:
    """
    Final slide - CTA: Brand gradient background.
    Large CTA button with pulse-ring decoration.
    Soft: save/follow. Hard: LINE invitation.
    """
    if theme is None:
        theme = DEFAULT_THEME

    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top = layout["safe_top"]
    s_bottom = layout["safe_bottom"]
    s_left = layout["safe_left"]
    s_right = layout["safe_right"]

    bg = _build_brand_gradient_bg(canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)
    center_x = cw // 2

    # -- Brand logo --
    logo_font_size = 64
    logo_font = load_font(bold=True, size=logo_font_size)
    logo_text = "神奈川ナース転職"
    tw, _ = measure_text(logo_text, logo_font)
    logo_x = center_x - tw // 2

    # Pre-calculate total CTA content height for vertical centering
    _cta_content_h = logo_font_size + 18 + 28 + 65 + 3  # logo + gap + tag + gap + sep
    if cta_type == "hard":
        _cta_content_h += 60 + 72 + 80 + 106 + 45 + 28 + 70 + 30  # badge+gap+btn+gap+sub+gap+trust
    else:
        _cta_content_h += 80 + 102 + 60 + 36 + 65 + 28 + 70 + 30  # save+gap+follow+gap+prof+gap+trust
    _available_h = ch - s_top - s_bottom - 80
    _cta_offset = max(40, (_available_h - _cta_content_h) // 2)
    logo_y = s_top + _cta_offset

    draw_text_shadow(
        draw, logo_x, logo_y, logo_text, logo_font,
        fill=COLOR_WHITE, shadow_offset=3,
    )

    # -- English tagline --
    tag_font = load_font(bold=False, size=28)
    tag_text = CTA_TEMPLATE.get("brand", "シン・AI転職") + " — " + CTA_TEMPLATE.get("tagline", "早い × 簡単 × 24時間")
    tw, th = measure_text(tag_text, tag_font)
    tag_max_w = cw - s_left - s_right - 20
    if tw > tag_max_w:
        tag_font = load_font(bold=False, size=tag_font.size - 4)
        tw, th = measure_text(tag_text, tag_font)
    tag_x = center_x - tw // 2
    tag_y = logo_y + logo_font_size + 18
    draw.text((tag_x, tag_y), tag_text, fill=(*COLOR_WHITE[:3], 150), font=tag_font)

    # -- Separator line --
    sep_y = tag_y + 65
    sep_w = 180
    draw.rounded_rectangle(
        (center_x - sep_w // 2, sep_y, center_x + sep_w // 2, sep_y + 3),
        radius=2, fill=(*COLOR_WHITE[:3], 70),
    )

    if cta_type == "hard":
        # === Hard CTA: LINE invitation ===

        # Badge: 手数料10%
        badge_y = sep_y + 60
        badge_font = load_font(bold=True, size=32)
        badge_text = "紹介手数料 業界最安10%"
        btw, bth = measure_text(badge_text, badge_font)
        badge_pad_x = 45
        badge_pad_y = 20
        badge_w = btw + badge_pad_x * 2
        badge_h = bth + badge_pad_y * 2
        badge_x = center_x - badge_w // 2

        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=badge_h // 2,
            fill=(*COLOR_WHITE[:3], 35),
            outline=(*COLOR_WHITE[:3], 160), width=2,
        )
        draw_text_shadow(
            draw, badge_x + badge_pad_x, badge_y + badge_pad_y,
            badge_text, badge_font, fill=COLOR_WHITE,
            shadow_offset=1, outline_width=1,
        )

        # CTA Button
        btn_y = badge_y + badge_h + 80
        btn_font = load_font(bold=True, size=42)
        btn_text = CTA_TEMPLATE.get("cta_text", "30秒AI診断であなたの求人がわかる")
        btn_pad_x = 70
        btn_pad_y = 32
        max_btn_w = cw - s_left - s_right - 40  # Don't exceed safe zone
        # If btn_text is too wide, reduce font size
        btw2 = measure_text(btn_text, btn_font)[0]
        while btw2 > max_btn_w - btn_pad_x * 2 and btn_font.size > 28:
            btn_font = load_font(bold=True, size=btn_font.size - 2)
            btw2 = measure_text(btn_text, btn_font)[0]
        btw2, bth2 = measure_text(btn_text, btn_font)
        btn_w = btw2 + btn_pad_x * 2
        if btn_w > max_btn_w:
            btn_w = max_btn_w
        btn_h = bth2 + btn_pad_y * 2
        btn_x = center_x - btn_w // 2

        # Pulse rings behind button
        pulse_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pulse_layer)
        btn_cx = center_x
        btn_cy = btn_y + btn_h // 2
        for ring_i in range(4):
            ring_r = btn_w // 2 + 20 + ring_i * 25
            ring_a = max(5, 30 - ring_i * 8)
            pd.ellipse(
                (btn_cx - ring_r, btn_cy - ring_r, btn_cx + ring_r, btn_cy + ring_r),
                outline=(255, 255, 255, ring_a), width=2,
            )
        bg = Image.alpha_composite(bg, pulse_layer)
        draw = ImageDraw.Draw(bg)

        # Button shadow
        draw.rounded_rectangle(
            (btn_x + 4, btn_y + 5, btn_x + btn_w + 4, btn_y + btn_h + 5),
            radius=btn_h // 2, fill=(0, 0, 0, 30),
        )
        # Button
        draw.rounded_rectangle(
            (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
            radius=btn_h // 2, fill=COLOR_WHITE,
        )
        draw.text(
            (btn_x + btn_pad_x, btn_y + btn_pad_y),
            btn_text, fill=COLOR_BRAND_BLUE, font=btn_font,
        )

        # Sub text
        sub_y = btn_y + btn_h + 45
        sub_font = load_font(bold=False, size=28)
        sub_text = CTA_TEMPLATE.get("cta_sub", "プロフィールのリンクから →")
        tw, _ = measure_text(sub_text, sub_font)
        draw.text((center_x - tw // 2, sub_y), sub_text, fill=(*COLOR_WHITE[:3], 170), font=sub_font)

        # Trust indicators
        trust_y = sub_y + 70
        _draw_trust_badges(draw, center_x, trust_y)

    else:
        # === Soft CTA: Save + Follow ===

        # "保存してね" button
        save_y = sep_y + 80
        save_font = load_font(bold=True, size=46)
        save_text = "保存してね"
        stw, sth = measure_text(save_text, save_font)
        save_pad_x = 60
        save_pad_y = 28
        save_w = stw + save_pad_x * 2
        save_h = sth + save_pad_y * 2
        save_x = center_x - save_w // 2

        # Pulse rings
        pulse_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pulse_layer)
        save_cx = center_x
        save_cy = save_y + save_h // 2
        for ring_i in range(3):
            ring_r = save_w // 2 + 15 + ring_i * 22
            ring_a = max(5, 25 - ring_i * 8)
            pd.ellipse(
                (save_cx - ring_r, save_cy - ring_r, save_cx + ring_r, save_cy + ring_r),
                outline=(255, 255, 255, ring_a), width=2,
            )
        bg = Image.alpha_composite(bg, pulse_layer)
        draw = ImageDraw.Draw(bg)

        # Button shadow
        draw.rounded_rectangle(
            (save_x + 4, save_y + 5, save_x + save_w + 4, save_y + save_h + 5),
            radius=save_h // 2, fill=(0, 0, 0, 25),
        )
        # Button
        draw.rounded_rectangle(
            (save_x, save_y, save_x + save_w, save_y + save_h),
            radius=save_h // 2, fill=COLOR_WHITE,
        )
        draw.text(
            (save_x + save_pad_x, save_y + save_pad_y),
            save_text, fill=COLOR_BRAND_BLUE, font=save_font,
        )

        # Follow text (clamped to safe zone)
        follow_y = min(save_y + save_h + 60, ch - s_bottom - 120)
        follow_font = load_font(bold=True, size=36)
        follow_text = "フォローで最新情報をチェック"
        follow_lines = wrap_text_jp(follow_text, follow_font, cw - 120)
        for fl in follow_lines:
            if follow_y > ch - s_bottom - 40:
                break
            tw, _ = measure_text(fl, follow_font)
            draw.text((center_x - tw // 2, follow_y), fl, fill=COLOR_WHITE, font=follow_font)
            follow_y += int(36 * LINE_HEIGHT_RATIO)

        # Subtitle (clamped to safe zone)
        prof_y = min(follow_y + 20, ch - s_bottom - 50)
        prof_font = load_font(bold=False, size=28)
        prof_text = "神奈川県の看護師転職"
        ptw, _ = measure_text(prof_text, prof_font)
        if prof_y < ch - s_bottom - 30:
            draw.text((center_x - ptw // 2, prof_y), prof_text, fill=(*COLOR_WHITE[:3], 150), font=prof_font)

        # Trust indicators
        trust_y = prof_y + 70
        _draw_trust_badges(draw, center_x, trust_y)

    _draw_slide_indicator(draw, total_slides, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _draw_trust_badges(draw: ImageDraw.ImageDraw, center_x: int, y: int):
    """Draw trust indicator badges at the bottom."""
    badge_font = load_font(bold=False, size=24)
    check_font = load_font(bold=True, size=24)
    items = ["有料職業紹介許可", "完全無料", "LINEで簡単相談"]

    check_text = "+"
    check_w, _ = measure_text(check_text, check_font)
    gap = 28
    total_w = 0
    item_widths = []
    for item in items:
        itw, _ = measure_text(item, badge_font)
        item_widths.append(itw)
        total_w += check_w + 8 + itw

    total_w += gap * (len(items) - 1)
    start_x = center_x - total_w // 2

    cx_pos = start_x
    for i, item in enumerate(items):
        draw.text((cx_pos, y), check_text, fill=(100, 255, 210), font=check_font)
        cx_pos += check_w + 8
        draw.text((cx_pos, y + 1), item, fill=(*COLOR_WHITE[:3], 190), font=badge_font)
        cx_pos += item_widths[i] + gap


# ===========================================================================
# v4.0 Category-specific slide templates
# ===========================================================================

def _v4_chat_bubble_content(
    slide_num: int,
    title: str,
    body: str,
    theme: dict,
    total_slides: int,
    platform: str,
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
) -> Image.Image:
    """あるある category: Chat bubble layout v2.

    Full text in a large speech bubble, vertically centered.
    Title as short header, body as main bubble content.
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top, s_bottom = layout["safe_top"], layout["safe_bottom"]
    s_left, s_right = layout["safe_left"], layout["safe_right"]
    c_w = layout["content_w"]
    c_h = layout["content_h"]
    center_x = cw // 2

    # Background: warm gradient
    bg = create_gradient(cw, ch, theme["bg_dark_top"], theme["bg_dark_bottom"], direction="diagonal")
    bg = _draw_diagonal_stripes(bg, theme, alpha=4)

    draw = ImageDraw.Draw(bg)

    # Combine title + body into full text for the bubble
    # Avoid duplication: if body starts with title text, just use body
    full_text = body if body else title
    if not full_text:
        full_text = title
    if title and body and body.startswith(title.rstrip("、。？！…")):
        # body already contains the title content, skip title header
        title = ""

    # --- Layout: fill the canvas, not shrink-wrap ---
    # Title block (only if short and distinct from body)
    show_title = bool(title and body and len(title) <= 20)
    title_font_size = 56
    title_font = load_font(bold=True, size=title_font_size, rounded=False)
    title_lines = wrap_text_jp(title, title_font, c_w - 60) if show_title else []
    title_line_h = int(title_font_size * 1.5)
    title_block_h = len(title_lines) * title_line_h + (40 if title_lines else 0)

    # Highlight block
    hl_block_h = 0
    if highlight_number:
        hl_block_h = int(120 * 1.3) + (65 if highlight_label else 45)

    # Bubble block - use large font, expand bubble to fill space
    bubble_pad = 60
    max_bubble_w = c_w - 40
    bubble_inner_w = max_bubble_w - bubble_pad * 2

    # Start with large font size (80px), shrink only if needed
    # Try largest size first for maximum readability on mobile
    bubble_font_size = 80
    bubble_font = load_font(bold=False, size=bubble_font_size, rounded=True)
    bubble_line_h = int(bubble_font_size * 1.55)
    wrapped_lines = wrap_text_jp(full_text, bubble_font, bubble_inner_w)
    bubble_text_h = len(wrapped_lines) * bubble_line_h

    # The bubble should fill most of the content height (minus title/highlight)
    non_bubble_h = title_block_h + hl_block_h + 60  # 60px for gaps
    min_bubble_h = c_h - non_bubble_h - 120  # Leave only 120px total margin
    bubble_h = max(bubble_text_h + bubble_pad * 2 + 10, min_bubble_h)

    # If bubble would be too tall, shrink font (min 42px for readability)
    max_bubble_h = c_h - title_block_h - hl_block_h - 80
    if bubble_h > max_bubble_h:
        bubble_h = max_bubble_h
        for try_size in range(72, 40, -2):
            bubble_font = load_font(bold=False, size=try_size, rounded=True)
            bubble_line_h = int(try_size * 1.55)
            wrapped_lines = wrap_text_jp(full_text, bubble_font, bubble_inner_w)
            bubble_text_h = len(wrapped_lines) * bubble_line_h
            if bubble_text_h + bubble_pad * 2 + 10 <= max_bubble_h:
                bubble_font_size = try_size
                break

    total_content_h = title_block_h + hl_block_h + bubble_h

    # --- Draw: center the whole block vertically in safe area ---
    available_space = c_h - total_content_h
    start_y = s_top + max(30, available_space // 2)
    current_y = start_y

    # Title (short header above bubble)
    if title_lines:
        for tl in title_lines:
            tw, _ = measure_text(tl, title_font)
            draw_text_shadow(draw, center_x - tw // 2, current_y, tl, title_font,
                             fill=COLOR_WHITE, shadow_offset=2, outline_width=1)
            current_y += title_line_h
        current_y += 30

    # Highlight number
    if highlight_number:
        num_font = load_font(bold=True, size=120)
        tw, _ = measure_text(highlight_number, num_font)
        draw_text_shadow(draw, center_x - tw // 2, current_y, highlight_number, num_font,
                         fill=(*theme["accent_light"][:3], 255), shadow_offset=4, outline_width=2)
        current_y += int(120 * 1.3)
        if highlight_label:
            label_font = load_font(bold=False, size=34)
            tw2, _ = measure_text(highlight_label, label_font)
            draw.text((center_x - tw2 // 2, current_y), highlight_label,
                      fill=theme["text_secondary"], font=label_font)
            current_y += 65
        else:
            current_y += 45

    # Main speech bubble - large, left-aligned, expanded to fill space
    bx = s_left + 30
    bg = draw_speech_bubble(
        bg, bx, current_y, max_bubble_w, bubble_h,
        full_text, is_right=False,
        bg_color=(255, 255, 255, 230),
        text_color=theme["text_on_light"],
        font_size=bubble_font_size,
    )

    # Swipe indicator on first 3 content slides
    if slide_num <= 4:
        bg = draw_swipe_indicator(bg, cw, ch, s_bottom, style="arrow",
                                  color=(*theme["accent_light"][:3], 120))

    draw = ImageDraw.Draw(bg)
    _draw_slide_indicator(draw, slide_num, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _v4_infographic_content(
    slide_num: int,
    title: str,
    body: str,
    theme: dict,
    total_slides: int,
    platform: str,
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
    chart_data: Optional[list] = None,
) -> Image.Image:
    """給与・データ category: Infographic layout.

    Large number callouts, bar charts for salary comparisons,
    mint + gold color scheme.
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top, s_bottom = layout["safe_top"], layout["safe_bottom"]
    s_left, s_right = layout["safe_left"], layout["safe_right"]
    c_w = layout["content_w"]
    center_x = cw // 2

    # Background
    bg = _build_dark_bg(theme, canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)

    # --- Pre-calculate total content height for vertical centering ---
    _title_font_size = 52
    _title_font = load_font(bold=True, size=_title_font_size, rounded=True)
    _title_lines = wrap_text_jp(title, _title_font, c_w - 40)
    _title_h = int(_title_font_size * 1.5) * len(_title_lines) + 20
    _yen_h = 80
    _hl_h = 0
    if highlight_number:
        _hl_h = 110 + 40 + 20  # number + label + padding
    _chart_h = 0
    _card_h = 0
    if chart_data:
        _chart_h = min(350, 300) + 20
    elif body:
        # Estimate with 56px (will be dynamically sized during rendering)
        _body_font_size = 56
        _body_font = load_font(bold=False, size=_body_font_size, rounded=True)
        card_margin = 30
        card_x0 = s_left + card_margin
        card_x1 = cw - s_right - card_margin
        _card_inner_pad = 35
        _body_lines = wrap_text_jp(body, _body_font, card_x1 - card_x0 - _card_inner_pad * 2)
        _line_h = int(_body_font_size * LINE_HEIGHT_RATIO)
        _card_h = _card_inner_pad * 2 + _line_h * len(_body_lines) + 20

    total_content_h = _title_h + _yen_h + _hl_h + max(_chart_h, _card_h)
    available_h = ch - s_top - s_bottom - 80
    current_y = s_top + max(40, (available_h - total_content_h) // 2)

    # Title
    title_font = load_font(bold=True, size=52, rounded=True)
    title_lines = wrap_text_jp(title, title_font, c_w - 40)
    for tl in title_lines:
        tw, _ = measure_text(tl, title_font)
        draw_text_shadow(draw, center_x - tw // 2, current_y, tl, title_font,
                         fill=COLOR_WHITE, shadow_offset=2, outline_width=1)
        current_y += int(52 * 1.5)

    current_y += 20

    # Yen icon
    draw_icon_yen(draw, center_x, current_y + 30, size=36,
                  color=theme.get("gradient_b", (255, 200, 60)))
    current_y += 80

    # Highlight number (big data point)
    if highlight_number:
        current_y = draw_number_callout(
            draw, center_x, current_y, highlight_number,
            label=highlight_label or "",
            number_color=theme.get("gradient_b", (255, 200, 60)),
            number_size=110,
        )
        current_y += 20

    # Bar chart if data provided
    if chart_data and current_y < ch - s_bottom - 200:
        chart_h = min(350, ch - s_bottom - current_y - 80)
        bg = draw_bar_chart(
            bg, s_left + 30, current_y, c_w - 60, chart_h,
            data=chart_data,
            bar_color=theme["accent"],
            highlight_idx=len(chart_data) - 1,  # last is usually ours
            highlight_color=theme.get("gradient_b", (255, 200, 60)),
        )
        draw = ImageDraw.Draw(bg)
        current_y += chart_h + 20
    else:
        # Body text in card — larger font for mobile readability
        if body:
            card_margin = 30
            card_x0 = s_left + card_margin
            card_x1 = cw - s_right - card_margin
            card_inner_pad = 35
            # Dynamic font sizing: try large first, shrink to fit
            max_card_h = ch - s_bottom - 80 - current_y
            body_text_w = card_x1 - card_x0 - card_inner_pad * 2
            body_font_size = 56
            for try_size in range(56, 38, -2):
                test_font = load_font(bold=False, size=try_size, rounded=True)
                test_lines = wrap_text_jp(body, test_font, body_text_w)
                test_h = card_inner_pad * 2 + int(try_size * LINE_HEIGHT_RATIO) * len(test_lines)
                if test_h <= max_card_h:
                    body_font_size = try_size
                    break
            body_font = load_font(bold=False, size=body_font_size, rounded=True)
            body_lines = wrap_text_jp(body, body_font, body_text_w)
            line_h = int(body_font_size * LINE_HEIGHT_RATIO)
            card_h = card_inner_pad * 2 + line_h * len(body_lines)
            card_bottom = min(current_y + card_h, ch - s_bottom - 80)

            # Card
            draw.rounded_rectangle(
                (card_x0, current_y, card_x1, card_bottom),
                radius=20, fill=(255, 255, 255, 20),
            )
            draw.rounded_rectangle(
                (card_x0, current_y, card_x0 + 6, card_bottom),
                radius=3, fill=(*theme["accent"][:3], 180),
            )

            ty = current_y + card_inner_pad
            for bl in body_lines:
                if ty > card_bottom - line_h:
                    break
                draw_text_shadow(draw, card_x0 + card_inner_pad + 10, ty, bl, body_font,
                                 fill=COLOR_WHITE, shadow_offset=1, outline_width=1)
                ty += line_h

    # Swipe
    if slide_num <= 4:
        bg = draw_swipe_indicator(bg, cw, ch, s_bottom, style="arrow",
                                  color=(*theme["accent_light"][:3], 120))

    draw = ImageDraw.Draw(bg)
    _draw_slide_indicator(draw, slide_num, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _v4_step_content(
    slide_num: int,
    title: str,
    body: str,
    theme: dict,
    total_slides: int,
    platform: str,
    step_number: int = 0,
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
) -> Image.Image:
    """転職・キャリア category: Step-by-step layout.

    Numbered circles, progress bar, navy + blue color scheme.
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top, s_bottom = layout["safe_top"], layout["safe_bottom"]
    s_left, s_right = layout["safe_left"], layout["safe_right"]
    c_w = layout["content_w"]
    center_x = cw // 2

    # Background
    bg = _build_dark_bg(theme, canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)

    # --- Pre-calculate total content height for vertical centering ---
    _title_font_size = 44 if step_number > 0 else 48
    _title_font = load_font(bold=True, size=_title_font_size, rounded=True)
    _title_max_w = (c_w - 120) if step_number > 0 else (c_w - 40)
    _title_lines = wrap_text_jp(title, _title_font, _title_max_w)
    _title_h = int(_title_font_size * 1.5) * len(_title_lines) + 10
    _progress_h = 30 if step_number > 0 else 0
    _highlight_h = 0
    if highlight_number:
        _highlight_h = 96 + 40 + 20  # number_size + label + padding
    _card_h = 0
    _card_inner_pad = 35
    if body:
        _body_font = load_font(bold=False, size=42, rounded=True)
        card_margin = 25
        card_x0 = s_left + card_margin
        card_x1 = cw - s_right - card_margin
        _body_max_w = card_x1 - card_x0 - _card_inner_pad * 2
        _body_paragraphs = body.split("\n")
        _line_h = int(42 * LINE_HEIGHT_RATIO)
        _total_body_h = 0
        for _para in _body_paragraphs:
            _para = _para.strip()
            if not _para:
                _total_body_h += _line_h // 2
                continue
            _lines = wrap_text_jp(_para, _body_font, _body_max_w)
            _total_body_h += _line_h * len(_lines) + 10
        _card_h = _card_inner_pad * 2 + _total_body_h

    total_content_h = _title_h + _progress_h + _highlight_h + _card_h
    available_h = ch - s_top - s_bottom - 80  # 80 for watermark/indicator
    start_y = s_top + max(40, (available_h - total_content_h) // 2)

    current_y = start_y

    # Step number circle (if > 0)
    if step_number > 0:
        draw_step_number(draw, s_left + 65, current_y + 28, step_number,
                         size=56, bg_color=theme["accent"])
        # Title next to step number
        title_font = load_font(bold=True, size=44, rounded=True)
        title_lines = wrap_text_jp(title, title_font, c_w - 120)
        ty = current_y
        for tl in title_lines:
            draw_text_shadow(draw, s_left + 110, ty, tl, title_font,
                             fill=COLOR_WHITE, shadow_offset=2, outline_width=1)
            ty += int(44 * 1.5)
        current_y = ty + 10
    else:
        title_font = load_font(bold=True, size=48, rounded=True)
        title_lines = wrap_text_jp(title, title_font, c_w - 40)
        for tl in title_lines:
            tw, _ = measure_text(tl, title_font)
            draw_text_shadow(draw, center_x - tw // 2, current_y, tl, title_font,
                             fill=COLOR_WHITE, shadow_offset=2, outline_width=1)
            current_y += int(48 * 1.5)
        current_y += 10

    # Progress bar (shows progress through carousel)
    if step_number > 0:
        progress = step_number / max(total_slides - 2, 1)
        draw_progress_bar(draw, s_left + 30, current_y, c_w - 60,
                          progress, bar_height=10,
                          fill_color=theme["accent"])
        current_y += 30

    # Highlight number
    if highlight_number:
        current_y += 10
        current_y = draw_number_callout(
            draw, center_x, current_y, highlight_number,
            label=highlight_label or "",
            number_color=(*theme["accent_light"][:3], 255),
            number_size=96,
        )
        current_y += 10

    # Body in card
    if body:
        card_margin = 25
        card_x0 = s_left + card_margin
        card_x1 = cw - s_right - card_margin
        card_inner_pad = 35
        body_font = load_font(bold=False, size=42, rounded=True)
        body_max_w = card_x1 - card_x0 - card_inner_pad * 2

        body_paragraphs = body.split("\n")
        line_h = int(42 * LINE_HEIGHT_RATIO)
        total_body_h = 0
        for para in body_paragraphs:
            para = para.strip()
            if not para:
                total_body_h += line_h // 2
                continue
            lines = wrap_text_jp(para, body_font, body_max_w)
            total_body_h += line_h * len(lines) + 10

        card_h = card_inner_pad * 2 + total_body_h
        max_card_bottom = ch - s_bottom - 80
        card_bottom = min(current_y + card_h, max_card_bottom)

        # Card shadow + body
        shadow_layer = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.rounded_rectangle(
            (card_x0 + 5, current_y + 6, card_x1 + 5, card_bottom + 6),
            radius=24, fill=(0, 0, 0, 25),
        )
        bg = Image.alpha_composite(bg, shadow_layer)
        draw = ImageDraw.Draw(bg)

        draw.rounded_rectangle(
            (card_x0, current_y, card_x1, card_bottom),
            radius=24, fill=(255, 255, 255, 20),
        )
        # Left accent bar
        draw.rounded_rectangle(
            (card_x0, current_y + 24, card_x0 + 6, card_bottom - 24),
            radius=3, fill=(*theme["accent"][:3], 180),
        )

        ty = current_y + card_inner_pad
        for para in body_paragraphs:
            para = para.strip()
            if not para:
                ty += line_h // 2
                continue
            if ty > max_card_bottom - line_h:
                break
            is_bullet = para.startswith(("・", "- ", "* "))
            if is_bullet:
                clean = para.lstrip("・- *").strip()
                lines = wrap_text_jp(clean, body_font, body_max_w - 50)
                marker_y = ty + 42 // 2
                draw.ellipse(
                    (card_x0 + card_inner_pad + 10, marker_y - 6,
                     card_x0 + card_inner_pad + 22, marker_y + 6),
                    fill=(*theme["accent"][:3], 220),
                )
                for line in lines:
                    if ty > max_card_bottom - line_h:
                        break
                    draw_text_shadow(draw, card_x0 + card_inner_pad + 40, ty, line, body_font,
                                     fill=COLOR_WHITE, shadow_offset=1, outline_width=1)
                    ty += line_h
                ty += 10
            else:
                lines = wrap_text_jp(para, body_font, body_max_w)
                for line in lines:
                    if ty > max_card_bottom - line_h:
                        break
                    draw_text_shadow(draw, card_x0 + card_inner_pad + 10, ty, line, body_font,
                                     fill=COLOR_WHITE, shadow_offset=1, outline_width=1)
                    ty += line_h
                ty += 10

    # Swipe
    if slide_num <= 4:
        bg = draw_swipe_indicator(bg, cw, ch, s_bottom, style="arrow",
                                  color=(*theme["accent_light"][:3], 120))

    draw = ImageDraw.Draw(bg)
    _draw_slide_indicator(draw, slide_num, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _v4_location_card_content(
    slide_num: int,
    title: str,
    body: str,
    theme: dict,
    total_slides: int,
    platform: str,
    area_name: str = "",
    highlight_number: Optional[str] = None,
    highlight_label: Optional[str] = None,
) -> Image.Image:
    """地域ネタ category: Location card layout.

    Location pin icon, area name badge, warm orange color scheme.
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top, s_bottom = layout["safe_top"], layout["safe_bottom"]
    s_left, s_right = layout["safe_left"], layout["safe_right"]
    c_w = layout["content_w"]
    center_x = cw // 2

    # Background: warm gradient
    bg = create_gradient(cw, ch, theme["bg_dark_top"], theme["bg_dark_bottom"], direction="diagonal")

    # Subtle glow
    glow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(400, 0, -8):
        a = max(1, int(8 * (1 - r / 400)))
        gd.ellipse((center_x - r, ch // 4 - r, center_x + r, ch // 4 + r),
                    fill=(*theme["accent"][:3], a))
    bg = Image.alpha_composite(bg, glow)

    draw = ImageDraw.Draw(bg)
    _draw_corner_accents(draw, theme, canvas_w=cw, canvas_h=ch, alpha=25)

    current_y = s_top + 60

    # Area badge at top
    if area_name:
        badge_bottom = draw_area_badge(draw, center_x, current_y, area_name,
                                       bg_color=theme["accent"])
        current_y = badge_bottom + 25
    else:
        # Extract area from title if possible
        for area in ["小田原", "平塚", "秦野", "南足柄", "湘南", "箱根", "横浜", "川崎", "神奈川"]:
            if area in title:
                badge_bottom = draw_area_badge(draw, center_x, current_y, area,
                                               bg_color=theme["accent"])
                current_y = badge_bottom + 25
                break

    # Title
    title_font = load_font(bold=True, size=44, rounded=True)
    title_lines = wrap_text_jp(title, title_font, c_w - 40)
    for tl in title_lines:
        tw, _ = measure_text(tl, title_font)
        draw_text_shadow(draw, center_x - tw // 2, current_y, tl, title_font,
                         fill=COLOR_WHITE, shadow_offset=2, outline_width=1)
        current_y += int(44 * 1.5)
    current_y += 15

    # Highlight number
    if highlight_number:
        current_y = draw_number_callout(
            draw, center_x, current_y, highlight_number,
            label=highlight_label or "",
            number_color=(*theme["gradient_b"][:3], 255) if "gradient_b" in theme else theme["accent"],
            number_size=96,
        )
        current_y += 10

    # Body in card
    if body:
        card_margin = 25
        card_x0 = s_left + card_margin
        card_x1 = cw - s_right - card_margin
        card_inner_pad = 30
        body_font = load_font(bold=False, size=34, rounded=True)
        body_max_w = card_x1 - card_x0 - card_inner_pad * 2

        body_lines_all = []
        for para in body.split("\n"):
            para = para.strip()
            if not para:
                body_lines_all.append(("blank", []))
                continue
            is_bullet = para.startswith(("・", "- ", "* "))
            if is_bullet:
                clean = para.lstrip("・- *").strip()
                lines = wrap_text_jp(clean, body_font, body_max_w - 50)
                body_lines_all.append(("bullet", lines))
            else:
                lines = wrap_text_jp(para, body_font, body_max_w)
                body_lines_all.append(("text", lines))

        line_h = int(34 * LINE_HEIGHT_RATIO)
        total_h = sum(
            line_h // 2 if t == "blank" else line_h * len(ls) + 10
            for t, ls in body_lines_all
        )
        card_h = card_inner_pad * 2 + total_h
        card_bottom = min(current_y + card_h, ch - s_bottom - 80)

        # Card
        draw.rounded_rectangle(
            (card_x0, current_y, card_x1, card_bottom),
            radius=20, fill=(255, 255, 255, 25),
        )
        draw.rounded_rectangle(
            (card_x0, current_y + 20, card_x0 + 6, card_bottom - 20),
            radius=3, fill=(*theme["accent"][:3], 180),
        )

        ty = current_y + card_inner_pad
        for para_type, lines in body_lines_all:
            if para_type == "blank":
                ty += line_h // 2
                continue
            if ty > card_bottom - line_h:
                break
            if para_type == "bullet":
                marker_y = ty + 34 // 2
                draw.ellipse(
                    (card_x0 + card_inner_pad + 8, marker_y - 5,
                     card_x0 + card_inner_pad + 18, marker_y + 5),
                    fill=(*theme["accent"][:3], 220),
                )
                for line in lines:
                    if ty > card_bottom - line_h:
                        break
                    draw_text_shadow(draw, card_x0 + card_inner_pad + 35, ty, line, body_font,
                                     fill=COLOR_WHITE, shadow_offset=1, outline_width=1)
                    ty += line_h
                ty += 10
            else:
                for line in lines:
                    if ty > card_bottom - line_h:
                        break
                    draw_text_shadow(draw, card_x0 + card_inner_pad + 10, ty, line, body_font,
                                     fill=COLOR_WHITE, shadow_offset=1, outline_width=1)
                    ty += line_h
                ty += 10

    # Swipe
    if slide_num <= 4:
        bg = draw_swipe_indicator(bg, cw, ch, s_bottom, style="arrow",
                                  color=(*theme["accent_light"][:3], 120))

    draw = ImageDraw.Draw(bg)
    _draw_slide_indicator(draw, slide_num, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


def _v4_dispatch_content_slide(
    slide_num: int,
    slide_data: dict,
    category: str,
    theme: dict,
    total_slides: int,
    platform: str,
    content_slide_index: int = 0,
) -> Image.Image:
    """Dispatch to the correct v4 template based on category.

    Falls back to the original generate_slide_content() for unknown categories.
    """
    template_type = CATEGORY_TEMPLATE_TYPE.get(category, "default_enhanced")
    title = slide_data.get("title", "")
    body = slide_data.get("body", "")
    hl_num = slide_data.get("highlight_number")
    hl_label = slide_data.get("highlight_label")

    if template_type == "chat_bubble":
        return _v4_chat_bubble_content(
            slide_num, title, body, theme, total_slides, platform,
            highlight_number=hl_num, highlight_label=hl_label,
        )
    elif template_type == "infographic":
        chart_data = slide_data.get("chart_data")
        return _v4_infographic_content(
            slide_num, title, body, theme, total_slides, platform,
            highlight_number=hl_num, highlight_label=hl_label,
            chart_data=chart_data,
        )
    elif template_type == "step":
        return _v4_step_content(
            slide_num, title, body, theme, total_slides, platform,
            step_number=content_slide_index + 1,
            highlight_number=hl_num, highlight_label=hl_label,
        )
    elif template_type == "location_card":
        area = slide_data.get("area_name", "")
        return _v4_location_card_content(
            slide_num, title, body, theme, total_slides, platform,
            area_name=area,
            highlight_number=hl_num, highlight_label=hl_label,
        )
    else:
        # default_enhanced: use original generator with swipe indicator
        dark = (content_slide_index % 2 == 0)
        img = generate_slide_content(
            slide_num=slide_num, title=title, body=body,
            highlight_number=hl_num, highlight_label=hl_label,
            dark_theme=dark, theme=theme,
            total_slides=total_slides, platform=platform,
        )
        # Add swipe indicator for first 3 slides
        if slide_num <= 4:
            layout = _get_platform_layout(platform)
            img_rgba = img.convert("RGBA")
            img_rgba = draw_swipe_indicator(
                img_rgba, layout["canvas_w"], layout["canvas_h"],
                layout["safe_bottom"], style="arrow",
                color=(*theme.get("accent_light", (200, 200, 200))[:3], 120),
            )
            return img_rgba.convert("RGB")
        return img


# ===========================================================================
# v4.0 Enhanced CTA slide
# ===========================================================================

def _v4_generate_cta(
    cta_type: str,
    theme: dict,
    total_slides: int,
    platform: str,
) -> Image.Image:
    """Enhanced CTA slide with better visuals.

    Soft: Save icon + bookmark visual + warm encouragement
    Hard: LINE green button + trust badges + QR-like visual
    """
    layout = _get_platform_layout(platform)
    cw, ch = layout["canvas_w"], layout["canvas_h"]
    s_top = layout["safe_top"]
    s_bottom = layout["safe_bottom"]
    s_left = layout["safe_left"]
    s_right = layout["safe_right"]
    center_x = cw // 2

    bg = _build_brand_gradient_bg(canvas_w=cw, canvas_h=ch)
    draw = ImageDraw.Draw(bg)

    # Pre-calculate total CTA content height for vertical centering
    _header_h = 60 + 70 + 26 + 55 + 3  # logo + gap + tagline + gap + separator
    if cta_type == "hard":
        _body_h = 50 + 62 + 60 + 102 + 40 + 26 + 65 + 30  # badge+btn+sub+trust
    else:
        _body_h = 50 + 62 + 30 + 96 + 50 + 44 + 60 + 26 + 65 + 30  # bookmark+save+follow+prof+trust
    _total_cta_h = _header_h + _body_h
    _available_h = ch - s_top - s_bottom - 80
    _cta_start = s_top + max(40, (_available_h - _total_cta_h) // 2)

    # Brand logo (rounded font)
    logo_font = load_font(bold=True, size=60, rounded=True)
    logo_text = "神奈川ナース転職"
    tw, _ = measure_text(logo_text, logo_font)
    logo_y = _cta_start
    draw_text_shadow(draw, center_x - tw // 2, logo_y, logo_text, logo_font,
                     fill=COLOR_WHITE, shadow_offset=3)

    # Brand tagline
    tag_font = load_font(bold=False, size=26)
    tag_text = CTA_TEMPLATE.get("brand", "シン・AI転職") + " — " + CTA_TEMPLATE.get("tagline", "早い × 簡単 × 24時間")
    tw, th = measure_text(tag_text, tag_font)
    tag_max_w = cw - s_left - s_right - 20
    if tw > tag_max_w:
        tag_font = load_font(bold=False, size=tag_font.size - 4)
        tw, th = measure_text(tag_text, tag_font)
    tag_y = logo_y + 70
    draw.text((center_x - tw // 2, tag_y), tag_text, fill=(*COLOR_WHITE[:3], 150), font=tag_font)

    sep_y = tag_y + 55
    draw.rounded_rectangle(
        (center_x - 90, sep_y, center_x + 90, sep_y + 3),
        radius=2, fill=(*COLOR_WHITE[:3], 70),
    )

    if cta_type == "hard":
        # === Hard CTA: LINE green button ===

        # Badge
        badge_y = sep_y + 50
        badge_font = load_font(bold=True, size=30, rounded=True)
        badge_text = "紹介手数料 業界最安10%"
        btw, bth = measure_text(badge_text, badge_font)
        badge_pad_x, badge_pad_y = 40, 16
        badge_w = btw + badge_pad_x * 2
        badge_h = bth + badge_pad_y * 2
        badge_x = center_x - badge_w // 2

        draw.rounded_rectangle(
            (badge_x, badge_y, badge_x + badge_w, badge_y + badge_h),
            radius=badge_h // 2,
            fill=(*COLOR_WHITE[:3], 35),
            outline=(*COLOR_WHITE[:3], 160), width=2,
        )
        draw.text((badge_x + badge_pad_x, badge_y + badge_pad_y),
                  badge_text, fill=COLOR_WHITE, font=badge_font)

        # CTA green button
        LINE_GREEN = (6, 199, 85)
        btn_y = badge_y + badge_h + 60
        btn_font = load_font(bold=True, size=42, rounded=True)
        btn_text = CTA_TEMPLATE.get("cta_text", "30秒AI診断であなたの求人がわかる")
        btn_pad_x, btn_pad_y = 65, 30
        max_btn_w = cw - s_left - s_right - 40  # Don't exceed safe zone
        # If btn_text is too wide, reduce font size
        btw2 = measure_text(btn_text, btn_font)[0]
        while btw2 > max_btn_w - btn_pad_x * 2 and btn_font.size > 28:
            btn_font = load_font(bold=True, size=btn_font.size - 2, rounded=True)
            btw2 = measure_text(btn_text, btn_font)[0]
        btw2, bth2 = measure_text(btn_text, btn_font)
        btn_w = btw2 + btn_pad_x * 2
        if btn_w > max_btn_w:
            btn_w = max_btn_w
        btn_h = bth2 + btn_pad_y * 2
        btn_x = center_x - btn_w // 2

        # Pulse rings
        pulse = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pulse)
        btn_cx, btn_cy = center_x, btn_y + btn_h // 2
        for ri in range(4):
            rr = btn_w // 2 + 18 + ri * 22
            ra = max(5, 28 - ri * 7)
            pd.ellipse((btn_cx - rr, btn_cy - rr, btn_cx + rr, btn_cy + rr),
                       outline=(*LINE_GREEN[:3], ra), width=2)
        bg = Image.alpha_composite(bg, pulse)
        draw = ImageDraw.Draw(bg)

        # Button shadow
        draw.rounded_rectangle(
            (btn_x + 4, btn_y + 5, btn_x + btn_w + 4, btn_y + btn_h + 5),
            radius=btn_h // 2, fill=(0, 0, 0, 30),
        )
        # Button (LINE green)
        draw.rounded_rectangle(
            (btn_x, btn_y, btn_x + btn_w, btn_y + btn_h),
            radius=btn_h // 2, fill=LINE_GREEN,
        )
        draw.text((btn_x + btn_pad_x, btn_y + btn_pad_y),
                  btn_text, fill=COLOR_WHITE, font=btn_font)

        # Sub text
        sub_y = btn_y + btn_h + 40
        sub_font = load_font(bold=False, size=26, rounded=True)
        sub_text = CTA_TEMPLATE.get("cta_sub", "プロフィールのリンクから →")
        tw, _ = measure_text(sub_text, sub_font)
        draw.text((center_x - tw // 2, sub_y), sub_text,
                  fill=(*COLOR_WHITE[:3], 170), font=sub_font)

        # Trust badges
        trust_y = sub_y + 65
        _draw_trust_badges(draw, center_x, trust_y)

    else:
        # === Soft CTA: Save bookmark ===

        # Bookmark icon (alpha-composited overlay)
        bm_y = sep_y + 50
        bm_size = 48
        bm_x = center_x - bm_size // 2
        bm_overlay = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        bm_draw = ImageDraw.Draw(bm_overlay)
        bm_bottom = bm_y + int(bm_size * 1.3)
        # Bookmark body
        bm_draw.rectangle((bm_x, bm_y, bm_x + bm_size, bm_bottom),
                          fill=(255, 255, 255, 60))
        # V-notch cutout: draw background-color triangle to create notch
        bm_draw.polygon([
            (bm_x, bm_bottom),
            (bm_x + bm_size // 2, bm_bottom - bm_size // 3),
            (bm_x + bm_size, bm_bottom),
        ], fill=(0, 0, 0, 0))
        bg = Image.alpha_composite(bg, bm_overlay)
        draw = ImageDraw.Draw(bg)

        # Save text
        save_y = bm_y + int(bm_size * 1.3) + 30
        save_font = load_font(bold=True, size=44, rounded=True)
        save_text = "保存してね"
        stw, sth = measure_text(save_text, save_font)
        save_pad_x, save_pad_y = 55, 26
        save_w = stw + save_pad_x * 2
        save_h = sth + save_pad_y * 2
        save_x = center_x - save_w // 2

        # Pulse rings
        pulse = Image.new("RGBA", bg.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pulse)
        for ri in range(3):
            rr = save_w // 2 + 12 + ri * 20
            ra = max(5, 22 - ri * 7)
            pd.ellipse((center_x - rr, save_y + save_h // 2 - rr,
                        center_x + rr, save_y + save_h // 2 + rr),
                       outline=(255, 255, 255, ra), width=2)
        bg = Image.alpha_composite(bg, pulse)
        draw = ImageDraw.Draw(bg)

        # Button
        draw.rounded_rectangle(
            (save_x + 3, save_y + 4, save_x + save_w + 3, save_y + save_h + 4),
            radius=save_h // 2, fill=(0, 0, 0, 25),
        )
        draw.rounded_rectangle(
            (save_x, save_y, save_x + save_w, save_y + save_h),
            radius=save_h // 2, fill=COLOR_WHITE,
        )
        draw.text((save_x + save_pad_x, save_y + save_pad_y),
                  save_text, fill=COLOR_BRAND_BLUE, font=save_font)

        # Heart icon next to bookmark
        draw_icon_heart(draw, center_x + save_w // 2 + 30, save_y + save_h // 2,
                        size=18, color=(255, 120, 140))

        # Follow text (clamped to safe zone)
        follow_y = min(save_y + save_h + 50, ch - s_bottom - 120)
        follow_font = load_font(bold=True, size=34, rounded=True)
        follow_text = "フォローで最新情報をチェック"
        follow_lines = wrap_text_jp(follow_text, follow_font, cw - 120)
        for fl in follow_lines:
            if follow_y > ch - s_bottom - 40:
                break
            tw, _ = measure_text(fl, follow_font)
            draw.text((center_x - tw // 2, follow_y), fl, fill=COLOR_WHITE, font=follow_font)
            follow_y += int(34 * LINE_HEIGHT_RATIO)

        # Subtitle (clamped to safe zone)
        prof_y = min(follow_y + 20, ch - s_bottom - 50)
        prof_font = load_font(bold=False, size=26, rounded=True)
        prof_text = "神奈川県の看護師転職"
        ptw, _ = measure_text(prof_text, prof_font)
        if prof_y < ch - s_bottom - 30:
            draw.text((center_x - ptw // 2, prof_y), prof_text,
                      fill=(*COLOR_WHITE[:3], 150), font=prof_font)

        # Trust badges (clamped)
        trust_y = min(prof_y + 60, ch - s_bottom - 30)
        _draw_trust_badges(draw, center_x, trust_y)

    _draw_slide_indicator(draw, total_slides, total_slides, light_bg=False, canvas_w=cw, safe_top=s_top)
    _draw_brand_watermark(draw, light_bg=False, platform=platform, canvas_w=cw, canvas_h=ch, safe_bottom=s_bottom)

    return bg.convert("RGB")


# ===========================================================================
# v4.0 Enhanced hook slide
# ===========================================================================

def _v4_generate_hook(
    hook_text: str,
    theme: dict,
    total_slides: int,
    platform: str,
    category: str = "",
) -> Image.Image:
    """Enhanced hook slide using rounded font + category-specific accent.

    Delegates to the original generator but uses rounded font and adds swipe arrow.
    """
    # Use existing hook generator (it's already good)
    img = generate_slide_hook(hook_text, theme=theme, total_slides=total_slides, platform=platform)

    # Add swipe indicator
    layout = _get_platform_layout(platform)
    img_rgba = img.convert("RGBA")
    img_rgba = draw_swipe_indicator(
        img_rgba, layout["canvas_w"], layout["canvas_h"],
        layout["safe_bottom"], style="arrow",
        color=(*theme.get("accent_light", (200, 200, 200))[:3], 140),
    )
    return img_rgba.convert("RGB")


# ===========================================================================
# Main carousel generator v4.0
# ===========================================================================

def generate_carousel(
    content_id: str,
    hook: str,
    slides: list[dict],
    output_dir: str,
    category: str = "あるある",
    cta_type: str = "soft",
    reveal: dict = None,   # kept for backward compat, merged into last content slide
    platform: str = "tiktok",
) -> list[str]:
    """
    Generate an 8-slide carousel set (Hook + 6 Content + CTA).

    Args:
        content_id: Unique ID (e.g. "A01")
        hook: Text for slide 1 (10 chars ideal)
        slides: List of dicts for content slides:
                [{title, body, highlight_number?, highlight_label?}, ...]
                Up to 6 slides used. If 7+ provided, last is merged or truncated.
        output_dir: Directory to save PNG files
        category: Content category for color scheme
        cta_type: "soft" or "hard"
        reveal: (backward compat) If provided, appended as last content slide
        platform: "tiktok" (9:16), "instagram" (4:5 feed), or "instagram_story" (9:16)

    Returns:
        List of saved PNG file paths
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Resolve category aliases (e.g. "aruaru" -> "あるある")
    resolved_cat = CATEGORY_ALIASES.get(category, category)
    theme = CATEGORY_THEMES.get(resolved_cat, DEFAULT_THEME)

    # All slides are now rendered NATIVELY at the correct platform dimensions.
    target_w, target_h = PLATFORM_SIZES.get(platform, (CANVAS_W, CANVAS_H))

    # v4.0: Use category-specific templates for TikTok
    use_v4 = (platform != "instagram") and (resolved_cat in CATEGORY_TEMPLATE_TYPE)

    def _save_slide(img: Image.Image, path: Path) -> str:
        """Save slide (already rendered at correct platform dimensions)."""
        img.save(str(path), "PNG", quality=95)
        return str(path)

    # Merge reveal into slides if provided (backward compat)
    content_slides = list(slides)
    if reveal and reveal.get("text"):
        reveal_title = reveal.get("text", "")
        reveal_body = ""
        if reveal.get("number"):
            reveal_body = reveal["number"]
            if reveal.get("label"):
                reveal_body += "\n" + reveal["label"]
        content_slides.append({
            "title": reveal_title,
            "body": reveal_body,
            "highlight_number": reveal.get("number"),
            "highlight_label": reveal.get("label"),
        })

    # Limit to 6 content slides for 8-slide total
    content_slides = content_slides[:6]

    total_slides_count = 1 + len(content_slides) + 1  # Hook + Content + CTA
    saved_paths: list[str] = []

    template_type = CATEGORY_TEMPLATE_TYPE.get(resolved_cat, "default") if use_v4 else "legacy"
    platform_label = f", platform: {platform} {target_w}x{target_h}" if platform != "tiktok" else ""
    print(f"  [{content_id}] Generating {total_slides_count}-slide v4 carousel "
          f"(category: {resolved_cat}, template: {template_type}{platform_label})")

    # --- Instagram: use dedicated IG design system ---
    use_ig = (platform == "instagram")

    # --- Slide 1: HOOK ---
    if use_ig:
        img1 = generate_ig_hook_slide(hook, total_slides=total_slides_count)
    elif use_v4:
        img1 = _v4_generate_hook(hook, theme=theme, total_slides=total_slides_count,
                                  platform=platform, category=resolved_cat)
    else:
        img1 = generate_slide_hook(hook, theme=theme, total_slides=total_slides_count, platform=platform)
    p1 = out / f"{content_id}_slide_01_hook.png"
    saved_paths.append(_save_slide(img1, p1))
    print(f"    slide 01 (HOOK{'|IG' if use_ig else ''}): {hook[:30]}...")

    # --- Slides 2-7: CONTENT ---
    for i, slide_data in enumerate(content_slides):
        slide_num = i + 2

        if use_ig:
            title = slide_data.get("title", "")
            body = slide_data.get("body", "")
            hl_num = slide_data.get("highlight_number")
            hl_label = slide_data.get("highlight_label")
            img = generate_ig_content_slide(
                slide_num=slide_num,
                title=title,
                body=body,
                highlight_number=hl_num,
                highlight_label=hl_label,
                total_slides=total_slides_count,
            )
        elif use_v4:
            img = _v4_dispatch_content_slide(
                slide_num=slide_num,
                slide_data=slide_data,
                category=resolved_cat,
                theme=theme,
                total_slides=total_slides_count,
                platform=platform,
                content_slide_index=i,
            )
        else:
            dark = (i % 2 == 0)
            title = slide_data.get("title", "")
            body = slide_data.get("body", "")
            hl_num = slide_data.get("highlight_number")
            hl_label = slide_data.get("highlight_label")
            img = generate_slide_content(
                slide_num=slide_num,
                title=title,
                body=body,
                highlight_number=hl_num,
                highlight_label=hl_label,
                dark_theme=dark,
                theme=theme,
                total_slides=total_slides_count,
                platform=platform,
            )
        p = out / f"{content_id}_slide_{slide_num:02d}_content.png"
        saved_paths.append(_save_slide(img, p))
        title_preview = slide_data.get("title", "")[:30]
        print(f"    slide {slide_num:02d} (CONTENT|{template_type}): {title_preview}...")

    # --- Final slide: CTA ---
    cta_slide_num = total_slides_count
    if use_ig:
        img_cta = generate_ig_cta_slide(cta_type=cta_type, total_slides=total_slides_count)
    elif use_v4:
        img_cta = _v4_generate_cta(cta_type=cta_type, theme=theme, total_slides=total_slides_count, platform=platform)
    else:
        img_cta = generate_slide_cta(cta_type=cta_type, theme=theme, total_slides=total_slides_count, platform=platform)
    p_cta = out / f"{content_id}_slide_{cta_slide_num:02d}_cta.png"
    saved_paths.append(_save_slide(img_cta, p_cta))
    print(f"    slide {cta_slide_num:02d} (CTA{'|IG' if use_ig else ''}: {cta_type})")

    print(f"  [{content_id}] Done: {len(saved_paths)} slides saved to {out}")
    return saved_paths


# ===========================================================================
# Queue integration
# ===========================================================================

def _split_title_body(text: str) -> tuple[str, str]:
    """Split a slide text into a short title and longer body.

    Title is a short header (max 20 chars), body is the full text.
    If no good split point is found, title is a truncated version
    and body gets the FULL original text (not the remainder).
    """
    MAX_TITLE = 20

    if "\n" in text:
        parts = text.split("\n", 1)
        candidate = parts[0].strip()
        if len(candidate) <= MAX_TITLE:
            return candidate, parts[1].strip()

    # Try splitting at sentence boundaries
    for delim in ["。", "？", "！"]:
        if delim in text:
            parts = text.split(delim, 1)
            candidate = parts[0].strip()
            if len(candidate) <= MAX_TITLE:
                return candidate + delim, parts[1].strip() if parts[1].strip() else text

    # Try comma as last resort
    if "、" in text:
        parts = text.split("、", 1)
        candidate = parts[0].strip()
        if len(candidate) <= MAX_TITLE:
            # Body gets the FULL text so nothing is lost
            return candidate + "、", text

    # No good split: short title + full text as body
    if len(text) > MAX_TITLE:
        return text[:MAX_TITLE] + "...", text

    # Short text: use as title only, body empty
    return text, ""


def _extract_carousel_content(json_path: str) -> Optional[dict]:
    """Extract carousel content from a slide JSON file."""
    path = Path(json_path)
    if not path.exists():
        print(f"  WARNING: JSON not found: {json_path}")
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  WARNING: Cannot parse {json_path}: {e}")
        return None

    content_id = data.get("content_id", data.get("id", path.stem))
    category = data.get("category", "あるある")
    cta_type = data.get("cta_type", "soft")
    raw_slides = data.get("slides", [])

    if not raw_slides:
        print(f"  WARNING: No slides in {json_path}")
        return None

    slide_texts: list[str] = []
    if isinstance(raw_slides[0], str):
        slide_texts = [s.strip() for s in raw_slides]
    elif isinstance(raw_slides[0], dict):
        for s in raw_slides:
            text = s.get("text", "")
            subtext = s.get("subtext", "")
            if subtext:
                slide_texts.append(f"{text}\n{subtext}")
            else:
                slide_texts.append(text.strip())

    if len(slide_texts) < 2:
        print(f"  WARNING: Need at least 2 slides, got {len(slide_texts)} in {json_path}")
        return None

    hook = data.get("hook", slide_texts[0])

    # v4.0: Extract slide_meta for category-specific templates
    slide_meta = data.get("slide_meta", {})
    chart_data = slide_meta.get("chart_data")
    area_name = slide_meta.get("area_name", "")
    meta_hl_number = slide_meta.get("highlight_number")
    meta_hl_label = slide_meta.get("highlight_label")

    # Build content slides (up to 6 for 8-slide format)
    middle = slide_texts[1:]
    content_slides: list[dict] = []
    for i in range(min(6, len(middle))):
        text = middle[i]
        title, body = _split_title_body(text)
        slide = {"title": title, "body": body}

        # Apply slide_meta to appropriate slides
        if area_name:
            slide["area_name"] = area_name
        # Apply chart_data to Data slide (index 1 = 3rd slide overall)
        if chart_data and i == 1:
            slide["chart_data"] = chart_data
        # Apply highlight to Reveal slide (index 4 = 6th slide overall) or first slide without one
        if meta_hl_number and i == min(4, len(middle) - 1):
            slide["highlight_number"] = meta_hl_number
            slide["highlight_label"] = meta_hl_label or ""

        content_slides.append(slide)

    # If no content slides, create at least one
    if not content_slides:
        content_slides.append({"title": "...", "body": "..."})

    return {
        "content_id": content_id,
        "hook": hook,
        "slides": content_slides,
        "category": category,
        "cta_type": cta_type,
    }


def generate_from_queue(queue_path: str, output_base: str) -> int:
    """Read posting_queue.json, generate carousel slides for pending items."""
    qpath = Path(queue_path)
    if not qpath.exists():
        print(f"ERROR: Queue file not found: {queue_path}")
        return 0

    with open(qpath, "r", encoding="utf-8") as f:
        queue = json.load(f)

    posts = queue.get("posts", [])
    pending = [p for p in posts if p.get("status") in ("pending", "failed")]

    if not pending:
        print("No pending posts in queue.")
        return 0

    print(f"Found {len(pending)} pending posts in queue.")
    out_base = Path(output_base)
    generated = 0

    for post in pending:
        json_path = post.get("json_path")
        cid = post.get("content_id", "unknown")
        if not json_path:
            print(f"  [{cid}] Skipping: no json_path")
            continue

        content = _extract_carousel_content(json_path)
        if not content:
            print(f"  [{cid}] Skipping: could not extract content")
            continue

        today = datetime.now().strftime("%Y%m%d")
        output_dir = out_base / f"carousel_{today}_{cid}"

        try:
            paths = generate_carousel(
                content_id=content["content_id"],
                hook=content["hook"],
                slides=content["slides"],
                output_dir=str(output_dir),
                category=content["category"],
                cta_type=content.get("cta_type", "soft"),
            )
            generated += 1
        except Exception as e:
            print(f"  [{cid}] ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\nGenerated {generated}/{len(pending)} carousel sets.")
    return generated


# ===========================================================================
# Demo
# ===========================================================================

def generate_demo(output_dir: str = "content/generated/carousel_demo_v3") -> list[str]:
    """Generate a sample carousel set for review."""
    print("=== Generating demo carousel (v3.0) ===\n")

    return generate_carousel(
        content_id="DEMO_V3",
        hook="手数料\n知ってる？",
        slides=[
            {
                "title": "看護師は無料で使える",
                "body": "でも、病院側は年収の20〜30%を\nエージェントに支払っています。\n\n・年収400万 → 手数料80〜120万\n・年収500万 → 手数料100〜150万",
            },
            {
                "title": "手数料が高いとどうなる？",
                "body": "病院は高い手数料を払った分\n採用のハードルを上げます。\n\n・面接が厳しくなる\n・条件交渉が通りにくい\n・入職後の圧が強くなる",
                "highlight_number": "120万円",
                "highlight_label": "大手の平均手数料（年収400万の場合）",
            },
            {
                "title": "手数料10%で解決",
                "body": "病院の負担が軽い\n→ 採用されやすい\n→ 条件交渉もしやすい\n→ 入職後の関係も良好\n\nつまり、あなたが得をする。",
                "highlight_number": "10%",
                "highlight_label": "神奈川ナース転職の紹介手数料",
            },
        ],
        output_dir=output_dir,
        category="転職・キャリア",
        cta_type="hard",
    )


def generate_demo_aruaru(output_dir: str = "content/generated/carousel_demo_aruaru_v3") -> list[str]:
    """Generate an aruaru-themed demo for review."""
    print("=== Generating aruaru demo carousel (v3.0) ===\n")

    return generate_carousel(
        content_id="DEMO_ARUARU_V3",
        hook="AIは怒らない",
        slides=[
            {
                "title": "先輩の恐怖のセリフ",
                "body": "新人の頃、質問したら\n返ってきたあの一言。\n\n「それ前にも言ったよね？」\n\n心臓止まるかと思った。",
            },
            {
                "title": "AIに100回聞いてみた",
                "body": "「この薬の投与速度は？」\n\n・1回目: 丁寧に説明\n・50回目: まだ丁寧\n・100回目: 変わらず丁寧\n\n全然怒らない。",
            },
            {
                "title": "理想の先輩だった",
                "body": "・何回聞いても怒らない\n・「前にも言ったよね」ゼロ\n・24時間いつでも対応\n・ため息もつかない",
                "highlight_number": "0回",
                "highlight_label": "AIが怒った回数",
            },
        ],
        output_dir=output_dir,
        category="あるある×AI",
        cta_type="soft",
    )


def generate_demo_instagram(output_dir: str = "content/generated/carousel_demo_instagram") -> list[str]:
    """Generate Instagram-specific demo carousel using the Warm Coral design system."""
    print("=== Generating Instagram demo carousel (Warm Coral) ===\n")

    return generate_carousel(
        content_id="DEMO_IG",
        hook="手数料\n知ってる？",
        slides=[
            {
                "title": "看護師は無料で使える",
                "body": "でも、病院側は年収の20〜30%を\nエージェントに支払っています。\n\n・年収400万 → 手数料80〜120万\n・年収500万 → 手数料100〜150万",
            },
            {
                "title": "手数料が高いとどうなる？",
                "body": "病院は高い手数料を払った分\n採用のハードルを上げます。\n\n・面接が厳しくなる\n・条件交渉が通りにくい\n・入職後の圧が強くなる",
                "highlight_number": "120万円",
                "highlight_label": "大手の平均手数料（年収400万の場合）",
            },
            {
                "title": "手数料10%で解決",
                "body": "病院の負担が軽い\n→ 採用されやすい\n→ 条件交渉もしやすい\n→ 入職後の関係も良好\n\nつまり、あなたが得をする。",
                "highlight_number": "10%",
                "highlight_label": "神奈川ナース転職の紹介手数料",
            },
        ],
        output_dir=output_dir,
        category="転職・キャリア",
        cta_type="hard",
        platform="instagram",
    )


def generate_demo_all(base_dir: str = "content/generated/carousel_demo_v4") -> dict[str, list[str]]:
    """Generate demo carousels for ALL 5 category templates + CTA variants.

    Returns dict mapping category name to list of saved paths.
    """
    print("=" * 60)
    print("  v4.0 DEMO: Generating all 5 category templates")
    print("=" * 60)

    base = Path(base_dir)
    results = {}

    # 1. あるある (Chat Bubble)
    print("\n--- [1/5] あるある (Chat Bubble) ---")
    results["あるある"] = generate_carousel(
        content_id="V4_ARUARU",
        hook="先輩の口癖\n知ってる？",
        slides=[
            {
                "title": "先輩に質問した結果",
                "body": "この薬の投与速度は？\n前にも言ったよね？\n…聞けなくなった",
            },
            {
                "title": "AIに100回聞いてみた",
                "body": "1回目: 丁寧に説明してくれた\n50回目: まだ丁寧\n100回目: 変わらず丁寧",
            },
            {
                "title": "夜勤明けの顔",
                "body": "AIに何歳に見えるか聞いた\n実年齢+10歳って言われた\n…嘘でもいいから盛ってくれ",
                "highlight_number": "+10歳",
                "highlight_label": "AIの残酷な正直さ",
            },
        ],
        output_dir=str(base / "aruaru"),
        category="あるある",
        cta_type="soft",
    )

    # 2. 給与・待遇 (Infographic)
    print("\n--- [2/5] 給与・待遇 (Infographic) ---")
    results["給与"] = generate_carousel(
        content_id="V4_SALARY",
        hook="手取り\n比べてみた",
        slides=[
            {
                "title": "神奈川の看護師年収",
                "body": "平均年収は地域で大きく違う。\n同じ仕事なのに、差がある現実。",
                "highlight_number": "480万円",
                "highlight_label": "神奈川県の看護師平均年収",
            },
            {
                "title": "地域別の比較",
                "body": "",
                "chart_data": [
                    {"label": "横浜市", "value": 520, "display": "520万"},
                    {"label": "川崎市", "value": 500, "display": "500万"},
                    {"label": "平塚市", "value": 460, "display": "460万"},
                    {"label": "小田原市", "value": 440, "display": "440万"},
                ],
            },
            {
                "title": "手数料の真実",
                "body": "大手は年収の20-30%を病院に請求。\n年収400万なら80-120万円。\n\n神奈川ナース転職は10%。\n40万円で済む。差額は病院の負担軽減。",
                "highlight_number": "10%",
                "highlight_label": "神奈川ナース転職の紹介手数料",
            },
        ],
        output_dir=str(base / "salary"),
        category="給与・待遇",
        cta_type="hard",
    )

    # 3. 転職・キャリア (Step)
    print("\n--- [3/5] 転職・キャリア (Step) ---")
    results["転職"] = generate_carousel(
        content_id="V4_CAREER",
        hook="転職の手順\n3ステップ",
        slides=[
            {
                "title": "LINEで相談する",
                "body": "まずはLINEで友だち追加。\n\n・希望エリア\n・希望の働き方\n・気になること\n\n何でも聞いてください。",
            },
            {
                "title": "求人を紹介してもらう",
                "body": "条件に合う求人をご提案。\n\n・手数料10%だから病院も受入やすい\n・条件交渉もしやすい\n・面接対策もサポート",
            },
            {
                "title": "入職・アフターフォロー",
                "body": "入職後も安心のサポート。\n\n・入職後の悩み相談\n・条件の確認\n・何かあればいつでもLINE",
                "highlight_number": "0円",
                "highlight_label": "看護師さんの負担",
            },
        ],
        output_dir=str(base / "career"),
        category="転職・キャリア",
        cta_type="hard",
    )

    # 4. 地域ネタ (Location Card)
    print("\n--- [4/5] 地域ネタ (Location Card) ---")
    results["地域ネタ"] = generate_carousel(
        content_id="V4_LOCAL",
        hook="小田原の\n看護師事情",
        slides=[
            {
                "title": "小田原から横浜まで72分",
                "body": "往復144分。年間600時間。\n満員電車に捧げる時間。\n\nでも地元で働けば\nその600時間が自由になる。",
                "area_name": "小田原",
                "highlight_number": "600時間",
                "highlight_label": "年間の通勤時間（横浜往復の場合）",
            },
            {
                "title": "県西部の求人事情",
                "body": "看護師不足は深刻。\nでも大手紹介会社の手数料が高くて\n病院が使えない。\n\n手数料10%なら、\n地元の病院も紹介を使える。",
                "area_name": "神奈川県西部",
            },
            {
                "title": "地元で働くメリット",
                "body": "・通勤30分以内\n・家賃が安い\n・夕飯を家で食べられる\n・子育てしやすい\n・地域に根ざした医療",
                "area_name": "小田原",
            },
        ],
        output_dir=str(base / "local"),
        category="地域ネタ",
        cta_type="soft",
    )

    # 5. サービス紹介 (Default Enhanced)
    print("\n--- [5/5] サービス紹介 (Default Enhanced) ---")
    results["サービス紹介"] = generate_carousel(
        content_id="V4_SERVICE",
        hook="手数料10%\nって何？",
        slides=[
            {
                "title": "看護師は無料で使える",
                "body": "でも、病院側は年収の20〜30%を\nエージェントに支払っています。\n\n・年収400万 → 手数料80〜120万\n・年収500万 → 手数料100〜150万",
            },
            {
                "title": "手数料が高いとどうなる？",
                "body": "病院は高い手数料を払った分\n採用のハードルを上げます。\n\n・面接が厳しくなる\n・条件交渉が通りにくい\n・入職後の圧が強くなる",
                "highlight_number": "120万円",
                "highlight_label": "大手の平均手数料（年収400万の場合）",
            },
            {
                "title": "手数料10%で解決",
                "body": "病院の負担が軽い\n→ 採用されやすい\n→ 条件交渉もしやすい\n→ 入職後の関係も良好\n\nつまり、あなたが得をする。",
                "highlight_number": "10%",
                "highlight_label": "神奈川ナース転職の紹介手数料",
            },
        ],
        output_dir=str(base / "service"),
        category="サービス紹介",
        cta_type="hard",
    )

    print("\n" + "=" * 60)
    total = sum(len(v) for v in results.values())
    print(f"  v4.0 DEMO COMPLETE: {total} slides across {len(results)} categories")
    print(f"  Output: {base}")
    print("=" * 60)

    return results


# ===========================================================================
# CLI
# ===========================================================================

def generate_carousel_backgrounds(
    content_id: str,
    hook: str,
    slides: list[dict],
    output_dir: str,
    category: str = "あるある",
    cta_type: str = "soft",
    platform: str = "tiktok",
) -> dict:
    """
    Generate background-only slides (no text) + metadata JSON for animated video.

    Returns dict with 'backgrounds' (list of paths) and 'metadata' (text positioning info).
    Used by video_text_animator.py to create dynamic text animations with ffmpeg.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Platform dimensions
    canvas_w, canvas_h = PLATFORM_SIZES.get(platform, (CANVAS_W, CANVAS_H))
    safe = SAFE_ZONES.get(platform, SAFE_ZONES["tiktok"])

    theme = CATEGORY_THEMES.get(category, DEFAULT_THEME)
    content_slides = list(slides)[:6]
    total = 1 + len(content_slides) + 1

    bg_paths = []
    metadata = {
        "content_id": content_id,
        "platform": platform,
        "canvas": {"w": canvas_w, "h": canvas_h},
        "safe_zones": safe,
        "total_slides": total,
        "category": category,
        "cta_type": cta_type,
        "slides": [],
    }

    # Slide 1: Hook background (rendered natively at platform size)
    bg1 = _build_dark_bg(theme, canvas_w=canvas_w, canvas_h=canvas_h)
    p1 = out / f"{content_id}_bg_01_hook.png"
    bg1.save(str(p1), "PNG")
    bg_paths.append(str(p1))

    font_hook = load_font(bold=True, size=120)
    hook_bbox = font_hook.getbbox(hook[:MAX_HOOK_CHARS])
    hook_w = hook_bbox[2] - hook_bbox[0]
    hook_h = hook_bbox[3] - hook_bbox[1]

    metadata["slides"].append({
        "type": "hook",
        "text": hook[:MAX_HOOK_CHARS],
        "font_size": 120,
        "font_bold": True,
        "color": list(theme["text_primary"]),
        "x": (canvas_w - hook_w) // 2,
        "y": (canvas_h - hook_h) // 2,
        "animation": "zoom_in",
        "duration": 2.5,
    })

    # Content slides (rendered natively at platform size)
    for i, slide_data in enumerate(content_slides):
        slide_num = i + 2
        dark = (i % 2 == 0)

        if dark:
            bg = _build_dark_bg(theme, canvas_w=canvas_w, canvas_h=canvas_h)
        else:
            bg = _build_light_bg(theme, canvas_w=canvas_w, canvas_h=canvas_h)

        p = out / f"{content_id}_bg_{slide_num:02d}_content.png"
        bg.save(str(p), "PNG")
        bg_paths.append(str(p))

        title = slide_data.get("title", "")
        body = slide_data.get("body", "")
        text_color = list(theme["text_primary"]) if dark else list(theme["text_on_light"])

        # Calculate card area for text positioning
        card_x = safe["left"] + 20
        card_y = safe["top"] + 80
        card_w = canvas_w - safe["left"] - safe["right"] - 40

        title_font_size = 64
        body_font_size = 48

        metadata["slides"].append({
            "type": "content",
            "dark": dark,
            "title": title,
            "title_font_size": title_font_size,
            "body": body,
            "body_font_size": body_font_size,
            "color": text_color,
            "card_x": card_x,
            "card_y": card_y,
            "card_w": card_w,
            "highlight_number": slide_data.get("highlight_number"),
            "highlight_label": slide_data.get("highlight_label"),
            "animation": "fade_in_stagger",
            "duration": 3.5,
        })

    # CTA background (rendered natively at platform size)
    bg_cta = _build_brand_gradient_bg(canvas_w=canvas_w, canvas_h=canvas_h)
    p_cta = out / f"{content_id}_bg_{total:02d}_cta.png"
    bg_cta.save(str(p_cta), "PNG")
    bg_paths.append(str(p_cta))

    cta_texts = {
        "soft": ["保存してね", CTA_TEMPLATE.get("cta_sub", "プロフィールのリンクから →")],
        "hard": [CTA_TEMPLATE.get("cta_text", "30秒AI診断であなたの求人がわかる"), CTA_TEMPLATE.get("cta_sub", "プロフィールのリンクから →")],
    }
    cta = cta_texts.get(cta_type, cta_texts["soft"])

    metadata["slides"].append({
        "type": "cta",
        "cta_type": cta_type,
        "texts": cta,
        "font_size": 56,
        "color": [255, 255, 255],
        "animation": "pulse",
        "duration": 3.0,
    })

    # Save metadata
    meta_path = out / f"{content_id}_text_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"  [{content_id}] Backgrounds: {len(bg_paths)} + metadata saved")
    return {"backgrounds": bg_paths, "metadata": str(meta_path)}


# ===========================================================================
# Playwright rendering (HTML template-based)
# ===========================================================================

# Viewport sizes for Playwright renderer
PLAYWRIGHT_VIEWPORTS = {
    "tiktok": {"width": 1080, "height": 1920},
    "instagram_feed": {"width": 1080, "height": 1350},
    "instagram_square": {"width": 1080, "height": 1080},
}

# Map platform names used in CLI to Playwright viewport keys
_PLATFORM_TO_PW_FORMAT = {
    "tiktok": "tiktok",
    "instagram": "instagram_feed",
    "instagram_story": "tiktok",  # same 9:16 ratio
}


def render_slide_playwright(
    slide_data: dict,
    format: str,
    category: str,
    output_path: str,
) -> str:
    """Render a single slide using Playwright to screenshot an HTML template.

    Args:
        slide_data: Dict with keys: slide_type, title_text, body_text,
                    accent_text, label_text, cta_text, slide_number, cta_button_text
        format: "tiktok", "instagram_feed", or "instagram_square"
        category: "aruaru", "tenshoku", "kyuyo", "service", "trend"
        output_path: Where to save the PNG screenshot

    Returns:
        The output_path on success.

    Raises:
        RuntimeError: If Playwright/Jinja2 are not installed.
    """
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright rendering requires playwright and jinja2. "
            "Install with: pip install playwright jinja2 && playwright install chromium"
        )

    # Resolve template directory
    templates_dir = Path(__file__).parent.parent / "templates"
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("base.html")

    # Build template variables
    template_vars = {
        "format": format,
        "category": category,
        "slide_type": slide_data.get("slide_type", "body"),
        "title_text": slide_data.get("title_text", ""),
        "body_text": slide_data.get("body_text", ""),
        "accent_text": slide_data.get("accent_text", ""),
        "label_text": slide_data.get("label_text", ""),
        "cta_text": slide_data.get("cta_text", ""),
        "slide_number": slide_data.get("slide_number", 1),
        "cta_button_text": slide_data.get("cta_button_text", ""),
    }

    html_content = template.render(**template_vars)

    # Get viewport size
    viewport = PLAYWRIGHT_VIEWPORTS.get(format, PLAYWRIGHT_VIEWPORTS["tiktok"])

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport_size=viewport)
            page.set_content(html_content, wait_until="networkidle")
            page.screenshot(path=output_path, full_page=False)
        finally:
            browser.close()

    return output_path


def generate_carousel_playwright(
    slides: list[dict],
    format: str,
    category: str,
    output_dir: str,
) -> list[str]:
    """Generate a full carousel set using Playwright HTML rendering.

    Args:
        slides: List of slide_data dicts (see render_slide_playwright for keys).
        format: "tiktok", "instagram_feed", or "instagram_square"
        category: "aruaru", "tenshoku", "kyuyo", "service", "trend"
        output_dir: Directory to save output PNGs.

    Returns:
        List of output PNG paths.
    """
    if not HAS_PLAYWRIGHT:
        raise RuntimeError(
            "Playwright rendering requires playwright and jinja2. "
            "Install with: pip install playwright jinja2 && playwright install chromium"
        )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    output_paths = []

    # Resolve template directory and create Jinja2 environment once
    templates_dir = Path(__file__).parent.parent / "templates"
    if not templates_dir.exists():
        raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("base.html")

    viewport = PLAYWRIGHT_VIEWPORTS.get(format, PLAYWRIGHT_VIEWPORTS["tiktok"])

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport_size=viewport)

            for i, slide_data in enumerate(slides):
                slide_num = slide_data.get("slide_number", i + 1)
                output_path = str(out / f"slide_{slide_num:02d}.png")

                template_vars = {
                    "format": format,
                    "category": category,
                    "slide_type": slide_data.get("slide_type", "body"),
                    "title_text": slide_data.get("title_text", ""),
                    "body_text": slide_data.get("body_text", ""),
                    "accent_text": slide_data.get("accent_text", ""),
                    "label_text": slide_data.get("label_text", ""),
                    "cta_text": slide_data.get("cta_text", ""),
                    "slide_number": slide_num,
                    "cta_button_text": slide_data.get("cta_button_text", ""),
                }

                html_content = template.render(**template_vars)
                page.set_content(html_content, wait_until="networkidle")
                page.screenshot(path=output_path, full_page=False)
                output_paths.append(output_path)
                print(f"  [Playwright] Slide {slide_num} -> {output_path}")

        except Exception as e:
            print(f"ERROR: Playwright rendering failed: {e}")
            raise
        finally:
            browser.close()

    return output_paths


def main():
    parser = argparse.ArgumentParser(
        description="TikTok/Instagram carousel slide generator v4.0 (category templates)",
    )
    parser.add_argument("--demo", action="store_true", help="Generate a demo carousel set for review")
    parser.add_argument("--demo-aruaru", action="store_true", help="Generate aruaru-themed demo")
    parser.add_argument("--demo-instagram", action="store_true", help="Generate Instagram Warm Coral design demo")
    parser.add_argument("--demo-all", action="store_true",
                       help="Generate demo carousels for ALL 5 category templates (v4.0)")
    parser.add_argument("--queue", help="Path to posting_queue.json")
    parser.add_argument("--output", default="content/generated/", help="Output base directory")
    parser.add_argument("--single-json", help="Generate carousel from a single slide JSON file")
    parser.add_argument("--background-only", action="store_true",
                       help="Generate background-only PNGs + text metadata JSON (for animated video)")
    parser.add_argument("--platform", choices=["tiktok", "instagram", "instagram_story"],
                       default="tiktok", help="Target platform for dimensions")
    parser.add_argument("--renderer", choices=["pillow", "playwright"], default="pillow",
                       help="Rendering engine: pillow (default) or playwright (HTML template)")

    args = parser.parse_args()

    # Validate Playwright availability if requested
    if args.renderer == "playwright" and not HAS_PLAYWRIGHT:
        print("ERROR: --renderer playwright requires playwright and jinja2.")
        print("  Install with: pip install playwright jinja2 && playwright install chromium")
        sys.exit(1)

    project_root = Path(__file__).parent.parent

    if args.demo_all:
        out = project_root / "content" / "generated" / "carousel_demo_v4"
        results = generate_demo_all(str(out))
        total = sum(len(v) for v in results.values())
        print(f"\nv4.0 demo complete. {total} slides across {len(results)} categories saved to {out}")

    elif args.demo:
        out = project_root / "content" / "generated" / "carousel_demo_v3"
        paths = generate_demo(str(out))
        print(f"\nDemo complete. {len(paths)} slides saved to {out}")

    elif args.demo_aruaru:
        out = project_root / "content" / "generated" / "carousel_demo_aruaru_v3"
        paths = generate_demo_aruaru(str(out))
        print(f"\nAruaru demo complete. {len(paths)} slides saved to {out}")

    elif args.demo_instagram:
        out = project_root / "content" / "generated" / "carousel_demo_instagram"
        paths = generate_demo_instagram(str(out))
        print(f"\nInstagram demo complete. {len(paths)} slides saved to {out}")

    elif args.queue:
        queue_path = Path(args.queue)
        if not queue_path.is_absolute():
            queue_path = project_root / queue_path
        output = Path(args.output)
        if not output.is_absolute():
            output = project_root / output
        count = generate_from_queue(str(queue_path), str(output))
        print(f"\nQueue processing complete. {count} sets generated.")

    elif args.single_json:
        json_path = Path(args.single_json)
        if not json_path.is_absolute():
            json_path = project_root / json_path
        content = _extract_carousel_content(str(json_path))
        if content:
            output = Path(args.output)
            if not output.is_absolute():
                output = project_root / output
            today = datetime.now().strftime("%Y%m%d")
            out_dir = output / f"carousel_{today}_{content['content_id']}"

            if args.background_only:
                result = generate_carousel_backgrounds(
                    content_id=content["content_id"],
                    hook=content["hook"],
                    slides=content["slides"],
                    output_dir=str(out_dir),
                    category=content["category"],
                    cta_type=content.get("cta_type", "soft"),
                    platform=args.platform,
                )
                print(f"\nBackgrounds: {len(result['backgrounds'])} files")
                print(f"Metadata: {result['metadata']}")
            elif args.renderer == "playwright":
                # Convert extracted content to Playwright slide_data format
                pw_format = _PLATFORM_TO_PW_FORMAT.get(args.platform, "tiktok")
                pw_category = CATEGORY_ALIASES.get(content["category"], content["category"])
                # Map Japanese category names to template category keys
                _cat_to_template = {
                    "あるある": "aruaru", "あるある×AI": "aruaru",
                    "転職・キャリア": "tenshoku", "給与・待遇": "kyuyo",
                    "サービス紹介": "service", "地域ネタ": "trend",
                }
                pw_cat_key = _cat_to_template.get(pw_category, content["category"])

                pw_slides = []
                # Slide 1: Hook
                pw_slides.append({
                    "slide_type": "hook",
                    "title_text": content["hook"],
                    "body_text": "",
                    "accent_text": "",
                    "label_text": pw_category,
                    "cta_text": "",
                    "slide_number": 1,
                    "cta_button_text": "",
                })
                # Slides 2-7: Body
                for j, s in enumerate(content["slides"][:6]):
                    pw_slides.append({
                        "slide_type": "body",
                        "title_text": s.get("title", ""),
                        "body_text": s.get("body", ""),
                        "accent_text": s.get("highlight_number", ""),
                        "label_text": s.get("title", ""),
                        "cta_text": "",
                        "slide_number": j + 2,
                        "cta_button_text": "",
                    })
                # Slide 8: CTA
                cta_text = "LINEで無料相談 →"
                if content.get("cta_type") == "hard":
                    cta_text = "今すぐLINE登録 →"
                pw_slides.append({
                    "slide_type": "cta",
                    "title_text": "あなたの転職、AIがサポート",
                    "body_text": "手数料10% × 24時間対応",
                    "accent_text": "AI",
                    "label_text": "",
                    "cta_text": cta_text,
                    "slide_number": len(pw_slides) + 1,
                    "cta_button_text": cta_text,
                })

                paths = generate_carousel_playwright(
                    slides=pw_slides,
                    format=pw_format,
                    category=pw_cat_key,
                    output_dir=str(out_dir),
                )
                print(f"\nPlaywright rendering complete. {len(paths)} slides saved to {out_dir}")
            else:
                generate_carousel(
                    content_id=content["content_id"],
                    hook=content["hook"],
                    slides=content["slides"],
                    output_dir=str(out_dir),
                    category=content["category"],
                    cta_type=content.get("cta_type", "soft"),
                    platform=args.platform,
                )
        else:
            print("ERROR: Could not extract carousel content from JSON.")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
