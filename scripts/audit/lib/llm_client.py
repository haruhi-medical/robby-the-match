#!/usr/bin/env python3
"""
LLMClient — ゲートキーパー(Opus) / 整合性補助(gpt-4o-mini) 統一インタフェース

設計上の役割分離 (DESIGN.md §0):
    - 計画者(planner): Claude Sonnet または gpt-4o-mini
    - ゲートキーパー(gatekeeper): Claude Opus 専用 ← このクラスのデフォルト
    - 同じLLMを両方で使うと self-evaluation bias が生じる

【優先順位】
    1. ANTHROPIC_API_KEY が .env または環境変数にあれば Anthropic Claude
    2. なければ OPENAI_API_KEY で OpenAI GPT-4o (fallback)
    3. どちらも無ければ ``LLMClientConfigError``

【使い方】
    >>> client = LLMClient(model="claude-opus-4-7")
    >>> txt = client.generate("hello")
    >>> obj = client.generate_json("Output JSON {score: 1-5}")

【self-consistency 用ヘルパ】
    >>> scores = client.generate_json_n("...prompt...", n=3, key="score")
    >>> median = sorted(scores)[len(scores) // 2]
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================================
# 例外
# ============================================================================

class LLMClientError(Exception):
    """LLMClient 例外基底クラス"""


class LLMClientConfigError(LLMClientError):
    """API key 未設定など設定不備"""


class LLMClientAPIError(LLMClientError):
    """API呼出失敗 (タイムアウト/レート制限/サーバエラー)"""


class LLMClientParseError(LLMClientError):
    """応答のJSON解析失敗"""


# ============================================================================
# .env ローダ（依存ゼロ）
# ============================================================================

def _load_env(env_path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _resolve_repo_root() -> Path:
    """``scripts/audit/lib/`` から3階層上 = repo root"""
    return Path(__file__).resolve().parent.parent.parent.parent


# ============================================================================
# モデル名マッピング
# ============================================================================

# 設計書指定: ゲートキーパー = Opus
ANTHROPIC_MODEL_ALIASES = {
    "claude-opus-4-7": "claude-opus-4-5",  # SDK上は claude-opus-4-5 (4.7は1M-context版エイリアス想定)
    "claude-opus": "claude-opus-4-5",
    "claude-sonnet": "claude-sonnet-4-5",
    "claude-sonnet-4-7": "claude-sonnet-4-5",
    "claude-haiku": "claude-haiku-4-5",
}

OPENAI_FALLBACK_MODEL = "gpt-4o"
OPENAI_LIGHT_MODEL = "gpt-4o-mini"


# ============================================================================
# LLMClient
# ============================================================================

class LLMClient:
    """Anthropic / OpenAI 統一クライアント。

    Args:
        model: 第一希望モデル。Anthropic 形式 (``claude-opus-4-7``) を渡しても
               自動的に SDK 名 (``claude-opus-4-5``) に解決される。
        prefer: ``"anthropic"`` / ``"openai"`` で優先プロバイダ強制。
                省略時は ANTHROPIC_API_KEY 優先。
        env_path: ``.env`` のパス。省略時 repo root の ``.env``。
        max_retries: API失敗時のリトライ回数。
        retry_delay: リトライ前の待機秒。

    Attributes:
        provider: 実際に使われているプロバイダ ``"anthropic"`` or ``"openai"``。
        model: 解決済みのモデル名（プロバイダSDK直渡し可能な文字列）。
    """

    def __init__(
        self,
        model: str = "claude-opus-4-7",
        prefer: Optional[str] = None,
        env_path: Optional[Path] = None,
        max_retries: int = 2,
        retry_delay: float = 2.0,
    ) -> None:
        self.env_path = env_path or (_resolve_repo_root() / ".env")
        env = _load_env(self.env_path)

        self._anthropic_key = (
            os.environ.get("ANTHROPIC_API_KEY")
            or env.get("ANTHROPIC_API_KEY", "")
        )
        self._openai_key = (
            os.environ.get("OPENAI_API_KEY")
            or env.get("OPENAI_API_KEY", "")
        )

        # provider 決定
        want = (prefer or "").lower()
        if want == "anthropic":
            if not self._anthropic_key:
                raise LLMClientConfigError("ANTHROPIC_API_KEY required (prefer='anthropic')")
            self.provider = "anthropic"
        elif want == "openai":
            if not self._openai_key:
                raise LLMClientConfigError("OPENAI_API_KEY required (prefer='openai')")
            self.provider = "openai"
        else:
            # auto: model がclaude系なら Anthropic 優先、それ以外はopenai
            is_claude = model.lower().startswith("claude") or model in ANTHROPIC_MODEL_ALIASES
            if is_claude and self._anthropic_key:
                self.provider = "anthropic"
            elif self._openai_key:
                self.provider = "openai"
            elif self._anthropic_key:
                self.provider = "anthropic"
            else:
                raise LLMClientConfigError(
                    f"No API key found in env or {self.env_path} "
                    "(need ANTHROPIC_API_KEY or OPENAI_API_KEY)"
                )

        # モデル名解決
        self.model = self._resolve_model_name(model, self.provider)
        self.max_retries = max(0, max_retries)
        self.retry_delay = retry_delay

        # SDK lazy import
        self._anthropic_client = None
        self._openai_client = None

        # コスト追跡
        self.total_calls = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    # ------------------------------------------------------------------
    # モデル名解決
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_model_name(model: str, provider: str) -> str:
        """`claude-opus-4-7` のようなエイリアスを SDK 直渡し可能な名前に解決。

        Args:
            model: ユーザ指定モデル名。
            provider: ``"anthropic"`` / ``"openai"``。

        Returns:
            プロバイダSDKに渡せるモデル名。
        """
        if provider == "anthropic":
            # claude-* 以外が来たらフォールバック (例: gpt-4o指定→opus)
            if not model.lower().startswith("claude"):
                return ANTHROPIC_MODEL_ALIASES["claude-opus"]
            return ANTHROPIC_MODEL_ALIASES.get(model, model)
        # openai
        if model.lower().startswith("claude"):
            # claude指定→openaiフォールバック時はgpt-4o
            return OPENAI_FALLBACK_MODEL
        return model

    # ------------------------------------------------------------------
    # SDK lazy init
    # ------------------------------------------------------------------

    def _get_anthropic(self):
        if self._anthropic_client is None:
            try:
                import anthropic  # noqa: WPS433
            except ImportError as e:
                raise LLMClientConfigError("anthropic SDK not installed") from e
            self._anthropic_client = anthropic.Anthropic(api_key=self._anthropic_key)
        return self._anthropic_client

    def _get_openai(self):
        if self._openai_client is None:
            try:
                import openai  # noqa: WPS433
            except ImportError as e:
                raise LLMClientConfigError("openai SDK not installed") from e
            self._openai_client = openai.OpenAI(api_key=self._openai_key)
        return self._openai_client

    # ------------------------------------------------------------------
    # generate
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        system: Optional[str] = None,
    ) -> str:
        """テキスト生成。プロバイダ抽象化。

        Args:
            prompt: ユーザプロンプト。
            max_tokens: 最大出力トークン。
            temperature: サンプリング温度（self-consistency用は呼び側で固定 or 多様化）。
            system: システムプロンプト（任意）。

        Returns:
            生成テキスト（前後trim済み）。
        """
        last_err: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self.provider == "anthropic":
                    return self._generate_anthropic(prompt, max_tokens, temperature, system)
                return self._generate_openai(prompt, max_tokens, temperature, system)
            except LLMClientAPIError as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
        # 通常到達不可
        raise LLMClientAPIError(f"all retries exhausted: {last_err}")

    def _generate_anthropic(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        client = self._get_anthropic()
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            res = client.messages.create(**kwargs)
        except Exception as e:  # noqa: BLE001
            raise LLMClientAPIError(f"anthropic.messages.create failed: {e}") from e

        # コスト追跡
        self.total_calls += 1
        try:
            self.total_input_tokens += int(getattr(res.usage, "input_tokens", 0) or 0)
            self.total_output_tokens += int(getattr(res.usage, "output_tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            pass

        # content[0].text を取り出す（stream/text両対応）
        try:
            for block in res.content:
                # block: TextBlock(text=...) or dict
                t = getattr(block, "text", None)
                if t is None and isinstance(block, dict):
                    t = block.get("text")
                if t:
                    return t.strip()
        except Exception as e:  # noqa: BLE001
            raise LLMClientParseError(f"anthropic response parse: {e}") from e
        return ""

    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system: Optional[str],
    ) -> str:
        client = self._get_openai()
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            res = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:  # noqa: BLE001
            raise LLMClientAPIError(f"openai.chat.completions failed: {e}") from e

        self.total_calls += 1
        try:
            usage = getattr(res, "usage", None)
            if usage:
                self.total_input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
                self.total_output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)
        except Exception:  # noqa: BLE001
            pass

        try:
            return (res.choices[0].message.content or "").strip()
        except Exception as e:  # noqa: BLE001
            raise LLMClientParseError(f"openai response parse: {e}") from e

    # ------------------------------------------------------------------
    # JSON 専用ヘルパ
    # ------------------------------------------------------------------

    def generate_json(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.3,
        system: Optional[str] = None,
        default: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """JSON出力を期待するgenerate。失敗時は ``default`` または例外。

        プロンプトに「JSONのみで出力」と明記推奨。
        ``\`\`\`json ... \`\`\``ブロックも自動抽出。
        """
        text = self.generate(prompt, max_tokens=max_tokens, temperature=temperature, system=system)
        return _parse_json_lenient(text, default=default)

    def generate_json_n(
        self,
        prompt: str,
        n: int = 3,
        max_tokens: int = 500,
        temperature: float = 0.3,
        system: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """同一プロンプトを n 回独立呼出（self-consistency 用）。

        各呼出はseedをずらすため、temperatureは0より大きい推奨（0.3デフォルト）。

        Returns:
            n 個の dict のリスト（解析失敗分は除外）。
        """
        results: List[Dict[str, Any]] = []
        for _ in range(max(1, n)):
            try:
                obj = self.generate_json(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                )
                results.append(obj)
            except (LLMClientAPIError, LLMClientParseError):
                # 1回失敗しても他の応答で中央値が出せれば良い
                continue
        return results

    # ------------------------------------------------------------------
    # コスト試算
    # ------------------------------------------------------------------

    def cost_summary(self) -> Dict[str, Any]:
        """累積トークン+概算USD。

        単価（2026-04時点の参考値）:
            - Anthropic Opus: $15/MTok入, $75/MTok出
            - OpenAI gpt-4o:  $2.5/MTok入, $10/MTok出
            - OpenAI gpt-4o-mini: $0.15/MTok入, $0.60/MTok出
        """
        if self.provider == "anthropic" and "opus" in self.model.lower():
            in_rate, out_rate = 15.0 / 1_000_000, 75.0 / 1_000_000
        elif self.provider == "openai" and "mini" in self.model.lower():
            in_rate, out_rate = 0.15 / 1_000_000, 0.60 / 1_000_000
        elif self.provider == "openai":
            in_rate, out_rate = 2.5 / 1_000_000, 10.0 / 1_000_000
        else:
            in_rate, out_rate = 3.0 / 1_000_000, 15.0 / 1_000_000  # claude sonnet概算
        usd = (
            self.total_input_tokens * in_rate
            + self.total_output_tokens * out_rate
        )
        return {
            "provider": self.provider,
            "model": self.model,
            "calls": self.total_calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "estimated_usd": round(usd, 4),
        }


# ============================================================================
# JSON 寛容パーサ
# ============================================================================

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_JSON_BARE_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def _parse_json_lenient(
    text: str,
    default: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """LLM応答からJSONを抽出。fence優先 → 最初の {...} → 失敗時 default。"""
    text = (text or "").strip()
    # 1) ```json ... ```
    m = _JSON_FENCE_RE.search(text)
    candidates = [m.group(1)] if m else []
    # 2) bare {...}
    m2 = _JSON_BARE_RE.search(text)
    if m2:
        candidates.append(m2.group(1))
    # 3) raw text
    candidates.append(text)

    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict):
                return obj
            if isinstance(obj, list):
                return {"_list": obj}
        except json.JSONDecodeError:
            continue

    if default is not None:
        return default
    raise LLMClientParseError(f"failed to parse JSON from: {text[:300]}")


# ============================================================================
# CLI 動作確認
# ============================================================================

if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="LLMClient smoke test")
    parser.add_argument("--prompt", default="JSON で {\"ok\": true} を返して")
    parser.add_argument("--model", default="claude-opus-4-7")
    parser.add_argument("--prefer", default=None, choices=[None, "anthropic", "openai"])
    parser.add_argument("--n", type=int, default=1)
    args = parser.parse_args()

    cli = LLMClient(model=args.model, prefer=args.prefer)
    print(f"[provider={cli.provider} model={cli.model}]")
    if args.n > 1:
        results = cli.generate_json_n(args.prompt, n=args.n)
        for i, r in enumerate(results, 1):
            print(f"#{i}: {json.dumps(r, ensure_ascii=False)}")
    else:
        print(cli.generate(args.prompt))
    print(json.dumps(cli.cost_summary(), ensure_ascii=False))
