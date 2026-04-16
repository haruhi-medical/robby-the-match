#!/usr/bin/env python3
"""
ハローワーク求人 → D1 jobsテーブル 全件INSERT

hellowork_rank.py の出力（data/hellowork_ranked.json）を
Cloudflare D1 の jobs テーブルに全件投入する。

使い方:
  python3 scripts/hellowork_to_d1.py              # 本番D1に投入
  python3 scripts/hellowork_to_d1.py --dry-run     # SQLファイル出力のみ（D1更新なし）
  python3 scripts/hellowork_to_d1.py --local        # ローカルSQLiteに投入（テスト用）
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RANKED_FILE = PROJECT_ROOT / "data" / "hellowork_ranked.json"
SQL_OUTPUT = PROJECT_ROOT / "data" / "hellowork_jobs_d1.sql"
LOCAL_DB = PROJECT_ROOT / "data" / "hellowork_jobs.sqlite"
WRANGLER_CONFIG = PROJECT_ROOT / "api" / "wrangler.toml"
D1_DB_NAME = "nurse-robby-db"

# ========= 都道府県解決ロジック =========
# 優先順: (1) 住所文字列に都道府県名が含まれる → 抽出
#         (2) 住所文字列に市区町村名が含まれる → CITY_PREF_MAPで逆引き
#         (3) ハローワーク area 値 → AREA_PREF_REVERSE で逆引き
# 関東4都県（東京/神奈川/千葉/埼玉）のみ対象。
# 派遣求人除外ルールは hellowork_rank.py 側で処理済み。

PREFECTURES = ("東京都", "神奈川県", "千葉県", "埼玉県")

# 市区町村名 → 都道府県マップ
# 注意: 曖昧性回避のため、他県と同名の市区町村は除外（例: 府中市は東京都/広島県に存在）
# 関東4都県内で重複する名称はコメント付きで明示
CITY_PREF_MAP = {
    # 神奈川県（33市町村）
    "横浜市": "神奈川県", "川崎市": "神奈川県", "相模原市": "神奈川県",
    "横須賀市": "神奈川県", "三浦市": "神奈川県", "鎌倉市": "神奈川県",
    "逗子市": "神奈川県", "葉山町": "神奈川県", "寒川町": "神奈川県",
    "大磯町": "神奈川県", "二宮町": "神奈川県", "伊勢原市": "神奈川県",
    "厚木市": "神奈川県", "海老名市": "神奈川県", "綾瀬市": "神奈川県",
    "座間市": "神奈川県", "大和市": "神奈川県", "秦野市": "神奈川県",
    "松田町": "神奈川県", "山北町": "神奈川県", "南足柄市": "神奈川県",
    "開成町": "神奈川県", "中井町": "神奈川県", "大井町": "神奈川県",
    "箱根町": "神奈川県", "真鶴町": "神奈川県", "湯河原町": "神奈川県",
    "愛川町": "神奈川県", "清川村": "神奈川県", "小田原市": "神奈川県",
    "藤沢市": "神奈川県", "茅ヶ崎市": "神奈川県", "平塚市": "神奈川県",
    # 東京都（市部。23区は別処理）
    "八王子市": "東京都", "立川市": "東京都", "武蔵野市": "東京都",
    "三鷹市": "東京都", "青梅市": "東京都", "昭島市": "東京都",
    "調布市": "東京都", "町田市": "東京都", "小金井市": "東京都",
    "小平市": "東京都", "日野市": "東京都", "東村山市": "東京都",
    "国分寺市": "東京都", "国立市": "東京都", "福生市": "東京都",
    "狛江市": "東京都", "東大和市": "東京都", "清瀬市": "東京都",
    "東久留米市": "東京都", "武蔵村山市": "東京都", "多摩市": "東京都",
    "稲城市": "東京都", "羽村市": "東京都", "あきる野市": "東京都",
    "西東京市": "東京都",
    # 府中市は広島県にもあるが東京都が一般的と判断
    "府中市": "東京都",
    # 千葉県
    "千葉市": "千葉県", "船橋市": "千葉県", "松戸市": "千葉県",
    "柏市": "千葉県", "市川市": "千葉県", "習志野市": "千葉県",
    "八千代市": "千葉県", "浦安市": "千葉県", "我孫子市": "千葉県",
    "流山市": "千葉県", "野田市": "千葉県", "鎌ケ谷市": "千葉県",
    "白井市": "千葉県", "印西市": "千葉県", "成田市": "千葉県",
    "四街道市": "千葉県", "佐倉市": "千葉県", "八街市": "千葉県",
    "市原市": "千葉県", "袖ケ浦市": "千葉県", "木更津市": "千葉県",
    "君津市": "千葉県", "富津市": "千葉県", "茂原市": "千葉県",
    "東金市": "千葉県", "大網白里市": "千葉県", "勝浦市": "千葉県",
    "いすみ市": "千葉県", "館山市": "千葉県", "鴨川市": "千葉県",
    "南房総市": "千葉県", "旭市": "千葉県", "銚子市": "千葉県",
    # 埼玉県
    "さいたま市": "埼玉県", "川越市": "埼玉県", "川口市": "埼玉県",
    "所沢市": "埼玉県", "春日部市": "埼玉県", "熊谷市": "埼玉県",
    "上尾市": "埼玉県", "草加市": "埼玉県", "越谷市": "埼玉県",
    "朝霞市": "埼玉県", "志木市": "埼玉県", "新座市": "埼玉県",
    "和光市": "埼玉県", "富士見市": "埼玉県", "三郷市": "埼玉県",
    "戸田市": "埼玉県", "蕨市": "埼玉県", "ふじみ野市": "埼玉県",
    "入間市": "埼玉県", "狭山市": "埼玉県", "飯能市": "埼玉県",
    "坂戸市": "埼玉県", "鶴ヶ島市": "埼玉県", "日高市": "埼玉県",
    "東松山市": "埼玉県", "本庄市": "埼玉県", "深谷市": "埼玉県",
    "桶川市": "埼玉県", "北本市": "埼玉県", "久喜市": "埼玉県",
    "加須市": "埼玉県", "羽生市": "埼玉県", "行田市": "埼玉県",
    "蓮田市": "埼玉県", "幸手市": "埼玉県", "白岡市": "埼玉県",
    "三芳町": "埼玉県", "毛呂山町": "埼玉県",
}

# 東京23区（都道府県が含まれない住所からの抽出用）
TOKYO_23_WARDS = (
    "千代田区", "中央区", "港区", "新宿区", "文京区", "台東区",
    "墨田区", "江東区", "品川区", "目黒区", "大田区", "世田谷区",
    "渋谷区", "中野区", "杉並区", "豊島区", "北区", "荒川区",
    "板橋区", "練馬区", "足立区", "葛飾区", "江戸川区",
)

# ハローワーク area 値 → 都道府県（最終フォールバック）
AREA_PREF_REVERSE = {
    "横浜": "神奈川県", "川崎": "神奈川県", "相模原": "神奈川県",
    "横須賀": "神奈川県", "鎌倉": "神奈川県", "藤沢": "神奈川県",
    "茅ヶ崎": "神奈川県", "平塚": "神奈川県", "大磯": "神奈川県",
    "秦野": "神奈川県", "伊勢原": "神奈川県", "厚木": "神奈川県",
    "大和": "神奈川県", "海老名": "神奈川県", "小田原": "神奈川県",
    "南足柄・開成": "神奈川県",
    "23区": "東京都", "多摩": "東京都",
    "さいたま": "埼玉県", "川口・戸田": "埼玉県",
    "所沢・入間": "埼玉県", "川越・東松山": "埼玉県",
    "越谷・草加": "埼玉県", "埼玉その他": "埼玉県",
    "千葉": "千葉県", "船橋・市川": "千葉県",
    "柏・松戸": "千葉県", "千葉その他": "千葉県",
}


# ========= 市区町村 → ハローワーク area 逆引きマップ（Phase1 #22） =========
# prefecture は埋まっているが area が空欄になっている 167件 (5.6%) を救済する。
# ハローワーク16エリアと同名の市区町村（「横浜」「川崎」「千葉」等）は上位判定を優先。
# 重複する場合は「より狭いエリア」が先に来るよう辞書順に並べる（Python 3.7+ は挿入順を保持）。
CITY_AREA_REVERSE = {
    # --- 神奈川県 ---
    # 政令市・中核市（ハローワーク area と市名が一致する場合はそのまま）
    "横浜市": "横浜", "川崎市": "川崎", "相模原市": "相模原",
    "横須賀市": "横須賀",
    "三浦市": "横須賀", "葉山町": "横須賀",  # 横須賀ハローワーク管轄
    "鎌倉市": "鎌倉", "逗子市": "鎌倉",  # 鎌倉所管
    "藤沢市": "藤沢", "寒川町": "藤沢",
    "茅ヶ崎市": "茅ヶ崎",
    "平塚市": "平塚", "二宮町": "平塚",
    "大磯町": "大磯",
    "秦野市": "秦野",
    "伊勢原市": "伊勢原",
    "厚木市": "厚木", "愛川町": "厚木", "清川村": "厚木",
    "海老名市": "海老名", "座間市": "海老名", "綾瀬市": "海老名",
    "大和市": "大和",
    "小田原市": "小田原", "箱根町": "小田原", "真鶴町": "小田原",
    "湯河原町": "小田原", "中井町": "小田原", "大井町": "小田原",
    "松田町": "小田原", "山北町": "小田原",
    "南足柄市": "南足柄・開成", "開成町": "南足柄・開成",
    # --- 東京都 ---
    # 23区（TOKYO_23_WARDS と同じ集合）
    "千代田区": "23区", "中央区": "23区", "港区": "23区", "新宿区": "23区",
    "文京区": "23区", "台東区": "23区", "墨田区": "23区", "江東区": "23区",
    "品川区": "23区", "目黒区": "23区", "大田区": "23区", "世田谷区": "23区",
    "渋谷区": "23区", "中野区": "23区", "杉並区": "23区", "豊島区": "23区",
    "北区": "23区", "荒川区": "23区", "板橋区": "23区", "練馬区": "23区",
    "足立区": "23区", "葛飾区": "23区", "江戸川区": "23区",
    # 多摩地域（東京市部+西多摩郡+南多摩郡+北多摩郡）
    "八王子市": "多摩", "立川市": "多摩", "武蔵野市": "多摩",
    "三鷹市": "多摩", "青梅市": "多摩", "昭島市": "多摩",
    "調布市": "多摩", "町田市": "多摩", "小金井市": "多摩",
    "小平市": "多摩", "日野市": "多摩", "東村山市": "多摩",
    "国分寺市": "多摩", "国立市": "多摩", "福生市": "多摩",
    "狛江市": "多摩", "東大和市": "多摩", "清瀬市": "多摩",
    "東久留米市": "多摩", "武蔵村山市": "多摩", "多摩市": "多摩",
    "稲城市": "多摩", "羽村市": "多摩", "あきる野市": "多摩",
    "西東京市": "多摩", "府中市": "多摩",
    "瑞穂町": "多摩", "日の出町": "多摩", "檜原村": "多摩",
    "奥多摩町": "多摩",
    # --- 千葉県 ---
    "千葉市": "千葉", "市原市": "千葉",  # 千葉ハローワーク所管
    "船橋市": "船橋・市川", "市川市": "船橋・市川", "浦安市": "船橋・市川",
    "習志野市": "船橋・市川", "八千代市": "船橋・市川",
    "柏市": "柏・松戸", "松戸市": "柏・松戸", "我孫子市": "柏・松戸",
    "流山市": "柏・松戸", "野田市": "柏・松戸", "鎌ケ谷市": "柏・松戸",
    "白井市": "柏・松戸",
    # 千葉その他（成田・印旛・外房・内房等の広域）
    "成田市": "千葉その他", "印西市": "千葉その他", "四街道市": "千葉その他",
    "佐倉市": "千葉その他", "八街市": "千葉その他", "富里市": "千葉その他",
    "袖ケ浦市": "千葉その他", "木更津市": "千葉その他", "君津市": "千葉その他",
    "富津市": "千葉その他", "茂原市": "千葉その他", "東金市": "千葉その他",
    "大網白里市": "千葉その他", "勝浦市": "千葉その他", "いすみ市": "千葉その他",
    "館山市": "千葉その他", "鴨川市": "千葉その他", "南房総市": "千葉その他",
    "旭市": "千葉その他", "銚子市": "千葉その他",
    # --- 埼玉県 ---
    "さいたま市": "さいたま",
    "川口市": "川口・戸田", "戸田市": "川口・戸田", "蕨市": "川口・戸田",
    "所沢市": "所沢・入間", "入間市": "所沢・入間", "狭山市": "所沢・入間",
    "飯能市": "所沢・入間", "日高市": "所沢・入間",
    "川越市": "川越・東松山", "東松山市": "川越・東松山",
    "坂戸市": "川越・東松山", "鶴ヶ島市": "川越・東松山",
    "越谷市": "越谷・草加", "草加市": "越谷・草加", "八潮市": "越谷・草加",
    "三郷市": "越谷・草加", "吉川市": "越谷・草加",
    # 埼玉その他（北部・中部の広域）
    "春日部市": "埼玉その他", "熊谷市": "埼玉その他", "上尾市": "埼玉その他",
    "朝霞市": "埼玉その他", "志木市": "埼玉その他", "新座市": "埼玉その他",
    "和光市": "埼玉その他", "富士見市": "埼玉その他", "ふじみ野市": "埼玉その他",
    "桶川市": "埼玉その他", "北本市": "埼玉その他", "久喜市": "埼玉その他",
    "加須市": "埼玉その他", "羽生市": "埼玉その他", "行田市": "埼玉その他",
    "蓮田市": "埼玉その他", "幸手市": "埼玉その他", "白岡市": "埼玉その他",
    "本庄市": "埼玉その他", "深谷市": "埼玉その他",
    "伊奈町": "埼玉その他", "三芳町": "埼玉その他", "毛呂山町": "埼玉その他",
}


def resolve_area(loc: str, pref: str, current_area: str) -> str:
    """area が空欄の場合、loc の市区町村名から逆引きしてハローワーク area 値を補完する。

    Args:
        loc: 住所文字列
        pref: resolve_prefecture で決定済みの都道府県（""可）
        current_area: 既存の area 値。非空ならそのまま返す

    Returns:
        area 値（空欄解消に成功した場合のみ変更、失敗時は current_area をそのまま返す）
    """
    area = (current_area or "").strip()
    if area:
        return area
    loc = (loc or "").strip()
    if not loc:
        return area
    # 23区チェック（loc に「○○区」が含まれる場合）
    for ward in TOKYO_23_WARDS:
        if ward in loc:
            return "23区"
    # 市区町村逆引き
    for city, mapped_area in CITY_AREA_REVERSE.items():
        if city in loc:
            return mapped_area
    # 都道府県が埋まっていれば「その他」カテゴリにフォールバック（ハローワーク区分に準拠）
    if pref == "千葉県":
        return "千葉その他"
    if pref == "埼玉県":
        return "埼玉その他"
    return area


def resolve_prefecture(loc: str, area: str) -> str:
    """都道府県を3段階で解決する。

    Args:
        loc: 住所文字列（work_location / work_address / employer_address）
        area: ハローワークのエリア値（例: "横浜", "23区"）

    Returns:
        都道府県名（"神奈川県"等）。解決できない場合は空文字。
    """
    loc = (loc or "").strip()
    area = (area or "").strip()

    # (1) 住所文字列に都道府県名が直接含まれる
    for p in PREFECTURES:
        if p in loc:
            return p

    # (2) 住所文字列に市区町村名が含まれる → 逆引き
    if loc:
        # 23区チェック（locに都道府県がない場合でも「○○区」で判定）
        for ward in TOKYO_23_WARDS:
            if ward in loc:
                return "東京都"
        # 市区町村名チェック
        for city, pref in CITY_PREF_MAP.items():
            if city in loc:
                return pref

    # (3) area 値から逆引き
    if area:
        pref = AREA_PREF_REVERSE.get(area, "")
        if pref:
            return pref

    return ""


def load_ranked_jobs():
    """ランク済み求人データを読み込み"""
    with open(RANKED_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("jobs", [])


def escape_sql(s):
    """SQL文字列エスケープ"""
    if s is None:
        return "NULL"
    s = str(s).replace("'", "''")
    return f"'{s}'"


# #16 派遣除外 / #17 保育園・幼稚園・学校求人除外（D1投入直前のセーフティネット）
EXCLUDE_EMP_TYPES = ("派遣",)
EXCLUDE_FACILITY_KEYWORDS = (
    "保育園", "幼稚園", "保育所", "認定こども園", "こども園",
    "学校", "小学校", "中学校", "高等学校", "高校", "特別支援学校",
)


def should_exclude_job(job):
    """派遣・保育園・幼稚園・学校求人を除外。(除外するか, 理由) を返す"""
    details = job.get("details", {}) or {}
    # #16 emp_type == '派遣' を除外
    emp_type = (details.get("emp_type") or job.get("employment_type") or "") or ""
    title = (job.get("job_title") or "") or ""
    for kw in EXCLUDE_EMP_TYPES:
        if kw in emp_type or kw in title:
            return True, f"emp_type={kw}"
    # #17 施設名・業種・職種名・仕事内容に保育園/幼稚園/学校キーワード
    haystack = " ".join([
        job.get("employer", "") or "",
        title,
        job.get("work_location", "") or "",
        job.get("employer_address", "") or "",
        (job.get("industry") or details.get("industry") or "") or "",
        (job.get("job_description", "") or "")[:300],
    ])
    for kw in EXCLUDE_FACILITY_KEYWORDS:
        if kw in haystack:
            return True, f"facility_kw={kw}"
    return False, ""


def build_sql(jobs):
    """全求人のINSERT文を生成"""
    lines = []
    lines.append("-- ハローワーク求人 D1投入SQL")
    lines.append(f"-- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 件数: {len(jobs)}")
    lines.append("")

    # テーブル再作成
    lines.append("DROP TABLE IF EXISTS jobs;")
    lines.append("""CREATE TABLE jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  kjno TEXT UNIQUE,
  employer TEXT NOT NULL,
  title TEXT,
  rank TEXT,
  score INTEGER,
  area TEXT,
  prefecture TEXT,
  work_location TEXT,
  salary_form TEXT,
  salary_min INTEGER,
  salary_max INTEGER,
  salary_display TEXT,
  bonus_text TEXT,
  holidays INTEGER,
  emp_type TEXT,
  station_text TEXT,
  shift1 TEXT,
  shift2 TEXT,
  description TEXT,
  welfare TEXT,
  score_sal INTEGER,
  score_hol INTEGER,
  score_bon INTEGER,
  score_emp INTEGER,
  score_wel INTEGER,
  score_loc INTEGER,
  contract_period TEXT,
  insurance TEXT,
  synced_at TEXT
);""")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_area ON jobs(area);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_prefecture ON jobs(prefecture);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_rank ON jobs(rank);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score DESC);")
    lines.append("CREATE INDEX IF NOT EXISTS idx_jobs_emp_type ON jobs(emp_type);")
    lines.append("")

    synced_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # #16/#17 除外カウンタ
    excluded_counts = {}
    kept_count = 0
    for j in jobs:
        excluded, reason = should_exclude_job(j)
        if excluded:
            excluded_counts[reason] = excluded_counts.get(reason, 0) + 1
            continue
        kept_count += 1
        details = j.get("details", {})
        bd = j.get("breakdown", {})

        # 勤務地: work_location → work_address → employer_address の順でフォールバック
        loc = (j.get("work_location") or "").strip()
        if not loc:
            loc = (j.get("work_address") or "").strip()
        if not loc:
            loc = (j.get("employer_address") or "").strip()

        # 都道府県を3段階で解決（loc直接抽出 → 市区町村逆引き → area逆引き）
        pref = resolve_prefecture(loc, j.get("area", ""))

        # #22 area 空欄救済: 市区町村逆引きで area を補完（既にある場合は保持）
        resolved_area = resolve_area(loc, pref, j.get("area", ""))

        # 年間休日数値
        holidays_str = j.get("annual_holidays", "")
        holidays_num = 0
        if holidays_str:
            m = re.search(r"(\d+)", str(holidays_str))
            if m:
                holidays_num = int(m.group(1))

        # 仕事内容（300文字制限）
        desc = (j.get("job_description", "") or "")[:300]

        # salary_formをsalary_displayから正確に判定
        sal_display = details.get("salary", "")
        sal_form = j.get("salary_form", "")
        if sal_display.startswith("月給"):
            sal_form = "月給"
        elif sal_display.startswith("時給"):
            sal_form = "時給"

        vals = [
            escape_sql(j.get("kjno", "")),
            escape_sql(j.get("employer", "")),
            escape_sql(j.get("job_title", "")),
            escape_sql(j.get("rank", "")),
            str(j.get("score", 0)),
            escape_sql(resolved_area),
            escape_sql(pref),
            escape_sql(loc),
            escape_sql(sal_form),
            str(j.get("salary_low", 0) or 0),
            str(j.get("salary_high", 0) or 0),
            escape_sql(details.get("salary", "")),
            escape_sql(details.get("bonus", "")),
            str(holidays_num),
            escape_sql(details.get("emp_type", "")),
            escape_sql(j.get("work_station_text", "")),
            escape_sql(j.get("shift1", "")),
            escape_sql(j.get("shift2", "")),
            escape_sql(desc),
            escape_sql(details.get("welfare", "")),
            str(bd.get("sal", 0)),
            str(bd.get("hol", 0)),
            str(bd.get("bon", 0)),
            str(bd.get("emp", 0)),
            str(bd.get("wel", 0)),
            str(bd.get("loc", 0)),
            escape_sql(j.get("contract_period", "")),
            escape_sql(j.get("insurance", "")),
            escape_sql(synced_at),
        ]

        lines.append(
            "INSERT OR IGNORE INTO jobs (kjno,employer,title,rank,score,area,prefecture,"
            "work_location,salary_form,salary_min,salary_max,salary_display,"
            "bonus_text,holidays,emp_type,station_text,shift1,shift2,"
            "description,welfare,score_sal,score_hol,score_bon,score_emp,"
            "score_wel,score_loc,contract_period,insurance,synced_at) VALUES ("
            + ",".join(vals) + ");"
        )

    # #16/#17 除外サマリをヘッダ直後のコメントとログに記録
    total_excluded = sum(excluded_counts.values())
    summary_lines = [
        f"-- 投入対象: {kept_count}件 / 除外: {total_excluded}件",
    ]
    for reason, cnt in sorted(excluded_counts.items(), key=lambda x: -x[1]):
        summary_lines.append(f"--   除外[{reason}]: {cnt}件")
    # ヘッダ直後（件数行の次）に挿入
    insert_at = 3
    lines[insert_at:insert_at] = summary_lines
    print(f"[Filter] 除外: 計{total_excluded}件 / 残存: {kept_count}件")
    for reason, cnt in sorted(excluded_counts.items(), key=lambda x: -x[1]):
        print(f"  除外[{reason}]: {cnt}件")

    return "\n".join(lines)


def deploy_to_d1(sql_file):
    """wrangler d1 execute でリモートD1に投入"""
    cmd = [
        "npx", "wrangler", "d1", "execute", D1_DB_NAME,
        "--config", str(WRANGLER_CONFIG),
        "--remote",
        "--file", str(sql_file),
    ]
    env = os.environ.copy()
    env.pop("CLOUDFLARE_API_TOKEN", None)  # OAuth認証を使う

    print(f"実行: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT / "api"), env=env,
                          capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"エラー: {result.stderr}")
        return False
    print(result.stdout)
    return True


def deploy_to_local(sql_text):
    """ローカルSQLiteに投入（テスト用）"""
    if LOCAL_DB.exists():
        LOCAL_DB.unlink()
    conn = sqlite3.connect(str(LOCAL_DB))
    conn.executescript(sql_text)
    # 確認
    cnt = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    print(f"ローカルDB: {LOCAL_DB} ({cnt}件)")
    return True


def print_prefecture_stats(jobs):
    """resolve_prefecture / resolve_area を全レコードに適用して統計を表示（DB更新なし）"""
    total = len(jobs)
    filled = 0
    empty = 0
    pref_counts = {}
    empty_samples = []
    # #22 area解消統計
    area_was_empty = 0
    area_resolved_from_empty = 0
    area_still_empty = 0
    area_still_empty_samples = []
    for j in jobs:
        loc = (j.get("work_location") or "").strip()
        if not loc:
            loc = (j.get("work_address") or "").strip()
        if not loc:
            loc = (j.get("employer_address") or "").strip()
        pref = resolve_prefecture(loc, j.get("area", ""))
        if pref:
            filled += 1
            pref_counts[pref] = pref_counts.get(pref, 0) + 1
        else:
            empty += 1
            if len(empty_samples) < 10:
                empty_samples.append({
                    "kjno": j.get("kjno", ""),
                    "area": j.get("area", ""),
                    "loc": loc[:60],
                })
        # area解消
        orig_area = (j.get("area") or "").strip()
        if not orig_area:
            area_was_empty += 1
            new_area = resolve_area(loc, pref, orig_area)
            if new_area:
                area_resolved_from_empty += 1
            else:
                area_still_empty += 1
                if len(area_still_empty_samples) < 10:
                    area_still_empty_samples.append({
                        "kjno": j.get("kjno", ""),
                        "pref": pref,
                        "loc": loc[:60],
                    })
    print(f"\n=== prefecture 解決統計 ===")
    print(f"  total: {total}")
    print(f"  filled: {filled} ({filled/total*100:.1f}%)")
    print(f"  empty:  {empty} ({empty/total*100:.1f}%)")
    for p in ["東京都", "神奈川県", "千葉県", "埼玉県"]:
        print(f"  {p}: {pref_counts.get(p, 0)}件")
    if empty_samples:
        print(f"\n未解決サンプル（最大10件）:")
        for s in empty_samples:
            print(f"  kjno={s['kjno']} area={s['area']!r} loc={s['loc']!r}")
    print(f"\n=== area 空欄救済統計 (#22) ===")
    print(f"  元々 area 空欄: {area_was_empty}件")
    print(f"  逆引きで埋まった: {area_resolved_from_empty}件 ({area_resolved_from_empty/max(1,area_was_empty)*100:.1f}%)")
    print(f"  まだ空欄: {area_still_empty}件")
    if area_still_empty_samples:
        print(f"\n逆引き失敗サンプル（最大10件）:")
        for s in area_still_empty_samples:
            print(f"  kjno={s['kjno']} pref={s['pref']!r} loc={s['loc']!r}")


def main():
    parser = argparse.ArgumentParser(description="ハローワーク求人 → D1 jobsテーブル投入")
    parser.add_argument("--dry-run", action="store_true", help="SQLファイル出力のみ")
    parser.add_argument("--local", action="store_true", help="ローカルSQLiteに投入")
    parser.add_argument("--stats-only", action="store_true",
                        help="prefecture解決統計のみ表示（DB/ファイル更新なし）")
    args = parser.parse_args()

    # データ読み込み
    jobs = load_ranked_jobs()
    print(f"入力: {len(jobs)}件のランク済み求人")

    if args.stats_only:
        print_prefecture_stats(jobs)
        return

    # ランク分布
    rank_counts = {}
    for j in jobs:
        r = j.get("rank", "?")
        rank_counts[r] = rank_counts.get(r, 0) + 1
    for r in ["S", "A", "B", "C", "D"]:
        print(f"  {r}ランク: {rank_counts.get(r, 0)}件")

    # SQL生成
    sql_text = build_sql(jobs)
    with open(SQL_OUTPUT, "w", encoding="utf-8") as f:
        f.write(sql_text)
    print(f"SQL出力: {SQL_OUTPUT}")

    if args.dry_run:
        print("(dry-run: D1更新なし)")
        return

    if args.local:
        deploy_to_local(sql_text)
        return

    # 本番D1に投入
    print("\n=== D1リモート投入 ===")
    success = deploy_to_d1(SQL_OUTPUT)
    if success:
        print("✅ D1 jobsテーブル更新完了")
    else:
        print("❌ D1投入失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
