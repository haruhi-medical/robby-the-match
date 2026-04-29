# scripts/audit/lib — 監査システム基盤ライブラリ

ナースロビー LINE Bot 全体品質監査システム ([設計書](../../../docs/audit/2026-04-29-qa-system/DESIGN.md)) の基盤ライブラリ。

| ファイル | 役割 |
|---------|------|
| `line_client.py` | Worker への E2E webhook 送信クライアント |
| `chain_logger.py` | 改ざん耐性 hash-chain + Ed25519 監査ログ |

cron用ユーティリティは `../verify_chain.py`。

---

## セットアップ

```bash
# 1) 依存ライブラリ (cryptography は通常インストール済み)
python3 -c "import cryptography; print(cryptography.__version__)"
# → 2.x 以上があればOK

# 2) Ed25519 鍵ペア生成 (初回のみ)
python3 -c "from scripts.audit.lib.chain_logger import generate_keypair; print(generate_keypair())"
# → ~/.config/audit/ed25519_{priv,pub}.pem (priv: 0600, pub: 0644)

# 3) .env に LINE_CHANNEL_SECRET があることを確認
grep LINE_CHANNEL_SECRET ~/robby-the-match/.env
```

---

## LineClient

Worker へ webhook イベントを HMAC-SHA256 署名付きで送る。
既存 `scripts/test_line_flow.py` の署名ロジックと完全互換。

### 基本

```python
from scripts.audit.lib.line_client import LineClient

c = LineClient()                         # .env から自動ロード
uid = c.make_test_user_id("aica001")     # "U_TEST_..." 33文字
res = c.send_text(uid, "こんにちは")      # text message
print(res["status"], res["body"])
```

### 全API

| メソッド | 用途 |
|---------|------|
| `send_text(uid, text)` | text message webhook |
| `send_postback(uid, data, params=None)` | postback webhook |
| `send_audio(uid, audio_path)` | audio message (Whisperテスト用、base64同梱) |
| `send_follow(uid)` | follow event |
| `send_unfollow(uid)` | unfollow event (replyToken無し) |
| `send_webhook(events)` | 任意イベント配列（バッチ・異常系テスト） |
| `send_line_start(source, intent, answers, ...)` | LP 経由のセッション作成 (`/api/line-start` GET) |
| `link_session(session_id, user_id)` | LIFF link (`/api/link-session` POST) |
| `make_test_user_id(suffix)` | `U_TEST_` + 26文字 → 33文字 |
| `reply_token()` | 擬似 reply token |
| `sign_body(body)` | HMAC-SHA256 → base64 |

### 例外

| 例外 | 発生条件 |
|------|---------|
| `LineClientConfigError` | `.env` 未設定、ファイル不存在 |
| `LineClientNetworkError` | DNS/接続/タイムアウト失敗 |
| `LineClientAuthError` | HTTP 401/403 |
| `LineClientParseError` | 予期せぬレスポンス形式 |

### LP→follow 完全フロー例

```python
c = LineClient()
uid = c.make_test_user_id()

# 1) LP診断回答 → session 作成
ls = c.send_line_start(
    source="shindan",
    intent="diagnose",
    answers={"prefecture": "kanagawa", "area": "yokohama_kawasaki"},
)
sid = ls["session_id"]

# 2) LIFF で session と userId を紐付け
c.link_session(sid, uid)

# 3) follow webhook → Worker は matching_preview Flex 送信を試みる
c.send_follow(uid)
```

---

## ChainLogger

監査ログを `chain.jsonl` (1行=1イベント, append-only) に記録。
各行は `prev_hash` と SHA-256 でチェーン化、Ed25519 署名で改ざん検出。

### 基本

```python
from scripts.audit.lib.chain_logger import ChainLogger

logger = ChainLogger("logs/audit/2026-04-29")

# イベント追記
h1 = logger.append("planner", "case_generated", {"case_id": "aica_001"})
h2 = logger.append("runner", "case_executed", {"case_id": "aica_001", "ok": True})
h3 = logger.append("gatekeeper", "verdict",
                   {"case_id": "aica_001", "F": 5, "U": 4, "verdict": "PASS"})

# 検証 (任意の時点で)
result = logger.verify_chain()
# {"ok": True, "broken_at": -1, "total": 3, "reason": None}

# 外部anchor用 summary
logger.export_for_anchor("logs/audit/2026-04-29/anchor.json")
print(logger.latest_hash())   # Slack/git tag に貼る値
```

### actor / kind の規約

| actor | 例 |
|-------|-----|
| `planner` | テスト計画者 (Sonnet) |
| `runner` | E2E実行 |
| `gatekeeper` | 判定者 (Opus、別ペルソナ) |
| `fixer` | 自動修正提案者 |
| `human:<name>` | 人間操作 (例: `human:yoshiyuki`) |

| kind | 用途 |
|------|------|
| `case_generated` | テストケース生成 |
| `case_executed` | E2E実行完了 |
| `verdict` | 判定結果 |
| `patch_proposed` | 修正案生成 |
| `patch_applied` | 修正適用 |
| `rollback` | 自動ロールバック |
| `anchor_published` | 外部anchor送信 |

### tamper-resistance の仕組み

1. **hash chain**: `this_hash = SHA-256(prev_hash || canonical_json(record_pre))`
   - `record_pre` には `seq, ts, actor, kind, payload, payload_sha256, prev_hash` を含む
   - 中間行を改ざんすると、その行 + 以降の `this_hash` が全て不一致になる
2. **payload_sha256**: payload単体のSHA-256。payload改ざん検出を高速化
3. **Ed25519 署名**: `signature = sign(priv, this_hash_bytes)`
4. **canonical JSON**: `sort_keys=True, ensure_ascii=False, separators=(",", ":")`
5. **外部anchor**: `latest_hash` を毎日 Slack `#claudecode` + git tag で公開

### 鍵管理

- 私有鍵: `~/.config/audit/ed25519_priv.pem` (mode 0600)
- 公開鍵: `~/.config/audit/ed25519_pub.pem` (mode 0644)
- 私有鍵を失うと既存ログの新規追記は破綻 (検証は公開鍵のみで可)
- 鍵ローテ: 旧 `pubkey_id` のログは旧公開鍵でverify、新規は新鍵で署名

```python
# テスト・分離環境用に独立した鍵を使う
from scripts.audit.lib.chain_logger import ChainLogger, generate_keypair

generate_keypair("/tmp/audit_keys", pubkey_id="test-2026-04", overwrite=True)
logger = ChainLogger(
    "/tmp/audit_logs",
    private_key_path="/tmp/audit_keys/ed25519_priv.pem",
    public_key_path="/tmp/audit_keys/ed25519_pub.pem",
    auto_generate_key=False,
)
```

---

## verify_chain.py (cron 用)

毎時、本日のログを検証。破断を検出すると Slack `#claudecode` へ 🚨 通知 + `exit 1`。

```bash
# 本日分を検証
python3 scripts/audit/verify_chain.py --since today

# 特定日付
python3 scripts/audit/verify_chain.py --date 2026-04-29

# 任意ディレクトリ + Slack抑止
python3 scripts/audit/verify_chain.py --log-dir /tmp/foo --no-slack -v
```

### cron 例

```cron
# 毎時 :05 に本日ログを検証
5 * * * * cd ~/robby-the-match && /usr/bin/env python3 \
    scripts/audit/verify_chain.py --since today >> logs/audit/cron.log 2>&1
```

---

## テスト実行例

```bash
cd ~/robby-the-match

# 1) LineClient 動作確認
python3 -c "from scripts.audit.lib.line_client import LineClient; c = LineClient(); print(c.make_test_user_id())"
# → U_TEST_xxxxxxxxxxxxxxxxxxxxxxxxxx (33文字)

# 2) ChainLogger 動作確認
python3 -c "from scripts.audit.lib.chain_logger import ChainLogger; l = ChainLogger('/tmp/qa_test'); l.append('test', 'init', {'msg': 'ok'}); print(l.verify_chain())"
# → {'ok': True, 'broken_at': -1, 'total': 1, 'reason': None}

# 3) verify_chain --help
python3 scripts/audit/verify_chain.py --help

# 4) tamper検出テスト
python3 -c "
import sys, json
sys.path.insert(0, '.')
from scripts.audit.lib.chain_logger import ChainLogger
l = ChainLogger('/tmp/qa_tamper')
l.append('test', 'a', {'n': 1})
l.append('test', 'b', {'n': 2})
# 1行目を改ざん
p = '/tmp/qa_tamper/chain.jsonl'
lines = open(p).readlines()
rec = json.loads(lines[0]); rec['payload']['n'] = 999
lines[0] = json.dumps(rec, ensure_ascii=False, separators=(',', ':')) + '\n'
open(p, 'w').writelines(lines)
print(l.verify_chain())
"
# → {'ok': False, 'broken_at': 1, 'total': 2, 'reason': 'payload_sha256 mismatch (payload tampered)'}
```

---

## 設計上の注意

- `auditTrail` (Worker側 entry に埋め込む実行追跡) と `chain.jsonl` (audit側ログ) は別物。
  Worker は KV に書き、監査側は ChainLogger で別途記録する（責務分離）。
- `chain.jsonl` を **rotate するときは絶対に切り詰めるな**。日次ディレクトリ
  (`logs/audit/YYYY-MM-DD/chain.jsonl`) を分けることで自然にローテ。
- 各日チェーンの先頭は `prev_hash = "0" * 64` (genesis)。
  日跨ぎ整合性が必要な場合は、前日 `latest_hash` を新日初行 payload に埋め込む。
