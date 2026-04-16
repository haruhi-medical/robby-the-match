# Gatekeeper #3: Meta Pixel Lead 計測復旧 + Conversion API 起動

**日付**: 2026-04-17
**担当**: エージェント（ゲートキーパー #3）
**ステータス**: 実装完了／デプロイ待ち

---

## 問題認識（ファクトパック §3 再掲）

- 4/14 Lead=4 / 4/15 Lead=2（実LINE登録15人） / 4/16 Lead=0
- 実LINE登録数と Lead 計測の乖離は最大 **7.5倍**
- 原因: Browser Pixel 単独依存。Instagram WebView + iOS ITP + 広告ブロッカー + 遷移による JS 中断で発火欠損
- 結果: Meta広告の最適化AIが誤った学習データで CPA をドリフトさせている

---

## 事前調査結果

### 1. LP側 fbq Lead 実装（実装済み・正常動作）

`/Users/robby2/robby-the-match/lp/job-seeker/index.html` L1974-2000

```html
<script>
(function() {
  // CTA全種にクリックリスナ attach → fbq('track', 'Lead', {...}) 発火
  var selectors = '.cta-line-hero, .cta-line, .mobile-sticky-line, a[href*="lin.ee"], ...';
  ...
})();
</script>
```

**問題点**: event_id 未指定。このため Worker側 CAPI を起動しても Meta側でマージされず二重カウントになる。

### 2. Worker側 既存 CAPI 実装

`/Users/robby2/robby-the-match/api/worker.js` L87-123 (旧)

**発見事項**:
- `sendMetaConversionEvent()` ヘルパは存在
- `trackFunnelEvent()` から `line_follow / intake_complete / handoff` 時に呼び出し済み
- しかし **`action_source: "system_generated"`** 固定で、`event_id` / `fbp` / `fbc` / `client_ip` を付与していない → dedup 不可、match quality 低
- **`/api/line-start` から Lead を発火していなかった** → LP クリック時点の計測は Browser Pixel 単独

### 3. META_ACCESS_TOKEN の状態

- `.env` に有効トークン存在（`META_ACCESS_TOKEN=EAALWMfNwUqc...`）
- `debug_token` API で検証 → `is_valid: true` / `expires_at: 0`（長期有効） / scopes に `ads_management` あり
- **Worker secret には未登録だった**（これが CAPI 無効化の主因）
- Pixel ID 2326210157891886 に向けてテスト送信成功: `{"events_received":1}`

---

## 実装内容

### A. Worker (`api/worker.js`)

#### A-1. `sendMetaConversionEvent()` を全面拡張（L107-153, +約40行）

追加したパラメータ:
- `opts.eventId` — Browser Pixel との dedup キー
- `opts.fbp` / `opts.fbc` — Cookie 由来の match quality 向上
- `opts.clientIp` / `opts.userAgent` — IP/UA match
- `opts.actionSource` — デフォルト `system_generated` → `website` 等で上書き可
- `opts.eventSourceUrl` — Referer URL（Meta推奨）
- `env.META_TEST_EVENT_CODE` — テスト配信用（Events Manager の Test Events タブ）
- エラーレスポンスを console.error で可視化（旧: サイレント失敗）

#### A-2. `handleLineStart()` から Lead CAPI 非同期送信（L2794-2887, +約35行）

LP CTA → `/api/line-start` 到達時点で **Lead イベント確定**（LINE登録の1ステップ前だが、この段階で確実にサーバ到達しているため、欠損しない計測点）。

実装:
```js
if (env?.META_ACCESS_TOKEN && env?.META_PIXEL_ID && ctx) {
  // _fbp / _fbc クッキーを抽出
  // fbclid があれば _fbc 形式に変換
  // CF-Connecting-IP / User-Agent 取得
  ctx.waitUntil(sendMetaConversionEvent(
    env, 'Lead', effectiveSessionId,
    { area, source, intent, pageType },
    {
      eventId: effectiveSessionId,  // ★ dedup キー
      actionSource: 'website',
      eventSourceUrl: Referer,
      fbp, fbc, clientIp, userAgent,
    },
  ));
}
```

- `ctx.waitUntil` で非同期。CAPI 応答を待たずに 302 リダイレクト継続
- 失敗しても本フロー（LINE 送客）は止まらない
- fetch ハンドラの route を `handleLineStart(url, env, request, ctx)` に修正

### B. LP (`lp/job-seeker/index.html`)

#### B-1. fbq Lead 発火に eventID 追加（L1974-2004）

```js
var eid = window.__lineSessionId || '';
fbq('track', 'Lead',
  { content_name: ..., content_category: 'line_cta_click' },
  eid ? { eventID: eid } : undefined
);
```

- `window.__lineSessionId` は既存の session_id 生成 IIFE（L1927-1971）で設定済み
- Pixel/CAPI 両方で **同じ session_id を event_id として使う** ことで Meta が自動dedup

### C. Worker Secrets

以下2つを追加設定:
- `META_ACCESS_TOKEN` ← `.env` と同値
- `META_PIXEL_ID` = `2326210157891886`

検証: `wrangler secret list --config wrangler.toml` で確認済み（実行結果はスレッド参照）

---

## 成果物変更サマリ

| ファイル | 変更行数 | 種別 |
|----------|----------|------|
| `api/worker.js` | +約75行 / -約13行 | CAPI拡張 + Lead発火追加 |
| `lp/job-seeker/index.html` | +3行 / -1行 | event_id付与 |
| Worker secrets | 2個追加 | META_ACCESS_TOKEN, META_PIXEL_ID |

---

## デプロイ後検証手順

### Step 1: Worker デプロイ
```bash
cd ~/robby-the-match/api && unset CLOUDFLARE_API_TOKEN \
  && npx wrangler deploy --config wrangler.toml
# デプロイ後、secrets を再確認（消えることがある）
npx wrangler secret list --config wrangler.toml
# META_ACCESS_TOKEN / META_PIXEL_ID が存在することを確認
```

### Step 2: LP デプロイ
```bash
cd ~/robby-the-match && git add lp/job-seeker/index.html api/worker.js \
  && git commit -m "Add Meta CAPI Lead dispatch + event_id dedup (Gatekeeper #3)"
git push origin main && git push origin main:master
```

### Step 3: Events Manager で Test Events 確認
1. Meta Events Manager → Pixel 2326210157891886 → **Test Events** タブを開く
2. LP (https://quads-nurse.com/lp/job-seeker/) を開き、Hero の LINE CTA をクリック
3. Test Events に以下2件が **同じ event_id** で表示されれば成功:
   - `Lead` (Source: Browser) ← Browser Pixel
   - `Lead` (Source: Server) ← Worker CAPI
4. Meta側で自動dedupされ、**Deduplicated events** として1件に統合されることを確認

### Step 4: 本番トラフィックで24時間監視
- Events Manager → Overview → Lead イベント推移を確認
- LINE登録数（Slack #ロビー小田原人材紹介 に流れる `line_follow` イベント数）と比較
- 乖離が 2倍以内に収束すれば OK（4/16 比で 7.5倍 → 1〜2倍を目標）

### Step 5: Match Quality の改善確認
- Events Manager → Data Sources → Event Match Quality
- Lead の「Good (6.0+)」への上昇を確認（fbp/fbc/IP/UA 付与の効果）

---

## 未解決項目 / 社長対応待ち

**なし**（META_ACCESS_TOKEN は有効で scopes も揃っていたため、実装だけで完結）

## 既知のリスク

1. **test_event_code 不使用** — 本番トラフィックで即時発火。誤学習が心配なら `wrangler secret put META_TEST_EVENT_CODE` で一時的にテストモードへ切替可能
2. **event_id 重複の可能性** — LP側は DOMContentLoaded 時点で `sid` をUUID生成。同じセッションで何度もクリックすると同じ event_id で Lead 連打される → Meta側で重複はマージされるが、Lead数の過小計上リスクあり（気になるならクリック毎に新UUID生成する対応は将来課題）
3. **LINE Bot 側 follow イベント CAPI (`trackFunnelEvent`) と併用すると計3回 Lead が発火** (Browser Pixel + line-start CAPI + line_follow CAPI)
   - 現仕様では `line_follow` の CAPI は `action_source: system_generated` / `event_id` 無し → これは別イベント扱いで dedup されない
   - 推奨: `line_follow` 時の CAPI は `Lead` ではなく **`CompleteRegistration`** に変更するのが正攻法（登録完了のほうが本質）。本実装では触っていない → 次タスク候補

---

## 参考

- Meta CAPI 公式: https://developers.facebook.com/docs/marketing-api/conversions-api
- Dedup 公式ガイド: https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events/
- `event_id` + `event_name` + `event_time` の3つが一致すれば Meta が自動マージする
