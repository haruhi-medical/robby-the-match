#!/usr/bin/env python3
"""Insert or update a diagnostic CTA block into area, guide, and blog HTML pages.

The CTA block uses inline styles matching the LP's premium design language:
  - Primary: #1a7f64 (teal)
  - CTA button: #06C755 (LINE green)
  - Dark text: #1a1a2e
  - Light bg: #f8fffe
  - Font: system stack + Noto Sans JP
  - Rounded corners (16px card, 50px button)
  - Subtle shadows and transitions
"""

import os
import re

BASE = os.path.expanduser("~/robby-the-match")

AREA_MAP = {
    "yokohama.html": "yokohama_kawasaki",
    "kawasaki.html": "yokohama_kawasaki",
    "fujisawa.html": "shonan_kamakura",
    "chigasaki.html": "shonan_kamakura",
    "kamakura.html": "shonan_kamakura",
    "hiratsuka.html": "shonan_kamakura",
    "oiso.html": "shonan_kamakura",
    "ninomiya.html": "shonan_kamakura",
    "odawara.html": "odawara_seisho",
    "minamiashigara.html": "odawara_seisho",
    "matsuda.html": "odawara_seisho",
    "kaisei.html": "odawara_seisho",
    "hakone.html": "odawara_seisho",
    "yamakita.html": "odawara_seisho",
    "sagamihara.html": "sagamihara_kenoh",
    "atsugi.html": "sagamihara_kenoh",
    "ebina.html": "sagamihara_kenoh",
    "yamato.html": "sagamihara_kenoh",
    "hadano.html": "sagamihara_kenoh",
    "isehara.html": "sagamihara_kenoh",
    "yokosuka.html": "yokosuka_miura",
}


def make_cta(href="/lp/job-seeker/#shindan"):
    return f"""<!-- shindan-cta -->
<div style="background:linear-gradient(170deg,#f0faf7 0%,#ffffff 60%,#f8fffe 100%);padding:40px 24px;text-align:center;margin:48px 0 0;border-radius:16px;border:1px solid rgba(26,127,100,0.1);box-shadow:0 4px 20px rgba(26,127,100,0.06);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans JP','Hiragino Sans','Hiragino Kaku Gothic ProN',Meiryo,sans-serif;">
  <p style="font-size:0.8rem;color:#1a7f64;margin:0 0 8px;font-weight:700;letter-spacing:0.1em;">AI CAREER MATCH</p>
  <p style="font-size:1.2rem;color:#1a1a2e;margin:0 0 8px;font-weight:800;line-height:1.5;">あなたにマッチする求人、<br>何件あるか知りたくないですか？</p>
  <p style="font-size:0.85rem;color:#666;margin:0 0 20px;line-height:1.6;">たった30秒・3問で診断できます（LINE登録不要）</p>
  <a href="{href}" style="display:inline-block;background:#06C755;color:#fff;padding:16px 40px;border-radius:50px;text-decoration:none;font-weight:700;font-size:1rem;box-shadow:0 4px 16px rgba(6,199,85,0.3);transition:transform 0.2s,box-shadow 0.2s;min-height:48px;line-height:1.4;">30秒で求人診断 &#9654;</a>
  <p style="font-size:0.75rem;color:#999;margin:12px 0 0;">&#x2705; 完全無料 &#x2705; 登録不要 &#x2705; 神奈川県特化</p>
</div>
<!-- /shindan-cta -->"""


def collect_files():
    files = []
    # area pages
    area_dir = os.path.join(BASE, "lp/job-seeker/area")
    for f in sorted(os.listdir(area_dir)):
        if f.endswith(".html") and f != "index.html":
            files.append((os.path.join(area_dir, f), "area", f))
    # guide pages
    guide_dir = os.path.join(BASE, "lp/job-seeker/guide")
    for f in sorted(os.listdir(guide_dir)):
        if f.endswith(".html") and f != "index.html":
            files.append((os.path.join(guide_dir, f), "guide", f))
    # blog pages
    blog_dir = os.path.join(BASE, "blog")
    for f in sorted(os.listdir(blog_dir)):
        if f.endswith(".html") and f != "index.html":
            files.append((os.path.join(blog_dir, f), "blog", f))
    return files


def patch_file(path, category, filename):
    with open(path, "r", encoding="utf-8") as fh:
        html = fh.read()

    # Determine href
    if category == "area" and filename in AREA_MAP:
        href = f"/lp/job-seeker/#shindan?area={AREA_MAP[filename]}"
    else:
        href = "/lp/job-seeker/#shindan"

    cta = make_cta(href)

    # Replace existing CTA block if present
    if "<!-- shindan-cta -->" in html:
        html = re.sub(
            r"<!-- shindan-cta -->.*?<!-- /shindan-cta -->",
            cta,
            html,
            flags=re.DOTALL,
        )
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        return "UPDATED"

    # Insert before last </footer>, or before </body>
    footer_matches = list(re.finditer(r"</footer>", html, re.IGNORECASE))
    if footer_matches:
        pos = footer_matches[-1].start()
        html = html[:pos] + cta + "\n" + html[pos:]
    else:
        body_matches = list(re.finditer(r"</body>", html, re.IGNORECASE))
        if body_matches:
            pos = body_matches[-1].start()
            html = html[:pos] + cta + "\n" + html[pos:]
        else:
            # Append at end as fallback
            html += "\n" + cta + "\n"

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return "PATCHED"


def main():
    files = collect_files()
    patched = 0
    updated = 0
    for path, category, filename in files:
        result = patch_file(path, category, filename)
        if result == "PATCHED":
            patched += 1
            print(f"  PATCHED: {path}")
        elif result == "UPDATED":
            updated += 1
            print(f"  UPDATED: {path}")
    print(f"\nDone. New: {patched}, Updated: {updated}, Total: {len(files)}")


if __name__ == "__main__":
    main()
