#!/usr/bin/env python3
"""
ハローワーク求人情報提供API — 看護師求人取得スクリプト

毎朝06:30 cronで実行。M114（神奈川県・民間職業紹介事業者用）から
看護師関連求人をフィルタしてJSONに保存する。

使い方:
  python3 scripts/hellowork_fetch.py              # 全ページ取得
  python3 scripts/hellowork_fetch.py --test        # 1ページだけテスト
  python3 scripts/hellowork_fetch.py --stats       # 保存済みデータの統計表示
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "hellowork_nurse_jobs.json"
RAW_DIR = DATA_DIR / "hellowork_raw"

# API設定
API_BASE = "https://teikyo.hellowork.mhlw.go.jp/teikyo/api/2.0"
DATA_ID = "M114"  # 神奈川県・民間職業紹介事業者用一般求人

# 看護師フィルタキーワード
NURSE_KEYWORDS = ["看護", "ナース", "准看護", "訪問看護", "保健師", "助産師"]

# .envから認証情報読み込み
def load_env():
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print("❌ .envファイルが見つかりません")
        sys.exit(1)
    env = {}
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip()
    return env


def api_post(url, retries=2):
    """POST リクエストを送信してXMLレスポンスを返す（リトライ付き）"""
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, method="POST", data=b"")
        req.add_header("User-Agent", "HaruiMedical-HWClient/1.0")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode("utf-8")
                # XMLとして妥当か簡易チェック
                if not body.strip().startswith("<?xml") and not body.strip().startswith("<"):
                    print(f"⚠️ 非XMLレスポンス（リトライ {attempt+1}/{retries+1}）: {body[:200]}")
                    if attempt < retries:
                        import time; time.sleep(5)
                        continue
                    return None
                return body
        except urllib.error.HTTPError as e:
            if e.code == 503:
                print("⚠️ メンテナンス中（0-6時 or 月末21:30-翌6時）")
            else:
                print(f"❌ HTTP {e.code}: {e.reason}")
            if attempt < retries:
                import time; time.sleep(5)
                continue
            return None
        except Exception as e:
            print(f"❌ リクエスト失敗: {e}")
            if attempt < retries:
                import time; time.sleep(5)
                continue
            return None
    return None


def get_token(user_id, password):
    """トークン発行"""
    params = urllib.parse.urlencode({"id": user_id, "pass": password})
    xml_str = api_post(f"{API_BASE}/auth/getToken?{params}")
    if not xml_str:
        return None
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError as e:
        print(f"❌ XMLパースエラー: {e}")
        print(f"   レスポンス先頭200文字: {xml_str[:200]}")
        return None
    token = root.findtext("token")
    if not token:
        err = root.findtext("errorDetail", "不明なエラー")
        print(f"❌ 認証失敗: {err}")
        return None
    return token


def delete_token(token):
    """トークン破棄"""
    api_post(f"{API_BASE}/auth/delToken?token={token}")


def get_data_list(token):
    """求人一覧データ取得 → M114の情報を返す"""
    xml_str = api_post(f"{API_BASE}/kyujin?token={token}")
    if not xml_str:
        return None
    root = ET.fromstring(xml_str)
    for data in root.findall(".//data"):
        if data.findtext("data_id") == DATA_ID:
            return {
                "count": int(data.findtext("count", "0")),
                "pages": int(data.findtext("page", "0")),
            }
    print(f"❌ {DATA_ID}が見つかりません。利用権限を確認してください。")
    return None


def fetch_page(token, page):
    """指定ページの求人データを取得"""
    url = f"{API_BASE}/kyujin/{DATA_ID}/{page}?token={token}"
    xml_str = api_post(url)
    if not xml_str:
        return []
    root = ET.fromstring(xml_str)
    return root.findall(".//kyujin/data")


def is_nurse_job(data_elem):
    """看護師関連の求人か判定"""
    fields_to_check = [
        "sksu",                # 職種
        "shigoto_ny",          # 仕事内容
        "menkyo_skkuyohi1_n",  # 免許・資格1
        "menkyo_skkuyohi2_n",  # 免許・資格2
        "menkyo_skkuyohi3_n",  # 免許・資格3
        "hynamenkyo_snta",     # 必要な免許資格その他
    ]
    text = " ".join(data_elem.findtext(f, "") for f in fields_to_check)
    return any(kw in text for kw in NURSE_KEYWORDS)


def parse_job(data_elem):
    """XMLのdata要素から必要なフィールドを抽出してdictにする"""
    def t(tag):
        return (data_elem.findtext(tag) or "").strip()

    # 基本給の数値化
    salary_low = t("khkykagen")
    salary_high = t("khkyjgn")

    return {
        # 求人識別
        "kjno": t("kjno"),                           # 求人番号
        "uktkymd": t("uktkymd_seireki"),             # 受付日
        "kjyukoymd": t("kjyukoymd"),                 # 有効期限

        # 事業所
        "employer": t("jgshmei"),                    # 事業所名
        "employer_kana": t("jgshmeikana"),           # 事業所名カナ
        "employer_address": t("jgshszci"),           # 事業所住所
        "employer_url": t("jgshhp"),                 # HP

        # 職種・仕事
        "job_title": t("sksu"),                      # 職種
        "job_description": t("shigoto_ny"),          # 仕事内容
        "industry": t("sngbrui_n"),                  # 産業分類

        # 勤務地
        "work_location": t("shgbsjusho1_n"),         # 就業場所1
        "work_address": t("shgbsjusho"),             # 就業場所住所
        "work_station": t("shgbs_myre"),             # 最寄り駅
        "work_station_text": t("shgbs_myremjr"),     # 最寄り駅文字列

        # 雇用条件
        "employment_type": t("koyokeitai_n"),        # 雇用形態
        "full_part": t("kjkbn2_n"),                  # フルタイム/パート
        "permanent_hire": t("ssintoyo_umu_n"),       # 正社員登用

        # 給与
        "salary_low": salary_low,                    # 基本給下限
        "salary_high": salary_high,                  # 基本給上限
        "salary_text": t("khky"),                    # 基本給テキスト
        "salary_form": t("chgnkeitai_n"),            # 賃金形態（月給/時給等）
        "bonus": t("shoyoumu_n"),                    # 賞与有無
        "bonus_detail": t("shoyo"),                  # 賞与詳細
        "raise": t("shkyumu_n"),                     # 昇給有無

        # 勤務時間
        "work_hours": t("shgjn"),                    # 就業時間区分
        "shift1": t("shgjn1_open_close"),            # 就業時間1
        "shift2": t("shgjn2_open_close"),            # 就業時間2
        "shift3": t("shgjn3_open_close"),            # 就業時間3
        "overtime": t("jkgi_umu_n"),                 # 時間外労働
        "overtime_avg": t("jkgi_thkinjn_ji_n"),      # 時間外月平均

        # 休日
        "holidays": t("kyjs"),                       # 休日
        "annual_holidays": t("nenkankjsu_n"),        # 年間休日数
        "weekdays_off": ", ".join(filter(None, [
            "月" if t("kyjs_mon") else "",
            "火" if t("kyjs_tue") else "",
            "水" if t("kyjs_wed") else "",
            "木" if t("kyjs_thu") else "",
            "金" if t("kyjs_fri") else "",
            "土" if t("kyjs_sat") else "",
            "日" if t("kyjs_sun") else "",
        ])),

        # 資格
        "license1": t("menkyo_skkuyohi1_n"),         # 免許・資格1
        "license2": t("menkyo_skkuyohi2_n"),         # 免許・資格2
        "license3": t("menkyo_skkuyohi3_n"),         # 免許・資格3

        # 福利厚生
        "insurance": t("knyuhkn"),                   # 加入保険
        "retirement": t("tskknseido_n"),             # 退職金制度
        "childcare": t("tkjshsetu_n"),               # 託児施設
        "car_commute": t("mycartsknkahi_n"),         # マイカー通勤
        "smoking": t("shgbs_okni_jdktentisk_n"),     # 受動喫煙対策

        # メタ
        "fetched_at": datetime.now().isoformat(),
    }


def show_stats():
    """保存済みデータの統計を表示"""
    if not OUTPUT_FILE.exists():
        print("❌ データファイルが見つかりません。先に取得してください。")
        return

    with open(OUTPUT_FILE) as f:
        data = json.load(f)

    jobs = data.get("jobs", [])
    print(f"📊 ハローワーク看護師求人データ統計")
    print(f"   取得日時: {data.get('fetched_at', '不明')}")
    print(f"   全求人数: {data.get('total_all', '不明')}件")
    print(f"   看護師求人: {len(jobs)}件")
    print()

    # 雇用形態別
    types = {}
    for j in jobs:
        t = j.get("employment_type", "不明")
        types[t] = types.get(t, 0) + 1
    print("   【雇用形態別】")
    for t, c in sorted(types.items(), key=lambda x: -x[1]):
        print(f"     {t}: {c}件")

    # エリア別
    areas = {}
    for j in jobs:
        loc = j.get("work_location", "")
        city = loc.replace("神奈川県", "") if loc else "不明"
        # 市区町村レベルで集計
        for suffix in ["市", "区", "町", "村"]:
            idx = city.find(suffix)
            if idx >= 0:
                city = city[:idx+1]
                break
        areas[city] = areas.get(city, 0) + 1
    print("\n   【エリア別 TOP10】")
    for a, c in sorted(areas.items(), key=lambda x: -x[1])[:10]:
        print(f"     {a}: {c}件")


def main():
    parser = argparse.ArgumentParser(description="ハローワーク看護師求人取得")
    parser.add_argument("--test", action="store_true", help="1ページだけテスト取得")
    parser.add_argument("--stats", action="store_true", help="保存済みデータの統計表示")
    parser.add_argument("--save-raw", action="store_true", help="生XMLも保存")
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    env = load_env()
    user_id = env.get("HELLOWORK_USER_ID")
    password = env.get("HELLOWORK_PASSWORD")

    if not user_id or not password:
        print("❌ .envにHELLOWORK_USER_ID/HELLOWORK_PASSWORDを設定してください")
        sys.exit(1)

    print(f"🔑 トークン取得中...")
    token = get_token(user_id, password)
    if not token:
        sys.exit(1)
    print(f"✅ トークン取得成功")

    try:
        # M114の情報取得
        info = get_data_list(token)
        if not info:
            sys.exit(1)
        total_count = info["count"]
        total_pages = info["pages"]
        print(f"📦 {DATA_ID}: 全{total_count}件 ({total_pages}ページ)")

        max_pages = 1 if args.test else total_pages
        all_nurse_jobs = []

        for page in range(1, max_pages + 1):
            print(f"   ページ {page}/{max_pages} 取得中...", end=" ", flush=True)
            records = fetch_page(token, page)

            if args.save_raw:
                RAW_DIR.mkdir(parents=True, exist_ok=True)

            nurse_count = 0
            for rec in records:
                if is_nurse_job(rec):
                    job = parse_job(rec)
                    all_nurse_jobs.append(job)
                    nurse_count += 1

            print(f"{len(records)}件中 看護師{nurse_count}件")

            # レートリミット対策
            if page < max_pages:
                time.sleep(1)

        # JSON保存
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output = {
            "fetched_at": datetime.now().isoformat(),
            "data_id": DATA_ID,
            "total_all": total_count,
            "total_nurse": len(all_nurse_jobs),
            "pages_fetched": max_pages,
            "jobs": all_nurse_jobs,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 完了: 看護師求人 {len(all_nurse_jobs)}件 → {OUTPUT_FILE}")

        if args.test:
            print(f"   ※テストモード: 1ページのみ取得。全件取得は --test なしで実行")

    finally:
        print("🔓 トークン破棄中...")
        delete_token(token)
        print("✅ トークン破棄完了")


if __name__ == "__main__":
    main()
