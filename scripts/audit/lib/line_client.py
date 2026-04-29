#!/usr/bin/env python3
"""
LineClient — ナースロビー Worker への E2E テスト用クライアント

既存 ``scripts/test_line_flow.py`` の HMAC-SHA256 署名/webhook送信ロジックを
ライブラリ化したもの。互換性を保つため、署名ロジックは bytes ベースで完全一致。

【主な機能】
- LINE webhookイベント送信 (text/postback/audio/follow/unfollow)
- LP→Worker /api/line-start を経由したsession作成
- テスト専用userId (``U_TEST_`` prefix + 32文字hex) 生成
- HMAC-SHA256 署名生成 (X-Line-Signature ヘッダ用)

【使い方】
    >>> from scripts.audit.lib.line_client import LineClient
    >>> c = LineClient()
    >>> uid = c.make_test_user_id("aica001")
    >>> c.send_text(uid, "こんにちは")

【例外】
- ``LineClientConfigError``: 環境変数欠落・設定不整合
- ``LineClientNetworkError``: HTTP/TCP通信失敗
- ``LineClientAuthError``: 4xx 認証/署名失敗
- ``LineClientParseError``: レスポンスJSON解析失敗
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request


# ============================================================================
# 例外クラス
# ============================================================================

class LineClientError(Exception):
    """LineClient 例外基底クラス"""


class LineClientConfigError(LineClientError):
    """設定不備（.env欠落など）"""


class LineClientNetworkError(LineClientError):
    """ネットワーク失敗（接続タイムアウト/DNSなど）"""


class LineClientAuthError(LineClientError):
    """認証失敗 (HTTP 401/403、署名不一致)"""


class LineClientParseError(LineClientError):
    """レスポンス解析失敗"""


# ============================================================================
# .env ローダ（依存ゼロ）
# ============================================================================

def _load_env(env_path: Path) -> Dict[str, str]:
    """``.env`` を1行ずつパース。``KEY=VALUE`` 形式のみ対応。"""
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


# ============================================================================
# 定数
# ============================================================================

DEFAULT_WORKER_URL = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"
DEFAULT_TIMEOUT_SEC = 15
USER_ID_HEX_LEN = 32  # LINE userId は U + 32文字hex (合計33文字)
TEST_USER_ID_PREFIX = "U_TEST_"


# ============================================================================
# LineClient
# ============================================================================

class LineClient:
    """ナースロビー Worker への E2E テスト用クライアント。

    Args:
        worker_url: Worker base URL。省略時は ``DEFAULT_WORKER_URL``。
        channel_secret: LINE channel secret。省略時は ``.env`` から読込。
        env_path: ``.env`` ファイルパス。省略時は repo root の ``.env``。
        timeout: HTTP タイムアウト秒。

    Raises:
        LineClientConfigError: ``channel_secret`` が空。
    """

    def __init__(
        self,
        worker_url: Optional[str] = None,
        channel_secret: Optional[str] = None,
        env_path: Optional[Path] = None,
        timeout: int = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        # repo root = scripts/audit/lib/ から3階層上
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        self.env_path = env_path or (repo_root / ".env")
        env = _load_env(self.env_path)

        self.worker_url = (
            worker_url
            or os.environ.get("WORKER_BASE")
            or env.get("WORKER_BASE")
            or DEFAULT_WORKER_URL
        ).rstrip("/")

        self.channel_secret = (
            channel_secret
            or os.environ.get("LINE_CHANNEL_SECRET")
            or env.get("LINE_CHANNEL_SECRET", "")
        )
        self.channel_access_token = (
            os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
            or env.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        )

        if not self.channel_secret:
            raise LineClientConfigError(
                f"LINE_CHANNEL_SECRET not found in env or {self.env_path}"
            )

        self.timeout = timeout

    # ------------------------------------------------------------------
    # 署名
    # ------------------------------------------------------------------

    def sign_body(self, body: str | bytes) -> str:
        """LINE webhook 署名 (HMAC-SHA256, base64) を生成。

        ``test_line_flow.py`` の ``sign_body(body: bytes)`` と完全互換。

        Args:
            body: 生のリクエストボディ。``str`` の場合は UTF-8 で encode。

        Returns:
            base64 エンコード済み署名文字列（X-Line-Signature 用）。
        """
        if isinstance(body, str):
            body_bytes = body.encode("utf-8")
        else:
            body_bytes = body
        h = hmac.new(self.channel_secret.encode(), body_bytes, hashlib.sha256).digest()
        return base64.b64encode(h).decode()

    # ------------------------------------------------------------------
    # 内部 HTTP ヘルパ
    # ------------------------------------------------------------------

    def _post(
        self,
        path: str,
        body: bytes,
        headers: Dict[str, str],
        parse_json: bool = True,
    ) -> Dict[str, Any]:
        """``path`` に POST 送信。レスポンス情報を dict で返す。

        Returns:
            ``{"status": int, "body": str|dict, "raw": str}``
        """
        url = f"{self.worker_url}{path}"
        req = urllib.request.Request(url, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                raw = res.read().decode("utf-8", errors="replace")
                parsed: Any = raw
                if parse_json and raw.strip().startswith(("{", "[")):
                    try:
                        parsed = json.loads(raw)
                    except json.JSONDecodeError:
                        # 非JSONでも失敗扱いにせず、生文字列のまま返す
                        parsed = raw
                return {"status": res.status, "body": parsed, "raw": raw}
        except urllib.error.HTTPError as e:
            err_raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            if e.code in (401, 403):
                raise LineClientAuthError(
                    f"POST {path} returned {e.code}: {err_raw[:200]}"
                ) from e
            # 4xx/5xx を含むレスポンスも返却（呼び出し側が判定）
            return {"status": e.code, "body": err_raw, "raw": err_raw}
        except urllib.error.URLError as e:
            raise LineClientNetworkError(f"POST {path} failed: {e}") from e

    def _get(
        self,
        path: str,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        follow_redirect: bool = False,
    ) -> Dict[str, Any]:
        """``path`` に GET 送信。redirect (302/303) を制御可能。"""
        qs = ""
        if params:
            qs = "?" + urllib.parse.urlencode(params)
        url = f"{self.worker_url}{path}{qs}"
        req = urllib.request.Request(
            url, method="GET", headers=headers or {"User-Agent": "Mozilla/5.0 (LineClient)"}
        )

        if not follow_redirect:
            class _NoRedirect(urllib.request.HTTPRedirectHandler):
                def http_error_302(self, req, fp, code, msg, headers):  # noqa: D401
                    raise urllib.error.HTTPError(req.full_url, code, msg, headers, fp)
                http_error_301 = http_error_303 = http_error_307 = http_error_302

            opener = urllib.request.build_opener(_NoRedirect)
        else:
            opener = urllib.request.build_opener()

        try:
            with opener.open(req, timeout=self.timeout) as res:
                raw = res.read().decode("utf-8", errors="replace")
                return {
                    "status": res.status,
                    "body": raw,
                    "raw": raw,
                    "headers": dict(res.headers.items()),
                }
        except urllib.error.HTTPError as e:
            err_raw = ""
            try:
                err_raw = e.read().decode("utf-8", errors="replace") if e.fp else ""
            except Exception:
                pass
            if e.code in (301, 302, 303, 307, 308):
                return {
                    "status": e.code,
                    "body": err_raw,
                    "raw": err_raw,
                    "headers": dict(e.headers.items()) if e.headers else {},
                    "location": e.headers.get("Location") if e.headers else None,
                }
            if e.code in (401, 403):
                raise LineClientAuthError(
                    f"GET {path} returned {e.code}: {err_raw[:200]}"
                ) from e
            return {"status": e.code, "body": err_raw, "raw": err_raw}
        except urllib.error.URLError as e:
            raise LineClientNetworkError(f"GET {path} failed: {e}") from e

    # ------------------------------------------------------------------
    # webhook 送信
    # ------------------------------------------------------------------

    def send_webhook(
        self,
        events: List[Dict[str, Any]],
        headers_override: Optional[Dict[str, str]] = None,
        destination: str = "TEST_BOT",
    ) -> Dict[str, Any]:
        """webhook イベント配列を Worker に送信し、署名を自動付与。

        Args:
            events: LINE webhook events 配列。
            headers_override: 追加/上書きヘッダ（署名検証ミスを意図的に試す等）。
            destination: ``destination`` フィールド値。

        Returns:
            ``{"status": int, "body": ..., "raw": str}``
        """
        payload = {"destination": destination, "events": events}
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        sig = self.sign_body(body)
        headers = {
            "Content-Type": "application/json",
            "X-Line-Signature": sig,
            "User-Agent": "LineBotWebhook/2.0",
        }
        if headers_override:
            headers.update(headers_override)
        return self._post("/api/line-webhook", body, headers)

    # ------------------------------------------------------------------
    # イベント生成 + 送信
    # ------------------------------------------------------------------

    def _base_event(
        self,
        type_: str,
        user_id: str,
        reply_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        ev: Dict[str, Any] = {
            "type": type_,
            "timestamp": int(time.time() * 1000),
            "source": {"type": "user", "userId": user_id},
            "mode": "active",
            "webhookEventId": "test-" + uuid.uuid4().hex,
            "deliveryContext": {"isRedelivery": False},
        }
        if reply_token is not None:
            ev["replyToken"] = reply_token
        elif type_ in ("message", "postback", "follow"):
            ev["replyToken"] = self.reply_token()
        return ev

    def send_text(
        self,
        user_id: str,
        text: str,
        reply_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """text message イベントを送信。"""
        ev = self._base_event("message", user_id, reply_token)
        ev["message"] = {
            "id": str(int(time.time() * 1000)),
            "type": "text",
            "text": text,
        }
        return self.send_webhook([ev])

    def send_postback(
        self,
        user_id: str,
        data: str,
        reply_token: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """postback イベントを送信。"""
        ev = self._base_event("postback", user_id, reply_token)
        ev["postback"] = {"data": data}
        if params:
            ev["postback"]["params"] = params
        return self.send_webhook([ev])

    def send_audio(
        self,
        user_id: str,
        audio_path: str,
        reply_token: Optional[str] = None,
        duration_ms: int = 3000,
    ) -> Dict[str, Any]:
        """audio message イベントを送信。

        ファイルを読み base64 化して payload に同梱（``contentBase64``）。
        Worker側でWhisper処理時に参照する独自フィールド扱い（webhook標準仕様外）。
        """
        path = Path(audio_path).expanduser()
        if not path.exists():
            raise LineClientConfigError(f"audio file not found: {path}")
        b64 = base64.b64encode(path.read_bytes()).decode("ascii")
        ev = self._base_event("message", user_id, reply_token)
        ev["message"] = {
            "id": str(int(time.time() * 1000)),
            "type": "audio",
            "duration": duration_ms,
            "contentProvider": {"type": "line"},
            "contentBase64": b64,  # テスト用拡張（Workerで分岐）
            "filename": path.name,
        }
        return self.send_webhook([ev])

    def send_follow(
        self,
        user_id: str,
        reply_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """follow イベントを送信。"""
        ev = self._base_event("follow", user_id, reply_token)
        return self.send_webhook([ev])

    def send_unfollow(self, user_id: str) -> Dict[str, Any]:
        """unfollow イベントを送信（reply_token なし仕様）。"""
        ev = self._base_event("unfollow", user_id, reply_token=None)
        # unfollow は仕様上 replyToken を持たない
        ev.pop("replyToken", None)
        return self.send_webhook([ev])

    # ------------------------------------------------------------------
    # /api/line-start 経由のセッション作成
    # ------------------------------------------------------------------

    def send_line_start(
        self,
        source: str = "test",
        intent: str = "see_jobs",
        session_id: Optional[str] = None,
        answers: Optional[Dict[str, Any]] = None,
        area: str = "",
        page_type: str = "paid_lp",
        **extra: Any,
    ) -> Dict[str, Any]:
        """``/api/line-start`` に GET し、LP由来のセッションを作成。

        Args:
            source: 流入元 (``shindan`` / ``paid`` / ``test``)。
            intent: 意図 (``diagnose`` / ``see_jobs`` / ``ask`` ...)。
            session_id: 省略時は新規 UUID。
            answers: LP診断回答 dict。JSON シリアライズして渡す。
            area: エリアコード。
            page_type: LP種別。
            **extra: 追加クエリパラメタ。

        Returns:
            ``{"session_id": str, "status": int, "location": str|None, ...}``
        """
        sid = session_id or str(uuid.uuid4())
        params: Dict[str, str] = {
            "session_id": sid,
            "source": source,
            "intent": intent,
            "area": area,
            "page_type": page_type,
        }
        if answers is not None:
            params["answers"] = json.dumps(answers, ensure_ascii=False)
        for k, v in extra.items():
            params[k] = str(v)

        res = self._get("/api/line-start", params=params, follow_redirect=False)
        res["session_id"] = sid
        return res

    def link_session(
        self,
        session_id: str,
        user_id: str,
        already_friend: bool = False,
    ) -> Dict[str, Any]:
        """``/api/link-session`` で session と userId を紐付け。"""
        body = json.dumps(
            {
                "session_id": session_id,
                "user_id": user_id,
                "already_friend": already_friend,
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (LineClient)",
        }
        return self._post("/api/link-session", body, headers)

    # ------------------------------------------------------------------
    # ID生成ヘルパ
    # ------------------------------------------------------------------

    def make_test_user_id(self, suffix: Optional[str] = None) -> str:
        """テスト用 userId を生成。

        本番LINE仕様: ``U`` + 32文字 hex。
        テスト用は ``U_TEST_`` (7文字) + 25文字 hex で合計 33文字を維持しつつ、
        suffix 指定時は suffix を埋め込み残りを hex で埋める。

        Args:
            suffix: 識別用文字列（英数のみ推奨）。

        Returns:
            ``U_TEST_<suffix><hex...>`` 形式の文字列（合計 33文字）。
        """
        # LINE userId フォーマット: 'U' + 32hex → 33文字
        # 本クラスは "U_TEST_" prefix のため hex部分は 32 - len("_TEST_") = 26文字
        prefix = TEST_USER_ID_PREFIX  # "U_TEST_" (7文字)
        target_len = 1 + USER_ID_HEX_LEN  # 33
        body_len = target_len - len(prefix)  # 26
        if suffix:
            # suffix を ASCII safe な小文字hex化（衝突回避のため hash 一部利用）
            safe = "".join(c for c in suffix.lower() if c in "0123456789abcdef")
            if not safe:
                # hex以外の場合は SHA-256 で hex化
                safe = hashlib.sha256(suffix.encode()).hexdigest()
            head = safe[: max(0, body_len - 8)]
            tail = uuid.uuid4().hex[:8]
            body = (head + tail)[:body_len].ljust(body_len, "0")
        else:
            body = uuid.uuid4().hex[:body_len].ljust(body_len, "0")
        return prefix + body

    def reply_token(self) -> str:
        """擬似 reply token を生成。Worker側ではテスト用token無効扱いで構わない。"""
        return "test-reply-token-" + uuid.uuid4().hex[:16]
