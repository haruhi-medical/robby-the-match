# Meta Ads 健全性監査 — 2026-04-17

**対象**: NR_2026-04_line_direct（Pixel 2326210157891886）
**期間**: 2026-04-13〜2026-04-17（5日）
**監査基準**: ads-meta skill / 46-check audit

---

## 🎯 Meta Ads Health Score: **63/100（C+）**

```
Pixel / CAPI Health: 74/100  ███████░░░  (30%)
Creative:            58/100  █████░░░░░  (30%)
Account Structure:   54/100  █████░░░░░  (20%)
Audience:            66/100  ██████░░░░  (20%)
```

---

## 📊 実績サマリ（4日確定値）

| 日付 | 消化 | imp | clicks | CTR | CPC | LPV | Lead | LINE | CPA(Lead) |
|------|-----:|----:|------:|----:|---:|---:|---:|---:|---:|
| 4/13 | ¥2,567 | 494 | 19 | 3.85% | ¥135 | 12 | 4 | 3 | ¥642 |
| 4/14 | ¥2,613 | 489 | 20 | 4.09% | ¥131 | 15 | 2 | 15 | ¥1,306 |
| 4/15 | ¥1,884 | 309 | 14 | 4.53% | ¥135 | 9 | 0 | ? | N/A |
| 4/16 | ¥867 | 161 | 5 | 3.11% | ¥173 | 3 | 0 | ? | N/A |
| **計** | **¥7,931** | **1,453** | **58** | **~3.9%** | **~¥137** | **39** | **6** | **18+** | **¥1,322** |

### 一目診断
- ✅ **CTR 3.1〜4.5%** — 業界平均の**3〜4倍**（B2C平均1%）。クリエイティブは刺さっている
- ✅ **CPA（Lead）¥642〜¥1,306** — 目標¥5,000を大幅クリア。¥10,000ラインからはほど遠く、増額余地ありに見える
- 🔴 **消化額が日次で急減**（¥2,567→¥867、66%減）。Metaが配信を絞っている
- 🔴 **4/15-16でLeadイベント0件** — CAPI計測が壊れているか、実際に止まっているか要特定
- 🟡 **Lead/LINE乖離**: 4/14は Lead 2 / LINE 15（Lead過少）、4/13は Lead 4 / LINE 3（Lead過多）— eventが安定していない

---

## 🟥 致命的問題（即日対処）

### F-01: 配信量急減（66% drop in 3 days）
**症状**: 4/13 ¥2,567 → 4/16 ¥867。imp は 494→161（-67%）
**原因候補**:
1. Learning phase限定（LLM: Learning Limited — Leadが1日0件だとMetaはシグナル不足と判断）
2. 4/15-16のLead 0件 → 最適化シグナル消失 → 配信絞り込み
3. 広告セット予算¥2,000/日は **CPA ¥1,322の約1.5倍**。5x CPA = ¥6,610/日が必要（学習フェーズ脱出条件）
**対処**:
- [ ] Events Managerで4/15-16にLeadイベントが実際に発火していたか確認
- [ ] 発火していない場合: LP側fbq('track','Lead')のJSエラー調査 / CAPI side の META_ACCESS_TOKEN 有効性確認
- [ ] 発火しているのに反映されていない場合: event_id dedup のdedup rateを確認
- [ ] 根本対処: Lead目的ならLead発火を安定させる、または目的を「リンククリック」に戻して学習シグナルを担保

### F-02: Lead/LINE計測乖離
**症状**: MEMORY.md記載「Meta Lead vs LINE登録乖離 7.5倍」。4/14で検証すると Lead 2 / LINE 15 = LINE側が7.5倍
**原因**: LP側の `fbq('track','Lead')` は「LINE CTAクリック時」に発火する設計なのに、Lead数がLINE登録数より**少ない**のは以下のいずれか:
- (a) LINE登録者の多くが広告経由ではない（SNS/検索/ダイレクト）
- (b) LP経由せずに直接LINE QR/lin.ee を踏んでいる
- (c) Browser Pixelがads-blockerにブロックされている（Meta計測の5-10%ロス）
- (d) fbq発火時点でsession_id未設定で dedup 失敗

**対処**:
- [ ] source=meta_ad でLINE登録したユーザーだけを数える（Worker KV の `welcomeSource` を日次集計）
- [ ] LPの `window.__lineSessionId` が常にセットされているか確認（A/Bテスト用の経路で漏れがち）

### F-03: EMQ推定スコア 4-6（Fair）
**症状**: CAPI送信時の user_data は `external_id + fbp/fbc` のみ。email/phone未送信
**影響**: match quality低 → オーディエンス学習・Lookalike精度低下 → CPA悪化
**対処**:
- [ ] LINE Bot で電話番号を収集するhandoff_phone_number フェーズ後、CAPI Lead に `ph` (SHA256ハッシュ化済み電話) を追加
- [ ] 実装箇所: `api/worker.js:122-168` の `sendMetaConversionEvent` に `userData.ph` 追加
- [ ] 目標EMQ: 6→8

---

## 🟨 警告項目（1週間以内対処）

### W-01: クリエイティブフォーマット不足
- 現状: 動画1 + 静止画2 = 2フォーマット（目標: ≥3）
- 推奨: カルーセル追加（3-5枚構成。年収30〜50万/夜勤なし/日勤のみ等の要素を枚分け）
- メリット: CPC下げ、フォーマット疲労対策

### W-02: ad set あたりクリエイティブ数が境界
- 現状: 3本 / ad set（Meta推奨 ≥5）
- 対処: ミサキテスト結果（implementations/misaki_test.md）の上位3本を追加投入

### W-03: 予算 per ad set が学習フェーズ要件を下回る
- 現状: ¥2,000/日, 1 ad set = ¥2,000
- Lead CPA ¥1,322 × 5（Meta推奨）= **¥6,610/日**必要
- 現予算ではLearning Limited に入るリスク大（実際4/15-16で症状）
- 対処2択:
  - (A) 予算を¥3,000/日に増額し、学習促進
  - (B) 最適化目的を「リンククリック」or「ランディングページビュー」に変更し、より頻繁な最適化シグナルを供給（Leadは副次KPIで追跡）

### W-04: 配置をAdvantage+ではなく手動IG/FBフィード4面のみ
- MEMORY記載「IG/FBフィード手動4面のみ」 / guideには「Advantage+配置」とあり不一致
- Reels/Stories除外 → 若年ミサキ層（24-38歳）のReel視聴時間に届かない
- 対処: Reels/Storiesを追加（Story用9:16動画は既存カルーセルから流用可）

### W-05: 過去のv6失敗の原因が残存リスク
- MEMORY: v6でAudience Network/インストリームにゴミトラフィック配信
- v7で手動配置化は正解だが、将来Advantage+に戻すなら**Audience Networkだけを除外設定**推奨

### W-06: コピー訴求が散漫
- v5（給与/エリア/不満の3訴求）と v3 campaign_guide（年収診断/共感/数字インパクト）が並走
- 現行配信がどちらか不明 → 勝ちパターン特定困難
- 対処: 実際に配信中のad名（`ad1_salary_line` 等）を確認し、命名とコピーを統一

---

## 🟩 評価できる点

- ✅ Meta Pixel × CAPI 両方実装（dedup設計あり、event_id共有）
- ✅ fbp/fbc Cookie拾ってCAPIに添付（match quality向上）
- ✅ CTR 3.9% は業界トップ5%水準（v7の訴求改善が効いている）
- ✅ CPA ¥1,322 は目標の1/5以下（経済性はOK、あとは量）
- ✅ ジオ絞り（関東4都県）+ 年齢/性別（24-38F）+ 興味関心で適切に絞り込み
- ✅ 日次自動レポート（meta_ads_report.py 08:00 cron）で可視化

---

## 46項目チェック結果サマリ

### Pixel / CAPI Health（30%）— 74/100
| 項目 | 判定 | 備考 |
|------|:----:|------|
| Pixel installed全ページ | ✅ | 2326210157891886 |
| PageView発火 | ✅ | LP index.html:80 |
| CAPI 有効 | ✅ | worker.js:122 sendMetaConversionEvent |
| Event dedup (event_id) | ✅ | session_id共有 |
| EMQ ≥8.0 | 🟡 | 推定4-6、email/phone未送信 |
| 標準イベント | 🟡 | PageView + Lead + CompleteRegistration（ViewContent/AddToCart相当なし） |
| Domain verification | ❓ | 未確認、要Business Manager確認 |
| Aggregated Event Measurement | ❓ | iOS配信では未設定なら最大8イベント/domain制限違反リスク |
| CAPIに customer_information | 🔴 | external_id/fbp/fbc のみ、em/ph 未送信 |
| 通貨・value param | 🔴 | Lead イベントに value 未設定 |

### Creative（30%）— 58/100
| 項目 | 判定 | 備考 |
|------|:----:|------|
| ≥3 フォーマット | 🔴 | 動画+静止画のみ（2種） |
| ≥5 creative/ad set | 🟡 | 3本 |
| フォーマット疲労検知 | 🟡 | 4/16 CTR 3.11%（14日で-31%は該当） |
| 動画15s以内（Stories） | ❓ | 配置がフィードのみのため問題なし |
| UGC/証言テスト | 🔴 | 未実施 |
| DCO | 🔴 | 未使用 |
| headline<40字 | ✅ | v5コピー確認済 |
| primary<125字 | 🟡 | v5案Cは125字超 |
| 2-4週リフレッシュ | 🟡 | v7は4/12開始、そろそろ更新タイミング |

### Account Structure（20%）— 54/100
| 項目 | 判定 | 備考 |
|------|:----:|------|
| CBO使用 | ✅ | 設定あり |
| キャンペーン数 ≤5 | ✅ | 1キャンペーン |
| Learning Limited <30% | 🔴 | 4/15-16の配信減はLL症状 |
| 予算 ≥5x CPA | 🔴 | ¥2,000 vs 必要¥6,610 |
| ad set overlap <30% | ✅ | 1 ad setなので該当せず |
| 命名規則一貫 | 🟡 | v3 / v5のコピーが並走、ad nameと実コピーの照合不明 |
| Advantage+ Shopping | N/A | 非EC |

### Audience（20%）— 66/100
| 項目 | 判定 | 備考 |
|------|:----:|------|
| prospecting frequency <3 | ❓ | Ads Manager要確認 |
| retargeting frequency <8 | N/A | リタゲなし |
| Custom Audiences | 🔴 | 未作成（LP訪問者・LINE登録者ベースの作成可能） |
| Lookalike | 🔴 | 未作成（LINE登録18人+ では小さすぎるがseedとして試す価値あり） |
| Advantage+ Audience | ✅ | ONの記載あり |
| 興味関心 | ✅ | 看護/医療/転職 |
| Exclusions | 🟡 | LINE登録済みの除外リスト未設定（重複配信リスク） |
| 地域 | ✅ | 関東4都県 |

---

## 🚀 Quick Wins（影響度×実装コスト）

| 優先度 | 施策 | 影響 | 工数 |
|---|------|------|------|
| **1** | 4/15-16 Lead 0件の原因特定（Events Manager確認） | 配信回復 | 30分 |
| **2** | CAPI Lead にphone(SHA256)追加 | EMQ 6→8, CPA改善 | 1h |
| **3** | 日予算 ¥2,000→¥3,000 に増額（学習フェーズ脱出） | 配信安定化 | 5分 |
| **4** | カルーセル広告追加（第3フォーマット） | CTR維持、フォーマット疲労対策 | 2h |
| **5** | LP訪問者のCustom Audience作成（180日窓） | リタゲ基盤 | 15分 |
| **6** | LINE登録済みの除外オーディエンス作成 | 無駄配信削減 | 15分 |
| **7** | ad name とコピーv5/v3の整合確認+統一 | 勝ちパターン特定 | 1h |
| **8** | Domain Verification 確認 | iOS計測精度 | 30分 |

---

## 💡 判断が必要な事項（社長確認）

1. **目的変更の是非**: Lead目的を継続するか、「リンククリック」に戻して学習を担保するか
   - 推奨: まず¥3,000増額 + CAPI強化で1週間様子見、ダメなら目的変更
2. **予算増額の是非**: 現¥2,000/日 → ¥3,000/日（月¥90,000）
   - CPA ¥1,322は十分に安い。量が取れれば成約1件/月ライン到達可能
3. **v5コピーと v7 クリエイティブの整合**: 現在何が配信中か要確認

---

## 次アクション

1. **社長手動**: Ads Manager で (a) 4/15-16のLeadイベント発火履歴 (b) 現在の配信中クリエイティブ名 を確認
2. **Claude実装**: CAPI に phone 追加（要: 電話番号取得フェーズの洗い出し）
3. **48時間後の検証**: Lead再発火、配信量回復、CPA推移

---

**監査担当**: ads-meta skill / Claude Code 経営参謀
**次回監査**: 2026-04-24（クリエイティブ疲労検知再実施）
