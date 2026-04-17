# Meta広告戦略 調査結果 — 2026-04-17

## 調査タスク4件の結果

| # | タスク | 状態 | 結果 |
|---|--------|:----:|------|
| 1 | Clarity録画確認 | 🟡 保留 | セッション切れ、社長ログイン必要 |
| 2 | Custom Audience 3種作成 | 🔴 ブロック | 利用規約未承諾、社長手動1クリック必要 |
| 3 | Lookalike基盤調査 | ✅ 完了 | seed不足、対策あり |
| 4 | welcomeSource計測バグ調査 | ✅ 完了 | 計測は仕様通り、設計欠陥判明 |

---

## 🎯 重要発見1: welcomeSource="none" の正体

### 実装上は「バグ」ではなく「仕様欠陥」
```
広告 → LP → CTAクリック → Worker /api/line-start
  ↓ session_idをKVに保存
  ↓ 302 redirect → line.me/R/ti/p/@174cxnev?dm_text=<session_id>
LINEアプリ/Web: 事前入力テキスト画面を表示
  ↓ ユーザーが「送信」ボタン押下
  ↓ Botがテキスト受信 → session_id認識 → welcomeSource=meta_ad 記録
```

**落とし穴**: ユーザーが「送信」ボタンを**押さないと source が判定できない**。
- KV 15人調査: `messageCount=0` が10人（67%） = 友だち追加だけでメッセージ未送信
- これらは全員 `welcomeSource='none'` で保存 → 広告経由か判別不能

### 発見した第二の設計バグ
LP `/lp/job-seeker/index.html` のCTA source=hero/sticky/bottom **固定**。
URL querystringの `utm_source=meta` を読んで継承する機構が無い。
→ **広告経由で登録成功したユーザーでも source が "meta_ad" にならず "hero" になる**
→ 「Meta広告経由登録者」のCustom Audienceが作れない根本原因

---

## 🎯 重要発見2: Pixelイベント実態

### 3/1〜4/17 Pixel累計
```
PageView: 493件
Lead:     59件  ← 広告レポートLead 14件と乖離（広告外でもLead発火多数）
```

### 日次内訳の異常
- **4/14 Lead 25件**: 広告レポート「Lead 2件」と乖離14倍
- **社長のテスト利用**でLead誤発火の可能性（ヘビーユーザーU7e23b5... messageCount=592）
- LP内でCTAを何度もクリックするとLead乱発する設計

### 修正すべき点
- Lead発火は「session_idごと1回のみ」に制限（LocalStorageで発火済みフラグ）
- 本番Lead基準を `CompleteRegistration`（CAPI側、LINE友だち追加）に統一

---

## 🎯 重要発見3: Lookalike実現性

### Seed評価
| Seed源 | 現数 | Lookalike可否 |
|--------|-----:|:------------:|
| Pixel Lead発火者 | 59件 | 🔴 不足（推奨1,000+） |
| Pixel PageView発火者 | 493件 | 🟡 微妙（180日で積み上げ可） |
| @robby.for.nurse IGフォロワー | 3人（MEMORY記載） | 🔴 実質不可 |
| LINE登録者(KV) | 15人 | 🔴 不可 |
| LINE登録者のうち看護師 | **0-1人** | 🔴 論外 |

### 現実解
1. **即時**: Lookalike 1% の seed確保は厳しい。**諦めて別手段**
2. **ダイレクト看護師ターゲティング**: @ナース専科 等の看護師特化IGアカウントはMeta側で「類似オーディエンス」として指定不可（Metaはページ単位のLookalikeを他アカウント向けに作れない）
3. **時間軸**: 180日間Pixel PageView積み上げで1,000件到達を待つ
4. **今できる最大値**: `CA_all_pageview_180d` を作って広告セットに追加（リタゲのみ）

---

## 🎯 重要発見4: Custom Audience利用規約

Meta Ads APIでCustom Audience作成するには、アカウントで1回だけ規約同意が必要。
社長手動作業: https://www.facebook.com/customaudiences/app/tos/?act=907937825198755 にアクセスして同意ボタン押下のみ。

---

## 🚨 結論: 戦略を3段階に分ける

### 段階1: 今すぐ止血（社長手動 1時間）
- [ ] Custom Audience利用規約承諾（1クリック）
- [ ] Ads Managerで広告セット**一時停止**（¥2,000/日の垂れ流し防止、計測修復まで）
- [ ] Clarityログインして広告流入セッション10本録画視聴

### 段階2: 計測修復（Claude実装 1日）
- [ ] LP: URL param `utm_source=meta` をCTA source に継承する修正
- [ ] LP: Lead発火をsession_idごと1回に制限（LocalStorage）
- [ ] Worker: CAPIで Pixel Lead の代わりに `CompleteRegistration`（LINE友だち追加）を主イベント化
- [ ] Ads Manager: 最適化目標を`Lead`→`CompleteRegistration`に変更
- [ ] 動作確認: テストユーザーで実装通り source=meta_ad が記録されるか

### 段階3: 本格配信再開（7日間）
- [ ] Custom Audience `CA_all_pageview_180d` 作成（ToS承諾後）
- [ ] Lookalike `LAL_1pct_PV_JP` 作成（seed 493件、期待value小）
- [ ] 広告セット再開: 23-65F / 関東4都県 / IG + FBフィード / Advantage+ OFF
- [ ] 日次KPI: **CompleteRegistrationベース**でCPA測定
- [ ] 7日後: 本物看護師登録者の割合で判断

---

## 📊 6人パネル再評価

| 専門家 | 再評価ポイント |
|--------|----------------|
| 広告プロ | 「Custom Audience作ろう」→ **ToS承諾すらしてなかった**。スタート地点以前の状態 |
| UXデザイナー | welcomeメッセージのCTA改善が急務（67%離脱の根本） |
| 悪魔 | 「Lead偽物疑惑」→ **看護師確定ゼロで的中**。厳しい現実 |
| 行動経済学者 | welcome画面で「送信」ボタンを押す動機設計ゼロ |
| LINE Bot開発者 | Lead定義→CompleteRegistration置換が最優先 |
| ミサキ | 「AI転職は胡散臭い」→ クリエイティブ刷新も並行で必要 |

---

## 📌 社長に依頼したい手動作業（3点、合計15分）

1. **Custom Audience規約承諾**: https://www.facebook.com/customaudiences/app/tos/?act=907937825198755
2. **Ads Manager広告セット一時停止**（計測修復までの2-3日間のみ）
3. **Clarityログイン**: https://clarity.microsoft.com/projects/view/vmaobifgm0/dashboard

3つ全部終わった時点でSlackで一報ください。続行タスクに移ります。
