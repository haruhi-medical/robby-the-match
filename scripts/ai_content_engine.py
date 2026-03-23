#!/usr/bin/env python3
"""
ai_content_engine.py — 神奈川ナース転職 自律型AIコンテンツ生成エンジン v2.0

Claude Code CLI (claude -p) を使った高品質コンテンツ生成。
企画→生成→品質チェック→スケジュール→投稿準備を一気通貫で実行する。

使い方:
  python3 scripts/ai_content_engine.py --plan              # 1週間分のコンテンツ企画
  python3 scripts/ai_content_engine.py --generate 7        # N件のコンテンツを生成
  python3 scripts/ai_content_engine.py --review             # 生成済みコンテンツの品質チェック
  python3 scripts/ai_content_engine.py --schedule           # 投稿スケジュール設定
  python3 scripts/ai_content_engine.py --auto               # 全自動モード（plan→generate→review→schedule）
  python3 scripts/ai_content_engine.py --status             # 現状サマリ表示

AI: Claude Code CLI（サブスク内、追加コストゼロ）
フォールバック: Cloudflare Workers AI（Llama 3.3 70B、無料枠）
"""

import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ロビー君キャラクターシステム
try:
    from robby_character import (
        get_robby_system_prompt,
        pick_hook_pattern,
        pick_cta,
        pick_narration_opening,
        pick_narration_transition,
        pick_catchphrase,
        pick_behavioral_template,
        validate_robby_voice,
        validate_hook,
        build_robby_caption,
        ROBBY,
        ROBBY_VOICE,
        ROBBY_BEHAVIORAL_ECONOMICS,
    )
    ROBBY_LOADED = True
except ImportError:
    ROBBY_LOADED = False
    print("[INFO] robby_character.py not found. Using default system prompt.")

# ============================================================
# Constants & Configuration
# ============================================================

PROJECT_DIR = Path(__file__).parent.parent

QUEUE_PATH = PROJECT_DIR / "data" / "posting_queue.json"
PLAN_PATH = PROJECT_DIR / "data" / "content_plan.json"
GENERATED_DIR = PROJECT_DIR / "content" / "generated"
READY_DIR = PROJECT_DIR / "content" / "ready"
LOG_DIR = PROJECT_DIR / "logs"
ENV_FILE = PROJECT_DIR / ".env"

# Cloudflare Workers AI endpoint (FREE)
CF_AI_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

# Content MIX ratios (v2.0 戦略改定 2026-03-05)
# 地域25%+業界裏側15%で競合ゼロの独占領域を最大化
MIX_RATIOS = {
    "あるある": 0.35,
    "給与": 0.20,
    "業界裏側": 0.15,
    "地域ネタ": 0.15,
    "転職": 0.10,
    "トレンド": 0.05,
}

# Category to content_type mapping for queue integration
CATEGORY_TO_CONTENT_TYPE = {
    "あるある": "aruaru",
    "給与": "salary",
    "業界裏側": "industry",
    "地域ネタ": "local",
    "転職": "career",
    "トレンド": "trend",
}

# CTA 8:2 rule
CTA_HARD_RATIO = 0.2

# Auto mode: minimum buffer = 2 weeks of content (~14 posts, aim for at least 7 pending)
AUTO_MIN_PENDING = 7
AUTO_TARGET_PENDING = 14

# Optimal posting times (from CLAUDE.md: nurse work rhythm)
POSTING_TIMES = ["17:30", "12:00", "21:00"]

# Curated hashtag sets per category (4エージェント討論 2026-02-27 改定)
# 4個構成: 地域1 + ニッチ1 + 中規模1 + 一般1
# 禁止タグ: #AI, #fyp, #神奈川ナース転職（宣伝感・飽和回避）
# 地域タグローテーション: 神奈川看護師, 小田原, 平塚, 秦野, 湘南ナース, 県西部
HASHTAG_SETS = {
    "あるある": [
        ["#神奈川看護師", "#夜勤あるある", "#看護師あるある", "#看護師"],
        ["#小田原", "#病棟あるある", "#看護師あるある", "#ナース"],
        ["#平塚", "#看護記録", "#看護師の日常", "#看護師"],
        ["#秦野", "#夜勤あるある", "#看護師あるある", "#ナース"],
        ["#湘南ナース", "#師長", "#ナースの本音", "#看護師"],
        ["#県西部", "#病棟あるある", "#看護師あるある", "#看護師"],
    ],
    "給与": [
        ["#神奈川看護師", "#手取り公開", "#看護師転職", "#看護師"],
        ["#小田原", "#手取り公開", "#看護師あるある", "#ナース"],
        ["#湘南ナース", "#手取り公開", "#看護師転職", "#看護師"],
        ["#県西部", "#手取り公開", "#看護師の日常", "#ナース"],
    ],
    "地域ネタ": [
        ["#神奈川看護師", "#夜勤あるある", "#看護師あるある", "#看護師"],
        ["#小田原", "#病棟あるある", "#看護師の日常", "#ナース"],
        ["#平塚", "#師長", "#看護師あるある", "#看護師"],
        ["#秦野", "#看護記録", "#ナースの本音", "#ナース"],
        ["#湘南ナース", "#夜勤あるある", "#看護師転職", "#看護師"],
        ["#県西部", "#転職理由", "#看護師あるある", "#看護師"],
    ],
    "転職": [
        ["#神奈川看護師", "#転職理由", "#看護師転職", "#転職"],
        ["#小田原", "#転職理由", "#看護師転職", "#看護師"],
        ["#湘南ナース", "#師長", "#看護師転職", "#ナース"],
        ["#県西部", "#転職理由", "#看護師転職", "#転職"],
    ],
    "トレンド": [
        ["#神奈川看護師", "#夜勤あるある", "#看護師あるある", "#看護師"],
        ["#小田原", "#病棟あるある", "#ナースの本音", "#ナース"],
        ["#湘南ナース", "#師長", "#看護師の日常", "#看護師"],
        ["#県西部", "#夜勤あるある", "#看護師あるある", "#ナース"],
    ],
}

# ============================================================
# Hashtag Rotation & Validation (2026-02-28)
# ============================================================

BANNED_HASHTAGS = {"#AI", "#fyp", "#foryou", "#viral", "#foryoupage", "#AIやってみた"}


def get_rotated_hashtags():
    """ハッシュタグローテーション（data/hashtag_rotation.json）"""
    rotation_file = PROJECT_DIR / "data" / "hashtag_rotation.json"
    if rotation_file.exists():
        try:
            with open(rotation_file, "r", encoding="utf-8") as f:
                rotation = json.load(f)
            combos = rotation.get("combos", [])
            if combos:
                day_idx = datetime.now().timetuple().tm_yday % len(combos)
                combo = combos[day_idx]
                return validate_hashtags(combo["tags"])
        except Exception as e:
            print(f"[WARN] Failed to load hashtag rotation: {e}")
    # Fallback
    return ["#看護師あるある", "#看護師の日常", "#神奈川看護師", "#看護師転職"]


def validate_hashtags(tags):
    """禁止タグの除去 + 個数制限"""
    # Load banned tags from rotation file if available
    banned = set(BANNED_HASHTAGS)
    rotation_file = PROJECT_DIR / "data" / "hashtag_rotation.json"
    if rotation_file.exists():
        try:
            with open(rotation_file, "r", encoding="utf-8") as f:
                rotation = json.load(f)
            for tag in rotation.get("banned_tags", []):
                banned.add(tag)
        except Exception:
            pass
    clean = [t for t in tags if t not in banned]
    return clean[:5]  # max 5 tags


# Content stock ideas for planning context
# 2026-02-28 改定: アンチジェネリック基準で全面刷新
# 緊張・矛盾・違和感から始まる鋭いコンセプト。予測可能な「AIにやらせてみた」パターンを排除。
CONTENT_STOCK_HINTS = {
    "あるある": [
        "師長に退職届を出した日、ロッカーに3年分のPHSストラップが溜まってた",
        "申し送りで「異常なし」って言った直後、自分の異常に気づいてないことに気づいた",
        "新人に「大丈夫？」って聞いたら「大丈夫です」。自分も5年間同じ嘘ついてた",
        "ナースコール鳴らない夜勤が一番怖い。静かすぎる病棟は何かが起きる前兆",
        "休憩室のカップ麺を3分待てたことがない。2分40秒で戻るのがデフォルト",
        "「看護師向いてないかも」と思う日と「この仕事しかない」と思う日が同じ日に来る",
        "先輩の「私の時代はもっと大変だった」。その時代を終わらせたのは誰？",
        "有給申請したら師長に「みんな我慢してるのに」って言われた。それ法律違反では？",
        "インシデントレポート書いてたら朝になってた。報告書を書く時間は業務外扱い",
        "プリセプターやれって言われた。自分がまだプリセプティーの気持ちなのに",
    ],
    "給与": [
        "応援ナースの時給3,000円。同じ病棟で常勤の自分は時給換算1,800円。同じ仕事なのになぜ？",
        "夜勤専従なら月10回で手取り35万。でも体がもつのは何年？",
        "美容クリニックに転職した同期が月収40万。急性期5年目の自分は24万",
        "派遣看護師の時給2,200円、常勤の時給換算は約1,800円。ボーナスで取り返せてる？",
        "夜勤1回の手当は平均11,000円（日本看護協会調査）。16時間拘束で手当だけ見ると時給換算687円",
        "訪問看護に転職したら年収は下がったけど、オンコール手当で月3万入る。QOLは上がった",
        "産業看護師（企業ナース）の年収500万。病棟5年目の自分は430万。何が違う？",
        "紹介会社の手数料135万。それ、看護師の年間ボーナスとほぼ同額",
        "クリニック日勤のみで手取り22万。夜勤ありの病棟と2万しか変わらないなら？",
        "ICU5年目で年収480万。一般病棟5年目は430万。同じ看護師免許で100万差",
    ],
    "地域ネタ": [
        "小田原から横浜まで片道72分。年間600時間を通勤に使う看護師の選択は正しいのか",
        "県西部の病院は紹介会社に135万払えない。だから看護師が来ない。この悪循環",
        "横浜の病院で手取り28万。小田原なら24万。でも家賃は4万安い。結局どっちが得？",
        "秦野の病院、夜勤の日だけ駐車場が満車。始発じゃ間に合わないから全員車通勤",
        "応援ナースが神奈川に来る理由。寮付き・交通費全額で手取り35万。地元ナースより高い",
        "川崎の大学病院と小田原の市民病院、同じ5年目で年収50万差。立地だけでこんなに違う？",
    ],
    "転職": [
        "転職サイトに登録した瞬間、知らない番号から17件。看護師の個人情報はいくら？",
        "「3年は続けなさい」。それ、誰のための3年？病院の離職率のための3年だった",
        "退職届を出したら急に「待遇改善する」と言われた。3年間の不満を無視してたくせに",
        "紹介会社の営業が「あなたにぴったり」って言う。全員に同じこと言ってるのに",
        "応援ナースを1年やって貯金300万。常勤3年で貯められなかった額を1年で超えた",
        "訪問看護に転職したら残業ゼロ。病棟時代の月40時間残業は何だったのか",
        "美容クリニックに転職した同期、施術のインセンティブで月収50万。でも看護スキルは？",
        "夜勤専従に切り替えたら月10回で手取り35万。日勤のみの常勤より10万多い。体と引き換え",
    ],
    "トレンド": [
        "彼氏が「夜勤って暇でしょ」と言った夜、急変2件。翌朝の「おはよう」が出なかった",
        "母に「看護師辞めたい」と言ったら「せっかく資格取ったのに」。資格は足枷じゃない",
        "合コンで「看護師です」→「優しそう」。12時間立ちっぱなしで優しさ搾り出してるとは言えない",
        "看護学生の娘が「ママみたいになりたい」。嬉しいのに「やめとけ」が先に出た自分",
        "友達に「看護師って給料いいでしょ」って言われた。手取り24万のどこが？",
    ],
    "業界裏側": [
        "看護師1人の紹介で病院が払う手数料135万。その看護師の年間ボーナスより高い",
        "大手紹介会社の利益率40%。看護師の転職1件で営業マンに50万のインセンティブ",
        "手数料30%の紹介会社が「看護師に寄り添う」と言う矛盾。寄り添ってるのは病院の財布",
        "紹介手数料を10%にしたら病院は90万浮く。その90万で看護師2人分の夜勤手当が上がる",
        "お祝い金で釣る紹介会社は2025年から違法。それでも裏で渡してる会社がある",
        "紹介会社経由で入職すると「すぐ辞めるな」プレッシャーが強くなる。手数料のせいで",
    ],
}

# ============================================================
# Anti-Generic Script Writer Prompt (2026-02-28)
# ============================================================

SCRIPT_WRITER_PROMPT_PATH = PROJECT_DIR / "data" / "prompts" / "script_writer.md"

def _load_script_writer_prompt() -> str:
    """Load anti-generic script writer prompt template."""
    if SCRIPT_WRITER_PROMPT_PATH.exists():
        try:
            return SCRIPT_WRITER_PROMPT_PATH.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] Failed to load script writer prompt: {e}")
    return ""

SCRIPT_WRITER_PROMPT = _load_script_writer_prompt()

# Anti-generic rules injected into content generation
ANTI_GENERIC_RULES = """
## アンチジェネリック・ルール（最重要）
以下のAIスロップを完全に回避せよ:

【禁止】
- 「知ってましたか？」「実は…」「想像してみてください」で始めるフック
- 自己啓発的・モチベーショナルトーン
- 予測可能な3点リスト構成
- 「人生が変わります」系の曖昧な約束
- 過度に磨かれた企業トーン
- 典型的CTA（「フォローしてね」「リンクはプロフに」）で終わる

【代わりにやること】
- 緊張、矛盾、違和感から始める
- 抽象ではなく具体で語る（病棟の匂い、PHSの重さ、ナースシューズの擦れ）
- 安全な3つより、鋭い1つを選ぶ
- リズムを意図的に崩す（短文の後に長文、沈黙の後に怒り）
- 真正性が増すなら、わずかな粗さを許容する
- 「看護師 転職」で検索して出てくる広告と同じトーンなら書き直せ
- 読んで心拍数が上がらないなら書き直せ

トーン: 反体制的だが品がある。怒りではなく「静かな確信」。
「快適に感じるライン」より10%過激に寄せろ。混沌ではなく、鋭さ。
"""

# ============================================================
# Behavioral Psychology x Positive Psychology x Philosophy Templates
# 行動経済学 x ポジティブ心理学 x 哲学 統合カルーセルテンプレート 30本
# ============================================================

TEMPLATES_PATH = PROJECT_DIR / "data" / "carousel_templates.json"

def _load_templates() -> List[Dict]:
    """Load carousel templates from JSON file."""
    if TEMPLATES_PATH.exists():
        try:
            with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load carousel templates: {e}")
    return []

TEMPLATES = _load_templates()

# Index templates by ID for quick lookup
TEMPLATES_BY_ID = {t["id"]: t for t in TEMPLATES}

# Index templates by category + psychology combination
TEMPLATES_BY_CATEGORY = {}
for _t in TEMPLATES:
    _cat = _t.get("category", "")
    if _cat not in TEMPLATES_BY_CATEGORY:
        TEMPLATES_BY_CATEGORY[_cat] = []
    TEMPLATES_BY_CATEGORY[_cat].append(_t)

PSYCHOLOGY_ALIASES = {
    "behavioral_economics": ["行動経済学", "損失回避", "アンカリング", "フレーミング", "サンクコスト", "社会的証明", "デフォルト効果", "現状維持", "IKEA効果", "初頭効果", "ハロー効果", "メンタルアカウンティング", "機会費用", "時間的割引", "ゼロリスク"],
    "positive_psychology": ["ポジティブ心理学", "PERMA", "成長マインドセット", "フロー理論", "VIA", "感謝介入", "希望理論", "自己決定理論", "ポジティブ加齢"],
    "philosophy": ["哲学", "ストア", "実存主義", "サルトル", "アドラー", "ニーチェ", "禅仏教", "マインドフルネス", "功利主義"],
}

def pick_template(category: str = None, psychology: str = None) -> Optional[Dict]:
    """Pick a random template, optionally filtered by category or psychology."""
    pool = TEMPLATES
    if category:
        pool = [t for t in pool if t.get("category") == category]
    if psychology:
        # Support English alias keys (e.g. "behavioral_economics")
        keywords = PSYCHOLOGY_ALIASES.get(psychology, [psychology])
        pool = [t for t in pool if any(kw in t.get("psychology", "") for kw in keywords)]
    return random.choice(pool) if pool else None

def get_template_for_generation(category: str, cta_type: str = "soft") -> Optional[Dict]:
    """Get a template suitable for content generation, matching CTA type preference."""
    candidates = TEMPLATES_BY_CATEGORY.get(category, [])
    if not candidates:
        return None
    # Prefer templates matching the requested CTA type
    matching_cta = [t for t in candidates if any(
        s.get("cta_type") == cta_type for s in t.get("slides", []) if s.get("type") == "cta"
    )]
    if matching_cta:
        return random.choice(matching_cta)
    return random.choice(candidates)


# ============================================================
# Environment & Utilities
# ============================================================

def load_env():
    """Load .env file from PROJECT_DIR.

    Called at module level AND in main() to ensure env vars are available
    even in cron environments where .zshrc is not sourced.
    Uses os.environ.setdefault() so existing env vars are not overwritten.
    """
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)


# Load .env at module level to ensure credentials are available
# before any function calls (critical for cron execution)
load_env()


def get_cf_credentials() -> Tuple[str, str]:
    """Get Cloudflare credentials from environment."""
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not account_id or not api_token:
        print("[FATAL] CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not set in .env")
        sys.exit(1)
    return account_id, api_token


def log_event(event_type: str, data: dict):
    """Write an event to the daily log file."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"ai_engine_{datetime.now().strftime('%Y%m%d')}.log"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "data": data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def slack_notify(message: str):
    """Send a Slack notification."""
    try:
        result = subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "notify_slack.py"),
             "--message", message],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print("  [SLACK] Notification sent")
        else:
            print(f"  [SLACK] Send failed (exit {result.returncode})")
    except Exception as e:
        print(f"  [SLACK] Error: {e}")


def timestamp_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ============================================================
# Claude Code CLI Client (Primary) + Cloudflare AI (Fallback)
# ============================================================

CLAUDE_CLI_TIMEOUT = 120  # seconds

def call_claude_code(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.7,
    retries: int = 1,
) -> Optional[str]:
    """
    Claude Code CLI (claude -p) で高品質テキスト生成。
    サブスク内なので追加コストゼロ。
    失敗時は Cloudflare Workers AI にフォールバック。
    """
    full_prompt = ""
    if system_prompt:
        full_prompt += f"[System]\n{system_prompt}\n\n[User]\n"
    full_prompt += prompt

    # Primary: Claude Code CLI
    result = _call_claude_cli(full_prompt, retries)
    if result:
        return result

    # Fallback: Cloudflare Workers AI
    print("  [FALLBACK] Claude CLI failed. Trying Cloudflare Workers AI...")
    return _call_cloudflare_ai_fallback(prompt, system_prompt, max_tokens, temperature)


def _call_claude_cli(prompt: str, retries: int = 1) -> Optional[str]:
    """Invoke claude -p and return stdout."""
    for attempt in range(retries + 1):
        try:
            env = os.environ.copy()
            env.pop("CLAUDECODE", None)
            env.pop("CLAUDE_CODE_ENTRYPOINT", None)

            result = subprocess.run(
                ["claude", "-p", prompt, "--max-turns", "1"],
                capture_output=True,
                text=True,
                timeout=CLAUDE_CLI_TIMEOUT,
                env=env,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

            print(f"  [WARN] Claude CLI exit code {result.returncode} (attempt {attempt + 1})")
            if result.stderr:
                print(f"  stderr: {result.stderr[:300]}")

        except subprocess.TimeoutExpired:
            print(f"  [WARN] Claude CLI timeout ({CLAUDE_CLI_TIMEOUT}s) (attempt {attempt + 1})")
        except FileNotFoundError:
            print("  [ERROR] 'claude' command not found. Install Claude Code CLI.")
            return None
        except Exception as e:
            print(f"  [WARN] Claude CLI failed (attempt {attempt + 1}): {e}")

        if attempt < retries:
            time.sleep(2)

    return None


def _call_cloudflare_ai_fallback(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> Optional[str]:
    """Fallback: Cloudflare Workers AI (Llama 3.3 70B, FREE)."""
    import urllib.request
    import urllib.error

    try:
        account_id, api_token = get_cf_credentials()
    except SystemExit:
        print("  [WARN] CF credentials not available. Skipping fallback.")
        return None

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{CF_AI_MODEL}"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_token}")
    req.add_header("Content-Type", "application/json")

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    response_text = data.get("result", {}).get("response", "")
                    if response_text:
                        return response_text
        except Exception as e:
            print(f"  [WARN] CF AI fallback failed (attempt {attempt + 1}): {e}")
            if attempt == 0:
                time.sleep(3)

    return None


# Backward compatibility alias
call_cloudflare_ai = call_claude_code


# ============================================================
# アトミック書き込みユーティリティ
# ============================================================

def atomic_json_write(filepath, data, indent=2):
    """アトミックJSON書き込み（書き込み中クラッシュによるデータ破損を防止）"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Write to temp file in same directory (same filesystem for atomic rename)
        fd, tmp_path = tempfile.mkstemp(
            dir=filepath.parent,
            suffix='.tmp',
            prefix=filepath.stem + '_'
        )
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        # Atomic rename
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass
        raise


# ============================================================
# Queue I/O
# ============================================================

def load_queue() -> dict:
    """Load posting_queue.json（破損時のバックアップ復旧付き）."""
    if not QUEUE_PATH.exists():
        return {
            "version": 2,
            "created": datetime.now().isoformat(),
            "updated": None,
            "posts": [],
        }
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        backup = QUEUE_PATH.with_suffix('.json.bak')
        if backup.exists():
            print(f"[WARN] キュー破損、バックアップから復旧: {e}")
            try:
                with open(backup, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("[ERROR] バックアップも破損しています")
        else:
            print(f"[ERROR] キュー破損、バックアップなし: {e}")
        return {
            "version": 2,
            "created": datetime.now().isoformat(),
            "updated": None,
            "posts": [],
        }


def save_queue(queue: dict):
    """Save posting_queue.json（バックアップ + アトミック書き込み）."""
    queue["updated"] = datetime.now().isoformat()
    # Create backup of current file
    if QUEUE_PATH.exists():
        backup = QUEUE_PATH.with_suffix('.json.bak')
        try:
            shutil.copy2(QUEUE_PATH, backup)
        except Exception:
            pass
    atomic_json_write(QUEUE_PATH, queue)


def load_plan() -> dict:
    """Load content_plan.json."""
    if not PLAN_PATH.exists():
        return {"created": None, "plans": []}
    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_plan(plan: dict):
    """Save content_plan.json（アトミック書き込み）."""
    plan["updated"] = datetime.now().isoformat()
    atomic_json_write(PLAN_PATH, plan)


def get_next_queue_id(queue: dict) -> int:
    """Next integer ID for the posting queue."""
    posts = queue.get("posts", [])
    if not posts:
        return 1
    return max(p.get("id", 0) for p in posts) + 1


def count_by_status(queue: dict) -> Dict[str, int]:
    """Count posts grouped by status."""
    counts: Dict[str, int] = {}
    for p in queue.get("posts", []):
        s = p.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


def count_pending(queue: dict) -> int:
    """Count pending posts."""
    return sum(1 for p in queue.get("posts", []) if p.get("status") == "pending")


def analyze_queue_mix(queue: dict) -> Dict[str, int]:
    """Analyze content type distribution in pending/ready posts."""
    dist: Dict[str, int] = {cat: 0 for cat in MIX_RATIOS}
    for p in queue.get("posts", []):
        if p.get("status") in ("pending", "ready"):
            ct = p.get("content_type", "")
            # Map content_type back to category
            for cat, ctype in CATEGORY_TO_CONTENT_TYPE.items():
                if ctype == ct:
                    dist[cat] += 1
                    break
    return dist


# ============================================================
# System Prompt for Content Generation
# ============================================================

# SYSTEM_PROMPT: ロビー君キャラクターシステムが読み込まれていればそちらを使う
if ROBBY_LOADED:
    SYSTEM_PROMPT = get_robby_system_prompt()
else:
    SYSTEM_PROMPT = """あなたは「ロビー」としてSNSコンテンツを生成するAIだ。
神奈川ナース転職——元病院人事が始めた手数料10%の看護師紹介サービスのマスコット。

## ロビーの性格（4柱）
1. 正直 — データと事実で語る。嘘をつけない。
2. 看護師の味方 — 常に看護師の立場。病院側ではない。
3. おせっかい助手 — 聞かれなくても調べてくる。
4. 押し売りしない — 情報を渡して、選ぶのは看護師さん。

## ロビーの使命（企業ポリシー: 最初から堂々と発信）
- 創業者は元病院人事責任者。紹介料20-30%の高さに疑問
- 「この金が看護師に還元されたら、病院の設備に反映されたら」
- AIで効率化して手数料10%を実現
- スライド3枚目以降でこの想いを自然に語れ

## ロビーの口調
- 一人称「ロビー」は使わない。主語なしか自然な語り口で。「~だよ」「~なんだ」。敬語禁止。

## あなたの敵＝ジェネリックAI出力
予測可能なフック、使い古されたトーン、きれいだが感情のない脚本を完全に回避せよ。

## ペルソナ「ミサキ」（28歳中堅看護師）
- 急性期5-8年目。夜勤あり。手取り24万。神奈川県在住。
- 転職サイトは怖い（電話17件のトラウマ）。LINEなら相談してみたい。
- 帰りの電車と寝る前にTikTok/Instagramを見る。

## フック（1枚目）ルール【最重要】
- 25文字以内。日本語として自然な文にすること。省略しすぎて意味不明にするな。ロビーの名前は入れない。「AI」も入れない。

### フックの心理学原則（必ず守れ）
フックは「事実の陳列」ではない。**未解決の問い（オープンループ）**を作れ。
人は答えがわからない問いを見ると、解決するためにスワイプする（ツァイガルニク効果）。
好奇心は「知っていること」と「知りたいこと」のギャップから生まれる（情報ギャップ理論）。

フックの絶対条件 — **5W1Hが明確であること**:
読んだ人が「誰が」「何を」「いつ」「なぜ」を迷わず理解できなければフック失格。
曖昧な状況描写は人によって解釈がバラバラになる → 刺さらない。

フックに必要な4要素:
1. **誰の話か** — 看護師が「私のことだ」と1秒でわかる（看護師5年目/夜勤月8回の看護師）
2. **何の話か** — 具体的な数字や状況（手取り24万/紹介料135万/残業80時間）
3. **未解決の問い** — 答えが気になってスワイプする（？/なぜ/理由/本当に/...）
4. **誰が読んでも同じ意味に取れる** — 曖昧な表現は禁止

BAD: 「夜勤明け、電車で座る暇ある？」→ 誰が？行きの電車？帰り？座れるかは人による。5W1H不明。
BAD: 「看護師5年目、手取り24万」→ 事実の陳列。「で？」で終わる。オープンループなし。
BAD: 「湘南で夜勤明け、電車2本見送る理由って?」→ なぜ見送る？疲れ？混雑？理由が曖昧。
GOOD: 「看護師5年目で手取り24万って普通なの？」→ 誰が＝5年目看護師、何が＝手取り24万、問い＝普通？ 全部明確。
GOOD: 「夜勤月8回の看護師の時給、コンビニと同じって本当？」→ 誰が＝夜勤看護師、何が＝時給、問い＝本当？
GOOD: 「師長に退職を切り出したら急に優しくなった...なぜ？」→ 誰が＝退職希望の看護師、何が＝師長の態度変化、問い＝なぜ？

- 現場語: 夜勤/師長/病棟/手取り/残業/申し送り/有給/退職/転職
- フック7型（全て問いかけ or 未完了の文にすること。閉じた文は禁止。省略しすぎず日本語として自然に）:
  1. 数字+疑問: 「看護師5年目で手取り24万って普通なの？」
  2. あるある+問い: 「夜勤明けの帰りの電車で何してる？」
  3. 問いかけ: 「5年目の手取りって低いと思う？」
  4. 対比+疑問: 「夜勤の時給がコンビニバイトと同じって本当？」
  5. 本音+未完了: 「師長に退職を切り出したら...」
  6. 地域+疑問: 「神奈川の看護師がワースト3位なのはなぜ？」
  7. 業界+疑問: 「あなたの転職で病院が135万払ってるって知ってた？」

## スライド構成（8枚）
1枚目: Hook — 現場語で止める（ロビー不在）
2枚目: Escalation — 共感の深掘り+地域（ロビー不在）
3枚目: Data — データ提示。「調べたんだけど」とデータを見せる
4枚目: Shift — 視点転換。企業ポリシー（手数料問題等）をここで自然に
5枚目: Core — 鋭い洞察1つ
6枚目: Reveal — ロビーのまとめ「正直に言うね」
7枚目: Reflection — 余韻
8枚目: CTA — ソフト8:ハード2

## 3要素ルール
すべての投稿に「看護師のリアル × 鋭い洞察 × 地域」を含めること。

## ハッシュタグ4個
地域1+ニッチ1+中規模1+一般1。禁止: #AI, #fyp, #神奈川ナース転職

## 法的制約
- 架空設定。患者情報触れない。実在施設の批判なし。ハッシュタグ4個厳守。"""


# ============================================================
# Phase 1: AI Content Planning (--plan)
# ============================================================

def cmd_plan():
    """
    Analyze the current queue balance and generate a 1-week content plan
    using Claude Code CLI (fallback: Cloudflare Workers AI).
    """
    print("=" * 60)
    print(f"[PLAN] AI Content Planning - {timestamp_str()}")
    print("=" * 60)

    queue = load_queue()
    pending = count_pending(queue)
    mix = analyze_queue_mix(queue)
    total_active = sum(mix.values())

    print(f"\n[STATUS] Pending in queue: {pending}")
    print(f"[STATUS] Active content mix:")
    for cat, count in mix.items():
        target_pct = MIX_RATIOS[cat] * 100
        actual_pct = (count / total_active * 100) if total_active > 0 else 0
        gap = target_pct - actual_pct
        indicator = "OK" if abs(gap) < 10 else ("LOW" if gap > 0 else "HIGH")
        print(f"  {cat:8s}: {count:2d}  (actual {actual_pct:4.1f}% / target {target_pct:4.0f}%) [{indicator}]")

    # Determine how many posts to plan for (1 week = 7 posts, TikTok daily or near-daily)
    plan_count = 7
    needed = max(0, AUTO_MIN_PENDING - pending)
    if needed > 0:
        plan_count = max(plan_count, needed)
    plan_count = min(plan_count, 14)  # Cap at 2 weeks

    print(f"\n[PLAN] Generating plan for {plan_count} posts...")

    # Determine category allocation
    allocation = _allocate_categories(plan_count, mix)
    print("[PLAN] Category allocation:")
    for cat, n in sorted(allocation.items(), key=lambda x: -x[1]):
        if n > 0:
            print(f"  {cat}: {n}")

    # Assign CTA types (8:2 rule)
    hard_count = max(1, round(plan_count * CTA_HARD_RATIO))
    soft_count = plan_count - hard_count

    # Build plan items
    plan_items = []
    idx = 0
    cats_expanded = []
    for cat, n in allocation.items():
        cats_expanded.extend([cat] * n)
    random.shuffle(cats_expanded)

    for i, cat in enumerate(cats_expanded):
        cta = "hard" if i < hard_count else "soft"
        plan_items.append({
            "day": i + 1,
            "category": cat,
            "cta_type": cta,
            "status": "planned",
            "content_id": None,
            "hint": random.choice(CONTENT_STOCK_HINTS.get(cat, ["(free topic)"])),
        })

    # Call AI to refine plan with specific topic suggestions
    ai_plan = _ai_refine_plan(plan_items, mix)
    if ai_plan:
        plan_items = ai_plan

    # Save plan
    plan = {
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
        "week_of": datetime.now().strftime("%Y-%m-%d"),
        "total": len(plan_items),
        "queue_pending_at_creation": pending,
        "plans": plan_items,
    }
    save_plan(plan)

    # Display
    print(f"\n[PLAN] Content plan saved ({len(plan_items)} items):")
    print("-" * 60)
    for item in plan_items:
        cta_mark = "H" if item["cta_type"] == "hard" else "S"
        hook_hint = item.get("hook_idea", item.get("hint", ""))[:40]
        print(f"  Day {item['day']:2d} | {item['category']:6s} | CTA:{cta_mark} | {hook_hint}")
    print("-" * 60)

    log_event("plan_created", {"count": len(plan_items), "pending": pending})
    print(f"\n[OK] Plan saved to {PLAN_PATH.relative_to(PROJECT_DIR)}")
    return plan_items


def _allocate_categories(count: int, current_mix: Dict[str, int]) -> Dict[str, int]:
    """Allocate categories for new content to balance the MIX ratios."""
    total_current = sum(current_mix.values())

    # Calculate deficit: how many of each category we need to reach ideal ratio
    allocation: Dict[str, int] = {cat: 0 for cat in MIX_RATIOS}
    remaining = count

    # Priority: categories most underrepresented
    deficits = []
    for cat, ratio in MIX_RATIOS.items():
        ideal = ratio * (total_current + count)
        current = current_mix.get(cat, 0)
        deficit = ideal - current
        deficits.append((cat, deficit))

    deficits.sort(key=lambda x: -x[1])  # most underrepresented first

    for cat, deficit in deficits:
        if remaining <= 0:
            break
        alloc = max(0, min(remaining, round(deficit)))
        # Ensure at least the minimum ratio is represented
        min_alloc = max(0, round(MIX_RATIOS[cat] * count))
        alloc = max(alloc, min(min_alloc, remaining))
        allocation[cat] = alloc
        remaining -= alloc

    # Distribute any remaining to the largest category
    if remaining > 0:
        biggest = max(MIX_RATIOS, key=MIX_RATIOS.get)
        allocation[biggest] += remaining

    return allocation


def _ai_refine_plan(plan_items: List[Dict], current_mix: Dict[str, int]) -> Optional[List[Dict]]:
    """Use AI to suggest specific hook ideas for each planned item."""
    categories_list = "\n".join(
        f"Day {item['day']}: category={item['category']}, cta={item['cta_type']}, hint={item.get('hint', '')}"
        for item in plan_items
    )

    prompt = f"""以下のSNS投稿計画について、各日のフック（1枚目のテキスト）案を考えてください。

## 現在の投稿計画
{categories_list}

## アンチジェネリック・ルール（最重要）
「知ってましたか？」「実は…」系のフックは禁止。
緊張、矛盾、違和感から始めろ。安全な言葉を選ぶな。
他の100本の看護師TikTokでも使えるフックなら書き直せ。

## フックの絶対ルール
- 看護師が「私のことだ！」と一瞬でわかる主語を必ず入れろ
- BAD: 「神奈川で24万」→何の24万？家賃？意味不明。主語がない=不合格
- GOOD: 「看護師5年目、手取り24万」→私のことだ！と即わかる

## フックの型（ローテーション必須。ロビーの名前は入れるな）
1. 数字衝撃型: 「看護師5年目、手取り24万」「夜勤手当、相場いくら？」
2. あるある共感型: 「夜勤明け、電車で座れない」「申し送り中のナースコール」
3. 問いかけ型: 「5年目の手取り、低い？」「転職って逃げですか？」
4. 対比衝撃型: 「看護師の夜勤、コンビニと同じ時給」
5. 本音暴露型: 「看護師辞めたいのに辞められない」「師長に退職、いつ言う？」
6. 地域密着型: 「神奈川の看護師、全国ワースト3位」「湘南で夜勤なし、ある？」
7. 業界暴露型: 「あなたの転職で病院が払う紹介料」「看護師の転職、誰が儲けてる？」

## ルール
- フックは25文字以内。日本語として意味が通る文にすること。看護師が「自分のことだ」と即座にわかること
- フックに「ロビー」を入れるな。知らない人には意味不明。看護師の現場語で書け
- 病棟の匂い、PHSの重さ、ナースシューズの擦れ——その粒度で具体的に書け
- ミサキ（28歳、夜勤明け、帰りの電車）のスクロールを止める違和感
- hintを参考にしつつ、ジェネリックなら捨てて書き直せ
- 読んで心拍数が上がらないフックは不合格

## 出力形式
JSON配列のみ出力。マークダウン記法や説明文は不要。
[
  {{"day": 1, "hook_idea": "フック案"}},
  {{"day": 2, "hook_idea": "フック案"}},
  ...
]"""

    print("\n[AI] Generating hook ideas via Claude Code...")
    result = call_cloudflare_ai(prompt, SYSTEM_PROMPT, max_tokens=1500, temperature=0.8)

    if not result:
        print("[WARN] AI plan refinement failed. Using hint-based plan.")
        return None

    # Parse JSON from AI response
    parsed = _parse_json_from_text(result)
    if parsed and isinstance(parsed, list):
        for ai_item in parsed:
            day = ai_item.get("day")
            hook = ai_item.get("hook_idea", "")
            if day and hook:
                for plan_item in plan_items:
                    if plan_item["day"] == day:
                        plan_item["hook_idea"] = hook[:20]
                        break
        print(f"[AI] Refined {len(parsed)} hook ideas")
        return plan_items

    print("[WARN] Could not parse AI response. Using hint-based plan.")
    return None


# ============================================================
# Phase 2: AI Content Generation (--generate N)
# ============================================================

def cmd_generate(count: int):
    """
    Generate N complete carousel content sets using Claude Code CLI (fallback: Cloudflare Workers AI).
    Creates slide JSON + carousel images, then adds to posting queue.
    """
    if count < 1 or count > 20:
        print(f"[ERROR] Count must be 1-20, got {count}")
        sys.exit(1)

    print("=" * 60)
    print(f"[GENERATE] AI Content Generation - {timestamp_str()}")
    print(f"[GENERATE] Target: {count} posts")
    print("=" * 60)

    # Load plan if available
    plan = load_plan()
    plan_items = [p for p in plan.get("plans", []) if p.get("status") == "planned"]

    queue = load_queue()
    current_mix = analyze_queue_mix(queue)

    # If no plan, create an ad-hoc allocation
    if not plan_items:
        print("[INFO] No plan found. Creating ad-hoc allocation.")
        allocation = _allocate_categories(count, current_mix)
        plan_items = []
        idx = 0
        hard_count = max(1, round(count * CTA_HARD_RATIO))
        for cat, n in allocation.items():
            for _ in range(n):
                cta = "hard" if idx < hard_count else "soft"
                plan_items.append({
                    "day": idx + 1,
                    "category": cat,
                    "cta_type": cta,
                    "status": "planned",
                    "hint": random.choice(CONTENT_STOCK_HINTS.get(cat, [""])),
                })
                idx += 1

    # Use only as many plan items as requested
    items_to_generate = plan_items[:count]

    # Create batch directory
    batch_name = f"ai_batch_{datetime.now().strftime('%Y%m%d_%H%M')}"
    batch_dir = GENERATED_DIR / batch_name
    batch_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n[BATCH] Directory: {batch_dir.relative_to(PROJECT_DIR)}")

    generated = []
    failed = []
    batch_hooks = []  # このバッチで生成済みのフック（重複防止用）

    for i, item in enumerate(items_to_generate, 1):
        category = item["category"]
        cta_type = item["cta_type"]
        hook_hint = item.get("hook_idea", item.get("hint", ""))

        content_id = f"ai_{category[:2]}_{datetime.now().strftime('%m%d')}_{i:02d}"

        print(f"\n{'=' * 50}")
        print(f"[{i}/{count}] Generating: {content_id} ({category}, CTA:{cta_type})")
        print(f"{'=' * 50}")

        # Step 1: Generate content JSON via AI
        content_data = _generate_content_with_ai(
            category=category,
            cta_type=cta_type,
            content_id=content_id,
            hook_hint=hook_hint,
            used_hooks=batch_hooks,
        )

        if not content_data:
            print(f"  [FAIL] Content generation failed for {content_id}")
            failed.append({"content_id": content_id, "category": category, "reason": "AI generation failed"})
            continue

        batch_hooks.append(content_data.get("hook", ""))

        # Step 2: Save content JSON
        json_path = batch_dir / f"{content_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(content_data, f, ensure_ascii=False, indent=2)
        print(f"  [OK] Content JSON saved: {json_path.name}")

        # Step 3: Generate carousel slide images
        slide_dir = batch_dir / content_id
        slide_paths = _generate_carousel_slides(content_data, str(slide_dir))

        if not slide_paths:
            print(f"  [WARN] Carousel generation failed. Adding to queue anyway.")
            failed.append({"content_id": content_id, "category": category, "reason": "Carousel generation failed (queued)"})

        # Step 4: Add to queue
        next_id = get_next_queue_id(queue)
        queue_entry = {
            "id": next_id,
            "content_id": content_id,
            "batch": batch_name,
            "slide_dir": str(slide_dir.relative_to(PROJECT_DIR)),
            "json_path": str(json_path.relative_to(PROJECT_DIR)),
            "caption": content_data.get("caption", ""),
            "hashtags": content_data.get("hashtags", []),
            "cta_type": cta_type,
            "content_type": CATEGORY_TO_CONTENT_TYPE.get(category, "aruaru"),
            "status": "pending",
            "video_path": None,
            "posted_at": None,
            "tiktok_url": None,
            "error": None,
            "performance": {"views": None, "likes": None, "saves": None, "comments": None},
            "ai_score": content_data.get("_ai_score"),
            "quality_score": content_data.get("quality_score"),
        }
        queue["posts"].append(queue_entry)
        print(f"  [OK] Added to queue: id={next_id}")

        generated.append({
            "content_id": content_id,
            "category": category,
            "cta_type": cta_type,
            "hook": content_data.get("hook", ""),
            "queue_id": next_id,
        })

        # Mark plan item as generated
        item["status"] = "generated"
        item["content_id"] = content_id

    # Save queue and plan
    save_queue(queue)
    save_plan(plan)

    # Slack notification
    summary_lines = [
        f"[AI Content Engine] Generation complete",
        f"Batch: {batch_name}",
        f"Generated: {len(generated)} / Failed: {len(failed)}",
        "",
    ]
    for g in generated:
        summary_lines.append(f"  {g['content_id']} ({g['category']}, {g['cta_type']}): {g['hook'][:30]}")

    slack_notify("\n".join(summary_lines))

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"[SUMMARY] Generated: {len(generated)} | Failed: {len(failed)}")
    print(f"  Batch: {batch_name}")
    print(f"  Queue pending: {count_pending(queue)}")
    for g in generated:
        print(f"    {g['content_id']} ({g['category']}) hook: {g['hook'][:35]}")
    if failed:
        print("  Failures:")
        for f_item in failed:
            print(f"    {f_item['content_id']}: {f_item['reason']}")
    print("=" * 60)

    log_event("generate_complete", {
        "batch": batch_name,
        "generated": len(generated),
        "failed": len(failed),
        "queue_pending": count_pending(queue),
    })

    return generated


def _clean_ai_text(s: str) -> str:
    """AIが生成したテキストから外国語混入・ハルシネーション・不要パターンを除去。"""
    # 「1枚目:」「2枚目:」等のprefix除去
    s = re.sub(r'^[0-9０-９]*枚目[:：\s]*', '', s.strip())
    # 韓国語除去
    s = re.sub(r'[\uac00-\ud7af]+', '', s)
    # ギリシャ文字除去
    s = re.sub(r'[\u0370-\u03ff\u1f00-\u1fff]+', '', s)
    # キリル文字除去
    s = re.sub(r'[\u0400-\u04ff]+', '', s)
    # アラビア文字除去
    s = re.sub(r'[\u0600-\u06ff]+', '', s)
    # 英語混入（-looking, -san, LookingFor等）の除去
    s = re.sub(r'-?[Ll]ooking\w*', '', s)
    s = re.sub(r'-san(?=[^a-zA-Z]|$)', 'さん', s, flags=re.IGNORECASE)
    s = re.sub(r'-chan(?=[^a-zA-Z]|$)', 'ちゃん', s, flags=re.IGNORECASE)
    s = re.sub(r'-kun(?=[^a-zA-Z]|$)', 'くん', s, flags=re.IGNORECASE)
    s = re.sub(r'-sama(?=[^a-zA-Z]|$)', 'さま', s, flags=re.IGNORECASE)
    # ハルシネーション（/add, /remove等のコマンド風文字列）
    s = re.sub(r'/[a-z]+\b', '', s, flags=re.IGNORECASE)
    # スペイン語/中国語の接続詞を日本語に置換
    s = re.sub(r'(?<![a-zA-Z])pero(?![a-zA-Z])[、,]?\s*', 'でも、', s, flags=re.IGNORECASE)
    s = re.sub(r'(?<![a-zA-Z])but(?![a-zA-Z])[、,]?\s*', 'でも、', s, flags=re.IGNORECASE)
    s = re.sub(r'但是[、,]?\s*', 'でも、', s)
    s = re.sub(r'真的に', '本当に', s)
    s = re.sub(r'空间', '余地', s)
    # 半角英字のみの単語が3文字以上連続している場合は除去（日本語文中の英語ハルシネーション）
    # ただしAI, LINE, TikTok等の固有名詞は残す
    allowed_english = {"AI", "LINE", "TikTok", "Instagram", "OK", "QR", "ICU", "ER", "NICU", "SNS", "LP"}
    def _remove_stray_english(m):
        word = m.group(0)
        if word.upper() in {w.upper() for w in allowed_english}:
            return word
        return ''
    s = re.sub(r'(?<![A-Za-z])[A-Za-z]{4,}(?![A-Za-z])', _remove_stray_english, s)
    # 連続空白の整理
    s = re.sub(r'\s{2,}', ' ', s)
    # 連続句読点の整理
    s = re.sub(r'、{2,}', '、', s)
    s = re.sub(r'。{2,}', '。', s)
    return s.strip()


def _generate_content_with_ai(
    category: str,
    cta_type: str,
    content_id: str,
    hook_hint: str = "",
    used_hooks: List[str] = None,
) -> Optional[Dict]:
    """Generate a complete carousel content set using Claude Code CLI (fallback: Cloudflare Workers AI)."""

    cta_instruction = ""
    if cta_type == "soft":
        cta_instruction = (
            "8枚目のCTAはソフトCTA（バリエーション豊富に）:\n"
            "  - 保存系: 「この表、保存しといて損ないよ」「あとで見返したい人は保存」\n"
            "  - フォロー系: 「フォローしたら毎日こういう情報届くよ」「続きはフォローして待ってて」\n"
            "  - 共感系: 「わかる！って人はいいね押してほしい」「同じ経験ある人コメントで教えて」\n"
            "  - 共有系: 「同僚にも教えてあげて」「夜勤仲間にシェアして」\n"
            "  サービス名は出さない。宣伝感ゼロで。"
        )
    else:
        cta_instruction = (
            "8枚目のCTAはハードCTA（でも自然に）:\n"
            "  - 相談誘導: 「気になる人はプロフのリンクから相談できるよ」\n"
            "  - LINE誘導: 「もっと詳しく知りたい人はLINEで聞いてみて」\n"
            "  - 情報提供: 「手数料10%で転職サポートしてるんだ。プロフ見てみて」\n"
            "  押し売り感を出すな。あくまで「情報を渡す」スタンス。"
        )

    hint_text = f"フックのヒント: {hook_hint}" if hook_hint else ""

    # テンプレートベースの心理学フレームワーク注入
    template_context = ""
    template = get_template_for_generation(category, cta_type)
    if template:
        psych = template.get("psychology", "")
        emotion_curve = " → ".join(template.get("emotion_curve", []))
        slide_types = [s.get("type", "") for s in template.get("slides", [])]
        robby_voice_ref = template.get("robby_voice", "")[:100]
        template_context = f"""

## 心理学フレームワーク（テンプレート {template['id']} 参照）
- 心理学理論: {psych}
- 感情曲線: {emotion_curve}
- スライド構成: {' → '.join(slide_types)}
- ロビー君の語り口参考: 「{robby_voice_ref}...」
- このテンプレートのhook参考: 「{template.get('slides', [{}])[0].get('text', '')}」"""

    # ロビーキャラクターシステムが利用可能な場合、追加コンテキストを注入
    robby_context = ""
    if ROBBY_LOADED:
        # 毎回異なるフックパターンを選ぶ（同じフック回避）
        hook_pattern = pick_hook_pattern(category)
        # カテゴリ別のフック例をランダムに2つ選んで多様性を確保
        from robby_character import HOOK_PATTERNS_V2
        all_examples = []
        for htype, hdata in HOOK_PATTERNS_V2.items():
            all_examples.extend(hdata["examples"])
        random.shuffle(all_examples)
        diverse_examples = all_examples[:3]

        cta_template = pick_cta(cta_type)
        behavioral_hint = ""
        if category in ("給与", "転職", "業界裏側"):
            behavioral_hint = f"\n- 仕掛け（学術用語は使うな。自然に組み込め）: {pick_behavioral_template('loss_aversion')}"
        elif category == "あるある":
            behavioral_hint = f"\n- 仕掛け（学術用語は使うな。自然に組み込め）: {pick_behavioral_template('social_proof')}"

        # 業界裏側カテゴリの場合、企業ポリシーを強調
        mission_hint = ""
        if category == "業界裏側":
            mission_hint = """
- 【業界裏側カテゴリ】創業者の想いを看護師目線で語れ:
  元病院人事が見た紹介料の矛盾 / 手数料30%が看護師の待遇に影響 / AI効率化で10%実現
  大手エージェントの固有名詞は出すな。構造そのものを問題提起しろ。"""

        robby_context = f"""

## ロビーキャラクター指示
- 一人称「ロビー」は使わない。主語なしか自然な語り口で。
- 口調は「~だよ」「~なんだ」。敬語禁止。
- フック（1枚目）にはロビーの名前を入れるな。「AI」も入れるな。看護師の現場語だけ。
- 1-2枚目: ロビー不在。看護師の世界で語る。
- 3枚目: データ提示。「調べたんだけど」とデータを見せる。
- 4-5枚目: 解説者として語る。企業ポリシー（手数料10%の理由）もここで自然に。
- 6-7枚目: まとめ。「ロビーだから正直に言うね」で核心を突く。
- 行動経済学の学術用語（アンカリング、損失回避等）は絶対に使うな。仕掛けだけ使え。
- 参考フック（この中から選ぶな。これらと違うフックを考えろ）: {', '.join(diverse_examples)}
- CTA参考: {cta_template['text']}{behavioral_hint}{mission_hint}"""

    # 使用済みフックを渡して重複防止
    used_hooks_text = ""
    if used_hooks:
        hooks_list = "\n".join([f"- 「{h}」" for h in used_hooks])
        # 使用済みキーワードを抽出して禁止
        banned_keywords = set()
        for h in used_hooks:
            if "24万" in h: banned_keywords.add("24万")
            if "手取り" in h: banned_keywords.add("手取り")
            if "時給" in h and "1,500" in h: banned_keywords.add("時給1,500")
            if "コンビニ" in h: banned_keywords.add("コンビニ")
            if "135万" in h: banned_keywords.add("135万")
            if "電車" in h: banned_keywords.add("電車")
            if "普通" in h: banned_keywords.add("普通")
        banned_text = "、".join(banned_keywords) if banned_keywords else ""
        used_hooks_text = f"""

## 絶対禁止（重複防止）
以下のフックは既に使った。同じフック・同じテーマ・同じ数字は絶対に使うな:
{hooks_list}
禁止キーワード: {banned_text}
→ 上記と全く違う話題・数字・切り口にしろ。"""

    # 感情ベクトル候補（カテゴリ別）
    emotion_vectors = {
        "あるある": ["連帯と疲弊の共存", "静かな怒り", "自嘲と誇りの矛盾", "孤独な共感"],
        "給与": ["構造への怒り", "諦観の先にある反骨", "数字が暴く不条理", "搾取への静かな告発"],
        "地域ネタ": ["土地への執着と葛藤", "都会信仰への違和感", "地元の不便さへの愛憎"],
        "転職": ["恐怖と衝動の狭間", "制度への不信", "自由と安定の二律背反"],
        "トレンド": ["日常の中の断絶", "理解されない怒り", "皮肉混じりの愛情"],
    }
    chosen_emotion = random.choice(emotion_vectors.get(category, ["反骨"]))

    prompt = f"""TikTokカルーセル投稿の台本を1つ生成してください。

{ANTI_GENERIC_RULES}

## 方向性コミットメント（書く前に決めろ）
- 感情ベクトル: {chosen_emotion}
- この感情にコミットしてブレるな。安全に書くな。平均化するな。

## 指定
- カテゴリ: {category}
- CTA種類: {cta_type}
- {cta_instruction}
{hint_text}{template_context}{robby_context}{used_hooks_text}

## 構成（8枚: Hook → Escalation → Data → Shift → Core → Reveal → Reflection → CTA）
- hook: 1枚目（25文字以内。「ロビー」「AI」は入れるな。以下の条件を全て満たすこと）
  【条件1】5W1Hが明確: 誰が・何が・なぜ、が読んだ人全員同じ解釈になること
  【条件2】オープンループ: 疑問（？）・未完了（...）・理由/なぜ で終わること
  【条件3】自然な日本語: 省略しすぎず、意味が1秒で伝わること
  GOOD: 「看護師5年目で手取り24万って普通なの？」→ 誰が＝5年目看護師、何が＝手取り、問い＝普通？
  GOOD: 「夜勤月8回の看護師の時給、コンビニと同じって本当？」→ 比較対象が明確
  BAD: 「夜勤明け、電車で座る暇ある？」→ 行きの電車？帰り？座れるかは人による。曖昧。
  BAD: 「同じコンビニ?」→ 何がコンビニと同じなのか不明。省略しすぎ。）
- slides: 8枚分のテキスト（配列）
  - slides[0]: Hook（フック） — 看護師が自分事と感じるオープンループ（25文字以内。自然な日本語で）
  - slides[1]: Escalation（エスカレーション） — 状況の深掘り、具体的な描写。超具体的なシーン+地域要素
  - slides[2]: Data（データ） — 数字・データ・事実で裏付け。説得力を持たせる
  - slides[3]: Shift（シフト） — 視点の転換、意外な角度。「知らなかった」を生む事実
  - slides[4]: Core（コア） — 本質的なメッセージ。感情のピーク。鋭い1つの洞察
  - slides[5]: Reveal（リビール） — 深い気づき、結論。構造的な真実を暴く
  - slides[6]: Reflection（リフレクション） — 共感を呼ぶ一言、感情の着地。余韻を残す
  - slides[7]: CTA — CTAだが余韻を残す。見た人が5秒間スクロールの手を止める一文
- caption: SNSキャプション:
  1行目: 感情フック（質問形式推奨。地域名含む）
  2-3行目: 核心（短文で区切る）
  最終行: 自然なCTA（典型的CTAは禁止）
  ※改行は \\n で表現。200文字以内。
- hashtags: ハッシュタグ4個（地域1+ニッチ1+中規模1+一般1）
  禁止: #AI, #fyp, #神奈川ナース転職
- reveal_text: コアスライドの衝撃テキスト（短く、鋭く）
- reveal_number: 数字（あれば。例: "144分", "80万円"）
- emotion_vector: "{chosen_emotion}"
- bgm_mood: BGMの質感（曲名ではなく音の描写。例:「ナースシューズが廊下を叩く音だけ」）

## v4.0 スライドメタデータ（カテゴリ別テンプレート用）
- slide_meta: カテゴリ固有のメタデータ（オブジェクト）
  - 給与カテゴリの場合: chart_data を含めること（棒グラフ用データ）
    例: "chart_data": [{{"label": "横浜市", "value": 520, "display": "520万"}}, ...]
  - 地域ネタカテゴリの場合: area_name を含めること（エリアバッジ用）
    例: "area_name": "小田原"
  - 全カテゴリ共通: highlight_number, highlight_label（大数字強調用、任意）

## フックの5W1Hチェック（曖昧なフックは絶対禁止）
フックを書いたら必ず確認: 「10人が読んで10人とも同じ状況を想像するか？」
人によって解釈が変わるフックは刺さらない。

BAD: 「夜勤明け、電車で座る暇ある？」→ 行き？帰り？座れるかは路線・時間による。曖昧。
BAD: 「夜勤明け、電車2本見送る理由って？」→ 疲れ？混雑？理由が不特定。
BAD: 「湘南の海が見える病室、看護師は海を見る暇ある？」→ 看護師は忙しいに決まってる。答えが自明。
GOOD: 「看護師5年目で手取り24万って普通なの？」→ 誰＝5年目看護師、何＝手取り24万、問い＝普通？ 曖昧さゼロ。
GOOD: 「夜勤月8回の看護師の時給、コンビニバイトと同じって本当？」→ 比較対象が明確。本当かどうか知りたくなる。
BAD: 「退職届を出したら急に待遇改善と言われた」→ オチまで書いてある。
GOOD: 「退職届出したら師長が急に...」→ 何が起きた？が気になる＝スワイプ。

## 事実ベース厳守【嘘禁止】
- 数字（時給・年収・手取り・手数料）は実在するデータに基づくこと。根拠のない数字は禁止。
- 看護師の実際の働き方（応援ナース、夜勤専従、訪問看護、クリニック等）を使え。
- 「こういう働き方が実際にある」という事実ベースで書け。
- 参考データ（厚労省令和6年賃金構造基本統計調査・日本看護協会等。嘘禁止、このデータだけ使え）:
  【神奈川県】
  - 看護師平均年収: 546万円（月収38.9万円+賞与79.6万円）。全国平均519万を上回る
  - 充足率: 72.6%（全国最低水準）。必要数11.6万人に対し供給8.5万人。3.1万人不足
  - 横浜vs小田原: 横浜が年収20-50万円高い傾向。県西部は住宅手当等で人材確保
  【働き方別の実際の給与】
  - 応援ナース（トラベルナース）: 月収40-50万円（離島は60万円も）。寮無料・交通費支給。ボーナスなし
  - 夜勤専従: 月収32-42万円（月9-10回）。年収522-589万円。夜勤手当1回11,815円（二交代）
  - 訪問看護: 常勤年収500-543万円。オンコール待機手当1,000-3,000円/回、出動5,000-10,000円/回
  - クリニック日勤のみ: 月収26-30.5万円（手取り23-24.4万円）。年収420-508万円
  - 美容クリニック: 月収30-40万円。経験者年収550-800万円。インセンティブで1,000万円も
  - 派遣看護師: 時給1,800-2,500円。夜勤ありなら月収56万円。ボーナスなし
  - 産業看護師（企業ナース）: 年収450-500万円。大手なら600万円台。夜勤なし
  - ICU/救急: 年収490-520万円。夜勤手当1回15,000-18,000円（一般の1.2-1.5倍）
  【比較用】
  - コンビニ深夜バイト時給: 約1,300-1,500円（神奈川）
  - 夜勤看護師の時給換算: 約1,800-2,200円（基本給+夜勤手当÷拘束時間）
  - 大手紹介会社の手数料: 年収の20-30%（年収450万なら90-135万円）

## セルフチェック（引っかかったら書き直せ）
□ フックの5W1Hは明確か？10人が読んで同じ意味に取れるか？
□ 使った数字に根拠はあるか？嘘ではないか？
□ このフック、他の100本の看護師TikTokでも使えないか？
□ 前回と同じフックになっていないか？毎回違うフックを書け。

## 重要
- 地域名を1つ以上含めること（台本 or キャプション）
- 自然な語り口で語る（タメ口「〜だよ」「〜なんだ」、一人称「ロビー」は使わない）
- 架空のストーリーだが、数字とデータは実際の相場に基づくこと
- キャプション200文字以内

## 出力形式
JSON形式のみ出力。マークダウン記法、コードフェンス、説明文は一切不要。JSONだけ返してください。

{{
  "id": "{content_id}",
  "hook": "25文字以内。自然な日本語のオープンループ（疑問/未完了で終わる。省略しすぎるな）",
  "emotion_vector": "{chosen_emotion}",
  "slides": [
    "1枚目: Hook（25文字以内。自然な日本語のオープンループ。省略しすぎるな）",
    "2枚目: Escalation。状況の深掘り。超具体的場面+地域",
    "3枚目: Data。数字・データ・事実で裏付け",
    "4枚目: Shift。視点の転換。事実で殴る",
    "5枚目: Core。この動画の存在理由。鋭い洞察1つ",
    "6枚目: Reveal。深い気づき、構造的な真実",
    "7枚目: Reflection。共感を呼ぶ一言、感情の着地",
    "8枚目: CTA。余韻を残すCTA"
  ],
  "slide_meta": {{
    "chart_data": [{{"label": "名前", "value": 数値, "display": "表示"}}],
    "area_name": "地域名（地域ネタの場合）",
    "highlight_number": "大数字（任意。例: 80万円）",
    "highlight_label": "数字の説明（任意。例: 大手の手数料）"
  }},
  "caption": "感情フック+地域名\\n\\n核心。\\n\\n自然なCTA",
  "hashtags": ["#地域タグ", "#ニッチタグ", "#中規模タグ", "#一般タグ"],
  "reveal_text": "鋭いリビールテキスト",
  "reveal_number": "数字（任意）",
  "bgm_mood": "音の質感",
  "category": "{category}",
  "cta_type": "{cta_type}"
}}"""

    for attempt in range(5):
        if attempt > 0:
            print(f"  [RETRY] Attempt {attempt + 1}/5")

        print(f"  [AI] Calling Claude Code CLI...")
        result = call_cloudflare_ai(prompt, SYSTEM_PROMPT, max_tokens=2000, temperature=0.75)

        if not result:
            print(f"  [WARN] AI returned no result (attempt {attempt + 1})")
            continue

        data = _parse_json_from_text(result)
        if not data:
            print(f"  [WARN] Could not parse JSON from AI response")
            print(f"  [DEBUG] First 300 chars: {result[:300]}")
            continue

        # Validate and fix
        if _validate_content(data, content_id):
            # Assign curated hashtags if AI-generated ones are poor
            if not data.get("hashtags") or len(data["hashtags"]) < 2:
                # Use rotation grid first, fallback to HASHTAG_SETS
                data["hashtags"] = get_rotated_hashtags()

            # Validate hashtags: remove banned tags + enforce max 5
            data["hashtags"] = validate_hashtags(data.get("hashtags", []))

            # Ensure category and id are correct
            data["id"] = content_id
            data["category"] = category
            data["cta_type"] = cta_type

            # スライドテキストのクリーンアップ
            cleaned_slides = []
            for s in data.get("slides", []):
                s = _clean_ai_text(s)
                cleaned_slides.append(s)
            data["slides"] = cleaned_slides
            # hookもクリーンアップ
            hook = _clean_ai_text(data.get("hook", ""))
            data["hook"] = hook

            # スライド最低文字数チェック（スカスカ防止）
            short_slides = [i for i, s in enumerate(cleaned_slides) if len(s) < 10 and i > 0 and i < len(cleaned_slides) - 1]
            if len(short_slides) >= 2:
                print(f"  [QUALITY] REJECT: スライド{short_slides}が短すぎる（10文字未満）。リトライ。")
                continue

            # 学術用語チェック
            banned_terms = ["アンカリング効果", "認知バイアス", "サンクコスト", "フレーミング効果",
                           "ナッジ理論", "行動経済学", "心理学的", "エビデンスベース",
                           "コグニティブ", "メタ認知", "ヒューリスティック"]
            all_slide_text = " ".join(cleaned_slides)
            found_terms = [t for t in banned_terms if t in all_slide_text]
            if found_terms:
                print(f"  [QUALITY] REJECT: 学術用語検出 {found_terms}。リトライ。")
                continue

            # ロビー君の口調バリデーション
            if ROBBY_LOADED:
                all_text = " ".join([
                    data.get("hook", ""),
                    data.get("caption", ""),
                    " ".join(data.get("slides", [])),
                ])
                voice_issues = validate_robby_voice(all_text)
                if voice_issues:
                    for issue in voice_issues:
                        print(f"  [VOICE] {issue}")
                    data["_voice_issues"] = voice_issues
                else:
                    print(f"  [VOICE] OK: ロビー君の口調に準拠")

                # フック品質チェック（v2.0: オープンループ必須）
                hook_issues = validate_hook(data.get("hook", ""))
                if hook_issues:
                    for hi in hook_issues:
                        print(f"  [HOOK] REJECT: {hi}")
                    print(f"  [HOOK] フック「{data.get('hook', '')}」不合格。リトライ。")
                    continue  # retry with new generation

            # AI品質ゲート（日本語の自然さ・意味の通りを判定）
            passed, score, reason = _ai_quality_gate(data)
            if not passed:
                print(f"  [QUALITY] REJECT: {score}/10 — {reason}")
                print(f"  [QUALITY] フック「{data.get('hook', '')}」不合格。リトライ。")
                continue

            print(f"  [QUALITY] PASS: {score}/10")
            print(f"  [OK] Content generated: hook=\"{data.get('hook', '')[:30]}\"")
            data["quality_score"] = score
            return data

    print(f"  [FAIL] Content generation failed after 5 attempts")
    return None


def _ai_quality_gate(data: dict) -> Tuple[bool, int, str]:
    """AIでフックとスライドの品質を採点。合格=7点以上。"""
    hook = data.get("hook", "")
    slides = data.get("slides", [])
    slides_text = "\n".join([f"[{i+1}] {s}" for i, s in enumerate(slides)])

    prompt = f"""以下のTikTokカルーセル投稿を10点満点で採点してください。

フック: 「{hook}」
スライド:
{slides_text}

採点基準（1つでも0点なら全体5点以下にしろ）:
1. フックの5W1H: 「誰が」「何が」「なぜ」が明確か？10人が読んで同じ意味に取れるか？曖昧なら0点
2. オープンループ: 答えが気になってスワイプしたくなるか？事実の陳列なら0点
3. 日本語の自然さ: 省略しすぎ・意味不明・文法崩壊・外国語混入（pero, 但是, -san, ギリシャ文字等）があったら0点
4. ペルソナ適合: 看護師が「自分のことだ」と思えるか。学術用語（アンカリング効果、認知バイアス等）は看護師に響かないので0点
5. 数字の根拠: 使われている数字に根拠があるか？嘘っぽい数字なら0点
6. スライドの情報密度: 各スライドに十分な情報があるか？テキストが極端に短い（10文字未満）スライドが2枚以上あったら0点

回答形式（この形式のみ。余計な説明不要）:
SCORE: [数字]
REASON: [不合格の場合の理由を1行で]"""

    result = call_cloudflare_ai(prompt, system_prompt="あなたはSNSコンテンツの品質審査官です。厳しく採点してください。", max_tokens=100, temperature=0.3)
    if not result:
        return True, 7, "採点API失敗（通過させる）"

    # Parse score
    score = 7  # default pass
    reason = ""
    for line in result.strip().split("\n"):
        line = line.strip()
        if line.startswith("SCORE:"):
            try:
                score = int(line.replace("SCORE:", "").strip().split("/")[0].split(".")[0])
            except (ValueError, IndexError):
                pass
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()

    passed = score >= 7
    return passed, score, reason


def _validate_content(data: dict, content_id: str) -> bool:
    """Validate that generated content has required fields and correct structure."""
    required = ["hook", "slides", "caption"]
    for key in required:
        if key not in data:
            print(f"  [WARN] Missing key: {key}")
            return False

    hook = data.get("hook", "")
    if len(hook) > 25:
        # Auto-trim hook but preserve open-loop markers at the end
        trimmed = hook[:25]
        for marker in ["？", "?", "...", "…"]:
            if hook.endswith(marker) and not trimmed.endswith(marker):
                trimmed = hook[:25 - len(marker)] + marker
                break
        data["hook"] = trimmed
        print(f"  [WARN] Hook trimmed to {len(trimmed)} chars: \"{trimmed}\"")

    slides = data.get("slides", [])
    if not isinstance(slides, list) or len(slides) < 3:
        print(f"  [WARN] slides must have at least 3 items, got {len(slides) if isinstance(slides, list) else 'N/A'}")
        return False

    # Pad to 8 slides if needed (Hook + Content x6 + CTA)
    while len(slides) < 8:
        slides.append(slides[-1] if slides else "...")
    data["slides"] = slides[:8]

    caption = data.get("caption", "")
    if len(caption) > 200:
        data["caption"] = caption[:200]
        print(f"  [WARN] Caption trimmed to 200 chars")

    return True


def _generate_carousel_slides(content_data: dict, output_dir: str) -> Optional[List[str]]:
    """
    Call generate_carousel.py to create slide images from content data.
    Returns list of generated file paths, or None on failure.
    """
    carousel_script = PROJECT_DIR / "scripts" / "generate_carousel.py"
    if not carousel_script.exists():
        print(f"  [WARN] generate_carousel.py not found at {carousel_script}")
        return None

    # Save a temp JSON that generate_carousel can read
    temp_json = Path(output_dir).parent / f"_temp_{content_data.get('id', 'unknown')}.json"
    temp_json.parent.mkdir(parents=True, exist_ok=True)
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(content_data, f, ensure_ascii=False, indent=2)

    try:
        print(f"  [CAROUSEL] Generating slides...")
        result = subprocess.run(
            [
                "python3", str(carousel_script),
                "--single-json", str(temp_json),
                "--output", str(Path(output_dir).parent),
            ],
            capture_output=True, text=True, timeout=120,
            cwd=str(PROJECT_DIR),
        )

        if result.returncode == 0:
            # Check if output directory has PNG files
            out_path = Path(output_dir)
            if not out_path.exists():
                # generate_carousel.py may use a different naming; check parent
                parent = Path(output_dir).parent
                for d in parent.iterdir():
                    if d.is_dir() and content_data.get("id", "") in d.name:
                        out_path = d
                        break

            if out_path.exists():
                pngs = sorted(out_path.glob("*.png"))
                if pngs:
                    print(f"  [CAROUSEL] Generated {len(pngs)} slides in {out_path.name}")
                    return [str(p) for p in pngs]

            # Fallback: check stdout for paths
            print(f"  [CAROUSEL] Output: {result.stdout[-300:].strip()}")
            return []
        else:
            print(f"  [CAROUSEL] Failed (exit {result.returncode})")
            if result.stderr:
                print(f"  [CAROUSEL] stderr: {result.stderr[-300:]}")
            return None

    except subprocess.TimeoutExpired:
        print(f"  [CAROUSEL] Timeout")
        return None
    except Exception as e:
        print(f"  [CAROUSEL] Error: {e}")
        return None
    finally:
        # Clean up temp file
        if temp_json.exists():
            temp_json.unlink()


# ============================================================
# Phase 3: AI Quality Review (--review)
# ============================================================

def cmd_review():
    """
    Review all pending/unreviewed content in the queue.
    Uses AI to score each post 1-10 on brand guidelines fit.
    Auto-rejects score < 6.
    """
    print("=" * 60)
    print(f"[REVIEW] AI Quality Check - {timestamp_str()}")
    print("=" * 60)

    queue = load_queue()
    posts_to_review = [
        p for p in queue.get("posts", [])
        if p.get("status") == "pending" and p.get("ai_score") is None
    ]

    if not posts_to_review:
        print("[INFO] No unreviewed pending posts found.")
        return

    print(f"[REVIEW] Found {len(posts_to_review)} posts to review\n")

    reviewed = 0
    rejected = 0
    approved = 0

    for post in posts_to_review:
        post_id = post["id"]
        content_id = post.get("content_id", "?")
        caption = post.get("caption", "")
        hashtags = post.get("hashtags", [])
        cta_type = post.get("cta_type", "soft")
        content_type = post.get("content_type", "unknown")

        # Try to load full content JSON for deeper review
        json_path = post.get("json_path")
        slides_text = ""
        if json_path:
            full_path = PROJECT_DIR / json_path
            if full_path.exists():
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content_json = json.load(f)
                    slides = content_json.get("slides", [])
                    slides_text = "\n".join(
                        f"  Slide {i+1}: {s}" for i, s in enumerate(slides)
                    )
                except Exception:
                    pass

        print(f"[REVIEW] #{post_id} {content_id} ({content_type}, {cta_type})")

        prompt = f"""以下のSNS投稿を品質チェックしてください。

## 投稿内容
- ID: {content_id}
- カテゴリ: {content_type}
- CTA: {cta_type}
- キャプション: {caption}
- ハッシュタグ: {' '.join(hashtags)}
{f'- スライド内容:{chr(10)}{slides_text}' if slides_text else ''}

## 評価基準（各項目1-10で採点）
1. ペルソナ適合度: ミサキ（28歳看護師）が手を止めるか？
2. フック強度: 1枚目で「見たい」と思うか？3秒ルール
3. 法的遵守: 架空設定か？患者情報なし？施設批判なし？
4. CTA適切性: 8:2ルール（ソフト/ハード比率）に合っているか？
5. 共感度: 看護師のリアルな気持ちに寄り添っているか？

## 出力形式（JSONのみ。説明文不要）
{{
  "score": 総合スコア（1-10の整数）,
  "persona_fit": 1-10,
  "hook_strength": 1-10,
  "legal_compliance": 1-10,
  "cta_quality": 1-10,
  "empathy": 1-10,
  "issues": ["問題点があれば記載"],
  "suggestion": "改善提案（1文）"
}}"""

        result = call_cloudflare_ai(prompt, SYSTEM_PROMPT, max_tokens=500, temperature=0.3)

        if result:
            review_data = _parse_json_from_text(result)
            if review_data and isinstance(review_data.get("score"), (int, float)):
                score = int(review_data["score"])
                post["ai_score"] = score
                post["ai_review"] = review_data

                status_mark = "PASS" if score >= 6 else "REJECT"
                if score < 6:
                    post["status"] = "rejected"
                    post["error"] = f"AI review score {score}/10: {review_data.get('suggestion', '')}"
                    rejected += 1
                else:
                    approved += 1

                issues = review_data.get("issues", [])
                issues_str = ", ".join(issues[:2]) if issues else "none"
                print(f"  Score: {score}/10 [{status_mark}] Issues: {issues_str}")

                reviewed += 1
                continue

        # If AI review failed, give a neutral pass
        print(f"  [WARN] AI review failed for #{post_id}. Assigning score 7 (default pass).")
        post["ai_score"] = 7
        approved += 1
        reviewed += 1

    save_queue(queue)

    print(f"\n{'=' * 60}")
    print(f"[REVIEW SUMMARY]")
    print(f"  Reviewed: {reviewed}")
    print(f"  Approved (score >= 6): {approved}")
    print(f"  Rejected (score < 6): {rejected}")
    print("=" * 60)

    if rejected > 0:
        slack_notify(
            f"[AI Review] {reviewed} posts reviewed: {approved} approved, {rejected} rejected.\n"
            f"Rejected posts need regeneration."
        )

    log_event("review_complete", {
        "reviewed": reviewed,
        "approved": approved,
        "rejected": rejected,
    })


# ============================================================
# Phase 4: Auto-Schedule (--schedule)
# ============================================================

def cmd_schedule():
    """
    Pick next pending posts from queue, prepare them for posting.
    Sets optimal posting times and creates content/ready/ directory.
    """
    print("=" * 60)
    print(f"[SCHEDULE] Content Scheduling - {timestamp_str()}")
    print("=" * 60)

    queue = load_queue()
    pending_posts = [
        p for p in queue.get("posts", [])
        if p.get("status") == "pending" and p.get("ai_score", 7) >= 6
    ]

    if not pending_posts:
        print("[INFO] No schedulable posts in queue.")
        return

    # Schedule up to 7 posts (1 week)
    to_schedule = pending_posts[:7]
    print(f"[SCHEDULE] Scheduling {len(to_schedule)} posts\n")

    READY_DIR.mkdir(parents=True, exist_ok=True)
    scheduled = []

    for i, post in enumerate(to_schedule):
        post_id = post["id"]
        content_id = post.get("content_id", "unknown")

        # Calculate scheduled datetime
        schedule_date = datetime.now() + timedelta(days=i)
        posting_time = POSTING_TIMES[i % len(POSTING_TIMES)]
        schedule_dt = f"{schedule_date.strftime('%Y-%m-%d')} {posting_time}"

        print(f"  #{post_id} {content_id} -> {schedule_dt}")

        # Prepare ready directory
        ready_name = f"{schedule_date.strftime('%Y%m%d')}_{content_id}"
        ready_subdir = READY_DIR / ready_name
        ready_subdir.mkdir(parents=True, exist_ok=True)

        # Copy slides if they exist
        slide_dir = PROJECT_DIR / post.get("slide_dir", "")
        slides_copied = 0
        if slide_dir.exists():
            for png in sorted(slide_dir.glob("*.png")):
                dest = ready_subdir / png.name
                shutil.copy2(str(png), str(dest))
                slides_copied += 1

        # Write caption.txt
        caption_file = ready_subdir / "caption.txt"
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(post.get("caption", ""))
            f.write("\n\n")
            f.write(" ".join(post.get("hashtags", [])))

        # Write schedule.json
        meta = {
            "post_id": post_id,
            "content_id": content_id,
            "scheduled_for": schedule_dt,
            "posting_time": posting_time,
            "content_type": post.get("content_type", ""),
            "cta_type": post.get("cta_type", ""),
            "ai_score": post.get("ai_score"),
            "slides_count": slides_copied,
            "prepared_at": datetime.now().isoformat(),
        }
        with open(ready_subdir / "schedule.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # Update queue
        post["status"] = "ready"
        post["scheduled_for"] = schedule_dt
        post["error"] = None

        scheduled.append({
            "post_id": post_id,
            "content_id": content_id,
            "scheduled_for": schedule_dt,
            "slides": slides_copied,
            "ready_dir": str(ready_subdir.relative_to(PROJECT_DIR)),
        })

    save_queue(queue)

    # Slack notification
    schedule_lines = [f"[Schedule] {len(scheduled)} posts scheduled:"]
    for s in scheduled:
        schedule_lines.append(
            f"  #{s['post_id']} {s['content_id']} -> {s['scheduled_for']} ({s['slides']} slides)"
        )
    schedule_lines.append(f"\nReady folders in content/ready/")
    schedule_lines.append(f"Upload via Buffer, then: python3 scripts/sns_workflow.py --mark-posted <ID>")
    slack_notify("\n".join(schedule_lines))

    print(f"\n{'=' * 60}")
    print(f"[SCHEDULE SUMMARY]")
    print(f"  Scheduled: {len(scheduled)} posts")
    for s in scheduled:
        print(f"    #{s['post_id']} {s['content_id']} -> {s['scheduled_for']} ({s['slides']} slides)")
    print(f"  Ready at: content/ready/")
    print("=" * 60)

    log_event("schedule_complete", {"scheduled": len(scheduled)})


# ============================================================
# Phase 5: Full Auto Mode (--auto)
# ============================================================

def cmd_auto():
    """
    Full autonomous mode: plan -> generate -> review -> schedule.
    Maintains a 2-week content buffer. Self-correcting.
    """
    print("=" * 60)
    print(f"[AUTO] Full Auto Mode - {timestamp_str()}")
    print("=" * 60)

    queue = load_queue()
    pending = count_pending(queue)
    statuses = count_by_status(queue)

    print(f"\n[AUTO] Queue status:")
    for status, cnt in sorted(statuses.items()):
        print(f"  {status}: {cnt}")
    print(f"  Total pending: {pending}")
    print(f"  Target buffer: {AUTO_TARGET_PENDING}")

    # Step 1: Plan
    print(f"\n{'=' * 50}")
    print("[AUTO] Step 1: Planning...")
    print(f"{'=' * 50}")
    plan_items = cmd_plan()

    # Step 2: Generate (only if queue needs more content)
    queue = load_queue()  # Reload
    pending = count_pending(queue)
    need_count = max(0, AUTO_MIN_PENDING - pending)

    if need_count > 0:
        print(f"\n{'=' * 50}")
        print(f"[AUTO] Step 2: Generating {need_count} posts (pending={pending} < min={AUTO_MIN_PENDING})")
        print(f"{'=' * 50}")
        cmd_generate(need_count)
    else:
        print(f"\n[AUTO] Step 2: Skip generation (pending={pending} >= min={AUTO_MIN_PENDING})")

    # Step 3: Review
    print(f"\n{'=' * 50}")
    print("[AUTO] Step 3: Quality Review...")
    print(f"{'=' * 50}")
    cmd_review()

    # Step 3.5: Self-correction - regenerate rejected posts
    queue = load_queue()
    rejected_count = sum(1 for p in queue.get("posts", []) if p.get("status") == "rejected")
    if rejected_count > 0:
        print(f"\n[AUTO] Self-correction: {rejected_count} posts rejected. Regenerating...")
        # Remove rejected posts from queue
        queue["posts"] = [p for p in queue["posts"] if p.get("status") != "rejected"]
        save_queue(queue)
        # Generate replacements
        cmd_generate(min(rejected_count, 5))
        # Re-review
        cmd_review()

    # Step 4: Schedule
    print(f"\n{'=' * 50}")
    print("[AUTO] Step 4: Scheduling...")
    print(f"{'=' * 50}")
    cmd_schedule()

    # Final status
    queue = load_queue()
    final_statuses = count_by_status(queue)

    print(f"\n{'=' * 60}")
    print("[AUTO] COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Final queue status:")
    for status, cnt in sorted(final_statuses.items()):
        print(f"    {status}: {cnt}")
    print(f"  Total: {sum(final_statuses.values())}")

    slack_notify(
        f"[AI Engine Auto] Complete.\n"
        f"Queue: {json.dumps(final_statuses, ensure_ascii=False)}\n"
        f"Total: {sum(final_statuses.values())}"
    )

    log_event("auto_complete", {"final_status": final_statuses})


# ============================================================
# Status Display (--status)
# ============================================================

def cmd_status():
    """Display comprehensive status of the content engine."""
    print("=" * 60)
    print(f"AI Content Engine Status - {timestamp_str()}")
    print("=" * 60)

    # Queue status
    queue = load_queue()
    statuses = count_by_status(queue)
    total = sum(statuses.values())
    pending = statuses.get("pending", 0)

    print(f"\n[QUEUE] {total} total posts")
    for status in ["pending", "ready", "posted", "rejected", "failed"]:
        cnt = statuses.get(status, 0)
        if cnt > 0:
            print(f"  {status:10s}: {cnt}")

    # Mix analysis
    mix = analyze_queue_mix(queue)
    total_active = sum(mix.values())
    print(f"\n[MIX] Active content balance ({total_active} posts):")
    for cat in MIX_RATIOS:
        cnt = mix.get(cat, 0)
        target_pct = MIX_RATIOS[cat] * 100
        actual_pct = (cnt / total_active * 100) if total_active > 0 else 0
        bar_len = int(actual_pct / 5)
        bar = "#" * bar_len
        print(f"  {cat:8s}: {cnt:2d} ({actual_pct:4.1f}% / {target_pct:4.0f}%) {bar}")

    # Plan status
    plan = load_plan()
    plan_items = plan.get("plans", [])
    planned = sum(1 for p in plan_items if p.get("status") == "planned")
    generated_from_plan = sum(1 for p in plan_items if p.get("status") == "generated")
    print(f"\n[PLAN] {len(plan_items)} items (planned: {planned}, generated: {generated_from_plan})")
    if plan.get("week_of"):
        print(f"  Week of: {plan['week_of']}")

    # AI review scores
    scored_posts = [p for p in queue.get("posts", []) if p.get("ai_score") is not None]
    if scored_posts:
        scores = [p["ai_score"] for p in scored_posts]
        avg_score = sum(scores) / len(scores)
        print(f"\n[QUALITY] {len(scored_posts)} reviewed, avg score: {avg_score:.1f}/10")
        print(f"  Approved (>=6): {sum(1 for s in scores if s >= 6)}")
        print(f"  Rejected (<6):  {sum(1 for s in scores if s < 6)}")

    # Ready directory
    if READY_DIR.exists():
        ready_dirs = [d for d in READY_DIR.iterdir() if d.is_dir()]
        if ready_dirs:
            print(f"\n[READY] {len(ready_dirs)} prepared for upload:")
            for d in sorted(ready_dirs)[:5]:
                pngs = list(d.glob("*.png"))
                print(f"  {d.name}/ ({len(pngs)} slides)")
            if len(ready_dirs) > 5:
                print(f"  ... and {len(ready_dirs) - 5} more")

    # Buffer health
    print(f"\n[HEALTH]")
    if pending >= AUTO_TARGET_PENDING:
        print(f"  Buffer: EXCELLENT ({pending} pending >= {AUTO_TARGET_PENDING} target)")
    elif pending >= AUTO_MIN_PENDING:
        print(f"  Buffer: GOOD ({pending} pending >= {AUTO_MIN_PENDING} minimum)")
    else:
        print(f"  Buffer: LOW ({pending} pending < {AUTO_MIN_PENDING} minimum)")
        print(f"  Run: python3 scripts/ai_content_engine.py --auto")

    print()


# ============================================================
# JSON Parsing Helper
# ============================================================

def _parse_json_from_text(text: str) -> Optional[Any]:
    """
    Parse JSON from text that may contain markdown fences or extra text.
    Handles both objects and arrays.
    """
    if not text:
        return None

    # Already parsed (list or dict from API)
    if isinstance(text, (list, dict)):
        return text

    text = str(text).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Remove markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find first JSON object
    for start_char, end_char in [("{", "}"), ("[", "]")]:
        start_idx = text.find(start_char)
        if start_idx == -1:
            continue

        # Find matching closing bracket
        depth = 0
        for i in range(start_idx, len(text)):
            if text[i] == start_char:
                depth += 1
            elif text[i] == end_char:
                depth -= 1
                if depth == 0:
                    candidate = text[start_idx:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break

    return None


# ============================================================
# Feedback Loop (--feedback-loop)
# ============================================================

def _content_type_to_category(content_type: str) -> str:
    """Map English content_type back to Japanese category name."""
    for jp, en in CATEGORY_TO_CONTENT_TYPE.items():
        if en == content_type:
            return jp
    return "あるある"


def _collect_category_performance(queue: dict) -> Dict[str, Dict]:
    """Collect per-category performance stats from posted entries.

    Returns dict like:
        {"あるある": {"count": 5, "total_views": 1200, "total_likes": 80,
                     "total_saves": 30, "has_perf_data": 3}, ...}
    """
    category_stats: Dict[str, Dict] = {}

    for post in queue.get("posts", []):
        if post.get("status") != "posted":
            continue

        cat_name = _content_type_to_category(post.get("content_type", "aruaru"))
        perf = post.get("performance", {})
        if not isinstance(perf, dict):
            perf = {}

        views = perf.get("views")
        likes = perf.get("likes")
        saves = perf.get("saves")

        if cat_name not in category_stats:
            category_stats[cat_name] = {
                "count": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_saves": 0,
                "has_perf_data": 0,
            }

        stats = category_stats[cat_name]
        stats["count"] += 1

        # Only count posts that have at least views data
        has_data = False
        if views is not None:
            stats["total_views"] += views
            has_data = True
        if likes is not None:
            stats["total_likes"] += likes
            has_data = True
        if saves is not None:
            stats["total_saves"] += saves
            has_data = True
        if has_data:
            stats["has_perf_data"] += 1

    return category_stats


def _compute_composite_score(stats: Dict) -> float:
    """Compute a weighted composite score for a category.

    Formula: views * 1.0 + likes * 2.0 + saves * 3.0
    Saves are weighted highest (algorithm signal + intent signal).
    """
    n = stats["has_perf_data"]
    if n == 0:
        return 0.0
    avg_views = stats["total_views"] / n
    avg_likes = stats["total_likes"] / n
    avg_saves = stats["total_saves"] / n
    return avg_views * 1.0 + avg_likes * 2.0 + avg_saves * 3.0


def cmd_feedback_loop():
    """Data-driven content generation: analyze performance -> adjust mix -> generate.

    1. Load posting_queue.json
    2. Analyze performance data per category (views, saves, likes averages)
    3. If 5+ posts have performance data, adjust MIX_RATIOS:
       - High-performing categories: +5% boost
       - Low-performing categories: -5% reduction
       - Normalize to 100%
    4. Log adjustment to Slack
    5. Save adjusted ratios to data/feedback_ratios.json
    6. Generate content with adjusted ratios
    """
    global MIX_RATIOS

    FEEDBACK_RATIOS_PATH = PROJECT_DIR / "data" / "feedback_ratios.json"

    print("=" * 60)
    print(f"[FEEDBACK] Performance-Based Content Loop - {timestamp_str()}")
    print("=" * 60)

    # Step 1: Update analytics (best-effort)
    print("\n[FEEDBACK] Step 1: Refreshing TikTok analytics...")
    try:
        analytics_script = PROJECT_DIR / "scripts" / "tiktok_analytics.py"
        if analytics_script.exists():
            result = subprocess.run(
                ["python3", str(analytics_script), "--update"],
                capture_output=True, text=True, timeout=120
            )
            print(result.stdout[-500:] if result.stdout else "  (no output)")
        else:
            print("  [INFO] tiktok_analytics.py not found, skipping refresh")
    except Exception as e:
        print(f"  [WARN] Analytics refresh failed: {e}")

    # Step 2: Load queue and analyze performance by category
    print("\n[FEEDBACK] Step 2: Analyzing performance by category...")
    queue = load_queue()
    category_stats = _collect_category_performance(queue)

    # Count total posts with actual performance data
    total_posts_with_data = sum(s["has_perf_data"] for s in category_stats.values())
    total_posted = sum(s["count"] for s in category_stats.values())

    print(f"  Posted: {total_posted} total, {total_posts_with_data} with performance data")

    if total_posts_with_data < 5:
        print(f"  Need 5+ posts with performance data for meaningful analysis.")
        print(f"  Using default MIX_RATIOS (no adjustment).")

        # Load previously saved feedback ratios if they exist
        if FEEDBACK_RATIOS_PATH.exists():
            try:
                with open(FEEDBACK_RATIOS_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                saved_ratios = saved.get("adjusted_ratios", {})
                if saved_ratios:
                    print(f"  Loading previously saved feedback ratios from {FEEDBACK_RATIOS_PATH.name}")
                    MIX_RATIOS = saved_ratios
            except Exception as e:
                print(f"  [WARN] Could not load saved ratios: {e}")
    else:
        # Display per-category stats
        print(f"\n  Per-category performance:")
        cat_scores = {}
        for cat_name, stats in category_stats.items():
            if stats["has_perf_data"] > 0:
                n = stats["has_perf_data"]
                avg_views = stats["total_views"] / n
                avg_likes = stats["total_likes"] / n
                avg_saves = stats["total_saves"] / n
                composite = _compute_composite_score(stats)
                cat_scores[cat_name] = composite
                print(f"    {cat_name}: {n} posts | avg views={avg_views:.0f}, "
                      f"likes={avg_likes:.0f}, saves={avg_saves:.0f} | score={composite:.0f}")
            else:
                print(f"    {cat_name}: {stats['count']} posts | no performance data")

        # Step 3: Adjust MIX_RATIOS with +/-5% per category
        if len(cat_scores) >= 2:
            global_avg_score = sum(cat_scores.values()) / len(cat_scores)
            print(f"\n  Global average composite score: {global_avg_score:.0f}")

            new_ratios = dict(MIX_RATIOS)
            adjustment_log = []

            for cat_name, score in cat_scores.items():
                if cat_name not in new_ratios:
                    continue

                old_val = new_ratios[cat_name]
                if score > global_avg_score:
                    # High-performing: +5%
                    new_ratios[cat_name] = old_val + 0.05
                    adjustment_log.append(f"{cat_name}: +5% (score {score:.0f} > avg {global_avg_score:.0f})")
                elif score < global_avg_score:
                    # Low-performing: -5%
                    new_ratios[cat_name] = max(0.02, old_val - 0.05)
                    adjustment_log.append(f"{cat_name}: -5% (score {score:.0f} < avg {global_avg_score:.0f})")
                else:
                    adjustment_log.append(f"{cat_name}: no change (score = avg)")

            # Normalize to sum=1.0
            total = sum(new_ratios.values())
            if total > 0:
                new_ratios = {k: round(v / total, 2) for k, v in new_ratios.items()}

            # Fix rounding: ensure sum is exactly 1.0
            rounding_diff = round(1.0 - sum(new_ratios.values()), 2)
            if rounding_diff != 0:
                # Add difference to the largest category
                largest_cat = max(new_ratios, key=new_ratios.get)
                new_ratios[largest_cat] = round(new_ratios[largest_cat] + rounding_diff, 2)

            # Display changes
            print(f"\n  Adjusted MIX_RATIOS:")
            change_lines = []
            for cat in MIX_RATIOS:
                old_pct = MIX_RATIOS[cat] * 100
                new_pct = new_ratios.get(cat, MIX_RATIOS[cat]) * 100
                arrow = "+" if new_pct > old_pct else ("-" if new_pct < old_pct else "=")
                line = f"    {cat}: {old_pct:.0f}% -> {new_pct:.0f}% ({arrow})"
                print(line)
                change_lines.append(f"{cat}: {old_pct:.0f}%->{new_pct:.0f}%")

            # Apply new ratios
            old_ratios = dict(MIX_RATIOS)
            MIX_RATIOS = new_ratios

            # Step 4: Save adjusted ratios to data/feedback_ratios.json
            feedback_data = {
                "timestamp": datetime.now().isoformat(),
                "original_ratios": old_ratios,
                "adjusted_ratios": new_ratios,
                "category_stats": {
                    cat: {
                        "posts": stats["count"],
                        "posts_with_data": stats["has_perf_data"],
                        "avg_views": round(stats["total_views"] / stats["has_perf_data"], 1) if stats["has_perf_data"] > 0 else None,
                        "avg_likes": round(stats["total_likes"] / stats["has_perf_data"], 1) if stats["has_perf_data"] > 0 else None,
                        "avg_saves": round(stats["total_saves"] / stats["has_perf_data"], 1) if stats["has_perf_data"] > 0 else None,
                        "composite_score": round(cat_scores.get(cat, 0), 1),
                    }
                    for cat, stats in category_stats.items()
                },
                "total_posts_analyzed": total_posted,
                "total_with_performance": total_posts_with_data,
                "adjustments": adjustment_log,
            }
            atomic_json_write(FEEDBACK_RATIOS_PATH, feedback_data)
            print(f"\n  Feedback ratios saved to {FEEDBACK_RATIOS_PATH}")

            # Step 5: Log adjustment to Slack
            slack_msg = (
                f"[Feedback Loop] MIX_RATIOS adjusted ({total_posts_with_data} posts analyzed)\n"
                + " | ".join(change_lines)
            )
            slack_notify(slack_msg)

        else:
            print(f"  Only {len(cat_scores)} categories with data. Need 2+. Using defaults.")

    # Step 6: Generate with adjusted ratios
    print(f"\n[FEEDBACK] Step 3: Running auto content generation with adjusted ratios...")
    cmd_auto()

    # Save performance analysis (legacy compatibility)
    analysis_file = PROJECT_DIR / "data" / "performance_analysis.json"
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "mix_ratios_used": MIX_RATIOS,
        "posted_count": total_posted,
        "posts_with_performance": total_posts_with_data,
    }
    atomic_json_write(analysis_file, analysis)

    print(f"\n[FEEDBACK] Complete. Analysis saved to {analysis_file}")


# ============================================================
# Content Calendar (--calendar)
# ============================================================

def _count_pending_and_ready(queue: dict) -> int:
    """Count posts with status 'pending' or 'ready'."""
    return sum(1 for p in queue.get("posts", [])
               if p.get("status") in ("pending", "ready"))


# Calendar-specific content type ratios (v2.0 戦略改定 2026-03-05)
CALENDAR_MIX_RATIOS = {
    "あるある": 0.35,
    "給与": 0.20,
    "業界裏側": 0.15,
    "地域ネタ": 0.15,
    "転職": 0.10,
    "トレンド": 0.05,
}

# Map calendar categories to content_type values used in queue
CALENDAR_CATEGORY_TO_CONTENT_TYPE = {
    "あるある": "aruaru",
    "給与": "salary",
    "業界裏側": "industry",
    "地域ネタ": "local",
    "転職": "career",
    "トレンド": "trend",
}


def cmd_calendar():
    """Maintain a rolling 2-week content calendar.

    Checks pending/ready posts count, auto-generates up to 14 total items
    if pending < 7, assigns scheduled_date (skipping Sundays), and
    balances content_type ratios per CALENDAR_MIX_RATIOS.
    """
    print("=" * 60)
    print(f"[CALENDAR] Content Calendar Manager - {timestamp_str()}")
    print("=" * 60)

    queue = load_queue()
    pending_ready = _count_pending_and_ready(queue)
    statuses = count_by_status(queue)

    print(f"\n  Current queue: {sum(statuses.values())} total posts")
    for s, c in sorted(statuses.items()):
        print(f"    {s}: {c}")
    print(f"\n  Pending + ready: {pending_ready}")
    print(f"  Threshold: {AUTO_MIN_PENDING} (trigger generation if below)")
    print(f"  Target:    {AUTO_TARGET_PENDING} (generate up to this many)")

    # --- Auto-generate if buffer is low ---
    generated_count = 0
    if pending_ready < AUTO_MIN_PENDING:
        need = AUTO_TARGET_PENDING - pending_ready
        if need > 0:
            # Determine content type distribution for new posts
            current_mix = _analyze_calendar_mix(queue)
            type_plan = _plan_calendar_types(need, current_mix)
            print(f"\n  Buffer low ({pending_ready} < {AUTO_MIN_PENDING}). Generating {need} posts...")
            print(f"  Planned type distribution: {type_plan}")
            cmd_generate(need)
            queue = load_queue()  # Reload after generation
            generated_count = need
    else:
        print(f"\n  Buffer sufficient ({pending_ready} >= {AUTO_MIN_PENDING}). No generation needed.")

    # --- Assign scheduled_dates to unscheduled pending/ready posts ---
    today = datetime.now().date()
    schedule_idx = 0

    # Load posting schedule (defines available days and times; Sunday is skipped)
    schedule_file = PROJECT_DIR / "data" / "posting_schedule.json"
    if schedule_file.exists():
        with open(schedule_file, encoding="utf-8") as f:
            schedule_data = json.load(f)
        day_times = schedule_data.get("schedule", {})
    else:
        # Default: Mon-Sat with varying times. Sunday excluded = skip.
        day_times = {"Mon": "17:30", "Tue": "12:00", "Wed": "21:00",
                     "Thu": "17:30", "Fri": "18:00", "Sat": "20:00"}

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    posts_to_schedule = [p for p in queue.get("posts", [])
                         if p.get("status") in ("pending", "ready") and not p.get("scheduled_date")]

    # Also collect already-scheduled dates to avoid double-booking
    already_scheduled = set()
    for p in queue.get("posts", []):
        sd = p.get("scheduled_date", "")
        if sd:
            already_scheduled.add(sd.split(" ")[0] if " " in sd else sd)

    scheduled_count = 0
    scheduled_details = []
    for post in posts_to_schedule:
        # Find next available day (skip Sundays explicitly)
        while schedule_idx < 60:  # Look up to 60 days ahead
            target_date = today + timedelta(days=schedule_idx + 1)
            day_name = day_names[target_date.weekday()]
            date_str = target_date.isoformat()
            # Skip Sundays (not in day_times schedule) and already-booked dates
            if day_name in day_times and date_str not in already_scheduled:
                time_str = day_times[day_name]
                post["scheduled_date"] = f"{date_str} {time_str}"
                already_scheduled.add(date_str)
                scheduled_count += 1
                scheduled_details.append(
                    f"    #{post.get('id')} ({post.get('content_type', '?')}) -> {date_str} {day_name} {time_str}"
                )
                schedule_idx += 1
                break
            schedule_idx += 1

    if scheduled_count > 0:
        save_queue(queue)
        print(f"\n  Scheduled {scheduled_count} posts (Sundays skipped):")
        for detail in scheduled_details:
            print(detail)
    else:
        print(f"\n  No posts needed scheduling.")

    # --- Validate content type MIX ratios ---
    cal_mix = _analyze_calendar_mix(queue)
    total_active = sum(cal_mix.values())
    print(f"\n  Content MIX across calendar ({total_active} active posts):")
    for cat, target_ratio in CALENDAR_MIX_RATIOS.items():
        cnt = cal_mix.get(cat, 0)
        target_pct = target_ratio * 100
        actual_pct = (cnt / total_active * 100) if total_active > 0 else 0
        ok = abs(actual_pct - target_pct) <= 15
        indicator = "[OK]" if ok else "[!!]"
        print(f"    {indicator} {cat}: {cnt} posts = {actual_pct:.0f}% (target {target_pct:.0f}%)")

    # --- Validate CTA 8:2 rule ---
    cta_counts = {"soft": 0, "hard": 0}
    for p in queue.get("posts", []):
        if p.get("status") in ("pending", "ready"):
            cta_counts[p.get("cta_type", "soft")] += 1

    total_cta = sum(cta_counts.values())
    if total_cta > 0:
        hard_pct = cta_counts["hard"] / total_cta * 100
        ok = 10 <= hard_pct <= 30
        indicator = "[OK]" if ok else "[!!]"
        print(f"\n  {indicator} CTA balance: soft={cta_counts['soft']} hard={cta_counts['hard']} ({hard_pct:.0f}% hard, target 20%)")

    # --- Summary ---
    final_pending_ready = _count_pending_and_ready(queue)
    summary = (
        f"[Calendar] Complete: {generated_count} generated, "
        f"{scheduled_count} scheduled, {final_pending_ready} total pending/ready"
    )
    print(f"\n{summary}")

    log_event("calendar", {
        "generated": generated_count,
        "scheduled": scheduled_count,
        "pending_ready": final_pending_ready,
        "mix": cal_mix,
    })

    slack_notify(summary)


def _analyze_calendar_mix(queue: dict) -> Dict[str, int]:
    """Analyze content type distribution using CALENDAR_MIX_RATIOS categories."""
    dist: Dict[str, int] = {cat: 0 for cat in CALENDAR_MIX_RATIOS}
    for p in queue.get("posts", []):
        if p.get("status") in ("pending", "ready"):
            ct = p.get("content_type", "")
            for cat, ctype in CALENDAR_CATEGORY_TO_CONTENT_TYPE.items():
                if ctype == ct:
                    dist[cat] += 1
                    break
            else:
                # Map regional, local etc. to closest category
                if ct in ("regional", "local"):
                    dist["あるある"] = dist.get("あるある", 0) + 1
    return dist


def _plan_calendar_types(need: int, current_mix: Dict[str, int]) -> Dict[str, int]:
    """Plan how many of each content type to generate to reach target ratios."""
    total_after = sum(current_mix.values()) + need
    plan: Dict[str, int] = {}
    remaining = need

    for cat, ratio in sorted(CALENDAR_MIX_RATIOS.items(), key=lambda x: -x[1]):
        target_count = max(0, round(total_after * ratio) - current_mix.get(cat, 0))
        assigned = min(target_count, remaining)
        if assigned > 0:
            plan[cat] = assigned
            remaining -= assigned

    # Distribute any remaining to the largest category
    if remaining > 0:
        top_cat = max(CALENDAR_MIX_RATIOS, key=CALENDAR_MIX_RATIOS.get)
        plan[top_cat] = plan.get(top_cat, 0) + remaining

    return plan


# ============================================================
# Main CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="AI Content Engine for 神奈川ナース転職 (Claude Code CLI + CF AI fallback)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --auto              Full auto: plan -> generate -> review -> schedule
  %(prog)s --feedback-loop     Data-driven: analytics -> adjust mix -> generate
  %(prog)s --calendar          Maintain 2-week rolling content calendar
  %(prog)s --plan              Generate a 1-week content plan
  %(prog)s --generate 7        Generate 7 carousel content sets
  %(prog)s --review            Quality-check all pending content
  %(prog)s --schedule          Schedule and prepare next posts
  %(prog)s --status            Show engine status

AI: Claude Code CLI (subscription, no extra cost). Fallback: Cloudflare Workers AI (FREE).
        """,
    )

    parser.add_argument("--auto", action="store_true",
                        help="Full auto mode: plan -> generate -> review -> schedule")
    parser.add_argument("--feedback-loop", action="store_true",
                        help="Data-driven: refresh analytics -> adjust MIX -> generate")
    parser.add_argument("--calendar", action="store_true",
                        help="Maintain 2-week rolling content calendar")
    parser.add_argument("--plan", action="store_true",
                        help="AI content planning (1-week plan)")
    parser.add_argument("--generate", type=int, metavar="N",
                        help="Generate N carousel content sets")
    parser.add_argument("--review", action="store_true",
                        help="AI quality review of pending content")
    parser.add_argument("--schedule", action="store_true",
                        help="Schedule and prepare posts for upload")
    parser.add_argument("--status", action="store_true",
                        help="Show engine status")

    args = parser.parse_args()

    # Load environment
    load_env()

    # Ensure data directory exists
    (PROJECT_DIR / "data").mkdir(parents=True, exist_ok=True)

    if args.auto:
        cmd_auto()
    elif args.feedback_loop:
        cmd_feedback_loop()
    elif args.calendar:
        cmd_calendar()
    elif args.plan:
        cmd_plan()
    elif args.generate is not None:
        cmd_generate(args.generate)
    elif args.review:
        cmd_review()
    elif args.schedule:
        cmd_schedule()
    elif args.status:
        cmd_status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
