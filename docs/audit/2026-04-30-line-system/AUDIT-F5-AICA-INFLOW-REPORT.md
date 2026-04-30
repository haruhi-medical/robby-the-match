# Patch 5: AICA流入経路調査レポート

**実施日**: 2026-04-30
**対象期間**: 直近30日（2026-04-01〜04-30）
**実ユーザー数**: 15名（QA監査テスト除外、`user_hash NOT LIKE 'U_TEST_%'`）

---

## サマリ（3行）

1. **AICA到達は1名のみ（社長本人テスト疑い）**。残14名は完全バイパス → AICA流入率 約7%
2. **真の原因は2つ**: ①LP診断経由が9/14（64%）で intake_qual から始まる ②直接follow組5/14（36%）も il_area へ流れる
3. **IL→AICAブリッジ（4/29実装）は実ユーザーで発火0件**。実ユーザーがボタン以外の自由文を送らない設計だから。**Patch 2 Phase B（4/30 全員AICA起動）が真の解**

---

## 3-1. 実ユーザー15名のフェーズ遷移パス

| ユーザー | 初回phase | 経路 | 到達フェーズ | 判定 |
|---|---|---|---|---|
| U7e23b53d103 | welcome | aica_turn1 / il_area / handoff... 461ev | **AICA到達** | ⚠️社長本人テスト疑い |
| U238ad7b6ffb | **intake_qual** | intake_age→postal→handoff→il_facility_type 15ev | バイパス | LP診断経由 |
| U35b16c157b8 | welcome | il_area→subarea→facility_type→workstyle→urgency→info_detour 19ev | バイパス | 直接follow組 |
| U3dac5c67f5c | **intake_qual** | intake_age→postal→handoff→il_facility_type 6ev | バイパス | LP診断経由 |
| U3fd0f296cd3 | welcome | welcome 1ev | バイパス | 即離脱 |
| U774791576ba | **intake_qual** | intake_age→postal→handoff 4ev | バイパス | LP診断経由 |
| U7edff5f6fd2 | welcome | il_area 3ev | バイパス | 直接follow組 |
| U80dbb77e5c4 | **intake_qual** | il_area 2ev | バイパス | LP診断経由 |
| U9963e248ba5 | welcome | il_area→subarea 3ev | バイパス | 直接follow組 |
| Ua3afee1a0a6 | **intake_qual** | il_area→subarea→facility_type→workstyle→urgency→info_detour 7ev | バイパス | LP診断経由 |
| Ua3bf4aad557 | **intake_qual** | il_facility_type→workstyle→urgency→matching_preview→rm_resume_start 7ev | バイパス | LP診断経由 |
| Uabfc1f44ec8 | (詳細別途) | 66ev welcome系 | バイパス | 直接follow組 |
| Ub4c1a131703 | **intake_qual** | intake_age→postal→handoff→il_area→subarea 13ev | バイパス | LP診断経由 |
| Ub62c74be1bb | **intake_qual** | intake_age→postal→handoff→il_facility_type→workstyle→urgency 32ev | バイパス | LP診断経由 |
| Ud8dab6f2b59 | **intake_qual** | intake_age→postal→handoff→il_facility_type→workstyle→urgency 9ev | バイパス | LP診断経由 |

### 初回フェーズ分布（社長本人除外、14名）

| 初回phase | 件数 | 比率 | 経路 |
|---|---|---|---|
| **intake_qual** | **9名** | **64%** | LP診断（chat.js）→LINE follow → intake_qual から始まる |
| **welcome** | **5名** | **36%** | 直接LINE友だち追加 → welcome → il_area 系へ |

→ どちらも AICA をバイパスする経路が支配的だった（4/30 Phase B 修正以前）。

---

## 3-2. 流入経路の分類と AICA到達率（4/30 Phase B 修正前）

| 分類 | 推定経路 | 件数 | AICA到達率 |
|---|---|---|---|
| LP診断完了→friend follow | shindan complete → intake_qual | 9名 | **0%** |
| 直接友だち追加 (welcome) | follow → il_area / il_subarea | 5名 | **0%** |
| 自由テキスト初発（感情系） | IL→AICAブリッジ | **0名** | (発火せず) |
| 社長テスト | aica_turn1直接 | 1名 | 100% |

---

## 3-3. IL→AICAブリッジ（4/29実装）の発火状況

```sql
SELECT COUNT(*) FROM phase_transitions
WHERE event_type = 'il_emotional_bridge'
  AND user_hash NOT LIKE 'U_TEST_%';
-- 結果: 0件
```

### 原因分析
1. **実ユーザーは自由テキストを送らない**: ボタン操作（postback）が支配的
2. ブリッジは「IL phase × 感情キーワード10文字以上」で発火するが、実ユーザーは IL phase でボタン押すだけで先に進む
3. 「もう本当に夜勤がきつくて限界です」のような自由文が来ない設計＝送る機会がない

→ ブリッジは設計として正しいが、**メイン解決策にはならない**。緊急時の保険として機能する程度。

---

## 3-4. ウェルカム文言・リッチメニュー導線の現状

### 現状（4/30 Phase B 修正後）
```javascript
// follow event handler (worker.js:9491)
{
  entry.welcomeSource = entry.welcomeSource || (preloadedCtx ? 'shindan' : 'none');
  entry.phase = "aica_turn1";  // ← 全員AICA起動
  ...
  await lineReply(event.replyToken, [{
    type: "text",
    text: aicaBuildWelcomeMessage(entry.aicaDisplayName),
  }], channelAccessToken);
}
```

### Welcomeメッセージ内容（aicaBuildWelcomeMessage）
```
こんばんは、{displayName}さん。
ナースロビーAIキャリアアドバイザーです。

私はAIです。
24時間いつでも、誰にも知られずに
お仕事のお話を伺えます。

最大4つの質問で、あなたの「本当に必要な条件」を
整理した後、具体的な求人をご提案します。

今、お仕事で気になっていることを、
一言で言うとどのようなことですか？
```

→ ボタンなし、自由文を促す設計。LINE Botの操作方式（ボタン主体）と乖離。

### リッチメニューの現状
- **2種のみ実装**: メインメニュー + Default_v3
- HEARING / MATCHED / HANDOFF は未作成
- DEFAULTのアクション定義は不明（要LINE Manager確認）

---

## 3-5. 改善案A/B/C/D 比較

| 案 | 内容 | 工数 | 期待AICA流入率 | リスク |
|---|---|---|---|---|
| **(A) Welcome文言再設計** | 「最大4問で…」を絞り込み、QuickReply 1個追加（「話を始める」ボタン） | 半日 | 90%+ | 低 |
| **(B) リッチメニュー4種完成** | HEARING/MATCHED/HANDOFF を作成 + phase連動 | 1.5日 | 既流入後の継続UX改善（流入率には影響少） | 中 |
| **(C) AICA直行ルート新設** | 全postbackから「いったんAICA経由」のラッパー | 1日 | 100%（過剰、既存資産を無駄にする可能性） | 中-高 |
| **(D) SNS流入時の自動AICA起動** | source=tiktok/instagram/meta_ads 時にwelcome後即TURN1へ | 半日 | SNS経由ユーザーは100% | 低（source計測修正必要） |

### 重要な前提
**Patch 2 Phase B（4/30 デプロイ済）で既に「全ユーザーaica_turn1起動」が実装されている**。

つまり (C) は既に実装済みに近い状態。残課題は:

1. (A) Welcome文言で「自由文を促す」UXを補強（ユーザーが何書いていいか迷う問題）
2. (B) リッチメニューでAICAバイパス導線を防ぐ
3. (D) source計測タグの修復（現状 source=none が14/14名）

### 推奨

**A + D の組み合わせ（合計1日工数）**

理由:
- Phase B でAICA起動は実装済 → 残るUX問題は「welcome後に何を書けばよいか分からない」だけ
- source計測修復で流入経路を正確に把握 → 改善PDCAが回る
- (C) は過剰実装、(B) は流入率改善ではなく継続UX改善なので別タスク

---

## 3-6. F1反映の確認

### v3.1まで誤って書かれていた数字

| 旧記載 | 実態 |
|---|---|
| 「il_facility_type→il_workstyle 2.0%」 | テスト混入。実ユーザー70%通過 |
| 「TURN1→matching 1.18%」 | 実ユーザーTURN1到達は1名のみ。全体ファネルに値しない |
| 「中盤離脱が最重要課題」 | 誤り。真の問題は AICA流入の不在 |

### 真の課題（v3.3で確定）

1. 🔴 **AICA流入率 約7%（15名中1名）** ← Phase B（4/30）で改善見込み
2. 🔴 **handoff後ロスト 53%（15名中8名がhandoff）** ← Phase A/B/C で対処済
3. 🟡 **source計測タグの不在** ← 流入経路が把握不能（要修復）
4. 🟡 **IL→AICAブリッジ発火0件** ← 設計は正しいが実ユーザー使用なし

---

## 3-7. 改善実装の優先順位

### P0（今すぐ・Phase B 効果測定 + Patch 6 着手判断）
- [ ] Phase B 効果測定: 5/1〜5/3 の実ユーザーで aica_turn1 起動率 100% を確認
- [ ] (A) Welcome文言再設計（QuickReply追加）

### P1（来週）
- [ ] (D) source計測タグ修復（welcomeSource を phase_transitions.source に正しく書き込み）
- [ ] (B) リッチメニュー4種完成

### P2（次月以降）
- [ ] AICA運用が安定したら (B) リッチメニューでさらなる継続UX改善

---

## 3-8. 社長アクション項目

- [ ] 上記推奨案 (A) + (D) で着手OKか
- [ ] (C) AICA直行ラッパーは Phase B で実質達成、不要と判断OKか
- [ ] (B) リッチメニュー作成のデザイン承認

---

**END OF REPORT**
