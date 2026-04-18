# /autoresearch — SNS台本プロンプト 自己改善ループを1ラウンド実行

Claude Code セッション内で autoresearch を1ラウンド実行する。
cron の Keychain 問題を回避するため、手動でこのスラッシュコマンドを叩く運用。

## 手順

1. **前置き確認**
   - `docs/strategy-autoresearch.md` を読んで手順・スコアリング基準を把握
   - `logs/autoresearch/latest_state.json` を読んで前回スコア・改善対象項目を確認

2. **Step 1 ベースライン or 前回状態**
   - latest_state.json が存在 → そこから `current_score` `last_change` `item_failure_rates` を引き継ぐ
   - 存在しない → ベースライン計測から開始（10本生成してスコア算出）

3. **Step 2 失敗パターン分析**
   - 最も失敗率の高いチェック項目を特定

4. **Step 3 プロンプト変更**
   - `scripts/ai_content_engine_improved.py` を編集（原本 `ai_content_engine.py` は触らない）
   - 変更内容を `logs/autoresearch/changelog.md` に追記

5. **Step 4 再テスト**
   - 変更後のプロンプトで台本10本を生成（Task ツールで並列可）
   - 各台本を8〜11項目のチェックリストで Yes/No 判定

6. **Step 5 判定**
   - スコア上昇 → 採用、`latest_state.json` 更新、`git commit` で変更保存
   - スコア同じ or 下降 → 変更を破棄

7. **Step 6 Slack 通知**
   - `python3 scripts/slack_bridge.py --send "🔬 autoresearch Round N: <対象項目> <before→after>点"`

## 停止条件

- 95%を3回連続達成 → ループ終了、Slackで社長承認依頼
- 3ラウンド連続スコア低下 → ループ停止、要因分析のみSlack報告

## 実行前チェック

- `logs/autoresearch/cron.log` の直近エラー（cron failure）は無視してOK（当スラッシュコマンドは直接Claude Code内で回す）

## 一緒に更新するファイル

- `logs/autoresearch/latest_state.json`
- `logs/autoresearch/changelog.md`
- `scripts/ai_content_engine_improved.py`（改善版保管）

## 注意

- API課金は発生しない（Claude Code CLI のトークンを使う）
- 毎日叩く必要はない。気が向いた時に1ラウンドずつで十分
- 原本 `scripts/ai_content_engine.py` は絶対に上書きしない。95%3連続後に社長承認を得てから昇格
