---
paths:
  - "scripts/**/*.py"
  - "scripts/**/*.sh"
---
# Scripts Rules

- Python: `/usr/bin/env python3` をshebangに使え
- venv依存スクリプト（tiktok系）は `.venv/bin/python3` を使え
- Slack通知: `slack_bridge.py --send` を使え（notify_slack.pyは旧式）
- .env読み込み: `python-dotenv` or `source .env` で環境変数を取得
- エラー時はSlackに通知してから終了しろ
- cron用スクリプトは `set -euo pipefail` を先頭に書け
- CLOUDFLARE_API_TOKENは権限不足 → Worker deploy時は `unset` してOAuth使え
