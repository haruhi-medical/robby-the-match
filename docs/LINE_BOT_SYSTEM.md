# LINE Bot システム全容（ナースロビー）

> このドキュメントはLINE Botの全体像を外部AI（Gemini等）に読み込ませるために作成。
> 最終更新: 2026-04-07

---

## 1. システム概要

神奈川県特化の看護師転職サービス「ナースロビー」のLINE Bot。
広告やSNSから流入した看護師に、3問の簡易診断→AIマッチング→人間のキャリアアドバイザーへのハンドオフまでを自動で行う。

### 技術スタック
- **バックエンド**: Cloudflare Worker（`worker.js` 約7,400行）
- **データ**: Cloudflare KV（セッション管理）+ D1（施設DB 17,913件）
- **メッセージング**: LINE Messaging API
- **AI応答**: OpenAI GPT-4o-mini
- **人間連携**: Slack（#ロビー小田原人材紹介チャンネル）
- **Webチャット**: chat.js（LP埋め込みウィジェット）

### デプロイ情報
- Worker URL: `https://robby-the-match-api.robby-the-robot-2026.workers.dev`
- LINE Webhook: `{Worker URL}/api/line-start`
- LINE公式アカウント: `@174cxnev`（https://lin.ee/oUgDB3x）

---

## 2. 全体フロー（広告クリック→成約まで）

```
広告（Meta/TikTok/Instagram/SEO）
  ↓
/api/line-start?source=meta_ad&intent=direct
  ↓ session_id自動生成 → KV保存 → LINE友だち追加画面にリダイレクト
  ↓
LINE友だち追加（follow イベント）
  ↓ ウェルカムメッセージ + Quick Reply 4択
  ↓
簡易診断（3問: エリア / 働き方 / 緊急度）
  ↓
AIマッチング（施設DBからスコアリング → 上位5件表示）
  ↓
ハンドオフ判定（5条件のいずれかでトリガー）
  ↓
Slackに通知 → 人間が !reply で返信
  ↓
求人紹介 → 応募 → 面接 → 内定 → 入職
```

---

## 3. APIエンドポイント一覧

| エンドポイント | メソッド | 機能 |
|--------------|---------|------|
| `/api/line-webhook` | POST | LINE Webhookの受信（follow/message/postback） |
| `/api/line-start` | GET | 広告等からの入口。session_id生成→LINE追加画面にリダイレクト |
| `/api/line-push` | POST | Slack→LINEの返信ブリッジ（LINE_PUSH_SECRET認証） |
| `/api/link-session` | POST | LIFF経由のWebセッション→LINEユーザー紐付け |
| `/api/web-session` | POST | Web→LINEセッション引き継ぎ |
| `/api/chat` | POST | Webチャットウィジェット用AI応答 |
| `/api/chat-init` | POST | チャットウィジェット初期化 |
| `/api/chat-complete` | POST | チャット完了→KV保存（LINE引き継ぎ用） |

---

## 4. 会話フェーズ（20状態）

```
ONBOARDING:  welcome
INTAKE:      il_area → il_subarea → il_facility_type → il_department
             → il_workstyle → il_urgency
MATCHING:    matching_preview → matching_browse → matching → condition_change
AI相談:      ai_consultation_waiting → ai_consultation_reply → ai_consultation_extend
応募:        apply_info → apply_consent → apply_confirm
面接:        interview_prep
ハンドオフ:   handoff → handoff_silent → handoff_phone_check
             → handoff_phone_time → handoff_phone_number
ナーチャー:   nurture_warm → nurture_subscribed → nurture_stay → area_notify_optin
FAQ:         faq_salary / faq_nightshift / faq_timing / faq_stealth / faq_holiday
```

### フェーズ遷移の流れ

```
welcome（友だち追加）
  ├→「求人を探す」→ il_area → il_workstyle → il_urgency → matching_preview
  ├→「年収を知りたい」→ faq_salary → il_area（診断へ誘導）
  ├→「まず相談したい」→ handoff（即ハンドオフ）
  └→「まだ見てるだけ」→ nurture_warm（ナーチャー）

matching_preview（マッチング結果表示）
  ├→ 施設詳細タップ → matching → handoff（興味あり→ハンドオフ）
  ├→「もっと見る」→ matching_browse（次の5件）
  ├→「条件変更」→ condition_change → il_area（やり直し）
  └→「今はいい」→ nurture_warm

handoff（人間対応）
  → handoff_silent（Bot沈黙。FAQ以外のpostbackをガード）
  → Slackに通知 → 人間が !reply で返信
```

---

## 5. 簡易診断（インテーク）の質問内容

### Q1: エリア（il_area）
```
どのあたりで働きたいですか？

[横浜] [川崎] [相模原] [横須賀・三浦]
[県央(厚木・大和)] [湘南東部(藤沢・茅ヶ崎)]
[湘南西部(平塚・秦野)] [県西(小田原・南足柄)]
[東京都内]
```

### Q2: 働き方（il_workstyle）
```
夜勤はどうですか？

[日勤のみ] [夜勤OK] [こだわらない]
```

### Q3: 緊急度（il_urgency）
```
転職の時期は？

[すぐ転職したい] [3ヶ月以内] [良い求人があれば] [情報収集中]
```

---

## 6. マッチングロジック

### スコアリング基準（scoreFacilities関数）

| 条件 | 加点 |
|------|------|
| 夜勤マッチ | ±15〜25点 |
| 施設タイプ一致 | +15点 |
| 優先タグ一致 | +10点/タグ |
| 給与が希望以上 | +15点 |
| 教育体制「充実」 | +5〜10点 |
| 看護配置7:1 | +5点 |
| 救急レベル適合 | +3〜10点 |
| 公的・国立病院 | +3〜10点（安定志向の場合） |

### データソース
- **FACILITY_DATABASE**: worker_facilities.jsに埋め込み（212施設・手動調査）
- **D1 Database**: 17,913施設（厚労省データ）
- **ハローワーク求人**: data/hellowork_nurse_jobs.json（毎朝06:30自動取得、3,268件+）

### マッチング結果の表示形式
LINE Flex Messageで施設カードを表示:
```
🏥 小林病院（スコア: 85点）
📍 小田原市 / 🚃 小田原駅 徒歩10分
💰 月給28〜35万円 / 賞与4.0ヶ月
🗓 年間休日120日 / 日勤のみ可
✅ マッチ理由: エリア一致、日勤のみ対応、教育体制充実
[詳しく聞く] [他の求人を見る]
```

---

## 7. ハンドオフ（Bot→人間の引き継ぎ）

### トリガー条件（5つのうちいずれか）
1. 緊急度=「すぐ転職したい」（温度感A）
2. 施設詳細をタップ（興味あり）
3. 逆指名（特定施設を指定）
4. ユーザーが「直接相談したい」を選択
5. 会話が5ターン以上（高エンゲージメント）

### Slack通知フォーマット
```
🎯 LINE相談 → 人間対応リクエスト
温度感: 🔴 A / 緊急度: すぐ転職したい
📞 連絡方法: LINEのみ希望

🔥 ハンドオフ理由:
• 温度感A（すぐ転職したい）
• 施設詳細タップ（小林病院）

📋 求職者サマリ:
資格: 看護師 / 経験年数: 5年
希望エリア: 神奈川県西部 / 働き方: 日勤のみ

🏆 AIマッチング上位:
85pt: 小林病院（月給28-35万）
75pt: 横浜医療センター（月給30-38万）

💬 直近の会話:
👤「小田原で日勤のみの病院ありますか？」
🤖「3件見つかりました！1位は小林病院で...」
👤「小林病院について詳しく知りたい」

返信コマンド:
!reply U1234567890abcdef ここにメッセージを入力
```

### ハンドオフ後のBot動作
- フェーズが `handoff_silent` に遷移
- Botは自動応答を停止（FAQのpostbackのみ許可）
- 全ユーザーメッセージはSlackに転送され続ける
- 人間が `!reply` で返信

---

## 8. Slack連携の仕組み

### チャンネル
- **#claudecode**（C09A7U4TV4G）: Claude Code作業報告用
- **#ロビー小田原人材紹介**（C0AEG626EUW）: LINE通知・ハンドオフ・返信用

### !reply コマンド（slack_commander.py）
```
!reply U1234567890abcdef こんにちは！小林病院の求人について詳しくお伝えしますね。
```

処理フロー:
1. slack_commander.pyがSlackメッセージを監視（3秒間隔）
2. `!reply` を検出 → userIdとメッセージを抽出
3. Worker `/api/line-push` にPOST（LINE_PUSH_SECRET認証）
4. WorkerがLINE Messaging API経由でユーザーにpush送信
5. Slackに送信完了を報告

### slack_commander.pyの常駐
- LaunchAgent（macOS）で常時起動
- 3秒間隔でSlackチャンネルをポーリング
- `!reply` 以外にも `!status` `!help` コマンドあり

---

## 9. ウェルカムメッセージ（ソース別）

### 通常の友だち追加
```
はじめまして！ナースロビーです 🏥

神奈川県の看護師求人を、LINEだけで探せます。
電話なし・完全無料・いつでもブロックOK。

まずは何をしたいですか？

[求人を探す] [年収を知りたい] [まず相談したい] [まだ見てるだけ]
```

### 広告経由（source=meta_ad）
```
広告から来てくれたんですね！

神奈川県の看護師求人、30秒で診断できます。
まずはエリアを教えてください 👇

[横浜] [川崎] [県西(小田原)] [その他]
```
→ ウェルカムをスキップして即インテーク開始

### Web診断経由（LIFF sessionあり）
- Web側で回答済みのデータをKVから復元
- インテークをスキップして即マッチング表示

---

## 10. KVデータ構造

### ユーザーエントリ（line:{userId}）
```json
{
  "userId": "U1234567890abcdef",
  "phase": "matching_preview",
  "messageCount": 3,
  "updatedAt": 1712345678000,
  "area": "kanagawa_west",
  "areaLabel": "神奈川県西部",
  "subarea": "odawara",
  "urgency": "good",
  "workStyle": "nightshift_ok",
  "workplace": "hospital",
  "qualification": "RN",
  "experience": 5,
  "matchingResults": [{"n": "小林病院", "s": 85, ...}],
  "matchingOffset": 0,
  "browsedJobIds": ["id1", "id2"],
  "handoffAt": null,
  "phoneNumber": null,
  "messages": [
    {"role": "user", "content": "小田原で日勤のみ"},
    {"role": "ai", "content": "3件見つかりました！"}
  ],
  "welcomeSource": "meta_ad",
  "welcomeIntent": "direct"
}
```

### KVキーパターン

| キー | TTL | 用途 |
|-----|-----|------|
| `line:{userId}` | 30日 | ユーザー全データ |
| `line:ver:{userId}` | 30日 | 同時編集防止バージョン |
| `session:{sessionId}` | 24時間 | Web→LINEセッション橋渡し |
| `liff:{userId}` | 24時間 | LIFFブリッジ |
| `handoff:{userId}` | 7日 | ハンドオフ追跡 |
| `nurture:{userId}` | 30日 | ナーチャー管理 |

---

## 11. リッチメニュー（4状態）

| 状態 | 表示タイミング | ボタン |
|------|-------------|--------|
| default | 初回・リセット時 | 求人探す / 年収チェック / 転職相談 / FAQ |
| hearing | インテーク中 | 条件変更 / 求人を見る / 担当者相談 |
| matched | マッチング後 | 求人を見る / 逆指名 / 経歴書作成 |
| handoff | 人間対応中 | 求人を見る / 経歴書作成 / FAQ |

---

## 12. AIキャラクター「ロビー」

### 性格
- **正直**: 嘘をつかない。データに基づく。不確かなことは「わからない」と言う
- **味方**: 看護師の側に立つ。病院側の都合ではなく看護師のメリットで話す
- **おせっかい**: 聞かれてないことも「知っておいた方がいいこと」は伝える
- **押し売りしない**: LINE登録を強要しない。8:2ルール（8割ソフトCTA）

### 話し方
- LINE Bot: 丁寧語（です・ます）
- SNS投稿: カジュアル（タメ口）
- 禁止: 「革命的」「画期的」「必見」等の煽り表現
- 推奨: 看護師の現場語（申し送り、プリセプター、ナースコール等）

---

## 13. エラーハンドリング

| 状況 | 対応 |
|------|------|
| KV読み込み失敗 | インメモリフォールバック |
| 同時メッセージ（レースコンディション） | line:ver:{userId}でバージョン比較→リトライ |
| LINE認証エラー | 200 OK返却（クラッシュ防止）→ログ記録 |
| OpenAI API失敗 | 定型文フォールバック |
| D1 DB接続失敗 | FACILITY_DATABASE（インメモリ212件）にフォールバック |
| Slack通知失敗 | ログ記録のみ（LINE側は正常続行） |

---

## 14. 環境変数（Worker Secrets）

```
LINE_CHANNEL_SECRET       # LINE Webhook署名検証
LINE_CHANNEL_ACCESS_TOKEN  # LINE Messaging API
LINE_PUSH_SECRET          # Slack→LINE返信の認証キー
SLACK_BOT_TOKEN           # Slack Bot
SLACK_CHANNEL_ID          # 通知先チャンネル（C0AEG626EUW）
OPENAI_API_KEY            # GPT-4o-mini
CHAT_SECRET_KEY           # Webチャット認証
RICH_MENU_DEFAULT         # リッチメニューID×4
RICH_MENU_HEARING
RICH_MENU_MATCHED
RICH_MENU_HANDOFF
META_ACCESS_TOKEN         # Meta CAPI用
META_PIXEL_ID             # Meta Pixel（2326210157891886）
```

---

## 15. Webチャットウィジェット（chat.js）

LP（/lp/job-seeker/）に埋め込まれたチャットウィジェット。
LINE登録前の「お試し診断」としてLP上で2問の簡易診断を実施し、LINE誘導する。

### フロー
1. ユーザーがチャットアイコンをタップ
2. Q1: エリア選択 → Q2: 気になること選択
3. 給与レンジカード表示
4. 施設3件をカード表示
5. 「LINEで詳しく見る」CTA → LINE友だち追加

### セッション引き継ぎ
- chat.jsがsessionIdを生成 → localStorageに保存
- LINE CTAタップ時にsessionIdをURLパラメータで渡す
- LINE follow時にKVからセッションデータを復元
- Web診断の回答をスキップしてマッチングに直行

---

## 16. ファイル一覧

| ファイル | 行数 | 役割 |
|---------|------|------|
| `api/worker.js` | 7,433 | メインWorker（Webhook, マッチング, ハンドオフ, 全API） |
| `api/worker_facilities.js` | - | 施設データベース（212施設） |
| `api/wrangler.toml` | - | Cloudflare Worker設定（KV/D1バインディング） |
| `chat.js` | 1,142 | Webチャットウィジェット |
| `chat.css` | - | チャットウィジェットスタイル |
| `scripts/slack_commander.py` | 792 | Slack !reply コマンド常駐プロセス |
| `scripts/robby_character.py` | 500+ | AIキャラクター設定 |
| `scripts/slack_bridge.py` | - | Claude Code↔Slack連携 |
| `data/hellowork_nurse_jobs.json` | - | ハローワーク求人データ（毎朝更新） |

---

## 17. 現在の課題・改善ポイント

1. **LP→LINE転換率0.9%** — 広告はCTR 1.4%と優秀だがLPでの離脱が多い。LINE直リンク方式に移行中（2026-04-07〜）
2. **ハンドオフ後の返信速度** — 人間の返信が遅いとブロックされる。目標: 30分以内
3. **ナーチャー機能** — nurture_warmフェーズの自動フォローアップメッセージが未実装
4. ~~**リッチメニュー** — 4状態の画像が未作成~~ → **誤検知**: 現行メインメニュー1種（rm=start/new_jobs/contact/resume）で完成済。4状態切替は当初設計だけで実装不要
5. **CAPI連携** — META_ACCESS_TOKENが開発モードのため、follow時のLead イベント送信が不安定
