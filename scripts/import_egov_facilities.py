#!/usr/bin/env python3
"""
e-Gov医療情報ネット CSV → D1インポートスクリプト
全47都道府県の病院・診療所をダウンロードしてJSON化

Usage:
  python3 scripts/import_egov_facilities.py --download   # CSVダウンロード+パース
  python3 scripts/import_egov_facilities.py --import     # D1にインポート
  python3 scripts/import_egov_facilities.py --all        # 全部やる
  python3 scripts/import_egov_facilities.py --kanto-only # 関東4都県のみ（旧挙動）
"""

import csv
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

BASE_URL = "https://www.mhlw.go.jp/content/11121000"
DATA_DIR = Path(__file__).parent.parent / "data" / "egov"
OUTPUT_JSON = DATA_DIR / "facilities_all_japan.json"

# ダウンロード対象（病院+診療所の施設票）
CSV_FILES = {
    "hospital": f"{BASE_URL}/01-1_hospital_facility_info_20251201.zip",
    "clinic": f"{BASE_URL}/02-1_clinic_facility_info_20251201.zip",
}

# 全47都道府県マッピング (JISコード → 都道府県名)
PREF_CODES_ALL = {
    '01': '北海道', '02': '青森県', '03': '岩手県', '04': '宮城県',
    '05': '秋田県', '06': '山形県', '07': '福島県',
    '08': '茨城県', '09': '栃木県', '10': '群馬県',
    '11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県',
    '15': '新潟県', '16': '富山県', '17': '石川県', '18': '福井県',
    '19': '山梨県', '20': '長野県',
    '21': '岐阜県', '22': '静岡県', '23': '愛知県', '24': '三重県',
    '25': '滋賀県', '26': '京都府', '27': '大阪府', '28': '兵庫県',
    '29': '奈良県', '30': '和歌山県',
    '31': '鳥取県', '32': '島根県', '33': '岡山県', '34': '広島県', '35': '山口県',
    '36': '徳島県', '37': '香川県', '38': '愛媛県', '39': '高知県',
    '40': '福岡県', '41': '佐賀県', '42': '長崎県', '43': '熊本県',
    '44': '大分県', '45': '宮崎県', '46': '鹿児島県', '47': '沖縄県',
}

# 対象都道府県（デフォルト: 全国47）
KANTO_PREFECTURES = {"東京都", "神奈川県", "千葉県", "埼玉県"}

def download_and_extract():
    """CSVをダウンロードして解凍"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for name, url in CSV_FILES.items():
        zip_path = DATA_DIR / f"{name}.zip"
        print(f"[{name}] Downloading from {url}...")
        try:
            urlretrieve(url, zip_path)
            print(f"[{name}] Downloaded: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
        except Exception as e:
            print(f"[{name}] Download failed: {e}")
            continue

        # 解凍
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(DATA_DIR / name)
                print(f"[{name}] Extracted: {z.namelist()}")
        except Exception as e:
            print(f"[{name}] Extract failed: {e}")

def find_csv_files():
    """解凍済みCSVファイルを検索"""
    csvs = []
    for name in CSV_FILES:
        dir_path = DATA_DIR / name
        if dir_path.exists():
            for f in dir_path.rglob("*.csv"):
                csvs.append((name, f))
    return csvs

def parse_facilities(kanto_only=False):
    """CSVを読み込んで指定範囲の施設を抽出（デフォルト: 全国47）"""
    csv_files = find_csv_files()
    if not csv_files:
        print("No CSV files found. Run with --download first.")
        return []

    facilities = []

    # 都道府県コード→名前マッピング
    if kanto_only:
        PREF_CODES = {'11': '埼玉県', '12': '千葉県', '13': '東京都', '14': '神奈川県'}
        TARGET_PREFECTURES = KANTO_PREFECTURES
    else:
        PREF_CODES = PREF_CODES_ALL
        TARGET_PREFECTURES = set(PREF_CODES_ALL.values())
    TARGET_CODES = set(PREF_CODES.keys())

    for category, csv_path in csv_files:
        print(f"\nParsing {csv_path.name}...")

        # UTF-8-BOM対応
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            print(f"  Columns ({len(headers)}): {headers[:15]}...")

            count = 0
            matched = 0
            for row in reader:
                count += 1

                # 都道府県コードでフィルタ
                pref_code = (row.get('都道府県コード', '') or '').strip()
                if pref_code not in TARGET_CODES:
                    # 所在地テキストでもチェック
                    addr_text = row.get('所在地', '') or ''
                    matched_pref = None
                    for p in TARGET_PREFECTURES:
                        if p in addr_text:
                            matched_pref = p
                            break
                    if not matched_pref:
                        continue
                    pref = matched_pref
                else:
                    pref = PREF_CODES[pref_code]

                matched += 1

                # 施設名
                name = row.get('正式名称', '') or row.get('略称', '') or ''

                # 住所
                address = row.get('所在地', '') or ''
                # 市区町村を住所から抽出
                city = ''
                if pref in address:
                    after_pref = address[len(pref):]
                    # 「市」「区」「町」「村」で区切る
                    for suffix in ['市', '区', '町', '村', '郡']:
                        idx = after_pref.find(suffix)
                        if idx >= 0:
                            city = after_pref[:idx + 1]
                            break

                # 座標
                lat = row.get('所在地座標（緯度）', '') or ''
                lng = row.get('所在地座標（経度）', '') or ''

                # 病床数
                beds = row.get('合計病床数', '') or row.get('一般病床', '') or ''

                # 診療科（このCSVには含まれないかも）
                departments = ''

                # カテゴリ判定
                if category == 'hospital':
                    cat = '病院'
                    # サブタイプ推定
                    sub_type = None
                    dept_str = departments.lower() if departments else ''
                    if '精神' in dept_str or '心療' in dept_str:
                        sub_type = '精神科'
                    elif '回復期' in name or 'リハビリ' in name:
                        sub_type = '回復期'
                    elif '療養' in name:
                        sub_type = '療養型'
                else:
                    cat = 'クリニック'
                    sub_type = None
                    if '訪問看護' in name:
                        cat = '訪問看護ST'
                    elif '介護' in name or '老健' in name:
                        cat = '介護施設'

                facility = {
                    'name': name.strip(),
                    'category': cat,
                    'sub_type': sub_type,
                    'prefecture': pref.strip(),
                    'city': city.strip(),
                    'address': address.strip(),
                    'lat': float(lat) if lat and lat not in ('', '0', '0.0') and lat.replace('.', '').replace('-', '').isdigit() else None,
                    'lng': float(lng) if lng and lng not in ('', '0', '0.0') and lng.replace('.', '').replace('-', '').isdigit() else None,
                    'bed_count': int(beds) if beds and beds.isdigit() else None,
                    'departments': departments.strip() if departments else None,
                    'source': 'egov_csv',
                }

                if facility['name']:  # 名前がない施設はスキップ
                    facilities.append(facility)

            scope = "関東4都県" if kanto_only else "全国47都道府県"
            print(f"  Total: {count}, Matched ({scope}): {matched}")

    print(f"\n=== Total facilities: {len(facilities)} ===")

    # 重複除去（名前+住所で判定）
    seen = set()
    unique = []
    for f in facilities:
        key = f"{f['name']}_{f['address']}"
        if key not in seen:
            seen.add(key)
            unique.append(f)

    print(f"After dedup: {len(unique)}")
    return unique

def save_json(facilities):
    """JSONファイルに保存"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(facilities, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT_JSON} ({len(facilities)} facilities)")

def _format_insert(fac):
    name = fac['name'].replace("'", "''")
    category = fac['category']
    sub_type = (fac.get('sub_type') or '').replace("'", "''")
    pref = fac['prefecture']
    city = (fac.get('city') or '').replace("'", "''")
    addr = (fac.get('address') or '').replace("'", "''")
    lat = fac.get('lat')
    lng = fac.get('lng')
    bed = fac.get('bed_count')
    depts = (fac.get('departments') or '').replace("'", "''")
    src = fac['source']
    lat_val = str(lat) if isinstance(lat, (int, float)) and lat else 'NULL'
    lng_val = str(lng) if isinstance(lng, (int, float)) and lng else 'NULL'
    bed_val = str(bed) if isinstance(bed, int) and bed else 'NULL'
    return (
        f"INSERT INTO facilities (name, category, sub_type, prefecture, city, address, lat, lng, bed_count, departments, source, last_synced_at) "
        f"VALUES ('{name}', '{category}', '{sub_type}', '{pref}', '{city}', '{addr}', {lat_val}, {lng_val}, {bed_val}, '{depts}', '{src}', datetime('now'));"
    )


def import_to_d1(facilities, batch_size=5000):
    """D1にインポート（バッチ分割でwrangler d1 execute）"""
    if not facilities:
        print("No facilities to import")
        return

    # 既存egov_csvを削除
    delete_sql = DATA_DIR / "delete_egov.sql"
    with open(delete_sql, 'w', encoding='utf-8') as f:
        f.write("DELETE FROM facilities WHERE source = 'egov_csv';\n")
    print(f"\n[1/2] Deleting old egov_csv rows...")
    result = subprocess.run(
        ["npx", "wrangler", "d1", "execute", "nurse-robby-db", f"--file={delete_sql}", "--remote", "--config", "wrangler.toml"],
        cwd=str(Path(__file__).parent.parent / "api"),
        capture_output=True, text=True,
        env={**os.environ, "CLOUDFLARE_API_TOKEN": ""},
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[-500:]}")
        return
    print(f"  ✅ delete done")

    # バッチ分割でINSERT
    n_batches = (len(facilities) + batch_size - 1) // batch_size
    print(f"\n[2/2] Inserting {len(facilities)} facilities in {n_batches} batches of {batch_size}...")

    for batch_idx in range(n_batches):
        start = batch_idx * batch_size
        end = min(start + batch_size, len(facilities))
        batch = facilities[start:end]

        sql_path = DATA_DIR / f"import_batch_{batch_idx:03d}.sql"
        with open(sql_path, 'w', encoding='utf-8') as f:
            for fac in batch:
                if fac.get('name'):
                    f.write(_format_insert(fac) + "\n")

        size_kb = sql_path.stat().st_size / 1024
        print(f"  Batch {batch_idx+1}/{n_batches}: {len(batch)} rows ({size_kb:.0f} KB)...", end=" ", flush=True)

        result = subprocess.run(
            ["npx", "wrangler", "d1", "execute", "nurse-robby-db", f"--file={sql_path}", "--remote", "--config", "wrangler.toml"],
            cwd=str(Path(__file__).parent.parent / "api"),
            capture_output=True, text=True,
            env={**os.environ, "CLOUDFLARE_API_TOKEN": ""},
        )
        if result.returncode != 0:
            print(f"❌ FAILED")
            print(f"    stderr: {result.stderr[-300:]}")
            return
        else:
            print(f"✅")
            sql_path.unlink()  # 成功したら削除

    print(f"\n✅ D1 import complete: {len(facilities)} facilities")

def main():
    args = sys.argv[1:]
    kanto_only = '--kanto-only' in args

    if '--download' in args or '--all' in args:
        download_and_extract()

    facilities = parse_facilities(kanto_only=kanto_only)

    if facilities:
        save_json(facilities)

    if '--import' in args or '--all' in args:
        if not facilities:
            # JSONから読み込み
            if OUTPUT_JSON.exists():
                with open(OUTPUT_JSON, 'r', encoding='utf-8') as f:
                    facilities = json.load(f)
                print(f"Loaded {len(facilities)} facilities from JSON")
        import_to_d1(facilities)

if __name__ == '__main__':
    main()
