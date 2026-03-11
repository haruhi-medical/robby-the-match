#!/usr/bin/env python3
"""Insert a diagnostic CTA block into area, guide, and blog HTML pages."""

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
<div style="background:linear-gradient(135deg,#f0faf7,#e8f5e9);padding:32px 16px;text-align:center;margin:40px 0 0;border-radius:12px;">
  <p style="font-size:1.1rem;color:#1a1a2e;margin:0 0 8px;font-weight:bold;">あなたにマッチする求人、何件あるか知りたくないですか？</p>
  <p style="font-size:0.9rem;color:#666;margin:0 0 16px;">たった30秒・3問で診断できます（LINE登録不要）</p>
  <a href="{href}" style="display:inline-block;background:#06C755;color:white;padding:14px 32px;border-radius:30px;text-decoration:none;font-weight:bold;font-size:1rem;box-shadow:0 2px 8px rgba(6,199,85,0.3);">30秒で求人診断 →</a>
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

    if "<!-- shindan-cta -->" in html:
        return False  # already patched

    # Determine href
    if category == "area" and filename in AREA_MAP:
        href = f"/lp/job-seeker/#shindan?area={AREA_MAP[filename]}"
    else:
        href = "/lp/job-seeker/#shindan"

    cta = make_cta(href)

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
    return True


def main():
    files = collect_files()
    patched = 0
    skipped = 0
    for path, category, filename in files:
        if patch_file(path, category, filename):
            patched += 1
            print(f"  PATCHED: {path}")
        else:
            skipped += 1
            print(f"  SKIPPED: {path}")
    print(f"\nDone. Patched: {patched}, Skipped (already had CTA): {skipped}, Total: {len(files)}")


if __name__ == "__main__":
    main()
