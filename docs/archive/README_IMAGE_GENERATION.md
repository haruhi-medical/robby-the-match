# 画像生成スクリプト - 使い方

## 📝 概要
Cloudflare Workers AI + Pillowで、SNS投稿用の画像を自動生成

---

## 🚀 クイックスタート

### 1. 背景画像を生成（6枚）
```bash
cd ~/robby_content
python3 generate_backgrounds.py
```

### 2. テキストオーバーレイを合成（6枚）
```bash
cd ~/robby_content
python3 add_text_overlay_v3.py
```

**注意**: `add_text_overlay_v3.py`の最後の部分を編集して、全6枚を生成するように変更してください。

---

## 📁 ファイル構成

```
~/robby_content/
├── fonts/
│   └── MPLUSRounded1c-Black.ttf  # 丸ゴシックフォント
├── post_001/
│   ├── slide_prompts.json        # 画像プロンプト
│   ├── caption.txt               # キャプション
│   ├── backgrounds/              # 背景画像（6枚）
│   └── final_slides_v3/          # 完成画像（6枚）
├── generate_backgrounds.py       # 背景生成スクリプト
└── add_text_overlay_v3.py        # テキスト合成スクリプト
```

---

## ⚙️ スクリプトの特徴

### `generate_backgrounds.py`
- Cloudflare Workers AI (FLUX.1-schnell) 使用
- 1024x1536 (縦向き) PNG生成
- 日本の病院廊下の背景

### `add_text_overlay_v3.py`
- **見切れ防止**: 左右10%マージン、自動フォントサイズ調整
- **フォント**: M PLUS Rounded 1c Black（丸ゴシック）
- **強調**: 重要ワードを黄色で表示
- **ターゲット**: 20代後半〜40代女性

---

## 🎨 カスタマイズ

### フォントを変更
`add_text_overlay_v3.py`の`font_paths`を編集

### 強調キーワードを変更
`parse_text_with_highlights()`関数の`highlight_keywords`を編集

### マージンを変更
```python
margin = width // 10  # 左右10% → 好きな値に変更
```

---

## 💡 次回の投稿用

post_002を作成する時：
1. `post_002/`ディレクトリを作成
2. `slide_prompts.json`と`caption.txt`を配置
3. スクリプトのパスを`post_002`に変更して実行

---

**作成日**: 2026-02-18
**最終更新**: 2026-02-18
