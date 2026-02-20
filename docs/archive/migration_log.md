# ファイル移動ログ — 2026-02-20

## 概要
ROBBY THE MATCH関連ファイルの散在を解消するため、
~/robby_content/、~/Desktop/claude/、~/Desktop/ 直下の関連ファイルを
~/robby-the-match/docs/archive/ に統合し、統合元を ~/Desktop/_archive_20260220/ に退避した。

## 移動元 → 統合先（~/robby-the-match/docs/archive/）

### ~/robby_content/ から
| 元ファイル | 統合先 |
|-----------|--------|
| add_text_overlay.py | docs/archive/add_text_overlay.py |
| add_text_overlay_v2.py | docs/archive/add_text_overlay_v2.py |
| add_text_overlay_v3.py | docs/archive/add_text_overlay_v3.py |
| generate_backgrounds.py | docs/archive/generate_backgrounds.py |
| download_font.py | docs/archive/download_font.py |
| workflow_automation.py | docs/archive/workflow_automation.py |
| test_cloudflare_image.py | docs/archive/test_cloudflare_image_rc.py |
| test_cloudflare_image_fixed.py | docs/archive/test_cloudflare_image_fixed_rc.py |
| CLOUDFLARE_SETUP.md | docs/archive/CLOUDFLARE_SETUP.md |
| ENVIRONMENT_STATUS.md | docs/archive/ENVIRONMENT_STATUS.md |
| GOOGLE_GEMINI_SETUP.md | docs/archive/GOOGLE_GEMINI_SETUP.md |
| README_IMAGE_GENERATION.md | docs/archive/README_IMAGE_GENERATION.md |

### ~/Desktop/ 直下から
| 元ファイル | 統合先 |
|-----------|--------|
| CLAUDE_v8.0 (2).md | docs/archive/CLAUDE_v8.0_copy.md |
| SETUP_PROMPT (1).md | docs/archive/SETUP_PROMPT_copy.md |

### ~/Desktop/claude/ から
| 元ファイル | 統合先 |
|-----------|--------|
| MANUAL.md | docs/archive/MANUAL_v2.0.md |
| config/agent_config.json | docs/archive/agent_config.json |
| config/content_strategy.json | docs/archive/content_strategy.json |
| scripts/CLOUDFLARE_IMPROVEMENTS.md | docs/archive/CLOUDFLARE_IMPROVEMENTS.md |
| scripts/generate_images_cloudflare.py | docs/archive/generate_images_cloudflare.py |
| scripts/generate_images_gemini.py | docs/archive/generate_images_gemini.py |
| scripts/test_cloudflare.py | docs/archive/test_cloudflare_dc.py |
| scripts/test_imagen.py | docs/archive/test_imagen.py |

## 統合元の退避先

統合元ディレクトリは削除せず ~/Desktop/_archive_20260220/ にまとめて移動した。

| 元の場所 | 退避先 |
|---------|--------|
| ~/robby_content/ | ~/Desktop/_archive_20260220/robby_content/ |
| ~/Desktop/claude/ | ~/Desktop/_archive_20260220/claude/ |
| ~/Desktop/CLAUDE_v8.0 (2).md | ~/Desktop/_archive_20260220/ |
| ~/Desktop/SETUP_PROMPT (1).md | ~/Desktop/_archive_20260220/ |

## 統合しなかったもの

- ~/Desktop/claudecodeproject1/project1/ — Team4で既にrobby-the-matchに統合済み。再コピー不要。
- ~/robby_content/post_001/ — 画像バイナリ（約15MB）。docs/archiveに入れると肥大化するため退避先に保持。
- ~/robby_content/fonts/ — フォントファイル（約4MB）。退避先に保持。
- ~/robby_content/test_images/ — テスト用画像。退避先に保持。

## その他の処置
- .DS_Store: robby-the-match/ および _archive_20260220/ 内で全削除
- 空ディレクトリ: robby-the-match/ 内の空ディレクトリを削除（.git配下除外）
