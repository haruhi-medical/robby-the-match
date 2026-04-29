#!/usr/bin/env python3
"""
fix_proposer.py — 失敗パターンに対する worker.js 修正案を Claude Opus で生成

設計書 §5 (DESIGN.md) に準拠:
    - 出力: ``patches/<round>/<pattern_id>.diff`` + ``.meta.json``
    - 1ラウンドあたり最大3パッチ (上位失敗パターン3件)
    - risk_level は LLM 返答 + 機械的キーワード検査の **OR (より厳しい方)** を採用
        → LLM が "LOW" と言っても HMAC を触っていれば HIGH に格上げ

【入力】
    - verdicts ディレクトリ (gatekeeper の出力)
        各 ``<case_id>.json`` に ``passed: bool`` と ``blocking_reasons: [str]`` を含む想定
    - cases ディレクトリ (元のYAMLケース)  ※ optional コンテキスト
    - worker.js のパス

【出力】
    - patches/<round>/<pattern_id>.diff       (unified diff、空もあり得る)
    - patches/<round>/<pattern_id>.meta.json  (risk + reasoning + cluster info)
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 兄弟モジュール import
SCRIPTS_AUDIT = Path(__file__).resolve().parent.parent
if str(SCRIPTS_AUDIT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_AUDIT))

from lib.llm_client import LLMClient, LLMClientAPIError, LLMClientParseError  # noqa: E402


# ============================================================================
# Risk 判定キーワード
# ============================================================================

# diff にこれらのトークンが含まれたら HIGH に格上げ
HIGH_RISK_PATTERNS = [
    r"\bHMAC\b",
    r"\bsignature\b",
    r"\bverifySignature\b",
    r"\bx-line-signature\b",
    r"crypto\.subtle",
    r"\bSLACK_BOT_TOKEN\b",
    r"\bSLACK_CHANNEL_ID\b",
    r"\bLINE_CHANNEL_SECRET\b",
    r"\bLINE_CHANNEL_ACCESS_TOKEN\b",
    r"\bLINE_PUSH_SECRET\b",
    r"\bCHAT_SECRET_KEY\b",
    r"\bEMERGENCY_KEYWORDS\b",
    r"\bEMERGENCY_RESPONSE\b",
    r"\bcreateLineEntry\b",
    r"\brichmenu\b",
    r"\brichMenu\b",
]

MED_RISK_PATTERNS = [
    r"\bphase\b",
    r"\baica_turn\d?\b",
    r"\bnextPhase\b",
    r"\bmatching\b",
    r"\bil_area\b",
    r"\bapply_intent\b",
    r"\bauditTrail\b",
]


def classify_risk_by_diff(diff_text: str) -> Tuple[str, str]:
    """unified diff の **追加/削除行のみ** を見て risk を機械判定。

    Returns:
        ``(risk_level, reasoning)``
    """
    if not diff_text.strip():
        return "LOW", "empty diff"

    changed_lines: List[str] = []
    for line in diff_text.splitlines():
        # +++/--- ヘッダは除外
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith(("+", "-")):
            changed_lines.append(line[1:])
    body = "\n".join(changed_lines)

    high_hits = [pat for pat in HIGH_RISK_PATTERNS if re.search(pat, body)]
    if high_hits:
        return "HIGH", f"matched HIGH-risk patterns: {high_hits[:5]}"

    med_hits = [pat for pat in MED_RISK_PATTERNS if re.search(pat, body)]
    if med_hits:
        return "MED", f"matched MED-risk patterns: {med_hits[:5]}"

    return "LOW", "no high/med risk keywords"


def merge_risk(llm_risk: str, machine_risk: str) -> str:
    """より厳しい方を採用。"""
    order = {"LOW": 0, "MED": 1, "HIGH": 2}
    a = order.get((llm_risk or "LOW").upper(), 0)
    b = order.get((machine_risk or "LOW").upper(), 0)
    return ["LOW", "MED", "HIGH"][max(a, b)]


# ============================================================================
# データクラス
# ============================================================================

@dataclass
class FailurePattern:
    """類似 fail を束ねたパターン。"""
    pattern_id: str
    common_blocking_reason: str
    affected_cases: List[str] = field(default_factory=list)
    example_evidence: Dict[str, Any] = field(default_factory=dict)
    affected_categories: List[str] = field(default_factory=list)

    @property
    def impact(self) -> int:
        return len(self.affected_cases)


@dataclass
class PatchCandidate:
    pattern_id: str = ""
    diff: str = ""
    affected_files: List[str] = field(default_factory=list)
    affected_lines: List[Tuple[int, int]] = field(default_factory=list)
    risk_level: str = "LOW"          # LOW / MED / HIGH (machine + LLM 統合後)
    risk_reasoning: str = ""
    expected_improvement: str = ""
    llm_raw_response: str = ""
    is_empty: bool = False           # diff が抽出できなかった
    error: Optional[str] = None      # LLM 呼出失敗時メッセージ

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["affected_lines"] = [list(t) for t in self.affected_lines]
        return d


# ============================================================================
# FixProposer
# ============================================================================

DEFAULT_WORKER_JS = Path("api/worker.js")
DEFAULT_PATCH_DIR = Path("logs/audit/patches")
SYSTEM_PROMPT = (
    "あなたは Cloudflare Workers (LINE Bot) の上級エンジニアです。"
    "壊さない・最小・正確 を最優先に worker.js のパッチを生成します。"
)


class FixProposer:
    """failure をクラスタリング→上位3つにOpusでパッチ生成。

    Args:
        repo_root: リポジトリルート (worker.js の解決に使う)。
        llm_client: ``LLMClient`` インスタンス。省略時は Opus で自動生成。
        worker_js_path: ``api/worker.js`` への相対パス。
        max_patterns: 1ラウンドで提案するパッチ数 (上位N件)。
        context_window_lines: パッチ生成プロンプトに含める worker.js の行数。
    """

    def __init__(
        self,
        repo_root: str | Path,
        llm_client: Optional[LLMClient] = None,
        worker_js_path: Optional[str | Path] = None,
        max_patterns: int = 3,
        context_window_lines: int = 200,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.worker_js = Path(worker_js_path) if worker_js_path else self.repo_root / DEFAULT_WORKER_JS
        if not self.worker_js.exists():
            raise FileNotFoundError(f"worker.js not found: {self.worker_js}")
        self.llm = llm_client or LLMClient(model="claude-opus-4-7")
        self.max_patterns = max_patterns
        self.context_window_lines = context_window_lines

        # worker.js を1度だけメモリにロード (13,000行+)
        self._worker_lines: List[str] = self.worker_js.read_text(encoding="utf-8").splitlines()

    # ------------------------------------------------------------------
    # 1. クラスタリング
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_reason(reason: str) -> str:
        """blocking_reason を「同じ症状」と判定するためのキーへ正規化。

        - 数字・行番号は ``<N>`` に置換
        - 改行/連続空白を1空白に
        - 末尾句読点除去
        """
        if not reason:
            return "empty_reason"
        s = re.sub(r"\d+", "<N>", reason)
        s = re.sub(r"\s+", " ", s)
        return s.strip(" 。、,.").lower()[:200]

    def cluster_failures(self, verdicts: List[Dict[str, Any]]) -> List[FailurePattern]:
        """同じ正規化 blocking_reason を持つ失敗をまとめる。

        Args:
            verdicts: gatekeeper 出力の dict リスト。各 dict に
                      ``case_id`` ``passed`` ``blocking_reasons`` ``category``
                      ``reply_excerpt`` などを期待 (欠損時はベストエフォート)。

        Returns:
            impact 降順の ``FailurePattern`` リスト。
        """
        groups: Dict[str, FailurePattern] = {}
        for v in verdicts:
            # 新 schema: verdict="PASS"/"FAIL"  旧 schema: passed=True/False
            if "verdict" in v:
                if str(v.get("verdict", "")).upper() == "PASS":
                    continue
            elif v.get("passed"):
                continue
            reasons = v.get("blocking_reasons") or []
            if not reasons:
                # 失敗だが reason 欄なし → unknown バケットへ
                reasons = ["__no_reason__"]
            primary = reasons[0]
            key = self._normalize_reason(primary)
            pattern_id = f"P_{abs(hash(key)) % 10**8:08d}"

            grp = groups.get(key)
            if grp is None:
                grp = FailurePattern(
                    pattern_id=pattern_id,
                    common_blocking_reason=primary,
                )
                grp.example_evidence = {
                    "case_id": v.get("case_id"),
                    "category": v.get("category"),
                    "reply_excerpt": (v.get("reply_excerpt") or "")[:300],
                    "expected": v.get("expected"),
                    "actual": v.get("actual"),
                    "all_blocking_reasons": reasons[:5],
                }
                groups[key] = grp
            grp.affected_cases.append(v.get("case_id", "?"))
            cat = v.get("category")
            if cat and cat not in grp.affected_categories:
                grp.affected_categories.append(cat)

        # impact 降順
        return sorted(groups.values(), key=lambda p: p.impact, reverse=True)

    # ------------------------------------------------------------------
    # 2. 関連コード抽出
    # ------------------------------------------------------------------

    def _extract_relevant_code(self, pattern: FailurePattern) -> str:
        """パターンの blocking_reason から worker.js の関連箇所を抽出。

        単純戦略: blocking_reason から英数字キーワードを抜き出し、
        worker.js を grep して **一致した行±周辺数十行** を貼る。
        ヒット数 > 5 ならカテゴリ別にトップ3に絞る。

        13,000行 worker.js 全文をプロンプトに入れるとコスト爆発するので、
        必ずこの抽出を経由する。
        """
        # 1) キーワード抽出 (英数_, 3文字以上)
        text_for_keys = " ".join([
            pattern.common_blocking_reason,
            json.dumps(pattern.example_evidence, ensure_ascii=False),
        ])
        # 日本語+英数字を分けて、英数字側だけ識別子候補に
        candidates = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text_for_keys)
        # 高頻度ノイズ除去
        noise = {
            "true", "false", "null", "None", "the", "and", "for", "case",
            "case_id", "expect_phase", "expect_keywords_any", "passed",
            "blocking", "reason", "reasons", "actual", "expected",
            "category", "reply", "excerpt", "rubric", "must", "should",
        }
        keys = [k for k in dict.fromkeys(candidates) if k.lower() not in noise][:8]

        if not keys:
            # フォールバック: worker.js の冒頭〜200行
            head = self._worker_lines[: self.context_window_lines]
            return "\n".join(f"{i+1:5d}| {line}" for i, line in enumerate(head))

        # 2) 行マッチ
        hits: List[Tuple[int, str]] = []
        for i, line in enumerate(self._worker_lines):
            for k in keys:
                if k in line:
                    hits.append((i, line))
                    break

        if not hits:
            head = self._worker_lines[: self.context_window_lines]
            return "\n".join(f"{i+1:5d}| {line}" for i, line in enumerate(head))

        # 3) 上位3ヒットの周辺40行ずつをスニペット化 (重複排除)
        snippets: List[str] = []
        used_ranges: List[Tuple[int, int]] = []
        for line_no, _ in hits[:5]:
            start = max(0, line_no - 20)
            end = min(len(self._worker_lines), line_no + 20)
            # 既存範囲と被るならスキップ
            if any(s <= line_no <= e for s, e in used_ranges):
                continue
            used_ranges.append((start, end))
            block_lines = self._worker_lines[start:end]
            header = f"# --- worker.js {start+1}..{end} (key match near line {line_no+1}) ---"
            block = "\n".join(
                f"{i+start+1:5d}| {l}" for i, l in enumerate(block_lines)
            )
            snippets.append(header + "\n" + block)
            if sum(len(s) for s in snippets) > 12_000:
                break

        return "\n\n".join(snippets)

    # ------------------------------------------------------------------
    # 3. プロンプト構築
    # ------------------------------------------------------------------

    def _build_prompt(self, pattern: FailurePattern) -> str:
        code = self._extract_relevant_code(pattern)
        evidence = json.dumps(pattern.example_evidence, ensure_ascii=False, indent=2)
        cats = ", ".join(pattern.affected_categories) or "(unknown)"
        return f"""【ナースロビー LINE Bot で発生している失敗パターン】
パターンID: {pattern.pattern_id}
症状 (blocking_reason): {pattern.common_blocking_reason}
影響ケース数: {pattern.impact}
影響カテゴリ: {cats}
代表的な証拠:
{evidence}

【既存 worker.js の関連箇所 (行番号付き)】
{code}

【修正方針 (厳守)】
1. 最小限の変更で症状を改善する。スタイル統一などのリファクタは禁止。
2. 既存の他テストを壊さない。フィールド削除・関数削除は原則禁止。
3. unified diff (`---`/`+++`/`@@` 付き) を **そのまま `git apply` できる形** で出力する。
4. パスは ``a/api/worker.js`` / ``b/api/worker.js`` 固定。
5. もし関連箇所が抽出スニペットの外にあると判断したら、その旨を理由に書いて diff は空でよい (`is_empty: true`)。

【出力フォーマット (JSONで全体を包む。json以外は出力しない)】
```json
{{
  "diff": "--- a/api/worker.js\\n+++ b/api/worker.js\\n@@ -1234,5 +1234,5 @@\\n ...",
  "risk_level": "LOW|MED|HIGH",
  "risk_reasoning": "なぜそのリスクか (1-2文)",
  "expected_improvement": "このパッチで何が直ると期待するか",
  "is_empty": false
}}
```
"""

    # ------------------------------------------------------------------
    # 4. パッチ提案 (LLM呼出)
    # ------------------------------------------------------------------

    def propose_patch(self, pattern: FailurePattern) -> PatchCandidate:
        """1パターンに対して Opus で diff を生成。"""
        prompt = self._build_prompt(pattern)
        candidate = PatchCandidate(pattern_id=pattern.pattern_id)
        try:
            obj = self.llm.generate_json(
                prompt,
                max_tokens=4000,
                temperature=0.2,
                system=SYSTEM_PROMPT,
                default={"diff": "", "is_empty": True, "risk_level": "LOW",
                         "risk_reasoning": "parse_failed", "expected_improvement": ""},
            )
        except (LLMClientAPIError, LLMClientParseError) as e:
            candidate.error = f"llm_error: {e}"
            candidate.is_empty = True
            return candidate

        diff_text = (obj.get("diff") or "").strip()
        candidate.diff = diff_text
        candidate.is_empty = bool(obj.get("is_empty")) or not diff_text
        candidate.expected_improvement = obj.get("expected_improvement") or ""
        candidate.affected_files = ["api/worker.js"] if diff_text else []
        candidate.affected_lines = _extract_diff_hunks(diff_text)
        candidate.llm_raw_response = json.dumps(obj, ensure_ascii=False)[:2000]

        # risk: LLM返答 + 機械検査をマージ
        llm_risk = (obj.get("risk_level") or "LOW").upper()
        machine_risk, mreason = classify_risk_by_diff(diff_text)
        candidate.risk_level = merge_risk(llm_risk, machine_risk)
        candidate.risk_reasoning = (
            f"llm={llm_risk} ({obj.get('risk_reasoning','')}); "
            f"machine={machine_risk} ({mreason})"
        )
        return candidate

    # ------------------------------------------------------------------
    # 5. ファイル出力
    # ------------------------------------------------------------------

    def save_patch(
        self,
        round_n: int,
        pattern: FailurePattern,
        candidate: PatchCandidate,
        out_dir: Optional[str | Path] = None,
    ) -> Dict[str, str]:
        """diff と meta を ``patches/<round>/<pattern_id>.{diff,meta.json}`` に保存。"""
        base_dir = Path(out_dir) if out_dir else (self.repo_root / DEFAULT_PATCH_DIR)
        round_dir = base_dir / f"round_{round_n:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)

        diff_path = round_dir / f"{pattern.pattern_id}.diff"
        meta_path = round_dir / f"{pattern.pattern_id}.meta.json"

        diff_path.write_text(candidate.diff or "", encoding="utf-8")

        meta = {
            "pattern_id": pattern.pattern_id,
            "round": round_n,
            "common_blocking_reason": pattern.common_blocking_reason,
            "impact": pattern.impact,
            "affected_cases_count": len(pattern.affected_cases),
            "affected_cases_sample": pattern.affected_cases[:10],
            "affected_categories": pattern.affected_categories,
            "candidate": candidate.to_dict(),
        }
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"diff": str(diff_path), "meta": str(meta_path)}

    # ------------------------------------------------------------------
    # 6. ワンショット: cluster → propose top-N → save
    # ------------------------------------------------------------------

    def run_round(
        self,
        round_n: int,
        verdicts: List[Dict[str, Any]],
        dry_run: bool = False,
    ) -> List[Dict[str, Any]]:
        """1ラウンド分のパッチ提案を生成・保存。

        Returns:
            各パターンについての ``{"pattern": FailurePattern, "candidate": PatchCandidate, "files": {...}}`` リスト。
            (dry_run 時は files なし)
        """
        patterns = self.cluster_failures(verdicts)[: self.max_patterns]
        results: List[Dict[str, Any]] = []
        for pat in patterns:
            cand = self.propose_patch(pat)
            pat_dict = asdict(pat)
            pat_dict["impact"] = pat.impact  # @property は asdict 対象外
            entry: Dict[str, Any] = {
                "pattern": pat_dict,
                "candidate": cand.to_dict(),
            }
            if not dry_run:
                files = self.save_patch(round_n, pat, cand)
                entry["files"] = files
            results.append(entry)
        return results


# ============================================================================
# diff hunks 抽出 (affected_lines 計算用)
# ============================================================================

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", re.MULTILINE)


def _extract_diff_hunks(diff_text: str) -> List[Tuple[int, int]]:
    """`@@ -A,B +C,D @@` の (C, C+D-1) を抽出。"""
    out: List[Tuple[int, int]] = []
    for m in _HUNK_RE.finditer(diff_text or ""):
        start = int(m.group(3))
        size = int(m.group(4) or 1)
        out.append((start, start + max(0, size - 1)))
    return out


# ============================================================================
# CLI
# ============================================================================

def _load_verdicts(verdicts_dir: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in sorted(verdicts_dir.glob("*.json")):
        try:
            obj = json.loads(p.read_text(encoding="utf-8"))
            out.append(obj)
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    import argparse

    p = argparse.ArgumentParser(
        description="Cluster verdict failures and propose worker.js patches via Claude Opus"
    )
    p.add_argument("--verdicts-dir", required=True, help="verdicts/<case_id>.json があるディレクトリ")
    p.add_argument("--round", type=int, required=True, help="ラウンド番号 (1始まり)")
    p.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[3]))
    p.add_argument("--worker-js", default=None)
    p.add_argument("--max-patterns", type=int, default=3)
    p.add_argument("--dry-run", action="store_true", help="保存せずstdoutに結果のみ")
    p.add_argument("--model", default="claude-opus-4-7")
    args = p.parse_args()

    verdicts_dir = Path(args.verdicts_dir)
    if not verdicts_dir.exists():
        print(f"verdicts dir not found: {verdicts_dir}", file=sys.stderr)
        return 1

    verdicts = _load_verdicts(verdicts_dir)
    if not verdicts:
        print(f"no verdicts in {verdicts_dir}", file=sys.stderr)
        return 1

    proposer = FixProposer(
        repo_root=args.repo_root,
        worker_js_path=args.worker_js,
        max_patterns=args.max_patterns,
        llm_client=LLMClient(model=args.model),
    )
    results = proposer.run_round(args.round, verdicts, dry_run=args.dry_run)

    summary = {
        "round": args.round,
        "patterns_processed": len(results),
        "verdicts_total": len(verdicts),
        "verdicts_failed": sum(1 for v in verdicts if not v.get("passed")),
        "patches": [
            {
                "pattern_id": r["pattern"]["pattern_id"],
                "impact": r["pattern"]["impact"],
                "risk": r["candidate"]["risk_level"],
                "is_empty": r["candidate"]["is_empty"],
                "files": r.get("files"),
            }
            for r in results
        ],
        "llm_cost": proposer.llm.cost_summary(),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
