# Harness設計 — Planner→Generator→Evaluator ループ

> Anthropic harnessパターンに準拠したSNSコンテンツ自動化の再設計案

## 現状の問題

```
現状（2026-03-29）:
  Planner(06:00) → Generator(06:00+07:30) → [Gap] → Quality Gate(16:00) → Post(21:00) → [Gap]
                                                 ↑                                          ↑
                                          9時間の空白                              翌日のReviewまで放置
```

**致命的な欠損:**
1. Generator出力の即時検証がない（07:30画像生成→16:00品質ゲートまで9時間放置）
2. 投稿後のフィードバックが翌日のPlannerに反映されない
3. Evaluatorが「スコアリング」するだけで「リジェクト→再生成」のループがない

## 目標アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│                  HARNESS (orchestrator)           │
│                                                   │
│  ┌──────────┐    ┌───────────┐    ┌───────────┐  │
│  │ PLANNER  │───→│ GENERATOR │───→│ EVALUATOR │  │
│  │ 何を作る  │    │ 作る      │    │ 良いか判定 │  │
│  └──────────┘    └───────────┘    └─────┬─────┘  │
│       ↑                                  │        │
│       │            ┌─────────┐           │        │
│       └────────────│ FEEDBACK │←──────────┘        │
│                    │ 次回改善  │     Pass/Fail      │
│                    └─────────┘                     │
└─────────────────────────────────────────────────┘
```

## パッチ案

### Phase 1: 即時Evaluator追加（工数: 2時間）

**変更: cron_carousel_render.sh の末尾に品質チェックを追加**

```bash
# 現状: Playwright画像生成 → 終了
# 改善: Playwright画像生成 → quality_checker.py → Fail時はステータスをrejectedに

# cron_carousel_render.sh の末尾に追加:
for slide_dir in $(find "$OUTPUT_DIR" -mindepth 1 -maxdepth 1 -type d -newer "$LOCK"); do
  score=$(python3 scripts/quality_checker.py --dir "$slide_dir" --json 2>/dev/null | jq -r '.score // 0')
  if [ "$score" -lt 60 ]; then
    # ステータスをrejectedに変更 → 投稿されない
    python3 -c "
import json, sys
q = json.load(open('data/posting_queue.json'))
for item in q:
    if item.get('slide_dir') == '$slide_dir':
        item['status'] = 'rejected'
        item['reject_reason'] = 'quality_score=$score'
json.dump(q, open('data/posting_queue.json', 'w'), ensure_ascii=False, indent=2)
"
    slack_send "⚠️ 品質ゲート不合格: $slide_dir (score=$score) → rejected"
  fi
done
```

### Phase 2: 投稿後Evaluator追加（工数: 3時間）

**新規cron: 22:00に投稿確認**

```bash
# cron_ig_post_verify.sh
# 22:00実行（投稿21:00の1時間後）
# 1. posting_queue.jsonから今日posted分を取得
# 2. Meta Graph APIでinstagram_idの存在確認
# 3. 投稿が存在しない → Slack緊急通知
# 4. 投稿が存在する → engagement初期値を記録
```

### Phase 3: Feedback Loop実装（工数: 4時間）

**pdca_ai_marketing.sh のPlanner部分に前日のフィードバックを注入**

```python
# content_pipeline.py の plan_content() に追加:
def plan_content():
    # 1. 前日の投稿結果を取得
    yesterday = get_yesterday_post_results()  # GA4/Instagram Insights

    # 2. 良かった投稿の特徴を抽出
    #    - CTR, 保存率, リーチ数
    #    - カテゴリ、フック文字数、トーン

    # 3. 今日の生成プロンプトに反映
    #    - 高パフォーマンスカテゴリの比率を上げる
    #    - 低パフォーマンスのフックパターンを避ける

    # 4. autoresearch の最新スコアも参照
    latest_autoresearch = load_autoresearch_state()
```

### Phase 4: Harness統合（工数: 8時間）

**全cronを1つのオーケストレーターに統合**

```python
# scripts/harness.py — 全自動PDCA統合オーケストレーター
class ContentHarness:
    def run_daily(self):
        # === PLAN ===
        plan = self.planner.plan(
            queue_state=self.get_queue_state(),
            feedback=self.get_yesterday_feedback(),
            autoresearch=self.get_autoresearch_state(),
        )

        # === GENERATE ===
        for content in plan.contents:
            result = self.generator.generate(content)

            # === EVALUATE (即時) ===
            score = self.evaluator.check_quality(result)
            if score < 60:
                # 再生成（最大2回）
                result = self.generator.regenerate(content, feedback=score.issues)
                score = self.evaluator.check_quality(result)

            if score >= 60:
                self.queue.add(result, status="ready")
            else:
                self.queue.add(result, status="rejected")
                self.slack.notify(f"⚠️ 2回生成しても品質不合格: {content.id}")

        # === POST ===
        # posting_schedule.jsonに従い時間になったら投稿

        # === POST-EVALUATE ===
        # 翌日のrun_daily()で前日のフィードバックとして使用
```

## 即時アクション（Phase 1のみ）

### 1. instagram_engage.py のcron削除
```bash
# 削除対象行:
0 12 * * 1-6 sleep $((RANDOM \% 3600)) && cd ~/robby-the-match && /usr/bin/python3 scripts/instagram_engage.py ...
```

### 2. pdca_content.sh のcron削除（ai_marketing.shと重複）
```bash
# 削除対象行:
0 15 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_content.sh
```

### 3. cron_carousel_render.sh に品質ゲート追加
上記Phase 1のパッチを適用。

## 判断を仰ぐ項目

- [ ] Phase 1（即時Evaluator）を今すぐ実装するか？
- [ ] autoresearch(02:00)の実行頻度を減らすか？
- [ ] Phase 4（harness統合）は今やるべきか、それとも後回しか？
- [ ] pdca_content.sh削除の承認

## 参考: Anthropic Harness設計原則

1. **Planner-Generator-Evaluator は1ループで閉じる** — 生成直後に検証し、不合格なら即再生成
2. **Evaluatorは具体的フィードバックを返す** — 「不合格」だけでなく「なぜ不合格か」をGeneratorに渡す
3. **フィードバックは蓄積する** — 過去の成功/失敗パターンをPlannerが学習する
4. **人間の介入ポイントを明確にする** — 自動化できる判断と人間が必要な判断を分ける
