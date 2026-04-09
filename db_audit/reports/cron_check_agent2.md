# cronジョブ SNS投稿系4本 徹底チェック結果

**実施日**: 2026-04-06
**対象**: pdca_sns_post.sh / cron_ig_post.sh / cron_tiktok_post.sh / cron_carousel_render.sh

---

## 1. bash -n 構文チェック

| スクリプト | 結果 |
|-----------|------|
| pdca_sns_post.sh | OK |
| cron_ig_post.sh | OK |
| cron_tiktok_post.sh | OK |
| cron_carousel_render.sh | OK |

全4本、構文エラーなし。

---

## 2. crontab登録状況

```
0 12,17,18,20,21 * * 1-6  pdca_sns_post.sh
0 21 * * 1-6               cron_ig_post.sh
30 2 * * 1-6               cron_tiktok_post.sh
30 7 * * 1-6               cron_carousel_render.sh
```

全4本がcrontabに登録済み。

---

## 3. 依存スクリプト確認

| 依存先 | 存在 | 使用元 |
|--------|------|--------|
| scripts/utils.sh | OK | pdca_sns_post.sh, cron_tiktok_post.sh |
| scripts/auto_post.py | OK | pdca_sns_post.sh |
| scripts/sns_workflow.py | OK | pdca_sns_post.sh |
| scripts/ai_content_engine.py | OK | pdca_sns_post.sh |
| scripts/ig_post_meta_suite.py | OK | cron_ig_post.sh |
| scripts/start_chrome_debug.sh | OK | cron_ig_post.sh |
| scripts/slack_bridge.py | OK | cron_ig_post.sh, cron_carousel_render.sh |
| scripts/tiktok_post.py | OK | cron_tiktok_post.sh |
| scripts/tiktok_carousel.py | - | cron_tiktok_post.sh (フォールバック、UPLOADPOST_API_KEY未設定で不使用) |
| scripts/generate_carousel_html.py | OK | cron_carousel_render.sh |
| data/posting_schedule.json | OK | pdca_sns_post.sh |
| data/posting_queue.json | OK | cron_carousel_render.sh |

全必須依存ファイルが存在。

---

## 4. 21:00 二重投稿問題 (最重要)

### 問題の構造

**水曜日21:00に、2つのスクリプトが同時にInstagram投稿を試みる。**

| 時刻 | pdca_sns_post.sh | cron_ig_post.sh |
|------|-----------------|-----------------|
| 月 17:30 | 投稿 (auto_post.py/instagrapi) | 起動→投稿 (ig_post_meta_suite.py/MBS) |
| 火 12:00 | 投稿 | 起動→投稿 |
| **水 21:00** | **投稿** | **投稿** |
| 木 17:30 | 投稿 | 起動→投稿 |
| 金 18:00 | 投稿 | 起動→投稿 |
| 土 20:00 | 投稿 | 起動→投稿 |

- `pdca_sns_post.sh`: posting_schedule.jsonを参照。水曜は`21:00`設定。CURRENT_HOUR==SCHEDULED_HOURで通過。`auto_post.py --instagram`(instagrapi)で投稿。
- `cron_ig_post.sh`: **毎日21:00に無条件実行**。posting_schedule.jsonを一切参照しない。`ig_post_meta_suite.py`(Meta Business Suite)で投稿。

### 実際の影響

- 方式が異なる（instagrapi vs MBS）ため、同じコンテンツを2回投稿するリスクは低い
- ただし**両方ともcontent/ready/からコンテンツを取得**する場合、同日2件消費の可能性あり
- 現状、pdca_sns_post.sh側は**login_required**で連日失敗中（後述）なので、実害は発生していない
- cron_ig_post.sh側は`[MBS] No ready content to post`で投稿なし（readyコンテンツの判定ロジックが異なる可能性）

### 推奨対応

1. **cron_ig_post.shにもposting_schedule.json参照を追加** — 曜日チェックして21:00以外の日はexit
2. **または**: pdca_sns_post.shの21:00枠を削除（cron_ig_post.shに一本化）
3. **最善策**: どちらか1本に統一。現状auto_post.py(instagrapi)が死んでいるので、cron_ig_post.sh(MBS)に一本化が合理的

---

## 5. 各スクリプトのエラー状況

### 5-1. pdca_sns_post.sh — Instagram投稿が連日失敗

**直近4日連続で`login_required`エラー。投稿ゼロ。**

```
[IG] Chrome cookie sync failed: Unable to get key for cookie decryption
[IG] Warm-up: error (non-critical): login_required
[IG] FAILED: login_required
=== Summary: 0 success, 1 failed ===
```

- **原因**: instagrapiのChromeセッションcookie復元が失敗。macOSキーチェーンアクセス権限またはChromeのcookie暗号化方式変更が原因の可能性。
- **影響**: auto_post.py経由のInstagram投稿が完全停止（4/6〜4/9確認分）
- **exit code**: スクリプト自体は`IG=1`で終了するが、`set -euo pipefail`の`IG_EXIT=$?`で捕捉され、スクリプトはcrashしない（正しい設計）
- **対応**: instagrapiセッション再構築 or MBS方式（cron_ig_post.sh）への完全移行

### 5-2. cron_ig_post.sh — 動作するが投稿対象なし

```
[MBS] No ready content to post
```

- Chrome Debug Mode起動: OK
- ランダム遅延: 正常動作（0〜1800秒）
- ig_post_meta_suite.py: 実行成功だが「readyコンテンツなし」で投稿スキップ
- **原因**: posting_queue.json内のreadyコンテンツとig_post_meta_suite.pyの判定ロジックの不一致、またはready状態のコンテンツに画像がない
- **影響**: MBS経由の投稿も実質停止中

### 5-3. cron_tiktok_post.sh — 全方法失敗（既知の問題）

```
[方法1] tiktokautouploader: タイムアウト (180秒)
[方法2b] Playwright直接: 成功を報告 → プロフィール検証FAILED (videoCount変化なし)
[方法3] Slack手動投稿依頼
```

- 動画生成自体は成功（MP4 3.7MB生成）
- アップロードが全方法で失敗（TikTok側のbot検出）
- exit code=0で終了（tiktok_post.pyがSlack通知後に正常終了扱い）
- **これはMEMORY.mdに既知の問題として記録済み**

### 5-4. cron_carousel_render.sh — generate_carousel_html.pyでクラッシュ

**23件のreadyコンテンツで画像生成が全失敗。**

```
AttributeError: 'str' object has no attribute 'get'
  File "generate_carousel_html.py", line 220, in generate_carousel
    slide_type = slide.get("type", "content")
```

- **原因**: JSONファイル内の`slides`が文字列のリスト（`["テキスト1", "テキスト2", ...]`）だが、generate_carousel_html.pyはdictのリスト（`[{"type": "content", "text": "..."}]`）を期待
- ai_content_engine.pyが生成するJSONフォーマットとgenerate_carousel_html.pyの期待するフォーマットが不一致
- **影響**: 新規カルーセル画像が生成されない → cron_ig_post.shの「No ready content」の根本原因はこれ
- **対応**: generate_carousel_html.pyにstr型slidesのフォールバック処理を追加

---

## 6. 問題の連鎖構造

```
ai_content_engine.py が slides を文字列リストで生成
  ↓
cron_carousel_render.sh (07:30) → generate_carousel_html.py が AttributeError で全失敗
  ↓
画像(PNG)が生成されない
  ↓
cron_ig_post.sh (21:00) → "No ready content to post"
  ↓
pdca_sns_post.sh (各時間) → instagrapi login_required で別の理由でも失敗
  ↓
Instagram投稿が完全停止
```

---

## 7. サマリと優先対応

| 優先度 | 問題 | 対応 |
|--------|------|------|
| P0 | generate_carousel_html.py: str型slides未対応 | slides要素がstrの場合の変換処理を追加 |
| P0 | auto_post.py: instagrapi login_required 連日失敗 | セッション再構築 or MBS一本化 |
| P1 | 21:00二重投稿リスク（水曜日） | cron_ig_post.shにスケジュール参照追加、または統一 |
| P2 | TikTok全方法失敗 | 既知。手動投稿 or 新APIキー取得待ち |
| P3 | cron_ig_post.sh: readyコンテンツ判定ロジック | P0修正後に自動解消の可能性あり |

---

## 8. 補足: ランダム遅延の重複リスク

- pdca_sns_post.sh: 0〜25分（posting_schedule.jsonのrandom_offset_minutes=25）
- cron_ig_post.sh: 0〜30分（RANDOM % 1800秒）
- cron_tiktok_post.sh: 0〜15分（RANDOM % 900秒）

水曜21:00に両方起動した場合、遅延後の実際の投稿時刻が重なる確率は低いが、ゼロではない。
