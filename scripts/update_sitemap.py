#!/usr/bin/env python3
"""
sitemap.xml の lastmod を各HTMLファイルの最終 git commit 日時に更新するスクリプト。

動作:
  - sitemap.xml 内の全URLについて対応するHTMLファイルの最終 git commit 日時を取得
  - lastmod をその日時（YYYY-MM-DD形式）に更新
  - 対応ファイルが存在しない URL には WARN を出力
  - blog/success-story-template.html の URL はsitemapから除外

使用法:
  python3 scripts/update_sitemap.py
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

# リポジトリルート
REPO_ROOT = Path(__file__).resolve().parent.parent
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
BASE_URL = "https://quads-nurse.com/"

# sitemapから除外するURLの相対パス部分（末尾スラッシュなし）
EXCLUDE_PATHS = {
    "blog/success-story-template.html",
}


def url_to_file_path(url: str) -> Optional[Path]:
    """
    URL をリポジトリ内のファイルパスに変換する。
    例:
      https://quads-nurse.com/            -> index.html
      https://quads-nurse.com/blog/       -> blog/index.html
      https://quads-nurse.com/blog/foo.html -> blog/foo.html
    """
    if not url.startswith(BASE_URL):
        return None

    rel = url[len(BASE_URL):]  # BASE_URL を除いた相対パス

    if rel == "" or rel.endswith("/"):
        # ディレクトリ URL -> index.html
        rel = rel + "index.html"

    return REPO_ROOT / rel


def get_git_lastmod(file_path: Path) -> Optional[str]:
    """
    指定ファイルの最終 git commit 日付を YYYY-MM-DD で返す。

    優先順位:
      1. --diff-filter=M  : ファイル内容が実際に変更されたコミットの最新日付
      2. --diff-filter=A  : 追加されたコミット（新規ファイル）
      3. フォールバック    : git log -1（上記で取得できない場合）

    git 管理外 or エラーの場合は None を返す。
    """
    rel_path = str(file_path.relative_to(REPO_ROOT))

    def _run_git_log(extra_args: list) -> Optional[str]:
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ad", "--date=short"]
                + extra_args
                + ["--", rel_path],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=10,
            )
            date_str = result.stdout.strip()
            if date_str and re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
                return date_str
            return None
        except Exception:
            return None

    # 1. 内容変更コミット（M=modified）
    date = _run_git_log(["--diff-filter=M"])
    if date:
        return date

    # 2. 追加コミット（A=added）
    date = _run_git_log(["--diff-filter=A"])
    if date:
        return date

    # 3. フォールバック: 最新コミット（リネーム等を含む）
    return _run_git_log([])


def main():
    if not SITEMAP_PATH.exists():
        print(f"ERROR: sitemap.xml が見つかりません: {SITEMAP_PATH}", file=sys.stderr)
        sys.exit(1)

    # XML 名前空間を保持するため登録してから parse
    namespace = "http://www.sitemaps.org/schemas/sitemap/0.9"
    ET.register_namespace("", namespace)

    tree = ET.parse(SITEMAP_PATH)
    root = tree.getroot()

    ns = {"sm": namespace}

    updated = 0
    unchanged = 0
    warned = 0
    excluded = 0

    # 除外する <url> 要素を後でまとめて削除するため収集
    urls_to_remove = []

    for url_elem in root.findall("sm:url", ns):
        loc_elem = url_elem.find("sm:loc", ns)
        if loc_elem is None:
            continue

        loc = loc_elem.text.strip()
        rel_path = loc[len(BASE_URL):]  # 相対パス部分

        # success-story-template.html など除外パスのチェック
        if rel_path in EXCLUDE_PATHS or rel_path.rstrip("/") in EXCLUDE_PATHS:
            urls_to_remove.append(url_elem)
            print(f"EXCLUDE: {loc}")
            excluded += 1
            continue

        file_path = url_to_file_path(loc)
        if file_path is None:
            print(f"WARN: URL をファイルパスに変換できません: {loc}", file=sys.stderr)
            warned += 1
            continue

        if not file_path.exists():
            print(
                f"WARN: ファイルが存在しません: {file_path.relative_to(REPO_ROOT)}  ({loc})",
                file=sys.stderr,
            )
            warned += 1
            continue

        lastmod_date = get_git_lastmod(file_path)
        if lastmod_date is None:
            print(
                f"WARN: git ログが取得できません（未コミット？）: {file_path.relative_to(REPO_ROOT)}",
                file=sys.stderr,
            )
            warned += 1
            continue

        # <lastmod> 要素を更新
        lastmod_elem = url_elem.find("sm:lastmod", ns)
        if lastmod_elem is not None:
            old = lastmod_elem.text
            if old != lastmod_date:
                lastmod_elem.text = lastmod_date
                print(f"UPDATE : {rel_path or '/':<55}  {old} -> {lastmod_date}")
                updated += 1
            else:
                print(f"  OK   : {rel_path or '/':<55}  {lastmod_date}")
                unchanged += 1
        else:
            # <lastmod> が存在しない場合は <loc> の次に挿入
            loc_index = list(url_elem).index(loc_elem)
            new_elem = ET.Element(f"{{{namespace}}}lastmod")
            new_elem.text = lastmod_date
            url_elem.insert(loc_index + 1, new_elem)
            print(f"INSERT : {rel_path or '/':<55}  {lastmod_date}")
            updated += 1

    # 除外要素を削除
    for url_elem in urls_to_remove:
        root.remove(url_elem)

    # XML を上書き保存（XML宣言付き・インデント整形）
    ET.indent(tree, space="  ")
    tree.write(SITEMAP_PATH, encoding="UTF-8", xml_declaration=True)

    print()
    print(f"完了: 更新={updated}件 / 変更なし={unchanged}件 / 除外={excluded}件 / 警告={warned}件")
    print(f"保存先: {SITEMAP_PATH}")


if __name__ == "__main__":
    main()
