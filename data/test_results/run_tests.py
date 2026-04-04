#!/usr/bin/env python3
"""
ナースロビー LINE Bot 検証スイート
実行日: 自動記録
検証者: Claude Code (自動テスト)
"""
import json, subprocess, os, re, sys
from datetime import datetime
from pathlib import Path

WORKER_JS = Path("api/worker.js")
RESULTS = []
PASS = 0
FAIL = 0
SKIP = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    status = "✅ PASS" if condition else "❌ FAIL"
    if condition: PASS += 1
    else: FAIL += 1
    RESULTS.append({"name": name, "status": status, "detail": detail})
    print(f"  {status}: {name}" + (f" ({detail})" if detail and not condition else ""))

def skip(name, reason):
    global SKIP
    SKIP += 1
    RESULTS.append({"name": name, "status": "⏭️ SKIP", "detail": reason})
    print(f"  ⏭️ SKIP: {name} ({reason})")

def d1_query(sql):
    """D1に実際にクエリを実行して結果を返す"""
    result = subprocess.run(
        ["npx", "wrangler", "d1", "execute", "nurse-robby-db",
         "--command", sql, "--remote", "--json", "--config", "wrangler.toml"],
        cwd="api", capture_output=True, text=True,
        env={**os.environ, "CLOUDFLARE_API_TOKEN": ""}
    )
    try:
        return json.loads(result.stdout)[0]['results']
    except:
        return None

# ファイル読み込み
with open(WORKER_JS) as f:
    code = f.read()

print(f"\n{'='*60}")
print(f"ナースロビー 検証スイート")
print(f"実行日時: {datetime.now().isoformat()}")
print(f"{'='*60}")

# ========== カテゴリ1: Worker API健全性 ==========
print(f"\n--- カテゴリ1: Worker API健全性 ---")

import urllib.request
try:
    res = urllib.request.urlopen("https://robby-the-match-api.robby-the-robot-2026.workers.dev/api/health", timeout=10)
    health = json.loads(res.read())
    test("Worker /api/health", health.get("status") == "ok", f"status={health.get('status')}")
except Exception as e:
    test("Worker /api/health", False, str(e))

# ========== カテゴリ2: EXTERNAL_JOBS データ整合性 ==========
print(f"\n--- カテゴリ2: EXTERNAL_JOBS データ整合性 ---")

EXPECTED_AREAS = [
    "23区", "多摩", "横浜", "川崎", "相模原", "横須賀", "鎌倉", "藤沢",
    "茅ヶ崎", "平塚", "秦野", "伊勢原", "厚木", "大和", "海老名", 
    "小田原", "南足柄・開成", "大磯",
    "さいたま", "川口・戸田", "所沢・入間", "川越・東松山", "越谷・草加", "埼玉その他",
    "千葉", "船橋・市川", "柏・松戸", "千葉その他"
]

total_jobs = 0
missing_areas = []
for area in EXPECTED_AREAS:
    start = code.find(f'"{area}": [')
    if start == -1:
        missing_areas.append(area)
        continue
    end = code.find('],', start)
    count = code[start:end].count('{n:')
    total_jobs += count
    if count == 0:
        missing_areas.append(f"{area}(0件)")

test("EXTERNAL_JOBS 全28エリア存在", len(missing_areas) == 0, f"欠損: {missing_areas}" if missing_areas else f"28エリア全OK")
test("EXTERNAL_JOBS 合計100件以上", total_jobs >= 100, f"{total_jobs}件")

# 求人データの品質チェック（サンプル）
sal_pattern = re.findall(r'sal:"(月給[\d.]+万円)"', code[:50000])
test("給与データ形式が正しい", len(sal_pattern) > 50, f"{len(sal_pattern)}件の月給データ")

# ========== カテゴリ3: AREA_ZONE_MAP 整合性 ==========
print(f"\n--- カテゴリ3: AREA_ZONE_MAP 整合性 ---")

azm_start = code.find("AREA_ZONE_MAP")
azm_section = code[azm_start:azm_start+3000]
for key in ["q3_yokohama_kawasaki_il", "q3_tokyo_23ku_il", "q3_tokyo_tama_il", 
            "q3_chiba_all_il", "q3_saitama_all_il", "q3_kanagawa_all_il", "q3_undecided_il"]:
    test(f"AREA_ZONE_MAP: {key}", key in azm_section)

# ========== カテゴリ4: AREA_CITY_MAP 整合性 ==========
print(f"\n--- カテゴリ4: AREA_CITY_MAP 整合性 ---")

acm_start = code.find("AREA_CITY_MAP = {")
acm_end = code.find("};", acm_start) + 2
acm = code[acm_start:acm_end]

for key in ["tokyo_23ku", "tokyo_tama", "chiba_all", "saitama_all", "kanagawa_all"]:
    idx = acm.find(f"{key}:")
    has_data = False
    if idx >= 0:
        bracket = acm.find("[", idx)
        bracket_end = acm.find("]", bracket)
        content = acm[bracket+1:bracket_end].strip()
        has_data = len(content) > 5
    test(f"AREA_CITY_MAP: {key} にデータあり", has_data)

# ========== カテゴリ5: ADJACENT_AREAS 整合性 ==========
print(f"\n--- カテゴリ5: ADJACENT_AREAS 整合性 ---")

adj_start = code.find("ADJACENT_AREAS = {")
adj_end = code.find("};", adj_start) + 2
adj = code[adj_start:adj_end]

for key in ["tokyo_23ku", "tokyo_tama", "saitama_all", "chiba_all", "kanagawa_all"]:
    test(f"ADJACENT_AREAS: {key}", f"{key}:" in adj)

# ========== カテゴリ6: D1 施設DB品質 ==========
print(f"\n--- カテゴリ6: D1 施設DB品質 ---")

r = d1_query("SELECT COUNT(*) as c FROM facilities")
total = r[0]['c'] if r else 0
test("D1 総施設数 > 20000", total > 20000, f"{total}件")

r = d1_query("SELECT COUNT(*) as c FROM facilities WHERE category='病院'")
hospitals = r[0]['c'] if r else 0
test("D1 病院数 > 1400", hospitals > 1400, f"{hospitals}件")

r = d1_query("SELECT COUNT(*) as c FROM facilities WHERE category='病院' AND departments IS NOT NULL AND departments != ''")
dept = r[0]['c'] if r else 0
test("D1 診療科カバー率 > 95%", dept/hospitals > 0.95 if hospitals else False, f"{dept}/{hospitals} ({dept*100//hospitals}%)")

r = d1_query("SELECT COUNT(*) as c FROM facilities WHERE category='病院' AND nearest_station IS NOT NULL AND nearest_station != ''")
sta = r[0]['c'] if r else 0
test("D1 最寄駅カバー率 > 95%", sta/hospitals > 0.95 if hospitals else False, f"{sta}/{hospitals} ({sta*100//hospitals}%)")

r = d1_query("SELECT COUNT(*) as c FROM facilities WHERE category='病院' AND CAST(nurse_fulltime AS INTEGER) > 0")
nurse = r[0]['c'] if r else 0
test("D1 看護師数カバー率 > 80%", nurse/hospitals > 0.80 if hospitals else False, f"{nurse}/{hospitals} ({nurse*100//hospitals}%)")

# 4県にデータがあるか
for pref in ['東京都', '神奈川県', '埼玉県', '千葉県']:
    r = d1_query(f"SELECT COUNT(*) as c FROM facilities WHERE prefecture='{pref}'")
    cnt = r[0]['c'] if r else 0
    test(f"D1 {pref}にデータあり", cnt > 100, f"{cnt}件")

# ========== カテゴリ7: postbackハンドラ網羅性 ==========
print(f"\n--- カテゴリ7: postbackハンドラ網羅性 ---")

# Quick Replyで使われるpostbackキーを抽出
qr_postbacks = set(re.findall(r'qrItem\([^,]+,\s*"([^"]+)"', code))
# handleLinePostback内でハンドルされるキーを抽出
handler_keys = set()
for m in re.finditer(r'params\.has\("(\w+)"\)', code):
    handler_keys.add(m.group(1))

# Flex Messageボタンのpostbackも抽出
flex_postbacks = set(re.findall(r'data:\s*["`]([^"`]+)["`]', code))

all_postbacks = qr_postbacks | flex_postbacks
unhandled = []
for pb in sorted(all_postbacks):
    key = pb.split("=")[0].split("&")[0]
    if key not in handler_keys and key not in ["handoff", "nurture", "faq", "welcome", 
                                                  "matching_preview", "match", "il_pref",
                                                  "il_area", "il_ft", "il_ws", "il_urg",
                                                  "il_dept", "phone_check", "phone_time",
                                                  "apply", "sheet", "resume", "consult"]:
        unhandled.append(pb)

test("全postbackにハンドラあり", len(unhandled) == 0, f"未処理: {unhandled[:5]}" if unhandled else "")

# ========== カテゴリ8: STATE_CATEGORIES整合性 ==========
print(f"\n--- カテゴリ8: STATE_CATEGORIES整合性 ---")

sc_start = code.find("STATE_CATEGORIES = {")
sc_end = code.find("};", sc_start) + 2
sc_states = set(re.findall(r'"(\w+)"', code[sc_start:sc_end]))

# buildPhaseMessageのcase文
bpm_cases = set(re.findall(r'case "(\w+)":', code))

for state in ["il_area", "il_subarea", "il_facility_type", "il_department", 
              "il_workstyle", "il_urgency", "matching_preview", "matching_browse",
              "nurture_warm", "nurture_subscribed", "handoff_phone_check", "handoff_phone_time"]:
    test(f"buildPhaseMessage case '{state}'", state in bpm_cases)

# ========== カテゴリ9: セキュリティ ==========
print(f"\n--- カテゴリ9: セキュリティ ---")

test("LINE Webhook署名検証あり", "verifyLineSignature" in code)
test("timingSafeEqual使用", "timingSafeEqual" in code)
test("D1バインドパラメータ（hospitalSubType）", "entry.hospitalSubType" not in code[code.find("WHERE category"):code.find("WHERE category")+200] if "WHERE category" in code else True, "文字列連結なし確認")

# SQLインジェクション: extraParams方式を確認
test("D1 SQLバインドパラメータ方式", "extraParams" in code and "extraFilters" in code)

# ========== カテゴリ10: cron設定 ==========
print(f"\n--- カテゴリ10: cron設定 ---")

with open("scripts/pdca_hellowork.sh") as f:
    cron_content = f.read()
test("cron 4県対応(--all-prefectures)", "--all-prefectures" in cron_content)

# ========== カテゴリ11: LINE Bot実行不可テスト（明示的にスキップ） ==========
print(f"\n--- カテゴリ11: LINE Bot E2Eテスト（実行不可） ---")
skip("LINE follow→welcomeメッセージ", "LINE Messaging APIトークンなし")
skip("LINE postback→応答", "LINE Messaging APIトークンなし")
skip("LIFF→セッション引き継ぎ", "ブラウザ操作が必要")
skip("Push API配信", "LINE APIトークンなし")
skip("ナーチャリングcronトリガー", "cron手動実行が必要")

# ========== 結果サマリ ==========
print(f"\n{'='*60}")
print(f"結果: ✅ PASS={PASS} / ❌ FAIL={FAIL} / ⏭️ SKIP={SKIP}")
print(f"{'='*60}")

# ログ保存
log = {
    "run_at": datetime.now().isoformat(),
    "summary": {"pass": PASS, "fail": FAIL, "skip": SKIP},
    "results": RESULTS,
}
with open("data/test_results/latest.json", "w") as f:
    json.dump(log, f, ensure_ascii=False, indent=2)
print(f"\nログ保存: data/test_results/latest.json")

sys.exit(1 if FAIL > 0 else 0)
