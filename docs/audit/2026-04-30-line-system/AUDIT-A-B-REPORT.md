# LINE Bot 設計文書 監査レポート（A群・B群）

**作成日**: 2026-04-30
**対象**: LINE_BOT_SYSTEM.md / MASTER-DESIGN-v2.md / aica-conversation-flow.md
**原則**: 実装が真。文書を実装に合わせる。実装側の問題は別チケットで報告。

---

## サマリ（3行）

1. **数値は全部古い or 間違い**: worker.js行数2倍、phase状態数1.65倍、D1件数バラバラ、緊急ワード3定義混在
2. **重大発見**: aica-conversation-flow.md は `candidates` D1テーブル前提だが**そのテーブルは存在しない**（KVのみ）
3. **コンプラ事案**: 「神奈川クリニック賞与平均2.8〜3.5ヶ月（厚労省R5賃金構造基本統計調査）」は**該当統計が公式に存在しない疑い**。要外部検証

---

## A群: 数値・カウント実態（実装側の事実）

| # | 項目 | 文書記載 | 実測値 | 差分 |
|---|---|---|---|---|
| A1 | phase状態数 | 20状態（LINE_BOT_SYSTEM.md:67） | **33状態** | +13 |
| A2 | worker.js行数 | 7,433行（LINE_BOT_SYSTEM.md:14, 394） | **15,702行** | 2.11倍 |
| A3a | facilities D1件数 | 17,913件（LINE_BOT_SYSTEM.md:15, 150）<br>84,613件（MASTER-DESIGN-v2:21, 494） | **89,674件** | LINE文書の5.0倍 / MASTER+5,061 |
| A3b | jobs D1件数 | 3,268件（LINE_BOT_SYSTEM.md:151）<br>21,149件（MASTER-DESIGN-v2:21, 493） | **3,438件** | LINE文書+170 / **MASTER -17,711（深刻）** |
| A3c | candidates D1件数 | aica-conversation-flow全編で前提化 | **テーブル不存在** | 設計と実装の根本ズレ |
| A4 | EMERGENCY語数 | 8語（MASTER-DESIGN-v2:101, 622）<br>14語（aica-conversation-flow.md:1171） | **3定義混在**（後述） | 実装側で要統一 |
| A5 | リッチメニュー実体数 | 4種詳述（LINE_BOT_SYSTEM.md §11） | **2種**（メイン + Default_v3） | HEARING/MATCHED/HANDOFFは未作成 |
| A6 | CAPI Lead送信成功率 | 「不安定」（LINE_BOT_SYSTEM.md §17） | **要手動確認**（後述） | Events Manager直視必要 |
| A7 | LINE OA フォロワー/DAU | KPI根拠 | **要手動確認** | LINE Official Account Manager必要 |

### A4 詳細: 緊急キーワードの実装混在

実装側に **3つの異なる定義** が同居:

| 場所 | 定数名 | 語数 | 内訳 |
|---|---|---|---|
| `api/worker.js:291` | `AICA_EMERGENCY_KEYWORDS` | **12語** | 死にたい/自殺/消えたい/殺したい/パワハラ/セクハラ/モラハラ/いじめ/ハラスメント/DV/ドメスティック/虐待 |
| `api/worker.js:10973` | `EMERGENCY_KEYWORDS`（ローカル再定義） | **8語** | 死にたい/自殺/もう無理/パワハラ/いじめ/セクハラ/暴力/被災 |
| `api-aica/src/prompts.js:186` | `EMERGENCY_KEYWORDS` | **14語** | 上記12 + 労基/弁護士 |

→ これは**実装バグ**。別チケットで統一が必要。文書側はその統一結果に合わせる。

### A6 補足: CAPIの状態確認

- Meta Graph API直接呼び出しは認証範囲外で取得困難
- 直近30日のCAPIイベント数・Match Quality・サーバー送信エラー率は **Events Manager UI**でのみ確認可能
- **社長アクション**: business.facebook.com/events_manager2 → ピクセル `2326210157891886` → 「概要」タブ
- 現状は4/23以降の[Meta CAPI クロスドメイン計測修復](../../../.claude/projects/-Users-robby2/memory/project_meta_capi_fix.md)で改善済みのはずだが**実測未確認**

### A7 補足: LINE OA データ

- LINE Official Account Manager（manager.line.biz）でのみ取得可
- 友だち数・ブロック数・直近DAUは画面読み取りまたはScraping必要
- **社長アクション**: 数値をSlackに貼ってもらえれば反映可

---

## B群: 自己矛盾の整理

| # | 矛盾内容 | 解決方針 |
|---|---|---|
| B1 | aica §0-1「人間介入は2箇所のみ」（A契約・請求 / B緊急時）vs §3-2「人と話したい」明示時もハンドオフ | §0-1を**3箇所**に修正、または「(C) ユーザー明示要求」を例外として追記 |
| B2 | aica §3-1「7日無応答→cron停止」「14日無応答→PAUSED」の**主体不明**（誰がPAUSEDセットするか） | 「14日無応答→cronが`phase=PAUSED`にセット（現実装：cron-resume.js）」と主体明記 |
| B3 | LINE_BOT_SYSTEM §13 「D1接続失敗→FACILITY_DATABASE（212件）にフォールバック」= **正常時89,674件→失敗時212件で99.76%欠損** | これは**設計意図**（DB全停止時の最低限フォールバック）と推定。文書に「フォールバックは緊急時のみで通常はD1利用」を明記 |
| B4 | LINE_BOT_SYSTEM §11 リッチメニュー4種詳述 vs §17「未作成」| §11を「**設計（4種想定）**」に、§17を「**現状（2種実装、HEARING/MATCHED/HANDOFFは未作成）**」に書き分け |

---

## 提案 git diff パッチ（A・B群）

### Patch 1: LINE_BOT_SYSTEM.md（A1, A2, A3a, A3b, B3, B4）

```diff
--- a/docs/LINE_BOT_SYSTEM.md
+++ b/docs/LINE_BOT_SYSTEM.md
@@ -12,3 +12,3 @@
-- **バックエンド**: Cloudflare Worker（`worker.js` 約7,400行）
+- **バックエンド**: Cloudflare Worker（`worker.js` 約15,700行 / 2026-04-30 計測）
@@ -15,1 +15,1 @@
-- **データ**: Cloudflare KV（セッション管理）+ D1（施設DB 17,913件）
+- **データ**: Cloudflare KV（セッション管理）+ D1（facilities 89,674件 / jobs 3,438件 / 2026-04-30 計測）
@@ -67,1 +67,1 @@
-## 4. 会話フェーズ（20状態）
+## 4. 会話フェーズ（33状態）
@@ -149,3 +149,3 @@
-- **FACILITY_DATABASE**: worker_facilities.jsに埋め込み（212施設・手動調査）
-- **D1 Database**: 17,913施設（厚労省データ）
-- **ハローワーク求人**: data/hellowork_nurse_jobs.json（毎朝06:30自動取得、3,268件+）
+- **D1 Database（主データソース）**: facilities 89,674件 / jobs 3,438件（厚労省+ハローワーク統合）
+- **FACILITY_DATABASE（フォールバック用）**: worker_facilities.jsに埋め込み（212施設・手動調査）。**通常運用ではD1を参照、D1全停止時の緊急フォールバックのみ使用**
+- **ハローワーク求人**: 毎朝06:30 cron で D1.jobs にUPSERT（hellowork_to_d1.py）
@@ -345,1 +345,1 @@
-| D1 DB接続失敗 | FACILITY_DATABASE（インメモリ212件）にフォールバック |
+| D1 DB接続失敗 | FACILITY_DATABASE（インメモリ212件）にフォールバック ※99.76%データ欠損するため緊急時のみ |
@@ -394,1 +394,1 @@
-| `api/worker.js` | 7,433 | メインWorker（Webhook, マッチング, ハンドオフ, 全API） |
+| `api/worker.js` | 15,702 | メインWorker（Webhook, AICA全フェーズ, マッチング, ハンドオフ, 全API） |
```

§11リッチメニュー詳述と§17未作成の整合（B4）:

```diff
@@ -<§11 開始位置>
-## 11. リッチメニュー（4状態）
+## 11. リッチメニュー（設計4状態 / 実装2状態）
+
+**現状（2026-04-30）**: LINE上の実体は2種（メインメニュー + NurseLobby_Default_v3）。HEARING/MATCHED/HANDOFFは**未作成**（§17参照）。以下は設計意図。
+
 （以下既存内容）
```

---

### Patch 2: MASTER-DESIGN-v2.md（A3a, A3b, A4） — **v3で置き換え推奨だが暫定パッチ**

```diff
--- a/docs/audit/2026-04-28-line-system/MASTER-DESIGN-v2.md
+++ b/docs/audit/2026-04-28-line-system/MASTER-DESIGN-v2.md
@@ -21,1 +21,1 @@
-5. **Data-Backed Replies**: AIは施設DB（84,613件）+求人DB（21,149件）+ハローワーク差分を参照して具体数字で答える
+5. **Data-Backed Replies**: AIは施設DB（89,674件）+求人DB（3,438件 ※2026-04-30計測値）+ハローワーク差分を参照して具体数字で答える
@@ -101,1 +101,1 @@
-2. **EMERGENCY検出**: 8語の緊急キーワード（「死にたい」「パワハラ」等）
+2. **EMERGENCY検出**: 12語の緊急キーワード（worker.js:291 AICA_EMERGENCY_KEYWORDS）
@@ -493,2 +493,2 @@
-│ +humanReplied│  │  21,149 jobs      │  │  ・LINE Push     │
-│ At (新)      │  │  84,613 facilities│  │  ・LINE Content  │
+│ +humanReplied│  │   3,438 jobs      │  │  ・LINE Push     │
+│ At (新)      │  │  89,674 facilities│  │  ・LINE Content  │
@@ -622,1 +622,1 @@
-| EMERGENCY検出漏れ | 重大事案 | 8語+追加学習、Slack通知3重化 |
+| EMERGENCY検出漏れ | 重大事案 | 12語+追加学習、Slack通知3重化 |
```

**注**: jobs件数が **21,149→3,438** と激減している。これは MASTER-DESIGN-v2 作成時（4/28）から jobs テーブルがクリーンアップされた可能性。要確認。

---

### Patch 3: aica-conversation-flow.md（A4, B1, B2）

```diff
--- a/docs/aica-conversation-flow.md
+++ b/docs/aica-conversation-flow.md
@@ -14,4 +14,5 @@
 - 人間が出るのは 2 箇所のみ:
   - **(A) 契約・請求**（法務・商流）
   - **(B) 緊急時**（自殺示唆・パワハラ等 14キーワード検出）
+  - **(C) ユーザー明示要求**（「人と話したい」を明示的に押した時、§3-2参照）
@@ -1153,3 +1153,3 @@
-| 7日無応答 | 沈黙モード（それ以降cronは停止） |
-| 14日無応答 | `candidates.phase = PAUSED` にセット |
+| 7日無応答 | 沈黙モード（cron `cron-resume.js` がそれ以降の Push を停止） |
+| 14日無応答 | cron `cron-resume.js` が `phase = PAUSED` にセット ※現状candidatesテーブル未実装のためKV側で代替 |
@@ -1171,1 +1171,1 @@
-14キーワードのいずれかを検出 → いのちの電話案内 + Slack `#aica-urgent` に通知 → BOT沈黙
+12キーワードのいずれかを検出（worker.js:291 AICA_EMERGENCY_KEYWORDS）→ 専門窓口案内 + Slack緊急通知 → BOT沈黙
+※実装側で `worker.js:291`(12語) と `worker.js:10973`(8語) と `api-aica/prompts.js:186`(14語) の3定義が混在。統一する別チケット起票予定
```

---

## 別チケット起票が必要な実装側の問題

| ID | 問題 | 影響度 |
|---|---|---|
| ISSUE-EMERG-1 | 緊急ワード定義が3箇所に分散・不一致（worker.js:291 / worker.js:10973 / api-aica/prompts.js:186） | 🔴 重大（取りこぼし or 過検知） |
| ISSUE-CANDIDATES-1 | aica-conversation-flow.md は `candidates` D1テーブル前提だが **テーブル不存在**（KV運用） | 🟡 設計-実装の根本ズレ |
| ISSUE-RICHMENU-1 | RICH_MENU_HEARING/MATCHED/HANDOFF が wrangler secret に未設定（DEFAULT のみ）→ phase別切替が機能していない可能性 | 🟡 UX影響 |
| ISSUE-WORKER-BLOAT | worker.js 15,702行（一体型）。AICA分離 or モジュール分割の検討が必要 | 🟢 保守性 |

---

## E4 緊急コンプラ確認: 厚労省R5統計の実在性

### 該当箇所
- `aica-conversation-flow.md:832-833`
- `new-ai-career-advisor-spec.md:508-509`

```
◇ 神奈川クリニック賞与平均: 2.8〜3.5ヶ月
  （厚労省R5賃金構造基本統計調査）
```

### 検証結果
**この統計は公式に存在しない疑いが濃厚**。理由:

1. 厚労省「**令和5年賃金構造基本統計調査**」の公式分類:
   - 産業中分類: 「医療業」「医療,福祉」レベル
   - 都道府県別はあるが「神奈川 × クリニック × 看護師 × 賞与月数」という細粒度クロス集計は**公開されていない**
2. 同調査の「年間賞与その他特別給与額」は**金額（円）**で報告。「2.8〜3.5ヶ月」のような月数表現は同調査の標準形式ではない
3. 「クリニック」という分類自体、賃金構造基本統計調査では**存在しない**（医療業の中に診療所/病院の区分はあるが、「クリニック」は俗称）

### 推奨アクション

🚨 **即時対応**:
1. 該当2文書から該当文言を**削除**（または「※暫定参考値、要出典確認」と明記）
2. 実装側（gpt-4oプロンプト）に同文言が含まれていないかgrep
3. 既にユーザーに送信した履歴があれば全件確認

```bash
# grep対象
grep -rn "神奈川クリニック賞与" ~/robby-the-match/
grep -rn "2.8〜3.5ヶ月" ~/robby-the-match/
grep -rn "2.8-3.5ヶ月" ~/robby-the-match/
```

→ E5（個人情報拡大）と合わせて E群レポートで詳述。

---

## 次の推奨アクション

1. **本レポートを社長確認** → A・Bパッチ適用OKか判断
2. **実装側ISSUE-EMERG-1** を最優先で修正（緊急ワード統一）
3. **E4の文言削除** を即実施（コンプラ事故防止）
4. C群（設計判断）レポートを次に作成
5. A6（CAPI状態）・A7（LINE OA数値）は社長から数値共有してもらえれば反映
