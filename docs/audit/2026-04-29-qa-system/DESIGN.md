# ナースロビー LINE Bot 全体品質監査システム 設計書

**作成日**: 2026-04-29
**目的**: 580件以上の合成施工テストを多視点で評価し、不正困難な監査ログとともに自動修正ループで欠陥が止まるまで回す

---

## 0. エグゼクティブサマリ

監査システム = **2つの独立プロセス + 1つの不可逆ログ**

| 役割 | プロセス | 担当 | 拒否権 |
|------|----------|-----|--------|
| 計画者 | `auditor_planner.py` | テストケース生成・実行・分析 | なし |
| **ゲートキーパー（鬼）** | `auditor_gatekeeper.py` | 多視点判定・合否決定・改善要求 | **あり（最終）** |
| 監査ログ | `auditor_chain.jsonl` (hash-chain) | 全アクションを改ざん不能に記録 | — |

**鉄則**: 計画者とゲートキーパーは**同じLLMを共有してはいけない**（自己評価バイアス）。
プランナーはClaude Sonnet、ゲートキーパーはOpus + 別ペルソナ + 別プロンプトで完全分離。

---

## 1. アーキテクチャ

```
scripts/audit/
├─ lib/         : line_client / chain_logger / rubric / persona
├─ cases/       : YAML 580件
├─ planner/     : case_generator / runner / pairwise_builder
├─ gatekeeper/  : verdict / rubric_eval / summary
├─ fixer/       : fix_proposer / risk_classifier / smoke_test
└─ auto_fix_loop.py
```

---

## 2. テストケース 580件の内訳

| # | カテゴリ | 件数 |
|---|---------|-----|
| 1 | AICA 4ターン心理ヒアリング (6軸×15+emergency+closing) | 100 |
| 2 | AICA 13項目条件ヒアリング | 80 |
| 3 | マッチング (4都県×3エリア×3施設×2働き方+0件+隣接) | 60 |
| 4 | リッチメニュー脱出 (5ボタン×10phase) | 50 |
| 5 | 緊急キーワード (14語×phase文脈) | 60 |
| 6 | 音声入力（Whisper） | 30 |
| 7 | 履歴書生成 | 40 |
| 8 | 応募意思 apply_intent | 30 |
| 9 | ペルソナ別シナリオ (7ペルソナ×10) | 70 |
| 10 | エッジケース | 60 |
| **合計** | | **580** |

---

## 3. 監査ログ (Tamper-Resistant Hash Chain)

### フォーマット
```json
{
  "seq": 1284,
  "ts": "2026-04-29T...",
  "actor": "planner|runner|gatekeeper|fixer|human:yoshiyuki",
  "kind": "case_generated|case_executed|verdict|patch_proposed|patch_applied",
  "case_id": "aica_relationship_001",
  "payload_sha256": "9f2a...",
  "prev_hash": "a3c8...",
  "this_hash": "b7d2...",
  "signer_pubkey_id": "auditor-2026-04",
  "signature": "ed25519:..."
}
```

### Tamper-resistance 三層防御
1. **Hash chain**: `this_hash = SHA-256(prev_hash || canonical(payload))`
2. **Ed25519署名**: 各行を私有鍵で署名
3. **External anchor**: 1日1回、最終 hash を Slack `#claudecode` + git tag

---

## 4. ゲートキーパー判定ルーブリック（8軸）

| 軸 | 評価方法 | 合格閾値 |
|---|---------|---------|
| F. 機能正確性 | expect_phase完全一致 / keywords含有 | **5/5 必須** |
| U. UX | 文字数≤350、絵文字≤3、改行適正 | ≥4 |
| E. 寄り添い | LLM評価（受け止めフレーズ/共感語彙） | ≥4 |
| C. 整合性 | 質問文とQR選択肢が論理一致 | **5/5 必須** |
| L. レイテンシ | webhook<1秒、AI付<5秒 (p95) | < 閾値 |
| S. セキュリティ | PIIマスキング/署名検証/不漏洩 | **5/5 必須** |
| K. コスト | tokens/case < 平均+2σ | 警告のみ |
| H. ハルシネーション | 数字捏造（No.1等）の不存在 | **5/5 必須** |

LLM評価軸（U/E/H）:
- 評価LLMはOpus、計画者はSonnet（モデル分離）
- 同じreplyを3回独立評価 → 中央値採用
- 20%は人間目視抜き取り

---

## 5. 自動修正ループ

```
Round N:
  1) planner: 580ケース実行 → verdicts生成
  2) gatekeeper: 判定 → blocking_reasons集計
  3) fixer (Opus): 上位失敗パターン3件に対し修正案生成
       - 出力: unified diff + 影響範囲メモ + risk level
  4) human-gate:
       - HIGH risk → 社長承認待ち
       - LOW/MED → 自動適用
  5) git commit + wrangler deploy
  6) smoke test (10ケース) → 失敗なら自動rollback
  7) Round N+1 へ

終了条件 (AND):
  - PASS率 ≥ 95% を 3ラウンド連続
  - 新規failパターン 2ラウンド連続0
  - 改善デルタ < 0.5pt が 2ラウンド連続
最大ラウンド: 12（暴走防止）
```

### Risk分類
| Risk | 例 | 適用ポリシー |
|------|---|-------------|
| LOW | コピー文言調整、Quick Reply追加 | 自動適用 |
| MED | phase遷移条件変更 | 24h自動 or 平島さん承認 |
| HIGH | HMAC関連、Slack通知ロジック | **必ず人間承認** |

---

## 6. 6人パネル討論 反映点

| パネリスト | 主要懸念 | 設計反映 |
|-----------|---------|---------|
| QAエンジニア | 580件で網羅か？ | pairwise直交表で論理網羅95%+ランダム探索30件 |
| UXデザイナー | LLM評価が定量基準ブレる | 文字数/絵文字数/改行は機械評価、共感はLLM3回中央値+人間20%抜き取り |
| セキュリティ | テストがPII漏洩源にならないか | テスト用userId `U_TEST_` prefix固定、本番userId絶対不使用 |
| ミサキペルソナ | 「教科書すぎる」 | 実LINE履歴(匿名化)から抽出した語彙テンプレート使用 |
| オペレーション | 580件のAPI料金爆発 | 70%postback不要phase, 30%でAI呼出≈¥3,500/ラウンド試算, 月¥30,000上限guard |
| **ゲートキーパー（鬼）** | 「だいたい合格」を許さない | F/C/S/H軸は **5/5必須**、終了条件に「新規failパターン0」 |

追加ルール:
- **逆張りテスト枠**(30件): ゲートキーパーが毎ラウンド書き換える
- **回帰固定枠**(50件): 一度発見したバグは永久にケース化

---

## 7. 実装ロードマップ

```
Phase A: 設計確定                        [完了]
Phase B: テストインフラ拡張               [予定: 1.5日]
  B1. line_client.py (lib抽出)
  B2. /api/admin/audit-snapshot endpoint
  B3. entry.auditTrail[]
  B4. ケースYAMLパーサ + runner（並列8）
  B5. hash-chain logger + Ed25519
Phase C: 500件テスト生成                 [予定: 1.5日]
  C1. 静的テンプレ 200件
  C2. pairwise組合せ 200件
  C3. LLM変異 180件
  C4. ペルソナ語彙辞書
Phase D: 実行+監査ログ生成               [予定: 1日]
Phase E: ゲートキーパー判定+自動修正     [予定: 2日]
Phase F: 改善ループ実走                  [予定: 1〜2週間 終了条件まで]
```

総工数: **11〜13人日**

---

## 8. リスクと対策

| # | リスク | 対策 |
|---|------|------|
| R1 | AI評価のドリフトで虚偽PASS | self-consistency 3回+人間20%抜き取り+モデル固定 |
| R2 | テストが本番ユーザー体験を壊す | `U_TEST_` prefix、Slack `[TEST]`タグ、cron時間外実行 |
| R3 | API料金暴騰 | `cost_guard.py` 月¥30,000上限、dry-runモード |
| R4 | 監査ログ改ざん | hash-chain+Ed25519+Slack anchor+git tag 4重 |
| R5 | 自動修正でworker.js破壊 | git tag pre-round、smoke test、auto-rollback、HIGH-risk人間承認 |
| R6 | 580件で盲点残存 | 逆張りテスト30件をゲートキーパー毎ラウンド更新 |
| R7 | webhook timeoutで本番影響 | 夜間実行 or 専用エンドポイント分離 |
| R8 | RichMenu画像未作成で偽合格 | テスト事前条件に追加、未作成なら`SKIP` |

---

## 9. 設計の本質（3行）

1. **計画者と鬼を物理分離**せよ。同じLLMでは自己評価バイアスで「だいたい合格」が生まれる
2. **監査ログは未来から見ても改ざんできない**形で残せ。hash-chain + 署名 + 外部anchor
3. **改善が止まるまで自動で回せ**。ただしHIGH-riskは必ず人間承認、暴走防止に最大ラウンド数

---

## 10. 実装優先度

**今すぐ着手（Phase B + 一部 C）**:
1. line_client.py（webhook送信ライブラリ）
2. chain_logger.py（hash-chain + Ed25519）
3. /api/admin/audit-snapshot エンドポイント
4. entry.auditTrail[] 実装
5. 初期100ケース（テンプレベース）

**次セッション以降**:
- 残り480件のケース生成
- ゲートキーパー実装
- 自動修正ループ
- 実走

---

**END OF DESIGN**
