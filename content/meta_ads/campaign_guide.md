# Meta広告キャンペーン — Ads Manager方式（v2.0）

> 目的: Instagram広告 → LP → LINE友だち追加（問い合わせ獲得）
> 予算: 月¥5,000（日¥500 × 5日 × 2回）

---

## ゴールと導線

```
Instagram広告（ストーリーズ/リール）
  ↓ CTA「詳しく見る」→ LP直リンク
LP（quads-nurse.com/lp/job-seeker/）
  ↓ ファーストビューにLINEボタン（7箇所配置済み）
LINE友だち追加（lin.ee/oUgDB3x）
```

**重要: 「投稿ブースト」は使わない。LPリンクが設定できないため。**

---

## 前提条件チェック

- [x] Facebookページ作成済み
- [x] Instagramビジネスアカウント化+FB連携済み
- [ ] **Meta Pixel ID取得 → LPに埋め込み**（下記手順）
- [ ] **Ads Managerでキャンペーン作成**（下記手順）

---

## 既存Facebookページでの出稿について

Facebookページが別サービス名であっても、Instagram広告はInstagramアカウント名で表示されるため問題ありません。
Ads Managerで広告を作成する際、「Instagramアカウント」として@robby.for.nurseを選択すれば、
ユーザーに表示される広告主名は「robby.for.nurse」になります。

---

## Step 1: Meta Pixel IDの取得（5分）

1. https://business.facebook.com/events_manager/ にアクセス
2. 左メニュー「データソース」→「ピクセル」
3. 「ピクセルを追加」→ 名前: 「ナースロビー」
4. 「手動でコードをインストール」を選択
5. **16桁の数字（Pixel ID）をコピー**
6. Slackで平島さんがPixel IDを共有 → Claude CodeがLPに埋め込み

> Pixel IDが設定されると、LP訪問者数・LINEボタンクリック数が
> Meta広告マネージャーで直接確認でき、広告の自動最適化が効く。

---

## Step 2: Ads Managerでキャンペーン作成（10分）

### アクセス
https://www.facebook.com/adsmanager/

### キャンペーン設定

| 項目 | 設定値 |
|------|--------|
| キャンペーン目的 | **トラフィック** |
| キャンペーン名 | `NR_2026-03_traffic_test` |
| 特別広告カテゴリ | なし（求人広告ではなく情報提供型のため） |

### 広告セット設定

| 項目 | 設定値 |
|------|--------|
| 広告セット名 | `kanagawa_nurse_25-40F` |
| 最適化対象 | **ランディングページビュー** |
| 日予算 | **¥500** |
| 期間 | 5日間 |
| 地域 | **神奈川県**（県全域） |
| 年齢 | 25-40歳 |
| 性別 | 女性 |
| 興味関心 | 「看護」「看護師」「医療」「転職」 |
| 配信面 | **Advantage+ 配置**（自動最適化。手動の場合はストーリーズ+リール優先） |

### 広告クリエイティブ設定

**広告1本目: AD1 地域密着型**

| 項目 | 設定値 |
|------|--------|
| 広告名 | `ad1_local_feed` |
| フォーマット | シングル画像 |
| 画像 | `content/meta_ads/v3/ad1_local_feed.png` をアップロード |
| メインテキスト | 下記参照 |
| リンク先URL | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad1_local` |
| CTAボタン | **「詳しくはこちら」** |

**メインテキスト（125文字以内）:**
```
神奈川県の看護師さんへ

転職エージェントの手数料、10%って知ってた？
神奈川県全域対応の転職サポート。相談無料。

▶ 詳しくはリンクから
```

**広告2本目: AD3 共感型**

| 項目 | 設定値 |
|------|--------|
| 広告名 | `ad3_empathy_feed` |
| 画像 | `content/meta_ads/v3/ad3_empathy_feed.png` をアップロード |
| リンク先URL | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad3_empathy` |
| CTAボタン | **「詳しくはこちら」** |

**メインテキスト:**
```
「前にも言ったよね」
この言葉、何回聞いた？

それ、環境を変えるだけで解決するかも。
神奈川県で、あなたに合う職場を見つけませんか？

▶ 相談無料・営業電話なし
```

> AD2（手数料比較）は2本の結果を見てから2回目のブーストで使用。
> 最初は2本でA/Bテスト。

---

## Step 3: 配信開始後のチェック（毎日1分）

### 確認場所
Meta Ads Manager → キャンペーン → `NR_2026-03_traffic_test`

### 見るべき数値

| 指標 | 意味 | 5日間の目安 |
|------|------|------------|
| リーチ | 見た人数 | 1,500-3,000人 |
| LPビュー | LPを開いた人数 | 15-40人 |
| CPC | 1クリックあたりコスト | ¥50-150 |
| CTR | クリック率 | 0.5-2.0% |

### 判断基準（5日後）
- **CTR 1%以上の広告 → 勝ち。2回目のブースト（¥2,500）に採用**
- **CTR 0.3%未満 → 負け。クリエイティブ差し替え**
- **両方0.5%前後 → AD2に差し替えて再テスト**

---

## 月間運用フロー

```
Day 1-5:  AD1 vs AD3 をA/Bテスト（¥2,500）
Day 6:    結果確認。勝ち広告を特定
Day 7-11: 勝ち広告 or AD2で2回目ブースト（¥2,500）
Day 12:   月次レビュー
```

### 月次レポート（Slackで共有）
```
【2026年3月 Instagram広告レポート】
■ 予算: ¥5,000（2回配信）
■ 総リーチ: ___人
■ LPビュー: ___回
■ CPC: ¥___
■ LINE新規登録: ___名（LINE管理画面で確認）
■ 1登録あたりコスト: ¥___
■ 最も効果的だった広告: AD_
```

---

## Meta Pixel ID取得後にClaude Codeがやること

Pixel IDを教えてもらったら:
1. `index.html` + `lp/job-seeker/index.html` の `PIXEL_ID` を実際のIDに置換（2ファイル計4箇所）
2. デプロイ: `git push origin main && git push origin main:master`
3. Metaイベントテストツールで PageView + Lead イベントを確認

> LINEボタンクリック時の `fbq('track', 'Lead')` およびチャット開封時の
> `fbq('trackCustom', 'ChatOpen')` は実装済み（Pixel ID未設定時は自動スキップ）。

---

## UTMパラメータ一覧

| 広告 | URL |
|------|-----|
| AD1 地域密着 | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad1_local` |
| AD2 手数料比較 | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad2_comparison` |
| AD3 共感型 | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=paid&utm_campaign=ad3_empathy` |
| オーガニック投稿 | `https://quads-nurse.com/lp/job-seeker/?utm_source=instagram&utm_medium=organic` |

---

## よくある質問

**Q: 投稿ブーストじゃダメなの？**
A: ダメ。投稿ブーストではLP直リンクが貼れない。「プロフィールへのアクセス」しか誘導できず、LINE登録に繋がらない。

**Q: 特別広告カテゴリは必要？**
A: 今回は不要。「看護師募集！」ではなく「転職の情報提供」なので求人広告に該当しない。

**Q: 予算を増やしたい場合は？**
A: LINE登録1件あたりのコスト（CPA）が¥2,000以下なら、月¥10,000-20,000に増額の価値あり。成約1件の利益（約30万円）に対してROASは十分。
