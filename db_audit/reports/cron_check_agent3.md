# Cronジョブ点検レポート (Agent 3)
> 対象: pdca_ai_marketing.sh / pdca_content.sh / autoresearch
> 実施日: 2026-04-09

---

## 1. pdca_ai_marketing.sh (06:00 月-土)

### 構文チェック
- `bash -n`: **PASS** (構文エラーなし)

### 依存ファイル
| ファイル | 存在 |
|---------|------|
| scripts/utils.sh | OK |
| scripts/ai_content_engine.py | OK |
| scripts/sns_workflow.py | OK |
| scripts/slack_bridge.py | OK |
| data/posting_queue.json | OK |

### 直近4日間のログ (04/06-09)
- 全日正常終了 (`completed successfully`)
- Slack送信: 全日成功

### 問題点

#### CRITICAL: 全readyコンテンツのスライド画像が0枚
- 04/09ログ: `slides_missing: 23` (ready 23件すべてスライドなし)
- posting_queue.json確認: **ready 30件中、スライド画像を持つ投稿が0件**
- 原因: `cron_carousel_render.sh` (07:30) で `generate_carousel_html.py` がクラッシュ
- エラー: `AttributeError: 'str' object has no attribute 'get'` (line 220)
- ai_content_engine.py が生成するJSONの `slides` が文字列配列 (`["テキスト1", "テキスト2"]`) になっており、`generate_carousel_html.py` が期待する辞書形式 (`[{"type": "content", "text": "..."}]`) と不一致
- **結果: コンテンツは生成されるが画像なしで投稿不能。パイプラインが事実上破綻**

#### WARNING: failedカウントが増加傾向
- 04/06: 21 → 04/07: 24 → 04/08: 25 → 04/09: 27
- failed投稿が蓄積し続けている（リトライやクリーンアップの仕組みなし）

#### MINOR: urllib3 SSL警告
- `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+` (LibreSSL 2.8.3)
- 動作には影響なし

---

## 2. pdca_content.sh (15:00 月-土)

### 構文チェック
- `bash -n`: **PASS** (構文エラーなし)

### 依存ファイル
- ai_content_engine.py: OK
- utils.sh: OK

### 直近4日間のログ (04/06-09)
- 全日 exit=0 で完了
- コンテンツ生成自体は成功（7本/日を安定生成）

### 問題点

#### WARNING: Claude CLI品質レビューが毎回失敗しフォールバック
- 全レビューで `Claude CLI exit code 1 (attempt 1)` → `(attempt 2)` → `FALLBACK to Cloudflare Workers AI`
- 原因: cron環境でClaude CLIの認証が通らない（`Not logged in`と同根）
- フォールバックのCloudflare Workers AIレビューは動作中、スコア7-8/10で全PASSしている
- **影響: 品質レビューの精度が低下している可能性（Workers AIはClaudeより判定が甘い傾向）**

#### WARNING: content_pipeline.py --status を依然として呼んでいる (L49)
```bash
QUEUE_STATUS=$(python3 "$PROJECT_DIR/scripts/content_pipeline.py" --status 2>/dev/null | tail -5)
```
- `2>/dev/null` で握りつぶしているため致命的ではないが、廃止済みと明記しながら残存
- `$QUEUE_STATUS` が空になり、進捗記録が不完全

#### CRITICAL (共通): スライド0枚のままスケジュール登録
- 04/09ログ: 7件をスケジュール登録、すべて `(0 slides)`
- カルーセル画像レンダリングの上流バグ（ai_content_engine.pyのJSON形式問題）が解消されない限り、生成→投稿の全パイプラインが機能しない

---

## 3. autoresearch (02:00 毎日)

### crontabエントリ
```
0 2 * * * cd ~/robby-the-match && /opt/homebrew/bin/claude --dangerously-skip-permissions \
  -p "docs/strategy-autoresearch.md に従い autoresearchを1ラウンド実行せよ" \
  --max-turns 30 >> logs/autoresearch/cron.log 2>&1
```

### ログ確認
- **CRITICAL: 100%失敗。1度も成功していない**
- ログ内容 (全21行、2パターンのみ):
  - `env: node: No such file or directory` (4回)
  - `Not logged in · Please run /login` (17回)

### 原因分析

1. **`env: node: No such file or directory`**: cron環境でPATHが通っていない時期のエラー。現在のcrontabにはPATH設定あり (`/opt/homebrew/bin` 含む) なので、これは古いログの残骸
2. **`Not logged in · Please run /login`**: Claude CLI認証がcron環境で有効でない。`claude` コマンドは対話的ログインが必要で、cronのヘッドレス環境ではセッションを維持できない

### claude CLI状態
- `/opt/homebrew/bin/claude` 存在確認: OK (v2.1.97)
- 対話的シェルでは認証済みだが、cronでは認証コンテキストが引き継がれない

### 影響
- `logs/autoresearch/latest_state.json` は 2026-03-18 のまま更新なし
- autoresearchによるプロンプト改善が3週間以上停止中
- 現在のスコア: baseline 0.56 のまま（改善ゼロ）

---

## 総合評価

| ジョブ | 実行 | 致命度 | 状態 |
|-------|------|--------|------|
| pdca_ai_marketing.sh | 毎日成功 | 中 | スライド0枚警告を毎日報告するだけで解決しない |
| pdca_content.sh | 毎日成功 | 高 | コンテンツ生成OK、しかしスライド0枚で投稿不能 |
| autoresearch | 毎日失敗 | 高 | Claude CLI認証問題で3週間完全停止 |

## 要対応事項 (優先順)

### P0: カルーセル画像レンダリング破綻
- **ファイル**: `scripts/generate_carousel_html.py` L220 + `scripts/ai_content_engine.py`
- ai_content_engine.pyが生成するJSONのslides形式（文字列配列）と、generate_carousel_html.pyが期待する形式（辞書配列）を統一する
- ready 30件が全滅しており、Instagram投稿パイプライン全体が機能停止中

### P1: autoresearch Claude CLI認証
- cronでClaude CLIを使う方法を確立するか、autoresearchをAPI経由（OpenAI/Cloudflare Workers AI）に書き換える
- 代替案: Claude Desktop Coworkのスケジュール機能で実行する

### P2: pdca_content.sh の content_pipeline.py --status 残存
- L49を `ai_content_engine.py --status` または直接キュー読み取りに差し替え

### P3: failed投稿の蓄積 (21→27、増加中)
- failed投稿のクリーンアップまたはリトライ機構を追加
