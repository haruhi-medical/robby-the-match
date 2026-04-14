#!/usr/bin/env python3
"""IndexNow API で更新URLをBing/Yandexに即時通知"""
import json
import urllib.request
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
KEY = "d6fd8814a7634eda8deaa2629270133d"
HOST = "quads-nurse.com"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"

def get_changed_urls(since_days=1):
    """直近N日以内にgitで変更されたHTMLのURLを取得"""
    result = subprocess.run(
        ["git", "diff", "--name-only", f"HEAD~{since_days}", "HEAD", "--", "*.html"],
        capture_output=True, text=True, cwd=str(PROJECT_DIR)
    )
    urls = []
    for line in result.stdout.strip().split('\n'):
        if not line: continue
        # ファイルパスをURLに変換
        url = f"https://{HOST}/{line}"
        urls.append(url)
    return urls

def ping_indexnow(urls):
    """IndexNow APIにバッチ送信"""
    if not urls:
        print("送信対象URLなし")
        return

    payload = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls[:10000]  # 最大10000件
    }).encode('utf-8')

    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=payload,
        method="POST"
    )
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow応答: HTTP {resp.status}")
            print(f"送信URL数: {len(urls)}")
    except Exception as e:
        print(f"IndexNowエラー: {e}")

if __name__ == "__main__":
    # --all で全ページ送信、デフォルトは直近変更分のみ
    if "--all" in sys.argv:
        # sitemap.xmlから全URL取得
        import xml.etree.ElementTree as ET
        tree = ET.parse(str(PROJECT_DIR / "sitemap.xml"))
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [u.find('sm:loc', ns).text for u in tree.findall('sm:url', ns)]
    else:
        urls = get_changed_urls(since_days=3)

    print(f"IndexNow送信: {len(urls)}件")
    for u in urls[:10]:
        print(f"  {u}")
    if len(urls) > 10:
        print(f"  ... 他{len(urls)-10}件")

    ping_indexnow(urls)
