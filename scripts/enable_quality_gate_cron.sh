#!/bin/bash
# 品質ゲートをcronに有効化するスクリプト
# 使い方: bash scripts/enable_quality_gate_cron.sh

crontab -l > /tmp/cron_qg.txt
python3 -c "
t = open('/tmp/cron_qg.txt').read()
t = t.replace(
    '# 0 14 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_quality_gate.sh',
    '0 16 * * 1-6 /bin/bash ~/robby-the-match/scripts/pdca_quality_gate.sh >> ~/robby-the-match/logs/quality_gate.log 2>&1'
)
open('/tmp/cron_qg.txt','w').write(t)
"
crontab /tmp/cron_qg.txt
echo "品質ゲートcron有効化完了:"
crontab -l | grep quality
