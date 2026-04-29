#!/usr/bin/env python3
"""
ChainLogger — tamper-resistant 監査ログ (hash-chain + Ed25519署名)

設計書 §3 (DESIGN.md) に準拠:
    - hash chain : ``this_hash = SHA-256(prev_hash || canonical_json(payload))``
    - Ed25519署名: 各イベントを私有鍵で署名
    - external anchor: 1日1回 latest_hash を Slack/git tag に固定

【ファイル構造】
    log_dir/                            (例: logs/audit/2026-04-29/)
    ├── chain.jsonl                     # append-only、各行1イベント
    └── meta.json                       # signer_pubkey_id, created_at

    ~/.config/audit/                    (鍵ストア、permission 0700)
    ├── ed25519_priv.pem                # 私有鍵 (PKCS#8 PEM, encrypted=False)
    └── ed25519_pub.pem                 # 公開鍵 (SubjectPublicKeyInfo PEM)

【使い方】
    >>> from scripts.audit.lib.chain_logger import ChainLogger, generate_keypair
    >>> generate_keypair()              # 初回のみ
    >>> logger = ChainLogger("logs/audit/2026-04-29")
    >>> logger.append("planner", "case_generated", {"case_id": "aica_001"})
    >>> result = logger.verify_chain()  # {"ok": True, "broken_at": -1, "total": 1}

【設計上の不変条件】
    - chain.jsonl は append-only。中間行の編集/削除はチェーンを破壊する
    - canonical_json: ``json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",",":"))``
      → ASCII外も保持しつつキーソートのみで決定論性を担保
    - prev_hash の初期値は ``"0" * 64`` (genesis)
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.exceptions import InvalidSignature


# ============================================================================
# 定数
# ============================================================================

GENESIS_HASH = "0" * 64
DEFAULT_KEY_DIR = Path("~/.config/audit").expanduser()
PRIV_KEY_NAME = "ed25519_priv.pem"
PUB_KEY_NAME = "ed25519_pub.pem"
DEFAULT_PUBKEY_ID = "auditor-2026-04"
CHAIN_FILENAME = "chain.jsonl"
META_FILENAME = "meta.json"


# ============================================================================
# 例外
# ============================================================================

class ChainLoggerError(Exception):
    """ChainLogger 例外基底クラス"""


class KeyNotFoundError(ChainLoggerError):
    """Ed25519 鍵ファイル未生成"""


class ChainCorruptError(ChainLoggerError):
    """hash chain 破断検出"""


# ============================================================================
# 鍵管理
# ============================================================================

def generate_keypair(
    out_dir: str | Path = DEFAULT_KEY_DIR,
    pubkey_id: str = DEFAULT_PUBKEY_ID,
    overwrite: bool = False,
) -> Dict[str, str]:
    """新規 Ed25519 鍵ペアを生成し、PEM形式で保存。

    Args:
        out_dir: 保存先ディレクトリ。
        pubkey_id: 鍵識別子（監査ログの ``signer_pubkey_id`` に対応）。
        overwrite: 既存鍵を上書きするか。``False`` の場合、存在時は何もせず返す。

    Returns:
        ``{"priv": "<path>", "pub": "<path>", "pubkey_id": "..."}``
    """
    out = Path(out_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    priv_path = out / PRIV_KEY_NAME
    pub_path = out / PUB_KEY_NAME

    if priv_path.exists() and not overwrite:
        return {
            "priv": str(priv_path),
            "pub": str(pub_path),
            "pubkey_id": pubkey_id,
            "generated": False,
        }

    priv = Ed25519PrivateKey.generate()
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    # 書き込み + permission tighten
    priv_path.write_bytes(priv_pem)
    os.chmod(priv_path, 0o600)
    pub_path.write_bytes(pub_pem)
    os.chmod(pub_path, 0o644)

    return {
        "priv": str(priv_path),
        "pub": str(pub_path),
        "pubkey_id": pubkey_id,
        "generated": True,
    }


def _load_priv_key(path: Path) -> Ed25519PrivateKey:
    if not path.exists():
        raise KeyNotFoundError(
            f"Ed25519 private key not found: {path}\n"
            f"Run: python3 -c 'from scripts.audit.lib.chain_logger import generate_keypair; generate_keypair()'"
        )
    pem = path.read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ChainLoggerError(f"Key at {path} is not Ed25519")
    return key


def _load_pub_key(path: Path) -> Ed25519PublicKey:
    if not path.exists():
        raise KeyNotFoundError(f"Ed25519 public key not found: {path}")
    pem = path.read_bytes()
    key = serialization.load_pem_public_key(pem)
    if not isinstance(key, Ed25519PublicKey):
        raise ChainLoggerError(f"Key at {path} is not Ed25519")
    return key


# ============================================================================
# canonical JSON
# ============================================================================

def _canonical_json(payload: Any) -> bytes:
    """決定論的JSONエンコード。キーソート・空白なし・UTF-8。"""
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _payload_sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _compute_this_hash(prev_hash: str, payload: Any) -> str:
    """``this_hash = SHA-256(prev_hash || canonical_json(payload))``"""
    h = hashlib.sha256()
    h.update(prev_hash.encode("ascii"))
    h.update(_canonical_json(payload))
    return h.hexdigest()


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


# ============================================================================
# ChainLogger
# ============================================================================

class ChainLogger:
    """tamper-resistant 監査ログ writer/verifier。

    Args:
        log_dir: ログ保存ディレクトリ。存在しなければ作成。
        private_key_path: Ed25519私有鍵パス。省略時は ``~/.config/audit/ed25519_priv.pem``。
        public_key_path: 検証用公開鍵パス。省略時は ``~/.config/audit/ed25519_pub.pem``。
        pubkey_id: ログに記録される ``signer_pubkey_id``。
        auto_generate_key: 鍵が無い場合に自動生成するか（テスト用）。
    """

    def __init__(
        self,
        log_dir: str | Path,
        private_key_path: Optional[str | Path] = None,
        public_key_path: Optional[str | Path] = None,
        pubkey_id: str = DEFAULT_PUBKEY_ID,
        auto_generate_key: bool = True,
    ) -> None:
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.chain_path = self.log_dir / CHAIN_FILENAME
        self.meta_path = self.log_dir / META_FILENAME

        priv_path = Path(private_key_path).expanduser() if private_key_path else (
            DEFAULT_KEY_DIR / PRIV_KEY_NAME
        )
        pub_path = Path(public_key_path).expanduser() if public_key_path else (
            DEFAULT_KEY_DIR / PUB_KEY_NAME
        )

        if not priv_path.exists() and auto_generate_key:
            generate_keypair(priv_path.parent, pubkey_id=pubkey_id, overwrite=False)

        self._priv = _load_priv_key(priv_path)
        self._pub = _load_pub_key(pub_path)
        self.pubkey_id = pubkey_id

        # meta.json 初期化
        if not self.meta_path.exists():
            meta = {
                "created_at": _iso_now(),
                "signer_pubkey_id": pubkey_id,
                "pub_key_pem": pub_path.read_text(),
            }
            self.meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))

    # ------------------------------------------------------------------
    # 書き込み
    # ------------------------------------------------------------------

    def _read_last_record(self) -> Optional[Dict[str, Any]]:
        """末尾レコードを取得（無ければ ``None``）。"""
        if not self.chain_path.exists():
            return None
        last = None
        with self.chain_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    last = json.loads(line)
                except json.JSONDecodeError:
                    raise ChainCorruptError(f"non-JSON line in {self.chain_path}")
        return last

    def append(self, actor: str, kind: str, payload: Dict[str, Any]) -> str:
        """1イベントをチェーンに追記。

        Args:
            actor: 主体 (``planner`` / ``runner`` / ``gatekeeper`` / ``fixer`` / ``human:<name>``)。
            kind: 種別 (``case_generated`` / ``case_executed`` / ``verdict`` ...)。
            payload: イベント本体。任意のJSON serializable dict。

        Returns:
            算出された ``this_hash`` (hex 64文字)。
        """
        last = self._read_last_record()
        prev_hash = last["this_hash"] if last else GENESIS_HASH
        seq = (last["seq"] + 1) if last else 1

        ts = _iso_now()
        payload_sha = _payload_sha256(payload)

        # 署名対象: this_hash 計算前に作るため canonical な「事前record」を使う
        record_pre: Dict[str, Any] = {
            "seq": seq,
            "ts": ts,
            "actor": actor,
            "kind": kind,
            "payload": payload,
            "payload_sha256": payload_sha,
            "prev_hash": prev_hash,
        }
        this_hash = _compute_this_hash(prev_hash, record_pre)

        # 署名: this_hash の bytes に対して
        signature = self._priv.sign(bytes.fromhex(this_hash))
        sig_b64 = "ed25519:" + _b64(signature)

        record: Dict[str, Any] = {
            **record_pre,
            "this_hash": this_hash,
            "signer_pubkey_id": self.pubkey_id,
            "signature": sig_b64,
        }

        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        # append-only 書き込み（同時実行は推奨しないが、O_APPENDで簡易ロック）
        with self.chain_path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())

        return this_hash

    # ------------------------------------------------------------------
    # 検証
    # ------------------------------------------------------------------

    def verify_chain(self) -> Dict[str, Any]:
        """全行をhash再計算+署名検証。

        Returns:
            ``{"ok": bool, "broken_at": int, "total": int, "reason": str|None}``
            破断あれば ``broken_at`` に該当 seq、それ以外 -1。
        """
        if not self.chain_path.exists():
            return {"ok": True, "broken_at": -1, "total": 0, "reason": "empty"}

        prev_hash = GENESIS_HASH
        total = 0
        with self.chain_path.open("r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, start=1):
                raw = raw.strip()
                if not raw:
                    continue
                total += 1
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError as e:
                    return {
                        "ok": False,
                        "broken_at": lineno,
                        "total": total,
                        "reason": f"json decode failed: {e}",
                    }

                # 順序検証
                if rec.get("seq") != total:
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": f"seq mismatch (expected {total}, got {rec.get('seq')})",
                    }

                # prev_hash 一致
                if rec.get("prev_hash") != prev_hash:
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": "prev_hash mismatch",
                    }

                # payload_sha256 再計算
                expected_payload_sha = _payload_sha256(rec.get("payload"))
                if rec.get("payload_sha256") != expected_payload_sha:
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": "payload_sha256 mismatch (payload tampered)",
                    }

                # this_hash 再計算
                record_pre = {
                    "seq": rec["seq"],
                    "ts": rec["ts"],
                    "actor": rec["actor"],
                    "kind": rec["kind"],
                    "payload": rec["payload"],
                    "payload_sha256": rec["payload_sha256"],
                    "prev_hash": rec["prev_hash"],
                }
                expected_hash = _compute_this_hash(prev_hash, record_pre)
                if rec.get("this_hash") != expected_hash:
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": "this_hash mismatch (chain tampered)",
                    }

                # 署名検証
                sig_str = rec.get("signature", "")
                if not sig_str.startswith("ed25519:"):
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": "signature format invalid",
                    }
                try:
                    sig_bytes = _b64decode(sig_str[len("ed25519:"):])
                    self._pub.verify(sig_bytes, bytes.fromhex(rec["this_hash"]))
                except (InvalidSignature, ValueError) as e:
                    return {
                        "ok": False,
                        "broken_at": rec.get("seq", lineno),
                        "total": total,
                        "reason": f"signature invalid: {e}",
                    }

                prev_hash = rec["this_hash"]

        return {"ok": True, "broken_at": -1, "total": total, "reason": None}

    # ------------------------------------------------------------------
    # アンカー支援
    # ------------------------------------------------------------------

    def latest_hash(self) -> str:
        """最終 ``this_hash`` を返す。空なら ``GENESIS_HASH``。"""
        last = self._read_last_record()
        return last["this_hash"] if last else GENESIS_HASH

    def export_for_anchor(self, output_path: str | Path) -> Dict[str, Any]:
        """Slack/git anchor用 summary を JSON で書き出し。

        Returns:
            ``{"date": str, "total_events": int, "latest_hash": str, "chain_ok": bool}``
        """
        verify = self.verify_chain()
        date_str = self.log_dir.name  # 慣習: log_dir = .../YYYY-MM-DD
        summary = {
            "date": date_str,
            "log_dir": str(self.log_dir),
            "total_events": verify["total"],
            "latest_hash": self.latest_hash(),
            "chain_ok": verify["ok"],
            "broken_at": verify["broken_at"],
            "reason": verify["reason"],
            "signer_pubkey_id": self.pubkey_id,
            "exported_at": _iso_now(),
        }
        out = Path(output_path).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary


# ============================================================================
# base64 helpers (pad-safe)
# ============================================================================

import base64 as _base64


def _b64(b: bytes) -> str:
    return _base64.b64encode(b).decode("ascii")


def _b64decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return _base64.b64decode(s + pad)
