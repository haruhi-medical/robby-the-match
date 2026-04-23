# 次回セッション引き継ぎ — 2026-04-23 マイページ整備完了時点

- **最終コミット**: `87d898d` — マイページ群UI統一
- **最終 Worker Version**: `30edca84` (api側はマイページAPI改修後のまま、今回UI改修でworker.js未変更)
- **次回セッション開始時の最優先**: このファイルを読む → マイページの**実機UI確認**

---

## 🎯 次回セッション最初にやること

### Step 1: 起動プロトコル
```bash
cd ~/robby-the-match
python3 scripts/slack_bridge.py --start
# STATE.md を読む
git log --oneline -10
```

### Step 2: マイページ UI 統一の確認
GitHub Pages は既に反映済みのはず。以下をブラウザで確認:

| URL | 確認ポイント |
|---|---|
| https://quads-nurse.com/mypage/auth.html | ロゴヘッダー+白背景+絵文字なし |
| https://quads-nurse.com/mypage/preferences/ | チップ選択UI+ロゴヘッダー |
| https://quads-nurse.com/mypage/favorites/ | 空状態メッセージ+ロゴヘッダー |
| https://quads-nurse.com/resume/member-lite/ | ヒーロー+信頼フッター+ロゴ |

Playwrightで即撮るコマンド:
```bash
python3 -c "
from playwright.sync_api import sync_playwright
import os, time
out = '/Users/robby2/robby-the-match/docs/audit/2026-04-22-resume-security/screenshots'
urls = [
  ('mypage_auth_u', 'https://quads-nurse.com/mypage/auth.html'),
  ('mypage_prefs_u', 'https://quads-nurse.com/mypage/preferences/'),
  ('mypage_favs_u', 'https://quads-nurse.com/mypage/favorites/'),
  ('resume_lite_u', 'https://quads-nurse.com/resume/member-lite/'),
]
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    c = b.new_context(viewport={'width':390,'height':844},
      user_agent='Mozilla/5.0 (iPhone) Safari/604.1')
    c.route('**/*', lambda r: r.continue_(headers={**r.request.headers,'Cache-Control':'no-cache'}))
    for n,u in urls:
      pg=c.new_page()
      pg.goto(f'{u}?nocache={int(time.time()*1000)}', timeout=20000, wait_until='networkidle')
      pg.wait_for_timeout(3000)
      pg.screenshot(path=os.path.join(out, f'{n}.png'), full_page=True)
      print(f'✅ {n}')
      pg.close()
    b.close()
"
```

### Step 3: 代表の認証付きマイページ確認（実機）
代表（石づか/一なか = U7e23b53d10319c3b070313537485fbc6）のマイページを Safari で開く場合:
```bash
python3 /tmp/issue_mypage_token.py  # 24hトークンURLを発行（スクリプトがなければ作成）
```
もしくは LINE から「履歴書を作成する」でマイページへ遷移、履歴書編集・希望条件・お気に入り を見る。

---

## ✅ 2026-04-22 〜 04-23 で完成した機能 総まとめ

### MVP-A: 会員制基盤
- 履歴書作成→会員化 (`/resume/member/` + `/api/member-resume-generate`)
- マイページ (`/mypage/` + LIFF不要HMAC署名URL認証)
- 履歴書ビュー・編集・削除 (`/mypage/resume/` + edit.html)
- セッショントークン(24h) + CORS対応

### Phase 2: 会員価値機能
- 希望条件保存 (`/mypage/preferences/` + `/api/mypage-preferences`)
- お気に入り求人 (`/mypage/favorites/` + `/api/mypage-favorites` 最大50件)
- ルートB最小プロフ会員化 (`/resume/member-lite/` + `/api/member-lite-register`)

### Phase 3: LINE Bot 統合
- 求人 Flex カードに「保存」postback ボタン
- postback受信: 会員は favorites 保存、非会員は会員登録メリットFlex誘導
- matching_preview/browse 完了時の非会員誘導
- 新着求人Push cron (10時JST) の会員精密マッチ（preferences考慮）

### UI/UX
- 履歴書作成画面 (`/resume/member/`) 全面刷新
  - ロゴヘッダー + ヒーロー「AIが仕上げる 看護師さんの履歴書」
  - ボタン風chip: 簡単入力 / PDF保存・印刷 / マイページで編集可能
  - ステップ番号 01-09 構造
  - 絵文字ゼロ + Noto Sans JP 統一
  - ブランドカラー: primary #1A6B8A / cta #2D9F6F / accent #D4A843 / secondary #E8756D
  - 送信ボタン直前に信頼フッター
- 郵便番号→住所自動入力（zipcloud API、ひらがな変換対応）
- 学歴フォーム: 入学+卒業の両方の年月を入力可（UI 1ブロック、送信時に2行分解）
- マイページ群（8ファイル）を履歴書作成ページのデザイン言語に統一

### 法令・セキュリティ
- 個人情報保護法21/28/35条すべて対応
- OpenAI越境移転の明示同意（チェックボックス）
- 山田エリカ様履歴書削除ログ記録
- CORS Authorization ヘッダー許可
- HMAC-SHA256 timingSafeEqual 対応
- SSL/Referrer-Policy no-referrer/Cache-Control no-store

### E2Eテスト
- `scripts/test_mypage_full_e2e.py` — 37+12件、全PASS

---

## 📊 本番稼働中の全エンドポイント (17件)

| Method | Path | 用途 |
|---|---|---|
| POST | /api/line-webhook | LINE Bot Webhook |
| POST | /api/chat-init / /api/chat / /api/chat-complete | AIチャット |
| POST | /api/line-start | LP→LINEセッション |
| POST | /api/notify / /api/register | 通知・登録 |
| POST | /api/resume-generate | 旧履歴書API（互換維持、未使用） |
| POST | /api/member-resume-generate | 会員化+履歴書生成 |
| POST | /api/member-lite-register | ライト会員化 |
| POST | /api/mypage-init | マイページ認証 |
| GET/DELETE | /api/mypage-resume | 履歴書取得/削除 |
| GET | /api/mypage-resume-data | 編集用JSON |
| POST | /api/mypage-resume-edit | 履歴書更新 |
| GET/POST | /api/mypage-preferences | 希望条件 |
| GET/POST/DELETE | /api/mypage-favorites | お気に入り |
| POST | /api/admin/trigger-newjobs-push | 新着Push手動発火 |
| POST | /api/line-push | Slack→LINE |

## 🎨 本番稼働中の全UI (9ページ)

| URL | 用途 |
|---|---|
| /resume/ | 旧履歴書フォーム（LINE Botからは叩かれない、互換維持） |
| /resume/member/ | 会員化+履歴書作成フォーム（本線） |
| /resume/member-lite/ | ライト会員登録 |
| /mypage/ | マイページトップ |
| /mypage/auth.html | LIFFなし誘導 |
| /mypage/resume/ | 履歴書ビュー（iframe+印刷ボタン） |
| /mypage/resume/edit.html | 履歴書編集フォーム |
| /mypage/preferences/ | 希望条件設定 |
| /mypage/favorites/ | お気に入り求人一覧 |

## 🗄 KV データ構造
```
member:<userId>                         会員プロファイル(永続)
member:<userId>:resume                  履歴書HTML
member:<userId>:resume_data             履歴書元データJSON
member:<userId>:preferences             希望条件JSON
member:<userId>:favorites               お気に入り配列(最大50件)
resume_token:<uuid>                     30分短期トークン(使い切り)
session:<sid>                           LINE会話セッション(24h)
newjobs_notify:<userId>                 新着通知opt-out
```

---

## 🔴 次回セッションの候補タスク

### 優先度A: 実機確認+微調整
1. **代表の実機LINEで全フロー確認**
   - 履歴書作成→マイページ→確認・印刷→編集→希望条件→お気に入り
   - 「保存」ボタン動作（求人カードから）
2. **スクショ確認して UI 微調整**
   - 文言・配色・余白の最終調整

### 優先度B: Phase 4 候補（代表判断待ち）
- **応募履歴トラッキング**（「この病院に送りました」「面接日」「結果」）
- **面接対策AI**（AIが過去の面接質問を予習）
- **スカウト受信機能**（病院からの逆指名、本人許諾あり）
- **マイページに「書類作成」新機能**（職務経歴書、推薦状等）
- **LINE 旧 `/resume/` の deprecate** （JSリダイレクト or 削除）

### 優先度C: 運用・改善
- マイページにGA4イベント追加（転換率計測）
- Slack 通知のマークダウン整理
- KVの古いレコード棚卸し（テスト資産削除）
- 新機能の英語化（海外在住看護師対応）

---

## ⚠ 既知の注意事項

### 代表指示（厳守）
- **既存ファイル変更は必ず事前相談**: `/resume/index.html` `api/worker.js` の既存関数・既存ルーティング
- 現段階で触ったのはE1〜E6の承認済み変更 + T1/T2/T3 の LINE Bot 改修のみ

### 並行セッションとの衝突回避
- 別の窓で LINE Bot 改修（新着求人 Push・リッチメニュー・aica）が動いている可能性
- 作業前に必ず `git fetch origin && git pull --rebase origin main` で最新化

### キャッシュ問題
- GitHub Pages 反映に3-5分
- LINE内ブラウザはキャッシュ強い → 実機テスト前に**LINEアプリ再起動推奨**
- mypage.js は `?v=20260423b` 等でキャッシュバスト可、上げ忘れ注意

---

## 📁 参照ドキュメント
- 本書: `docs/audit/2026-04-22-resume-security/handoff-next-session.md`
- 監査レポート: `docs/audit/2026-04-22-resume-security/report.md`
- 代表向けブリーフィング: `docs/audit/2026-04-22-resume-security/briefing-for-tomorrow.md`
- 設計書: `docs/superpowers/specs/2026-04-22-nursrobby-membership-design.md`
- 実装計画: `docs/superpowers/plans/2026-04-22-nursrobby-membership-mvp-a.md`
- E2Eスモーク: `scripts/test_mypage_full_e2e.py`

---

## 直近コミット抜粋
```
87d898d style: マイページ群UI統一 — 履歴書作成ページのデザイン言語に揃える
c27a90a feat: 学歴フォームに入学年月フィールド追加
a988f44 fix: 郵便番号自動入力のひらがな変換を半角カタカナ対応
bd7a2fa feat: 郵便番号→住所自動入力(zipcloud API)
b382d9d style: ヒーロー改善(看護師さん+簡単入力ボタン風)+信頼バッジ移動
17015f6 style: 履歴書作成画面 ヒーロー再設計でAI訴求を最優先
af7ac14 style: 履歴書作成画面 ヘッダー改善・明朝フォント撤去
a234c96 style: 履歴書作成画面 UI 完璧化・絵文字全廃・ロゴで信用度向上
253d48c fix: CORS ヘッダー修正 — Authorization ヘッダー付き fetch で Load failed 解消
b0c176a feat: Phase 2 ルートB 最小プロフで会員化
...
```
