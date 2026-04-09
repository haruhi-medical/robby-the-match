# 投稿品質系cronジョブ 徹底チェック結果

**実施日**: 2026-04-06
**対象**: pdca_quality_gate.sh / post_preview.py / slack_reply_check.py

---

## 総合判定

| スクリプト | 構文 | 依存 | 動作 | 判定 |
|-----------|------|------|------|------|
| pdca_quality_gate.sh | OK | OK | OK | **正常** |
| post_preview.py | OK | OK | NG | **致命的バグ** |
| slack_reply_check.py | OK | OK | NG | **致命的バグ（連鎖）** |

**フロー全体判定: 機能していない**

---

## 1. pdca_quality_gate.sh（16:00 月-土）

### 構文チェック
- `bash -n` パス: OK
- `set -euo pipefail` 設定済み

### 依存確認
- `utils.sh`: 存在、正常（PROJECT_DIR/init_log/slack_notify/write_heartbeat 全て定義済み）
- `quality_checker.py`: 存在、`--fact-check`/`--appeal-check` 引数対応済み
- `posting_queue.json`: 存在（132件、readyが30件）
- `notify_slack.py`（utils.sh経由）: 存在

### ログ確認
- 最終実行: 2026-04-08 16:00（heartbeat記録あり、exit_code=0）
- エラー/FAIL件数: 0件
- 直近の品質スコア: 7.95〜9.12（全件合格、quality_failed 0件）
- Slack通知: 正常送信

### 問題点
- なし。正常動作中。

---

## 2. post_preview.py（19:00 月-土）

### 構文チェック
- `python3 -m py_compile`: OK

### 依存確認
- `python-dotenv`: OK
- `slack_utils.py`: 存在、`send_message`/`save_preview_ts`/`SLACK_CHANNEL_POST_REVIEW` 全てインポート可能
- `posting_queue.json`: 存在

### cron設定
```
0 19 * * 1-6 cd ~/robby-the-match && /usr/bin/python3 scripts/post_preview.py --platform instagram --slot 21:00
```

### ログ確認（4/1〜4/8 全日分）
```
全日同一: [INFO] Instagram 21:00: キューにデータなし
```
**8日間連続で1件もプレビューが送信されていない。**

### 致命的バグ: プラットフォームフィルタの不一致

`get_next_post("instagram")` の判定ロジック（post_preview.py 45-48行目）:
```python
if "instagram" in content_type or "ig_" in slide_dir:
    return post
```

しかし実際のキューデータ:
```
content_type='career', slide_dir='content/generated/ai_batch_20260331_1500/ai_転職_0331_09'
content_type='aruaru', slide_dir='content/generated/ai_batch_20260402_1500/ai_ある_0402_02'
```

**ready状態の30件全てが `content_type` に "instagram" を含まず、`slide_dir` に "ig_" を含まない。**
結果、`get_next_post("instagram")` は常に空辞書を返す。

一方、実際に21:00に投稿する `ig_post_meta_suite.py` の `get_next_content()` は:
```python
for post in q.get("posts", []):
    if post.get("status") != "ready":
        continue
    # プラットフォームフィルタなし — 最初のreadyを取る
    return post
```

**プレビューと実投稿でフィルタロジックが完全に不一致。**

### 副次的問題
- `preview_messages.json` が存在しない → `save_preview_ts` が一度も呼ばれていない証拠

---

## 3. slack_reply_check.py（19:30, 20:00, 20:30 月-土）

### 構文チェック
- `python3 -m py_compile`: OK

### 依存確認
- `slack_utils.py`: OK（`get_thread_replies`/`get_preview_ts` インポート可能）
- `posting_queue.json`: OK

### ログ確認（4/1〜4/8 全日分）
```
全3回×全日: [INFO] instagram 21:00: プレビューメッセージなし（スキップ）
```

### 致命的バグ（連鎖）
`post_preview.py` がプレビューを送信できないため:
1. `preview_messages.json` にts/channel情報が保存されない
2. `get_preview_ts("instagram", "21:00")` は常に空辞書を返す
3. `slack_reply_check.py` は毎回スキップ

さらに `find_post_in_queue("instagram")` も `post_preview.py` と同一のフィルタロジックを持つため、仮にプレビューtsが存在しても、キューから投稿を見つけられない。

### 承認フローの不在
- Slackスレッド返信による修正/承認機能は**一度も使われたことがない**
- `apply_modification()` / `update_queue()` は実質デッドコード

---

## フロー全体の断絶

### 設計上の想定フロー
```
16:00 品質ゲート → ready化
19:00 プレビュー送信 → Slackでレビュー依頼
19:30-20:30 返信チェック（3回）→ 修正反映 or 承認
21:00 Instagram投稿（cron_ig_post.sh → ig_post_meta_suite.py）
```

### 実際の動作
```
16:00 品質ゲート → 正常動作（readyにマーク）
19:00 プレビュー → "キューにデータなし"（フィルタ不一致で常に空振り）
19:30-20:30 返信チェック → "プレビューメッセージなし"（プレビュー未送信の連鎖）
21:00 Instagram投稿 → readyの先頭を無条件に投稿（レビューなし）
```

**品質ゲートは通っているが、人間レビュー（プレビュー→承認）のステップが完全にバイパスされている。**

---

## 修正方針

### 最優先（致命的）
`post_preview.py` と `slack_reply_check.py` のプラットフォームフィルタを `ig_post_meta_suite.py` と統一する。
具体的には `get_next_post()` / `find_post_in_queue()` で instagram 判定時のフィルタを外すか、キューエントリに `platform` フィールドを追加する。

最もシンプルな修正案:
```python
# post_preview.py / slack_reply_check.py
# Instagram用: content_type/slide_dirでのフィルタを廃止し、
# ig_post_meta_suite.pyと同様に最初のreadyを返す
if platform == "instagram":
    if status in ("ready", "pending"):
        return post  # プラットフォーム区別なし（現状全てInstagram用）
```

### 低優先（改善）
- urllib3 NotOpenSSLWarning を抑制（ログの可読性向上）
- `preview_messages.json` のクリーンアップロジック（月単位の比較が不正確 — 日付単位に変更推奨）

---

## 環境情報

- Python: system python3（/usr/bin/python3）
- urllib3: v2（LibreSSL 2.8.3でNotOpenSSLWarning発生 — 動作には影響なし）
- cron: 全5エントリ正常登録済み（月-土）
- 日曜スキップ: 正常（4/5のログなし）
