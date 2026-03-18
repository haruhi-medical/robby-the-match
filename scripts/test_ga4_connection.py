#!/usr/bin/env python3
"""
GA4 Data API + Search Console API 接続テスト
使い方: python3 scripts/test_ga4_connection.py
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    print("[NG] python-dotenv がインストールされていません")
    print("     pip3 install python-dotenv")
    sys.exit(1)

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GA4_CREDENTIALS_PATH = os.getenv("GA4_CREDENTIALS_PATH", "")
SC_SITE_URL = os.getenv("SC_SITE_URL", "https://quads-nurse.com/")

# Resolve relative path
if GA4_CREDENTIALS_PATH and not os.path.isabs(GA4_CREDENTIALS_PATH):
    GA4_CREDENTIALS_PATH = str(Path(__file__).parent.parent / GA4_CREDENTIALS_PATH)

PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"\033[0;32m[OK]\033[0m {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"\033[0;31m[NG]\033[0m {msg}")


def warn(msg):
    print(f"\033[1;33m[!!]\033[0m {msg}")


def test_env():
    """環境変数チェック"""
    print("=== 1. 環境変数チェック ===")
    if GA4_PROPERTY_ID:
        ok(f"GA4_PROPERTY_ID = {GA4_PROPERTY_ID}")
        # Must be numeric
        if GA4_PROPERTY_ID.isdigit():
            ok("GA4_PROPERTY_ID は数値 (正しい形式)")
        else:
            fail(f"GA4_PROPERTY_ID が数値ではありません: {GA4_PROPERTY_ID}")
            warn("GA4管理画面 > プロパティ設定 で数値のプロパティIDを確認してください")
            warn("G-X4G2BYW13B は測定IDであり、プロパティIDではありません")
    else:
        fail("GA4_PROPERTY_ID が未設定")
        warn(".env に GA4_PROPERTY_ID=数値 を設定してください")

    if GA4_CREDENTIALS_PATH:
        ok(f"GA4_CREDENTIALS_PATH = {GA4_CREDENTIALS_PATH}")
        if os.path.exists(GA4_CREDENTIALS_PATH):
            ok(f"認証ファイル存在: {GA4_CREDENTIALS_PATH}")
        else:
            fail(f"認証ファイルが見つかりません: {GA4_CREDENTIALS_PATH}")
    else:
        fail("GA4_CREDENTIALS_PATH が未設定")

    if SC_SITE_URL:
        ok(f"SC_SITE_URL = {SC_SITE_URL}")
    else:
        fail("SC_SITE_URL が未設定")

    print()


def test_ga4():
    """GA4 Data API 接続テスト"""
    print("=== 2. GA4 Data API テスト ===")

    if not GA4_PROPERTY_ID or not GA4_CREDENTIALS_PATH:
        fail("GA4設定不足のためスキップ")
        print()
        return

    if not os.path.exists(GA4_CREDENTIALS_PATH):
        fail("認証ファイルが存在しないためスキップ")
        print()
        return

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, DateRange, Metric,
        )
        from google.oauth2.service_account import Credentials
        ok("ライブラリ import 成功")
    except ImportError as e:
        fail(f"ライブラリ import 失敗: {e}")
        warn("pip3 install google-analytics-data google-auth")
        print()
        return

    try:
        creds = Credentials.from_service_account_file(GA4_CREDENTIALS_PATH)
        ok("認証情報読み込み成功")
        sa_email = creds.service_account_email
        ok(f"サービスアカウント: {sa_email}")
    except Exception as e:
        fail(f"認証情報読み込み失敗: {e}")
        print()
        return

    try:
        client = BetaAnalyticsDataClient(credentials=creds)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        req = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
            metrics=[Metric(name="activeUsers")],
        )
        resp = client.run_report(req)
        if resp.rows:
            users = resp.rows[0].metric_values[0].value
            ok(f"GA4 データ取得成功! 昨日のアクティブユーザー: {users}")
        else:
            ok("GA4 接続成功 (昨日のデータなし)")
    except Exception as e:
        err_str = str(e)
        fail(f"GA4 API エラー: {err_str[:200]}")
        if "403" in err_str or "PERMISSION_DENIED" in err_str:
            warn("サービスアカウントにGA4プロパティへのアクセス権限がありません")
            warn("GA4管理画面 > プロパティのアクセス管理 でサービスアカウントを追加してください")
        elif "404" in err_str or "NOT_FOUND" in err_str:
            warn(f"プロパティID {GA4_PROPERTY_ID} が見つかりません")
            warn("GA4管理画面 > プロパティ設定 で正しい数値IDを確認してください")
        elif "API has not been" in err_str or "DISABLED" in err_str:
            warn("Google Analytics Data API が有効化されていません")
            warn("https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com")

    print()


def test_search_console():
    """Search Console API 接続テスト"""
    print("=== 3. Search Console API テスト ===")

    if not GA4_CREDENTIALS_PATH:
        fail("認証ファイル未設定のためスキップ")
        print()
        return

    if not os.path.exists(GA4_CREDENTIALS_PATH):
        fail("認証ファイルが存在しないためスキップ")
        print()
        return

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        ok("ライブラリ import 成功")
    except ImportError as e:
        fail(f"ライブラリ import 失敗: {e}")
        warn("pip3 install google-api-python-client google-auth")
        print()
        return

    try:
        creds = Credentials.from_service_account_file(
            GA4_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds)
        ok("Search Console クライアント作成成功")
    except Exception as e:
        fail(f"クライアント作成失敗: {e}")
        print()
        return

    try:
        # List sites to verify access
        sites = service.sites().list().execute()
        site_list = sites.get("siteEntry", [])
        if site_list:
            ok(f"アクセス可能なサイト: {len(site_list)}件")
            for s in site_list:
                url = s.get("siteUrl", "?")
                level = s.get("permissionLevel", "?")
                print(f"     - {url} ({level})")
        else:
            warn("アクセス可能なサイトが0件")
            warn("Search Console でサービスアカウントをユーザーとして追加してください")
    except Exception as e:
        fail(f"サイト一覧取得エラー: {e}")

    # Try query
    try:
        target_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        result = service.searchanalytics().query(
            siteUrl=SC_SITE_URL,
            body={
                "startDate": target_date,
                "endDate": target_date,
                "dimensions": [],
            },
        ).execute()

        rows = result.get("rows", [])
        if rows:
            r = rows[0]
            ok(f"SC データ取得成功! ({target_date})")
            print(f"     クリック: {r.get('clicks', 0)}, 表示: {r.get('impressions', 0)}, "
                  f"CTR: {r.get('ctr', 0)*100:.1f}%, 平均順位: {r.get('position', 0):.1f}")
        else:
            ok(f"SC 接続成功 ({target_date} のデータなし)")
    except Exception as e:
        err_str = str(e)
        fail(f"SC クエリエラー: {err_str[:200]}")
        if "403" in err_str:
            warn(f"サービスアカウントに {SC_SITE_URL} へのアクセス権限がありません")
            warn("Search Console > 設定 > ユーザーと権限 でサービスアカウントを追加してください")
        elif "API has not been" in err_str or "DISABLED" in err_str:
            warn("Search Console API が有効化されていません")
            warn("https://console.cloud.google.com/apis/library/searchconsole.googleapis.com")

    print()


def main():
    print("=" * 50)
    print(" GA4 + Search Console API 接続テスト")
    print("=" * 50)
    print()

    test_env()
    test_ga4()
    test_search_console()

    print("=" * 50)
    print(f" 結果: {PASS} OK / {FAIL} NG")
    print("=" * 50)

    if FAIL > 0:
        print()
        print("セットアップガイドを実行:")
        print("  bash scripts/setup_ga4_api.sh")
        sys.exit(1)
    else:
        print()
        print("全テスト通過! ga4_report.py を実行できます:")
        print("  python3 scripts/ga4_report.py")


if __name__ == "__main__":
    main()
