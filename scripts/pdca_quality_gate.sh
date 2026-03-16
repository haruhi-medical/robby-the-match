#!/bin/bash
set -euo pipefail
# ===========================================
# 神奈川ナース転職 品質ゲート v1.0
# Claude Opus 4.6 による画像品質自動点検
# cron: 0 14 * * 1-6（月-土 14:00、コンテンツ生成15:00の前）
# ===========================================
source ~/robby-the-match/scripts/utils.sh
init_log "pdca_quality_gate"

echo "=== 品質ゲート開始 ===" >> "$LOG"

# Claude CLI認証チェック
if ! ensure_env; then
    echo "[ERROR] Claude CLI認証失敗" >> "$LOG"
    notify_slack ":x: 品質ゲート: Claude CLI認証エラー"
    exit $EXIT_CONFIG_ERROR
fi

# === 投稿キューから未点検のreadyコンテンツを取得 ===
QUEUE_FILE="$PROJECT_DIR/data/posting_queue.json"
if [ ! -f "$QUEUE_FILE" ]; then
    echo "[SKIP] posting_queue.json が見つかりません" >> "$LOG"
    exit 0
fi

# Python で未点検コンテンツのディレクトリ一覧を取得
UNCHECKED=$(python3 -c "
import json, sys
from pathlib import Path

data = json.loads(Path('$QUEUE_FILE').read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
unchecked = []
for idx, item in enumerate(posts):
    if not isinstance(item, dict):
        continue
    status = item.get('status', '')
    if status not in ('ready', 'pending'):
        continue
    if item.get('quality_checked'):
        continue
    img_dir = item.get('slide_dir', item.get('image_dir', ''))
    if img_dir and Path(img_dir).exists():
        hook = item.get('hook', item.get('caption', ''))[:30]
        unchecked.append(json.dumps({'index': idx, 'dir': img_dir, 'hook': hook}))
for u in unchecked[:5]:
    print(u)
" 2>> "$LOG")

if [ -z "$UNCHECKED" ]; then
    echo "[OK] 未点検コンテンツなし" >> "$LOG"
    exit 0
fi

TOTAL=$(echo "$UNCHECKED" | wc -l | tr -d ' ')
echo "[INFO] 未点検コンテンツ: ${TOTAL}件" >> "$LOG"

PASS_COUNT=0
FAIL_COUNT=0
FAIL_DETAILS=""

# === 各コンテンツをClaude Opus 4.6で視覚点検 ===
while IFS= read -r item; do
    INDEX=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin)['index'])")
    IMG_DIR=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin)['dir'])")
    HOOK=$(echo "$item" | python3 -c "import json,sys; print(json.load(sys.stdin)['hook'])")

    echo "[CHECK] #${INDEX}: ${HOOK}... (${IMG_DIR})" >> "$LOG"

    # 画像ファイル一覧を取得（hook + content最大3枚 + cta = 最大5枚）
    IMAGES=$(find "$IMG_DIR" -name "*.png" -type f | sort | head -5)
    IMG_COUNT=$(echo "$IMAGES" | wc -l | tr -d ' ')

    if [ "$IMG_COUNT" -lt 2 ]; then
        echo "[SKIP] 画像が2枚未満" >> "$LOG"
        continue
    fi

    # Claude Opus 4.6 に画像を送って品質判定
    # --model claude-opus-4-6 で最新Opusモデルを指定
    PROMPT="あなたはTikTok/Instagram投稿画像の品質検査官です。
以下の画像（カルーセル投稿のスライド）を厳密にチェックしてください。

チェック項目:
1. 文字サイズ: スマホ(375pt幅)で読めるか? 最低40px推奨。小さすぎないか?
2. セーフゾーン: 上150px/下250px/右100pxのTikTok UIで隠れる箇所にテキストがないか?
3. コントラスト: 背景色と文字色の可読性。WCAG AA基準(4.5:1)を満たすか?
4. レイアウト: テキストが画面の一部に偏っていないか? 空白が多すぎないか?
5. 日本語品質: 文字化け、不自然な改行、文字間延びがないか?
6. フック(1枚目): 3秒で内容が把握できるか? 文字数は25文字以内か?

判定結果をJSON形式で返してください:
{
  \"pass\": true/false,
  \"score\": 1-10,
  \"issues\": [\"問題1\", \"問題2\"],
  \"recommendation\": \"改善提案\"
}

passの基準: score 7以上でissuesに致命的問題（文字が読めない、セーフゾーン侵犯）がないこと。
JSONのみ返してください。説明文は不要です。

画像ディレクトリ: ${IMG_DIR}
各画像を読んで判定してください。"

    # run_claude を使ってClaude CLIで実行（最大5分）
    RESULT=$(claude -p "$PROMPT" \
        --model claude-opus-4-6 \
        --dangerously-skip-permissions \
        --max-turns 10 \
        2>> "$LOG")

    # JSON部分を抽出
    SCORE=$(echo "$RESULT" | python3 -c "
import json, sys, re
text = sys.stdin.read()
# JSON部分を抽出
match = re.search(r'\{[^{}]*\"pass\"[^{}]*\}', text, re.DOTALL)
if match:
    data = json.loads(match.group())
    print(data.get('score', 0))
else:
    print(0)
" 2>/dev/null)

    PASSED=$(echo "$RESULT" | python3 -c "
import json, sys, re
text = sys.stdin.read()
match = re.search(r'\{[^{}]*\"pass\"[^{}]*\}', text, re.DOTALL)
if match:
    data = json.loads(match.group())
    print('true' if data.get('pass', False) else 'false')
else:
    print('false')
" 2>/dev/null)

    ISSUES=$(echo "$RESULT" | python3 -c "
import json, sys, re
text = sys.stdin.read()
match = re.search(r'\{[^{}]*\"pass\"[^{}]*\}', text, re.DOTALL)
if match:
    data = json.loads(match.group())
    issues = data.get('issues', [])
    print(', '.join(issues[:3]) if issues else 'なし')
else:
    print('解析失敗')
" 2>/dev/null)

    echo "  Score: ${SCORE}/10, Pass: ${PASSED}, Issues: ${ISSUES}" >> "$LOG"

    # キューを更新
    if [ "$PASSED" = "true" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        python3 -c "
import json
from pathlib import Path
data = json.loads(Path('$QUEUE_FILE').read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
posts[$INDEX]['quality_checked'] = True
posts[$INDEX]['quality_score'] = $SCORE
Path('$QUEUE_FILE').write_text(json.dumps(data, ensure_ascii=False, indent=2))
" 2>> "$LOG"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAIL_DETAILS="${FAIL_DETAILS}\n- #${INDEX} ${HOOK}: ${ISSUES}"
        # 不合格: statusをquality_failedに変更
        python3 -c "
import json
from pathlib import Path
data = json.loads(Path('$QUEUE_FILE').read_text())
posts = data.get('posts', data if isinstance(data, list) else [])
posts[$INDEX]['quality_checked'] = True
posts[$INDEX]['quality_score'] = $SCORE
posts[$INDEX]['quality_issues'] = '''${ISSUES}'''
posts[$INDEX]['status'] = 'quality_failed'
Path('$QUEUE_FILE').write_text(json.dumps(data, ensure_ascii=False, indent=2))
" 2>> "$LOG"
    fi

done <<< "$UNCHECKED"

# === Slack通知 ===
if [ $FAIL_COUNT -gt 0 ]; then
    notify_slack ":warning: 品質ゲート結果: ${PASS_COUNT}件合格 / ${FAIL_COUNT}件不合格\n不合格:${FAIL_DETAILS}"
elif [ $PASS_COUNT -gt 0 ]; then
    notify_slack ":white_check_mark: 品質ゲート: ${PASS_COUNT}件全て合格 (Opus 4.6点検)"
fi

echo "=== 品質ゲート完了: Pass=${PASS_COUNT}, Fail=${FAIL_COUNT} ===" >> "$LOG"
