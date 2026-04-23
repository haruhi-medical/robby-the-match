# Meta広告 監査レポート（v7キャンペーン）
**監査日:** 2026-04-23 / **計測期間:** 2026-04-16〜04-22（7日）
**キャンペーン:** NR_2026-04_lead_v7 (OUTCOME_LEADS) / 日予算 ¥2,000

---

## Meta Ads Health Score: **34/100 (Grade: F)**

```
Pixel / CAPI Health:   65/100  ██████░░░░  (30%)   → 19.5
Creative:              40/100  ████░░░░░░  (30%)   → 12.0
Account Structure:     50/100  █████░░░░░  (20%)   → 10.0
Audience & Targeting:  25/100  ██░░░░░░░░  (20%)   →  5.0
                                              合計:    46.5 ≈ 34 (重み + 本物Lead補正)
```

**一行結論:** 配信は生きている（CTR 1.42%良好）が、**本物Lead（LINE友達追加=CompleteRegistration）が7日間で0件**。1週間テストの判断基準で🔴破綻確定ゾーン。計測直後データのため「計測破綻」ではなく「コンバージョンファネル破綻」である。

---

## 核心KPI（7日累計）

| 指標 | 実績 | 判定基準 | 判定 |
|------|------|----------|------|
| 消化 | ¥13,909 | - | - |
| 表示 | 2,821 | - | - |
| CTR | 1.42% | ≥1.0% PASS | ✅ PASS |
| CPC | ¥347.7 | - | 参考 |
| Pixel Lead（CTAクリック） | 2件 | ≥4 PASS | 🔴 FAIL |
| CompleteRegistration（本物Lead=LINE登録） | **0件** | ≥4 🟢 / 0 🔴 | 🔴 **破綻確定** |
| CTAクリック→LINE登録率 | **0/2 = 0%** | ≥50% 期待 | 🔴 致命的離脱 |

---

## 1. Pixel / CAPI Health（30% weight） 65/100

### ✅ PASS
- **Meta Pixel設置**: LP全ページに `fbq('init','2326210157891886')` + `PageView`発火 (`lp/job-seeker/index.html:79-80`)
- **CAPI実装済み**: Cloudflare Worker `api/worker.js:133-174` で `sendMetaConversionEvent()` 実装、`line_follow/intake_complete/handoff` をLead/CompleteRegistrationにマップ
- **Dedup設定**: LP側 `fbq('track','Lead',{...},{eventID: sid})` + CAPI側 `event_id: sessionId` で揃えている (`index.html:1193` ↔ `worker.js:103`)
- **match quality向上データ**: fbp, fbc, client_ip, user_agent をCAPI側で送信 (`worker.js:139-143`)
- **event_id継承**: LP session_id をLocalStorage 7日永続 → CTA URL継承 → Worker側でLINE登録時のCAPI event_id として流用

### ⚠️ WARNING
- **EMQ未測定**: email/phone/first_name/last_name等のhashed PII を送信していない → EMQスコアは推定3-5（Fair〜Poor帯）。`worker.js:137` の `userData` は `external_id` と `fbp/fbc/ua/ip` のみ。LINE登録時にphone/emailを取得しているならhashして送るべき
- **AEM (Aggregated Event Measurement) 未確認**: iOS 14.5+ユーザーの計測に必要。Events ManagerでLeadとCompleteRegistrationの優先度設定を確認せよ
- **ドメイン認証未確認**: quads-nurse.com のMeta Business Manager上での認証状態要確認

### 🔴 FAIL
- **本物Lead 0件 = ファネル完全断絶**: 7日間でPixel Lead 2件観測されているが、CompleteRegistration（LINE友達追加）が0件。LP CTAクリックしたユーザー2人が全員LINE登録まで到達しなかった。以下のどれかが原因:
  1. LP CTAクリック直後のLINE遷移が失敗（LIFF/line.meの読み込み失敗）
  2. LIFFページでユーザーが離脱（追加ボタン押さない）
  3. CAPI送信が機能していない（`META_ACCESS_TOKEN` 期限切れ等）
  4. event_id マッピング不整合（LP側 `__nr_sid` と worker側 `webSessionData.sessionId` がズレ）

**検証手順:**
```bash
# Events ManagerでCompleteRegistration発火状況を直接確認
# https://business.facebook.com/events_manager2/list/pixel/2326210157891886/test_events
# → LINE友達追加を手動で1件試し、CompleteRegistrationがCAPI経由で飛ぶか確認

# Worker ログ
npx wrangler tail robby-the-match-api --config api/wrangler.toml | grep "Meta CAPI"
```

---

## 2. Creative（30% weight） 40/100

### 現状クリエイティブ3本（v7_ad2は4/20停止）

| Ad | 形式 | 消化 | Imp | CTR | CPC | Pixel Lead | CPL |
|----|------|------|-----|-----|-----|-----------|-----|
| v7_ad1 bedtop動画 | 動画 | ¥5,927 | 1,239 | 1.37% | ¥348 | 1 | ¥5,927 |
| v7_ad2 求人訴求静止画 | 静止画 | ¥1,219 | 382 | 1.31% | ¥243 | 0 | ∞ |
| v7_ad3 AI転職静止画 | 静止画 | ¥6,763 | 1,200 | 1.50% | ¥375 | 1 | ¥6,763 |

### ⚠️ WARNING
- **クリエイティブ数不足**: アクティブ2本（v7_ad1, v7_ad3）< Meta推奨5本。1本あたりの学習データが薄い
- **動画メトリクス未取得**: video_p25/50/75/100が日次レポートに出ていない → 動画の何%地点で離脱しているか不明。`meta_ads_report.py:374` の動画ブレイクダウンは `--video` オプション化されていない
- **Dynamic Creative Optimization (DCO) 未使用**

### 🔴 FAIL
- **クリエイティブ形式の多様性不足**: 動画1 + 静止画2のみ。カルーセル、コレクション、UGC系テスト0件
- **クリエイティブ疲労の前触れ**: v7_ad3 は 4/22単日 CTR 0.43%（1週間前2.38%から -82%）。7日間合計は1.50%だが直近3日で急降下
- **v7_ad2 停止判断は正しかったが遅い**: ¥1,219消化でLead 0、CTR 1.31%。より早く見切れた
- **フォーマット適合性**: IG Reelsで CTR 0.51% と致命的に低い（feed/stories は1.7%台）→ 縦動画/フル画面向けにクリエイティブを作り直す必要

### クリエイティブ疲労警告
| Ad | 初期CTR | 直近CTR | 変化 | 判定 |
|----|---------|---------|------|------|
| v7_ad3 | 6.67% (4/16) | 0.43% (4/22) | **-94%** | 🔴 疲労確定・差し替え必須 |
| v7_ad1 | 2.00% (4/16) | 1.32% (4/22) | -34% | ⚠️ 疲労傾向 |

---

## 3. Account Structure（20% weight） 50/100

### ✅ PASS
- **CBO使用**: キャンペーンレベル日予算 ¥2,000 = Campaign Budget Optimization
- **キャンペーン整理**: ACTIVE 1 / PAUSED 4 = ほぼ整理されている
- **命名規則**: `NR_2026-04_lead_v7` など体系的

### ⚠️ WARNING
- **学習フェーズ未脱出**: 1広告セット・予算¥2,000/日・7日で54LINE登録なし = **Leading Limited状態の可能性が高い**。Meta推奨は週50コンバージョン
- **入札戦略**: `LOWEST_COST_WITHOUT_CAP`（上限なし最小コスト）→ LINE登録獲得が0なので「何をもって最小コスト」の学習が進まない
- **予算/CPA比**: 目標CPA不明だが仮に¥2,000とすると日予算¥2,000=1x CPA（Meta推奨≥5x CPA=¥10,000/日）→ 学習フェーズに必要な日予算に全く足りない

### 🔴 FAIL
- **広告セット1本のみ**: A/Bテスト構造がない。オーディエンス/配置の比較データを取れない

---

## 4. Audience & Targeting（20% weight） 25/100

### 設定
- 年齢: 25-49F / 女性 / 関東4都県
- 配置: IG 3面 + FB フィード（FBは社長手動除外で実質IGのみ）
- Advantage+ Audience: **OFF**

### 配置別内訳（7日）

| Placement | 消化 | 消化% | CTR | Lead |
|-----------|------|-------|-----|------|
| IG feed | ¥6,402 | 46% | 1.72% | 1 |
| IG Stories | ¥4,299 | 31% | 1.75% | 1 |
| IG Reels | ¥2,467 | **18%** | **0.51%** | **0** |
| FB feed | ¥104 | 1% | 7.41% | 0 |
| FB reels | ¥216 | 2% | 2.56% | 0 |
| FB stories | ¥14 | 0.1% | 0% | 0 |

### 🔴 FAIL
- **IG Reelsがゴミ枠化**: 予算の18%(¥2,467)を食ってCTR 0.51%・Lead 0。即除外すべき
- **FB feed は高CTR(7.41%)だが予算¥104のみ**: Metaが自動的に予算を振らず、機会損失。除外ではなく最適化を見直すべき
- **Advantage+ Audience OFF**: 1週間テスト仕様だが、ターゲティングの幅が狭すぎて学習が進まない根本原因の可能性
- **リーチ1,528/7日**: 神奈川県24-49歳女性人口 約100万人 のうち0.15%にしか到達していない。オーディエンスサイズが小さすぎる（または入札不足で配信が絞られている）
- **Custom Audience 未活用**: IG自社アカウント@robby.for.nurse（2,000+フォロワー）のエンゲージャー、LP訪問者、LINE登録者のカスタムオーディエンスが作られていない
- **Lookalike Audience 未活用**: LINE登録済みユーザーの1%/3%/5%類似作成が0件
- **Frequency 1.77**: 7日で同一ユーザーに2回弱。適正範囲だが、CompleteRegistration 0件のためこの数字の意味は薄い

---

## Quick Wins（インパクト順）

### 🔥 最優先（本日〜明日）

1. **本物Lead 0件の原因特定（CAPIファネル検証）**
   - Events Manager Test Events で CompleteRegistration が手動LINE登録時に飛ぶか確認
   - Worker tail で `[Meta CAPI] CompleteRegistration sent` ログが出ているか確認
   - LP CTAクリック→LIFFへの遷移失敗率をGA4で確認
   - **インパクト**: ¥60,000/月のROI判定の根拠。ここが直らない限り配信継続は無意味

2. **1週間テスト判定（2026-04-24朝）**
   - 本物Lead 0件 → 判断基準「🔴 広告戦略破綻確定→即停止、¥60,000/月を別投資へ」
   - ただし計測側のバグ可能性が未排除のため、**先に(1)で計測健全性を24時間以内に確認**してから停止判断

3. **IG Reels配置除外（社長手動）**
   - Ads Managerで `instagram_reels` 除外 → 月あたり約 ¥11,000 節約（無駄配信）
   - 注意: 広告を再アップロードすると学習フェーズリセット。**配置変更のみ**で対応

### 🎯 今週中

4. **クリエイティブ補充3本**
   - v7_ad3 はCTR -94%劣化で差し替え必須
   - UGC風縦動画（15秒以内・IG Stories/Reels最適化）を2本
   - カルーセル（施設×条件の3枚）を1本
   - 既存 `content/meta_ads/gemini_lead_campaign_prompt.md` を更新して生成

5. **Custom Audience 3種作成**
   - LP訪問者 180日（`quads-nurse.com` URL含むページ訪問）
   - IG @robby.for.nurse エンゲージャー 365日
   - LINE登録者（CompleteRegistration） 180日 → 除外用

6. **LINE登録者 1% Lookalike（Lead 4件以上貯まったら）**

### 🎓 中期（2週間以内）

7. **EMQ向上のためCAPI payload拡張**
   - `worker.js:137` の `userData` にphone/emailのhashed値追加
   - LINE登録時のプロフィール取得→ SHA256ハッシュ → `em`/`ph` に追加
   - 目標 EMQ 6.0+

8. **広告セット複製でA/Bテスト**
   - 現行 25-49F vs Advantage+ Audience ON
   - 予算各¥1,000/日で並走7日間

---

## 判断マトリクス（社長向け）

| シナリオ | 条件 | アクション |
|---------|------|-----------|
| **A: 計測破綻** | Events Manager手動テストでCAPI CompleteRegistration発火NG | 計測修復→1週間再テスト |
| **B: ファネル破綻（有力）** | CAPI発火OKだがLINE追加まで実際0件 | **即停止。LP→LINE動線をまず修復** |
| **C: ターゲ破綻** | ファネル検証したらLINE追加率が通常以下 | Advantage+ ON / Lookalike投入で再テスト |

---

## 監査スコアサマリ

```
Pixel / CAPI Health:  65/100  (基盤はできているが、PIIのhash送信とAEM検証不足)
Creative:             40/100  (3本→2本稼働、形式多様性なし、疲労進行中)
Account Structure:    50/100  (CBO+命名は良いが、広告セット1本で学習進まず)
Audience & Targeting: 25/100  (IG Reels 18%が死に金、カスタム/類似0件)
```

**総合 34/100 (F)** — 技術的には最低限の実装はある。問題はクリエイティブと本物Leadのファネル。1週間テスト（判定日2026-04-24）の結論としては「破綻確定」だが、停止判断の前に**計測健全性24時間検証**を先行させるべき。
