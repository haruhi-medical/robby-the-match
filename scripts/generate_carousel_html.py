#!/usr/bin/env python3
"""
Instagram カルーセル画像生成 — HTML/CSS + Playwright方式

HTMLテンプレートにテキストを注入し、Playwrightでスクリーンショット→PNG出力。
テンプレート5種 + 配色2系統で「静かなデータ型」デザインを自動生成。

Usage:
  python3 scripts/generate_carousel_html.py --test           # テスト画像1セット生成
  python3 scripts/generate_carousel_html.py --json data.json # JSONからカルーセル生成
"""

import json
import re
import argparse
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    raise ImportError("playwright未インストール: pip3 install playwright && python3 -m playwright install chromium")

PROJECT_DIR = Path(__file__).parent.parent
TEMPLATE_DIR = PROJECT_DIR / "content" / "html_templates"
OUTPUT_DIR = PROJECT_DIR / "content" / "generated"

# パレット: 王道フェミニン（ダスティピンク × ラベンダー × ベージュ）
PALETTE = {
    "primary": "#C27BA0",           # ダスティピンク
    "primary_light": "#F5E6EF",     # ペールピンク
    "accent": "#7B68AE",            # ラベンダー
    "accent_light": "#EDE8F5",      # ペールラベンダー
    "background": "#FFF9F7",        # ウォームホワイト
    "text_primary": "#3D3535",      # ダークブラウン
    "text_secondary": "#8C7E7E",    # モーブグレー
    "dot_inactive": "#D9CCCC",
    "brand_name": "神奈川ナース転職",
    "brand_tagline": "モヤモヤに、数字をくれる場所。",
}

# Hook slide: ダスティピンク背景（配色A）
HOOK_COLORS_TEAL = {
    "bg_color": "#C27BA0",
    "hook_text_color": "#FFFFFF",
    "sub_text_color": "rgba(255,255,255,0.75)",
    "swipe_bar_color": "#7B68AE",
    "dot_inactive_hook": "rgba(255,255,255,0.35)",
    "dot_active_hook": "#FFFFFF",
}

# Hook slide: ラベンダー背景（配色B）
HOOK_COLORS_CORAL = {
    "bg_color": "#7B68AE",
    "hook_text_color": "#FFFFFF",
    "sub_text_color": "rgba(255,255,255,0.75)",
    "swipe_bar_color": "#C27BA0",
    "dot_inactive_hook": "rgba(255,255,255,0.35)",
    "dot_active_hook": "#FFFFFF",
}


def render_template(template_path: Path, variables: dict) -> str:
    """Simple template rendering — replace {{var}} with values, handle {{#if}}."""
    html = template_path.read_text(encoding="utf-8")

    def resolve_if(match):
        var_name = match.group(1)
        content = match.group(2)
        if variables.get(var_name):
            return content
        return ""
    html = re.sub(r'\{\{#if (\w+)\}\}(.*?)\{\{/if\}\}', resolve_if, html, flags=re.DOTALL)

    for key, value in variables.items():
        html = html.replace("{{" + key + "}}", str(value))
    return html


def make_dots_html(total: int, current: int) -> str:
    """Generate progress dots HTML."""
    dots = []
    for i in range(1, total + 1):
        cls = "dot active" if i == current else "dot"
        dots.append(f'<div class="{cls}"></div>')
    return "\n".join(dots)


def auto_hook_font_size(text: str) -> int:
    """Choose font size based on hook text length.
    Max width is ~920px. At font-weight 900, roughly:
    72px = ~12 chars/line, 56px = ~16 chars/line, 42px = ~21 chars/line
    """
    length = len(text.replace("\n", ""))
    if length <= 12:
        return 72
    elif length <= 16:
        return 60
    elif length <= 21:
        return 52
    elif length <= 28:
        return 46
    else:
        return 40


def smart_line_break(text: str, max_chars_per_line: int = 18) -> str:
    """Insert <br> at natural break points for Japanese text.
    Avoids breaking in the middle of words/phrases.
    Break at: 、。？！・ or after particles (は/が/を/に/で/と/の/も/へ/から/まで/より)
    """
    if "\n" in text:
        # Already has manual line breaks
        return text.replace("\n", "<br>")

    if len(text) <= max_chars_per_line:
        return text

    # Natural break points (higher priority first)
    break_after = ["、", "。", "？", "！", "…", "・"]
    # Particles to break after (「の」は除外 — 「本当の理由」等が割れる)
    particles = ["は", "が", "を", "に", "で", "と", "も", "へ"]

    lines = []
    remaining = text

    while len(remaining) > max_chars_per_line:
        # Look for a natural break point within the line
        best_break = -1

        # First try: punctuation breaks
        for i in range(min(len(remaining), max_chars_per_line + 3), max(0, max_chars_per_line // 2), -1):
            if i < len(remaining) and remaining[i - 1] in break_after:
                best_break = i
                break

        # Second try: particle breaks (less ideal)
        if best_break == -1:
            for i in range(min(len(remaining), max_chars_per_line + 2), max(0, max_chars_per_line // 2), -1):
                if i < len(remaining) and remaining[i - 1] in particles:
                    best_break = i
                    break

        # Last resort: break at max_chars_per_line
        if best_break == -1:
            best_break = max_chars_per_line

        lines.append(remaining[:best_break])
        remaining = remaining[best_break:]

    if remaining:
        lines.append(remaining)

    return "<br>".join(lines)


def generate_carousel(slides_data: list, output_dir: Path, browser=None, color_scheme="teal"):
    """Generate a full carousel from slide data.

    slides_data: list of dicts, each with:
      - type: "hook" | "content" | "data" | "list" | "cta"
      - For hook: hook_text, sub_text (optional)
      - For content: slide_number, title, body, highlight (optional), source (optional)
      - For data: label, number, unit, description, source (optional), comparisons (optional)
      - For list: title, items (list of {label, desc})
      - For cta: summary_items (list), cta_text, button_text (optional), cta_sub (optional)

    color_scheme: "teal" or "coral" — hook slide background color
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(slides_data)

    hook_colors = HOOK_COLORS_TEAL if color_scheme == "teal" else HOOK_COLORS_CORAL

    own_browser = browser is None
    if own_browser:
        pw = sync_playwright().start()
        browser = pw.chromium.launch()

    page = browser.new_page(
        viewport={"width": 1080, "height": 1350},
        device_scale_factor=1,
    )

    generated = []
    for idx, slide in enumerate(slides_data):
        slide_num = idx + 1
        slide_type = slide.get("type", "content")
        dots_html = make_dots_html(total, slide_num)

        variables = {**PALETTE, "dots_html": dots_html}

        if slide_type == "hook":
            template = TEMPLATE_DIR / "slide_hook.html"
            variables.update(hook_colors)
            hook_text = slide.get("hook_text", "")
            # Hookのmax_chars_per_lineはフォントサイズに合わせる
            fs = auto_hook_font_size(hook_text)
            # 920px幅, font-weight:900 の日本語は1文字≈フォントサイズ*0.95
            chars_per_line = int(920 / (fs * 0.95))
            variables["hook_html"] = smart_line_break(hook_text, max_chars_per_line=chars_per_line)
            variables["hook_font_size"] = str(auto_hook_font_size(hook_text))
            variables["sub_text"] = slide.get("sub_text", "")

        elif slide_type == "content":
            template = TEMPLATE_DIR / "slide_content.html"
            variables["slide_number"] = str(slide.get("slide_number", slide_num))
            variables["title"] = slide.get("title", "")
            body = slide.get("body", "")
            variables["body_html"] = body.replace("\n", "<br>")
            variables["highlight"] = slide.get("highlight", "")
            variables["source"] = slide.get("source", "")

        elif slide_type == "data":
            template = TEMPLATE_DIR / "slide_data.html"
            variables["label"] = slide.get("label", "")
            variables["number"] = str(slide.get("number", ""))
            variables["unit"] = slide.get("unit", "")
            variables["description"] = slide.get("description", "").replace("\n", "<br>")
            variables["source"] = slide.get("source", "")
            # Build comparison cards
            comps = slide.get("comparisons", [])
            if comps:
                comp_html = ""
                for c in comps:
                    active = " active" if c.get("active") else ""
                    comp_html += f'<div class="comp-item{active}">'
                    comp_html += f'<div class="comp-label">{c["label"]}</div>'
                    comp_html += f'<div class="comp-value">{c["value"]}</div>'
                    comp_html += '</div>'
                variables["comparison"] = comp_html
            else:
                variables["comparison"] = ""

        elif slide_type == "list":
            template = TEMPLATE_DIR / "slide_list.html"
            variables["title"] = slide.get("title", "")
            items = slide.get("items", [])
            items_html = ""
            for i, item in enumerate(items):
                icon = item.get("icon", str(i + 1))
                items_html += f'<div class="list-item">'
                items_html += f'<div class="list-icon">{icon}</div>'
                items_html += f'<div class="list-content">'
                items_html += f'<div class="list-label">{item["label"]}</div>'
                if item.get("desc"):
                    items_html += f'<div class="list-desc">{item["desc"]}</div>'
                items_html += '</div></div>'
            variables["list_items_html"] = items_html

        elif slide_type == "cta":
            template = TEMPLATE_DIR / "slide_cta.html"
            items = slide.get("summary_items", [])
            variables["summary_items_html"] = "\n".join(
                f"<li>{item}</li>" for item in items
            )
            variables["cta_text"] = slide.get("cta_text", "").replace("\n", "<br>")
            btn = slide.get("button_text", "")
            if btn:
                variables["show_button"] = "true"
                variables["button_text"] = btn
            variables["cta_sub"] = slide.get("cta_sub", "")

        html = render_template(template, variables)
        page.set_content(html, wait_until="networkidle")
        page.wait_for_timeout(800)

        out_path = output_dir / f"slide_{slide_num:02d}.png"
        page.screenshot(path=str(out_path), type="png")
        generated.append(out_path)
        print(f"  [HTML] slide_{slide_num:02d}.png ({slide_type})")

    page.close()
    if own_browser:
        browser.close()
        pw.stop()

    return generated


def test_generate():
    """Generate test carousels — both color schemes."""

    # テストデータ: 「静かなデータ型」— 共感フック × データ本文 × 静かなCTA
    test_data = [
        {
            "type": "hook",
            "hook_text": "夜勤5回で手取り25万。\nこれって普通？",
            "sub_text": "神奈川の看護師給与データで検証",
        },
        {
            "type": "data",
            "label": "神奈川県 看護師の平均年収",
            "number": "520",
            "unit": "万円",
            "description": "全国平均508万円をやや上回るが、\n東京都（約550万円）には及ばない",
            "source": "出典: 厚労省 賃金構造基本統計調査",
            "comparisons": [
                {"label": "全国平均", "value": "508万"},
                {"label": "神奈川", "value": "520万", "active": True},
                {"label": "東京", "value": "550万"},
            ],
        },
        {
            "type": "content",
            "slide_number": 3,
            "title": "夜勤手当の相場は？",
            "body": "二交代制の夜勤手当は\n1回あたり<b>8,000〜12,000円</b>が相場。\n\n月5回なら<b>4〜6万円</b>。\nなくなると手取り5万円減。",
            "highlight": "「夜勤やめたいけど給料が怖い」\nが転職を迷う最大の理由",
            "source": "出典: 日本看護協会 実態調査",
        },
        {
            "type": "list",
            "title": "日勤のみで年収を維持する方法",
            "items": [
                {"icon": "🏠", "label": "訪問看護", "desc": "オンコール手当で補填できる"},
                {"icon": "🏥", "label": "クリニック", "desc": "残業手当が充実のところを選ぶ"},
                {"icon": "🏢", "label": "企業看護師", "desc": "土日祝休み+福利厚生◎"},
                {"icon": "🤝", "label": "介護施設", "desc": "管理者手当で年収維持"},
            ],
        },
        {
            "type": "cta",
            "summary_items": [
                "神奈川の看護師平均年収は約520万",
                "夜勤手当は月4〜6万。減ると痛い",
                "でも日勤のみで維持する方法もある",
            ],
            "cta_text": "あなたの給料、\n相場と比べてどう？",
            "button_text": "LINEで相場を見る",
            "cta_sub": "3分で終わる・しつこい連絡なし",
        },
    ]

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # 配色A: ティール
    out_a = OUTPUT_DIR / f"html_teal_{timestamp}"
    print(f"[HTML Carousel] 配色A（ティール）生成中...")
    start = time.time()
    files_a = generate_carousel(test_data, out_a, color_scheme="teal")

    # 配色B: コーラル
    out_b = OUTPUT_DIR / f"html_coral_{timestamp}"
    print(f"[HTML Carousel] 配色B（コーラル）生成中...")
    files_b = generate_carousel(test_data, out_b, color_scheme="coral")

    elapsed = time.time() - start
    print(f"[HTML Carousel] {len(files_a) + len(files_b)}枚生成完了 ({elapsed:.1f}秒)")
    print(f"[HTML Carousel] ティール: {out_a}")
    print(f"[HTML Carousel] コーラル: {out_b}")
    return files_a, files_b


def main():
    parser = argparse.ArgumentParser(description="HTML/CSS カルーセル画像生成")
    parser.add_argument("--test", action="store_true", help="テスト画像生成")
    parser.add_argument("--json", type=str, help="JSONファイルからカルーセル生成")
    parser.add_argument("--output-dir", type=str, help="出力ディレクトリ")
    parser.add_argument("--color", choices=["teal", "coral"], default="teal", help="配色")
    args = parser.parse_args()

    if args.test:
        test_generate()
    elif args.json:
        with open(args.json) as f:
            data = json.load(f)
        slides = data.get("slides", data) if isinstance(data, dict) else data
        out_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR / Path(args.json).stem
        generate_carousel(slides, out_dir, color_scheme=args.color)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
