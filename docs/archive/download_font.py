#!/usr/bin/env python3
"""
Google Fontsから日本語フォントをダウンロード
"""
import requests
from pathlib import Path
import zipfile
import io

# フォント保存先
font_dir = Path("/Users/robby2/robby_content/fonts")
font_dir.mkdir(exist_ok=True)

print("=" * 60)
print("Google Fontsから日本語フォントをダウンロード")
print("=" * 60)
print()

# M PLUS Rounded 1c (丸ゴシック、女性的)
fonts_to_download = [
    {
        "name": "M PLUS Rounded 1c",
        "url": "https://fonts.google.com/download?family=M%20PLUS%20Rounded%201c",
        "filename": "M_PLUS_Rounded_1c"
    },
    {
        "name": "Noto Sans JP",
        "url": "https://fonts.google.com/download?family=Noto%20Sans%20JP",
        "filename": "Noto_Sans_JP"
    }
]

for font_info in fonts_to_download:
    print(f"ダウンロード中: {font_info['name']}...")

    try:
        response = requests.get(font_info['url'], timeout=30)

        if response.status_code == 200:
            # ZIPファイルを解凍
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # TTFファイルを抽出
                for file in z.namelist():
                    if file.endswith('.ttf'):
                        z.extract(file, font_dir)
                        print(f"  ✅ 抽出: {file}")

            print(f"✅ {font_info['name']} ダウンロード完了")
        else:
            print(f"❌ エラー: {response.status_code}")

    except Exception as e:
        print(f"❌ エラー: {e}")

    print()

print("=" * 60)
print("ダウンロード完了！")
print("=" * 60)
print(f"保存先: {font_dir}")
print()
print("利用可能なフォント:")
for ttf in font_dir.glob("**/*.ttf"):
    print(f"  - {ttf}")
