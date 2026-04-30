# crontab 編集履歴

> Mac Mini M4 ローカルの crontab 編集記録。
> ロビー（Claude Code）が編集した場合は必ずここに追記すること。

---

## 2026-04-30 — daily_snapshot_merge.py 追加

**目的**: AUDIT-F1-DEEPDIVE-REPORT.md F1-5 で「daily_snapshot.json が4/16以降取得停止」と判明。スクリプトは存在するが crontab 未登録だった。

**変更**: 末尾に追加
```cron
# daily snapshot merge (2026-04-30 追加 by Patch 6 (D))
15 8 * * * cd ~/robby-the-match && /usr/bin/python3 scripts/daily_snapshot_merge.py >> logs/daily_snapshot_$(date +\%Y-\%m-\%d).log 2>&1
```

- **発火時刻**: 毎日 08:15 JST（daily_ads_report.py 08:10 の5分後）
- **出力先**: `logs/daily_snapshot_YYYY-MM-DD.log`
- **データ統合先**: `data/daily_snapshot.json`
- **バックアップ**: `/tmp/crontab_backup_20260430_132202.txt`

**実施者**: ロビー（Claude Code）
**承認**: 平島禎之（補足指示書 §2 で crontab 編集権限付与）

---

## 編集ルール（履歴開始時に確定）

1. 編集前に必ず `crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt`
2. 既存21cron（pdca_*.sh 系）を誤って削除しない
3. 追加・変更は本ファイルに必ず追記
4. 重大変更（PATH変更・削除等）は社長に事前通告
