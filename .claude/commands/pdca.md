# /pdca — ナースロビー PDCAサイクル実行

STATE.mdベースのPDCAサイクルを実行する。

## 手順

1. **Check（現状確認）** — 並列で実行:
   - `STATE.md` を読んで現在のフェーズ・KPI・未完了タスクを把握
   - `git log --oneline -5` で最新の変更を確認
   - `python3 scripts/slack_bridge.py --start` でSlack指示を確認

2. **Plan（計画）**:
   - STATE.mdの「次にやるべきこと」の🔴最優先タスクを特定
   - Slack指示があればそれを最優先
   - 今日実行すべきタスクを1〜3個選定

3. **Do（実行）**:
   - 選定したタスクを実行
   - 必要に応じてサブエージェント4体で並列実行
   - 進捗はSlackに報告: `python3 scripts/slack_bridge.py --send "進捗メッセージ"`

4. **Act（更新）**:
   - STATE.mdを更新（KPI、完了項目、次のタスク）
   - PROGRESS.mdに作業内容を追記
   - 必要ならデプロイ（`/deploy` スキルを使用）

5. **報告**: 実行結果のサマリを表示

## 注意
- Slack指示 > STATE.mdの優先順位
- 平島禎之からの指示は最優先で対応
- コスト意識を常に持つ（無料でできることに金を使うな）
