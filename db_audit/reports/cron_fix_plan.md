# Cronジョブ修復計画

> 作成: 2026-04-06 / 対象: 停止中6件のcronジョブ

## 概要

| # | ジョブ | 優先度 | 根本原因 | 修復方針 | 工数 |
|---|--------|--------|---------|---------|------|
| 1 | cron_carousel_render.sh | P1 | str→dict変換エラー（修正済み） | 動作確認のみ | 10分 |
| 2 | pdca_sns_post.sh (Instagram) | P0 | instagrapi認証切れ | MBS方式に一本化 | 2時間 |
| 3 | instagram_engage.py | P1 | instagrapi認証切れ | MBS方式 or 一時停止 | 1時間 |
| 4 | autoresearch (Claude CLI) | P1 | cron環境でOAuth不通 + ANTHROPIC_API_KEY未設定 | APIキー設定 | 15分 |
| 5 | pdca_weekly_content.sh | P1 | 同上（Claude CLI依存） | APIキー設定（#4と同時解決） | 0分 |
| 6 | cron_tiktok_post.sh | P2 | TikTok自動化手段が全滅 | Computer Use方式 or 手動運用 | 要検討 |

---

## Job #1: cron_carousel_render.sh（カルーセル画像レンダリング）

### 根本原因
`generate_carousel_html.py` 内で文字列をdict型として扱おうとするエラー（既に修正済みとの報告）。

### 修復作業
- **動作確認テスト**: 手動実行して正常終了を確認
  ```bash
  /bin/bash ~/robby-the-match/scripts/cron_carousel_render.sh
  ```
- `data/posting_queue.json` 内の `status: ready` かつ画像未生成のエントリで実際にPNGが生成されるか確認
- ログ確認: `logs/carousel_render_$(date +%Y-%m-%d).log`

### 担当Agent
単独実行。エージェント不要。

### テスト方法
1. `posting_queue.json` にreadyエントリが存在する状態でスクリプト実行
2. 出力ディレクトリに `slide_*.png` が生成されることを確認
3. 画像サイズが1080x1350であることを確認

### 完了条件
- 手動実行で exit 0
- Slack通知「全readyコンテンツの画像が準備済み」が送信される

---

## Job #2: pdca_sns_post.sh（Instagram投稿）— **最優先**

### 根本原因
`auto_post.py` が `instagrapi` ライブラリでInstagramにログインしようとしているが、Instagramがセッションを失効させ `login_required` エラーが発生。

現在の認証フロー:
1. Chrome cookie同期 → `browser_cookie3` で `.instagram.com` のcookieを取得
2. `instagrapi` の `load_settings()` でセッション復元
3. フォールバック: パスワードログイン（INSTAGRAM_PASSWORDは.envに設定済み）

**全段階が失敗している**。Instagramはinstagrapiによる非公式APIアクセスを積極的にブロックしている。

### 修復方針: Meta Business Suite (MBS) CDP方式に完全移行

現在 `ig_post_meta_suite.py` が存在するが、crontabでは `DISABLED` になっている。このMBS方式をメインに昇格する。

#### 作業手順

**Step 1: MBS方式の動作確認**（担当: メインエージェント）
```bash
# Chrome Debug Mode起動確認
curl -s http://localhost:9223/json | head -5

# MBSセッション有効性確認
python3 scripts/ig_post_meta_suite.py --dry-run
```

**Step 2: pdca_sns_post.sh の修正**
- `auto_post.py --instagram` の呼び出しを `ig_post_meta_suite.py` に差し替え
- フォールバック順序:
  1. **Primary**: `ig_post_meta_suite.py`（Chrome CDP経由MBS）
  2. **Fallback**: `auto_post.py --instagram`（instagrapiセッション復旧時のみ）

修正箇所（`pdca_sns_post.sh` L92-101）:
```bash
# Step 2: Instagram自動投稿（Meta Business Suite優先）
echo "[INFO] Instagram投稿 (MBS経由)..." >> "$LOG"
python3 "$PROJECT_DIR/scripts/ig_post_meta_suite.py" >> "$LOG" 2>&1
IG_EXIT=$?

if [ $IG_EXIT -ne 0 ]; then
    echo "[WARN] MBS失敗。instagrapiフォールバック..." >> "$LOG"
    python3 "$PROJECT_DIR/scripts/auto_post.py" --instagram >> "$LOG" 2>&1
    IG_EXIT=$?
fi
```

**Step 3: crontab修正**
- 現在の `0 12,17,18,20,21 * * 1-6 pdca_sns_post.sh` はそのまま維持
- `DISABLED` の `0 21 * * 1-6 cron_ig_post.sh` は削除（pdca_sns_post.shに統合）
- Chrome Debug Modeの自動起動をLaunchAgentに追加（未設定の場合）

**Step 4: MBSセッション維持**
- MBSセッション切れ時のSlack通知は既に `ig_post_meta_suite.py` に実装済み
- 手動再ログインが必要な場合はSlack経由で社長に通知

### 担当Agent
- **修正実装**: メインエージェント（pdca_sns_post.sh修正 + crontab更新）
- **テスト**: メインエージェント（--dry-run実行）

### テスト方法
1. `ig_post_meta_suite.py --dry-run` で投稿フロー全体がエラーなく通ること
2. Chrome Debug Modeが起動していること（`curl localhost:9223/json`）
3. MBSにログイン済みであること（セッション切れ検知が動くこと）
4. 実投稿テスト: readyコンテンツ1件で実際に投稿されることを確認

### 完了条件
- `pdca_sns_post.sh` 手動実行で Instagram投稿が成功
- Slack通知「Instagram投稿完了（Meta Business Suite経由）」が送信される

### リスク
- MBSのUI変更でCDP操作が壊れる可能性 → セレクタ更新が必要
- MBSセッションは手動ログインが定期的に必要（2FA含む）
- **将来的にはMeta Graph API（Instagram Publishing API）への移行が理想**
  - 条件: Facebookページ+Instagramビジネスアカウント連携 + `instagram_content_publish` 権限
  - META_ACCESS_TOKENは既に.envに存在するため、権限追加で対応可能

---

## Job #3: instagram_engage.py（エンゲージメント）

### 根本原因
`instagrapi` の `cl.login()` が `login_required` で失敗。Job #2と同じ認証問題。

### 修復方針: 2段階

**Phase A（即時）: 一時停止**
- エンゲージメント機能はInstagram BAN リスクが最も高い操作
- instagrapiが使えない現状で無理に自動化する価値は低い
- crontabのエンゲージメントジョブをコメントアウト

```bash
# DISABLED: instagrapi認証切れ
# 0 12 * * 1-6 sleep $((RANDOM % 3600)) && cd ~/robby-the-match && /usr/bin/python3 scripts/instagram_engage.py --daily
```

**Phase B（中期）: Chrome DevTools MCP方式でリビルド**
- Chrome経由で実際のInstagramブラウザセッションを使い、いいね操作を実行
- `ig_post_meta_suite.py` と同様のCDP方式
- ただしBAN リスクを考慮し、1日5-10アクションに制限

### 担当Agent
- Phase A: メインエージェント（crontab 1行コメントアウト）
- Phase B: 専用エージェント（新規 `instagram_engage_cdp.py` 開発）— **後回し可**

### テスト方法（Phase B完了後）
1. `--dry-run` でブラウザ操作フローを確認
2. 実行後にInstagramアカウントがブロックされていないことを確認

### 完了条件
- Phase A: crontabコメントアウト完了
- Phase B: CDP方式で1日5いいねが安定動作

---

## Job #4: autoresearch（Claude CLI cron実行）

### 根本原因
cronから `claude` CLI を実行する際、OAuth認証がインタラクティブログインを要求するため失敗。

ログの証拠:
```
env: node: No such file or directory    ← PATHにnodeがない
Not logged in · Please run /login       ← OAuth切れ
```

`utils.sh` の `ensure_env()` は `ANTHROPIC_API_KEY` 設定時にフォールバックするロジックがあるが、
**.envにANTHROPIC_API_KEYが設定されていない**。

### 修復方針

**Step 1: ANTHROPIC_API_KEYを.envに設定**
```bash
# .envに追加（社長にAPIキーを確認）
echo "ANTHROPIC_API_KEY=sk-ant-xxxxx" >> ~/robby-the-match/.env
```

**Step 2: crontabのclaude呼び出し修正**
現在:
```
0 2 * * * cd ~/robby-the-match && /opt/homebrew/bin/claude --dangerously-skip-permissions -p "..." --max-turns 30
```

修正案:
```
0 2 * * * cd ~/robby-the-match && source .env && export ANTHROPIC_API_KEY && /opt/homebrew/bin/claude --dangerously-skip-permissions -p "..." --max-turns 30
```

**Step 3: Claude CLIがAPIキーモードで動作するか確認**
```bash
source ~/robby-the-match/.env && export ANTHROPIC_API_KEY && claude -p "Hello" --max-turns 1
```

### 担当Agent
メインエージェント。社長にAPIキー取得を依頼する必要あり。

### テスト方法
1. `.env` に `ANTHROPIC_API_KEY` を設定
2. cron環境をシミュレート: `env -i HOME=$HOME PATH=/opt/homebrew/bin:/usr/bin:/bin bash -c 'source ~/robby-the-match/.env && export ANTHROPIC_API_KEY && claude -p "test" --max-turns 1'`
3. autoresearchの1ラウンドを手動実行して正常完了を確認

### 完了条件
- `logs/autoresearch/cron.log` に正常実行ログが出力される
- Slackに autoresearch ラウンド結果が通知される

### 備考
- `claude` CLIはAPIキーモード（`ANTHROPIC_API_KEY`環境変数）で動作する可能性があるが、
  `--dangerously-skip-permissions` との組み合わせで動作するか要検証
- 代替案: Claude Max プランのOAuth認証を `claude auth login` で手動実行し、
  トークンファイルがcronユーザーからも読めることを確認

---

## Job #5: pdca_weekly_content.sh（週次コンテンツ生成）

### 根本原因
Job #4と同一。`ensure_env()` でClaude CLI認証チェックに失敗し、`EXIT_CONFIG_ERROR(78)` で即終了。

### 修復方針
**Job #4の修復が完了すれば自動的に解決**。

`pdca_weekly_content.sh` は `ensure_env()` を呼び、ANTHROPIC_API_KEYが設定されていればAPIキーモードで続行する。
また、`content_pipeline.py --force N` でClaude CLIを使ってコンテンツ生成する部分も、APIキーがあれば動作する。

### 追加作業
なし（Job #4で解決）。

### テスト方法
1. Job #4修復後、日曜05:00を待つか手動実行:
   ```bash
   /bin/bash ~/robby-the-match/scripts/pdca_weekly_content.sh
   ```
2. `posting_queue.json` に新規エントリが追加されることを確認

---

## Job #6: cron_tiktok_post.sh（TikTok投稿）

### 根本原因
TikTokは自動投稿手段が全て封じられている（既知の問題）:
- `tiktokautouploader`: タイムアウト（300秒で失敗）
- Playwright経由: 偽成功（投稿されたように見えるが実際は投稿されない）
- TikTok API: 公式APIは限定パートナーのみ
- Upload-Post.com: APIキー未取得

### 修復方針: 3段階

**Phase A（即時）: crontab停止 + 手動運用フローを整備**
- crontabのTikTokジョブをコメントアウト（無駄なリソース消費を停止）
- 手動投稿フロー:
  1. `carousel_to_reel.py` でカルーセルPNG→MP4変換
  2. 社長がスマホでTikTokアプリから手動投稿
  3. 動画ファイルをSlackに送信して社長に投稿依頼

**Phase B（中期）: Computer Use方式**
- Claude Desktop + Computer UseでTikTok Studio（Web版）を操作
- `CLAUDE.md` v9.4のScheduled Tasksに既に「18:30毎日 TikTok投稿」が定義されている
- ただしComputer Useの安定性は未検証

**Phase C（長期）: Upload-Post.com API**
- APIキーを取得すれば `tiktok_carousel.py` のフォールバックが動く
- 月額コスト要確認（月3万円制限に注意）

### 担当Agent
- Phase A: メインエージェント（crontab修正 + Slack通知フロー）
- Phase B: Computer Use対応エージェント
- Phase C: 社長判断待ち

### テスト方法
- Phase A: `carousel_to_reel.py` の出力MP4がTikTokアプリで投稿可能か手動確認
- Phase B: Computer UseでTikTok Studioにアクセス→動画アップロード→投稿の一連フローをテスト

### 完了条件
- Phase A: 手動投稿フローが文書化され、社長に共有済み
- Phase B: Computer Useで投稿が実際に公開される

---

## 実行順序とタイムライン

```
Day 1（今日）:
  [10min] Job #1: カルーセルレンダリング動作確認
  [15min] Job #4: ANTHROPIC_API_KEY設定 → Claude CLI cron動作確認
  [15min] Job #3 Phase A: エンゲージメントcron停止
  [15min] Job #6 Phase A: TikTok cron停止 + 手動フロー整備

Day 1-2:
  [2h]    Job #2: pdca_sns_post.sh MBS方式移行 + テスト
  [0min]  Job #5: Job #4完了で自動解決 → テスト

Day 3以降（中期）:
  [4h]    Job #3 Phase B: CDP方式エンゲージメント開発
  [8h]    Job #6 Phase B: Computer Use TikTok投稿テスト
```

## 必要な社長アクション

1. **ANTHROPIC_API_KEY**: Anthropicアカウントからhttps://console.anthropic.com/settings/keys でAPIキーを発行して共有
2. **MBSログイン確認**: Chrome Debug ModeでMeta Business Suiteにログインし、セッションが有効であることを確認
3. **TikTok手動投稿**: Phase A完了後、Slackに送信されるMP4を手動投稿するフローを承認

## 監視体制

修復後、全ジョブの健全性を `watchdog.py`（30分間隔）で監視。
異常検知時はSlack #claudecodeに即時通知。
