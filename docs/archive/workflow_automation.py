#!/usr/bin/env python3
"""
ROBBY THE MATCH - ワークフロー自動化スクリプト
トピック生成 → 台本生成 → 画像プロンプト生成 → キャプション生成 → JSON保存
オプション: 背景画像生成 → テキスト合成
"""
import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess

# 環境変数チェック
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# プロジェクトディレクトリ
PROJECT_DIR = Path("/Users/robby2/robby_content")
MANUAL_PATH = Path("/Users/robby2/Desktop/claude/MANUAL.md")

# フックのテンプレートストック（MANUAL.mdより）
HOOK_TEMPLATES = {
    "転職・キャリア": [
        "転職エージェントに年収交渉ムリって言われたから、AIに相場出させたら担当が焦った",
        "彼氏に看護師辞めたいって言ったら反対されたから、AIで転職シミュレーション見せたら黙った",
        "先輩に3年は辞めるなって言われたから、AIにキャリア分析させたらまさかの結果",
        "お母さんに転職反対されたから、AIで年収比較見せたら態度変わった",
        "友達に夜勤やめたいって言ったら甘えって言われたから、AIに健康リスク出させたら泣いてた",
    ],
    "業務・現場": [
        "看護師の申し送りをAIに書かせたら師長が黙った",
        "看護記録をAIに要約させたら先輩より上手かった",
        "夜勤のスケジュールをAIに最適化させたら師長が怒った理由がヤバい",
        "患者さんの退院指導をAIに作らせたら主治医が驚いた",
        "インシデントレポートをAIに書かせたら完璧すぎて逆に怒られた",
    ],
    "ライフスタイル": [
        "夜勤明けの顔をAIで復元したらこうなった",
        "看護師の1日をAIに再現させたらリアルすぎて泣ける",
        "ナースのカバンの中身をAIに採点させたら辛辣すぎた",
        "看護師の手荒れをAIに見せたら対策リスト出てきたけどツッコミどころ満載",
        "看護師あるあるをAIに説明させたら的確すぎて笑った",
    ],
    "給与・待遇": [
        "看護師5年目の給料をAIに診断させたら衝撃の判定",
        "夜勤手当の相場をAIに全国調査させたらうちの病院ヤバかった",
        "AIにうちの病院の離職率を予測させたらリアルすぎた",
        "退職金をAIに計算させたら転職した方が得って出た",
    ],
}

# ハッシュタグストック
HASHTAGS = [
    "#看護師あるある",
    "#ナースあるある",
    "#看護師転職",
    "#夜勤あるある",
    "#看護師の日常",
    "#病棟あるある",
    "#看護師辞めたい",
    "#ナースの本音",
    "#AI看護師",
    "#看護師さんと繋がりたい",
]

# ベース画像プロンプト
BASE_IMAGE_PROMPT = """日本の病院の一般病棟。明るい照明。白い壁。ナースステーション前の廊下から撮影したような構図。奥にナースステーションのカウンター、電子カルテのPC画面が2台。壁に掲示板、シフト表。右手にワゴン。リアルなスマホ写真風の画質。やや暖かい照明。縦向き。アニメ調やイラスト調にしない。実写風。"""


class WorkflowAutomation:
    def __init__(self, post_number: str, theme: str = None, use_local_llm: bool = False):
        self.post_number = post_number
        self.theme = theme
        self.use_local_llm = use_local_llm
        self.post_dir = PROJECT_DIR / f"post_{post_number}"
        self.post_dir.mkdir(parents=True, exist_ok=True)

        # Claude APIキーチェック（ローカルLLMを使用しない場合）
        if not use_local_llm and not ANTHROPIC_API_KEY:
            print("⚠️  警告: ANTHROPIC_API_KEYが設定されていません")
            print("   環境変数を設定するか、--local-llmオプションを使用してください")

    def generate_topic(self) -> dict:
        """トピック生成"""
        print("\n" + "=" * 60)
        print("STEP 1: トピック生成")
        print("=" * 60)

        if self.theme:
            # テーマが指定されている場合はテンプレートから選択
            print(f"指定テーマ: {self.theme}")

            # カテゴリ検索
            for category, templates in HOOK_TEMPLATES.items():
                for template in templates:
                    if self.theme.lower() in template.lower():
                        topic = {
                            "category": category,
                            "hook": template,
                            "target": "看護師（5-10年目、転職検討中）",
                        }
                        print(f"✅ トピック選定: {template}")
                        return topic

            # 完全一致する場合
            for category, templates in HOOK_TEMPLATES.items():
                if self.theme in templates:
                    topic = {
                        "category": category,
                        "hook": self.theme,
                        "target": "看護師（5-10年目、転職検討中）",
                    }
                    print(f"✅ トピック選定: {self.theme}")
                    return topic

            print(f"⚠️  テーマ '{self.theme}' がテンプレートに見つかりません")
            print("   デフォルトトピックを使用します")

        # デフォルト: 転職・キャリア系の最初のテンプレート
        default_topic = {
            "category": "転職・キャリア",
            "hook": HOOK_TEMPLATES["転職・キャリア"][0],
            "target": "看護師（5-10年目、転職検討中）",
        }
        print(f"✅ デフォルトトピック: {default_topic['hook']}")
        return default_topic

    def generate_script(self, topic: dict) -> list:
        """台本生成（6枚構成のスライド）"""
        print("\n" + "=" * 60)
        print("STEP 2: 台本生成（6枚構成）")
        print("=" * 60)

        hook = topic["hook"]

        # 既存の例をベースに台本を生成（簡易版）
        # 実際の運用ではClaude APIまたはローカルLLMを使用

        if self.use_local_llm:
            print("⚠️  ローカルLLM未実装: サンプル台本を使用します")
        elif not ANTHROPIC_API_KEY:
            print("⚠️  Claude API未設定: サンプル台本を使用します")

        # サンプル台本（投稿#001をベースに）
        slides = [
            {
                "slide_number": 1,
                "role": "フック",
                "text_overlay": hook,
            },
            {
                "slide_number": 2,
                "role": "状況説明",
                "text_overlay": "看護師5年目、夜勤月8回\n年収420万で転職相談したら\n\n「今の相場だと\nこれが限界です」\nって即答された",
            },
            {
                "slide_number": 3,
                "role": "AIにやらせた",
                "text_overlay": "試しにAIに聞いてみた\n\n「神奈川西部、看護師5年目\n夜勤月8回の\n年収相場は?」",
            },
            {
                "slide_number": 4,
                "role": "結果（意外性）",
                "text_overlay": "AI回答:\n✓ 平均年収: 480-520万円\n✓ あなたは▲60-100万円低い\n✓ 交渉余地: 十分あり\n✓ 夜勤手当相場: 1.5万円/回",
            },
            {
                "slide_number": 5,
                "role": "オチ・反応",
                "text_overlay": "この画面を担当に見せたら\n\n「...ちょっと病院に\n再確認してみます」\n\nえ、最初から\nやってくれよ",
            },
            {
                "slide_number": 6,
                "role": "CTA",
                "text_overlay": "年収で損してる看護師\nめちゃくちゃ多い\n\n気になった人は\nプロフのリンクから\n相談できるよ",
            },
        ]

        print("✅ 台本生成完了（6枚構成）")
        for slide in slides:
            print(f"  - スライド{slide['slide_number']}: {slide['role']}")

        return slides

    def generate_image_prompts(self, slides: list) -> list:
        """画像プロンプト生成"""
        print("\n" + "=" * 60)
        print("STEP 3: 画像プロンプト生成")
        print("=" * 60)

        for slide in slides:
            text_overlay = slide["text_overlay"]
            slide_num = slide["slide_number"]

            # テキストオーバーレイ用のスタイル設定
            text_style = {
                "font": "太字ゴシック体",
                "color": "白（強調部分は黄色）",
                "size": "画面幅の1/8以上",
                "position": "中央〜やや下",
                "background": "半透明の黒帯",
            }

            # 画像プロンプト生成
            if slide_num == 3:
                # AIに聞いてみたシーン: スマホ画面を表示
                additional_prompt = "\n\n画面中央にスマホを持っている手のシルエット（ぼかし）。スマホ画面には明るい白い背景にチャットUIが表示されている様子が見える。"
            elif slide_num == 4:
                # AI回答シーン: 結果を表示
                additional_prompt = "\n\n画面中央に大きく半透明の黒い帯があり、その上に白い太字ゴシック体でAI回答が表示されている。チェックマーク（✓）と数字は黄色で強調。箇条書きで整理されたレイアウト。"
            else:
                additional_prompt = ""

            # ベースプロンプト + 追加プロンプト + テキストオーバーレイ
            image_prompt = f"{BASE_IMAGE_PROMPT}{additional_prompt}\n\n画面中央に半透明の黒い帯があり、その上に白い太字ゴシック体で日本語テキスト「{text_overlay}」が表示されている。テキストは画面幅の1/8以上の大きさで、スマホで読みやすいサイズ。"

            # スライドに追加
            slide["image_prompt"] = image_prompt.strip()
            slide["text_style"] = text_style

        print("✅ 画像プロンプト生成完了")
        return slides

    def generate_caption(self, topic: dict, slides: list) -> dict:
        """キャプション生成"""
        print("\n" + "=" * 60)
        print("STEP 4: キャプション生成")
        print("=" * 60)

        hook = topic["hook"]

        # キャプション構成
        caption_lines = [
            # 1行目: フックの拡張版
            hook,
            "",
            # 2-4行目: 看護師あるあるの共感ポイント
            "エージェントに即答で無理って言われたけど",
            "AIに聞いたら相場より60万以上低かった…",
            "",
            # 最終行: CTA
            "気になった人はプロフから覗いてみて",
        ]

        caption_text = "\n".join(caption_lines)

        # ハッシュタグ選択（5個以内）
        selected_hashtags = HASHTAGS[:5]
        hashtags_text = " ".join(selected_hashtags)

        # 最終キャプション
        full_caption = f"{caption_text}\n\n{hashtags_text}"

        caption = {
            "caption": caption_text,
            "hashtags": selected_hashtags,
            "full_caption": full_caption,
            "length": len(caption_text),
        }

        print(f"✅ キャプション生成完了（{caption['length']}文字）")
        print(f"   ハッシュタグ: {len(selected_hashtags)}個")

        return caption

    def save_json(self, topic: dict, slides: list, caption: dict):
        """JSONファイルに保存"""
        print("\n" + "=" * 60)
        print("STEP 5: JSONファイル保存")
        print("=" * 60)

        # データ構造
        data = {
            "post_id": self.post_number,
            "topic": topic["hook"],
            "category": topic["category"],
            "created_at": datetime.now().isoformat(),
            "format": {
                "size": "1024x1536",
                "orientation": "vertical",
                "format": "PNG",
            },
            "slides": slides,
            "caption": caption,
        }

        # slide_prompts.json を保存
        slide_prompts_file = self.post_dir / "slide_prompts.json"
        with open(slide_prompts_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ 保存完了: {slide_prompts_file}")

        # caption.txt を保存
        caption_file = self.post_dir / "caption.txt"
        with open(caption_file, "w", encoding="utf-8") as f:
            f.write(caption["full_caption"])

        print(f"✅ 保存完了: {caption_file}")

        return data

    def generate_backgrounds(self) -> bool:
        """背景画像生成の呼び出し（オプション）"""
        print("\n" + "=" * 60)
        print("STEP 6 (オプション): 背景画像生成")
        print("=" * 60)

        # Cloudflare API設定チェック
        if not os.environ.get("CLOUDFLARE_API_TOKEN") or not os.environ.get("CLOUDFLARE_ACCOUNT_ID"):
            print("⚠️  Cloudflare API未設定: スキップします")
            print("   背景画像生成をスキップするには --skip-images を使用してください")
            return False

        # generate_backgrounds.py を実行
        script_path = PROJECT_DIR / "generate_backgrounds.py"
        if not script_path.exists():
            print(f"❌ エラー: {script_path} が見つかりません")
            return False

        print("背景画像生成スクリプトを実行中...")
        try:
            # post番号に応じてスクリプトを修正する必要がある
            # ここでは簡略化のため、post_001固定のスクリプトをそのまま実行
            result = subprocess.run(
                ["python3", str(script_path)],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ 背景画像生成完了")
                print(result.stdout)
                return True
            else:
                print(f"❌ 背景画像生成エラー:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ 例外発生: {e}")
            return False

    def add_text_overlay(self) -> bool:
        """テキスト合成の呼び出し（オプション）"""
        print("\n" + "=" * 60)
        print("STEP 7 (オプション): テキスト合成")
        print("=" * 60)

        # add_text_overlay_v3.py を実行
        script_path = PROJECT_DIR / "add_text_overlay_v3.py"
        if not script_path.exists():
            print(f"❌ エラー: {script_path} が見つかりません")
            return False

        # 背景画像の存在チェック
        backgrounds_dir = self.post_dir / "backgrounds"
        if not backgrounds_dir.exists() or not list(backgrounds_dir.glob("*.png")):
            print("⚠️  背景画像が見つかりません: スキップします")
            return False

        print("テキスト合成スクリプトを実行中...")
        try:
            # post番号に応じてスクリプトを修正する必要がある
            result = subprocess.run(
                ["python3", str(script_path)],
                cwd=PROJECT_DIR,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ テキスト合成完了")
                print(result.stdout)
                return True
            else:
                print(f"❌ テキスト合成エラー:")
                print(result.stderr)
                return False
        except Exception as e:
            print(f"❌ 例外発生: {e}")
            return False

    def run(self, generate_images: bool = False, add_text: bool = False):
        """ワークフロー全体を実行"""
        print("\n" + "=" * 60)
        print(f"🤖 ROBBY THE MATCH - ワークフロー自動化")
        print("=" * 60)
        print(f"投稿番号: {self.post_number}")
        print(f"保存先: {self.post_dir}")
        print()

        # STEP 1: トピック生成
        topic = self.generate_topic()

        # STEP 2: 台本生成
        slides = self.generate_script(topic)

        # STEP 3: 画像プロンプト生成
        slides = self.generate_image_prompts(slides)

        # STEP 4: キャプション生成
        caption = self.generate_caption(topic, slides)

        # STEP 5: JSON保存
        data = self.save_json(topic, slides, caption)

        # オプション: 背景画像生成
        if generate_images:
            self.generate_backgrounds()

        # オプション: テキスト合成
        if add_text and generate_images:
            self.add_text_overlay()

        print("\n" + "=" * 60)
        print("✅ ワークフロー完了！")
        print("=" * 60)
        print(f"📁 出力ディレクトリ: {self.post_dir}")
        print(f"📄 台本・プロンプト: {self.post_dir / 'slide_prompts.json'}")
        print(f"📝 キャプション: {self.post_dir / 'caption.txt'}")

        if generate_images:
            print(f"🖼️  背景画像: {self.post_dir / 'backgrounds'}/")
            if add_text:
                print(f"✨ 最終画像: {self.post_dir / 'final_slides_v3'}/")

        print("\n次のステップ:")
        print("1. 生成されたJSONファイルを確認")
        if not generate_images:
            print("2. 背景画像を生成（python3 generate_backgrounds.py）")
            print("3. テキストを合成（python3 add_text_overlay_v3.py）")
        print("4. TikTok/Instagramに投稿（Postiz経由または手動）")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="ROBBY THE MATCH - ワークフロー自動化スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使い方（トピック生成〜JSON保存まで）
  python3 workflow_automation.py --post_number 002

  # テーマを指定
  python3 workflow_automation.py --post_number 002 --theme "夜勤明けの悩み"

  # 背景画像生成も実行
  python3 workflow_automation.py --post_number 002 --generate-images

  # 背景画像生成 + テキスト合成も実行
  python3 workflow_automation.py --post_number 002 --generate-images --add-text

  # ローカルLLMを使用（未実装）
  python3 workflow_automation.py --post_number 002 --local-llm
        """,
    )

    parser.add_argument(
        "--post_number",
        type=str,
        required=True,
        help="投稿番号（例: 002, 003）",
    )

    parser.add_argument(
        "--theme",
        type=str,
        help="トピックのテーマ（例: 夜勤明けの悩み、年収交渉）",
    )

    parser.add_argument(
        "--local-llm",
        action="store_true",
        help="ローカルLLMを使用（未実装）",
    )

    parser.add_argument(
        "--generate-images",
        action="store_true",
        help="背景画像生成も実行",
    )

    parser.add_argument(
        "--add-text",
        action="store_true",
        help="テキスト合成も実行（--generate-imagesと併用）",
    )

    args = parser.parse_args()

    # ワークフロー実行
    workflow = WorkflowAutomation(
        post_number=args.post_number,
        theme=args.theme,
        use_local_llm=args.local_llm,
    )

    workflow.run(
        generate_images=args.generate_images,
        add_text=args.add_text,
    )


if __name__ == "__main__":
    main()
