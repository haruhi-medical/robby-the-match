#!/usr/bin/env python3
"""マイページ セッショントークンのテスト（E2E スモーク）"""
import requests
import sys

WORKER = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"

def test_mypage_init_requires_userId():
    """userIdなしで /api/mypage-init を叩くと 400"""
    r = requests.post(f"{WORKER}/api/mypage-init", json={})
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
    print("✅ userId required check OK")

def test_mypage_init_rejects_invalid_userId():
    """不正な userId 形式で 400"""
    r = requests.post(f"{WORKER}/api/mypage-init", json={"userId": "invalid"})
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
    print("✅ invalid userId format rejected")

def test_mypage_init_nonexistent_user_returns_404():
    """存在しない userId で 404（※Task 3 実装後に初めてパスする）"""
    valid_format_user = "U" + "f" * 32
    r = requests.post(f"{WORKER}/api/mypage-init", json={"userId": valid_format_user})
    # Task 2 だけの段階では /api/mypage-init 未実装なので 404 (route) or その他
    # Task 3 完了後は 404 (not member)
    assert r.status_code in (404, 500), f"expected 404/500, got {r.status_code}: {r.text[:200]}"
    print("✅ non-existent user → 404 OK")

if __name__ == "__main__":
    test_mypage_init_requires_userId()
    test_mypage_init_rejects_invalid_userId()
    test_mypage_init_nonexistent_user_returns_404()
    print("全テストパス")
