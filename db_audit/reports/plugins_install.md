# Claude Code プラグイン/MCPサーバー調査・インストール結果

> 実施日: 2026-04-06

## 結果サマリ

| プラグイン | 種別 | インストール | 状態 |
|-----------|------|-------------|------|
| Context7 | MCP Server | `claude mcp add context7 -- npx -y @upstash/context7-mcp@latest` | Connected |
| Code Review | Plugin | `claude plugin install code-review@claude-plugins-official` | enabled |
| Frontend Design | Plugin | `claude plugin install frontend-design@claude-plugins-official` | enabled |
| Superpowers | Plugin | `claude plugin install superpowers@claude-plugins-official` | enabled (v5.0.7) |

---

## 1. Context7 (MCP Server)

- **提供元**: Upstash (GitHub: upstash/context7)
- **機能**: 最新のライブラリドキュメントをリアルタイム取得してプロンプトに注入。ハルシネーション抑制に有効
- **使い方**: プロンプトに `use context7` を追加するだけで、最新ドキュメントを参照可能
- **設定先**: `/Users/robby2/.claude.json` (project: /Users/robby2/robby-the-match)
- **コスト**: 無料

## 2. Code Review (Plugin)

- **提供元**: Anthropic公式マーケットプレイス (claude-plugins-official)
- **機能**: マルチエージェントPRレビュー。セキュリティ・テスト・型安全性・コード品質・簡素化の各観点から分析
- **使い方**: `/code-review` コマンドで起動
- **コスト**: 無料

## 3. Frontend Design (Plugin)

- **提供元**: Anthropic公式マーケットプレイス (claude-plugins-official)
- **機能**: フロントエンド生成時に美的方向性（ブルータリスト、レトロフューチャー、ラグジュアリー等）を選定してからコーディング。汎用的なデフォルトデザインを回避
- **使い方**: フロントエンド構築を依頼すると自動的に適用される
- **コスト**: 無料

## 4. Superpowers (Plugin)

- **提供元**: obra (GitHub: obra/superpowers)
- **機能**: 構造化ソフトウェア開発メソドロジーのスキルフレームワーク。TDD、体系的デバッグ、ブレスト、サブエージェント駆動開発+コードレビュー
- **使い方**: `/brainstorming`, `/execute-plan` 等のスラッシュコマンド
- **バージョン**: 5.0.7
- **コスト**: 無料

---

## 既存MCP/プラグイン一覧（インストール後）

### MCP Servers
| 名前 | 状態 |
|------|------|
| claude.ai Gmail | Needs authentication |
| claude.ai Google Calendar | Needs authentication |
| canva | Connected |
| chrome-devtools | Failed to connect |
| **context7** | **Connected** (今回追加) |

### Plugins
| 名前 | 状態 |
|------|------|
| **code-review** | enabled (今回追加) |
| **frontend-design** | enabled (今回追加) |
| **superpowers** | enabled v5.0.7 (今回追加) |

---

## 注意事項

- chrome-devtoolsが `Failed to connect` — Chromeが起動していない場合は正常
- Gmail / Google Calendarは認証未完了 — 必要時に `claude mcp login` で認証
- Context7はプロジェクトスコープ（robby-the-match）にインストール済み
- プラグイン3件はユーザースコープ（全プロジェクト共通）
