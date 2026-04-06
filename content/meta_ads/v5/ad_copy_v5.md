# Meta広告コピー v5（LINE直リンク・¥2,000/日）

> LP経由なし。広告→LINE直リンク。
> リンク先: `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-start?source=meta_ad&intent=direct`
> Worker経由でsession自動生成→LINE友だち追加→meta_ad用ウェルカムメッセージ

---

## AD1: 年収診断型（好奇心フック）

### メインテキスト
```
看護師5年目の平均年収、480万円って知ってた？

あなたの経験で、いくら貰えるはず？
LINEで30秒で分かります。

✅ 完全無料
✅ 電話なし・LINE完結
✅ いつでもブロックOK
```

### CTA: 「詳しくはこちら」
### リンク先: Worker /api/line-start?source=meta_ad&intent=direct

---

## AD2: 共感型（感情フック）

### メインテキスト
```
「前にも言ったよね」

この言葉、何回聞いた？
人間関係がしんどいなら、環境を変えるだけで解決するかも。

LINEで気軽に相談できます。

✅ 完全無料・電話なし
✅ 名前も電話番号もいらない
✅ いつでもブロックOK
```

### CTA: 「詳しくはこちら」
### リンク先: Worker /api/line-start?source=meta_ad&intent=direct

---

## AD3: 数字インパクト型

### メインテキスト
```
転職エージェントの手数料、50万円も差があるって知ってた？

手数料が安い → 病院の負担が軽い → 内定が出やすい。

まずはLINEで求人を見てみませんか？

✅ 完全無料・電話なし
✅ いつでもブロックOK
```

### CTA: 「詳しくはこちら」
### リンク先: Worker /api/line-start?source=meta_ad&intent=direct

---

## 共通設定

| 項目 | 値 |
|------|-----|
| リンク先URL | `https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/line-start?source=meta_ad&intent=direct` |
| CTA | 「詳しくはこちら」 |
| 配置 | Advantage+配置（自動最適化） |
| ターゲティング | 24-38歳女性 / 神奈川+東京+千葉+埼玉 / Advantage+オーディエンスON |
| 興味関心 | 看護 / 看護師 / 医療 / 転職 / ヘルスケア / 病院 |

## 重要ポイント

- 全広告に **「電話なし」「無料」「ブロックOK」** を明記（ミサキの不安除去）
- LP経由なし。広告タップ→即LINE友だち追加画面
- Workerがsource=meta_adを検出し、広告用ウェルカムメッセージを表示
- Meta CAPI: follow時にLeadイベント自動発火（META_ACCESS_TOKEN設定時）
