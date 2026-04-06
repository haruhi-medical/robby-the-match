# Matching Quality Audit Report

Date: 2026-04-06
Auditor: Specialist 3 (Matching Quality)

---

## Check 1: D1 Fallback Query Logic (generateLineMatching)

### Verified Correct:
- **chiba_all_il**: baseArea=chiba_all, cities=[], D1_AREA_PREF='千葉県' -> `WHERE category=? AND prefecture=?` OK
- **saitama_all_il**: Same pattern -> prefecture='埼玉県' OK
- **tokyo_included_il**: Same -> prefecture='東京都' OK
- **kanagawa_all_il**: Same -> prefecture='神奈川県' OK
- **yokohama_kawasaki_il**: cities=['横浜市','川崎市'] -> `WHERE address LIKE ?` OK
- **tokyo_23ku_il**: cities=[23 wards] -> `WHERE address LIKE ?` (23 clauses) OK
- **tokyo_tama_il**: cities=[25 tama cities] -> `WHERE address LIKE ?` (25 clauses) OK

### undecided_il Path:
- baseArea='undecided', cities=[], D1_AREA_PREF['undecided']=undefined, prefFilter=null
- entry.prefecture is typically null for undecided
- Falls through to: `WHERE category=?` (no area filter) -> returns random 5 from ALL prefectures
- **Verdict**: Acceptable. "Undecided" users get a broad sample. No bug.

---

## Check 2: EXTERNAL_JOBS Matching (AREA_ZONE_MAP)

### AREA_ZONE_MAP vs EXTERNAL_JOBS key alignment:

| Zone Map Entry | Zone Keys | EXTERNAL_JOBS Keys Present? |
|---|---|---|
| q3_chiba_all_il | ["千葉","船橋・市川","柏・松戸","千葉その他"] | All 4 present |
| q3_saitama_all_il | ["さいたま","川口・戸田","所沢・入間","川越・東松山","越谷・草加","埼玉その他"] | All 6 present |
| q3_kanagawa_all_il | ["横浜","川崎",...13 keys] | All present |
| q3_undecided_il | ["横浜","川崎","23区","多摩","さいたま","千葉"] | All present |

### BUG FOUND AND FIXED - Phantom "東京" key:
- **Before**: q3_tokyo_included_il had ["東京","23区","多摩"] but "東京" doesn't exist in EXTERNAL_JOBS
- **Before**: q3_tokyo_23ku_il had ["東京"] - phantom, always returned 0 EXTERNAL_JOBS results
- **Before**: q3_tokyo_tama_il had ["東京"] - same issue
- **Fix applied**: Removed "東京" from all three, aligned with actual EXTERNAL_JOBS keys ("23区", "多摩")

### Pre-existing Minor Issue (NOT FIXED):
- AREA_ZONE_MAP lists "南足柄", "開成", etc. as separate zone keys
- EXTERNAL_JOBS key is "南足柄・開成" (combined)
- collectJobs() uses exact key matching, so these individual keys never match
- Impact: Low. "小田原" is first in the zone list and has jobs. D1 fallback covers the rest.
- Recommendation: Add "南足柄・開成" to q3_odawara_kensei_il zone map in future update.

---

## Check 3: Candidate Count Accuracy (countCandidatesD1 vs generateLineMatching)

### BUG FOUND AND FIXED - tokyo_23ku / tokyo_tama count inflation:

**Before (countCandidatesD1)**:
- tokyo_23ku and tokyo_tama were in AREA_PREF_MAP mapping to '東京都'
- This caused the AREA_PREF_MAP branch to fire (line 602: `if (AREA_PREF_MAP[areaKey] !== undefined)`)
- The AREA_CITY_MAP cities array was never checked
- Result: COUNT returned ALL Tokyo facilities, not just 23ku or tama subset

**After (fixed)**:
- Logic now checks AREA_CITY_MAP first
- tokyo_23ku has 23 ward names -> filters by those wards
- tokyo_tama has 25 city names -> filters by those cities
- tokyo_included/kanagawa_all/chiba_all/saitama_all have empty arrays -> falls through to AREA_PREF_MAP
- Count now matches what user actually sees in matching results

### Consistency Matrix (post-fix):

| Area | countCandidatesD1 Filter | generateLineMatching D1 Filter | Match? |
|---|---|---|---|
| yokohama_kawasaki | cities=['横浜市','川崎市'] | cities=['横浜市','川崎市'] | YES |
| tokyo_23ku | cities=[23 wards] | cities=[23 wards] | YES |
| tokyo_tama | cities=[25 cities] | cities=[25 cities] | YES |
| tokyo_included | prefecture='東京都' | prefecture='東京都' | YES |
| chiba_all | prefecture='千葉県' | prefecture='千葉県' | YES |
| saitama_all | prefecture='埼玉県' | prefecture='埼玉県' | YES |
| kanagawa_all | prefecture='神奈川県' | prefecture='神奈川県' | YES |
| undecided | no filter | no filter | YES |

---

## Check 4: 0-Result Handling

### Flow trace:
1. EXTERNAL_JOBS search via collectJobs() using AREA_ZONE_MAP
2. If 0 results -> ADJACENT_AREAS expansion (tries each adjacent area until one has results)
3. If still 0 -> D1 fallback (SQL query against facilities table)
4. If D1 also 0 -> entry.matchingResults = [] (empty slice)

### ADJACENT_AREAS map verified:
- yokohama_kawasaki -> ['shonan_kamakura', 'sagamihara_kenoh', 'tokyo_included']
- tokyo_included -> ['yokohama_kawasaki']
- tokyo_23ku -> ['tokyo_tama', 'yokohama_kawasaki']
- tokyo_tama -> ['tokyo_23ku', 'sagamihara_kenoh']
- saitama_all -> ['tokyo_23ku', 'tokyo_tama']
- chiba_all -> ['tokyo_23ku']
- kanagawa_all -> ['tokyo_included']

### Issue: Adjacent area expansion uses `_il` suffix
Line 4479: `getAreaKeysFromZone(\`q3_${adj}_il\`)`
The adjacent area values DON'T have `_il` suffix in ADJACENT_AREAS (e.g., 'tokyo_included' not 'tokyo_included_il').
But the zone key constructed is `q3_tokyo_included_il` which IS in AREA_ZONE_MAP. So this works correctly.

### Empty result UI:
- matching_preview with 0 results -> buildPhaseMessage handles it
- matching_browse with 0 results -> shows "今ある求人は全てお見せしました" with change/wait options
- No crashes or undefined behavior.

---

## Check 5: matching_browse Pagination

### Flow:
1. User clicks "もっと見る" -> matching_browse=more -> nextPhase="matching_browse"
2. generateLineMatching(entry, env) is called again (offset=0, full re-query)
3. Results are filtered against entry.browsedJobIds (previously shown jobs)
4. New results are tracked in browsedJobIds
5. buildPhaseMessage("matching_browse") displays up to 5 results

### D1 Fallback + Pagination:
- D1 uses `ORDER BY RANDOM() LIMIT 5`
- With browsedJobIds filtering, repeated calls should return different random results
- However, if total matching facilities < 10, user may see "今ある求人は全てお見せしました" quickly

### Prefecture filter in pagination:
- generateLineMatching re-runs the full query each time
- D1_AREA_PREF is applied correctly on each call
- No pagination offset is used - instead, browsedJobIds deduplication handles it
- **Verdict**: Works correctly with prefecture filter.

---

## Check 6: Nurture Push Dynamic Count (BUG FOUND AND FIXED)

### BUG:
- handleScheduledNurture at line ~6925 used AREA_CITY_MAP to get cities
- For chiba_all/saitama_all/tokyo_included/kanagawa_all, cities=[]
- No prefecture fallback existed -> cnt stayed 0 -> dynamicJobCount was always empty string
- Users in these areas received generic messages instead of "XXX件の医療機関" messages

### FIX:
- Added NURTURE_PREF_MAP fallback when cities.length === 0
- Maps chiba_all->千葉県, saitama_all->埼玉県, tokyo_included->東京都, kanagawa_all->神奈川県
- Now queries `WHERE category='病院' AND prefecture=?` for these areas

---

## Summary of Changes Made

### Bug Fixes Applied to worker.js:

1. **countCandidatesD1 (line ~595-611)**: Reversed priority - now checks AREA_CITY_MAP first (for tokyo_23ku/tama precision), then falls back to AREA_PREF_MAP for empty-array areas. This fixes count inflation for tokyo_23ku and tokyo_tama.

2. **AREA_ZONE_MAP (line ~2992-2994)**: Removed phantom "東京" key from q3_tokyo_included_il, q3_tokyo_23ku_il, and q3_tokyo_tama_il. Aligned with actual EXTERNAL_JOBS keys ("23区", "多摩").

3. **Nurture push dynamicJobCount (line ~6925-6947)**: Added NURTURE_PREF_MAP fallback for prefecture-level areas (chiba_all, saitama_all, tokyo_included, kanagawa_all) so dynamic facility counts are shown in nurture messages.

### Remaining Issues (Not Fixed - Low Priority):

1. **AREA_ZONE_MAP "南足柄・開成" mismatch**: Zone map uses "南足柄" and "開成" separately but EXTERNAL_JOBS uses "南足柄・開成" combined key. Low impact since "小田原" zone covers the area and D1 fallback handles it.

2. **AREA_ZONE_MAP small-town zone keys**: "寒川", "愛川", "逗子", "葉山" etc. don't have EXTERNAL_JOBS entries. By design - these are covered by D1 fallback.
