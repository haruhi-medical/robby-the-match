# P0-1 QC Verdict: CONDITIONAL PASS

**Date:** 2026-04-06
**Auditor:** QC Supervisor (Claude)

## Verification Results

### 1. EXTERNAL_JOBS area-location check

| Area | Result | Detail |
|------|--------|--------|
| 大磯 | PASS | 1 job remaining: loc:"神奈川県足柄上郡中井町" -- legitimate |
| 大和 | FAIL (1 remaining issue) | 5 of 6 jobs OK. Line 358 "サニーライフ東大和" has loc:"" but station is "多摩モノレール 上北台" (東京都東大和市). This is a Tokyo facility misplaced in the Kanagawa "大和" area. Escaped the fix because loc was empty. |
| 南足柄・開成 | PASS | 6 jobs remaining, all loc values are 神奈川県 or empty with Kanagawa stations |

### 2. All remaining jobs in Kanagawa areas have legitimate loc values

Automated scan of all Kanagawa area entries: no non-Kanagawa `loc:` values found (only empty or 神奈川県-prefixed). However, the empty-loc case for サニーライフ東大和 shows the fix only caught jobs with explicit non-Kanagawa loc strings, not jobs with empty loc that are identifiable as out-of-area by station/name.

### 3. Syntax check

```
node --check api/worker.js
```
**Result: PASS** -- no syntax errors.

### 4. hellowork_rank.py classify_area logic

**Result: PASS** -- all three fixes verified:

- **None handling (line 319):** `(job.get("work_address") or "")` correctly converts None to empty string
- **Kanto validation (lines 323-325):** Rejects addresses not containing any of 東京都/神奈川県/千葉県/埼玉県
- **Length-based sort (lines 327-331):** `sort(key=lambda x: -len(x[0]))` ensures "東大和市" (4 chars) matches before "大和市" (3 chars), preventing the original misclassification

## Remaining Issue (P0-1b)

**Line 358 in worker.js:** "サニーライフ東大和" (station: 多摩モノレール 上北台) is a Tokyo facility that should be removed from the "大和" area or moved to "多摩". It has `loc:""` which masked the mismatch.

## Action Required

Remove line 358 from EXTERNAL_JOBS "大和" area to fully resolve P0-1. After that, this fix is PASS.
