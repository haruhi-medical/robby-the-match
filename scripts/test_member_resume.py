#!/usr/bin/env python3
"""会員化履歴書生成APIのテスト（E2Eスモーク）"""
import requests

WORKER = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"

def test_member_resume_generate_requires_token():
    """token なしで叩くと 403"""
    r = requests.post(f"{WORKER}/api/member-resume-generate", json={
        "lastName": "test", "firstName": "test",
        "consentPrivacy": True, "consentAi": True,
    })
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
    print("✅ token required OK")

def test_member_resume_generate_rejects_invalid_token_format():
    """不正なトークン形式で 403"""
    r = requests.post(f"{WORKER}/api/member-resume-generate", json={
        "token": "invalid",
        "lastName": "test", "firstName": "test",
        "consentPrivacy": True, "consentAi": True,
    })
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
    print("✅ invalid token format rejected")

def test_member_resume_generate_requires_consent():
    """同意なしで 400（tokenは有効形式にして、consent だけ欠如）"""
    r = requests.post(f"{WORKER}/api/member-resume-generate", json={
        "token": "f" * 36,
        "lastName": "test", "firstName": "test",
        "consentPrivacy": False,
        "consentAi": False,
    })
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text[:200]}"
    print("✅ consent required OK")

def test_member_resume_generate_rejects_nonexistent_token():
    """有効形式だが存在しないトークンで 403"""
    r = requests.post(f"{WORKER}/api/member-resume-generate", json={
        "token": "deadbeef-dead-beef-dead-beefdeadbeef",  # 36文字
        "lastName": "test", "firstName": "test",
        "consentPrivacy": True, "consentAi": True,
    })
    assert r.status_code == 403, f"expected 403, got {r.status_code}: {r.text[:200]}"
    print("✅ non-existent token rejected")

if __name__ == "__main__":
    test_member_resume_generate_requires_token()
    test_member_resume_generate_rejects_invalid_token_format()
    test_member_resume_generate_requires_consent()
    test_member_resume_generate_rejects_nonexistent_token()
    print("全テストパス")
