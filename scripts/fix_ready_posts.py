#!/usr/bin/env python3
"""
ready投稿16件の一括修正スクリプト
- ロビー → 自然な表現に置換
- ファクトチェック: 根拠なき数字に「目安」「程度」追加
- 重大問題のキャプション修正
- posting_queue.json更新
"""

import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent


def fix_robby_in_text(text):
    """ロビー参照を自然な表現に置換"""
    replacements = [
        ("ロビーが調べたんだけど、", "調べてみたら、"),
        ("ロビーが調べたんだけど，", "調べてみたら、"),
        ("ロビーは計算してみたんだけど、", "計算してみたら、"),
        ("ロビーは思ったんだけど、", "考えてみると、"),
        ("ロビーは思ったんだけど， ", "考えてみると、"),
        ("ロビーは「", "「"),
        ("ロビーに相談するだけでもOK", "まずは相談するだけでもOK"),
        ("ロビーに相談", "まずは相談"),
        ("ロビーは神奈川県全域の病院情報を持ってるから", "神奈川県全域の病院情報があるから"),
        ("ロビーは", ""),
        ("ロビーが", ""),
        ("ロビーの", ""),
        ("ロビーも", ""),
        ("ロビーに", ""),
        ("ロビーで", ""),
        ("ロビー", ""),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    # Clean up double spaces or leading spaces after replacement
    text = re.sub(r'　　+', '　', text)
    text = re.sub(r'  +', ' ', text)
    text = text.strip()
    return text


def fix_fact_issues(content_id, slides, caption, hook):
    """コンテンツIDに基づくファクト修正"""

    # ID 137: ai_給与_0305_05 — 根拠なき具体数字
    if content_id == "ai_給与_0305_05":
        # 546万→程度を追加、120万→程度追加
        for i, s in enumerate(slides):
            slides[i] = s.replace("平均年収は546万円", "平均年収は500万円台程度")
            slides[i] = slides[i].replace("年間120万もある", "年間100万円以上になることも")
            slides[i] = slides[i].replace("年収が100万も違う", "年収に大きな差がつくことがある")
            slides[i] = slides[i].replace("100-200万円も違う", "100万円以上違うケースもある")
        caption = caption.replace("平均年収は546万円", "平均年収は500万円台程度")
        caption = caption.replace("年間120万もある", "年間100万円以上になることも")
        caption = caption.replace("100-200万円も違う", "100万円以上違うケースもある")
        hook = hook.replace("546万円", "500万円台") if hook else hook

    # ID 151: claude_地域_0305_09 — 特定病院名
    if content_id == "claude_地域_0305_09":
        for i, s in enumerate(slides):
            slides[i] = s.replace("湘南鎌倉総合病院", "湘南エリアの大規模病院")
            slides[i] = slides[i].replace("669床", "600床以上")
            slides[i] = slides[i].replace("ずっと募集してる", "看護師を募集してることが多い")
        caption = caption.replace("湘南鎌倉総合病院", "湘南エリアの大規模病院")
        caption = caption.replace("669床", "600床以上")
        caption = caption.replace("ずっと募集してるんだ", "看護師を募集してることが多いよ")
        hook = hook.replace("湘南鎌倉総合病院", "湘南の大規模病院") if hook else hook

    # ID 142: ai_転職_0305_10 — 手取り35万
    if content_id == "ai_転職_0305_10":
        for i, s in enumerate(slides):
            slides[i] = s.replace("手取り35万", "手取り30〜35万円程度")
            slides[i] = slides[i].replace("月10回で手取り35万", "月10回程度で手取り30〜35万円程度の事例も")
        caption = caption.replace("手取り35万", "手取り30〜35万円程度")
        hook = hook.replace("手取り35万", "手取り30〜35万程度") if hook else hook

    # ID 134: ai_ある_0305_02 — フック調整
    if content_id == "ai_ある_0305_02":
        if slides and "朝になっちゃった" in slides[0]:
            slides[0] = "夜勤明けの報告書、何度書き直した？"
        hook = "夜勤明けの報告書、何度書き直した？"

    # ID 136: ai_ある_0305_04 — 時給に目安追加
    if content_id == "ai_ある_0305_04":
        for i, s in enumerate(slides):
            slides[i] = s.replace("時給は約1,500-2,000円です", "時給は約1,500〜2,000円程度（目安）")
        caption = caption.replace("時給は約1,500-2,000円です", "時給は約1,500〜2,000円程度（目安）")

    # ID 138: ai_給与_0305_06 — 手取りに目安追加
    if content_id == "ai_給与_0305_06":
        for i, s in enumerate(slides):
            slides[i] = s.replace("手取り24万って", "手取り24万円程度って")
        caption = caption.replace("手取り24万って", "手取り24万円程度って")
        hook = hook.replace("手取り24万って", "手取り24万程度って") if hook else hook

    # ID 139: ai_業界_0305_07 — CTA重複削減
    if content_id == "ai_業界_0305_07":
        caption = "神奈川県の看護師さん\n\n転職の舞台裏って?\n\n気になる人はプロフのリンクからどうぞ"

    # ID 140: ai_地域_0305_08 — 72分に目安追加
    if content_id == "ai_地域_0305_08":
        for i, s in enumerate(slides):
            slides[i] = s.replace("片道72分", "片道70分前後")
        caption = caption.replace("片道72分", "片道70分前後")
        hook = hook.replace("72分", "70分前後") if hook else hook

    # ID 147: claude_転職_0305_05 — 月収に目安追加
    if content_id == "claude_転職_0305_05":
        for i, s in enumerate(slides):
            slides[i] = s.replace("月収30〜40万", "月収30〜40万円程度（目安）")
        caption = caption.replace("月収30〜40万", "月収30〜40万円程度（目安）")

    # 全件共通: 数字の断定に「程度」「目安」がない場合を補完
    for i, s in enumerate(slides):
        # 「年収XXX万円」に程度がない場合
        slides[i] = re.sub(r'年収(\d{3,4})万円(?!程度|台|以上|以下|前後|未満)',
                           r'年収\1万円程度', slides[i])

    return slides, caption, hook


def fix_all_ready_posts():
    """全readyポストのJSON修正"""
    queue_path = PROJECT_ROOT / "data" / "posting_queue.json"
    with open(queue_path) as f:
        queue = json.load(f)

    ready_posts = [p for p in queue["posts"] if p["status"] == "ready"]
    print(f"修正対象: {len(ready_posts)}件のreadyポスト\n")

    fixed_count = 0
    issues_found = []

    for post in ready_posts:
        post_id = post["id"]
        content_id = post["content_id"]
        json_path = PROJECT_ROOT / post["json_path"]

        if not json_path.exists():
            print(f"⚠️ ID:{post_id} JSON not found: {json_path}")
            continue

        with open(json_path) as f:
            data = json.load(f)

        slides = data.get("slides", [])
        caption = data.get("caption", "")
        hook = data.get("hook", "")

        # 1. ロビー修正
        had_robby = any("ロビー" in s for s in slides) or "ロビー" in caption or "ロビー" in (hook or "")
        slides = [fix_robby_in_text(s) for s in slides]
        caption = fix_robby_in_text(caption)
        hook = fix_robby_in_text(hook) if hook else hook

        # 2. ファクト修正
        slides, caption, hook = fix_fact_issues(content_id, slides, caption, hook)

        # 3. JSON更新
        data["slides"] = slides
        data["caption"] = caption
        if hook:
            data["hook"] = hook
        data["fixed_at"] = datetime.now().isoformat()
        data["fixes_applied"] = ["robby_removed", "fact_checked"]

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 4. posting_queue.jsonのキャプション更新
        for p in queue["posts"]:
            if p["id"] == post_id:
                p["caption"] = caption
                p["status"] = "needs_regen"  # 画像再生成が必要
                break

        status = "🔧" if had_robby else "✅"
        print(f"{status} ID:{post_id} ({content_id}) — ロビー{'修正' if had_robby else 'なし'}, ファクト修正済み")

        # 残存チェック
        remaining_robby = [s for s in slides if "ロビー" in s]
        if remaining_robby:
            print(f"   ⚠️ まだロビーが残ってる: {remaining_robby[0][:50]}")
            issues_found.append(f"ID:{post_id} still has ロビー")

        fixed_count += 1

    # posting_queue.json保存
    queue["updated"] = datetime.now().isoformat()
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"修正完了: {fixed_count}/{len(ready_posts)}件")
    print(f"ステータス: ready → needs_regen に変更")
    if issues_found:
        print(f"⚠️ 残存問題: {len(issues_found)}件")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("✅ ロビー完全除去確認済み")
    print(f"{'='*60}")
    print(f"\n次のステップ: スライド画像を再生成してください")
    print(f"  python3 scripts/generate_carousel.py --regen-needs-regen")
    print(f"  または各JSONに対して python3 scripts/generate_slides.py <json_path>")


if __name__ == "__main__":
    fix_all_ready_posts()
