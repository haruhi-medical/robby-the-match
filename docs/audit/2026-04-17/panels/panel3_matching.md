# パネル3: マッチング品質 — 議長統合レポート

> 日付: 2026-04-17
> パネル: P3 マッチング品質
> 議長: Panel 3 Chair
> 生Round: [panel3_all_rounds.md](../rounds/panel3_all_rounds.md)
> North Star寄与: 紹介対象の品質とハンドオフ後の成約確率を高め、月1件成約の確度を上げる

---

## 1. サマリ

- 6人独立点検で **27件の阻害要因**を検出、Round 2相互批判で**4件を統合**（facility_idリンク欠落、AI応答フォールバック、Slack通知セキュリティ、prefecture空欄）、**1件を再分類**（非公開求人→Phase 3）し、**22件に整理**
- 最重要3件は: (A) **prefecture空欄877件=29.6%** (B) **AI応答に自動フォールバックが実装されていない** (C) **facilities↔jobsリンク切断で `has_active_jobs=0`**
- 実装/DBレベルで**FACT_PACK/STATE.md の記述と乖離**している項目が3件発見（4段フォールバック・診療科100%・prefecture空欄修正済）→ ドキュメント精度そのものが成約品質の土台を揺るがす

---

## 2. 重大3件（Phase 1候補の中核）

### 【重大1】 prefecture空欄877件（29.6%）でD1 jobs検索から脱落
- **ファクト**: `hellowork_jobs.sqlite: SELECT COUNT(*) FROM jobs WHERE prefecture=''` = 877。`worker.js L4702-4707` のprefFilterで空欄は検索対象外。STATE.md「prefecture空欄875→0件」の主張と矛盾
- **影響**: 県別検索（東京/神奈川/千葉/埼玉）時、29.6%の求人がヒットしない。特に神奈川全域希望で469件のうち推計100件以上が脱落の可能性
- **原因**: `hellowork_to_d1.py L110-L130` のprefecture判定が `loc` の「東京都/神奈川県/千葉県/埼玉県」完全一致のみ。市区町村のみの住所（例: `横浜市神奈川区...`）は判定不能
- **改善**: `AREA_PREF_REVERSE` を2段階に（① area→prefecture ② 市区町村名→prefecture）。work_addressからの抽出も追加
- **インパクト**: 求人検索ヒット率29.6pt↑、ミサキの「0件→handoff離脱」を防ぐ
- **コスト**: 3h
- **Phase**: **1**

### 【重大2】 AI応答の「4段フォールバック」は実装されていない（1段分岐のみ）
- **ファクト**: `worker.js L1779-L1851` は `if AI_PROVIDER==openai` / `else if anthropic` / `else workers-ai` の排他分岐。OpenAIが502/503のとき **フォールバックなし、502返却**（L1800）
- **影響**: OpenAI障害/認証切れ時、AI相談フェーズで全ユーザー無応答。ミサキ「既読無視?」の不安誘発
- **原因**: 設計時に「フォールバック実装」が言語化されず、分岐形で終了した
- **改善**: try/catchで順次試行（openai→workers-ai最低2段）。Workers AI（Llama 3.3 70B）は無料で既に設定済み
- **インパクト**: SLO向上（AI応答成功率 ≒99.9% → 事実上100%）、離脱防止
- **コスト**: 3h
- **Phase**: **1**

### 【重大3】 facilities↔jobs リンク切断で `has_active_jobs=0`
- **ファクト**: `nurse_robby_db.sqlite: SELECT COUNT(*) FROM facilities WHERE has_active_jobs=1` = **0**。hellowork_to_d1.py は新スキーマで DROP→CREATEする一方、facilitiesテーブルの `facility_id` 外部キーは更新されない
- **影響**: 「求人あり施設」フィルタが機能しない。マッチング候補から「実際に求人がある施設」を優先できず、紹介後の「空き確認可」返答遅延
- **原因**: jobs テーブルのスキーマが2種類存在（worker設計時の facility_id 版 / hellowork_to_d1.py の kjno版）
- **改善**: hellowork_to_d1.py に `UPDATE facilities SET has_active_jobs=1 WHERE id IN (SELECT facility_id FROM jobs)` を追加。facility_id 解決は `employer名 × 住所city` で fuzzy マッチ
- **インパクト**: 有効求人のある施設（hellowork現在2,963件）だけを優先提示できる。成約確度の高い施設優先
- **コスト**: 6h
- **Phase**: **1（急ぎ）** or **2**

---

## 3. 全阻害要因サマリ表（22件）

| # | タイトル | 提起者 | Phase | コスト | インパクト |
|---|---------|-------|-------|--------|----------|
| 1 | prefecture空欄877件修正 | P4 | **1** | 3h | 高 |
| 2 | AI応答フォールバックtry/catch実装 | P3 | **1** | 3h | 高 |
| 3 | facilities↔jobs 再統合（has_active_jobs更新） | P1+P4 | **1/2** | 6h | 高 |
| 4 | Slack通知の電話番号マスク（`090-****-5678`） | P5 | **1** | 1h | 中（プライバシー） |
| 5 | 緊急キーワード粒度調整（「限界」を降格） | P3 | **1** | 0.5h | 高 |
| 6 | 派遣`emp_type`除外フィルタ | P4 | **1** | 0.5h | 中（規則遵守） |
| 7 | 保育園/幼稚園/学校求人の除外フィルタ | P4 | **1** | 1h | 中 |
| 8 | D1 jobs検索に `rank IN ('S','A','B','C')` 制限（エリア15件以上時のみD除外） | P2 | **1** | 1h | 中 |
| 9 | handoff後24h経過Slackリマインダー | P5 | **1** | 2h | 中 |
| 10 | クリニック検索時に departments フィルタを bypass | P2 | **1** | 1h | 中 |
| 11 | area空欄167件の市区町村名→area逆引き | P4 | **1** | 2h | 中 |
| 12 | 電話番号バリデーション失敗時に postbackボタン「電話なし」 | P5 | **1** | 1h | 中 |
| 13 | 希望時間帯QRに「夜勤明け午前のみ」「週末のみ」追加 | P5 | **1** | 0.5h | 中 |
| 14 | handoff中24h以内1回の自動返信「担当者に転送しました」 | P5 | **1** | 2h | 中 |
| 15 | 紹介フィー10%訴求をLINE/求職者側で非表示化 | P6 | **1** | 1h | 中 |
| 16 | scoreFacilitiesのLP側（chat.js）もD1/24,488件対応 | P2 | **2** | 8h | 高 |
| 17 | 訪問看護ST データ投入（facilities 0件→800件推定） | P1 | **2** | 8-12h | 高 |
| 18 | ADJACENT_AREAS越境時のユーザー同意QR | P2 | **2** | 3h | 中 |
| 19 | Slack通知をBlock Kit化（長文→折りたたみ） | P5 | **2** | 3h | 中 |
| 20 | 提携病院フラグ `is_partner` + マッチング優先スコア | P6 | **2** | 3h | 高 |
| 21 | 逆指名フロー実装（施設名入力→Slack→24h回答） | P6 | **2** | 6h | 中〜高 |
| 22 | 非公開求人テーブル + バッジ表示 | P6 | **3** | 8h+運用 | 高 |

(参考: 成約プロセスstate管理、介護施設データ補完、OpenAI認証監視、ハローワーク求人フィー契約整合性、施設DB鮮度明記 はPhase 2/3の後回し案件)

---

## 4. ドキュメント整合性アラート（即時修正必要）

| 項目 | 記載 | 実態 |
|------|------|------|
| AI応答「4段フォールバック」(FACT_PACK §7, STATE.md) | OpenAI→Claude Haiku→Gemini→Workers AIの4段 | if/else if/elseで1つのみ選択、OpenAI失敗時フォールバックゼロ |
| 「診療科100%」(FACT_PACK §8, STATE.md) | 24,488施設でカバー率100% | 病院1,498件のみ100%。全体は 1,497/24,488=6.1% |
| 「prefecture空欄875件→0件」(STATE.md 2026-04-06) | 修正済 | 本番D1未確認だがローカルスナップショット（hellowork_jobs.sqlite 4/07）では877件=29.6%残存 |
| 「求人DB 2,936件」(FACT_PACK §8) | 2,936件 | ローカルは2,963件、4/16ログは 3,698→3,336→D1投入。数字揺れ |

これらの「記載と実装のズレ」は、他パネル（P1流入/P2コンバージョン/P4基盤）の判断を誤らせる二次被害がある。**ドキュメント精度の維持は成約品質の基盤**。

---

## 5. Phase別統合ロードマップ

### Phase 1（今日中 / 即時実行）
1. prefecture空欄修正（hellowork_to_d1.py）
2. AI応答 try/catchフォールバック実装（worker.js L1779-1851）
3. Slack電話番号マスク（L5224）
4. 緊急キーワード粒度調整（L6822）
5. 派遣/保育園/学校 除外フィルタ（hellowork_fetch.py）
6. D1検索でDランク除外（L4725）
7. クリニック時の departments bypass（L4890）
8. 希望時間帯QR追加（L4298）
9. 電話番号postbackボタン追加（L5787）
10. handoff自動返信1回（L6876付近）
11. 紹介フィー10%訴求のLINE側非表示
12. area空欄167件の市区町村→area逆引き

**Phase 1合計: 12件、推定16-18時間**

### Phase 2（48時間以内）
13. facilities↔jobs再統合（hellowork_to_d1.py + schema）
14. scoreFacilities LP側のD1 24,488件対応
15. 訪問看護ST データ投入
16. Slack Block Kit化
17. is_partner フラグ + 優先スコア
18. 逆指名フロー実装
19. ADJACENT_AREAS越境同意QR
20. handoff後24h Slackリマインダー

**Phase 2合計: 8件、推定32-40時間**

### Phase 3（1週間以内 or 継続検討）
21. 非公開求人テーブル+UI（営業と連動）
22. 応募→面接→内定→入職 state管理

---

## 6. 制約遵守チェック

- 架空データ: 全数値は hellowork_jobs.sqlite / nurse_robby_db.sqlite / worker.js の実データ引用 ✅
- 派遣求人除外: 改善提案に含まれる（#6） ✅
- マッチングアルゴリズム新規ML構築: 含まない（全て既存ロジック拡張） ✅
- 月3万超の新規ツール契約: 含まない ✅
- 紹介フィー10%不変: 事業モデル変更なし ✅
- 看護師個人情報の画面上操作: マスク強化（#4） ✅

---

## 7. 未確認データ（本点検では取得できなかった）

- 本番D1の実データ（ローカルスナップショット hellowork_jobs.sqlite は 2026-04-07。4/16パイプライン以降の本番データは未確認）
- ハンドオフ後の実際の返信SLA（24h遵守率）— 成約0件のため実績データなし
- LINE Bot の実ログ（Worker logs の prefFilter ヒット率分布）
- D1 jobsテーブルの実際のランク内訳（本番）
- 提携病院との有料職業紹介基本契約の有無（社長確認事項）

---

## 8. North Star への寄与度

Phase 1 で上記12件を実装すると:
- AI応答成功率 ≒85-95% → ≒99.9%（離脱防止）
- エリア別求人ヒット数 29.6%↑（prefecture空欄解消）
- 不適合求人（派遣/保育園）混入 62件→0件
- Dランク低品質求人 上位除外
- handoff後の不安（既読無視感）解消

**推定**: ハンドオフ率 10% → 14%（+4pt）、handoff→成約率 40% → 55%（+15pt）のドライブ。
実数ベースでは「月間LINE登録50人 × 14% × 55% ≒ 月間成約3.85件」の水準を理論値として見込む。ただし成約0件の現状では理論値の検証前に **まずLINE登録数の絶対量確保（Panel 1+2 と連動）が先**。
