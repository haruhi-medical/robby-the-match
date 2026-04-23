# AICA 引き継ぎ — 2026-04-23

> 本ドキュメントは AICA の現時点の状態・進捗・次回開始時に確認すべき事項をまとめた引継ぎメモ。
> 次回セッション開始時に必ず最初に読む。

## 今回（2026-04-22〜04-23）の成果サマリ

2日間で AICA MVP1 → MVP2 レベルに拡張。主な追加機能:

1. **音声入力対応**（Whisper）
2. **3段階分割＋中断/再開**（離脱対策）
3. **P0 改善3件**（電話番号後回し・Q&A文言・PAUSED復帰cron）
4. **P1 改善2件**（/health deep・志望動機フッター）
5. **Phase 14 病院推薦文送付準備**
6. **Phase 16 面接対策**（想定Q&A・模擬面接・逆質問）
7. **キャリアシート自動生成（Layer 1）** ← 今回の目玉

合計コミット: 10+件。Worker version は 04e73c52 → ce57e3ce まで複数回更新。

## デプロイ済み Worker 最終版
- Version ID: `ce57e3ce-760d-43c7-bb40-c7dd3524dc65`
- URL: https://nurserobby-aica-api.robby-the-robot-2026.workers.dev
- Cron: `0 0 * * *` (PAUSED復帰Push) / `0 * * * *` (未使用)
- Secrets: 7個全て設定済

## 実装状況

### ✅ 完了（14/20 フェーズ + 横断機能多数）
| # | フェーズ | 備考 |
|---|--------|------|
| 1 | Welcome | follow event |
| 2-5 | 心理ヒアリング 4ターン | 軸別分岐、空reply 3段フォールバック |
| 6 | 条件ヒアリング AI対話13項目 | is_complete=true でキャリアシート自動生成トリガー |
| 7 | 求人マッチング Flex 3件 | nurse-robby-db 参照 |
| 8 | 求人Q&A | 意図分類+AI事実回答 |
| 9 | 応募意思確認 | Stage 1→2 境界で中断可 |
| 10 | 個人情報収集 4問 | 電話除外 |
| 11 | 書類作成ヒアリング 5問 | |
| 12 | AI書類生成 | テキスト版のみ、PDF未実装 |
| 13 | 書類修正Q&A | |
| 14 | 病院推薦文送付準備 | Slack通知+D1記録 |
| 16 | 面接対策 | 4モード、割り込みエントリ対応 |

### 横断機能
- 音声入力（Whisper-1 ja + 看護師語prompt）
- 3段階分割 + 中断/再開（「続きから」で resume_from 復帰）
- PAUSED復帰 cron Push（Day 3/7）
- AI多層フォールバック（OpenAI→Claude→Gemini→Workers AI）
- 緊急キーワード14語検出
- /health?deep=1 疎通チェック
- キャリアシート自動生成（候補者には見えない、社長Slack通知のみ）

### ❌ 未実装（6/20 フェーズ）
- Phase 15 面接日程調整（電話番号収集はここ）
- Phase 17 面接後フォロー
- Phase 18 内定通知・条件交渉
- Phase 19 退職交渉支援
- Phase 20 入職前後フォロー Push（Day 1/3/7/30/90）
- Slack `!aica sent <userId>` コマンド → APPLIED 遷移

## キャリアシート（今回の目玉機能）

### 動作
```
候補者: 条件ヒアリング完了（is_complete=true）
  ↓
├─ フォアグラウンド: 求人マッチング3件 LINE Push
└─ バックグラウンド: ctx.waitUntil で自動生成
     ├─ D1 messages から候補者の実発言15件抽出
     ├─ AI推薦コメント生成（3段落250-400字）
     ├─ 禁止語検出→リトライ→伏せ字マスク（ハルシネーション防止）
     ├─ HTMLテンプレで A4縦1枚組立（氏名イニシャル化）
     ├─ D1 candidates に serial/html/generated_at 保存
     └─ Slack通知（候補者サマリ+推薦コメントプレビュー+URL）
```

### 社長の使い方
1. 候補者が条件ヒアリング終えるとSlackにキャリアシート完成通知が届く
2. 通知内の閲覧URLをクリック → ブラウザで開く
3. 印刷 or PDF保存してFAX/メールで病院に送付
4. 求人ある病院・ない病院どちらにも撒ける

### 最新出力サンプル（石塚さん = テスト候補者）
URL: https://nurserobby-aica-api.robby-the-robot-2026.workers.dev/career-sheet/NR-20260423-9615

推薦コメント:
> 急性期病棟の師長として10年のキャリアを積まれた方です。現在は呼吸器内科病棟にて、
> リーダー業務を中心に職員とのコミュニケーションを重視しながら日々の業務に取り組んで
> おられます。
>
> 転職にあたっては、急性期の現場での経験を活かしつつ、神奈川県全域で夜勤ありの常勤
> ポジションを探しておられます。給与水準は550万円以上を希望されており、特に納得できる
> 求人があれば入職を検討するご意向です。
>
> ヒアリングでは、職員とのコミュニケーションを大切にし、リーダーとしての役割をしっかり
> 果たされている印象が強く残りました。また、冷静な語り口で現場の状況を分析される姿勢が
> 印象的で、業務に対する真摯な姿勢を感じました。お人柄としては、責任感の強い方と
> お見受けしております。是非、前向きなご検討の程よろしくお願いいたします。

### 管理エンドポイント（社長向け）
既存候補者のキャリアシート生成が必要になった時に使う:
```bash
curl -X POST "https://nurserobby-aica-api.robby-the-robot-2026.workers.dev/admin/career-sheet/generate" \
  -H "Authorization: Bearer <AICA_ADMIN_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"candidateId": "Uxxx"}'

# 全員一括バックフィル
  -d '{"mode": "backfill_all"}'
```

AICA_ADMIN_KEY は Worker secret に保存済。社長依頼時に共有。

## 残課題 — 次回やるべき優先順位

### 🔴 P0（社長ヒアリング必要）
1. **送信元情報（電話・メール・許可番号）の反映**
   - キャリアシートのフッターに記載される
   - 現状: 「（要設定）」プレースホルダー
   - 解: 社長から値を聞いてテンプレに埋める（または Worker 環境変数化）

2. **履歴書フローの方針決定**
   - Phase 11-13 を残すか、ナースロビー本体のマイページに誘導に変更するか
   - 現状: AICA で書類生成まで実装済（並走中）
   - 社長発言: 「履歴書作成はすでにナースロビーで完成している」
   - 判断待ち: 疎結合（URL誘導のみ）で進める合意は得たが、実装は未着手

### 🟡 P1（すぐできる改善）
3. **キャリアシート PDF化**（R2 + pdf-lib）
   - FAX機直送・PDFダウンロード用
   - 現状: HTMLのみ（ブラウザで印刷→PDF保存は可）

4. **勤務先の匿名化レベル精緻化**
   - 現状: 「横浜◯◯病院」→「一般病院」一律置換
   - 改: 病床規模・診療科特化度・急性期/療養区分を保つ匿名化

5. **職歴テーブルのAI整形**
   - 現状: work_historyの生データを改行分割のみ
   - 改: 期間+施設種別+業務内容 に構造化

6. **Slack `!aica sent <userId>` コマンド**
   - APPROVED → APPLIED 遷移 + ユーザーに送付完了Push
   - 現状: 手動更新のみ

### 🟢 P2（順次）
7. Phase 15 面接日程調整（ここで電話番号収集）
8. Phase 19 退職交渉支援
9. Phase 20 入職後フォロー cron
10. Phase 17 面接後フォロー
11. Phase 18 内定通知・条件交渉
12. Layer 2: 候補者 opt-in でキャリアシート自動配信
13. 音声訂正フロー（「違う、〜と言った」で前phase戻す）
14. 軸判定の複数軸対応
15. Flex Carousel に AI所見（厚労省夜勤目安等）

## 次回開始時に必ず確認

```bash
# 1. Workerが生きているか
curl https://nurserobby-aica-api.robby-the-robot-2026.workers.dev/health?deep=1

# 2. secretsが消えていないか
cd ~/robby-the-match/api-aica && unset CLOUDFLARE_API_TOKEN && \
  npx wrangler secret list --config wrangler.toml
# 期待: 7個（LINE×2, OPENAI, SLACK×2, AICA_ADMIN_KEY, SLACK_CHANNEL_URGENT）

# 3. D1の候補者状況
unset CLOUDFLARE_API_TOKEN && \
  npx wrangler d1 execute nurserobby-aica-db --remote --config wrangler.toml \
  --command "SELECT phase, COUNT(*) FROM candidates GROUP BY phase;"
```

## ファイル・コード位置リファレンス

```
api-aica/
├── wrangler.toml         # Worker設定
├── schema.sql            # D1スキーマ（ALTERは手動実行・schema.sql自体は追いきれていない）
├── README.md             # セットアップ手順
└── src/
    ├── index.js            # エントリ（webhook+cron+/health+/career-sheet+/admin）
    ├── prompts.js          # intake/axis/summary/condition プロンプト
    ├── state-machine.js    # PHASES 定数、D1ヘルパ
    ├── lib/
    │   ├── line.js         # LINE reply/push
    │   ├── openai.js       # 多層フォールバック generateResponse
    │   ├── slack.js        # 通知
    │   ├── jobs.js         # 求人検索 + Flex
    │   ├── transcribe.js   # Whisper
    │   ├── staging.js      # 3段階分割+中断/再開
    │   └── cron-resume.js  # Day 3/7 Push
    └── phases/
        ├── intake.js           # 心理4ターン
        ├── condition.js        # 条件ヒアリング + キャリアシートトリガー
        ├── matching.js         # 求人マッチング
        ├── job-qa.js           # Q&A
        ├── apply.js            # 応募意思 + Stage1→2境界
        ├── apply-info.js       # 個人情報4問
        ├── documents-prep.js   # 書類ヒアリング5問 + Stage2→3境界
        ├── documents-gen.js    # AI書類3点生成
        ├── documents-review.js # 修正Q&A
        ├── hospital-send.js    # 推薦文生成+Slack通知
        ├── interview-prep.js   # 面接対策4モード
        ├── career-sheet.js     # ★キャリアシート自動生成★
        └── profile.js          # 旧・廃止予定
```

## 主要コミット履歴（2026-04-22〜23）

| Commit | 内容 |
|--------|------|
| 4dcfddb | Phase 8-10 実装（Q&A・応募意思・個人情報5問） |
| 296e1dd | Phase 11 実装（書類作成ヒアリング5問） |
| 20681c3 | 条件ヒアリング空reply 3段フォールバック |
| fa810a4 | Phase 12-13 実装（AI書類生成・修正Q&A） |
| 610430c | Phase 16 面接対策4モード |
| b25d007 | 音声入力（Whisper）対応 |
| 76f9767 | 3段階分割+中断/再開 |
| 9480793 | P0改善3件（電話番号後回し・Q&A文言・cron復帰） |
| 4876b12 | /health deep + 志望動機フッター |
| 3a62649 | Phase 14 病院推薦文送付準備 |
| 2e641b4 | キャリアシート自動生成 Layer 1 |
| 3e46789 | キャリアシートAIハルシネーション対策3段 |
| 55491de | キャリアシート表現改善（魅力的な推薦文） |

## 経営判断事項（社長対応待ち）

- [ ] AICAキャリアシートの送信元情報（電話・メール・許可番号）
- [ ] 履歴書フローの方針（AICA並走維持 / ナースロビー誘導）
- [ ] Layer 2（候補者opt-in配信）に進むか否か
- [ ] 求人持ってない病院への最初のFAX試験運用をいつ始めるか

## 学んだこと

### AI ハルシネーション対策は必須
初版で「子育て」「残業少なく」などprofileにない創作が混入。
病院に嘘を伝えるリスクが大きいため、3段構えで対策:
1. プロンプト厳格化（禁止ワード列挙）
2. 候補者の実発言を明示的にAIに渡す
3. 出力検証 → 混入時リトライ or マスク

### 表現と事実は独立した軸
同じ事実でも枠組みで魅力度が大きく変わる:
- ❌「夜勤がしんどい」→「残業少なく子育て理解を希望」（創作）
- ✅「夜勤がしんどい」→「長く続けられる働き方を重視」（枠組み変更のみ）

「嘘禁止・表現は前向き」の両立は、プロンプトで達成可能。

### 3段階分割は離脱対策に効く
20問一気通貫は集中力続かない。
中断ポイントを明示的に設け「今日はここまで・続きは明日」を選ばせる。
「続きから」キーワードで自然復帰。cron で Day 3/7 に促し。

### エージェント中心の設計が筋
スカウトDBサービスとの競合は避ける。
AICA = エージェントの武器（キャリアシート自動生成）として位置づけ。
1対1候補者営業 + 新規病院開拓の両方を強化する。

---

**最終更新**: 2026-04-23 AM
**Worker Version**: ce57e3ce-760d-43c7-bb40-c7dd3524dc65
**全コミット数**: 13（2日間で）
**次セッション開始時必読**
