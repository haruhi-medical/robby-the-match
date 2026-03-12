# 人間作業リスト（2026-03-12）

> Claude Codeでは自動化できなかったタスク。平島さんが手動で対応する必要あり。

---

## Task 5: Cloudflare Worker再デプロイ【要対応】

**問題**: `CLOUDFLARE_API_TOKEN` の権限が不足しており、wrangler deployが失敗。
エラー: `Authentication error [code: 10000]` — Workers編集権限がトークンにない。

**手順**:
1. https://dash.cloudflare.com/profile/api-tokens を開く
2. 現在のAPI Tokenを編集し、以下の権限を追加:
   - `Workers Scripts: Edit`
   - `Workers Routes: Edit`
   - `Account Settings: Read`
   - `User Details: Read`
3. トークンを再生成し、`.env` の `CLOUDFLARE_API_TOKEN` を更新
4. ターミナルで実行:
   ```bash
   cd ~/robby-the-match
   mv _redirects _redirects.bak
   npx wrangler deploy api/worker.js --config api/wrangler.toml
   mv _redirects.bak _redirects
   ```
5. 動作確認: LINE Botに何か送信してレスポンスを確認

**所要時間**: 5-10分

---

## Task 6: Meta広告クリエイティブ差し替え【要対応】

**状態**: v4クリエイティブが生成済み（`content/meta_ads/v4/`）。Ads Managerでの差し替えが必要。

**手順**:
1. https://www.facebook.com/adsmanager/ を開く
2. キャンペーン `NR_2026-03_traffic_test` を選択
3. 既存の広告（ad1_local等）を**オフ**にする（削除はしない）
4. 「広告を作成」で新しい広告2本を追加:

   **AD1: 年収診断型**
   - 画像: `content/meta_ads/v4/ad1_salary_feed.png`（フィード用）+ `ad1_salary_story.png`（ストーリー用）
   - テキスト:
     ```
     看護師5年目の平均年収、480万円って知ってた？
     あなたの経験年数で、いくら貰えるはず？
     30秒で年収診断できます。
     ▶ 詳しくはリンクから（相談無料・電話なし）
     ```
   - リンク先: `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad1_salary`
   - CTA: 「詳しくはこちら」

   **AD2: 共感型**
   - 画像: `content/meta_ads/v4/ad2_empathy_feed.png` + `ad2_empathy_story.png`
   - テキスト:
     ```
     「前にも言ったよね」
     この言葉、何回聞いた？
     人間関係がしんどいなら、環境を変えるだけで解決するかも。
     神奈川県で、あなたに合う職場を一緒に探しませんか？
     ▶ まずは話を聞いてみる（相談無料・しつこい電話なし）
     ```
   - リンク先: `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad2_empathy`
   - CTA: 「詳しくはこちら」

5. ターゲティング改善（同時に）:
   - 興味関心を追加: 「医療」「ヘルスケア」「病院」「介護」「看護学」
   - Advantage+ オーディエンスをONにして自動拡張を許可
6. 配信開始

**所要時間**: 10-15分

---

## Task 7: Meta広告予算 ¥500→¥1,000/日【要対応】

**理由**: ¥500/日では学習フェーズを抜けられない（最低50クリック必要）。
¥1,000/日×5日=¥5,000で一気にデータを貯め、勝ちクリエイティブを特定する。

**手順**:
1. Ads Manager → キャンペーン `NR_2026-03_traffic_test`
2. 広告セット `kanagawa_nurse_25-40F` を選択
3. 日予算を ¥500 → **¥1,000** に変更
4. 保存

**所要時間**: 1分

---

## Task 8: GA4ファネル設定【要対応】

**目的**: LPミニ診断の離脱ポイントを可視化する。

**手順**:
1. https://analytics.google.com/ を開く（プロパティ: G-X4G2BYW13B）
2. 左メニュー「探索」→「空白」→ テンプレート「ファネルデータ探索」を選択
3. ステップを以下の順番で設定:

   | ステップ | イベント名 | 説明 |
   |---------|-----------|------|
   | 1 | `page_view` | LP訪問 |
   | 2 | `shindan_start` | 診断開始（Q1表示） |
   | 3 | `shindan_q1` | Q1回答 |
   | 4 | `shindan_q2` | Q2回答 |
   | 5 | `shindan_q3` | Q3回答 |
   | 6 | `shindan_complete` | 診断完了（結果表示） |
   | 7 | `shindan_line_click` | LINE登録クリック |

4. フィルタ: ページパス = `/lp/job-seeker/`
5. 名前: 「ミニ診断ファネル」で保存
6. （オプション）カスタムイベントが届いているか確認:
   - 「レポート」→「リアルタイム」で診断を自分で実行してイベント確認

**所要時間**: 10分

---

## Task 9: Googleビジネスプロフィール登録【要対応】

**目的**: 「神奈川 看護師 転職」等のローカル検索でGoogleマップ枠に表示される。無料。

**手順**:
1. https://business.google.com/ にアクセス（Googleアカウントでログイン）
2. 「ビジネスを追加」→「ビジネスを1件追加」
3. 入力情報:
   - ビジネス名: **神奈川ナース転職**
   - カテゴリ: 「人材紹介会社」または「Employment agency」
   - 住所: はるひメディカルサービスの所在地
   - サービス提供エリア: **神奈川県**（県全域を追加）
   - 電話番号: 事業用電話番号
   - ウェブサイト: `https://quads-nurse.com`
4. 確認方法を選択（ハガキ/電話/メール — 業種による）
5. 確認完了後:
   - 営業時間: 平日9:00-18:00（または適切な時間）
   - サービス説明: 「神奈川県全域対応の看護師専門転職支援。紹介手数料10%で病院の採用コストを削減。AIマッチング+人間サポートで最適な職場を提案します。」
   - 写真: ロゴやLP画像をアップロード

**所要時間**: 15分（確認完了まで数日かかる場合あり）

---

## Task 10: Mac Miniスリープ無効化【対応不要】

**状態**: 既に無効化済み。
```
sleep                0 (sleep prevented by powerd, caffeinate)
displaysleep         0 (display sleep prevented by remoting_me2me_host)
disksleep            0
```
caffeinate + powerdがスリープを防止中。追加対応不要。

---

## Task 11: Upload-Post.com APIキー取得【要対応】

**目的**: TikTokカルーセル投稿の自動化（現在のtiktok_carousel.pyがAPIキー未設定で無効）。

**手順**:
1. https://upload-post.com/ にアクセス
2. アカウント作成（Googleアカウント or メール）
3. ダッシュボード → API設定 → APIキーを取得
4. `~/robby-the-match/.env` に追記:
   ```
   UPLOAD_POST_API_KEY=取得したキー
   ```
5. 動作確認: `python3 scripts/tiktok_carousel.py --test`

**注意**: 有料プランが必要な場合あり。料金を確認してから判断。

**所要時間**: 5分

---

## Task 12: Canva MCP OAuth認証【要対応】

**目的**: Claude CodeからCanva APIを使い、高品質なSNS画像を生成する。

**手順**:
1. Claude Codeを再起動（新しいセッション）
2. Canva MCPツールを使おうとすると、ブラウザでOAuth認証画面が開く
3. Canva有料アカウントでログイン
4. 「許可」をクリックしてアクセスを承認
5. Claude Codeに戻り、Canvaツールが使えることを確認

**前提**: `claude mcp add --transport http canva https://mcp.canva.com/mcp` は設定済み。

**所要時間**: 2分

---

## 優先度まとめ

| 優先度 | タスク | 理由 |
|--------|--------|------|
| **高** | Task 5: Worker再デプロイ | LINE Botが最新版でない |
| **高** | Task 6+7: 広告差し替え+予算増 | ROI改善の即効性 |
| **中** | Task 8: GA4ファネル | 診断離脱ポイントの可視化 |
| **中** | Task 9: GBP登録 | ローカルSEO強化（無料） |
| **低** | Task 11: Upload-Post | カルーセル自動化（代替手段あり） |
| **低** | Task 12: Canva MCP | 画像品質向上（Pillowで代替可） |
| **済** | Task 10: スリープ無効 | 既に設定済み |
