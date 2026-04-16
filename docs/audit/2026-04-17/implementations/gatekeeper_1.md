# ゲートキーパー #1: LP診断→LINE引き継ぎ復活

## 実装日
2026-04-17

## 問題
- `shindan.js:461` と `index.html:1940-1943` が LINE友だち追加URL (`https://line.me/R/ti/p/@174cxnev`) に直リンクしていた
- 結果: LP診断で選択した答え（エリア/施設タイプ/働き方/温度感）が全く Worker に渡らず、LINE側で再度5問聞かれる二度手間
- ファクトパック§3: 4/15 Lead=2 vs LINE登録=15 の乖離の主原因と仮説
- Worker側の `/api/line-start` エンドポイント（L1407, L2684）は生存していたのに LP が使っていなかった

## 過去の廃止理由（再検討）
元の `liff.html` ブリッジは LIFF（LINE内ブラウザ）に依存しており、Instagram WebView等でログイン壁になっていた。
しかし `/api/line-start` は **単純な302リダイレクト**（LIFFではない）なので WebView でも動く。
「LIFFブリッジ」と「/api/line-start経由」は別物。前者を廃止した時に後者まで切ってしまっていた。

## 修正内容

### shindan.js
- `WORKER_BASE` 定数を追加
- CTA URL を `/api/line-start?source=shindan&intent=diagnose&session_id=...&area=...&answers={"prefecture":"","area":"","facilityType":"","workstyle":"","urgency":""}` に変更
- session_id と5問の答え全てがKV経由で Worker に引き継がれる

### index.html（Hero / Sticky / Bottom の3つのCTA）
- `lineUrl(source, intent)` 関数を `/api/line-start?source=...&intent=...&session_id=...&page_type=paid_lp` を返すよう変更
- session_id は既存の UUID 生成ロジックを維持
- LINE_ADD_URL はフォールバック用として定数保持

## Worker側の受け入れ
worker.js:2684 `handleLineStart` は既に以下を処理する実装が存在:
1. URLパラメータから session_id / source / intent / area / answers を取得
2. KVの `session:{sessionId}` に JSON 保存（24h TTL）
3. webSessionMap（in-memory fallback）にも保存
4. `dm_text={sessionId}` 付きで LINE友だち追加URLへ 302リダイレクト

follow webhook は KVから session を復元してマッチング状態に直入り可能（L5999付近）。

## 期待されるインパクト
- ファネル中盤 **30-50%改善**（戦略監督推定）
- Lead計測と実LINE登録数の乖離解消
- ミサキ体験: 診断完了 → LINE開く → 即マッチング表示（5問スキップ）

## デプロイ手順
1. LP側（git push → GitHub Pages）で即反映
2. Worker側は追加修正不要（既存実装を使う）
3. 検証: LPから診断→LINE登録→マッチング表示まで手動トレース

## 懸念点
- Instagram WebView での302リダイレクト挙動の実機検証が未実施（高リスクだが、Meta広告LP直リンク方式は既に成功している → 同じパターン）
- `/api/line-start` の Worker側エラーログを監視（Cloudflare Workers ダッシュボード）

## 検証項目（デプロイ後）
- [ ] LP診断完了→CTAクリック→Worker 302→LINE友だち追加→welcome メッセージに診断内容が反映される
- [ ] 広告3クリエイティブ（既に /api/line-start 使用中）の挙動が壊れていない
- [ ] Cloudflare Workers ダッシュボードで 2xx/3xx レスポンス比率確認

## 変更ファイル
- lp/job-seeker/shindan.js (+7 -2)
- lp/job-seeker/index.html (+9 -4)
