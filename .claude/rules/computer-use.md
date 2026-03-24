---
description: >
  Computer Use（画面操作）に関するルール。
  「画面操作」「ブラウザで」「管理画面」「TikTok確認」「GA4見て」
  「スクショ」「Dispatch」「数字見て」に言及されたら適用。
globs:
  - scripts/computer_use/**
  - scripts/screen_*
  - data/metrics/**
---

# Computer Use 運用ルール

## 操作ヒエラルキー（必ず上から試せ）
1. scripts/ 内の既存Pythonスクリプト
2. API（Slack Bot, LINE Messaging API, GA4 Data API, Meta Marketing API）
3. Chrome DevTools MCP（ブラウザ操作）
4. Computer Use 画面操作（最終手段）

## 認証
- パスワード入力OK。.envから取得（ハードコード禁止）
- 2FA/MFAが出たらSlack通知 → YOSHIYUKI対応待ち
- ログイン操作は毎回Slackに記録（いつ・どのサービスに）
- セッション切れ検知 → 自動再ログイン試行 → 失敗2回でアラート

## 禁止事項
- クレジットカード番号の入力
- 候補者の個人情報（氏名・電話・住所）の画面上操作
- 銀行サイト・証券サイトへのアクセス
- rm -rf やシステム環境設定の変更
- pkill -f "Google Chrome"（Chrome Remote Desktopが死ぬ）

## タイムアウトとリトライ
- 1操作タスク: 最大5分
- リトライ: 最大3回（毎回手法を変える）
- 3回失敗 → フォールバック（既存API/スクリプト）
- フォールバックも失敗 → Slack通知

## 操作ログ
- 操作前スクショ → data/screenshots/before_YYYYMMDD_HHMMSS.png
- 操作後スクショ → data/screenshots/after_YYYYMMDD_HHMMSS.png
- 操作内容をSlack通知
