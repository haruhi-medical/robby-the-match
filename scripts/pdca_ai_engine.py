#!/usr/bin/env python3
"""
pdca_ai_engine.py — ナースロビー PDCA AIエンジン

Cloudflare Workers AI (Llama 3.3 70B, FREE) を使ったPDCAサイクル実行。
Claude CLI (run_claude) の代替。LLMにはテキスト分析・要約・提案のみ任せ、
ファイルI/Oは全てPythonが担う。

使い方:
  python3 scripts/pdca_ai_engine.py --job competitor [--dry-run]
  python3 scripts/pdca_ai_engine.py --job review [--dry-run]
  python3 scripts/pdca_ai_engine.py --job seo_batch [--dry-run]
  python3 scripts/pdca_ai_engine.py --job weekly [--dry-run]

コスト: Cloudflare Workers AI 10,000 neurons/day 無料。
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional, Tuple

# ============================================================
# Constants
# ============================================================

PROJECT_DIR = Path(__file__).parent.parent
ENV_FILE = PROJECT_DIR / ".env"
LOG_DIR = PROJECT_DIR / "logs"
CF_AI_MODEL = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

TODAY = datetime.now().strftime("%Y-%m-%d")
NOW = datetime.now().strftime("%H:%M:%S")


# ============================================================
# Environment & Logging
# ============================================================

def load_env():
    """Load .env file."""
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


load_env()


def get_cf_credentials() -> Tuple[str, str]:
    """Get Cloudflare credentials from environment."""
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not account_id or not api_token:
        print("[FATAL] CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_API_TOKEN not set in .env")
        sys.exit(78)  # EXIT_CONFIG_ERROR
    return account_id, api_token


def log(msg: str):
    """Print and append to daily log."""
    print(msg)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"pdca_ai_{TODAY}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{NOW}] {msg}\n")


def slack_notify(message: str):
    """Send Slack notification."""
    try:
        subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "notify_slack.py"),
             "--message", message],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        print(f"[WARN] Slack notification failed: {e}")


# ============================================================
# Cloudflare Workers AI Client (reused from ai_content_engine.py)
# ============================================================

def call_cf_ai(
    prompt: str,
    system_prompt: str = "",
    max_tokens: int = 2048,
    temperature: float = 0.5,
    retries: int = 2,
) -> Optional[str]:
    """Call Cloudflare Workers AI (Llama 3.3 70B). Returns text or None."""
    import urllib.request
    import urllib.error

    account_id, api_token = get_cf_credentials()
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

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("success"):
                    result = data.get("result", {})
                    response_text = result.get("response", "")
                    if response_text:
                        return response_text
                    print(f"  [WARN] Empty response (attempt {attempt + 1})")
                else:
                    errors = data.get("errors", [])
                    print(f"  [WARN] CF AI errors: {errors}")
        except urllib.error.HTTPError as e:
            print(f"  [WARN] CF AI HTTP {e.code} (attempt {attempt + 1})")
            if e.code == 429 and attempt < retries:
                time.sleep((attempt + 1) * 5)
                continue
        except Exception as e:
            print(f"  [WARN] CF AI request failed (attempt {attempt + 1}): {e}")

        if attempt < retries:
            time.sleep(2)

    return None


# ============================================================
# File I/O Helpers
# ============================================================

def read_file(path: str, max_lines: int = 200) -> str:
    """Read a file relative to PROJECT_DIR. Returns empty string if not found."""
    fp = PROJECT_DIR / path
    if not fp.exists():
        return ""
    try:
        lines = fp.read_text(encoding="utf-8").splitlines()
        return "\n".join(lines[:max_lines])
    except Exception as e:
        print(f"[WARN] Cannot read {path}: {e}")
        return ""


def append_to_md(path: str, content: str):
    """Append content to a markdown file, adding date header if needed."""
    fp = PROJECT_DIR / path
    existing = fp.read_text(encoding="utf-8") if fp.exists() else ""

    if f"## {TODAY}" not in existing:
        existing += f"\n## {TODAY}\n\n"

    existing += content + "\n\n"
    fp.write_text(existing, encoding="utf-8")


def update_state_timestamp(section: str):
    """Update the timestamp in STATE.md."""
    state_path = PROJECT_DIR / "STATE.md"
    if not state_path.exists():
        return
    text = state_path.read_text(encoding="utf-8")
    text = re.sub(
        r"# 最終更新:.*",
        f"# 最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')} by {section}",
        text,
    )
    state_path.write_text(text, encoding="utf-8")


# ============================================================
# HTML Meta Extraction
# ============================================================

class MetaExtractor(HTMLParser):
    """Extract title, h1, and meta description from HTML."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.description = ""
        self._in_title = False
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        elif tag == "h1" and not self.h1:
            self._in_h1 = True
        elif tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("name", "").lower() == "description":
                self.description = attrs_dict.get("content", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data.strip()
        elif self._in_h1:
            self.h1 += data.strip()


def extract_seo_meta(html_dir: str) -> list:
    """Extract SEO meta from all HTML files in a directory."""
    dir_path = PROJECT_DIR / html_dir
    if not dir_path.exists():
        return []

    results = []
    for html_file in sorted(dir_path.glob("*.html")):
        try:
            content = html_file.read_text(encoding="utf-8", errors="ignore")
            parser = MetaExtractor()
            parser.feed(content)
            results.append({
                "file": str(html_file.relative_to(PROJECT_DIR)),
                "title": parser.title[:100],
                "h1": parser.h1[:100],
                "description": parser.description[:160],
            })
        except Exception as e:
            print(f"[WARN] Cannot parse {html_file.name}: {e}")
    return results


def count_pages() -> dict:
    """Count HTML pages in key directories."""
    counts = {}
    for d in ["lp/job-seeker/area", "lp/job-seeker/guide", "blog"]:
        dp = PROJECT_DIR / d
        if dp.exists():
            counts[d] = len(list(dp.glob("*.html")))
        else:
            counts[d] = 0
    return counts


# ============================================================
# Job: competitor (内部SEOギャップ分析)
# ============================================================

def run_competitor(dry_run: bool = False) -> int:
    log("[competitor] 開始: 内部SEOギャップ分析")

    state_md = read_file("STATE.md")
    seo_strategy = read_file("docs/seo_strategy.md", max_lines=100)
    pages = count_pages()

    prompt = f"""あなたはSEOアナリストです。以下のデータから内部SEOギャップを分析し、改善提案をしてください。

## 現在のページ数
- area/（地域別ページ）: {pages.get('lp/job-seeker/area', 0)}ページ
- guide/（転職ガイド）: {pages.get('lp/job-seeker/guide', 0)}ページ
- blog/: {pages.get('blog', 0)}記事

## STATE.md（現状）
{state_md[:1500]}

## SEO戦略メモ
{seo_strategy[:1000]}

以下を日本語で簡潔に回答してください（500文字以内）:
1. カバレッジの穴（対象エリアでページがない地域や、不足しているガイドテーマ）
2. 改善優先度の高いアクション3つ
3. 次に作るべきページ2-3本の提案（タイトル案付き）
"""

    if dry_run:
        log(f"[competitor][DRY-RUN] Prompt length: {len(prompt)} chars")
        log(f"[competitor][DRY-RUN] Pages: {pages}")
        return 0

    result = call_cf_ai(prompt, system_prompt="看護師転職サイトのSEOアナリスト。簡潔に日本語で回答。")
    if not result:
        log("[competitor] ERROR: CF AI応答なし")
        return 1

    log(f"[competitor] AI分析結果:\n{result[:500]}")
    append_to_md("PROGRESS.md", f"### 🔎 競合・SEOギャップ分析（{NOW}）\n{result}")
    update_state_timestamp("競合分析")
    slack_notify(f"🔎 競合・SEOギャップ分析完了\n{result[:200]}")
    return 0


# ============================================================
# Job: review (日次レビュー)
# ============================================================

def run_review(dry_run: bool = False) -> int:
    log("[review] 開始: 日次レビュー")

    state_md = read_file("STATE.md")

    # パフォーマンスデータ読み込み
    perf_data = ""
    perf_path = PROJECT_DIR / "data" / "performance_analysis.json"
    if perf_path.exists():
        try:
            with open(perf_path, "r", encoding="utf-8") as f:
                perf = json.load(f)
            perf_data = json.dumps(perf, ensure_ascii=False, indent=None)[:1000]
        except Exception:
            perf_data = "(読込失敗)"

    # KPIログ（最新10行）
    kpi_data = ""
    kpi_path = PROJECT_DIR / "data" / "kpi_log.csv"
    if kpi_path.exists():
        try:
            lines = kpi_path.read_text(encoding="utf-8").splitlines()
            kpi_data = "\n".join(lines[:1] + lines[-10:])  # header + last 10
        except Exception:
            kpi_data = "(読込失敗)"

    # 今日のログからERROR/WARN抽出
    errors = []
    for log_file in LOG_DIR.glob(f"*_{TODAY}.log"):
        try:
            for line in log_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if any(kw in line for kw in ["ERROR", "WARN", "TIMEOUT", "FATAL"]):
                    errors.append(f"{log_file.name}: {line.strip()[:120]}")
        except Exception:
            pass
    error_summary = "\n".join(errors[-20:]) if errors else "エラーなし"

    # エージェント状態
    agent_state = ""
    agent_path = PROJECT_DIR / "data" / "agent_state.json"
    if agent_path.exists():
        try:
            with open(agent_path, "r", encoding="utf-8") as f:
                agent = json.load(f)
            statuses = agent.get("status", {})
            last_runs = agent.get("lastRun", {})
            agent_state = "\n".join(
                f"  {k}: {v} (最終実行: {last_runs.get(k, '不明')})"
                for k, v in statuses.items()
            )
        except Exception:
            agent_state = "(読込失敗)"

    pages = count_pages()

    prompt = f"""あなたは運用マネージャーです。以下のデータから日次レビューを作成してください。

## STATE.md
{state_md[:1500]}

## パフォーマンスデータ
{perf_data}

## KPIログ（最新）
{kpi_data[:500]}

## 今日のエラー/警告
{error_summary[:500]}

## エージェント稼働状況
{agent_state[:500]}

## ページ数
area: {pages.get('lp/job-seeker/area', 0)}, guide: {pages.get('lp/job-seeker/guide', 0)}, blog: {pages.get('blog', 0)}

以下を日本語で簡潔に回答（600文字以内）:
1. 今日のサマリ（3行）
2. 要注意事項（エラー/パフォーマンス低下）
3. 明日やるべきこと（3つ）
"""

    if dry_run:
        log(f"[review][DRY-RUN] Prompt length: {len(prompt)} chars")
        log(f"[review][DRY-RUN] Errors: {len(errors)}, Pages: {pages}")
        return 0

    result = call_cf_ai(prompt, system_prompt="ナースロビーの運用マネージャー。簡潔に日本語で。")
    if not result:
        log("[review] ERROR: CF AI応答なし")
        return 1

    log(f"[review] 日次レビュー結果:\n{result[:500]}")
    append_to_md("PROGRESS.md", f"### 📊 日次レビュー（{NOW}）\n{result}")
    update_state_timestamp("日次レビュー")
    slack_notify(f"📊 {TODAY} 日次レビュー\n━━━━━━━━━━━━\n{result[:300]}")
    return 0


# ============================================================
# Job: seo_batch (SEO診断+改善)
# ============================================================

def run_seo_batch(dry_run: bool = False) -> int:
    log("[seo_batch] 開始: SEO診断")

    # 全area/guide HTMLからメタ情報抽出
    area_meta = extract_seo_meta("lp/job-seeker/area")
    guide_meta = extract_seo_meta("lp/job-seeker/guide")
    blog_meta = extract_seo_meta("blog")

    # メタ情報をコンパクトにまとめる
    def format_meta(metas: list) -> str:
        lines = []
        for m in metas:
            lines.append(f"- {m['file']}: title=\"{m['title']}\" h1=\"{m['h1']}\" desc=\"{m['description'][:60]}...\"")
        return "\n".join(lines)

    area_text = format_meta(area_meta[:30])  # トークン節約
    guide_text = format_meta(guide_meta[:30])

    state_md = read_file("STATE.md", max_lines=80)
    pages = count_pages()

    prompt = f"""あなたはSEO専門家です。以下のページのSEO診断と改善提案をしてください。

## 現在のページ数
area: {pages.get('lp/job-seeker/area', 0)}, guide: {pages.get('lp/job-seeker/guide', 0)}, blog: {pages.get('blog', 0)}

## area/（地域別ページ）のメタ情報
{area_text[:1500]}

## guide/（転職ガイド）のメタ情報
{guide_text[:1500]}

## STATE.md
{state_md[:800]}

以下を日本語で回答（800文字以内）:
1. SEO改善が必要なページ（title/h1/descriptionの問題点）最大5つ
2. 不足しているテーマ/地域（新規ページ提案3本、タイトルとターゲットKW付き）
3. 内部リンクの改善提案
"""

    if dry_run:
        log(f"[seo_batch][DRY-RUN] area pages: {len(area_meta)}, guide pages: {len(guide_meta)}, blog: {len(blog_meta)}")
        log(f"[seo_batch][DRY-RUN] Prompt length: {len(prompt)} chars")
        return 0

    result = call_cf_ai(prompt, system_prompt="看護師転職サイトのSEO専門家。簡潔に日本語で。", max_tokens=2048)
    if not result:
        log("[seo_batch] ERROR: CF AI応答なし")
        return 1

    log(f"[seo_batch] SEO診断結果:\n{result[:500]}")
    append_to_md("PROGRESS.md", f"### 🔍 SEO診断（{NOW}）\n{result}")
    update_state_timestamp("SEO朝サイクル")

    # sitemap ping
    try:
        import urllib.request
        sitemap_url = "https://quads-nurse.com/sitemap.xml"
        ping_url = f"https://www.google.com/ping?sitemap={sitemap_url}"
        urllib.request.urlopen(ping_url, timeout=10)
        log("[seo_batch] Sitemap ping sent")
    except Exception as e:
        log(f"[seo_batch] Sitemap ping failed: {e}")

    slack_notify(f"🔍 SEO診断完了\n{result[:200]}")
    return 0


# ============================================================
# Job: weekly (週次総括)
# ============================================================

def run_weekly(dry_run: bool = False) -> int:
    log("[weekly] 開始: 週次総括")

    state_md = read_file("STATE.md")
    progress_md = read_file("PROGRESS.md", max_lines=150)

    # パフォーマンスデータ
    perf_data = ""
    perf_path = PROJECT_DIR / "data" / "performance_analysis.json"
    if perf_path.exists():
        try:
            with open(perf_path, "r", encoding="utf-8") as f:
                perf = json.load(f)
            perf_data = json.dumps(perf, ensure_ascii=False, indent=None)[:1200]
        except Exception:
            perf_data = "(読込失敗)"

    # KPIログ
    kpi_data = ""
    kpi_path = PROJECT_DIR / "data" / "kpi_log.csv"
    if kpi_path.exists():
        try:
            lines = kpi_path.read_text(encoding="utf-8").splitlines()
            kpi_data = "\n".join(lines[:1] + lines[-14:])  # header + last 2 weeks
        except Exception:
            kpi_data = "(読込失敗)"

    # git log (1 week)
    git_log = ""
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "--since=7 days ago"],
            capture_output=True, text=True, timeout=10, cwd=str(PROJECT_DIR),
        )
        git_log = r.stdout[:500]
    except Exception:
        git_log = "(取得失敗)"

    pages = count_pages()
    week_num = datetime.now().strftime("%V")

    prompt = f"""あなたは経営参謀AIです。以下のデータから週次総括レポートを作成してください。

## STATE.md
{state_md[:1500]}

## 今週のPROGRESS.md（抜粋）
{progress_md[:1500]}

## パフォーマンスデータ
{perf_data[:800]}

## KPIログ
{kpi_data[:500]}

## 今週のgit commits
{git_log[:400]}

## ページ数
area: {pages.get('lp/job-seeker/area', 0)}, guide: {pages.get('lp/job-seeker/guide', 0)}, blog: {pages.get('blog', 0)}

以下を日本語で回答（1000文字以内）:
1. 今週のサマリ（5行以内）
2. KPI進捗（目標対比）
3. マイルストーン進捗チェック
4. ピーター・ティールの問い: 今週やったことで1人の看護師の意思決定に影響を与えたか？
5. 来週の最優先アクション3つ
"""

    if dry_run:
        log(f"[weekly][DRY-RUN] Prompt length: {len(prompt)} chars")
        log(f"[weekly][DRY-RUN] Pages: {pages}, Week: {week_num}")
        return 0

    result = call_cf_ai(prompt, system_prompt="ナースロビーの経営参謀AI。簡潔に日本語で。", max_tokens=2048)
    if not result:
        log("[weekly] ERROR: CF AI応答なし")
        return 1

    log(f"[weekly] 週次総括:\n{result[:600]}")
    append_to_md("PROGRESS.md", f"### 📈 Week{week_num} 週次総括（{NOW}）\n{result}")
    update_state_timestamp("週次総括")

    # コンテンツパイプライン呼び出し
    log("[weekly] コンテンツパイプライン実行...")
    try:
        r = subprocess.run(
            ["python3", str(PROJECT_DIR / "scripts" / "content_pipeline.py"), "--force", "7"],
            capture_output=True, text=True, timeout=300, cwd=str(PROJECT_DIR),
        )
        if r.returncode == 0:
            log("[weekly] コンテンツ生成完了")
        else:
            log(f"[weekly] コンテンツ生成失敗 (exit {r.returncode})")
    except Exception as e:
        log(f"[weekly] コンテンツ生成エラー: {e}")

    slack_notify(f"📈 Week{week_num} 週次レポート\n━━━━━━━━━━━━\n{result[:400]}")
    return 0


# ============================================================
# Main
# ============================================================

JOBS = {
    "competitor": run_competitor,
    "review": run_review,
    "seo_batch": run_seo_batch,
    "weekly": run_weekly,
}


def main():
    parser = argparse.ArgumentParser(description="ナースロビー PDCA AIエンジン")
    parser.add_argument("--job", required=True, choices=JOBS.keys(), help="実行するジョブ")
    parser.add_argument("--dry-run", action="store_true", help="AIを呼ばずにデータ収集のみ")
    args = parser.parse_args()

    log(f"[pdca_ai_engine] job={args.job} dry_run={args.dry_run}")

    # Verify credentials exist before running
    get_cf_credentials()

    exit_code = JOBS[args.job](dry_run=args.dry_run)
    log(f"[pdca_ai_engine] job={args.job} 完了 (exit={exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
