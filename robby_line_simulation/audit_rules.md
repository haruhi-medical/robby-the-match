# 監視役（Auditor）監査ルール

## 監査項目
1. ケースIDの欠番・重複確認
2. 47都道府県のカバー確認
3. 各都道府県最低4件の確認
4. 各Worker 50件の確認
5. 実行証跡が薄いケースの差し戻し
6. 焼き直しケースの検知
7. failure_category 未設定ケースの差し戻し
8. severity 未設定ケースの差し戻し
9. retry_required の妥当性確認
10. 全条件充足まで完了承認しない

## 差し戻し基準
- 会話フローの記述がない
- System Behavior Evaluationが空
- 同一Worker内で3件以上がほぼ同じパターン
- failure_categoryがOTHERだけで具体性なし

## 焼き直し検知基準
- 同一県・同一属性・同一難易度の組み合わせが3回以上
- 会話フローが90%以上一致
- Fix Proposalが前のケースのコピペ

## 成果物
- audit/audit_log.md: 監査実行ログ
- audit/rejected_cases.md: 差し戻しケース一覧
- audit/duplicate_check.md: 重複・焼き直し検知結果
- audit/coverage_check.md: 都道府県カバレッジ確認
