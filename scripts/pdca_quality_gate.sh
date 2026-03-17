#!/bin/bash
set -euo pipefail
# ===========================================
# 神奈川ナース転職 品質ゲート v2.0
# quality_checker.py による自動品質点検
# cron: 0 16 * * 1-6（月-土 16:00、コンテンツ生成15:00の後）
#
# v2.0 変更点:
#   - Claude CLI 依存を撤廃（cronで認証不要）
#   - quality_checker.py --fact-check / --appeal-check を使用
#   - シェルインジェクション脆弱性を修正（tempファイル経由でデータ受渡し）
# ===========================================
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_quality_gate"

PYTHON="python3"
CHECKER="$PROJECT_DIR/scripts/quality_checker.py"
QUEUE_FILE="$PROJECT_DIR/data/posting_queue.json"

echo "=== 品質ゲート開始 ===" >> "$LOG"

# ===========================================
# 前提チェック
# ===========================================
if [ ! -f "$QUEUE_FILE" ]; then
    echo "[SKIP] posting_queue.json が見つかりません" >> "$LOG"
    exit 0
fi

if [ ! -f "$CHECKER" ]; then
    echo "[ERROR] quality_checker.py が見つかりません: $CHECKER" >> "$LOG"
    slack_notify ":x: 品質ゲート: quality_checker.py が見つかりません"
    exit 1
fi

# ===========================================
# 未点検の ready/pending 投稿をリストアップ（最大5件）
# ===========================================
UNCHECKED_FILE=$(mktemp /tmp/quality_gate_unchecked.XXXXXX)
trap 'rm -f "$UNCHECKED_FILE"' EXIT

$PYTHON - "$QUEUE_FILE" > "$UNCHECKED_FILE" 2>> "$LOG" << 'PYEOF'
import json, sys
from pathlib import Path

queue_file = sys.argv[1]
data = json.loads(Path(queue_file).read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
unchecked = []
for idx, item in enumerate(posts):
    if not isinstance(item, dict):
        continue
    if item.get('status', '') not in ('ready', 'pending'):
        continue
    if item.get('quality_checked'):
        continue
    hook = item.get('hook', item.get('caption', ''))[:30]
    unchecked.append(json.dumps({'index': idx, 'hook': hook}, ensure_ascii=False))
for u in unchecked[:5]:
    print(u)
PYEOF

if [ ! -s "$UNCHECKED_FILE" ]; then
    echo "[OK] 未点検コンテンツなし" >> "$LOG"
    exit 0
fi

TOTAL=$(wc -l < "$UNCHECKED_FILE" | tr -d ' ')
echo "[INFO] 未点検コンテンツ: ${TOTAL}件" >> "$LOG"

PASS_COUNT=0
FAIL_COUNT=0
# Accumulate failure details in a temp file to avoid shell injection
FAIL_DETAILS_FILE=$(mktemp /tmp/quality_gate_fails.XXXXXX)
trap 'rm -f "$UNCHECKED_FILE" "$FAIL_DETAILS_FILE"' EXIT

# ===========================================
# 各投稿をチェック
# ===========================================
while IFS= read -r item_json; do
    # Parse index and hook via a temp file to avoid shell injection
    META_FILE=$(mktemp /tmp/quality_gate_meta.XXXXXX)
    printf '%s' "$item_json" > "$META_FILE"

    INDEX=$($PYTHON -c "import json,sys; d=json.loads(open(sys.argv[1]).read()); print(d['index'])" "$META_FILE" 2>/dev/null)
    HOOK=$($PYTHON  -c "import json,sys; d=json.loads(open(sys.argv[1]).read()); print(d['hook'])"  "$META_FILE" 2>/dev/null)
    rm -f "$META_FILE"

    echo "[CHECK] #${INDEX}: ${HOOK}..." >> "$LOG"

    # ---------- fact-check ----------
    FACT_RESULT_FILE=$(mktemp /tmp/quality_gate_fact.XXXXXX)
    $PYTHON "$CHECKER" --fact-check "$QUEUE_FILE" --index "$INDEX" \
        > "$FACT_RESULT_FILE" 2>> "$LOG" || true

    FACT_SCORE=$($PYTHON -c "
import json, sys
try:
    d = json.loads(open(sys.argv[1]).read())
    print(d.get('fact_score', 0))
except Exception:
    print(0)
" "$FACT_RESULT_FILE" 2>/dev/null)

    # ---------- appeal-check ----------
    APPEAL_RESULT_FILE=$(mktemp /tmp/quality_gate_appeal.XXXXXX)
    $PYTHON "$CHECKER" --appeal-check "$QUEUE_FILE" --index "$INDEX" \
        > "$APPEAL_RESULT_FILE" 2>> "$LOG" || true

    APPEAL_SCORE=$($PYTHON -c "
import json, sys
try:
    d = json.loads(open(sys.argv[1]).read())
    print(d.get('appeal_score', 0))
except Exception:
    print(0)
" "$APPEAL_RESULT_FILE" 2>/dev/null)

    # ---------- 合算スコア ----------
    COMBINED=$($PYTHON -c "
import sys
try:
    f = float(sys.argv[1])
    a = float(sys.argv[2])
    print(round(f * 0.5 + a * 0.5, 2))
except Exception:
    print(0)
" "$FACT_SCORE" "$APPEAL_SCORE" 2>/dev/null)

    # issuesリストをtempファイル経由で安全に取得
    ISSUES_FILE=$(mktemp /tmp/quality_gate_issues.XXXXXX)
    $PYTHON - "$FACT_RESULT_FILE" "$APPEAL_RESULT_FILE" > "$ISSUES_FILE" 2>/dev/null << 'PYEOF'
import json, sys
issues = []
for path in sys.argv[1:]:
    try:
        d = json.loads(open(path).read())
        issues.extend(d.get('issues', []))
    except Exception:
        pass
# Deduplicate, cap at 5
seen = []
for i in issues:
    if i not in seen:
        seen.append(i)
print(', '.join(seen[:5]) if seen else 'なし')
PYEOF

    ISSUES=$(cat "$ISSUES_FILE")
    rm -f "$FACT_RESULT_FILE" "$APPEAL_RESULT_FILE" "$ISSUES_FILE"

    echo "  Fact: ${FACT_SCORE}/10, Appeal: ${APPEAL_SCORE}/10, Combined: ${COMBINED}, Issues: ${ISSUES}" >> "$LOG"

    # ---------- 合否判定（combined >= 6.0 で合格） ----------
    PASSED=$($PYTHON -c "
import sys
try:
    print('true' if float(sys.argv[1]) >= 6.0 else 'false')
except Exception:
    print('false')
" "$COMBINED" 2>/dev/null)

    # ---------- キューを安全に更新（env var 経由で注入） ----------
    if [ "$PASSED" = "true" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        _QUEUE="$QUEUE_FILE" _IDX="$INDEX" _SCORE="$COMBINED" \
        $PYTHON - << 'PYEOF' 2>> "$LOG"
import json, os
from pathlib import Path
queue_file = os.environ['_QUEUE']
idx        = int(os.environ['_IDX'])
score      = float(os.environ['_SCORE'])
data = json.loads(Path(queue_file).read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
posts[idx]['quality_checked'] = True
posts[idx]['quality_score']   = score
Path(queue_file).write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(f"[OK] #{idx} marked quality_checked=true score={score}")
PYEOF
    else:
        FAIL_COUNT=$((FAIL_COUNT + 1))
        # Append to failures file (safe: no shell interpolation into Python code)
        printf -- '- #%s %s: %s\n' "$INDEX" "$HOOK" "$ISSUES" >> "$FAIL_DETAILS_FILE"

        _QUEUE="$QUEUE_FILE" _IDX="$INDEX" _SCORE="$COMBINED" _ISSUES="$ISSUES" \
        $PYTHON - << 'PYEOF' 2>> "$LOG"
import json, os
from pathlib import Path
queue_file = os.environ['_QUEUE']
idx        = int(os.environ['_IDX'])
score      = float(os.environ['_SCORE'])
issues_str = os.environ['_ISSUES']
data = json.loads(Path(queue_file).read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
posts[idx]['quality_checked'] = True
posts[idx]['quality_score']   = score
posts[idx]['quality_issues']  = issues_str
posts[idx]['status']          = 'quality_failed'
Path(queue_file).write_text(json.dumps(data, ensure_ascii=False, indent=2))
print(f"[FAIL] #{idx} marked quality_failed score={score}")
PYEOF
    fi

done < "$UNCHECKED_FILE"

# ===========================================
# Slack通知
# ===========================================
if [ $FAIL_COUNT -gt 0 ]; then
    FAIL_BODY=$(cat "$FAIL_DETAILS_FILE")
    slack_notify ":warning: 品質ゲート結果: ${PASS_COUNT}件合格 / ${FAIL_COUNT}件不合格
不合格:
${FAIL_BODY}"
elif [ $PASS_COUNT -gt 0 ]; then
    slack_notify ":white_check_mark: 品質ゲート: ${PASS_COUNT}件全て合格 (quality_checker.py点検)"
fi

echo "=== 品質ゲート完了: Pass=${PASS_COUNT}, Fail=${FAIL_COUNT} ===" >> "$LOG"
write_heartbeat "pdca_quality_gate" 0
