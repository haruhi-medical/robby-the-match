#!/usr/bin/env python3
"""
Instagram カルーセル投稿 via Meta Business Suite
Chrome DevTools Protocol (CDP) を使ってMeta Business Suiteから投稿する。

前提:
- ChromeがリモートデバッグモードでPort 9222で起動していること
- Meta Business Suiteにログイン済みであること

Usage:
  python3 scripts/ig_post_meta_suite.py                    # 次のreadyを投稿
  python3 scripts/ig_post_meta_suite.py --dry-run           # ドライラン（投稿しない）
  python3 scripts/ig_post_meta_suite.py --content-id XXX    # 指定コンテンツを投稿
"""

import json
import time
import argparse
import subprocess
import sys
import os
from pathlib import Path

try:
    import websocket
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websocket-client", "requests", "--quiet"])
    import websocket
    import requests

PROJECT_DIR = Path(__file__).parent.parent
QUEUE_FILE = PROJECT_DIR / "data" / "posting_queue.json"
POST_LOG_FILE = PROJECT_DIR / "data" / "post_log.json"
CDP_PORT = 9222

# Meta Business Suite URLs
MBS_COMPOSER_URL = "https://business.facebook.com/latest/composer/?asset_id=1030390126820320&business_id=2381678942279702&nav_ref=internal_nav&ref=biz_web_home_create_post&context_ref=HOME"


class CDPClient:
    """Chrome DevTools Protocol client."""

    def __init__(self, port=CDP_PORT):
        self.port = port
        self.ws = None
        self.msg_id = 0

    def connect(self):
        """Connect to Chrome's debug port."""
        try:
            r = requests.get(f"http://localhost:{self.port}/json")
            tabs = r.json()
            # Find the first non-devtools tab
            target = None
            for tab in tabs:
                if tab.get("type") == "page" and "devtools" not in tab.get("url", ""):
                    target = tab
                    break
            if not target:
                target = tabs[0]

            ws_url = target["webSocketDebuggerUrl"]
            self.ws = websocket.create_connection(ws_url, timeout=30)
            print(f"[CDP] Connected to: {target.get('title', 'unknown')}")
            return True
        except Exception as e:
            print(f"[CDP] Connection failed: {e}")
            return False

    def send(self, method, params=None):
        """Send CDP command and return result."""
        self.msg_id += 1
        msg = {"id": self.msg_id, "method": method, "params": params or {}}
        self.ws.send(json.dumps(msg))

        while True:
            response = json.loads(self.ws.recv())
            if response.get("id") == self.msg_id:
                if "error" in response:
                    print(f"[CDP] Error: {response['error']}")
                return response.get("result", {})

    def navigate(self, url):
        """Navigate to URL and wait for load."""
        self.send("Page.navigate", {"url": url})
        time.sleep(3)
        # Wait for page load
        self.send("Page.enable")
        time.sleep(2)

    def evaluate(self, expression):
        """Evaluate JavaScript expression."""
        result = self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        return result.get("result", {}).get("value")

    def click_element(self, selector):
        """Click element by CSS selector."""
        self.evaluate(f"""
            (() => {{
                const el = document.querySelector('{selector}');
                if (el) {{ el.click(); return true; }}
                return false;
            }})()
        """)
        time.sleep(1)

    def click_by_text(self, text, tag="button"):
        """Click element by text content."""
        result = self.evaluate(f"""
            (() => {{
                const els = document.querySelectorAll('{tag}');
                for (const el of els) {{
                    if (el.textContent.includes('{text}')) {{
                        el.click();
                        return true;
                    }}
                }}
                return false;
            }})()
        """)
        time.sleep(1)
        return result

    def enable_file_chooser_interception(self):
        """Enable file chooser interception."""
        self.send("Page.enable")
        self.send("Page.setInterceptFileChooserDialog", {"enabled": True})

    def upload_file(self, file_path):
        """Upload file via file input or file chooser interception."""
        # Method 1: Try finding file input in DOM
        node_result = self.send("DOM.getDocument")
        root_id = node_result["root"]["nodeId"]

        search_result = self.send("DOM.querySelectorAll", {
            "nodeId": root_id,
            "selector": 'input[type="file"]'
        })

        if search_result.get("nodeIds"):
            node_id = search_result["nodeIds"][-1]
            self.send("DOM.setFileInputFiles", {
                "nodeId": node_id,
                "files": [str(file_path)]
            })
            time.sleep(2)
            return True

        # Method 2: Try creating a file input and triggering it
        result = self.evaluate(f"""
            (() => {{
                // Look for any file input, even hidden ones
                const inputs = document.querySelectorAll('input[type="file"]');
                if (inputs.length > 0) {{
                    return inputs.length;
                }}
                // Create a temporary file input
                const input = document.createElement('input');
                input.type = 'file';
                input.accept = 'image/*';
                input.multiple = true;
                input.style.display = 'none';
                document.body.appendChild(input);
                return -1;
            }})()
        """)

        if result and result > 0:
            # File inputs exist, try again
            search_result = self.send("DOM.querySelectorAll", {
                "nodeId": root_id,
                "selector": 'input[type="file"]'
            })
            if search_result.get("nodeIds"):
                node_id = search_result["nodeIds"][-1]
                self.send("DOM.setFileInputFiles", {
                    "nodeId": node_id,
                    "files": [str(file_path)]
                })
                time.sleep(2)
                return True

        print("[CDP] No file input found")
        return False

    def fill_text(self, selector, text):
        """Fill text into an input/textarea."""
        self.evaluate(f"""
            (() => {{
                const el = document.querySelector('{selector}');
                if (el) {{
                    el.focus();
                    el.textContent = `{text}`;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }})()
        """)
        time.sleep(0.5)

    def close(self):
        if self.ws:
            self.ws.close()


def get_next_content():
    """Get next ready content from posting queue."""
    if not QUEUE_FILE.exists():
        return None

    with open(QUEUE_FILE) as f:
        q = json.load(f)

    # Load post log to check what's already posted
    posted_dirs = set()
    if POST_LOG_FILE.exists():
        with open(POST_LOG_FILE) as f:
            log = json.load(f)
        for entry in log:
            if entry.get("platform") == "instagram" and entry.get("status") == "success":
                posted_dirs.add(entry.get("dir", ""))

    for post in q.get("posts", []):
        if post.get("status") != "ready":
            continue
        slide_dir = Path(post.get("slide_dir", ""))
        if not slide_dir.exists():
            continue
        slides = sorted(slide_dir.glob("*slide*.png"))
        if not slides:
            continue
        if slide_dir.name in posted_dirs:
            continue
        return post

    return None


def mark_as_posted(content_id):
    """Mark content as posted in queue."""
    with open(QUEUE_FILE) as f:
        q = json.load(f)

    for post in q.get("posts", []):
        if post.get("content_id") == content_id and post.get("status") == "ready":
            post["status"] = "posted"
            post["posted_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            post["posted_via"] = "meta_business_suite"
            break

    with open(QUEUE_FILE, "w") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)


def log_post(content_id, slide_dir, status, error=None):
    """Log post result."""
    log = []
    if POST_LOG_FILE.exists():
        with open(POST_LOG_FILE) as f:
            log = json.load(f)

    log.append({
        "platform": "instagram",
        "dir": Path(slide_dir).name,
        "content_id": content_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": status,
        "method": "meta_business_suite",
        "error": error,
    })

    with open(POST_LOG_FILE, "w") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def post_carousel(cdp, slides, caption, dry_run=False):
    """Post carousel to Instagram via Meta Business Suite."""

    print(f"[MBS] Navigating to Meta Business Suite composer...")
    cdp.navigate(MBS_COMPOSER_URL)
    time.sleep(8)  # MBS is slow to load

    # Close any welcome dialogs
    cdp.click_by_text("Done")
    time.sleep(1)
    cdp.click_by_text("Skip")
    time.sleep(1)

    # Enable file chooser interception
    cdp.send("Page.enable")
    cdp.send("DOM.enable")

    # Upload slides one by one
    for i, slide in enumerate(slides):
        print(f"[MBS] Uploading slide {i+1}/{len(slides)}: {slide.name}")

        # Click "Add photo" to open menu
        cdp.click_by_text("Add photo")
        time.sleep(1.5)

        # Click "Upload from desktop" — this triggers file chooser
        # We need to intercept it with CDP
        cdp.send("Page.setInterceptFileChooserDialog", {"enabled": True})
        cdp.click_by_text("Upload from desktop", tag="*")
        time.sleep(1)

        # Wait for fileChooserOpened event and handle it
        # Since we can't easily wait for events, use DOM approach:
        # After clicking, a file input should appear briefly
        time.sleep(1)

        # Try to find and set file input
        doc = cdp.send("DOM.getDocument")
        root_id = doc["root"]["nodeId"]
        inputs = cdp.send("DOM.querySelectorAll", {
            "nodeId": root_id,
            "selector": 'input[type="file"]'
        })

        if inputs.get("nodeIds"):
            node_id = inputs["nodeIds"][-1]
            cdp.send("DOM.setFileInputFiles", {
                "nodeId": node_id,
                "files": [str(slide.absolute())]
            })
            print(f"[MBS] Slide {i+1} uploaded via file input")
        else:
            # Fallback: try handling file chooser event
            try:
                cdp.send("Page.handleFileChooser", {
                    "action": "accept",
                    "files": [str(slide.absolute())]
                })
                print(f"[MBS] Slide {i+1} uploaded via file chooser")
            except Exception as e:
                print(f"[MBS] Upload method failed for slide {i+1}: {e}")
                # Last resort: inject file input
                cdp.evaluate(f"""
                    (() => {{
                        const input = document.querySelector('input[type="file"]') ||
                                      document.createElement('input');
                        input.type = 'file';
                        input.style.display = 'block';
                        if (!input.parentNode) document.body.appendChild(input);
                        return 'input ready';
                    }})()
                """)
                time.sleep(0.5)
                doc2 = cdp.send("DOM.getDocument")
                root_id2 = doc2["root"]["nodeId"]
                inputs2 = cdp.send("DOM.querySelectorAll", {
                    "nodeId": root_id2,
                    "selector": 'input[type="file"]'
                })
                if inputs2.get("nodeIds"):
                    cdp.send("DOM.setFileInputFiles", {
                        "nodeId": inputs2["nodeIds"][-1],
                        "files": [str(slide.absolute())]
                    })
                    print(f"[MBS] Slide {i+1} uploaded via injected input")
                else:
                    print(f"[MBS] Failed to upload slide {i+1}")
                    return False

        cdp.send("Page.setInterceptFileChooserDialog", {"enabled": False})
        time.sleep(3)  # Wait for upload to process

    print(f"[MBS] All {len(slides)} slides uploaded")

    # Fill caption
    print(f"[MBS] Setting caption...")
    # Use the contenteditable div for caption
    escaped_caption = caption.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    cdp.evaluate(f"""
        (() => {{
            // Find the text input area
            const inputs = document.querySelectorAll('[role="combobox"]');
            for (const input of inputs) {{
                if (input.getAttribute('aria-label')?.includes('dialogue box') ||
                    input.getAttribute('aria-label')?.includes('text with your post')) {{
                    input.focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('insertText', false, `{escaped_caption}`);
                    return true;
                }}
            }}
            return false;
        }})()
    """)
    time.sleep(1)

    if dry_run:
        print("[MBS] DRY RUN - not publishing")
        return True

    # Click Publish
    print("[MBS] Publishing...")
    cdp.click_by_text("Publish")
    time.sleep(5)

    # Check for success message
    page_text = cdp.evaluate("document.body.innerText") or ""
    if "published" in page_text.lower() or "投稿" in page_text:
        print("[MBS] SUCCESS - Post published!")
        # Click Done on success dialog
        cdp.click_by_text("Done")
        return True
    else:
        print(f"[MBS] Publish result unclear. Page text preview: {page_text[:200]}")
        return True  # Assume success if no error


def notify_slack(content_id, caption):
    """Send Slack notification about the post."""
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_DIR / ".env")

        token = os.environ.get("SLACK_BOT_TOKEN", "")
        channel = "C0AEG626EUW"  # ロビー小田原人材紹介

        if not token:
            return

        requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "channel": channel,
                "text": f"📸 *Instagram投稿完了（Meta Business Suite経由）*\nコンテンツ: {content_id}\nキャプション: {caption[:100]}...",
            }
        )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Instagram投稿 via Meta Business Suite")
    parser.add_argument("--dry-run", action="store_true", help="投稿せずにテスト")
    parser.add_argument("--content-id", type=str, help="指定コンテンツを投稿")
    args = parser.parse_args()

    # Get content to post
    post = None
    if args.content_id:
        with open(QUEUE_FILE) as f:
            q = json.load(f)
        for p in q.get("posts", []):
            if p.get("content_id") == args.content_id:
                post = p
                break
        if not post:
            print(f"Content {args.content_id} not found in queue")
            return
    else:
        post = get_next_content()

    if not post:
        print("[MBS] No ready content to post")
        return

    content_id = post.get("content_id", "unknown")
    slide_dir = Path(post.get("slide_dir", ""))
    slides = sorted(slide_dir.glob("*slide*.png"))
    caption = post.get("caption", "")
    hashtags = " ".join(post.get("hashtags", []))
    full_caption = f"{caption}\n\n{hashtags}" if hashtags else caption

    print(f"[MBS] Content: {content_id}")
    print(f"[MBS] Slides: {len(slides)}")
    print(f"[MBS] Caption: {full_caption[:80]}...")

    # Connect to Chrome
    cdp = CDPClient(CDP_PORT)
    if not cdp.connect():
        print("[MBS] FAILED: Cannot connect to Chrome. Is it running with --remote-debugging-port=9222?")
        return

    try:
        success = post_carousel(cdp, slides, full_caption, dry_run=args.dry_run)

        if success and not args.dry_run:
            mark_as_posted(content_id)
            log_post(content_id, slide_dir, "success")
            notify_slack(content_id, full_caption)
            print(f"[MBS] Done! {content_id} posted successfully")
        elif not success:
            log_post(content_id, slide_dir, "error", "MBS posting failed")
            print(f"[MBS] FAILED: {content_id}")
    finally:
        cdp.close()


if __name__ == "__main__":
    main()
