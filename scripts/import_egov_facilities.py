#!/usr/bin/env python3
"""
e-Gov医療情報ネット CSV → D1インポートスクリプト
神奈川県 + 東京都の病院・診療所をダウンロードしてJSON化

Usage:
  python3 scripts/import_egov_facilities.py --download   # CSVダウンロード+パース
  python3 scripts/import_egov_facilities.py --import     # D1にインポート
  python3 scripts/import_egov_facilities.py --all        # 全部やる
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
OUTPUT_JSON = DATA_DIR / "facilities_kanagawa_tokyo.json"

# ダウンロード対象（病院+診療所の施設票）
CSV_FILES = {
    "hospital": f"{BASE_URL}/01-1_hospital_facility_info_20251201.zip",
    "clinic": f"{BASE_URL}/02-1_clinic_facility_info_20251201.zip",
}

# 対象都道府県
TARGET_PREFECTURES = {"神奈川県", "東京都"}

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

def parse_facilities():
    """CSVを読み込んで神奈川+東京の施設を抽出"""
    csv_files = find_csv_files()
    if not csv_files:
        print("No CSV files found. Run with --download first.")
        return []

    facilities = []

    # 都道府県コード→名前マッピング
    PREF_CODES = {'13': '東京都', '14': '神奈川県'}
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
                    if not any(p in addr_text for p in TARGET_PREFECTURES):
                        continue
                    pref = '東京都' if '東京都' in addr_text else '神奈川県'
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

            print(f"  Total: {count}, Matched (神奈川+東京): {matched}")

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

def import_to_d1(facilities):
    """D1にインポート（wrangler d1 execute）"""
    if not facilities:
        print("No facilities to import")
        return

    # SQLファイル生成
    sql_path = DATA_DIR / "import.sql"
    with open(sql_path, 'w', encoding='utf-8') as f:
        f.write("DELETE FROM facilities WHERE source = 'egov_csv';\n\n")

        batch = []
        for i, fac in enumerate(facilities):
            vals = (
                fac['name'].replace("'", "''"),
                fac['category'],
                fac.get('sub_type') or '',
                fac['prefecture'],
                fac.get('city', ''),
                fac.get('address', '').replace("'", "''"),
                fac.get('lat') or 'NULL',
                fac.get('lng') or 'NULL',
                fac.get('bed_count') or 'NULL',
                (fac.get('departments') or '').replace("'", "''"),
                fac['source'],
            )
            lat_val = str(vals[6]) if vals[6] != 'NULL' else 'NULL'
            lng_val = str(vals[7]) if vals[7] != 'NULL' else 'NULL'
            bed_val = str(vals[8]) if vals[8] != 'NULL' else 'NULL'

            f.write(
                f"INSERT INTO facilities (name, category, sub_type, prefecture, city, address, lat, lng, bed_count, departments, source, last_synced_at) "
                f"VALUES ('{vals[0]}', '{vals[1]}', '{vals[2]}', '{vals[3]}', '{vals[4]}', '{vals[5]}', {lat_val}, {lng_val}, {bed_val}, '{vals[9]}', '{vals[10]}', datetime('now'));\n"
            )

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/{len(facilities)} INSERT statements...")

    print(f"SQL file: {sql_path} ({sql_path.stat().st_size / 1024:.0f} KB)")

    # wrangler d1 execute
    print("\nImporting to D1...")
    result = subprocess.run(
        ["npx", "wrangler", "d1", "execute", "nurse-robby-db", f"--file={sql_path}", "--remote", "--config", "wrangler.toml"],
        cwd=str(Path(__file__).parent.parent / "api"),
        capture_output=True, text=True,
        env={**os.environ, "CLOUDFLARE_API_TOKEN": ""},
    )
    print(result.stdout[-500:] if result.stdout else "")
    if result.returncode != 0:
        print(f"Error: {result.stderr[-500:]}")
    else:
        print("D1 import complete!")

def main():
    args = sys.argv[1:]

    if '--download' in args or '--all' in args:
        download_and_extract()

    facilities = parse_facilities()

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
