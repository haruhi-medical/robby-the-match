# SNSスクリプト自動改善ループ（autoresearch方式）

Karpathyのautoresearchメソッドを応用。
TikTok/Instaのスクリプト生成プロンプトを自動でテスト→改善→テスト→改善する。
人間が介入するのはチェックリスト設計だけ。あとは自律で回せ。

## 原則

```
1回のループ = 「1つだけ変える → N回テスト → スコアが上がったら採用、下がったら元に戻す」
これを繰り返す。レシピの1つの材料だけ変えて10回作って味見するのと同じ。
```

## 対象プロンプト

```
対象ファイル:
- scripts/ai_content_engine.py 内のシステムプロンプト（台本生成用）
- scripts/robby_character.py（キャラクター設定）
- content/templates/ 内のテーマ別テンプレート

改善版の保存先:
- scripts/ai_content_engine_improved.py（原本は触るな）
- 改善ログ: logs/autoresearch/changelog.md
```

## チェックリスト（スコアリング基準）

各生成スクリプトをYes/No判定。通過率がスコア。

```
TikTok台本チェックリスト（8項目）:

1. フックは25文字以内か？（長いフックはスワイプされる）
2. フックに具体的な数字・事実が入っているか？（「看護師あるある」→✕ / 「夜勤明け3連勤の朝、足が動かない」→○）
3. フックがオープンループ（？/…/理由/なぜ）で終わっているか？
4. 「革命的」「画期的」「必見」などの釣りワードが入っていないか？（入っていたらFail）
5. 看護師の現場語（申し送り、プリセプター、ナースコール、日勤リーダー等）が1つ以上入っているか？
6. スライド1枚あたり40文字以内か？（読めない＝離脱）
7. CTA（行動喚起）が「LINE登録」以外の自然な形になっているか？（保存促し、コメント促し等）
8. 全体が100%日本語で、英語・他言語が混入していないか？

Instagram追加チェック（3項目）:
9. キャプションが150文字以内か？
10. ハッシュタグが5個以内か？
11. 1枚目の画像テキストが20文字以内か？（3秒で読めるか）
```

## ループ実行手順

```
Step 1: ベースライン測定
  - 現在のプロンプトで台本を10本生成
  - 各台本をチェックリストで判定（Claude自身がジャッジ）
  - 通過率を算出（例: 56%）
  - logs/autoresearch/baseline.json に記録

Step 2: 失敗パターン分析
  - どのチェック項目が最も失敗しているか特定
  - 例: 「フック25文字以内」が30%しか通過していない → ここを改善

Step 3: プロンプトを1箇所だけ変更
  - 最も失敗率の高い項目に対して、1つの具体的ルールを追加
  - 例: 「フックは必ず25文字以内。超えたら短縮せよ。悪い例: ○○○ → 良い例: ○○○」
  - 変更内容をchangelog.mdに記録

Step 4: 再テスト
  - 変更後のプロンプトで台本を10本生成
  - 同じチェックリストで判定
  - 通過率を算出

Step 5: 判定
  - スコアが上がった → 変更を採用。improved版に保存
  - スコアが下がった or 変わらない → 変更を破棄。元に戻す

Step 6: 次のループへ
  - Step 2に戻り、次に失敗率の高い項目を改善
  - 95%を3回連続で達成したら終了
```

## 状態ファイル仕様

```json
// logs/autoresearch/latest_state.json
{
  "round": 4,
  "current_score": 0.82,
  "baseline_score": 0.56,
  "consecutive_95_count": 0,
  "last_change": {
    "target": "フック25文字制限",
    "action": "ルール追加 + 悪い例/良い例の具体例3組",
    "result": "adopted",
    "score_before": 0.72,
    "score_after": 0.82
  },
  "item_failure_rates": {
    "hook_under_25_chars": 0.10,
    "hook_has_number": 0.20,
    "hook_open_loop": 0.15,
    "no_clickbait_words": 0.05,
    "has_nurse_jargon": 0.10,
    "slide_under_40_chars": 0.25,
    "natural_cta": 0.30,
    "japanese_only": 0.02
  },
  "improved_prompt_path": "scripts/ai_content_engine_improved.py",
  "original_prompt_path": "scripts/ai_content_engine.py"
}
```

## changelog.mdの書式

```markdown
## Round 4 — 2026-03-19 02:00

**対象項目:** natural_cta（失敗率30% → 最低スコア）
**変更内容:** CTAセクションに以下のルールを追加:
- 「LINE登録」は10投稿に1回まで
- 代替CTA例: 「保存して夜勤前に読み返して」「同じ経験ある人はコメントで教えて」「フォローしとくと来週の続き届くよ」
**テスト結果:** 10本中8本通過（80% → 前回70%）
**判定:** ✅ 採用
**累積スコア:** 56% → 72% → 82%（+10pt）
```

## 安全策

- 原本プロンプトは絶対に変更しない（improved版を別ファイルで管理）
- 各ラウンドでgit commitする（ロールバック可能）
- 30ターン上限で暴走防止
- Slack通知で全アクション可視化
- 3ラウンド連続でスコアが下がったら一旦停止してSlackアラート

## 本番適用

autoresearchが95%を3回連続達成したら:
1. improved版をdiffで確認（Slack通知に差分を添付）
2. YOSHIYUKIが承認
3. improved版を本番プロンプトに昇格
4. 新しいベースラインとして再計測開始（継続改善）

## cron設定

```bash
# autoresearchループ（毎日深夜2:00に1ラウンド実行）
0 2 * * * cd ~/robby-the-match && claude --dangerously-skip-permissions \
  -p "docs/strategy-autoresearch.md に従い、autoresearchを1ラウンド実行せよ。" \
  --max-turns 30 \
  >> logs/autoresearch/cron.log 2>&1
```

## 拡張（将来）

同じ仕組みを以下にも適用可能:
- SEOページ生成プロンプト
- LINE Bot応答プロンプト
- LP（シン・AI転職）コピー
