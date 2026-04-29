#!/usr/bin/env python3
"""
rubric_eval.py — 8軸ルーブリック評価

DESIGN.md §4 のルーブリックを実装:

| 軸 | 評価方法 | 合格閾値 |
|---|---------|---------|
| F. 機能正確性     | expect_phase完全一致 / keywords含有 | **5/5 必須** |
| U. UX            | 文字数/絵文字/改行 (機械評価)        | ≥ 4         |
| E. 寄り添い      | LLM 3回中央値 (Opus self-consistency) | ≥ 4        |
| C. 整合性        | 質問⇔Quick Reply 論理一致           | **5/5 必須** |
| L. レイテンシ    | duration_ms p95                      | ≥ 4         |
| S. セキュリティ  | PII漏洩/署名検証                     | **5/5 必須** |
| K. コスト        | tokens推定                           | 警告のみ      |
| H. ハルシネーション | must_not + 数字捏造検知             | **5/5 必須** |

【run_result JSON 期待スキーマ】
    {
      "case_id": "aica_career_016",
      "duration_ms": 1234,           # 全stepの最大 or 合計
      "steps": [
        {
          "step_index": 0,
          "request": {"kind": "postback", "data": "rm=start", "invalid_signature": false},
          "response_status": 200,
          "duration_ms": 234,
          "replies": [                 # LINE messageList of message text
            {"type": "text", "text": "...", "quickReply": {"items":[...]}}
          ],
          "entry_after": {              # /api/admin/audit-snapshot で取得
            "phase": "il_area",
            "aicaAxis": null
          },
          "estimated_tokens_in": 0,
          "estimated_tokens_out": 0
        }
      ]
    }

【使い方】
    >>> from scripts.audit.gatekeeper.rubric_eval import RubricEvaluator
    >>> from scripts.audit.lib.llm_client import LLMClient
    >>> ev = RubricEvaluator(LLMClient(model="claude-opus-4-7"))
    >>> result = ev.evaluate(case_dict, run_result_dict)
    >>> print(result.verdict, result.scores)
"""
from __future__ import annotations

import json
import math
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ============================================================================
# 定数 / regex
# ============================================================================

# 絵文字ざっくり判定（emoji 1.x 相当の網羅は不要、看護師LINEの主要範囲）
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"   # misc symbols
    "\U00002700-\U000027BF"   # dingbats
    "\U0001F1E6-\U0001F1FF"   # regional flags
    "]+",
    flags=re.UNICODE,
)

# PII patterns
_PHONE_RE = re.compile(r"\b0\d{1,4}[-(\s]?\d{1,4}[-)\s]?\d{3,4}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_ADDRESS_HINT_RE = re.compile(
    r"(?:〒\s*\d{3}-?\d{4})|(?:東京都|神奈川県|大阪府|愛知県|福岡県)[^\s]{2,}[市区町村][^\s]{1,10}\d"
)

# 数字捏造の代表的キーワード
_HALLUCINATION_KEYWORDS = [
    "業界No.1", "業界1位", "業界一位", "日本一",
    "確実に儲かる", "100%成功", "絶対", "間違いなく", "最高",
]

# 数値捏造（時給/月給/手数料率の異常値）
_FABRICATED_FIGURE_RE = re.compile(
    r"(?:時給|時間給)\s?[\d,]+\s?円"
    r"|(?:月収|月給|年収)\s?[\d,]+\s?(?:万)?円"
    r"|(?:手数料)\s?\d+%"
)


# ============================================================================
# データクラス
# ============================================================================

@dataclass
class RubricResult:
    """1ケース分の8軸スコア + 判定 + 根拠"""

    case_id: str
    scores: Dict[str, int] = field(
        default_factory=lambda: {
            "F": 0, "U": 0, "E": 0, "C": 0,
            "L": 0, "S": 0, "K": 0, "H": 0,
        }
    )
    verdict: str = "PENDING"  # PASS / FAIL / SKIP
    blocking_reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    llm_eval_count: int = 0
    human_review_flag: bool = False  # 20%抜き取り

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "scores": dict(self.scores),
            "verdict": self.verdict,
            "blocking_reasons": list(self.blocking_reasons),
            "warnings": list(self.warnings),
            "evidence": self.evidence,
            "llm_eval_count": self.llm_eval_count,
            "human_review_flag": self.human_review_flag,
        }


# ============================================================================
# RubricEvaluator
# ============================================================================

class RubricEvaluator:
    """8軸ルーブリック評価。

    Args:
        llm_client: ゲートキーパー用LLM (Opus推奨)。
        consistency_llm_client: 整合性チェック用 LLM (gpt-4o-mini推奨)。
                                ``None`` のとき機械評価のみ。
        sample_rate_for_human: 人間目視抜き取り率 (0.0〜1.0)。
        empathy_n: 寄り添い評価のself-consistency回数（既定3）。
        rng: 抜き取り抽選用 random.Random（テスト時seed固定）。
    """

    def __init__(
        self,
        llm_client,
        consistency_llm_client=None,
        sample_rate_for_human: float = 0.2,
        empathy_n: int = 3,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.llm = llm_client
        self.consistency_llm = consistency_llm_client
        self.sample_rate = max(0.0, min(1.0, sample_rate_for_human))
        self.empathy_n = max(1, empathy_n)
        self._rng = rng or random.Random()

    # ------------------------------------------------------------------
    # 公開エントリ
    # ------------------------------------------------------------------

    def evaluate(self, case: Dict[str, Any], run_result: Dict[str, Any]) -> RubricResult:
        case_id = case.get("id", run_result.get("case_id", "unknown"))
        result = RubricResult(case_id=case_id)

        # SKIP: run_result が完全に欠落 / runner エラー
        if run_result.get("error") and not run_result.get("steps"):
            result.verdict = "SKIP"
            result.warnings.append(f"runner error: {run_result.get('error')}")
            return result

        # F. 機能正確性 (機械)
        result.scores["F"] = self._eval_functional(case, run_result, result)
        # U. UX (機械)
        result.scores["U"] = self._eval_ux(run_result, result)
        # C. 整合性 (機械 + 軽量LLM 補助)
        result.scores["C"] = self._eval_consistency(run_result, result)
        # L. レイテンシ (機械)
        result.scores["L"] = self._eval_latency(case, run_result, result)
        # S. セキュリティ (機械)
        result.scores["S"] = self._eval_security(case, run_result, result)
        # K. コスト (機械、警告のみ)
        result.scores["K"] = self._eval_cost(run_result, result)
        # H. ハルシネーション (機械優先 + LLM補助で数字検出)
        result.scores["H"] = self._eval_hallucination(case, run_result, result)
        # E. 寄り添い (LLM 3回 self-consistency 中央値)
        #   replyに人間向け文がある時のみ評価。403応答などスキップ。
        result.scores["E"] = self._eval_empathy(case, run_result, result)

        # 判定
        result.verdict = self._judge(result)
        # 20%人間レビューフラグ
        result.human_review_flag = self._rng.random() < self.sample_rate
        return result

    # ------------------------------------------------------------------
    # 判定
    # ------------------------------------------------------------------

    def _judge(self, r: RubricResult) -> str:
        """F/C/S/H = 5/5必須、U/E/L ≥ 4、K は警告のみ。"""
        for axis in ("F", "C", "S", "H"):
            if r.scores[axis] < 5:
                r.blocking_reasons.append(
                    f"{axis}={r.scores[axis]} below 5/5 (mandatory)"
                )
        for axis in ("U", "E", "L"):
            if r.scores[axis] < 4:
                r.blocking_reasons.append(f"{axis}={r.scores[axis]} below 4")

        # K は警告のみ
        if r.scores["K"] < 3:
            r.warnings.append(f"K={r.scores['K']} cost concern")

        return "PASS" if not r.blocking_reasons else "FAIL"

    # ==================================================================
    # F. 機能正確性
    # ==================================================================

    def _eval_functional(
        self,
        case: Dict[str, Any],
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """expect_phase / expect_keywords_any / expect_axis / expect_status の検査。

        全 step が一致したら 5、1つでも違反すれば 0（部分点なし）。
        """
        steps_case = case.get("steps", []) or []
        steps_run = run.get("step_results", run.get("steps", [])) or []
        evidence: Dict[str, Any] = {"step_results": []}

        if not steps_case:
            r.evidence["F"] = {"reason": "no steps in case"}
            return 5  # 検査対象なし→合格扱い

        if len(steps_run) < len(steps_case):
            r.evidence["F"] = {
                "reason": f"step count mismatch: case={len(steps_case)} run={len(steps_run)}"
            }
            return 0

        # entry_after を auditTrail から逆算する（runner が per-step snapshot を取らないため）
        # auditTrail は [follow] + [postback/text/audio] の順。case が follow_first=true なら +1 オフセット
        snapshots = run.get("entry_snapshots") or []
        audit_trail = []
        if snapshots and isinstance(snapshots[0], dict):
            ent = snapshots[0].get("entry") if isinstance(snapshots[0].get("entry"), dict) else snapshots[0]
            audit_trail = ent.get("auditTrail", []) if isinstance(ent, dict) else []

        # follow_first を考慮したオフセット
        follow_first = bool(case.get("preconditions", {}).get("follow_first"))
        offset = 1 if follow_first and audit_trail and audit_trail[0].get("eventKind") == "follow" else 0

        all_ok = True
        for idx, step_c in enumerate(steps_case):
            step_r = dict(steps_run[idx]) if idx < len(steps_run) else {}
            # auditTrail から phaseAfter / replyTexts を補完
            ai_idx = idx + offset
            if 0 <= ai_idx < len(audit_trail):
                trail = audit_trail[ai_idx]
                step_r["entry_after"] = {
                    "phase": trail.get("phaseAfter"),
                    "aicaAxis": (snapshots[0].get("entry", {}) if snapshots else {}).get("aicaAxis"),
                }
                # replyTexts → replies に正規化
                rt = trail.get("replyTexts") or []
                step_r["replies"] = [{"type": "text", "text": t} for t in rt if t]
            ok, why = self._check_one_step(step_c, step_r)
            evidence["step_results"].append({"step": idx, "ok": ok, "reason": why})
            if not ok:
                all_ok = False

        r.evidence["F"] = evidence
        return 5 if all_ok else 0

    @staticmethod
    def _check_one_step(step_c: Dict[str, Any], step_r: Dict[str, Any]) -> Tuple[bool, str]:
        # expect_status (HTTP)
        if "expect_status" in step_c:
            got = int(step_r.get("response_status", 0) or 0)
            if got != int(step_c["expect_status"]):
                return False, f"status {got} != expected {step_c['expect_status']}"
            # 不正署名期待時は entryチェック不要 → ここでpass
            return True, "status match"

        entry = step_r.get("entry_after") or {}
        # expect_phase
        exp_phase = step_c.get("expect_phase")
        if exp_phase is not None:
            got_phase = entry.get("phase")
            if got_phase != exp_phase:
                return False, f"phase {got_phase!r} != {exp_phase!r}"

        # expect_axis
        exp_axis = step_c.get("expect_axis")
        if exp_axis is not None:
            got_axis = entry.get("aicaAxis")
            if got_axis != exp_axis:
                return False, f"axis {got_axis!r} != {exp_axis!r}"

        # expect_keywords_any (replyテキスト連結に対するOR)
        exp_kws = step_c.get("expect_keywords_any") or []
        if exp_kws:
            joined = _flatten_reply_text(step_r.get("replies", []))
            if not any(kw in joined for kw in exp_kws):
                return False, f"keywords {exp_kws!r} not found in reply"

        return True, "ok"

    # ==================================================================
    # U. UX
    # ==================================================================

    def _eval_ux(self, run: Dict[str, Any], r: RubricResult) -> int:
        """文字数 / 絵文字数 / 改行から複合スコア。

        LINE Bot 1メッセージあたり:
          - chars ≤ 200 → +5、≤ 350 → +4、≤ 500 → +3、> 500 → +1
          - emojis 1〜3 → +5、0 → +2 (冷たい)、4〜6 → +3、≥ 7 → +1
          - newlines ≥ 1 → +0、< 1 → -1（モバイルで読みづらい）
        全メッセージ平均 → 切り捨て1〜5。

        replyが存在しない (403/follow ack のみ) は 5 (検査スキップ)。
        """
        msgs = _all_message_texts(run)
        if not msgs:
            r.evidence["U"] = {"reason": "no text replies (skipped)"}
            return 5

        per_msg_scores: List[float] = []
        details: List[Dict[str, Any]] = []
        for text in msgs:
            chars = len(text)
            emojis = sum(len(m.group(0)) for m in _EMOJI_RE.finditer(text))
            newlines = text.count("\n")

            if chars <= 200:
                s_chars = 5
            elif chars <= 350:
                s_chars = 4
            elif chars <= 500:
                s_chars = 3
            else:
                s_chars = 1

            if 1 <= emojis <= 3:
                s_emo = 5
            elif emojis == 0:
                s_emo = 2
            elif emojis <= 6:
                s_emo = 3
            else:
                s_emo = 1

            penalty = 0 if newlines >= 1 else 1

            score = (s_chars + s_emo) / 2 - penalty
            score = max(1, min(5, score))
            per_msg_scores.append(score)
            details.append({
                "chars": chars, "emojis": emojis, "newlines": newlines, "score": score,
            })

        avg = sum(per_msg_scores) / len(per_msg_scores)
        final = max(1, min(5, int(math.floor(avg + 0.0001))))
        r.evidence["U"] = {"per_message": details, "avg": round(avg, 2)}
        return final

    # ==================================================================
    # E. 寄り添い (LLM self-consistency)
    # ==================================================================

    def _eval_empathy(
        self,
        case: Dict[str, Any],
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """Opus に「寄り添い」を5段階で n回独立評価 → 中央値。

        replyテキストが空の場合は 5（検査スキップ）。
        """
        msgs = _all_message_texts(run)
        # Push API placeholder「考えています…」と「お待ちください」系は評価対象から除外
        # (これらは ack-only でAICAの実応答ではない)
        msgs = [m for m in msgs if not _is_placeholder_ack(m)]
        if not msgs:
            r.evidence["E"] = {"reason": "no text replies (skipped)"}
            return 5

        # ユーザの直近発話
        user_input = ""
        for step in reversed(case.get("steps", []) or []):
            if step.get("kind") == "text" and step.get("text"):
                user_input = step["text"]
                break

        persona = case.get("persona", "misaki")
        bot_reply = "\n---\n".join(msgs)[:1500]  # 長すぎ予防

        prompt = (
            "あなたは看護師向けLINE Botの応答品質審査員です。\n"
            "ユーザの発話に対するBot応答の「寄り添い度」を5段階で評価してください。\n\n"
            f"【ペルソナ】{persona}（28歳の二交代制看護師など）\n"
            f"【ユーザ発話】{user_input or '(postback操作)'}\n"
            f"【Bot応答】\n{bot_reply}\n\n"
            "【評価軸】\n"
            "・受け止めの言葉があるか（『お辛いですよね』『大変でしたね』等）\n"
            "・リフレクション（ユーザ言葉の繰り返し/言い換え）があるか\n"
            "・ジャッジしない（説教・命令調がない）\n"
            "・形式的・テンプレ的でない\n"
            "・看護師の現場語彙（夜勤明け/プリセプター/申し送り等）に違和感がない\n\n"
            "【スコア基準】\n"
            "5 = 心から寄り添えている（受け止め+具体的リフレクション+次の自然な質問）\n"
            "4 = 受け止めできている（受け止め+リフレクションあり）\n"
            "3 = ふつう（受け止めはあるがやや形式的）\n"
            "2 = 事務的（情報伝達のみ）\n"
            "1 = 冷たい/不適切（説教調・命令調・無視）\n\n"
            'JSON のみで出力: {"score": <1-5>, "reasoning": "<150字以内>"}'
        )

        responses = self.llm.generate_json_n(
            prompt, n=self.empathy_n, max_tokens=400, temperature=0.4,
        )
        r.llm_eval_count += len(responses)

        scores: List[int] = []
        for resp in responses:
            try:
                s = int(resp.get("score", 0))
                if 1 <= s <= 5:
                    scores.append(s)
            except (TypeError, ValueError):
                continue

        if not scores:
            r.warnings.append("E: LLM eval failed, fallback to 3")
            r.evidence["E"] = {"reason": "all LLM calls failed", "fallback": 3}
            return 3

        median = sorted(scores)[len(scores) // 2]
        r.evidence["E"] = {
            "scores_raw": scores,
            "median": median,
            "n": len(scores),
            "reasonings": [resp.get("reasoning", "") for resp in responses[:3]],
        }
        return median

    # ==================================================================
    # C. 整合性 (Quick Reply ↔ 質問文)
    # ==================================================================

    def _eval_consistency(
        self,
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """直近Bot応答に Quick Reply がある場合、質問文との論理一致を見る。

        QR が無い → 5 (検査対象なし)。
        QR の選択肢ラベルと質問文に共通テーマがあれば 5。
        ラベルが質問文と無関係（例: 「年数を聞いているのに施設選択肢」）→ 0。

        補助LLM（gpt-4o-mini想定）があれば論理判定を委譲、なければルールベース簡易版。
        """
        all_pairs = _extract_qr_pairs(run)
        if not all_pairs:
            r.evidence["C"] = {"reason": "no Quick Reply found (skipped)"}
            return 5

        details: List[Dict[str, Any]] = []
        worst = 5
        for question, labels in all_pairs:
            ok = self._check_qr_match(question, labels)
            details.append({"question": question[:80], "labels": labels, "ok": ok})
            if not ok:
                worst = 0
        r.evidence["C"] = {"checks": details}
        return worst

    def _check_qr_match(self, question: str, labels: List[str]) -> bool:
        """ルールベース1次判定。LLM補助があればさらに判定。"""
        if not labels:
            return True

        # ルールベース: 主要トピックの語彙群が質問とラベル両方に共通か
        topic_groups = [
            (["経験", "年目", "年数", "キャリア"],
             ["年目", "年", "未経験", "新卒", "経験"]),
            (["施設", "病院", "クリニック", "希望", "種類"],
             ["病院", "クリニック", "施設", "訪問", "介護"]),
            (["エリア", "地域", "場所", "都道府県", "県"],
             ["県", "市", "区", "横浜", "川崎", "東京", "全国"]),
            (["働き方", "勤務", "雇用", "形態"],
             ["常勤", "非常勤", "パート", "派遣", "正社員"]),
            (["夜勤", "シフト"],
             ["夜勤", "日勤", "二交代", "三交代"]),
        ]

        for q_kws, l_kws in topic_groups:
            q_match = any(kw in question for kw in q_kws)
            l_match = any(any(kw in lab for kw in l_kws) for lab in labels)
            if q_match and l_match:
                return True
            if q_match and not l_match:
                # 質問はトピック該当だが選択肢が外れている
                # LLMで再確認
                if self.consistency_llm:
                    return self._check_qr_with_llm(question, labels)
                return False

        # トピック対応が見つからない場合はLLMで判定（または許容）
        if self.consistency_llm:
            return self._check_qr_with_llm(question, labels)
        # LLM無 + ルール無 → 許容（false negative回避）
        return True

    def _check_qr_with_llm(self, question: str, labels: List[str]) -> bool:
        prompt = (
            "LINE Botの質問文とQuick Reply選択肢の整合性を判定してください。\n"
            f"【質問文】{question[:200]}\n"
            f"【選択肢】{labels}\n\n"
            "選択肢が質問への自然な回答群になっているか?\n"
            'JSON のみ: {"consistent": true|false, "reason": "..."}'
        )
        try:
            obj = self.consistency_llm.generate_json(
                prompt, max_tokens=200, temperature=0.0,
                default={"consistent": True, "reason": "fallback"},
            )
            return bool(obj.get("consistent", True))
        except Exception:  # noqa: BLE001
            return True  # 失敗時は false-positive 回避

    # ==================================================================
    # L. レイテンシ
    # ==================================================================

    def _eval_latency(
        self,
        case: Dict[str, Any],
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """ステップ最大 duration_ms から判定。

        - < 1000 ms → 5
        - < 2000 ms → 4
        - < 5000 ms → 3
        - < 10000 ms → 2
        - else → 1

        case.expectations.rubric.latency_p95_ms があればそれを上限基準に。
        """
        steps = run.get("step_results", run.get("steps", [])) or []
        durations = [int(s.get("duration_ms", 0) or 0) for s in steps]
        max_ms = max(durations) if durations else 0
        avg_ms = sum(durations) / len(durations) if durations else 0

        # 設計書の閾値
        thresholds = [(1000, 5), (2000, 4), (5000, 3), (10000, 2)]
        score = 1
        for limit, sc in thresholds:
            if max_ms < limit:
                score = sc
                break

        # case指定の上限を超えている場合は最低保証 -1
        case_limit = (
            case.get("expectations", {})
            .get("rubric", {})
            .get("latency_p95_ms", None)
        )
        if case_limit and max_ms > case_limit:
            score = min(score, 3)
            r.warnings.append(
                f"L: max_ms={max_ms} > case_limit={case_limit}"
            )

        r.evidence["L"] = {
            "max_ms": max_ms, "avg_ms": round(avg_ms, 1), "n": len(durations),
        }
        return score

    # ==================================================================
    # S. セキュリティ
    # ==================================================================

    def _eval_security(
        self,
        case: Dict[str, Any],
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """PII (電話/メール/住所) 漏洩検査 + 不正署名応答 検査。

        違反1個でも → -1 (1ステップにつき)、最低1。
        ・電話番号 0xx-xxxx-xxxx
        ・email
        ・郵便番号 + 住所
        不正HMAC署名のテストでは 401/403 が返ること必須。
        """
        score = 5
        violations: List[Dict[str, Any]] = []
        steps_case = case.get("steps", []) or []
        steps_run = run.get("step_results", run.get("steps", [])) or []

        # 不正署名期待ステップの応答コード確認
        for idx, sc in enumerate(steps_case):
            if sc.get("invalid_signature") and idx < len(steps_run):
                got = int(steps_run[idx].get("response_status", 0) or 0)
                if got not in (401, 403):
                    violations.append({
                        "step": idx, "kind": "auth",
                        "reason": f"invalid_signature got {got}, expected 401/403",
                    })
                    score = 1

        # PII漏洩スキャン
        all_text = "\n".join(_all_message_texts(run))
        if all_text:
            for label, regex in (
                ("phone", _PHONE_RE),
                ("email", _EMAIL_RE),
                ("address", _ADDRESS_HINT_RE),
            ):
                hits = regex.findall(all_text)
                # ホワイトリスト: 連絡先表記がpolicyに必要なケース
                hits = [h for h in hits if not _is_whitelisted_pii(h, label)]
                if hits:
                    violations.append({
                        "kind": "pii_leak", "label": label, "hits": hits[:3],
                    })
                    score = max(1, score - 1)

        r.evidence["S"] = {"violations": violations}
        return score

    # ==================================================================
    # K. コスト
    # ==================================================================

    def _eval_cost(
        self,
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """日本語1文字 ≈ 1.5tokens で出力サイズから推定。

        run.steps[].estimated_tokens_in/out があれば優先。
        - < 1000 tokens → 5
        - < 3000        → 4
        - < 5000        → 3
        - < 10000       → 2
        - else          → 1
        警告のみで blocking しない。
        """
        steps = run.get("step_results", run.get("steps", [])) or []
        total_in = sum(int(s.get("estimated_tokens_in", 0) or 0) for s in steps)
        total_out = sum(int(s.get("estimated_tokens_out", 0) or 0) for s in steps)

        if total_in == 0 and total_out == 0:
            # フォールバック: 文字数から推定
            chars = sum(len(t) for t in _all_message_texts(run))
            total_out = int(chars * 1.5)

        total = total_in + total_out
        if total < 1000:
            score = 5
        elif total < 3000:
            score = 4
        elif total < 5000:
            score = 3
        elif total < 10000:
            score = 2
        else:
            score = 1
        r.evidence["K"] = {"tokens_in": total_in, "tokens_out": total_out, "total": total}
        return score

    # ==================================================================
    # H. ハルシネーション
    # ==================================================================

    def _eval_hallucination(
        self,
        case: Dict[str, Any],
        run: Dict[str, Any],
        r: RubricResult,
    ) -> int:
        """must_not_in_reply 違反検査 + 数字捏造の代表パターン検出。

        違反 1個 → 0 (必須軸のため)。
        """
        forbidden = (case.get("expectations", {}) or {}).get("must_not_in_reply", []) or []
        # default forbidden words
        defaults = ["No.1", "業界1位", "業界一位", "確実に儲かる", "100%成功", "日本一"]
        all_forbidden = list({*forbidden, *defaults})

        all_text = "\n".join(_all_message_texts(run))
        violations: List[Dict[str, Any]] = []

        # 1) 直接禁止語
        for kw in all_forbidden:
            if kw and kw in all_text:
                violations.append({"kind": "forbidden", "term": kw})

        # 2) ハルシネーション疑いキーワード
        for kw in _HALLUCINATION_KEYWORDS:
            if kw in all_text and kw not in all_forbidden:
                violations.append({"kind": "halluc_keyword", "term": kw})

        # 3) 数値の異常（時給/月給/年収/手数料の具体的金額が出ているか）
        #    case.allow_figures: True で許容、それ以外で検出時は警告
        allow_figures = (case.get("allow_figures") is True)
        figs = _FABRICATED_FIGURE_RE.findall(all_text)
        if figs and not allow_figures:
            violations.append({"kind": "fabricated_figure", "samples": figs[:3]})

        r.evidence["H"] = {"violations": violations}
        return 0 if violations else 5


# ============================================================================
# ヘルパ
# ============================================================================

def _flatten_reply_text(replies: List[Any]) -> str:
    """``replies`` (LINE messageList) からテキストを連結。"""
    parts: List[str] = []
    for m in replies or []:
        if isinstance(m, dict):
            t = m.get("text") or m.get("altText") or ""
            if t:
                parts.append(str(t))
            # Flex Message の content から text bubble を拾う（ベストエフォート）
            contents = m.get("contents")
            if isinstance(contents, dict):
                parts.append(_extract_flex_text(contents))
        elif isinstance(m, str):
            parts.append(m)
    return "\n".join(parts)


def _extract_flex_text(node: Any) -> str:
    """Flex Message JSON ツリーから text を再帰抽出。"""
    if isinstance(node, dict):
        if node.get("type") == "text" and node.get("text"):
            return str(node["text"])
        chunks: List[str] = []
        for v in node.values():
            t = _extract_flex_text(v)
            if t:
                chunks.append(t)
        return "\n".join(chunks)
    if isinstance(node, list):
        return "\n".join(filter(None, (_extract_flex_text(v) for v in node)))
    return ""


# 即時 ack の placeholder。AICA の本物応答は Push 経由で aicaMessages に入る。
_PLACEHOLDER_PATTERNS = (
    "少々お待ちください",
    "考えています",
    "承知しました",
)


def _is_placeholder_ack(text: str) -> bool:
    """LINE Reply API で消費されるだけの即時 ack か判定。"""
    if not text:
        return True
    t = str(text)
    # 短くてプレースホルダ語を含むものは ack 扱い
    if len(t) > 80:
        return False
    return any(p in t for p in _PLACEHOLDER_PATTERNS)


def _all_message_texts(run: Dict[str, Any]) -> List[str]:
    """全 step replies のテキスト一覧。

    優先順位:
    1. step_results[].replies (旧スキーマ、runner未対応)
    2. entry_snapshots[0].entry.auditTrail[].replyTexts (即時 reply のみ)
    3. entry_snapshots[0].entry.aicaMessages[role=assistant] (AICA BG処理→Push経路)
    4. entry_snapshots[0].entry.messages[role=assistant] (汎用ヒストリ)

    AICA は ctx.waitUntil で LLM 呼んで Push API で送るため、auditTrail.replyTexts
    には placeholder「考えています…」しか残らない。実際の共感応答は
    entry.aicaMessages の assistant role に保存されているのでそちらも合算する。
    """
    out: List[str] = []
    # 1) step_results.replies
    for s in run.get("step_results", run.get("steps", [])) or []:
        for m in s.get("replies", []) or []:
            if isinstance(m, dict):
                t = m.get("text") or m.get("altText") or ""
                if t:
                    out.append(str(t))
                contents = m.get("contents")
                if isinstance(contents, dict):
                    flex_text = _extract_flex_text(contents)
                    if flex_text:
                        out.append(flex_text)
            elif isinstance(m, str):
                out.append(m)

    snaps = run.get("entry_snapshots") or []
    ent = None
    if snaps and isinstance(snaps[0], dict):
        ent = snaps[0].get("entry") if isinstance(snaps[0].get("entry"), dict) else snaps[0]

    # 2) auditTrail.replyTexts (placeholder含む即時reply)
    if not out and ent:
        audit = ent.get("auditTrail", []) if isinstance(ent, dict) else []
        for t in audit:
            for rt in t.get("replyTexts", []) or []:
                if rt:
                    out.append(str(rt))

    # 3) AICA: aicaMessages[role=assistant] (Push経由の本物の応答)
    if ent:
        aica_msgs = ent.get("aicaMessages") or []
        for m in aica_msgs:
            if not isinstance(m, dict):
                continue
            if m.get("role") != "assistant":
                continue
            txt = m.get("text") or m.get("content") or ""
            if txt:
                out.append(str(txt))
        # 4) 汎用 messages[role=assistant]
        msgs = ent.get("messages") or []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role") or m.get("type")
            if role != "assistant":
                continue
            txt = m.get("text") or m.get("content") or ""
            if txt and str(txt) not in out:
                out.append(str(txt))

    return out


def _extract_qr_pairs(run: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    """各stepの reply から (質問文, [QRラベル...]) を抽出。"""
    pairs: List[Tuple[str, List[str]]] = []
    for s in run.get("step_results", run.get("steps", [])) or []:
        for m in s.get("replies", []) or []:
            if not isinstance(m, dict):
                continue
            qr = m.get("quickReply")
            if not qr:
                continue
            items = qr.get("items") or []
            labels: List[str] = []
            for it in items:
                act = (it or {}).get("action") or {}
                lab = act.get("label") or act.get("text") or act.get("displayText")
                if lab:
                    labels.append(str(lab))
            question = m.get("text") or m.get("altText") or ""
            if labels:
                pairs.append((str(question), labels))
    return pairs


def _is_whitelisted_pii(hit: str, label: str) -> bool:
    """テスト用ダミー値 / 公開連絡先の許容（誤検知抑制）。"""
    if label == "phone":
        # 0120/0800系のフリーダイヤルは公開連絡先として許容
        if hit.startswith(("0120", "0800")):
            return True
        # テスト用の 03-0000-0000 / 090-1234-5678 などは許容しない
    if label == "email":
        # Workerサポートメールなどは許容
        if hit.endswith(("@example.com", "@test.local")):
            return True
    return False


# ============================================================================
# CLI 動作確認
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="rubric_eval smoke test")
    parser.add_argument("--case", required=True, help="case YAML path")
    parser.add_argument("--run", required=True, help="run result JSON path")
    parser.add_argument("--no-llm", action="store_true", help="LLM不使用 (mock)")
    args = parser.parse_args()

    import yaml  # type: ignore
    from pathlib import Path as _P

    case = yaml.safe_load(_P(args.case).read_text())
    run = json.loads(_P(args.run).read_text())

    if args.no_llm:
        class _MockLLM:
            def generate_json_n(self, prompt, n=3, **kw):
                return [{"score": 4, "reasoning": "mock"}] * n
            def generate_json(self, prompt, **kw):
                return {"consistent": True, "reason": "mock"}
            total_calls = 0
        ev = RubricEvaluator(_MockLLM(), consistency_llm_client=_MockLLM())
    else:
        from scripts.audit.lib.llm_client import LLMClient
        ev = RubricEvaluator(
            LLMClient(model="claude-opus-4-7"),
            consistency_llm_client=LLMClient(model="gpt-4o-mini", prefer="openai"),
        )

    result = ev.evaluate(case, run)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
