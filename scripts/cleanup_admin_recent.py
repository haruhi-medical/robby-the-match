#!/usr/bin/env python3
"""admin:recent:* と U_TEST_* 関連 KV を Cloudflare KV API で一括削除"""
import os
import sys
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

ACCOUNT_ID = "27d40459bf74cd28d5ab5df6b8084e01"
NAMESPACE_ID = "c523fb0833e2482cbfc58eef8824c7b0"  # LINE_SESSIONS

# .env から API token を読む
def load_env():
    env = {}
    with open(os.path.expanduser("~/robby-the-match/.env")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

env = load_env()
TOKEN = env.get("CLOUDFLARE_API_TOKEN")
if not TOKEN:
    print("ERROR: CLOUDFLARE_API_TOKEN not in .env")
    sys.exit(1)

BASE = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def list_keys(prefix, limit=1000):
    """Cursor pagination で全 key 取得"""
    all_keys = []
    cursor = None
    while True:
        params = {"prefix": prefix, "limit": limit}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{BASE}/keys", headers=HEADERS, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        result = data.get("result", [])
        all_keys.extend([k["name"] for k in result])
        cursor = data.get("result_info", {}).get("cursor")
        if not cursor:
            break
    return all_keys


def bulk_delete(keys, batch_size=10000):
    """Bulk delete API で一気に削除"""
    deleted = 0
    for i in range(0, len(keys), batch_size):
        batch = keys[i : i + batch_size]
        r = requests.delete(f"{BASE}/bulk", headers=HEADERS, json=batch, timeout=60)
        if r.ok:
            deleted += len(batch)
            print(f"  bulk delete {i}–{i + len(batch) - 1}: ok")
        else:
            print(f"  ERROR {r.status_code}: {r.text[:200]}")
            sys.exit(1)
    return deleted


def main():
    print("===== admin:recent:* 全削除（24h TTLのため再蓄積される）=====")
    keys = list_keys("admin:recent:")
    print(f"  list: {len(keys)} keys")
    if keys:
        deleted = bulk_delete(keys)
        print(f"  deleted: {deleted}")

    print("\n===== U_TEST_* userId に紐づく line:/ver: KV を削除 =====")
    line_keys = list_keys("line:U_TEST_")
    ver_keys = list_keys("ver:U_TEST_")
    print(f"  line:U_TEST_*: {len(line_keys)} keys")
    print(f"  ver:U_TEST_*: {len(ver_keys)} keys")
    target = line_keys + ver_keys
    if target:
        deleted = bulk_delete(target)
        print(f"  deleted: {deleted}")

    print("\n===== event:* 今日と昨日の line_follow カウンタをリセット =====")
    from datetime import datetime, timedelta, timezone
    JST = timezone(timedelta(hours=9))
    today = datetime.now(JST).strftime("%Y-%m-%d")
    yesterday = (datetime.now(JST) - timedelta(days=1)).strftime("%Y-%m-%d")
    targets = []
    for date in [today, yesterday]:
        for ev in ["line_follow", "line_unfollow", "line_message"]:
            targets.append(f"event:{date}:{ev}")
    print(f"  resetting: {targets}")
    bulk_delete(targets)
    print("  done")

    print("\n===== 確認 =====")
    after_recent = list_keys("admin:recent:", limit=1)
    after_line_test = list_keys("line:U_TEST_", limit=1)
    print(f"  admin:recent:* 残り: {len(list_keys('admin:recent:', limit=100))} (max 100で確認)")
    print(f"  line:U_TEST_*   残り: {len(after_line_test)}")


if __name__ == "__main__":
    main()
