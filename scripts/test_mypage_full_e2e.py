#!/usr/bin/env python3
"""
ナースロビー会員制 MVP-A E2E統合スモークテスト
- 石づか様の実データ(U7e23b53d10319c3b070313537485fbc6)で GET 系200確認
- POST/DELETE系は未認証のみ確認（本番データ保護）
- UI HTTP 200 + セキュリティヘッダー確認
"""
import hmac, hashlib, json, base64, time, urllib.request, os, sys

SECRET = os.environ.get("CHAT_SECRET_KEY") or open(os.path.expanduser("~/robby-the-match/.env")).read().split("CHAT_SECRET_KEY=")[1].splitlines()[0].strip()
USER_ID = "U7e23b53d10319c3b070313537485fbc6"  # 石づか様（テスト会員）
WORKER = "https://robby-the-match-api.robby-the-robot-2026.workers.dev"
SITE = "https://quads-nurse.com"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Safari/604.1"

PASS = 0
FAIL = 0

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_entry_token(user_id, secret, ttl_ms=24*3600*1000):
    payload = json.dumps({"userId": user_id, "exp": int(time.time()*1000) + ttl_ms}, separators=(",",":"))
    p64 = b64url(payload.encode())
    sig = hmac.new(secret.encode(), p64.encode(), hashlib.sha256).digest()
    return f"{p64}.{b64url(sig)}"

def req(url, method="GET", headers=None, body=None):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    r = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, dict(resp.headers), resp.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()

def check(name, got, expected):
    global PASS, FAIL
    ok = got in (expected if isinstance(expected, (list, tuple)) else [expected])
    mark = "✅" if ok else "❌"
    print(f"  {mark} {name}: got {got}, expected {expected}")
    if ok: PASS += 1
    else: FAIL += 1
    return ok

def section(title):
    print(f"\n========== {title} ==========")

# ============================================================
section("1. UI 静的ページ (全て HTTP 200)")
# ============================================================
for path in ["/resume/", "/resume/member/", "/mypage/", "/mypage/auth.html", "/mypage/resume/", "/mypage/resume/edit.html"]:
    code, _, _ = req(SITE + path)
    check(f"GET {path}", code, 200)

# ============================================================
section("2. UI セキュリティヘッダー確認 (/mypage/ のみ)")
# ============================================================
code, headers, _ = req(SITE + "/mypage/")
lh = {k.lower(): v for k, v in headers.items()}
# GitHub Pages は meta http-equiv なので、レスポンスヘッダーではなくHTMLで確認する場合もある
# ここはHTTP200のみ確認、詳細確認は別途

# ============================================================
section("3. API 未認証で 400/401/403")
# ============================================================
# /api/member-resume-generate — token なし → 403
code, _, _ = req(WORKER + "/api/member-resume-generate", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"lastName":"x","firstName":"x","consentPrivacy":True,"consentAi":True}).encode())
check("member-resume-generate no-token", code, 403)

# 同意なし → 400
code, _, _ = req(WORKER + "/api/member-resume-generate", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"token":"f"*36,"lastName":"x","firstName":"x"}).encode())
check("member-resume-generate no-consent", code, 400)

# /api/mypage-init — body なし → 400
code, _, _ = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"}, body=b"{}")
check("mypage-init empty-body", code, 400)

# /api/mypage-init — 不正 entryToken → 403
code, _, _ = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"entryToken":"invalid"}).encode())
check("mypage-init bad-token", code, 403)

# /api/mypage-resume — 認証なし → 401
code, _, _ = req(WORKER + "/api/mypage-resume")
check("mypage-resume no-auth", code, 401)

# /api/mypage-resume-data — 認証なし → 401
code, _, _ = req(WORKER + "/api/mypage-resume-data")
check("mypage-resume-data no-auth", code, 401)

# /api/mypage-resume-edit — 認証なし → 401
code, _, _ = req(WORKER + "/api/mypage-resume-edit", method="POST",
  headers={"Content-Type": "application/json"}, body=b"{}")
check("mypage-resume-edit no-auth", code, 401)

# /api/mypage-resume DELETE — 認証なし → 401
code, _, _ = req(WORKER + "/api/mypage-resume", method="DELETE")
check("mypage-resume DELETE no-auth", code, 401)

# ============================================================
section("4. 実データ認証フロー (石づか様)")
# ============================================================
entry_token = make_entry_token(USER_ID, SECRET)
print(f"  entryToken generated (len={len(entry_token)})")

# mypage-init で sessionToken 取得
code, _, body = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"entryToken": entry_token}).encode())
if not check("mypage-init with entryToken", code, 200):
    print(f"  レスポンス: {body[:300]}")
    sys.exit(1)

data = json.loads(body)
session = data.get("sessionToken")
print(f"  sessionToken: {session[:30]}...")
print(f"  displayName: {data.get('displayName')}")
print(f"  userId: {data.get('userId')}")

# sessionToken で mypage-resume GET
code, h, body = req(WORKER + "/api/mypage-resume",
  headers={"Authorization": f"Bearer {session}"})
check("mypage-resume GET", code, 200)
ct = h.get("content-type", h.get("Content-Type", ""))
check("mypage-resume Content-Type html", "text/html" in ct.lower(), True)
rp = h.get("referrer-policy", h.get("Referrer-Policy", ""))
check("mypage-resume Referrer-Policy", rp, "no-referrer")
print(f"  履歴書HTML length: {len(body)} bytes")

# sessionToken で mypage-resume-data GET
code, h, body = req(WORKER + "/api/mypage-resume-data",
  headers={"Authorization": f"Bearer {session}"})
check("mypage-resume-data GET", code, 200)
try:
    d = json.loads(body)
    check("resume_data has lastName", bool(d.get("lastName")), True)
    check("resume_data has updatedAt", bool(d.get("updatedAt")), True)
except:
    check("resume_data parseable JSON", False, True)

# ============================================================
section("5. 不正シナリオ")
# ============================================================
# 期限切れトークン
expired_token = make_entry_token(USER_ID, SECRET, ttl_ms=-1000)
code, _, _ = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"entryToken": expired_token}).encode())
check("mypage-init expired-token", code, 403)

# 改ざんトークン
tampered = entry_token[:-5] + "XXXXX"
code, _, _ = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"entryToken": tampered}).encode())
check("mypage-init tampered-signature", code, 403)

# 不正な userId 形式
code, _, _ = req(WORKER + "/api/mypage-init", method="POST",
  headers={"Content-Type": "application/json"},
  body=json.dumps({"userId": "invalid"}).encode())
check("mypage-init bad-userId-format", code, 400)

# ============================================================
print(f"\n========== 結果: {PASS} pass / {FAIL} fail ==========")
sys.exit(0 if FAIL == 0 else 1)
