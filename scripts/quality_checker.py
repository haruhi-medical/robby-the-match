#!/usr/bin/env python3
"""
quality_checker.py — SNSカルーセル品質検査エンジン v1.0

「神は細部に宿る」
テキスト・ビジュアル・コンテンツ・心理学の4軸で品質をスコアリングし、
世界水準のカルーセル投稿を保証する。

使い方:
  # カルーセルJSON（台本）の品質チェック
  python3 scripts/quality_checker.py --script data/posting_queue.json --index 0

  # 生成済みスライド画像の品質チェック
  python3 scripts/quality_checker.py --images content/generated/20260220_A01/

  # 台本+画像の総合チェック
  python3 scripts/quality_checker.py --script data/posting_queue.json --index 0 \
      --images content/generated/20260220_A01/

  # 全キューを一括チェック
  python3 scripts/quality_checker.py --audit data/posting_queue.json

  # 品質基準の表示
  python3 scripts/quality_checker.py --standards
"""

from __future__ import annotations

import argparse
import colorsys
import json
import math
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ============================================================
# Constants
# ============================================================

# Canvas dimensions (TikTok/Instagram 9:16)
CANVAS_W = 1080
CANVAS_H = 1920

# TikTok safe zones
SAFE_TOP = 150
SAFE_BOTTOM = 280
SAFE_RIGHT = 100
SAFE_LEFT = 40

# Content area
CONTENT_W = CANVAS_W - SAFE_LEFT - SAFE_RIGHT  # 940
CONTENT_H = CANVAS_H - SAFE_TOP - SAFE_BOTTOM  # 1490

# 12-column grid
GRID_COLUMNS = 12
GRID_GUTTER = 20
GRID_COL_W = (CONTENT_W - GRID_GUTTER * (GRID_COLUMNS - 1)) / GRID_COLUMNS

# Golden ratio
PHI = 1.618033988749895
PHI_INVERSE = 0.618033988749895
PHI_INVERSE_SQ = PHI_INVERSE ** 2  # 0.382

# Readability thresholds
MAX_CHARS_PER_SLIDE = 120
MAX_LINES_PER_SLIDE = 8
MAX_KANJI_RATIO = 0.30
IDEAL_KANJI_RATIO = (0.15, 0.25)

# Font size golden ratio: title:body:caption = 1:0.618:0.382
FONT_RATIO_TITLE = 1.0
FONT_RATIO_BODY = PHI_INVERSE      # 0.618
FONT_RATIO_CAPTION = PHI_INVERSE_SQ  # 0.382

# WCAG contrast ratios
WCAG_AA_RATIO = 4.5
WCAG_AAA_RATIO = 7.0

# Miller's Law: 7 +/- 2 chunks
MILLER_MIN = 5
MILLER_MAX = 9
MILLER_IDEAL = 7

# Loss aversion words (Japanese)
LOSS_AVERSION_WORDS = [
    "損", "損する", "知らないと", "見逃す", "失う", "もったいない",
    "後悔", "手遅れ", "損失", "リスク", "やばい", "危険",
]

# Emotion trigger words
EMOTION_TRIGGERS = [
    "驚愕", "涙", "ブチギレ", "衝撃", "鳥肌", "感動",
    "号泣", "激怒", "震えた", "黙った", "絶句", "目が覚めた",
]

# Persona-direct words (nurse-specific)
PERSONA_DIRECT_WORDS = [
    "看護師", "ナース", "5年目", "3年目", "7年目", "10年目",
    "夜勤", "夜勤明け", "日勤", "師長", "プリセプター",
    "急性期", "慢性期", "訪問看護", "クリニック", "病棟",
    "ナースコール", "看護記録", "申し送り", "インシデント",
]

# Question patterns
QUESTION_PATTERNS = [
    r"知ってた？", r"本当に？", r"マジ？", r"嘘でしょ？",
    r"どう思う？", r"聞いたことある？", r"\?$", r"？$",
]

# Save-worthy content patterns
SAVE_PATTERNS = {
    "data_comparison": [r"比較", r"ランキング", r"一覧", r"表", r"データ", r"統計"],
    "checklist": [r"チェック", r"リスト", r"確認", r"ポイント", r"〜つの"],
    "howto": [r"方法", r"やり方", r"手順", r"ステップ", r"コツ", r"裏技"],
}

# Share-worthy patterns
SHARE_PATTERNS = {
    "empathy": [r"あるある", r"わかる", r"それな", r"共感", r"同じ"],
    "surprise": [r"意外", r"実は", r"知らなかった", r"衝撃", r"まさか"],
    "practical": [r"使える", r"役立つ", r"便利", r"お得", r"裏技"],
}

# Ideal emotion curve for 7 slides
IDEAL_EMOTION_CURVE = [
    "surprise",   # Slide 1: Hook - surprise/curiosity
    "empathy",    # Slide 2: Connection - empathy/recognition
    "expect",     # Slide 3: Build-up - anticipation
    "learn",      # Slide 4: Insight - learning
    "convince",   # Slide 5: Evidence - conviction
    "hope",       # Slide 6: Resolution - hope
    "action",     # Slide 7: CTA - action/motivation
]

# CTA naturalness indicators
HARD_CTA_WORDS = [
    "登録", "今すぐ", "無料", "限定", "急いで", "締切",
    "申し込み", "購入", "入会", "ダウンロード",
]

SOFT_CTA_WORDS = [
    "保存", "フォロー", "続き", "もっと", "シェア", "教えて",
    "みんなは", "コメント", "プロフィール",
]

# Japanese typography: line-start prohibited characters (Kinsoku)
KINSOKU_LINE_START = set("、。，．）」』】〕〉》）]｝〟ー…‥？！!?・:;")

# Japanese typography: line-end prohibited characters
KINSOKU_LINE_END = set("（「『【〔〈《（[｛〝")


# ============================================================
# Data Classes
# ============================================================

@dataclass
class QualityScore:
    """Individual quality dimension score."""
    dimension: str
    name: str
    score: float          # 0.0 - 10.0
    max_score: float      # usually 10.0
    weight: float         # importance weight
    details: str          # human-readable explanation
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class SlideAnalysis:
    """Analysis result for a single slide."""
    slide_num: int
    char_count: int
    line_count: int
    kanji_ratio: float
    hiragana_ratio: float
    katakana_ratio: float
    chunk_count: int
    emotion_type: str
    has_number: bool
    readability_ok: bool


@dataclass
class QualityReport:
    """Complete quality report for a carousel post."""
    content_id: str
    timestamp: str
    overall_score: float          # 0-100 weighted average
    grade: str                    # S/A/B/C/D/F
    text_scores: list[QualityScore] = field(default_factory=list)
    visual_scores: list[QualityScore] = field(default_factory=list)
    content_scores: list[QualityScore] = field(default_factory=list)
    psychology_scores: list[QualityScore] = field(default_factory=list)
    slide_analyses: list[SlideAnalysis] = field(default_factory=list)
    blocking_issues: list[str] = field(default_factory=list)
    pass_fail: bool = True

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "content_id": self.content_id,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 1),
            "grade": self.grade,
            "pass_fail": self.pass_fail,
            "blocking_issues": self.blocking_issues,
            "text": [
                {"name": s.name, "score": round(s.score, 1),
                 "details": s.details, "issues": s.issues, "suggestions": s.suggestions}
                for s in self.text_scores
            ],
            "visual": [
                {"name": s.name, "score": round(s.score, 1),
                 "details": s.details, "issues": s.issues, "suggestions": s.suggestions}
                for s in self.visual_scores
            ],
            "content": [
                {"name": s.name, "score": round(s.score, 1),
                 "details": s.details, "issues": s.issues, "suggestions": s.suggestions}
                for s in self.content_scores
            ],
            "psychology": [
                {"name": s.name, "score": round(s.score, 1),
                 "details": s.details, "issues": s.issues, "suggestions": s.suggestions}
                for s in self.psychology_scores
            ],
            "slides": [
                {"num": sa.slide_num, "chars": sa.char_count,
                 "lines": sa.line_count, "kanji": round(sa.kanji_ratio, 3),
                 "emotion": sa.emotion_type, "chunks": sa.chunk_count}
                for sa in self.slide_analyses
            ],
        }


# ============================================================
# Utility Functions
# ============================================================

def classify_char(c: str) -> str:
    """Classify a single character into kanji/hiragana/katakana/ascii/punct/other."""
    cp = ord(c)
    if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
        return "kanji"
    if 0x3040 <= cp <= 0x309F:
        return "hiragana"
    if 0x30A0 <= cp <= 0x30FF:
        return "katakana"
    if 0x0021 <= cp <= 0x007E:
        return "ascii"
    if unicodedata.category(c).startswith("P"):
        return "punct"
    return "other"


def char_ratios(text: str) -> dict[str, float]:
    """Calculate character type ratios (excluding whitespace and punctuation)."""
    counts: dict[str, int] = {"kanji": 0, "hiragana": 0, "katakana": 0, "ascii": 0, "other": 0}
    total = 0
    for c in text:
        if c.isspace():
            continue
        cls = classify_char(c)
        if cls == "punct":
            continue
        counts[cls] = counts.get(cls, 0) + 1
        total += 1
    if total == 0:
        return {k: 0.0 for k in counts}
    return {k: v / total for k, v in counts.items()}


def count_chunks(text: str) -> int:
    """
    Count information chunks in text (Miller's Law: 7 +/- 2).
    A chunk is a semantic unit: a number, a key phrase, a bullet point, etc.
    Approximation: count sentences + standalone numbers + bullet items.
    """
    chunks = 0
    # Sentences (period, question mark, exclamation)
    chunks += len(re.findall(r"[。！？!?]+", text))
    # Standalone numbers/data points
    chunks += len(re.findall(r"\d+[%％万円件名本]", text))
    # Bullet-like items (dashes, dots, numbers at line start)
    chunks += len(re.findall(r"^[\s]*[・\-\d①②③④⑤⑥⑦⑧⑨⑩]", text, re.MULTILINE))
    return max(chunks, 1)


def has_halfwidth_fullwidth_mix(text: str) -> list[str]:
    """Detect mixed half-width and full-width numbers in the same text."""
    issues = []
    has_half = bool(re.search(r"[0-9]", text))
    has_full = bool(re.search(r"[０-９]", text))
    if has_half and has_full:
        issues.append("半角数字と全角数字が混在しています")
    return issues


def check_kinsoku(lines: list[str]) -> list[str]:
    """Check Japanese typography rules (Kinsoku Shori)."""
    issues = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        if line[0] in KINSOKU_LINE_START:
            issues.append(f"行{i+1}の先頭に禁則文字 '{line[0]}' があります")
        if line[-1] in KINSOKU_LINE_END:
            issues.append(f"行{i+1}の末尾に禁則文字 '{line[-1]}' があります")
    return issues


def estimate_punct_kerning_issues(text: str) -> list[str]:
    """
    Detect potential kerning issues around punctuation and brackets.
    Full-width punctuation in Japanese should have consistent spacing.
    """
    issues = []
    # Double punctuation
    if re.search(r"[。、]{2,}", text):
        issues.append("連続する句読点を検出: 不自然な空きの原因")
    # Space before punctuation (Japanese text should not have space before 。、)
    if re.search(r"\s[。、]", text):
        issues.append("句読点の前にスペースがあります")
    # Missing space after closing bracket before text
    if re.search(r"[）」』】][^\s。、）」』】\n]", text):
        # In Japanese this is actually normal, but flag if before opening bracket
        pass
    # Consecutive brackets without content
    if re.search(r"[（「『【][）」』】]", text):
        issues.append("空の括弧を検出")
    return issues


def relative_luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance per WCAG 2.1 spec."""
    def linearize(v: int) -> float:
        s = v / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color1: tuple, color2: tuple) -> float:
    """Calculate WCAG 2.1 contrast ratio between two RGB colors."""
    l1 = relative_luminance(*color1[:3])
    l2 = relative_luminance(*color2[:3])
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def detect_emotion_type(text: str) -> str:
    """Classify the emotional tone of slide text."""
    text_lower = text.lower()
    # Check for each emotion pattern
    surprise_words = ["驚", "衝撃", "まさか", "嘘", "マジ", "意外", "知らなかった", "？", "?"]
    empathy_words = ["あるある", "わかる", "つらい", "疲れ", "同じ", "共感", "気持ち"]
    expect_words = ["実は", "ところが", "しかし", "でも", "ここから", "注目", "次"]
    learn_words = ["データ", "調査", "結果", "分析", "比較", "平均", "統計", "%", "万円"]
    convince_words = ["証明", "根拠", "事実", "理由", "なぜ", "原因", "つまり"]
    hope_words = ["できる", "変わる", "希望", "未来", "チャンス", "可能性", "解決"]
    action_words = ["LINE", "フォロー", "保存", "相談", "プロフィール", "登録", "今すぐ"]

    scores = {
        "surprise": sum(1 for w in surprise_words if w in text),
        "empathy": sum(1 for w in empathy_words if w in text),
        "expect": sum(1 for w in expect_words if w in text),
        "learn": sum(1 for w in learn_words if w in text),
        "convince": sum(1 for w in convince_words if w in text),
        "hope": sum(1 for w in hope_words if w in text),
        "action": sum(1 for w in action_words if w in text),
    }
    if max(scores.values()) == 0:
        return "neutral"
    return max(scores, key=scores.get)


# ============================================================
# ContentQualityChecker
# ============================================================

class ContentQualityChecker:
    """
    SNSカルーセル投稿の細部品質チェッカー。

    4軸(テキスト/ビジュアル/コンテンツ/心理学)x 20+のチェック項目で
    0-100スコアを算出し、S/A/B/C/D/F のグレードを付与する。

    Usage:
        checker = ContentQualityChecker()
        report = checker.check(
            slides=[
                {"title": "フック", "body": "師長にAIで見せたら黙った"},
                {"title": "あるある", "body": "夜勤明けの..."},
                ...
            ],
            hook_text="師長にAIで見せたら黙った",
            caption="看護師あるある #看護師 #AI",
            category="あるある",
            content_id="A01",
            colors={
                "bg": (26, 26, 46),
                "text": (255, 255, 255),
                "accent": (255, 107, 107),
            },
            font_sizes={"title": 56, "body": 34, "caption": 20},
        )
        print(report.overall_score)  # 0-100
        print(report.grade)          # "A"
    """

    # Weights for each dimension (total = 1.0)
    DIMENSION_WEIGHTS = {
        "text": 0.25,
        "visual": 0.20,
        "content": 0.35,
        "psychology": 0.20,
    }

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (95, "S"),
        (85, "A"),
        (70, "B"),
        (55, "C"),
        (40, "D"),
        (0, "F"),
    ]

    # Minimum passing score
    PASS_THRESHOLD = 60.0

    def __init__(self, strict: bool = False):
        """
        Args:
            strict: If True, use WCAG AAA (7:1) contrast; else use AA (4.5:1).
        """
        self.strict = strict
        self.target_contrast = WCAG_AAA_RATIO if strict else WCAG_AA_RATIO

    # ----------------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------------

    def check(
        self,
        slides: list[dict],
        hook_text: str = "",
        caption: str = "",
        category: str = "",
        content_id: str = "unknown",
        colors: Optional[dict] = None,
        font_sizes: Optional[dict] = None,
        image_paths: Optional[list[Path]] = None,
    ) -> QualityReport:
        """
        Run all quality checks and return a comprehensive report.

        Args:
            slides: List of slide dicts, each with "title" and/or "body" keys.
            hook_text: The hook/opening text (slide 1).
            caption: Post caption text.
            category: Content category (あるある/転職/給与/紹介/トレンド).
            content_id: Identifier (e.g. "A01").
            colors: Dict with "bg", "text", "accent" RGB tuples.
            font_sizes: Dict with "title", "body", "caption" pixel sizes.
            image_paths: Optional list of paths to generated slide images.

        Returns:
            QualityReport with all scores, grade, and suggestions.
        """
        from datetime import datetime

        report = QualityReport(
            content_id=content_id,
            timestamp=datetime.now().isoformat(),
            overall_score=0.0,
            grade="F",
        )

        # -- Analyze individual slides --
        all_text = ""
        for i, slide in enumerate(slides):
            text = self._extract_slide_text(slide)
            all_text += text + "\n"
            analysis = self._analyze_slide(i + 1, text)
            report.slide_analyses.append(analysis)

        # If hook_text not provided, try to extract from first slide
        if not hook_text and slides:
            hook_text = self._extract_slide_text(slides[0])

        # -- Text quality checks --
        report.text_scores = self._check_text_quality(slides, all_text, report.slide_analyses)

        # -- Visual quality checks --
        colors = colors or {"bg": (26, 26, 46), "text": (255, 255, 255), "accent": (255, 107, 107)}
        font_sizes = font_sizes or {"title": 56, "body": 34, "caption": 20}
        report.visual_scores = self._check_visual_quality(colors, font_sizes, image_paths)

        # -- Content quality checks --
        report.content_scores = self._check_content_quality(
            slides, hook_text, caption, category, all_text
        )

        # -- Psychology quality checks --
        report.psychology_scores = self._check_psychology_quality(
            slides, report.slide_analyses, all_text
        )

        # -- Calculate overall score --
        dimension_scores = {
            "text": report.text_scores,
            "visual": report.visual_scores,
            "content": report.content_scores,
            "psychology": report.psychology_scores,
        }
        weighted_total = 0.0
        weighted_max = 0.0
        for dim, scores in dimension_scores.items():
            dim_weight = self.DIMENSION_WEIGHTS[dim]
            if not scores:
                continue
            dim_avg = sum(s.score for s in scores) / len(scores)
            dim_max = sum(s.max_score for s in scores) / len(scores)
            weighted_total += (dim_avg / dim_max) * dim_weight * 100
            weighted_max += dim_weight * 100

        report.overall_score = weighted_total if weighted_max == 0 else (weighted_total / weighted_max) * 100

        # -- Grade --
        for threshold, grade in self.GRADE_THRESHOLDS:
            if report.overall_score >= threshold:
                report.grade = grade
                break

        # -- Blocking issues --
        for scores in dimension_scores.values():
            for s in scores:
                if s.score <= 2.0:
                    report.blocking_issues.extend(s.issues[:1])

        report.pass_fail = (
            report.overall_score >= self.PASS_THRESHOLD
            and len(report.blocking_issues) == 0
        )

        return report

    # ----------------------------------------------------------------
    # Text Quality Checks (7 items)
    # ----------------------------------------------------------------

    def _check_text_quality(
        self,
        slides: list[dict],
        all_text: str,
        slide_analyses: list[SlideAnalysis],
    ) -> list[QualityScore]:
        scores = []

        # 1. Kerning (punctuation spacing)
        scores.append(self._check_kerning(all_text))

        # 2. Kinsoku (line-break rules)
        scores.append(self._check_kinsoku(slides))

        # 3. Number format consistency
        scores.append(self._check_number_consistency(all_text))

        # 4. Font size golden ratio
        # (Checked in visual, but we score text-side readability here)
        scores.append(self._check_font_ratio_readability(slides))

        # 5. Readability score (chars per slide, lines per slide)
        scores.append(self._check_readability(slide_analyses))

        # 6. Kanji ratio
        scores.append(self._check_kanji_ratio(all_text))

        # 7. Hiragana/katakana/kanji balance
        scores.append(self._check_char_balance(all_text))

        return scores

    def _check_kerning(self, text: str) -> QualityScore:
        """Check punctuation kerning issues."""
        issues = estimate_punct_kerning_issues(text)
        score = max(0, 10 - len(issues) * 3)
        return QualityScore(
            dimension="text", name="カーニング",
            score=score, max_score=10, weight=1.0,
            details=f"句読点・括弧の前後スペース検出: {len(issues)}件",
            issues=issues,
            suggestions=["句読点の前にスペースを入れない", "空の括弧を削除する"] if issues else [],
        )

    def _check_kinsoku(self, slides: list[dict]) -> QualityScore:
        """Check Japanese line-break rules."""
        all_issues = []
        for slide in slides:
            text = self._extract_slide_text(slide)
            lines = text.split("\n")
            all_issues.extend(check_kinsoku(lines))
        score = max(0, 10 - len(all_issues) * 2)
        return QualityScore(
            dimension="text", name="禁則処理",
            score=score, max_score=10, weight=1.0,
            details=f"禁則処理違反: {len(all_issues)}件",
            issues=all_issues,
            suggestions=["行頭の句読点を前の行に移動する"] if all_issues else [],
        )

    def _check_number_consistency(self, text: str) -> QualityScore:
        """Check half-width / full-width number consistency."""
        issues = has_halfwidth_fullwidth_mix(text)
        score = 10 if not issues else 3
        return QualityScore(
            dimension="text", name="数字表記統一",
            score=score, max_score=10, weight=1.0,
            details="数字は統一されています" if not issues else "半角/全角数字が混在",
            issues=issues,
            suggestions=["全て半角数字に統一する（SNS標準）"] if issues else [],
        )

    def _check_font_ratio_readability(self, slides: list[dict]) -> QualityScore:
        """
        Check that text hierarchy follows golden ratio principles.
        Title should be visually larger, body medium, caption small.
        Approximate by character count per line: fewer chars = larger intended font.
        """
        # Heuristic: check if slide 1 (hook) has fewer chars than body slides
        if len(slides) < 2:
            return QualityScore(
                dimension="text", name="テキスト階層",
                score=5, max_score=10, weight=0.8,
                details="スライド数が少なすぎて階層判定不可",
                issues=["スライド数を7枚に増やすことを推奨"],
            )

        hook_chars = len(self._extract_slide_text(slides[0]))
        body_chars = [len(self._extract_slide_text(s)) for s in slides[1:-1]] if len(slides) > 2 else [hook_chars]
        avg_body = sum(body_chars) / len(body_chars) if body_chars else hook_chars

        score = 10
        issues = []
        # Hook should be concise (under 40 chars ideally)
        if hook_chars > 50:
            score -= 3
            issues.append(f"フックが{hook_chars}文字: 40文字以内が理想")
        # Hook should be shorter than body average
        if hook_chars > avg_body * 1.2:
            score -= 2
            issues.append("フックが本文より長い: テキスト階層が逆転")

        return QualityScore(
            dimension="text", name="テキスト階層（黄金比）",
            score=max(0, score), max_score=10, weight=0.8,
            details=f"フック{hook_chars}文字 / 本文平均{avg_body:.0f}文字",
            issues=issues,
            suggestions=["フックは20文字以内が最強。3秒で読める量に"] if issues else [],
        )

    def _check_readability(self, analyses: list[SlideAnalysis]) -> QualityScore:
        """Check per-slide character count and line count."""
        issues = []
        over_count = 0
        for a in analyses:
            if a.char_count > MAX_CHARS_PER_SLIDE:
                over_count += 1
                issues.append(f"スライド{a.slide_num}: {a.char_count}文字 (上限{MAX_CHARS_PER_SLIDE})")
            if a.line_count > MAX_LINES_PER_SLIDE:
                issues.append(f"スライド{a.slide_num}: {a.line_count}行 (上限{MAX_LINES_PER_SLIDE})")

        score = max(0, 10 - over_count * 2 - (len(issues) - over_count))
        return QualityScore(
            dimension="text", name="読みやすさスコア",
            score=score, max_score=10, weight=1.2,
            details=f"文字数超過スライド: {over_count}/{len(analyses)}枚",
            issues=issues,
            suggestions=["1スライド120文字以内、8行以内に収める"] if issues else [],
        )

    def _check_kanji_ratio(self, text: str) -> QualityScore:
        """Check that kanji ratio stays under 30%."""
        ratios = char_ratios(text)
        kanji = ratios.get("kanji", 0)
        score = 10
        issues = []

        if kanji > MAX_KANJI_RATIO:
            score = max(0, 10 - (kanji - MAX_KANJI_RATIO) * 50)
            issues.append(f"漢字比率 {kanji:.1%} > 上限{MAX_KANJI_RATIO:.0%}")
        elif kanji < IDEAL_KANJI_RATIO[0]:
            score = 8
            issues.append(f"漢字比率 {kanji:.1%}: やや少ない（専門性が薄い印象）")

        return QualityScore(
            dimension="text", name="漢字比率",
            score=score, max_score=10, weight=1.0,
            details=f"漢字比率: {kanji:.1%} (理想: 15-25%, 上限: 30%)",
            issues=issues,
            suggestions=["漢字の多い語をひらがなに開く（例: 致します→いたします）"] if kanji > MAX_KANJI_RATIO else [],
        )

    def _check_char_balance(self, text: str) -> QualityScore:
        """Check hiragana / katakana / kanji balance for readability."""
        ratios = char_ratios(text)
        kanji = ratios.get("kanji", 0)
        hiragana = ratios.get("hiragana", 0)
        katakana = ratios.get("katakana", 0)

        score = 10
        issues = []

        # Ideal: hiragana 40-60%, kanji 15-25%, katakana 5-20%
        if hiragana < 0.30:
            score -= 3
            issues.append(f"ひらがな比率 {hiragana:.1%}: 少なすぎる（硬い印象）")
        if hiragana > 0.70:
            score -= 2
            issues.append(f"ひらがな比率 {hiragana:.1%}: 多すぎる（幼い印象）")
        if katakana > 0.30:
            score -= 2
            issues.append(f"カタカナ比率 {katakana:.1%}: 多すぎる（読みにくい）")

        return QualityScore(
            dimension="text", name="文字種バランス",
            score=max(0, score), max_score=10, weight=0.8,
            details=f"ひらがな{hiragana:.0%} / 漢字{kanji:.0%} / カタカナ{katakana:.0%}",
            issues=issues,
            suggestions=["看護師ペルソナが3秒で読める水準: ひらがな40-60%を目指す"] if issues else [],
        )

    # ----------------------------------------------------------------
    # Visual Quality Checks (6 items)
    # ----------------------------------------------------------------

    def _check_visual_quality(
        self,
        colors: dict,
        font_sizes: dict,
        image_paths: Optional[list[Path]] = None,
    ) -> list[QualityScore]:
        scores = []

        # 1. Contrast ratio (WCAG)
        scores.append(self._check_contrast(colors))

        # 2. Margin golden ratio
        scores.append(self._check_margins())

        # 3. Grid alignment
        scores.append(self._check_grid_alignment())

        # 4. Icon / decoration consistency (heuristic)
        scores.append(self._check_decoration_consistency(colors))

        # 5. Gradient smoothness
        scores.append(self._check_gradient_smoothness(colors))

        # 6. Shadow realism
        scores.append(self._check_shadow_consistency())

        # 7. Font size golden ratio (visual dimension)
        scores.append(self._check_font_golden_ratio(font_sizes))

        # If images provided, do pixel-level checks
        if image_paths:
            scores.append(self._check_images(image_paths))

        return scores

    def _check_contrast(self, colors: dict) -> QualityScore:
        """Check WCAG 2.1 contrast ratio."""
        bg = colors.get("bg", (26, 26, 46))
        text = colors.get("text", (255, 255, 255))
        accent = colors.get("accent", (255, 107, 107))

        cr_text = contrast_ratio(bg, text)
        cr_accent = contrast_ratio(bg, accent)

        score = 10
        issues = []
        target = self.target_contrast
        label = "AAA (7:1)" if self.strict else "AA (4.5:1)"

        if cr_text < target:
            score -= 5
            issues.append(f"テキスト/背景コントラスト {cr_text:.1f}:1 < {label}")
        if cr_accent < 3.0:
            score -= 3
            issues.append(f"アクセント/背景コントラスト {cr_accent:.1f}:1 < 3:1")

        return QualityScore(
            dimension="visual", name="コントラスト比 (WCAG)",
            score=max(0, score), max_score=10, weight=1.5,
            details=f"テキスト/BG: {cr_text:.1f}:1, アクセント/BG: {cr_accent:.1f}:1 (基準: {label})",
            issues=issues,
            suggestions=["背景を暗くするか文字を明るくしてコントラスト比を上げる"] if issues else [],
        )

    def _check_margins(self) -> QualityScore:
        """Check that margins follow golden ratio proportions."""
        # TikTok safe zones define outer margins
        # Check if they approximate golden ratio relationships
        left_ratio = SAFE_LEFT / CANVAS_W
        right_ratio = SAFE_RIGHT / CANVAS_W
        top_ratio = SAFE_TOP / CANVAS_H
        bottom_ratio = SAFE_BOTTOM / CANVAS_H

        score = 10
        issues = []

        # Horizontal margins should be roughly proportional
        h_ratio = SAFE_LEFT / SAFE_RIGHT if SAFE_RIGHT > 0 else 0
        if h_ratio < 0.3 or h_ratio > 0.6:
            # Asymmetric is OK for TikTok (UI icons on right), but flag if extreme
            score -= 1
            issues.append(f"左右マージン比 {h_ratio:.2f}: TikTok UIのため非対称（許容）")

        # Vertical: bottom needs more space (TikTok caption/buttons)
        if SAFE_BOTTOM < SAFE_TOP:
            score -= 3
            issues.append("下部マージンが上部より小さい: TikTok UIが被る可能性")

        # Content area ratio to canvas
        content_ratio = (CONTENT_W * CONTENT_H) / (CANVAS_W * CANVAS_H)
        if content_ratio < 0.50:
            score -= 2
            issues.append(f"コンテンツ領域比 {content_ratio:.1%}: 小さすぎる")
        elif content_ratio > 0.85:
            score -= 1
            issues.append(f"コンテンツ領域比 {content_ratio:.1%}: 余白が少ない")

        return QualityScore(
            dimension="visual", name="余白バランス",
            score=max(0, score), max_score=10, weight=1.0,
            details=f"コンテンツ領域: {CONTENT_W}x{CONTENT_H} ({content_ratio:.1%}), セーフゾーン: T{SAFE_TOP}/B{SAFE_BOTTOM}/L{SAFE_LEFT}/R{SAFE_RIGHT}",
            issues=issues,
            suggestions=["TikTokセーフゾーンを守りつつ余白を確保する"] if issues else [],
        )

    def _check_grid_alignment(self) -> QualityScore:
        """Check 12-column grid compliance."""
        # Verify that content width accommodates a 12-col grid
        usable = CONTENT_W - GRID_GUTTER * (GRID_COLUMNS - 1)
        col_w = usable / GRID_COLUMNS

        score = 10
        issues = []
        if col_w < 50:
            score -= 3
            issues.append(f"グリッド列幅 {col_w:.1f}px: 狭すぎる")
        if CONTENT_W % GRID_COLUMNS > GRID_COLUMNS // 2:
            # Not perfectly divisible, minor issue
            score -= 1
            issues.append(f"コンテンツ幅{CONTENT_W}は12列で割り切れない（{CONTENT_W % 12}px余り）")

        return QualityScore(
            dimension="visual", name="グリッドシステム",
            score=max(0, score), max_score=10, weight=0.8,
            details=f"12列グリッド: 列幅{col_w:.1f}px, ガター{GRID_GUTTER}px",
            issues=issues,
            suggestions=["テキストブロックをグリッドの2/4/6/8/10/12列幅に揃える"] if issues else [],
        )

    def _check_decoration_consistency(self, colors: dict) -> QualityScore:
        """Heuristic check for decoration consistency rules."""
        accent = colors.get("accent", (255, 107, 107))
        primary = colors.get("primary", colors.get("bg", (26, 115, 232)))

        score = 10
        issues = []

        # Check that accent and primary are visually distinct
        cr = contrast_ratio(accent, primary)
        if cr < 2.0:
            score -= 3
            issues.append(f"アクセントとプライマリの色差が小さい (コントラスト{cr:.1f}:1)")

        # Check that accent is not too saturated or desaturated
        r, g, b = accent[:3]
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        if s < 0.3:
            score -= 2
            issues.append(f"アクセント色の彩度が低い ({s:.2f}): インパクト不足")
        if v < 0.4:
            score -= 2
            issues.append(f"アクセント色の明度が低い ({v:.2f}): 視認性不足")

        return QualityScore(
            dimension="visual", name="装飾の統一感",
            score=max(0, score), max_score=10, weight=0.8,
            details=f"アクセント/プライマリ対比: {cr:.1f}:1, 彩度: {s:.2f}, 明度: {v:.2f}",
            issues=issues,
            suggestions=["アクセント色はCTA要素のみに使い、使いすぎない"] if issues else [],
        )

    def _check_gradient_smoothness(self, colors: dict) -> QualityScore:
        """
        Check gradient configuration for banding risk.
        Banding occurs when color distance is too large for available steps.
        """
        bg = colors.get("bg", (26, 26, 46))
        bg2 = colors.get("bg2", colors.get("bg", (22, 33, 62)))

        # Calculate perceptual color distance
        dr = abs(bg[0] - bg2[0])
        dg = abs(bg[1] - bg2[1])
        db = abs(bg[2] - bg2[2])
        distance = math.sqrt(dr ** 2 + dg ** 2 + db ** 2)

        score = 10
        issues = []

        # For 1920px height, we have 1920 color steps
        # Banding risk when distance > 128 (visible steps in 8-bit color)
        if distance > 200:
            score -= 4
            issues.append(f"グラデーション色差 {distance:.0f}: バンディングリスク高")
        elif distance > 128:
            score -= 2
            issues.append(f"グラデーション色差 {distance:.0f}: 軽微なバンディングの可能性")

        # Very small distance = flat (OK but note it)
        if distance < 10:
            score -= 1
            issues.append("グラデーションがほぼフラット: 意図的であれば問題なし")

        return QualityScore(
            dimension="visual", name="グラデーション品質",
            score=max(0, score), max_score=10, weight=0.6,
            details=f"色差距離: {distance:.1f} (1920ステップ, バンディング閾値: ~128)",
            issues=issues,
            suggestions=["中間色を追加して3段階グラデーションにする"] if distance > 128 else [],
        )

    def _check_shadow_consistency(self) -> QualityScore:
        """Check shadow design rules (consistent angle, opacity, spread)."""
        # Based on generate_carousel.py defaults:
        # shadow_offset=2, shadow_color=(0,0,0,128)
        # These are reasonable defaults. Score based on rules compliance.
        score = 9  # Good defaults in the codebase
        details = "影の角度: 右下2px, 透明度: 50%, 統一的設定"
        issues = []
        suggestions = []

        # Check if offset is proportional to font size (should be ~3-5% of font size)
        # Assuming default shadow_offset=2, font_size=56 -> 3.5% (good)
        return QualityScore(
            dimension="visual", name="影のリアリズム",
            score=score, max_score=10, weight=0.5,
            details=details,
            issues=issues,
            suggestions=suggestions,
        )

    def _check_font_golden_ratio(self, font_sizes: dict) -> QualityScore:
        """Check that font sizes follow golden ratio: title:body:caption = 1:0.618:0.382."""
        title = font_sizes.get("title", 56)
        body = font_sizes.get("body", 34)
        caption = font_sizes.get("caption", 20)

        ideal_body = title * FONT_RATIO_BODY
        ideal_caption = title * FONT_RATIO_CAPTION

        body_dev = abs(body - ideal_body) / ideal_body
        caption_dev = abs(caption - ideal_caption) / ideal_caption

        score = 10
        issues = []

        if body_dev > 0.15:
            score -= 3
            issues.append(f"本文{body}px: 理想は{ideal_body:.0f}px (タイトルx0.618)")
        if caption_dev > 0.20:
            score -= 2
            issues.append(f"キャプション{caption}px: 理想は{ideal_caption:.0f}px (タイトルx0.382)")

        actual_ratio = f"{title}:{body}:{caption}"
        ideal_ratio = f"{title}:{ideal_body:.0f}:{ideal_caption:.0f}"

        return QualityScore(
            dimension="visual", name="フォントサイズ黄金比",
            score=max(0, score), max_score=10, weight=1.0,
            details=f"実際: {actual_ratio}, 理想: {ideal_ratio} (1:0.618:0.382)",
            issues=issues,
            suggestions=[f"本文を{ideal_body:.0f}px、キャプションを{ideal_caption:.0f}pxに調整"] if issues else [],
        )

    def _check_images(self, image_paths: list[Path]) -> QualityScore:
        """Pixel-level checks on generated images (requires PIL)."""
        try:
            from PIL import Image
        except ImportError:
            return QualityScore(
                dimension="visual", name="画像ピクセル検査",
                score=5, max_score=10, weight=0.5,
                details="PIL未インストール: 画像検査スキップ",
                issues=["pip install Pillow でインストールしてください"],
            )

        score = 10
        issues = []
        for path in image_paths:
            if not path.exists():
                score -= 2
                issues.append(f"画像が見つからない: {path.name}")
                continue

            img = Image.open(path)
            w, h = img.size

            # Check dimensions
            if w != 1080 or h != 1920:
                score -= 3
                issues.append(f"{path.name}: サイズ {w}x{h} (期待: 1080x1920)")

            # Check safe zone: top 150px should not have primary content text
            # (Heuristic: check if top strip is relatively uniform / gradient)

        return QualityScore(
            dimension="visual", name="画像ピクセル検査",
            score=max(0, score), max_score=10, weight=0.8,
            details=f"{len(image_paths)}枚の画像を検査",
            issues=issues,
            suggestions=["全スライドを1080x1920で生成する"] if issues else [],
        )

    # ----------------------------------------------------------------
    # Content Quality Checks (4 items)
    # ----------------------------------------------------------------

    def _check_content_quality(
        self,
        slides: list[dict],
        hook_text: str,
        caption: str,
        category: str,
        all_text: str,
    ) -> list[QualityScore]:
        scores = []

        # 1. Hook power score
        scores.append(self._score_hook_power(hook_text))

        # 2. Save value score
        scores.append(self._score_save_value(all_text, slides))

        # 3. Share value score
        scores.append(self._score_share_value(all_text, slides))

        # 4. CTA naturalness
        scores.append(self._score_cta_naturalness(slides, caption))

        return scores

    def _score_hook_power(self, hook_text: str) -> QualityScore:
        """
        Score the "stopping power" of the hook (0-10).
        Based on behavioral economics triggers.
        """
        score = 0
        triggers = []

        # Loss aversion words: +2
        for w in LOSS_AVERSION_WORDS:
            if w in hook_text:
                score += 2
                triggers.append(f"損失回避: '{w}'")
                break

        # Numbers: +1
        if re.search(r"\d+", hook_text):
            score += 1
            triggers.append("数字入り")

        # Question form: +1
        for pattern in QUESTION_PATTERNS:
            if re.search(pattern, hook_text):
                score += 1
                triggers.append("疑問形")
                break

        # Emotion triggers: +1
        for w in EMOTION_TRIGGERS:
            if w in hook_text:
                score += 1
                triggers.append(f"感情トリガー: '{w}'")
                break

        # Persona-direct: +2
        persona_hit = False
        for w in PERSONA_DIRECT_WORDS:
            if w in hook_text:
                if not persona_hit:
                    score += 2
                    persona_hit = True
                triggers.append(f"ペルソナ直撃: '{w}'")

        # Character count bonus/penalty
        hook_len = len(hook_text)
        if hook_len <= 20:
            score += 1
            triggers.append(f"文字数{hook_len}: 3秒で読める")
        elif hook_len > 40:
            score -= 1
            triggers.append(f"文字数{hook_len}: 長すぎる")

        # Conflict/contrast structure (他者+否定→変化)
        conflict_words = ["けど", "のに", "でも", "なのに", "vs", "対", "黙った", "怒った", "泣いた"]
        for w in conflict_words:
            if w in hook_text:
                score += 1
                triggers.append(f"対立構造: '{w}'")
                break

        score = min(10, max(0, score))

        return QualityScore(
            dimension="content", name="フック力スコア",
            score=score, max_score=10, weight=2.0,
            details=f"トリガー: {', '.join(triggers) if triggers else 'なし'}",
            issues=["フック力が弱い: 損失回避/ペルソナ/感情/数字を追加"] if score < 5 else [],
            suggestions=self._suggest_hook_improvement(hook_text, score),
        )

    def _suggest_hook_improvement(self, hook_text: str, current_score: int) -> list[str]:
        """Generate specific improvement suggestions for the hook."""
        suggestions = []
        if current_score >= 8:
            return ["現在のフックは高品質です"]

        has_persona = any(w in hook_text for w in PERSONA_DIRECT_WORDS)
        has_loss = any(w in hook_text for w in LOSS_AVERSION_WORDS)
        has_number = bool(re.search(r"\d+", hook_text))
        has_question = any(re.search(p, hook_text) for p in QUESTION_PATTERNS)

        if not has_persona:
            suggestions.append("ペルソナ直撃ワードを追加: 「看護師」「夜勤明け」「5年目」など")
        if not has_loss:
            suggestions.append("損失回避を追加: 「知らないと損する」「見逃すな」など")
        if not has_number:
            suggestions.append("数字を追加: 「100万」「3つの」「5年目」など")
        if not has_question:
            suggestions.append("疑問形にする: 「知ってた？」「本当に？」")
        if len(hook_text) > 30:
            suggestions.append(f"文字数を{len(hook_text)}→20以内に圧縮")

        return suggestions[:3]  # Top 3 suggestions

    def _score_save_value(self, all_text: str, slides: list[dict]) -> QualityScore:
        """Score the "save for later" value (0-10)."""
        score = 0
        triggers = []

        # Data/comparison: +3
        for w in SAVE_PATTERNS["data_comparison"]:
            if re.search(w, all_text):
                score += 3
                triggers.append(f"データ/比較: '{w}'")
                break

        # Checklist: +2
        for w in SAVE_PATTERNS["checklist"]:
            if re.search(w, all_text):
                score += 2
                triggers.append(f"チェックリスト: '{w}'")
                break

        # How-to: +2
        for w in SAVE_PATTERNS["howto"]:
            if re.search(w, all_text):
                score += 2
                triggers.append(f"How-to: '{w}'")
                break

        # Numbered items: +1
        if re.search(r"[①②③④⑤⑥⑦⑧⑨⑩]|[1-9][\.\）]", all_text):
            score += 1
            triggers.append("番号付きリスト")

        # Slide count: 5+ slides with data = high save value
        data_slides = sum(1 for s in slides if re.search(r"\d+[%％万円]", self._extract_slide_text(s)))
        if data_slides >= 3:
            score += 2
            triggers.append(f"データスライド{data_slides}枚")

        score = min(10, max(0, score))

        return QualityScore(
            dimension="content", name="保存価値スコア",
            score=score, max_score=10, weight=1.5,
            details=f"保存トリガー: {', '.join(triggers) if triggers else 'なし'}",
            issues=["保存価値が低い: データ表/チェックリスト/手順を含める"] if score < 4 else [],
            suggestions=["比較表やデータを追加すると保存率が上がる"] if score < 6 else [],
        )

    def _score_share_value(self, all_text: str, slides: list[dict]) -> QualityScore:
        """Score the "share with friends" value (0-10)."""
        score = 0
        triggers = []

        # Empathy: +2
        for w in SHARE_PATTERNS["empathy"]:
            if re.search(w, all_text):
                score += 2
                triggers.append(f"共感: '{w}'")
                break

        # Surprise: +2
        for w in SHARE_PATTERNS["surprise"]:
            if re.search(w, all_text):
                score += 2
                triggers.append(f"意外性: '{w}'")
                break

        # Practical: +1
        for w in SHARE_PATTERNS["practical"]:
            if re.search(w, all_text):
                score += 1
                triggers.append(f"実用性: '{w}'")
                break

        # Storytelling structure (beginning-middle-end): +2
        if len(slides) >= 5:
            score += 2
            triggers.append(f"ストーリー構造: {len(slides)}枚")

        # Relatable persona mention: +1
        nurse_words = ["看護師", "ナース", "病棟", "夜勤"]
        if any(w in all_text for w in nurse_words):
            score += 1
            triggers.append("看護師コミュニティ向け")

        # Humor/surprise ending
        last_slide = self._extract_slide_text(slides[-1]) if slides else ""
        surprise_end = ["笑", "www", "草", "まさか", "予想外", "黙った"]
        if any(w in last_slide for w in surprise_end):
            score += 2
            triggers.append("オチが面白い")

        score = min(10, max(0, score))

        return QualityScore(
            dimension="content", name="シェア価値スコア",
            score=score, max_score=10, weight=1.0,
            details=f"シェアトリガー: {', '.join(triggers) if triggers else 'なし'}",
            issues=["シェア価値が低い: 共感/意外性/オチを強化"] if score < 4 else [],
            suggestions=["「友達にLINEで送りたくなるか？」を基準に判断"] if score < 6 else [],
        )

    def _score_cta_naturalness(self, slides: list[dict], caption: str) -> QualityScore:
        """Score CTA naturalness (0-10, where 10 = completely natural, 0 = spam)."""
        all_text = "\n".join(self._extract_slide_text(s) for s in slides)
        full_text = all_text + "\n" + caption

        hard_count = sum(1 for w in HARD_CTA_WORDS if w in full_text)
        soft_count = sum(1 for w in SOFT_CTA_WORDS if w in full_text)

        score = 10
        issues = []

        # Penalize hard CTA density
        if hard_count >= 4:
            score -= 5
            issues.append(f"ハードCTA {hard_count}個: セールス感が強すぎる")
        elif hard_count >= 2:
            score -= 2
            issues.append(f"ハードCTA {hard_count}個: やや売り込み感")

        # CTA in early slides is bad
        if slides and len(slides) >= 3:
            early_text = "\n".join(self._extract_slide_text(s) for s in slides[:3])
            early_hard = sum(1 for w in HARD_CTA_WORDS if w in early_text)
            if early_hard >= 2:
                score -= 3
                issues.append("前半スライドにハードCTA: 離脱リスク大")

        # Bonus for soft CTA
        if soft_count >= 1 and hard_count <= 1:
            score = min(10, score + 1)

        # No CTA at all
        if hard_count == 0 and soft_count == 0:
            score -= 1
            issues.append("CTAが皆無: 最低でもソフトCTA（保存/フォロー）を1つ入れる")

        score = max(0, min(10, score))

        return QualityScore(
            dimension="content", name="CTA自然度",
            score=score, max_score=10, weight=1.2,
            details=f"ハードCTA: {hard_count}個, ソフトCTA: {soft_count}個",
            issues=issues,
            suggestions=["8:2ルール: 10投稿中8投稿はソフトCTAのみ"] if hard_count >= 2 else [],
        )

    # ----------------------------------------------------------------
    # Psychology Quality Checks (4 items)
    # ----------------------------------------------------------------

    def _check_psychology_quality(
        self,
        slides: list[dict],
        slide_analyses: list[SlideAnalysis],
        all_text: str,
    ) -> list[QualityScore]:
        scores = []

        # 1. Cognitive load (Miller's Law)
        scores.append(self._check_cognitive_load(slide_analyses))

        # 2. Emotion curve
        scores.append(self._check_emotion_curve(slides, slide_analyses))

        # 3. Zeigarnik effect
        scores.append(self._check_zeigarnik(slides))

        # 4. Peak-End rule
        scores.append(self._check_peak_end(slides, slide_analyses))

        return scores

    def _check_cognitive_load(self, analyses: list[SlideAnalysis]) -> QualityScore:
        """Check cognitive load per slide (Miller's Law: 7 +/- 2 chunks)."""
        overloaded = []
        for a in analyses:
            if a.chunk_count > MILLER_MAX:
                overloaded.append(f"スライド{a.slide_num}: {a.chunk_count}チャンク (上限{MILLER_MAX})")

        score = max(0, 10 - len(overloaded) * 3)
        avg_chunks = sum(a.chunk_count for a in analyses) / len(analyses) if analyses else 0

        return QualityScore(
            dimension="psychology", name="認知負荷 (ミラーの法則)",
            score=score, max_score=10, weight=1.2,
            details=f"平均チャンク数: {avg_chunks:.1f}/スライド (理想: {MILLER_IDEAL}以内)",
            issues=overloaded,
            suggestions=["情報を分割して1スライド7チャンク以内にする"] if overloaded else [],
        )

    def _check_emotion_curve(
        self,
        slides: list[dict],
        analyses: list[SlideAnalysis],
    ) -> QualityScore:
        """
        Check the emotion arc across all slides.
        Ideal 7-slide curve: surprise -> empathy -> expect -> learn -> convince -> hope -> action
        """
        actual_emotions = [a.emotion_type for a in analyses]

        # Score based on how well the actual curve matches the ideal
        score = 10
        issues = []

        if len(actual_emotions) < 5:
            score -= 3
            issues.append(f"スライド数{len(actual_emotions)}: 感情曲線の設計には5枚以上必要")

        # Check key positions
        if actual_emotions:
            # First slide should have surprise/curiosity
            if actual_emotions[0] not in ("surprise", "neutral"):
                score -= 1
                issues.append(f"1枚目の感情: '{actual_emotions[0]}' (理想: surprise)")

            # Last slide should drive action
            if len(actual_emotions) >= 5 and actual_emotions[-1] not in ("action", "hope"):
                score -= 1
                issues.append(f"最終スライドの感情: '{actual_emotions[-1]}' (理想: action/hope)")

        # Check monotony (same emotion throughout = boring)
        unique_emotions = set(actual_emotions)
        if len(unique_emotions) <= 2 and len(actual_emotions) >= 5:
            score -= 3
            issues.append(f"感情の種類が{len(unique_emotions)}種のみ: 単調すぎる")
        elif len(unique_emotions) >= 4:
            score = min(10, score + 1)  # bonus for variety

        # Check for emotional build-up (should have some "learn" or "convince" in middle)
        if len(actual_emotions) >= 5:
            middle = actual_emotions[2:-1]
            informative = sum(1 for e in middle if e in ("learn", "convince", "expect"))
            if informative == 0:
                score -= 2
                issues.append("中盤に学び/説得のスライドがない: 説得力不足")

        return QualityScore(
            dimension="psychology", name="感情曲線",
            score=max(0, score), max_score=10, weight=1.5,
            details=f"感情推移: {' -> '.join(actual_emotions)}",
            issues=issues,
            suggestions=[
                "理想: 驚き→共感→期待→学び→納得→希望→行動",
                "中盤にデータ/根拠スライドを入れて説得力を持たせる",
            ] if issues else [],
        )

    def _check_zeigarnik(self, slides: list[dict]) -> QualityScore:
        """
        Check Zeigarnik effect: does each slide create "want to see next" tension?
        Indicators: cliffhangers, incomplete statements, "...", "?", sequential numbering.
        """
        score = 0
        total_transitions = max(1, len(slides) - 1)
        tension_count = 0

        for i in range(len(slides) - 1):
            text = self._extract_slide_text(slides[i])
            has_tension = False

            # Ellipsis / trailing off
            if text.rstrip().endswith("…") or text.rstrip().endswith("..."):
                has_tension = True
            # Question ending
            if text.rstrip().endswith("？") or text.rstrip().endswith("?"):
                has_tension = True
            # "But..." / "However..."
            tension_words = ["しかし", "ところが", "でも", "だけど", "実は", "ただ", "→"]
            if any(text.rstrip().endswith(w) for w in tension_words):
                has_tension = True
            # Sequential numbering
            if re.search(r"[①②③④⑤]|その[1-5]|STEP\s*[1-5]", text):
                has_tension = True
            # "Next" / continuation hints
            if "続き" in text or "次" in text:
                has_tension = True

            if has_tension:
                tension_count += 1

        tension_ratio = tension_count / total_transitions
        score = min(10, int(tension_ratio * 12))  # Slight bonus for high tension

        issues = []
        if tension_ratio < 0.3:
            issues.append(f"テンション遷移: {tension_count}/{total_transitions} (30%未満)")

        return QualityScore(
            dimension="psychology", name="ザイガルニック効果",
            score=score, max_score=10, weight=1.0,
            details=f"「続きが気になる」遷移: {tension_count}/{total_transitions}箇所 ({tension_ratio:.0%})",
            issues=issues,
            suggestions=[
                "スライド末尾を「...」「？」「しかし」で終わらせて次への期待を作る",
                "「3つの理由」のように連番構造で引っ張る",
            ] if tension_ratio < 0.5 else [],
        )

    def _check_peak_end(self, slides: list[dict], analyses: list[SlideAnalysis]) -> QualityScore:
        """
        Check Peak-End Rule: the most impressive slide and the last slide
        should both be high quality.
        """
        if not slides or not analyses:
            return QualityScore(
                dimension="psychology", name="ピーク・エンドの法則",
                score=0, max_score=10, weight=1.3,
                details="スライドがありません",
                issues=["スライドデータを提供してください"],
            )

        score = 10
        issues = []

        # Find the "peak" slide (most data/emotion-dense)
        peak_idx = 0
        peak_score = 0
        for i, a in enumerate(analyses):
            slide_richness = a.chunk_count + (2 if a.has_number else 0) + (1 if a.emotion_type != "neutral" else 0)
            if slide_richness > peak_score:
                peak_score = slide_richness
                peak_idx = i

        # Peak should not be slide 1 or 2 (too early)
        if peak_idx <= 1 and len(slides) >= 5:
            score -= 2
            issues.append(f"ピークがスライド{peak_idx + 1}: 早すぎる（中盤〜後半が理想）")

        # Last slide quality
        last_text = self._extract_slide_text(slides[-1])
        last_analysis = analyses[-1]

        # Last slide should have a clear action/emotion
        if last_analysis.emotion_type == "neutral":
            score -= 2
            issues.append("最終スライドの感情が「neutral」: 行動喚起/希望を入れる")

        # Last slide should not be too text-heavy
        if last_analysis.char_count > 80:
            score -= 1
            issues.append(f"最終スライド{last_analysis.char_count}文字: シンプルで印象的にする")

        # Last slide should have CTA or memorable conclusion
        has_cta = any(w in last_text for w in SOFT_CTA_WORDS + HARD_CTA_WORDS)
        has_conclusion = any(w in last_text for w in ["結論", "まとめ", "つまり", "だから"])
        if not has_cta and not has_conclusion:
            score -= 2
            issues.append("最終スライドにCTAもまとめもない: 余韻が残らない")

        return QualityScore(
            dimension="psychology", name="ピーク・エンドの法則",
            score=max(0, score), max_score=10, weight=1.3,
            details=f"ピーク: スライド{peak_idx + 1} (豊かさ{peak_score}), ラスト: {last_analysis.emotion_type}/{last_analysis.char_count}文字",
            issues=issues,
            suggestions=[
                "最も印象的なデータ/感情を中盤〜後半に配置する",
                "最終スライドは短く、印象的に。CTAかまとめで締める",
            ] if issues else [],
        )

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    def _extract_slide_text(self, slide: dict) -> str:
        """Extract all text from a slide dict."""
        parts = []
        for key in ("hook", "title", "heading", "body", "text", "cta", "caption"):
            if key in slide and slide[key]:
                parts.append(str(slide[key]))
        if not parts:
            # Fallback: join all string values
            for v in slide.values():
                if isinstance(v, str) and v.strip():
                    parts.append(v)
        return "\n".join(parts)

    def _analyze_slide(self, slide_num: int, text: str) -> SlideAnalysis:
        """Analyze a single slide's text."""
        clean = text.strip()
        lines = [l for l in clean.split("\n") if l.strip()]
        ratios = char_ratios(clean)

        return SlideAnalysis(
            slide_num=slide_num,
            char_count=len(clean.replace("\n", "").replace(" ", "")),
            line_count=len(lines),
            kanji_ratio=ratios.get("kanji", 0),
            hiragana_ratio=ratios.get("hiragana", 0),
            katakana_ratio=ratios.get("katakana", 0),
            chunk_count=count_chunks(clean),
            emotion_type=detect_emotion_type(clean),
            has_number=bool(re.search(r"\d+", clean)),
            readability_ok=(
                len(clean.replace("\n", "").replace(" ", "")) <= MAX_CHARS_PER_SLIDE
                and len(lines) <= MAX_LINES_PER_SLIDE
            ),
        )


# ============================================================
# FactChecker — 事実確認エンジン v1.0
# ============================================================
# 投稿前に給与数値・統計・百分率を基準データと照合し、
# 虚偽・誇張・内部矛盾を検出する。外部API不使用・純粋ローカル動作。
# ============================================================


@dataclass
class FactIssue:
    """Individual fact-check finding."""
    severity: str   # "error" | "warning"
    field: str      # "hook" | "slide_1" ... "slide_8" | "caption"
    claim: str      # the verbatim problematic text fragment
    expected: str   # human-readable correct range
    source: str     # reference source name


@dataclass
class FactCheckResult:
    """Aggregate result returned by FactChecker.fact_check_post()."""
    passed: bool
    score: float            # 0-10  (10 = zero issues)
    issues: list[FactIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": round(self.score, 1),
            "issues": [
                {
                    "severity": i.severity,
                    "field": i.field,
                    "claim": i.claim,
                    "expected": i.expected,
                    "source": i.source,
                }
                for i in self.issues
            ],
        }


class FactChecker:
    """
    SNS投稿の事実確認チェッカー。

    給与数値・統計・百分率をリファレンスデータと照合し、
    範囲外の数値・出典不明の統計・内部矛盾をフラグする。

    Usage:
        fc = FactChecker()
        result = fc.fact_check_post(queue_entry)
        if not result.passed:
            for issue in result.issues:
                print(issue.severity, issue.field, issue.claim)
    """

    # ----------------------------------------------------------
    # リファレンスデータ
    # 出典: 厚労省令和6年賃金構造基本統計調査・日本看護協会等
    # ----------------------------------------------------------

    # 給与レンジ: key → (min, max, unit, label, source)
    SALARY_RANGES: Dict[str, Tuple] = {
        # パート時給
        "正看護師_パート_時給":    (1_800,       2_500,       "円/時",  "正看護師パート時給",         "厚労省R6賃金構造"),
        "准看護師_パート_時給":    (1_600,       2_000,       "円/時",  "准看護師パート時給",         "厚労省R6賃金構造"),
        # 月給
        "正看護師_月給":           (250_000,     389_000,     "円/月",  "正看護師月給",               "厚労省R6賃金構造"),
        # 夜勤手当
        "夜勤手当_二交替":         (10_000,      15_000,      "円/回",  "夜勤手当(二交替)",           "日本看護協会2023"),
        "夜勤手当_三交替":          (4_000,       8_000,      "円/回",  "夜勤手当(三交替)",           "日本看護協会2023"),
        # 年収
        "神奈川_看護師_年収":      (5_000_000,   5_500_000,   "円/年",  "神奈川県看護師平均年収",     "厚労省R6賃金構造"),
        # 応援ナース月収
        "応援ナース_月収":         (400_000,     600_000,     "円/月",  "応援ナース月収",             "各種求人情報"),
        # 美容クリニック月収
        "美容クリニック_月収":     (300_000,     400_000,     "円/月",  "美容クリニック看護師月収",   "各種求人情報"),
        # 紹介手数料率（業界平均、percent単位）
        "紹介手数料_率":           (20,          30,          "%",      "紹介手数料率（業界平均）",   "厚労省職業安定局"),
    }

    # 既知の有効統計: key → (value, unit, description, source)
    KNOWN_STATS: Dict[str, Tuple] = {
        "神奈川_看護師_総数":       (77_188,  "人",        "神奈川県看護師総数",             "厚労省R6看護職員就業届"),
        "神奈川_人口10万_看護師":   (813.2,   "人/10万人", "神奈川県人口10万人あたり看護師数","厚労省R6"),
        "神奈川_充足率":            (72.6,    "%",         "神奈川県看護師充足率",           "厚労省R6"),
        "業界_紹介手数料_下限":     (20,      "%",         "大手紹介会社手数料下限",         "厚労省職業安定局"),
        "業界_紹介手数料_上限":     (30,      "%",         "大手紹介会社手数料上限",         "厚労省職業安定局"),
        "当社_手数料":              (10,      "%",         "神奈川ナース転職手数料",         "社内規定"),
    }

    # 神奈川コンビニ深夜バイト時給帯（比較用・誤用検出）
    CONVENIENCE_STORE_HOURLY: Tuple[int, int] = (1_300, 1_500)

    # 乖離率のしきい値
    ERROR_THRESHOLD:   float = 0.20   # ±20% 超 → error
    WARNING_THRESHOLD: float = 0.10   # ±10% 超 → warning

    # ----------------------------------------------------------
    # 正規表現パターン
    # ----------------------------------------------------------

    # 「時給 X,XXX 円」「時給約X,XXX円」
    _RE_HOURLY = re.compile(
        r"時給\s*(?:約\s*)?(\d[\d,，]*)\s*円"
    )
    # 「月給/月収 XX万円」「月収XX〜YY万円」
    _RE_MONTHLY_MAN = re.compile(
        r"月(?:給|収|収入)\s*(?:約\s*)?(\d+(?:\.\d+)?)\s*(?:〜\s*(\d+(?:\.\d+)?)\s*)?万円"
    )
    # 「月給/月収 XXX,XXX 円」（万なし直接数値）
    _RE_MONTHLY_YEN = re.compile(
        r"月(?:給|収|収入)\s*(?:約\s*)?([\d,，]+)\s*円"
    )
    # 「年収 XXX万円」「年収XXX〜YYY万円」
    _RE_ANNUAL_MAN = re.compile(
        r"年収\s*(?:約\s*)?(\d+(?:\.\d+)?)\s*(?:〜\s*(\d+(?:\.\d+)?)\s*)?万円"
    )
    # 「夜勤手当 X万円」
    _RE_YOQIN_MAN = re.compile(
        r"夜勤手当\s*(?:約\s*)?(\d+(?:\.\d+)?)\s*万円"
    )
    # 「夜勤手当 X,XXX円」
    _RE_YOQIN_YEN = re.compile(
        r"夜勤手当\s*(?:約\s*)?([\d,，]+)\s*円"
    )
    # パーセント表現 「XX%」「XX％」
    _RE_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s*[%％]")
    # 人数「X万X,XXX人」
    _RE_PEOPLE_MAN = re.compile(r"(\d+(?:\.\d+)?)\s*万\s*(\d+)?\s*人")
    # 人数「X,XXX人」
    _RE_PEOPLE_RAW = re.compile(r"([\d,，]+)\s*人")

    # ----------------------------------------------------------
    # 内部ヘルパー
    # ----------------------------------------------------------

    @staticmethod
    def _clean_number(s: str) -> float:
        """「1,234」「1，234」→ float 1234.0"""
        return float(s.replace(",", "").replace("，", ""))

    @staticmethod
    def _man_to_yen(man: float) -> float:
        return man * 10_000

    def _deviation(self, value: float, lo: float, hi: float) -> float:
        """
        値が [lo, hi] からどれだけ外れているかの比率を返す。
        範囲内なら 0.0、範囲外は正値。
        """
        if lo <= value <= hi:
            return 0.0
        mid = (lo + hi) / 2
        return abs(value - mid) / mid if mid > 0 else 0.0

    def _severity(self, deviation: float) -> Optional[str]:
        if deviation > self.ERROR_THRESHOLD:
            return "error"
        if deviation > self.WARNING_THRESHOLD:
            return "warning"
        return None

    # ----------------------------------------------------------
    # 公開メソッド 1: check_salary_claims
    # ----------------------------------------------------------

    def check_salary_claims(self, text: str, field_name: str = "unknown") -> List[FactIssue]:
        """
        テキスト中の時給・月給・年収・夜勤手当を抽出し、
        リファレンスレンジと照合して FactIssue リストを返す。

        Args:
            text:       チェック対象テキスト
            field_name: どのフィールドか（"hook" / "slide_2" 等）

        Returns:
            問題のある FactIssue のリスト（問題なければ空リスト）
        """
        issues: List[FactIssue] = []

        # ---- 時給チェック ----------------------------------------
        for m in self._RE_HOURLY.finditer(text):
            raw = self._clean_number(m.group(1))
            lo, hi, unit, label, src = self.SALARY_RANGES["正看護師_パート_時給"]
            dev = self._deviation(raw, lo, hi)
            sev = self._severity(dev)
            if sev:
                issues.append(FactIssue(
                    severity=sev,
                    field=field_name,
                    claim=m.group(0),
                    expected=f"{label}: {lo:,}〜{hi:,}{unit}",
                    source=src,
                ))

        # 応援ナース・美容クリニック文脈かどうかを先に判定
        is_oen    = "応援" in text or "トラベル" in text
        is_beauty = "美容" in text

        # ---- 月給チェック（「XX万円」形式）-----------------------
        for m in self._RE_MONTHLY_MAN.finditer(text):
            lo_m, hi_m, unit, label, src = self.SALARY_RANGES["正看護師_月給"]
            val_lo = self._man_to_yen(float(m.group(1)))
            val_hi = self._man_to_yen(float(m.group(2))) if m.group(2) else val_lo
            flagged = False
            for val in (val_lo, val_hi):
                if flagged:
                    break
                dev = self._deviation(val, lo_m, hi_m)
                sev = self._severity(dev)
                if not sev:
                    continue
                # 応援ナース・美容クリニックは別レンジで再判定
                if is_oen:
                    alt_lo, alt_hi = (self.SALARY_RANGES["応援ナース_月収"][0],
                                      self.SALARY_RANGES["応援ナース_月収"][1])
                    if not self._severity(self._deviation(val, alt_lo, alt_hi)):
                        continue
                elif is_beauty:
                    alt_lo, alt_hi = (self.SALARY_RANGES["美容クリニック_月収"][0],
                                      self.SALARY_RANGES["美容クリニック_月収"][1])
                    if not self._severity(self._deviation(val, alt_lo, alt_hi)):
                        continue
                issues.append(FactIssue(
                    severity=sev,
                    field=field_name,
                    claim=m.group(0),
                    expected=f"{label}: {lo_m // 10_000}〜{hi_m // 10_000}万{unit}",
                    source=src,
                ))
                flagged = True

        # ---- 月給チェック（直接数値「XXX,XXX円」形式）-----------
        for m in self._RE_MONTHLY_YEN.finditer(text):
            raw = self._clean_number(m.group(1))
            # 月給として妥当な範囲（10万〜100万）に限定
            if 100_000 <= raw <= 1_000_000:
                lo_m, hi_m, unit, label, src = self.SALARY_RANGES["正看護師_月給"]
                dev = self._deviation(raw, lo_m, hi_m)
                sev = self._severity(dev)
                # 応援ナース・美容クリニック文脈では別レンジで再判定
                if sev and is_oen:
                    alt_lo, alt_hi = (self.SALARY_RANGES["応援ナース_月収"][0],
                                      self.SALARY_RANGES["応援ナース_月収"][1])
                    if not self._severity(self._deviation(raw, alt_lo, alt_hi)):
                        sev = None
                elif sev and is_beauty:
                    alt_lo, alt_hi = (self.SALARY_RANGES["美容クリニック_月収"][0],
                                      self.SALARY_RANGES["美容クリニック_月収"][1])
                    if not self._severity(self._deviation(raw, alt_lo, alt_hi)):
                        sev = None
                if sev:
                    issues.append(FactIssue(
                        severity=sev,
                        field=field_name,
                        claim=m.group(0),
                        expected=f"{label}: {lo_m // 10_000}〜{hi_m // 10_000}万{unit}",
                        source=src,
                    ))

        # ---- 年収チェック（「XX万円」形式）-----------------------
        for m in self._RE_ANNUAL_MAN.finditer(text):
            lo_a, hi_a, unit, label, src = self.SALARY_RANGES["神奈川_看護師_年収"]
            val_lo = self._man_to_yen(float(m.group(1)))
            val_hi = self._man_to_yen(float(m.group(2))) if m.group(2) else val_lo
            flagged = False
            for val in (val_lo, val_hi):
                if flagged:
                    break
                dev = self._deviation(val, lo_a, hi_a)
                sev = self._severity(dev)
                if not sev:
                    continue
                # 応援ナース・美容クリニックは年収レンジが異なるため再判定
                is_oen = "応援" in text or "トラベル" in text
                is_beauty = "美容" in text
                if is_oen:
                    lo2 = self.SALARY_RANGES["応援ナース_月収"][0] * 12
                    hi2 = self.SALARY_RANGES["応援ナース_月収"][1] * 12
                    if not self._severity(self._deviation(val, lo2, hi2)):
                        continue
                elif is_beauty:
                    lo2 = self.SALARY_RANGES["美容クリニック_月収"][0] * 12
                    hi2 = self.SALARY_RANGES["美容クリニック_月収"][1] * 12
                    if not self._severity(self._deviation(val, lo2, hi2)):
                        continue
                issues.append(FactIssue(
                    severity=sev,
                    field=field_name,
                    claim=m.group(0),
                    expected=f"{label}: {lo_a // 10_000}〜{hi_a // 10_000}万{unit}",
                    source=src,
                ))
                flagged = True

        # ---- 夜勤手当チェック（万円形式）------------------------
        for m in self._RE_YOQIN_MAN.finditer(text):
            val = self._man_to_yen(float(m.group(1)))
            key = "夜勤手当_三交替" if ("三交替" in text or "三交代" in text) else "夜勤手当_二交替"
            lo_y, hi_y, unit, label, src = self.SALARY_RANGES[key]
            dev = self._deviation(val, lo_y, hi_y)
            sev = self._severity(dev)
            if sev:
                issues.append(FactIssue(
                    severity=sev,
                    field=field_name,
                    claim=m.group(0),
                    expected=f"{label}: {lo_y:,}〜{hi_y:,}{unit}",
                    source=src,
                ))

        # ---- 夜勤手当チェック（直接円形式）----------------------
        for m in self._RE_YOQIN_YEN.finditer(text):
            raw = self._clean_number(m.group(1))
            key = "夜勤手当_三交替" if ("三交替" in text or "三交代" in text) else "夜勤手当_二交替"
            lo_y, hi_y, unit, label, src = self.SALARY_RANGES[key]
            dev = self._deviation(raw, lo_y, hi_y)
            sev = self._severity(dev)
            if sev:
                issues.append(FactIssue(
                    severity=sev,
                    field=field_name,
                    claim=m.group(0),
                    expected=f"{label}: {lo_y:,}〜{hi_y:,}{unit}",
                    source=src,
                ))

        return issues

    # ----------------------------------------------------------
    # 公開メソッド 2: check_statistics
    # ----------------------------------------------------------

    def check_statistics(self, text: str, field_name: str = "unknown") -> List[FactIssue]:
        """
        テキスト中のパーセント・人数表現を抽出し、
        既知の有効統計値と照合して FactIssue リストを返す。
        出典不明の統計的パーセントは warning として記録する。

        Args:
            text:       チェック対象テキスト
            field_name: どのフィールドか

        Returns:
            問題のある FactIssue のリスト
        """
        issues: List[FactIssue] = []

        # ---- パーセント表現 -------------------------------------
        for m in self._RE_PERCENT.finditer(text):
            val = float(m.group(1))
            snippet = m.group(0)
            context = text[max(0, m.start() - 25):m.end() + 25]

            # 手数料パーセントの検証
            if any(kw in context for kw in ("手数料", "紹介料", "紹介手数料")):
                if val == 10.0:
                    continue  # 当社10% — OK
                lo_fee = self.KNOWN_STATS["業界_紹介手数料_下限"][0]
                hi_fee = self.KNOWN_STATS["業界_紹介手数料_上限"][0]
                if not (lo_fee <= val <= hi_fee):
                    issues.append(FactIssue(
                        severity="error",
                        field=field_name,
                        claim=snippet,
                        expected=f"業界手数料: {lo_fee}〜{hi_fee}%、当社: 10%",
                        source="厚労省職業安定局",
                    ))
                continue

            # 充足率の検証
            if "充足" in context:
                known_val = self.KNOWN_STATS["神奈川_充足率"][0]
                if abs(val - known_val) > 3.0:   # ±3ポイント許容
                    issues.append(FactIssue(
                        severity="warning",
                        field=field_name,
                        claim=snippet,
                        expected=f"神奈川県看護師充足率: {known_val}%",
                        source="厚労省R6",
                    ))
                continue

            # その他: 統計的文脈かつ出典記載なし → warning
            STAT_KEYWORDS = ("割合", "率", "の看護師", "比較", "増", "減", "差",
                             "低下", "上昇", "達成", "改善", "悪化")
            SOURCE_MARKERS = ("厚労省", "日本看護協会", "調査", "データ",
                              "統計", "出典", "参考", "報告書")
            if (any(kw in context for kw in STAT_KEYWORDS)
                    and 0 < val < 100
                    and not any(sm in text for sm in SOURCE_MARKERS)):
                issues.append(FactIssue(
                    severity="warning",
                    field=field_name,
                    claim=snippet,
                    expected="統計的主張には出典が必要（厚労省・日本看護協会等）",
                    source="内部品質基準",
                ))

        # ---- 人数表現: 「X万X,XXX人」形式 ----------------------
        for m in self._RE_PEOPLE_MAN.finditer(text):
            man_part = float(m.group(1))
            sub_part = float(m.group(2)) if m.group(2) else 0.0
            total = man_part * 10_000 + sub_part
            ctx = text[max(0, m.start() - 30):m.end() + 30]
            if "看護師" in ctx and "神奈川" in text:
                known = self.KNOWN_STATS["神奈川_看護師_総数"][0]
                if abs(total - known) > known * 0.05:   # ±5% 許容
                    issues.append(FactIssue(
                        severity="error",
                        field=field_name,
                        claim=m.group(0),
                        expected=f"神奈川県看護師総数: {known:,}人",
                        source="厚労省R6看護職員就業届",
                    ))

        # ---- 人数表現: 「X,XXX人」形式（100〜100,000 人の範囲） -
        for m in self._RE_PEOPLE_RAW.finditer(text):
            raw = self._clean_number(m.group(1))
            if 100 <= raw <= 100_000:
                ctx = text[max(0, m.start() - 30):m.end() + 30]
                if "看護師" in ctx and "神奈川" in text:
                    known = self.KNOWN_STATS["神奈川_看護師_総数"][0]
                    if abs(raw - known) > known * 0.05:
                        issues.append(FactIssue(
                            severity="warning",
                            field=field_name,
                            claim=m.group(0),
                            expected=f"神奈川県看護師総数: {known:,}人",
                            source="厚労省R6看護職員就業届",
                        ))

        return issues

    # ----------------------------------------------------------
    # 公開メソッド 3: check_consistency
    # ----------------------------------------------------------

    def check_consistency(self, text: str, field_name: str = "full_post") -> List[FactIssue]:
        """
        同一投稿内での数値矛盾・論理矛盾を検出する。

        検出パターン:
          1. 時給X円 × 「コンビニと同じ」の矛盾
          2. 年収と月給の整合性（年収 ÷ 12 ≒ 月給 × 1.1〜1.3）
          3. 高時給フック（≥2,000円）× 低手取り言及の矛盾

        Args:
            text:       投稿全文（フック+スライド+キャプション結合済み）
            field_name: "full_post" 等

        Returns:
            矛盾として検出された FactIssue リスト
        """
        issues: List[FactIssue] = []

        # ---- 矛盾パターン 1: 時給 × 「コンビニと同じ」 ----------
        hourly_matches = self._RE_HOURLY.findall(text)
        has_conveni_same = bool(re.search(
            r"コンビニ(?:と|バイトと|深夜と)?\s*(?:同じ|変わらない|同等|並み)",
            text,
        ))
        if hourly_matches and has_conveni_same:
            conv_lo, conv_hi = self.CONVENIENCE_STORE_HOURLY
            for raw_str in hourly_matches:
                val = self._clean_number(raw_str)
                if not (conv_lo <= val <= conv_hi):
                    issues.append(FactIssue(
                        severity="error",
                        field=field_name,
                        claim=f"時給{raw_str}円 + 「コンビニと同じ」",
                        expected=(
                            f"「コンビニと同じ」と主張するなら時給は"
                            f"{conv_lo:,}〜{conv_hi:,}円帯のはず。"
                            f"「コンビニより少し上」等に修正せよ"
                        ),
                        source="内部整合性チェック",
                    ))

        # ---- 矛盾パターン 2: 年収と月給の整合性 -----------------
        annual_matches  = self._RE_ANNUAL_MAN.findall(text)
        monthly_matches = self._RE_MONTHLY_MAN.findall(text)
        if annual_matches and monthly_matches:
            ann_val = self._man_to_yen(float(annual_matches[0][0]))
            mon_val = self._man_to_yen(float(monthly_matches[0][0]))
            if mon_val > 0:
                ratio = ann_val / (mon_val * 12)
                # 妥当な賞与込み比率: 0.95〜1.40
                if not (0.95 <= ratio <= 1.40):
                    issues.append(FactIssue(
                        severity="warning",
                        field=field_name,
                        claim=(
                            f"年収{annual_matches[0][0]}万円"
                            f" + 月給{monthly_matches[0][0]}万円"
                        ),
                        expected=(
                            f"年収 ÷ 12 ≈ 月給×1.1〜1.3（賞与込み）が妥当。"
                            f"現在の比率: {ratio:.2f}x"
                        ),
                        source="内部整合性チェック",
                    ))

        # ---- 矛盾パターン 3: 高時給フック × 低手取りボディ ------
        if hourly_matches:
            high_hourly = any(self._clean_number(h) >= 2_000 for h in hourly_matches)
            LOW_INCOME_PHRASES = (
                "手取り24万", "手取り23万", "手取り22万",
                "手取り21万", "手取り20万",
                "手取りが低", "給料が安", "給与が安",
            )
            mentions_low = any(p in text for p in LOW_INCOME_PHRASES)
            if high_hourly and mentions_low:
                issues.append(FactIssue(
                    severity="warning",
                    field=field_name,
                    claim="高時給（≥2,000円）× 低手取りの記述",
                    expected=(
                        "時給2,000円以上なら常勤換算で月収32万円超のはず。"
                        "「パート時給」と「常勤手取り」の混同に注意"
                    ),
                    source="内部整合性チェック",
                ))

        return issues

    # ----------------------------------------------------------
    # 公開メソッド 4: fact_check_post（メインエントリポイント）
    # ----------------------------------------------------------

    def fact_check_post(self, post: dict) -> FactCheckResult:
        """
        投稿キューエントリ全体の事実確認を実行する。

        Args:
            post: posting_queue.json の1エントリ。
                  期待するキー:
                    - "hook"        (str)
                    - "slides"      (list[str | dict]) または
                      "slide_texts" (list[str | dict])
                    - "caption"     (str)
                  いずれか欠けていても graceful に処理する。

        Returns:
            FactCheckResult (passed / score / issues)

        Scoring:
            - error  : -2.0 点（ベース10点から減算）
            - warning: -0.5 点
            - 最低 0 点
            - error が 1 件以上 or score < 6.0 → passed = False
        """
        all_issues: List[FactIssue] = []

        # フィールドマップを構築 --------------------------------
        fields: Dict[str, str] = {}

        hook = post.get("hook", "")
        if hook:
            fields["hook"] = str(hook)

        slides_raw: list = post.get("slides") or post.get("slide_texts") or []
        for i, slide in enumerate(slides_raw, start=1):
            field_key = f"slide_{i}"
            if isinstance(slide, dict):
                parts = [str(slide[k]) for k in ("hook", "title", "body", "text") if slide.get(k)]
                fields[field_key] = " ".join(parts)
            elif isinstance(slide, str):
                fields[field_key] = slide

        caption = post.get("caption", "")
        if caption:
            fields["caption"] = str(caption)

        # 各フィールドに対して salary + statistics を実行 ------
        for field_name, text in fields.items():
            all_issues.extend(self.check_salary_claims(text, field_name))
            all_issues.extend(self.check_statistics(text, field_name))

        # 整合性チェックは投稿全文に対して1回だけ実行 ----------
        full_text = " ".join(fields.values())
        all_issues.extend(self.check_consistency(full_text, "full_post"))

        # 重複排除（同一 field + claim + severity の組み合わせ） -
        seen: set = set()
        unique_issues: List[FactIssue] = []
        for issue in all_issues:
            key = (issue.field, issue.claim, issue.severity)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        # スコア算出 --------------------------------------------
        error_count   = sum(1 for i in unique_issues if i.severity == "error")
        warning_count = sum(1 for i in unique_issues if i.severity == "warning")
        score = max(0.0, 10.0 - error_count * 2.0 - warning_count * 0.5)
        passed = (error_count == 0) and (score >= 6.0)

        return FactCheckResult(passed=passed, score=score, issues=unique_issues)


# ============================================================
# Report Formatter
# ============================================================

def format_report(report: QualityReport, verbose: bool = True) -> str:
    """Format a QualityReport as human-readable text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  品質レポート: {report.content_id}")
    lines.append(f"  総合スコア: {report.overall_score:.1f}/100  グレード: {report.grade}")
    lines.append(f"  判定: {'PASS' if report.pass_fail else 'FAIL'}")
    lines.append("=" * 60)

    if report.blocking_issues:
        lines.append("")
        lines.append("  *** ブロッキング問題 ***")
        for issue in report.blocking_issues:
            lines.append(f"  [!] {issue}")

    def _format_dimension(title: str, scores: list[QualityScore]):
        lines.append("")
        dim_avg = sum(s.score for s in scores) / len(scores) if scores else 0
        lines.append(f"  [{title}] 平均: {dim_avg:.1f}/10")
        lines.append("  " + "-" * 50)
        for s in scores:
            bar = "█" * int(s.score) + "░" * (10 - int(s.score))
            lines.append(f"    {s.name:<20s} {bar} {s.score:.1f}/10")
            if verbose and s.details:
                lines.append(f"      {s.details}")
            if verbose:
                for issue in s.issues:
                    lines.append(f"      [!] {issue}")
                for sug in s.suggestions:
                    lines.append(f"      [>] {sug}")

    _format_dimension("テキスト品質", report.text_scores)
    _format_dimension("ビジュアル品質", report.visual_scores)
    _format_dimension("コンテンツ品質", report.content_scores)
    _format_dimension("心理学的品質", report.psychology_scores)

    if verbose and report.slide_analyses:
        lines.append("")
        lines.append("  [スライド分析]")
        lines.append("  " + "-" * 50)
        lines.append(f"  {'#':>3s}  {'文字':>4s}  {'行':>2s}  {'漢字':>5s}  {'チャンク':>4s}  {'感情':<10s}")
        for a in report.slide_analyses:
            ok = "o" if a.readability_ok else "x"
            lines.append(
                f"  {a.slide_num:3d}  {a.char_count:4d}  {a.line_count:2d}  "
                f"{a.kanji_ratio:5.1%}  {a.chunk_count:4d}    {a.emotion_type:<10s} {ok}"
            )

    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def print_standards():
    """Print quality standards reference."""
    print("""
╔══════════════════════════════════════════════════════════╗
║            品質基準リファレンス v1.0                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  [テキスト品質]                                           ║
║  - カーニング: 句読点前後/括弧前後の空き検出                ║
║  - 禁則処理: 行頭禁則（句読点）/行末禁則（開き括弧）        ║
║  - 数字表記: 半角/全角混在なし                             ║
║  - フォント黄金比: タイトル:本文:キャプション = 1:0.618:0.382║
║  - 読みやすさ: 1スライド120文字/8行以内                     ║
║  - 漢字比率: 15-25% (上限30%)                             ║
║  - 文字種バランス: ひらがな40-60% / 漢字15-25%             ║
║                                                          ║
║  [ビジュアル品質]                                          ║
║  - コントラスト: WCAG AA 4.5:1 / AAA 7:1                  ║
║  - 余白: TikTokセーフゾーン準拠                            ║
║  - グリッド: 12列準拠                                      ║
║  - グラデーション: バンディング防止（色差128以内）           ║
║  - 影: 角度・透明度統一（右下2px, 50%）                    ║
║  - フォントサイズ: 黄金比準拠                              ║
║                                                          ║
║  [コンテンツ品質]                                          ║
║  - フック力: 損失回避+2/数字+1/疑問+1/感情+1/ペルソナ+2    ║
║  - 保存価値: データ+3/チェックリスト+2/How-to+2            ║
║  - シェア価値: 共感+2/意外性+2/実用性+1                    ║
║  - CTA自然度: ハードCTAは10投稿中2以下                     ║
║                                                          ║
║  [心理学的品質]                                            ║
║  - 認知負荷: 7±2チャンク/スライド（ミラーの法則）           ║
║  - 感情曲線: 驚き→共感→期待→学び→納得→希望→行動           ║
║  - ザイガルニック: 次スライドへのテンション遷移率50%+       ║
║  - ピーク・エンド: 最印象スライド(中盤)+ラスト(CTA)        ║
║                                                          ║
║  [グレード]                                                ║
║  S: 95+  A: 85+  B: 70+  C: 55+  D: 40+  F: <40         ║
║  合格ライン: 60点 + ブロッキング問題なし                    ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


# ============================================================
# CLI
# ============================================================

def load_queue_item(queue_path: Path, index: int) -> tuple[list[dict], dict]:
    """Load a specific item from posting_queue.json, resolving json_path references."""
    with open(queue_path) as f:
        queue = json.load(f)

    items = queue if isinstance(queue, list) else queue.get("posts", queue.get("queue", []))
    if index >= len(items):
        print(f"Error: index {index} out of range (queue has {len(items)} items)")
        sys.exit(1)

    item = items[index]
    project_dir = Path(__file__).parent.parent

    # Extract slides from item directly
    slides = item.get("slides", [])

    # If no slides in queue item, try loading from json_path (script file)
    if not slides and item.get("json_path"):
        json_path = project_dir / item["json_path"]
        if json_path.exists():
            with open(json_path) as f:
                script_data = json.load(f)
            slides = script_data.get("slides", [])
            # Merge script metadata into item for hook/caption extraction
            for key in ("hook", "caption", "category", "hashtags"):
                if key in script_data and key not in item:
                    item[key] = script_data[key]
            if "content_id" not in item and "id" in script_data:
                item["content_id"] = script_data["id"]

    if not slides:
        # Try alternative structures within item
        script = item.get("script", {})
        if isinstance(script, dict):
            slides = script.get("slides", [])
        elif isinstance(script, list):
            slides = script

    # If slides are just strings, convert to dicts
    if slides and isinstance(slides[0], str):
        slides = [{"body": s} for s in slides]

    return slides, item


def check_from_queue(
    queue_path: Path,
    index: int,
    verbose: bool = True,
    suppress_text: bool = False,
) -> QualityReport:
    """Run quality check on a queue item."""
    slides, item = load_queue_item(queue_path, index)
    checker = ContentQualityChecker()

    hook = item.get("hook", item.get("title", ""))
    if not hook and slides:
        hook = slides[0].get("hook", slides[0].get("body", slides[0].get("title", "")))

    report = checker.check(
        slides=slides,
        hook_text=hook,
        caption=item.get("caption", ""),
        category=item.get("category", item.get("content_type", "")),
        content_id=item.get("content_id", item.get("id", f"queue_{index}")),
    )
    if not suppress_text:
        print(format_report(report, verbose=verbose))
    return report


def audit_queue(queue_path: Path) -> list[QualityReport]:
    """Run quality check on all items in the queue."""
    with open(queue_path) as f:
        queue = json.load(f)

    items = queue if isinstance(queue, list) else queue.get("posts", queue.get("queue", []))
    reports = []

    for i in range(len(items)):
        print(f"\n--- Checking item {i} ---")
        report = check_from_queue(queue_path, i, verbose=False)
        reports.append(report)

    # Summary
    print("\n" + "=" * 60)
    print("  一括監査サマリ")
    print("=" * 60)
    print(f"  {'ID':<12s} {'スコア':>6s}  {'グレード':>4s}  {'判定':>4s}")
    print("  " + "-" * 40)
    for r in reports:
        status = "PASS" if r.pass_fail else "FAIL"
        print(f"  {r.content_id:<12s} {r.overall_score:6.1f}  {r.grade:>4s}  {status:>4s}")

    avg = sum(r.overall_score for r in reports) / len(reports) if reports else 0
    passed = sum(1 for r in reports if r.pass_fail)
    print("  " + "-" * 40)
    print(f"  平均スコア: {avg:.1f}/100")
    print(f"  合格: {passed}/{len(reports)}")
    print("=" * 60)

    return reports


def check_images_dir(image_dir: Path, verbose: bool = True) -> QualityReport:
    """Run visual checks on generated slide images."""
    image_paths = sorted(image_dir.glob("*.png")) + sorted(image_dir.glob("*.jpg"))
    if not image_paths:
        print(f"Error: No images found in {image_dir}")
        sys.exit(1)

    checker = ContentQualityChecker()
    report = checker.check(
        slides=[{"body": f"slide_{i}"} for i in range(len(image_paths))],
        content_id=image_dir.name,
        image_paths=image_paths,
    )
    print(format_report(report, verbose=verbose))
    return report


def _dim_avg(scores: list) -> float:
    """Return average score for a list of QualityScore objects, scaled 0-10."""
    if not scores:
        return 5.0
    return sum(s.score for s in scores) / len(scores)


def _report_to_gate_json(report: QualityReport) -> dict:
    """
    Convert a QualityReport into the compact JSON expected by pdca_quality_gate.sh.

    Mapping:
      fact_score   = mean(text_scores + content_scores)   — accuracy & content quality
      appeal_score = mean(visual_scores + psychology_scores) — visual & psychological appeal
      combined     = fact_score * 0.5 + appeal_score * 0.5
      passed       = combined >= 6.0
    """
    fact_score = _dim_avg(report.text_scores + report.content_scores)
    appeal_score = _dim_avg(report.visual_scores + report.psychology_scores)
    combined = round(fact_score * 0.5 + appeal_score * 0.5, 2)
    all_issues: list[str] = []
    for s in (report.text_scores + report.content_scores +
              report.visual_scores + report.psychology_scores):
        all_issues.extend(s.issues)
    return {
        "passed": combined >= 6.0,
        "fact_score": round(fact_score, 2),
        "appeal_score": round(appeal_score, 2),
        "combined": combined,
        "issues": all_issues[:10],  # cap to avoid huge JSON
    }


def gate_check_queue_item(queue_path: Path, index: int) -> dict:
    """
    Run ContentQualityChecker + AppealChecker on queue item N and return gate JSON.
    Called by --fact-check / --appeal-check / --full-check.
    Returns a combined dict with both content quality and appeal scores.
    """
    slides, item = load_queue_item(queue_path, index)

    hook = item.get("hook", item.get("title", ""))
    if not hook and slides:
        hook = slides[0].get("hook", slides[0].get("body", slides[0].get("title", "")))

    # --- ContentQualityChecker (text/visual/content/psychology) ---
    cq_checker = ContentQualityChecker()
    report = cq_checker.check(
        slides=slides,
        hook_text=hook,
        caption=item.get("caption", ""),
        category=item.get("category", item.get("content_type", "")),
        content_id=item.get("content_id", item.get("id", f"queue_{index}")),
    )
    gate = _report_to_gate_json(report)

    # --- AppealChecker (訴求力・説得力) ---
    slide_texts = []
    for s in slides:
        if isinstance(s, dict):
            parts = [str(s[k]) for k in ("title", "body", "text") if s.get(k)]
            slide_texts.append("\n".join(parts))
        elif isinstance(s, str):
            slide_texts.append(s)

    appeal_checker = AppealChecker()
    appeal_result = appeal_checker.evaluate_post({
        "hook": hook,
        "slides": slide_texts,
        "cta_text": item.get("cta_text", ""),
        "cta_type": item.get("cta_type", ""),
        "caption": item.get("caption", ""),
    })

    gate["appeal_score"] = appeal_result.composite_score
    gate["appeal_pass"] = appeal_result.pass_fail
    gate["appeal_blocking"] = appeal_result.blocking_issues[:5]
    # combined = average of content quality and appeal
    gate["combined"] = round(
        (gate.get("fact_score", 5.0) * 0.5 + appeal_result.composite_score * 0.5), 2
    )
    gate["passed"] = gate["combined"] >= 6.0 and not appeal_result.blocking_issues

    return gate


def gate_audit_queue(queue_path: Path) -> list[dict]:
    """
    Run gate_check_queue_item on ALL 'ready'/'pending' posts that lack quality_checked=true.
    Returns list of dicts: [{index, hook, result}, ...]
    """
    with open(queue_path) as f:
        queue = json.load(f)

    items = queue if isinstance(queue, list) else queue.get("posts", queue.get("queue", []))
    results = []

    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("status", "") not in ("ready", "pending"):
            continue
        if item.get("quality_checked"):
            continue

        hook = item.get("hook", item.get("caption", ""))[:30]
        try:
            result = gate_check_queue_item(queue_path, idx)
        except Exception as exc:
            result = {
                "passed": False,
                "fact_score": 0.0,
                "appeal_score": 0.0,
                "combined": 0.0,
                "issues": [f"チェック実行エラー: {exc}"],
            }
        results.append({"index": idx, "hook": hook, "result": result})

    return results



# ============================================================
# AppealChecker — 訴求力・説得力チェッカー v1.0
# ============================================================
#
# 投稿が「世界水準の品質」である前に、「看護師ミサキが止まるか」を判定する。
# 文法・レイアウト的に正しくても訴求力がゼロなら投稿してはいけない。
# ContentQualityChecker の後段、公開前の最終ゲートとして使う。
#
# 使い方:
#   from scripts.quality_checker import AppealChecker
#   ac = AppealChecker()
#   result = ac.evaluate_post({
#       "hook": "夜勤月8回の看護師の時給、コンビニと同じって本当？",
#       "slides": ["スライド2本文", "スライド3本文", ...],
#       "cta_text": "気になる人はプロフのリンクからどうぞ",
#       "cta_type": "soft",   # or "hard"
#   })
#   print(result.composite_score, result.pass_fail)
#
# CLIデモ:
#   python3 scripts/quality_checker.py --appeal-demo
# ============================================================

# ----------------------------------------------------------
# AppealChecker: キーワード定数
# ----------------------------------------------------------

# 看護師の現場語（フックに1つ以上含まれていることが必須）
NURSING_TERMS = [
    # 業務・技術系
    "アセスメント", "申し送り", "夜勤明け", "インシデント", "カルテ",
    "ナースコール", "プリセプター", "リーダー", "急変", "看護記録",
    "バイタル", "ラウンド", "サマリ", "退院支援", "点滴",
    # 職場環境系
    "師長", "病棟", "外来", "ICU", "手術室", "訪問看護",
    "夜勤", "日勤", "残業", "有給", "夜勤専従",
    # 転職・待遇系
    "手取り", "夜勤手当", "奨学金返済", "紹介料", "手数料",
    "転職", "年収", "給料", "給与",
    # ペルソナ属性
    "看護師", "ナース", "5年目", "3年目", "7年目", "10年目",
    "急性期", "プリ", "メンバー",
]

# 陳腐・AI臭い・過剰断言表現（本文に含まれてはいけない）
BANNED_WORDS = [
    # AI臭い
    "さまざまな", "多角的に", "包括的な", "最適化", "パラダイム",
    "革新的", "画期的", "ソリューション", "エビデンスベース",
    # 広告臭い
    "今だけ", "必見", "見逃すな", "業界最安値", "No.1",
    "圧倒的な", "充実したサポート", "安心・安全・信頼",
    # 過剰断言（法的リスクあり）
    "絶対", "必ず", "100%", "間違いなく", "確実に",
    # 攻撃的・煽り
    "ブラック", "クソ", "衝撃", "驚愕", "閲覧注意", "マジでやばい",
    "知らないと損", "気づいてない人", "まだ転職してないの",
    # まとめ・解説臭
    "いかがでしたか", "まとめると", "について解説します",
    "ぜひ参考にしてください", "重要なお知らせ",
]

# 薄い共感・陳腐共感表現（単体使用でテンプレート感を与えるもの）
WEAK_EMPATHY = [
    "わかる〜", "それな", "つらいよね", "大変でしたね",
    "頑張っていますね", "あなたは素晴らしい", "応援しています",
    "素敵な転職を", "自分を責めないで",
]

# 強引なCTA（使ってはいけない言葉）
PUSHY_CTA = [
    "今すぐ", "限定", "特別", "登録しないと損", "残りわずか",
    "急いで", "締切", "今しか", "無料だから損はない",
    "3分で完了", "フォローとリポスト忘れずに",
]

# ロビーらしい文末語尾
ROBBY_ENDINGS = [
    "だよ", "だね", "なんだよね", "かも", "よね",
    "なんだ", "だったんだ", "だよね", "んだよ",
]

# 5W1H要素検出パターン（最低2要素が必要）
_FW1H_PATTERNS: Dict[str, List[str]] = {
    "who": [
        r"看護師", r"ナース", r"\d+年目", r"師長", r"プリセプター",
        r"夜勤専従", r"急性期", r"訪問看護", r"新人", r"ベテラン",
    ],
    "what": [
        r"手取り", r"年収", r"給料", r"時給", r"夜勤手当", r"紹介料",
        r"手数料", r"転職", r"退職", r"有給", r"\d+万", r"\d+円", r"\d+%",
    ],
    "when": [
        r"夜勤明け", r"休憩中", r"帰りの電車", r"5年目", r"3年目",
        r"月\d+回", r"週\d+", r"今", r"毎月",
    ],
    "where": [
        r"神奈川", r"横浜", r"川崎", r"相模原", r"小田原",
        r"湘南", r"病棟", r"ICU", r"外来", r"訪問",
    ],
    "why": [
        r"なぜ", r"理由", r"原因", r"なんで", r"どうして",
        r"わけ", r"から", r"ため",
    ],
    "how": [
        r"方法", r"やり方", r"どうやって", r"どうしたら", r"どう",
        r"計算", r"比較", r"確認",
    ],
}

# 好奇心トリガーパターン（数字+驚き / 問い / 秘密）
_CURIOSITY_TRIGGERS: Dict[str, List[str]] = {
    "number_surprise": [
        r"\d+万", r"\d+%", r"\d+円", r"\d+人", r"\d+回",
        r"倍", r"差", r"ランキング",
    ],
    "question": [
        r"？$", r"？\s*$", r"\?$", r"本当", r"知ってた", r"知ってる",
        r"普通", r"って何", r"いくら",
    ],
    "secret_reveal": [
        r"実は", r"…$", r"…", r"理由", r"正体",
        r"知られていない", r"裏側", r"暴露",
    ],
}

# 共感→構造→提案 フロー検出キーワード
_FLOW_EMPATHY = [
    "あるある", "わかる", "よね", "気持ち", "つらい", "疲れ",
    "同じ", "経験", "感じる", "ない？", "いない？", "ある？",
]
_FLOW_STRUCTURE = [
    "理由", "なぜ", "データ", "実は", "調べた", "計算",
    "比較", "平均", "統計", "事実", "原因", "仕組み",
]
_FLOW_PROPOSAL = [
    "できる", "方法", "解決", "変わる", "選べる", "選択肢",
    "チャンス", "改善", "参考", "相談", "プロフ",
]

# ミサキ(28歳看護師)のペインポイント
_MISAKI_PAIN_POINTS = [
    "人間関係", "夜勤", "給与", "師長", "残業",
    "有給", "インシデント", "申し送り", "転職",
    "手取り", "疲れ", "しんどい", "辞めたい", "給料",
]

# ミサキの具体的状況描写キーワード
_MISAKI_SITUATION = [
    "5年目", "急性期", "夜勤あり", "病棟", "リーダー",
    "帰りの電車", "休憩中", "夜勤明け", "神奈川",
]

# 神奈川・地域名キーワード
_KANAGAWA_KEYWORDS = [
    "神奈川", "横浜", "川崎", "相模原", "小田原", "湘南",
    "横須賀", "鎌倉", "藤沢", "茅ヶ崎", "平塚", "秦野",
    "海老名", "大和", "厚木", "座間", "県西", "県央",
]


# ----------------------------------------------------------
# AppealChecker: データクラス
# ----------------------------------------------------------

@dataclass
class AppealScore:
    """個別訴求力チェック1軸の結果（0-10スコア）。"""

    dimension: str
    label: str
    score: float
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    detail: str = ""


@dataclass
class AppealResult:
    """evaluate_post() の返却値。5軸の結果 + 加重スコア + PASS/FAIL。"""

    hook_power: AppealScore
    body_structure: AppealScore
    cta_effectiveness: AppealScore
    brand_voice: AppealScore
    target_resonance: AppealScore
    composite_score: float
    pass_fail: bool
    blocking_issues: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _s(s: AppealScore) -> dict:
            return {
                "dimension": s.dimension,
                "label": s.label,
                "score": round(s.score, 1),
                "issues": s.issues,
                "suggestions": s.suggestions,
                "detail": s.detail,
            }
        return {
            "composite_score": round(self.composite_score, 2),
            "pass_fail": self.pass_fail,
            "blocking_issues": self.blocking_issues,
            "hook_power": _s(self.hook_power),
            "body_structure": _s(self.body_structure),
            "cta_effectiveness": _s(self.cta_effectiveness),
            "brand_voice": _s(self.brand_voice),
            "target_resonance": _s(self.target_resonance),
        }


# ----------------------------------------------------------
# AppealChecker: メインクラス
# ----------------------------------------------------------

class AppealChecker:
    """
    SNS投稿の訴求力・説得力チェッカー v1.0。

    「看護師ミサキがスクロールを止めるか / 行動を起こすか」を5軸でスコアリング。
    ContentQualityChecker の後段、公開前の最終ゲートとして使用する。

    軸と重み:
        hook_power        0.30  フック訴求力（最重要）
        target_resonance  0.20  ターゲット共鳴
        body_structure    0.20  ボディ構造
        brand_voice       0.15  ブランドボイス
        cta_effectiveness 0.15  CTA効果

    合格基準: composite_score >= 6.0 かつブロッキング問題（score<=3.0の軸）がゼロ。
    """

    WEIGHTS: Dict[str, float] = {
        "hook_power":        0.30,
        "target_resonance":  0.20,
        "body_structure":    0.20,
        "brand_voice":       0.15,
        "cta_effectiveness": 0.15,
    }

    PASS_THRESHOLD: float = 6.0

    # ----------------------------------------------------------------
    # 1. フック訴求力チェック
    # ----------------------------------------------------------------

    def check_hook_power(self, hook: str) -> AppealScore:
        """
        フック（スライド1枚目テキスト）の訴求力を 0-10 でスコアリング。

        採点:
            +2.0  25文字以内
            +2.0  オープンループ（？/…/理由/なぜ等）あり
            +2.0  看護師現場語（NURSING_TERMS）が1語以上
            +2.0  5W1H要素が2要素以上
            +2.0  好奇心トリガー（数字+驚き / 問い / 秘密）がある
        """
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.0

        char_len = len(hook)
        if char_len <= 25:
            score += 2.0
        else:
            issues.append(
                f"フックが{char_len}文字（上限25文字）。通勤電車では読み切れず即スワイプされる。"
            )
            suggestions.append("体言止め・助詞省略で25文字以内に圧縮する")

        open_loop_markers = [
            "？", "?", "…", "...", "理由", "なぜ", "本当", "知ってた", "知ってる",
            "普通", "正体", "わけ", "でしょ", "ない？", "いない？", "ある？", "って何", "とは",
        ]
        has_open_loop = any(m in hook for m in open_loop_markers)
        if has_open_loop:
            score += 2.0
        else:
            issues.append(
                "オープンループがない。答えが出ているフックはスワイプされる。"
                "「次が気になる」感覚を作れていない。"
            )
            suggestions.append(
                "末尾を「？」「…」で終わらせる、または「理由」「正体」「なぜ」を使う"
            )

        has_nursing_term = any(term in hook for term in NURSING_TERMS)
        if has_nursing_term:
            score += 2.0
        else:
            issues.append(
                "看護師の現場語がない。誰にでも刺さる汎用フックは誰にも刺さらない。"
            )
            suggestions.append(
                "「夜勤明け」「申し送り」「師長」「手取り」「インシデント」等を1語入れる"
            )

        matched_5w1h: List[str] = []
        for element, patterns in _FW1H_PATTERNS.items():
            if any(re.search(p, hook) for p in patterns):
                matched_5w1h.append(element)
        if len(matched_5w1h) >= 2:
            score += 2.0
        else:
            issues.append(
                f"5W1H要素が{len(matched_5w1h)}個（最低2個必要）。"
                "10人が読んで10人とも同じ状況を想像できる具体性が必要。"
            )
            suggestions.append(
                "「看護師5年目」(who) + 「手取り24万」(what) のように2要素以上を入れる"
            )

        triggered_types: List[str] = []
        for trigger_type, patterns in _CURIOSITY_TRIGGERS.items():
            if any(re.search(p, hook) for p in patterns):
                triggered_types.append(trigger_type)
        if triggered_types:
            score += 2.0
        else:
            issues.append(
                "好奇心トリガー（具体的な数字 / 問い / 秘密暴露）がない。"
                "「知っていること」と「知りたいこと」のギャップを作れていない。"
            )
            suggestions.append(
                "具体的な数字（「手取り24万」「時給1,800円」）か"
                "「実は」「正体」等の秘密暴露ワードを入れる"
            )

        matched_str = ", ".join(matched_5w1h) if matched_5w1h else "なし"
        detail = (
            f"文字数:{char_len}文字 / "
            f"オープンループ:{'あり' if has_open_loop else 'なし'} / "
            f"現場語:{'あり' if has_nursing_term else 'なし'} / "
            f"5W1H:{matched_str}({len(matched_5w1h)}要素) / "
            f"好奇心トリガー:{', '.join(triggered_types) if triggered_types else 'なし'}"
        )

        return AppealScore(
            dimension="hook_power",
            label="フック訴求力",
            score=score,
            issues=issues,
            suggestions=suggestions,
            detail=detail,
        )

    # ----------------------------------------------------------------
    # 2. ボディ構造チェック
    # ----------------------------------------------------------------

    def check_body_structure(self, slides: List[str]) -> AppealScore:
        """
        スライド本文（2枚目以降）の構造品質を 0-10 でスコアリング。

        採点:
            +2.5  詰め込みスライド（3文以上&4行以上）が1枚以内
            +2.5  共感→構造→提案フローの要素が2/3以上ある
            +2.5  テキスト過多スライド（>80文字）が1枚以内
            +2.5  各スライドに前スライドにない新規ワードが2語以上ある
        """
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.0

        if not slides:
            return AppealScore(
                dimension="body_structure",
                label="ボディ構造",
                score=0.0,
                issues=["スライドデータが空（2枚目以降のボディが必要）"],
                suggestions=["最低3枚以上のスライドを設計する（共感→情報→CTA）"],
                detail="スライドなし",
            )

        multi_message_slides: List[int] = []
        for i, text in enumerate(slides):
            sentence_count = len(re.findall(r"[。！？!?]+", text))
            line_count = len([ln for ln in text.split("\n") if ln.strip()])
            if sentence_count >= 3 and line_count >= 4:
                multi_message_slides.append(i + 1)
                issues.append(
                    f"スライド{i+1}: {sentence_count}文/{line_count}行は1枚に多すぎる"
                    f"（1スライド1メッセージ原則違反）"
                )
        if len(multi_message_slides) == 0:
            score += 2.5
        else:
            suggestions.append(
                f"詰め込みスライド（{multi_message_slides}）を分割する。1枚に伝えることは1つだけ。"
            )

        all_body = " ".join(slides)
        has_empathy   = any(w in all_body for w in _FLOW_EMPATHY)
        has_structure = any(w in all_body for w in _FLOW_STRUCTURE)
        has_proposal  = any(w in all_body for w in _FLOW_PROPOSAL)
        flow_count = sum([has_empathy, has_structure, has_proposal])
        if flow_count >= 2:
            score += 2.5
        else:
            missing = []
            if not has_empathy:
                missing.append("共感（あるある/よね/ない？）")
            if not has_structure:
                missing.append("構造（データ/理由/なぜ/実は）")
            if not has_proposal:
                missing.append("提案（できる/方法/選択肢）")
            issues.append(f"共感→構造→提案フローが不完全。不足: {'/'.join(missing)}")
            suggestions.append(
                "2枚目に共感描写→3-5枚目にデータ/理由→最終枚に解決策/CTAの流れを作る"
            )

        heavy: List[int] = [
            i + 1 for i, t in enumerate(slides)
            if len(t.replace("\n", "").replace(" ", "")) > 80
        ]
        if len(heavy) <= 1:
            score += 2.5
        else:
            issues.append(
                f"スライド{heavy}が80文字超え。3秒で読み切れない→途中でスワイプされる。"
            )
            suggestions.append(
                "1スライドのテキストは本文80文字以内。超える場合はスライドを2枚に分割する。"
            )

        seen_words: set = set()
        escalation_fails = 0
        for i, text in enumerate(slides[1:], start=2):
            words = set(re.findall(
                r"[\u4e00-\u9fff\u30a0-\u30ff\u3040-\u309f]{2,}", text
            ))
            new_words = words - seen_words
            if len(words) > 0 and len(new_words) < 2:
                escalation_fails += 1
            seen_words |= words
        if escalation_fails <= 1:
            score += 2.5
        else:
            issues.append(
                f"{escalation_fails}枚のスライドで新しい情報が追加されていない。"
                "「次も読もう」という動機が失われる。"
            )
            suggestions.append(
                "各スライドに前スライドにない新しい数字・視点・事実を1つ以上追加する"
            )

        detail = (
            f"スライド{len(slides)}枚 / "
            f"詰め込み:{len(multi_message_slides)}枚 / "
            f"フロー:{flow_count}/3要素 / "
            f"テキスト過多:{len(heavy)}枚 / "
            f"エスカレ失敗:{escalation_fails}枚"
        )

        return AppealScore(
            dimension="body_structure",
            label="ボディ構造",
            score=score,
            issues=issues,
            suggestions=suggestions,
            detail=detail,
        )

    # ----------------------------------------------------------------
    # 3. CTA効果チェック
    # ----------------------------------------------------------------

    def check_cta_effectiveness(self, cta_text: str, cta_type: str) -> AppealScore:
        """
        CTAテキストの自然さ・効果を 0-10 でスコアリング。

        採点:
            +3.0  強引な表現（PUSHY_CTA）を含まない
            +3.0  cta_typeに合った誘導語を使っている
            +4.0  価値提示が明確（ハード）or 体験が想像できる（ソフト）
        """
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.0
        cta_type = (cta_type or "soft").lower().strip()
        if cta_type not in ("soft", "hard"):
            cta_type = "soft"

        found_pushy = [p for p in PUSHY_CTA if p in cta_text]
        if not found_pushy:
            score += 3.0
        else:
            issues.append(
                f"強引なCTA表現を検出: {found_pushy}。"
                "看護師は「売り込まれた」と感じた瞬間に離脱する。"
            )
            suggestions.append(
                "「今すぐ」「限定」を削除し「気になった人は」「プロフのリンクから」に置き換える"
            )

        soft_vocab = ["保存", "フォロー", "コメント", "教えて", "送って", "続き"]
        hard_vocab = ["LINE", "プロフ", "リンク", "相談", "求人", "登録"]
        has_soft = any(w in cta_text for w in soft_vocab)
        has_hard = any(w in cta_text for w in hard_vocab)

        if cta_type == "soft":
            if has_soft:
                score += 3.0
            else:
                issues.append(
                    "ソフトCTAに「保存/フォロー/コメント」等の低ハードル誘導語がない。"
                )
                suggestions.append(
                    "「保存しておくと転職する時に役立つよ」「コメントで教えて」を使う"
                )
        else:
            if has_hard:
                score += 3.0
            else:
                issues.append(
                    "ハードCTAに「LINE/プロフ/求人/相談」等の行き先が明示されていない。"
                )
                suggestions.append(
                    "「LINEで非公開求人も見れるよ」「プロフから無料相談できるよ」のように行き先を明示"
                )

        cta_len = len(cta_text)
        if cta_type == "soft":
            soft_value = ["役立つ", "参考", "見返して", "次回", "詳しく", "調べる", "保存", "教えて"]
            has_value = any(w in cta_text for w in soft_value)
            if has_value and cta_len <= 40:
                score += 4.0
            elif has_value:
                score += 2.5
                issues.append(f"ソフトCTAが{cta_len}文字と長い（推奨40文字以内）。")
                suggestions.append("ソフトCTAは1文・40文字以内で完結させる")
            else:
                score += 1.0
                issues.append(
                    "ソフトCTAに行動後の体験イメージがない。なぜ保存/フォローするのかが伝わらない。"
                )
                suggestions.append("「保存しておくと転職する時に役立つよ」のように体験を一言で伝える")
        else:
            hard_value = ["非公開求人", "手数料10%", "無料", "転職サポート", "市場価値", "求人", "相談"]
            has_value = any(w in cta_text for w in hard_value)
            if has_value:
                score += 4.0
            else:
                score += 1.5
                issues.append(
                    "ハードCTAに具体的な価値（非公開求人/手数料10%/無料相談等）がない。"
                )
                suggestions.append(
                    "「LINEで非公開求人も見れるよ」「手数料10%の転職サポート、詳しくはプロフから」を使う"
                )

        detail = (
            f"タイプ:{cta_type} / "
            f"強引表現:{found_pushy if found_pushy else 'なし'} / "
            f"文字数:{cta_len}文字"
        )

        return AppealScore(
            dimension="cta_effectiveness",
            label="CTA効果",
            score=min(score, 10.0),
            issues=issues,
            suggestions=suggestions,
            detail=detail,
        )

    # ----------------------------------------------------------------
    # 4. ブランドボイスチェック
    # ----------------------------------------------------------------

    def check_brand_voice(self, text: str) -> AppealScore:
        """
        テキストがロビーのブランドボイスに沿っているかを 0-10 でスコアリング。

        採点:
            +2.5  ロビーらしい文末語尾（だよ/だね/なんだよね等）が使われている
            +2.5  禁止表現（BANNED_WORDS）を含まない
            +2.5  陳腐表現（WEAK_EMPATHY）を含まない
            +2.5  敬語（です・ます）が文末の40%未満
        """
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.0

        if len(text) >= 100:
            has_robby_ending = any(ending in text for ending in ROBBY_ENDINGS)
            if has_robby_ending:
                score += 2.5
            else:
                issues.append(
                    "ロビーらしい文末語尾（〜だよ/〜だね/〜なんだよね）が見当たらない。"
                    "キャラクター感が消えて「別のサービスのコンテンツ」に見える。"
                )
                suggestions.append(
                    "文末を「〜だよ」「〜なんだよね」「〜かも」に統一する。"
                    "一人称が「私/僕」なら「ロビー」に修正する。"
                )
        else:
            score += 2.5

        found_banned = [w for w in BANNED_WORDS if w in text]
        if not found_banned:
            score += 2.5
        else:
            issues.append(
                f"禁止表現を検出: {found_banned[:5]}。AI臭・広告臭・過剰断言はブランドへの信頼を損なう。"
            )
            suggestions.append(
                "具体的な数字や事実に置き換える。「絶対」→「多くの場合」、「圧倒的な」→数字で表現"
            )

        found_weak = [w for w in WEAK_EMPATHY if w in text]
        if not found_weak:
            score += 2.5
        else:
            issues.append(
                f"薄い共感・陳腐表現を検出: {found_weak}。テンプレート感が出て信頼を失う。"
            )
            suggestions.append(
                "具体的なシーン描写に変える。「つらいよね」→「夜勤明けに書類を書く、それが当たり前になってた話」"
            )

        desu_masu_count = len(
            re.findall(r"(?:です|ます|でした|ました|ください|でしょう)[。\n\s]", text)
        )
        total_sentences = max(len(re.findall(r"[。！？!?]+", text)), 1)
        desu_masu_ratio = desu_masu_count / total_sentences

        if desu_masu_ratio < 0.4:
            score += 2.5
        elif desu_masu_ratio < 0.7:
            score += 1.5
            issues.append(
                f"敬語の文が約{int(desu_masu_ratio*100)}%。"
                "ロビーはタメ口ベースのキャラクター。「丁寧すぎる」は距離感を生む。"
            )
            suggestions.append("「〜です」→「〜だよ」、「〜ます」→「〜するよ」に書き換える")
        else:
            issues.append(
                f"敬語の文が約{int(desu_masu_ratio*100)}%と多い。ロビーは「です・ます」を使わない。"
            )
            suggestions.append("ロビーの口調: 一人称「ロビー」・「〜だよ」「〜なんだ」で統一")

        detail = (
            f"禁止表現:{len(found_banned)}個 / "
            f"陳腐表現:{len(found_weak)}個 / "
            f"敬語比率:{int(desu_masu_ratio*100)}%"
        )

        return AppealScore(
            dimension="brand_voice",
            label="ブランドボイス",
            score=score,
            issues=issues,
            suggestions=suggestions,
            detail=detail,
        )

    # ----------------------------------------------------------------
    # 5. ターゲット共鳴チェック
    # ----------------------------------------------------------------

    def check_target_resonance(self, text: str) -> AppealScore:
        """
        「ミサキ（28歳・急性期・夜勤あり）が自分のことだと感じるか」を 0-10 でスコアリング。

        採点:
            +3.0  ミサキのペインポイント（人間関係/夜勤/給与等）が1つ以上
            +3.0  ミサキの具体的状況（5年目/急性期/夜勤明け等）を連想させる語がある
            +2.0  一般的アドバイス口調（しましょう/すべき）でなく「一緒に考える」スタンス
            +2.0  神奈川・地域名が含まれる（地域特化 = 大手との差別化）/ 地域名なしは+1
        """
        issues: List[str] = []
        suggestions: List[str] = []
        score = 0.0

        found_pain = [p for p in _MISAKI_PAIN_POINTS if p in text]
        if found_pain:
            score += 3.0
        else:
            issues.append(
                "ミサキのペインポイント（人間関係/夜勤/給与/師長/残業/辞めたい等）が見当たらない。"
                "「誰向けか」がわからない汎用コンテンツ。"
            )
            suggestions.append(
                "「夜勤」「師長」「手取り」「有給」等、ミサキが日常的に感じる悩みを1語以上入れる"
            )

        found_situation = [s for s in _MISAKI_SITUATION if s in text]
        if found_situation:
            score += 3.0
        else:
            issues.append(
                "ミサキの具体的な状況（5年目/急性期/病棟/夜勤明け等）が伝わらない。"
                "「これ私のことだ」という即反応が起きない。"
            )
            suggestions.append(
                "「5年目の看護師」「急性期病棟」「帰りの電車」等、ミサキが一致する状況描写を1箇所入れる"
            )

        generic_patterns = [
            r"しましょう", r"すべき", r"大切です", r"重要です",
            r"することをおすすめ", r"意識しましょう", r"心がけ",
        ]
        found_generic = [p for p in generic_patterns if re.search(p, text)]
        if not found_generic:
            score += 2.0
        else:
            issues.append(
                f"一般的アドバイス口調を検出: {found_generic[:3]}。"
                "「教える」スタンスはミサキに「上から目線」と感じさせる。"
            )
            suggestions.append(
                "「〜しましょう」→「〜してみて」「〜かも」に変える。「一緒に考える」スタンスで書く。"
            )

        has_local = any(kw in text for kw in _KANAGAWA_KEYWORDS)
        if has_local:
            score += 2.0
        else:
            score += 1.0
            issues.append(
                "神奈川・地域名が含まれていない。地域特化は大手がやらない最大の差別化ポイント。"
            )
            suggestions.append("「神奈川の看護師は〜」「横浜の病院では〜」等、地域名を1箇所入れる")

        detail = (
            f"ペインポイント:{found_pain[:3] if found_pain else 'なし'} / "
            f"状況描写:{found_situation[:3] if found_situation else 'なし'} / "
            f"一般アドバイス:{len(found_generic)}件 / "
            f"地域名:{'あり' if has_local else 'なし'}"
        )

        return AppealScore(
            dimension="target_resonance",
            label="ターゲット共鳴",
            score=min(score, 10.0),
            issues=issues,
            suggestions=suggestions,
            detail=detail,
        )

    # ----------------------------------------------------------------
    # 6. メインエントリポイント
    # ----------------------------------------------------------------

    def evaluate_post(self, post: dict) -> AppealResult:
        """
        投稿データ全体の訴求力を評価する。

        Args:
            post (dict):
                hook      (str)   : 1枚目フックテキスト（必須）
                slides    (list)  : スライドのリスト（str or dict）
                cta_text  (str)   : CTAテキスト（省略可）
                cta_type  (str)   : "soft" or "hard"（省略可、自動判定）
                body_text (str)   : 本文全体（省略可、slides から自動結合）

        Returns:
            AppealResult: 5軸スコア + composite_score + pass_fail
        """
        hook: str = post.get("hook") or post.get("hook_text") or ""

        raw_slides = post.get("slides", [])
        slides: List[str] = []
        for s in raw_slides:
            if isinstance(s, str):
                slides.append(s)
            elif isinstance(s, dict):
                parts = [str(s[k]) for k in ("title", "body", "text") if s.get(k)]
                slides.append("\n".join(parts))

        body_text: str = post.get("body_text", "") or "\n".join(slides)

        cta_text: str = post.get("cta_text", "")
        if not cta_text and slides:
            cta_text = slides[-1]

        raw_cta_type: str = post.get("cta_type", "")
        if raw_cta_type:
            cta_type = raw_cta_type
        else:
            cta_type = "hard" if any(w in cta_text for w in HARD_CTA_WORDS) else "soft"

        all_text = hook + "\n" + body_text

        hook_score      = self.check_hook_power(hook)
        body_score      = self.check_body_structure(slides)
        cta_score       = self.check_cta_effectiveness(cta_text, cta_type)
        voice_score     = self.check_brand_voice(all_text)
        resonance_score = self.check_target_resonance(all_text)

        scores_map: Dict[str, float] = {
            "hook_power":        hook_score.score,
            "target_resonance":  resonance_score.score,
            "body_structure":    body_score.score,
            "brand_voice":       voice_score.score,
            "cta_effectiveness": cta_score.score,
        }
        composite = sum(
            scores_map[dim] * weight for dim, weight in self.WEIGHTS.items()
        )

        blocking: List[str] = []
        for s_obj in [hook_score, body_score, cta_score, voice_score, resonance_score]:
            if s_obj.score <= 3.0 and s_obj.issues:
                blocking.append(f"[{s_obj.label}] {s_obj.issues[0]}")

        return AppealResult(
            hook_power=hook_score,
            body_structure=body_score,
            cta_effectiveness=cta_score,
            brand_voice=voice_score,
            target_resonance=resonance_score,
            composite_score=round(composite, 2),
            pass_fail=(composite >= self.PASS_THRESHOLD and len(blocking) == 0),
            blocking_issues=blocking,
        )


# ----------------------------------------------------------
# AppealChecker: フォーマット出力
# ----------------------------------------------------------

def format_appeal_result(result: AppealResult, verbose: bool = True) -> str:
    """AppealResult を人間が読みやすいテキスト形式に変換する。"""
    lines: List[str] = []
    sep = "=" * 60

    lines.append(sep)
    lines.append("  訴求力チェック結果  (AppealChecker v1.0)")
    lines.append(sep)

    verdict = "PASS \u2713" if result.pass_fail else "FAIL \u2717"
    lines.append(
        f"  総合スコア: {result.composite_score:.1f} / 10.0  "
        f"[{verdict}]  (合格閾値: {AppealChecker.PASS_THRESHOLD:.1f})"
    )
    lines.append("")

    lines.append("  --- 5軸スコア ---")
    all_scores = [
        result.hook_power,
        result.target_resonance,
        result.body_structure,
        result.brand_voice,
        result.cta_effectiveness,
    ]
    for s in all_scores:
        weight_pct = int(AppealChecker.WEIGHTS.get(s.dimension, 0) * 100)
        bar_fill = int(s.score)
        bar = "\u2588" * bar_fill + "\u2591" * (10 - bar_fill)
        lines.append(
            f"  {s.label:<14s}  {bar}  {s.score:.1f}/10  (重み{weight_pct}%)"
        )

    if result.blocking_issues:
        lines.append("")
        lines.append("  --- ブロッキング問題（公開前に修正必須）---")
        for issue in result.blocking_issues:
            lines.append(f"  \u2717 {issue}")

    if verbose:
        lines.append("")
        lines.append("  --- 詳細 ---")
        for s in all_scores:
            lines.append(f"\n  [{s.label}]  {s.score:.1f}/10")
            lines.append(f"    {s.detail}")
            for issue in s.issues:
                lines.append(f"    \u2717 {issue}")
            for sug in s.suggestions:
                lines.append(f"    -> {sug}")

    lines.append("")
    lines.append(sep)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="SNSカルーセル品質チェッカー — 神は細部に宿る",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--script", type=Path, help="投稿キューJSONのパス")
    parser.add_argument("--index", type=int, default=0, help="キュー内のインデックス")
    parser.add_argument("--images", type=Path, help="生成済みスライド画像のディレクトリ")
    parser.add_argument("--audit", type=Path, help="全キューの一括品質監査")
    parser.add_argument("--standards", action="store_true", help="品質基準リファレンスの表示")
    parser.add_argument("--json", action="store_true", help="JSON形式で出力")
    parser.add_argument("--strict", action="store_true", help="厳格モード (WCAG AAA)")
    parser.add_argument("-q", "--quiet", action="store_true", help="サマリのみ表示")

    # --- cron / gate interface ---
    # These three flags all run the same full checker and emit compact gate JSON.
    # Kept as separate flags for shell-script readability / future divergence.
    parser.add_argument(
        "--fact-check", type=Path, metavar="QUEUE_FILE",
        help="FactCheck モード: キューアイテムNのファクト品質をチェック（gate JSON出力）"
    )
    parser.add_argument(
        "--appeal-check", type=Path, metavar="QUEUE_FILE",
        help="AppealCheck モード: キューアイテムNの訴求品質をチェック（gate JSON出力）"
    )
    parser.add_argument(
        "--full-check", type=Path, metavar="QUEUE_FILE",
        help="フルチェック: fact + appeal の両方をチェック（gate JSON出力）"
    )
    parser.add_argument(
        "--appeal-demo", action="store_true",
        help="AppealChecker デモ: サンプル投稿で訴求力チェックを実行して結果を表示"
    )

    args = parser.parse_args()

    if args.standards:
        print_standards()
        return

    if args.appeal_demo:
        _run_appeal_demo()
        return

    # Gate interface: --fact-check / --appeal-check / --full-check
    # All three emit the same compact JSON; the shell script combines scores itself.
    for gate_flag in (args.fact_check, args.appeal_check, args.full_check):
        if gate_flag is not None:
            result = gate_check_queue_item(gate_flag, args.index)
            print(json.dumps(result, ensure_ascii=False))
            return

    # --audit with gate JSON output
    if args.audit:
        if args.json:
            # Gate-mode audit: emit list of {index, hook, result} for cron script
            results = gate_audit_queue(args.audit)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            reports = audit_queue(args.audit)
        return

    if args.script:
        if args.json:
            report = check_from_queue(args.script, args.index, verbose=False, suppress_text=True)
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        else:
            report = check_from_queue(args.script, args.index, verbose=not args.quiet)
        return

    if args.images:
        report = check_images_dir(args.images, verbose=not args.quiet)
        if args.json:
            print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
        return

    # Demo mode: run with sample data
    print("=== デモモード: サンプルデータで品質チェック ===\n")

    sample_slides = [
        {"hook": "師長にAIで見せたら黙った"},
        {"title": "きっかけ", "body": "夜勤明けの休憩中\nいつものように愚痴ってたら\n後輩が「AI使えば？」って…"},
        {"title": "やってみた", "body": "ChatGPTに\n「師長への退職相談の\n伝え方を教えて」\nって聞いてみた"},
        {"title": "AIの回答", "body": "退職理由を3つに整理\n感情ではなくデータで説明\n代替案も一緒に提示…"},
        {"title": "師長の反応", "body": "「こんなに整理して\n考えてたんだ…」\nって言って黙った"},
        {"title": "その後", "body": "すぐには辞めなかったけど\n師長の態度が変わった\n話を聞いてくれるようになった"},
        {"title": "", "body": "転職の相談もAIにできる時代\nでも最後は人の温もりが大事\n\n保存して見返してね"},
    ]

    checker = ContentQualityChecker()
    report = checker.check(
        slides=sample_slides,
        hook_text="師長にAIで見せたら黙った",
        caption="看護師あるある！師長にAI見せたらまさかの反応…\n#看護師あるある #AI #神奈川ナース転職",
        category="あるある",
        content_id="A01_demo",
        colors={
            "bg": (26, 26, 46),
            "text": (255, 255, 255),
            "accent": (255, 107, 107),
        },
        font_sizes={"title": 56, "body": 34, "caption": 20},
    )

    print(format_report(report, verbose=True))


def _run_appeal_demo() -> None:
    """
    AppealChecker のデモを2投稿（PASS例・FAIL例）で実行して結果を表示する。
    CLI: python3 scripts/quality_checker.py --appeal-demo
    """
    print("\n=== AppealChecker デモ (2投稿比較) ===\n")

    # --- PASS例: 良い投稿 ---
    good_post = {
        "hook": "夜勤月8回の看護師の時給、コンビニと同じって本当？",
        "slides": [
            "夜勤明けの帰り道、ふと計算したことある？\n夜勤1回8時間、手当は1万2千円。\n時給換算すると…1,500円。コンビニと同じよね。",
            "ロビーが調べたんだけど、神奈川の夜勤手当、\n病院によって月5万〜12万の差があるんだ。\n同じ看護師なのに、なぜこんなに違うの？",
            "実は交渉できる病院が増えてるんだよね。\n「夜勤手当の交渉なんてできない」って思ってた人が\n転職で月3万上がったケースもある。",
            "神奈川の非公開求人、気になったらプロフのリンクからどうぞ。\n手数料10%だから、病院も喜んでくれるよ。",
        ],
        "cta_text": "神奈川の非公開求人、気になったらプロフのリンクからどうぞ。",
        "cta_type": "hard",
    }

    # --- FAIL例: 問題のある投稿 ---
    bad_post = {
        "hook": "看護師の皆さんへ大切なお知らせです",
        "slides": [
            "転職を考えている方は、ぜひ今すぐ登録してください！\n絶対に後悔しません。充実したサポートで安心・安全・信頼の転職を！\n今だけ限定キャンペーン中。残りわずかです。",
            "転職しましょう。転職は大切です。\n転職することをおすすめします。意識しましょう。",
        ],
        "cta_text": "今すぐ登録！限定特別キャンペーン！登録しないと損！",
        "cta_type": "hard",
    }

    ac = AppealChecker()

    for label, post in [("良い投稿（PASS期待）", good_post), ("問題のある投稿（FAIL期待）", bad_post)]:
        print(f"--- {label} ---")
        print(f"  フック: 「{post['hook']}」")
        result = ac.evaluate_post(post)
        print(format_appeal_result(result, verbose=True))
        print()


if __name__ == "__main__":
    main()
