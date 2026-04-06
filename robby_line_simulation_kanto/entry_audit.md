# Entry Route & Re-entry Audit — Specialist 6

**Date:** 2026-04-06
**File:** `/Users/robby2/robby-the-match/api/worker.js`

---

## Area 1: All Entry Routes

### Route 1: Direct Follow (no session) — Line 5489-5590

**Trigger:** `event.type === "follow"` with no LIFF session found.

**Welcome message:**
```
はじめまして！
ナースロビーのロビーです🤖

{jobCount}件の医療機関の中から
あなたにぴったりの職場を見つけま���。

完全無料・電話なし・LINE完結。

まずは求人を探してみませんか？
```

**Quick Reply options:** 求人を探す / 年収を知りたい / まず相談したい / まだ見てるだけ

**Phase set to:** `welcome` (entry created with `welcomeSource = 'none'`)

**Leads to il_area?** YES — via `welcome=see_jobs` postback -> `il_area` (line 5173)

**Status:** OK. Job count is dynamically fetched from D1. Default fallback is 123.

---

### Route 2: Meta Ad (source=meta_ad) — buildSessionWelcome line 3129-3145

**Trigger:** `/api/line-start?source=meta_ad&intent=see_jobs` -> 302 redirect to LINE with dm_text=UUID -> text message handler detects UUID -> calls `buildSessionWelcome`.

**Welcome message:**
```
広告から来てくれたんですね！
ナースロビーです🏥

看護師さん専門の転職サポートです。
完全無料・電話なし・LINE完結。
いつでもブロックOKです。

さっそく求人を探してみませんか？
```

**Quick Reply:** 求人を探す / 年収を知りたい / まず相談したい

**Phase:** `welcome`

**Leads to il_area?** YES — via `welcome=see_jobs`

**Status:** OK. The "いつでもブロックOKです" is good for ad-sourced users (low trust).

---

### Route 3: LP Hero/Sticky/Bottom — buildSessionWelcome line 3147-3180

**Trigger:** `/api/line-start?source=hero|sticky|bottom&intent=see_jobs|consult`

**Two variants:**
- `intent=consult`: "転職のご相談ですね..." with さっそく始める / まず相談したい
- `intent=see_jobs` (default): "求人をお探しなんですね..." with さっそく始める / ちょっと相談したい / まだ見てるだけ

**Phase:** `welcome`

**Leads to il_area?** YES

**Status:** OK

---

### Route 4: Blog/Guide page — buildSessionWelcome line 3112-3127

**Trigger:** `/api/line-start?source=blog`

**Welcome:**
```
記事を読んでくださって
ありがとうございます📖

よかったら、あなたに合う
神奈川の求人も見てみませんか？
3つだけ質問させてください。
```

**Quick Reply:** 求人を見てみる / まだ情報収集中

**Phase:** `welcome`

**Leads to il_area?** YES

**Status:** OK

---

### Route 5: Area page — buildSessionWelcome line 3075-3093

**Trigger:** `/api/line-start?source=area_page&area={area_key}`

**Welcome:**
```
こんにちは！ナースロビーです。

{areaLabel}の看護師求人を
お探しですね。

あと2つだけ教えてください👇
```

**Quick Reply:** 日勤のみ / 夜勤ありOK / パート・非常勤 / 夜勤専従

**Phase:** `welcome`

**Leads to il_area?** NO — SKIPS il_area. Goes `area_welcome={day|twoshift|part|night}` -> sets workStyle -> `il_urgency` directly. This is correct behavior since area is already known.

**Status:** OK. Smart shortcut.

---

### Route 6: Salary Check — buildSessionWelcome line 3095-3110

**Trigger:** `/api/line-start?source=salary_check`

**Welcome:**
```
ようこそ！ナースロビーです。

年収診断からいらっしゃったんですね。
もう少し詳しい年収情報と、
あなたの条件に合う求人を
お見せできます。

3つだけ教えてくださいね。
```

**Quick Reply:** さっそく始める / 年収だけ知りたい

**Phase:** `welcome`

**Leads to il_area?** YES — via `welcome=see_jobs`

**Status:** OK

---

### Route 7: Shindan (LP diagnosis) — buildSessionWelcome line 3058-3073

**Trigger:** `/api/line-start?source=shindan&answers={JSON}` with area+workStyle+urgency all present in entry.

**Welcome:**
```
診断結果を引き継ぎました✨

{areaLabel}エリアで
求人を探しますね。

ちょっとお待ちください…
```

**Quick Reply:** 求人を見る (`welcome=start_with_session`)

**Phase:** `welcome`

**Leads to il_area?** NO — Goes to `welcome=start_with_session` -> checks entry has area+workStyle+urgency -> `matching_preview` directly. This is correct; all intake data is pre-filled.

**ISSUE FOUND:** If any of area/workStyle/urgency is missing, falls through to the default welcome (line 3182). The `nextPhase` is still `welcome`, which means the user sees a generic welcome and starts from scratch. The original shindan answers (partial) are lost from the welcome message context. This is a minor edge case.

---

### Route 8: LIFF Session — Follow event line 5439-5561

**Trigger:** `event.type === "follow"` + `liff:{userId}` found in KV/memory.

**Flow:** Restores session data from LIFF bridge -> calls `buildSessionWelcome(liffSessionCtx, entry)` -> sends appropriate welcome based on source.

**Phase:** Set by `buildSessionWelcome.nextPhase` (always `welcome`)

**Status:** OK. LIFF session deleted after use (line 5560).

---

### Route 9: dm_text Session Detection — Text handler line 5954-6017

**Trigger:** `event.type === "message"` + text matches UUID v4 pattern + phase is follow/welcome/consent/il_area.

**Flow:** Looks up `session:{UUID}` in KV -> calls `buildSessionWelcome(sessionCtx, entry)` -> sets phase from returned nextPhase.

**Status:** OK. This is the primary mechanism for `/api/line-start` flow (dm_text method). The `text=` prefix is stripped (line 5957).

---

### Route 10: Legacy 6-char Code — Text handler line 6021-6181

**Trigger:** Text matches `/^[A-Z0-9]{6}$/` + phase is follow/welcome/consent/il_area.

**Flow:** Old shindan 7-question flow. Maps all answers to entry fields -> `matching` phase directly with `generateLineMatching`.

**Status:** OK. Legacy but functional. 24h TTL on session.

---

## Area 2: Re-entry After Dropout

### Scenario A: User starts flow, reaches il_facility_type, goes silent 24h, sends message

**What happens:**
1. KV entry exists with `phase = "il_facility_type"`, TTL = 30 days (expirationTtl: 2592000)
2. User sends text message -> `getLineEntryAsync` retrieves from KV
3. `LINE_SESSION_TTL = 2592000000` (30 days in ms) -> entry is still valid
4. `handleFreeTextInput` is called with phase = "il_facility_type"
5. Since the text is unexpected (line 5415-5420), `unexpectedTextCount` is incremented
6. User gets "すみません、うまく読み取れませんでした。下のボタンからお選びいただけますか？" + current phase Quick Reply

**Status:** OK. User continues exactly where they left off. The Quick Reply re-shows the current question.

### Scenario B: Completes matching, doesn't respond, comes back a week later

**What happens:**
1. Depends on phase at time of silence:
   - If `matching_preview`: KV still valid (30 day TTL). Text -> unexpectedTextCount++ -> Quick Reply re-shown
   - If `nurture_warm`: Same. User gets nurture Quick Reply re-shown
   - If `matching_browse`: Same pattern
2. User can tap any Quick Reply to continue
3. If user types "求人" or a prefecture name, `handleFreeTextInput` won't detect it (no keyword matching for these phases except il_area/il_subarea/welcome)

**Status:** OK but could be improved. There is no "re-engagement" welcome for returning users who have been silent. They just get their current phase's Quick Reply re-shown, which may feel abrupt.

### Scenario C: Was in handoff phase, comes back

**What happens:**
1. `entry.phase === "handoff"` -> direct check at line 6190
2. Bot is COMPLETELY SILENT. No LINE response sent.
3. Message forwarded to Slack with `!reply {userId}` instructions
4. If user sends postback (Quick Reply tap), handoff guard at line 5581-5589 blocks ALL postbacks except `faq=*`

**Status:** OK. This is correct behavior. Human operator handles via Slack `!reply`.

**ISSUE:** There is no timeout/escape mechanism. If handoff was 30 days ago and no human ever responded, the user is stuck in permanent silence. The handoff KV entry has 7-day TTL (`expirationTtl: 604800`), but the main user entry keeps `phase = "handoff"` for 30 days.

### Scenario D: Blocked and then unblocked the bot

**What happens:**
1. **Block:** `event.type === "unfollow"` fires. Nurture and handoff KV keys are deleted. But the main `line:{userId}` KV entry is NOT deleted.
2. **Unblock/Re-follow:** `event.type === "follow"` fires.
   - `getLineEntryAsync` finds existing entry in KV
   - `entry.phase` is RESET to `"welcome"` (line 5431)
   - `entry.updatedAt` is updated
   - All previous data (area, workStyle, matchingResults etc.) is PRESERVED
   - Normal follow flow: check LIFF session -> if none, send default welcome

**Status:** OK. Phase reset to welcome is correct. Previous data preserved is a good touch (user doesn't have to re-answer if they re-engage via session-based route).

---

## Area 3: Rich Menu States

### States (line 3207-3211)

| State | Description | Env Variable |
|-------|-------------|--------------|
| `default` | Initial: 求人探す/年収チェック/転職相談/FAQ | `RICH_MENU_DEFAULT` |
| `hearing` | During intake: 条件変更/求人を見る/担当者相談/FAQ | `RICH_MENU_HEARING` |
| `matched` | After matching: 求人を見る/逆指名/経歴書/担当者相談 | `RICH_MENU_MATCHED` |
| `handoff` | Human handling: 求人を見る/経歴書/FAQ/自由入力 | `RICH_MENU_HANDOFF` |

### Phase-to-Menu Mapping (getMenuStateForPhase, line 3214-3228)

- `handoff` / `handoff_silent` -> handoff
- `matching_preview` / `matching_browse` / `matching` / `matching_more` / `apply_*` / `career_sheet` / `interview_prep` -> matched
- `il_area` / `il_workstyle` / `il_urgency` / `ai_consultation*` -> hearing
- Everything else -> default

### When does it change? (line 5927-5934 for postback, line 6430-6436 for text)

On every phase transition, `getMenuStateForPhase(prevPhase)` vs `getMenuStateForPhase(newPhase)` are compared. If different, `switchRichMenu` is called via `ctx.waitUntil`.

### Are env variables set?

**CANNOT VERIFY from code alone.** The `switchRichMenu` function (line 3230-3253) checks `if (!menuId || !env.LINE_CHANNEL_ACCESS_TOKEN) return;` — meaning if env vars are not set, rich menu switching silently fails. This is a graceful degradation but means rich menus may not be working at all if not configured.

**ISSUE:** `il_subarea`, `il_facility_type`, `il_department` are NOT in the hearing phases list (line 3223-3224). Users in these phases get `default` menu instead of `hearing`. This means the rich menu jumps back to "default" during the middle of intake, which is confusing.

---

## Area 4: Sticker/Image/Location/Voice Handling

### Current handling

The event processing loop (line 5407-6451) handles:
1. `event.type === "follow"` — Welcome flow
2. `event.type === "unfollow"` — Cleanup
3. `event.type === "postback"` — Quick Reply handling
4. `event.type === "message" && event.message.type === "text"` — Text processing

**There is NO handler for:**
- Stickers (`event.message.type === "sticker"`)
- Images (`event.message.type === "image"`)
- Location (`event.message.type === "location"`)
- Voice (`event.message.type === "audio"`)
- Video (`event.message.type === "video"`)
- Files (`event.message.type === "file"`)

**What happens:** These messages fall through all if/else blocks silently. The outer try/catch catches nothing (no error). The `continue` at the end of the for loop moves to the next event. **The user gets NO response at all.**

**Note:** The Slack forwarding at line 5417-5423 only fires for `event.message?.type === "text"`, so non-text messages are not even forwarded to Slack.

**BUG: Non-text messages are completely ignored with no response.** A user sending a sticker (common in LINE culture) or a photo of their nursing license gets zero feedback.

---

## Issues Summary

### BUG-1: Non-text messages silently ignored (HIGH)
**Location:** Line 5407-6451 (processLineEvents event loop)
**Impact:** Users sending stickers, images, location, voice get no response. This is confusing and may cause users to think the bot is broken.
**Fix:** Add handler for non-text message types that acknowledges receipt and re-shows current phase Quick Reply.

### BUG-2: Rich menu missing phases for il_subarea/il_facility_type/il_department (MEDIUM)
**Location:** Line 3223-3224 (getMenuStateForPhase)
**Impact:** Rich menu flickers between "default" and "hearing" during intake flow.
**Fix:** Add `il_subarea`, `il_facility_type`, `il_department` to the hearing phases list.

### BUG-3: Handoff has no escape/timeout (LOW-MEDIUM)
**Location:** Line 6190-6207
**Impact:** If human operator never responds, user is stuck in permanent silence for 30 days.
**Status:** Requires design decision. Not auto-fixable.

### BUG-4: Slack forwarding misses non-text messages (MEDIUM)
**Location:** Line 5417-5423
**Impact:** If a user sends a photo (e.g., nursing license, resume photo), it is not forwarded to Slack at all.
**Fix:** Extend Slack forwarding to include non-text message types.

---

## Fixes Applied

### Fix 1: Non-text message handler (BUG-1 + BUG-4)
Added handler after the text message block for sticker/image/location/voice/video messages.
- Acknowledges receipt
- Re-shows current phase Quick Reply (or appropriate response based on phase)
- Forwards notification to Slack for non-text messages
- In handoff phase, forwards to Slack without LINE response (consistent with handoff silence)

### Fix 2: Rich menu phases (BUG-2)
Added `il_subarea`, `il_facility_type`, `il_department` to the hearing phases in `getMenuStateForPhase`.
