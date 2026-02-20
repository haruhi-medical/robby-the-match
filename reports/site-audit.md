# ROBBY THE MATCH - Site Audit Report

**Date:** 2026-02-16
**Auditor:** Site Audit Agent
**Files Analyzed:** index.html, style.css, script.js, chat.js, chat.css, config.js

---

## Executive Summary

The site is a well-structured dark-mode LP for a medical staffing platform targeting nurses in Kanagawa Prefecture. The foundation is solid with glassmorphism effects, particle animations, and an AI chat widget. However, it lacks visual "wow" factor, has several layout and UX issues, missing trust signals, and needs significant improvements to persuasion, micro-interactions, and mobile experience.

---

## CRITICAL Priority

### C1. Missing OGP Image and Empty OG URL
- **File:** `index.html:14-15`
- **Issue:** `og:image` points to `assets/ogp.png` but no `assets/` directory exists. `og:url` is empty string.
- **Impact:** Social sharing will show broken images. Critical for LINE/Twitter marketing in Japan.
- **Fix:** Create OGP image (1200x630px), place in assets/ directory. Set og:url to actual domain.

### C2. No Favicon or Touch Icons
- **File:** `index.html` (missing entirely)
- **Issue:** No `<link rel="icon">`, no Apple touch icon, no manifest.json.
- **Impact:** Browser tabs show generic icon. Save-to-homescreen on mobile looks unprofessional.
- **Fix:** Add favicon.ico, apple-touch-icon.png, and site.webmanifest.

### C3. Sensitive File Exposed: slack-bot.env
- **File:** `slack-bot.env` (root directory)
- **Issue:** Environment file with potential secrets is in the web-accessible directory.
- **Impact:** Security risk if deployed as-is. Could expose API keys/tokens.
- **Fix:** Move to server-side only location, add to .gitignore, never deploy to static hosting.

### C4. Placeholder License Number Visible
- **File:** `index.html:265, 469` / `config.js:17`
- **Issue:** `##-ユ-######` placeholder for the business license number is shown to users in both the Trust section and Footer.
- **Impact:** Destroys credibility immediately. Users see an unlicensed service.
- **Fix:** Either show actual license number or change text to "申請中" with expected date.

### C5. Empty Company Contact Info in config.js
- **File:** `config.js:18-20`
- **Issue:** `address`, `phone`, and `email` in CONFIG.COMPANY are all empty strings.
- **Impact:** No phone number visible on the entire site. Users cannot call. No address for credibility.
- **Fix:** Populate with real company information. Display prominently in footer and trust section.

### C6. No Google Analytics / Tracking
- **File:** `index.html` (missing entirely)
- **Issue:** Zero analytics integration. No GA4, no GTM, no conversion tracking.
- **Impact:** Cannot measure traffic, conversions, or ROI of any marketing efforts.
- **Fix:** Add GA4 + GTM. Set up conversion events for form submissions and chat starts.

---

## HIGH Priority

### H1. Form Submission Goes Nowhere (Data Loss Risk)
- **File:** `script.js:601-609`
- **Issue:** When both Slack webhook and Google Sheets IDs are empty (current state), form data is only logged to console. User sees "thank you" but data is lost.
- **Impact:** All registrations are lost. Critical for a lead-generation LP.
- **Fix:** At minimum, configure Slack webhook immediately. Add server-side fallback.

### H2. No Testimonials / Social Proof
- **File:** `index.html` (missing section)
- **Issue:** Zero testimonials, user stories, or success metrics. No "XX nurses helped" counter. No "satisfaction rate" stat.
- **Impact:** Major conversion killer. Nurse job-changers need reassurance from peers.
- **Fix:** Add testimonial section with anonymized nurse stories (2-3 minimum). Add aggregate stats like "consultation satisfaction rate XX%."

### H3. Only 1 Hospital in Config, 3 in HTML
- **File:** `config.js:24-36` vs `index.html:134-159`
- **Issue:** config.js HOSPITALS array has only Hospital A. HTML table has A, B, C. Chat AI only knows about Hospital A.
- **Impact:** Chat widget can only recommend one hospital. Inconsistency between chat and page.
- **Fix:** Add Hospital B and C data to config.js HOSPITALS array.

### H4. Hero Section Typography Lacks Impact
- **File:** `style.css:497-503`
- **Issue:** Hero title on mobile is 2.2rem (35px) which is adequate but not impactful. Desktop bumps to 3.2rem. No font-weight variation, no gradient text effect on the title. Subtitle line-height 1.8 creates too much vertical space.
- **Impact:** First impression lacks the "wow" moment. Hero does not command attention.
- **Fix:** Increase mobile hero title to 2.6rem, desktop to 4rem. Apply gradient text to highlight span. Tighten subtitle line-height to 1.6. Add letter-spacing: -0.02em to title for modern feel.

### H5. No Phone Number CTA / Click-to-Call
- **File:** `index.html` (missing)
- **Issue:** No visible phone number anywhere on the landing page. Footer has email but no phone. Nurses may prefer calling over forms.
- **Impact:** Lost conversions from users who prefer voice contact. Especially important for older demographic.
- **Fix:** Add phone number in header (desktop) and as sticky mobile CTA bar at bottom. Use `tel:` link for click-to-call.

### H6. Custom Cursor Hides System Cursor
- **File:** `style.css:196-198`
- **Issue:** `body { cursor: none; }` hides the system cursor on desktop. The custom cursor has inherent lag (0.15 easing factor in script.js:39) and uses mix-blend-mode: difference which can make it invisible on certain backgrounds.
- **Impact:** Usability issue. Users may lose track of cursor. Accessibility concern for users with motor impairments.
- **Fix:** Remove cursor:none entirely. Keep the custom cursor as a decorative follower but don't hide the real cursor. Or make it opt-in with reduced lag.

### H7. Form Too Long - No Progressive Disclosure
- **File:** `index.html:287-432`
- **Issue:** Registration form has 11 fields visible at once (8 required, 3 optional + consent). This is overwhelming for a "3 minutes" promise.
- **Impact:** High form abandonment rate. Too many decisions at once.
- **Fix:** Split into 2-3 steps with progress indicator. Step 1: Name + phone + email (3 fields). Step 2: Experience + status + timing + salary. Step 3: Optional fields. Or hide optional fields behind an expandable "More options" section.

### H8. No Sticky/Fixed CTA on Scroll
- **File:** `style.css` (missing)
- **Issue:** Once the user scrolls past the hero section, there is no persistent CTA button visible. They must scroll to find "register" links.
- **Impact:** Missed conversion opportunities when user is ready to act mid-scroll.
- **Fix:** Add a sticky bottom bar on mobile with "Register" CTA that appears after scrolling past hero. On desktop, the nav CTA serves this purpose but should be more prominent.

### H9. Table Section Not Mobile-Friendly
- **File:** `style.css:653-710`, `index.html:122-166`
- **Issue:** Hospital comparison table has `min-width: 700px` requiring horizontal scroll on mobile. No card-view alternative for small screens.
- **Impact:** Mobile users get a poor experience scrolling horizontally. Key data is hard to compare.
- **Fix:** Transform table into stacked cards on mobile (below 640px). Each hospital becomes a full-width card with key metrics as label-value pairs.

### H10. Missing Error Recovery for Form
- **File:** `script.js:605-609`
- **Issue:** When form submission fails (catch block), it still shows the thank-you screen (`showThanks()`). User thinks submission succeeded.
- **Impact:** Users believe they registered but their data was lost.
- **Fix:** Show an error message with retry option. Only show thanks on actual success.

---

## MEDIUM Priority

### M1. Typing Animation Flashes Content
- **File:** `script.js:407-462`
- **Issue:** Hero subtitle has its original HTML content, then gets replaced by typing animation after 1.2s delay. During typing, the original `<span class="highlight">` markup is replaced by plain text. After completion, it restores original HTML - causing a visual flash/jump.
- **Impact:** Jarring visual experience. Content reflows when original HTML is restored.
- **Fix:** Either (a) keep typed text and don't restore original HTML, or (b) type the HTML-aware content using innerHTML, or (c) remove typing animation and use a cleaner reveal effect.

### M2. Parallax Section Gradient Overlays Cause Clipping
- **File:** `style.css:1218-1235`
- **Issue:** All `.parallax-section` elements have `::after` pseudo-element creating bottom gradient fade. Combined with `transform: translateY()` in script.js:389, this can cause visible seams between sections and content clipping.
- **Impact:** Visual artifacts at section boundaries. Z-index battles.
- **Fix:** Use `position: relative` with overflow: hidden on parallax sections. Ensure gradient overlays account for transform offsets.

### M3. Section Spacing Inconsistency
- **File:** `style.css` (multiple sections)
- **Issue:** Features/Hospitals/Flow/Mission all use `padding: 100px 0`, Trust uses `padding: 100px 0`, Register uses `padding: 100px 0`. While consistent, there is no visual rhythm differentiation between major and minor sections.
- **Impact:** Page feels monotonous. Every section has equal weight.
- **Fix:** Vary section padding: Hero (full viewport), Main sections (100px), Sub-sections (80px). Add decorative dividers or subtle background pattern changes between key sections.

### M4. Feature Cards Stagger Delay Only Goes to 4
- **File:** `style.css:1212-1215`, `script.js:280-284`
- **Issue:** Stagger delay classes only defined up to `.delay-4`, but feature cards use `delay-(i+1)` where i goes 0-3, resulting in delay-1 through delay-4. This works for 4 cards but the system is fragile - adding a 5th card would fail silently.
- **Impact:** Low risk currently, but indicates brittle animation system.
- **Fix:** Use inline transition-delay via JavaScript instead of numbered classes. `el.style.transitionDelay = (i * 0.1) + 's'`.

### M5. No Loading State Feedback on Chat Send
- **File:** `chat.js:292-304`
- **Issue:** When user sends a message, the button is disabled but there is no visual change to the send button itself (no spinner, no color change). Only the typing indicator in the chat body shows activity.
- **Impact:** User may think the button is broken.
- **Fix:** Add a spinning animation to the send button while waiting for response, or change its appearance.

### M6. Chat Window Z-Index Conflicts
- **File:** `chat.css:81` - z-index 8999, `style.css:101` - scroll progress z-index 10000
- **Issue:** Chat window (8999) is below scroll progress bar (10000). The chat toggle is at 9000. Loading screen is at 99999. The z-index hierarchy is ad-hoc.
- **Impact:** Potential overlapping issues. Chat could be partially obscured.
- **Fix:** Establish a clear z-index scale: base content (1-10), header (100), modals/overlays (200), chat (300), loading (999).

### M7. No Focus Trap in Mobile Menu / Chat
- **File:** `script.js:210-230`, `chat.js:199-219`
- **Issue:** When mobile menu or chat window opens, focus is not trapped. Users can Tab out into content behind the overlay.
- **Impact:** Accessibility issue. Screen reader users and keyboard navigators can get lost.
- **Fix:** Implement focus trap for mobile menu and chat window. Trap Tab/Shift+Tab cycling within the open element.

### M8. Missing Skip-to-Content Link
- **File:** `index.html` (missing)
- **Issue:** No skip navigation link for keyboard/screen reader users to jump past the header.
- **Impact:** Accessibility violation. Keyboard users must tab through all nav items every page load.
- **Fix:** Add `<a href="#hero" class="skip-link">コンテンツへスキップ</a>` as first child of body, visually hidden until focused.

### M9. Color Contrast Issues
- **File:** `style.css:23` - `--text-secondary: #A0A0A0` on `--bg-primary: #0D1B2A`
- **Issue:** Secondary text (#A0A0A0) on primary background (#0D1B2A) has contrast ratio of approximately 6.5:1 which passes AA but the text is often at 0.85-0.9rem making it harder to read. More critically, the hero-note and table-note use this color at 0.8-0.85rem.
- **Impact:** Small secondary text may be hard to read for users with visual impairments.
- **Fix:** Increase secondary text to #B0B0B0 or increase font-size minimums to 0.9rem for all secondary text.

### M10. No 404 Page
- **File:** (missing)
- **Issue:** No custom 404 page. If terms.html or privacy.html links break, user sees default server 404.
- **Impact:** Lost users when broken links are encountered.
- **Fix:** Create a branded 404.html page with navigation back to main LP.

### M11. Chat Whitespace Handling
- **File:** `chat.js:285`
- **Issue:** `bubble.textContent = content` does not preserve newlines from AI responses. The demo responses contain `\n` characters (e.g., line 100-101) but textContent does not render them.
- **Impact:** AI chat responses appear as continuous text blocks without paragraph breaks.
- **Fix:** Use `bubble.innerHTML` with sanitized content (escape HTML, convert `\n` to `<br>`), or set `white-space: pre-wrap` on `.chat-bubble`.

### M12. No Preload for Critical Resources
- **File:** `index.html:23-24`
- **Issue:** CSS files are loaded with regular `<link rel="stylesheet">` but no preload hints. No font preloading. No preconnect to any external domains.
- **Impact:** Render-blocking CSS. Slower FCP (First Contentful Paint).
- **Fix:** Add `<link rel="preload" href="style.css" as="style">`. If using external fonts later, add preconnect.

### M13. Mission Cycle Diagram Readability on Mobile
- **File:** `style.css:828-847`, `index.html:214-238`
- **Issue:** The cycle-flow is `display: flex; flex-wrap: wrap` with arrow spans. On narrow screens, the flow wraps awkwardly with arrows appearing at start of new lines instead of between items.
- **Impact:** The "bad cycle" vs "good cycle" comparison -- the key persuasion element -- becomes hard to follow on mobile.
- **Fix:** On mobile, convert to a vertical flow with downward arrows. Use `flex-direction: column` below 640px and replace horizontal arrows with vertical ones.

---

## LOW Priority

### L1. No CSS Minification / Build Step
- **File:** All CSS/JS files
- **Issue:** All files are unminified development versions. Total CSS: ~1,930 lines (style.css + chat.css). Total JS: ~1,240 lines (script.js + chat.js + config.js).
- **Impact:** Slightly slower load times. Approximately 15-20KB larger than necessary.
- **Fix:** Set up a build step with CSS/JS minification for production deployment.

### L2. Particle Canvas Performance on Low-End Devices
- **File:** `script.js:69-205`
- **Issue:** Canvas particle animation runs with O(n^2) distance checks for connections (line 109-138). 70 particles on desktop = 2,415 comparisons per frame. While IntersectionObserver pauses when off-screen, there is no throttle on low-end devices.
- **Impact:** May cause battery drain and jank on older mobile devices.
- **Fix:** Reduce mobile particles further (20 instead of 30). Add frame-rate monitoring and auto-reduce complexity. Consider using CSS-only particle alternative.

### L3. No Print Stylesheet
- **File:** (missing)
- **Issue:** Printing the page outputs dark backgrounds, hidden content, and broken layout.
- **Impact:** Users who want to print hospital comparison info get unusable output.
- **Fix:** Add `@media print` styles that switch to light background, hide nav/chat/loading elements, and ensure table prints properly.

### L4. meta description Uses "業界最低水準" Phrasing
- **File:** `config.js:11`
- **Issue:** META_DESCRIPTION says "業界最低水準の10%" but this text differs from what is used in index.html:7. The HTML says "一般的な紹介手数料の約半分、10%に" which is more accurate and less likely to trigger regulatory concerns.
- **Impact:** Inconsistent messaging. "業界最低水準" could be a compliance issue (unverifiable superlative claim).
- **Fix:** Unify messaging. Use "一般的な紹介手数料の約半分" consistently.

### L5. No Lazy Loading for Below-the-Fold Content
- **File:** `index.html`
- **Issue:** While there are no images currently, when images/icons are added, there is no lazy loading strategy. Scripts all load synchronously at end of body.
- **Impact:** Minimal now, but will worsen as content grows.
- **Fix:** Add `loading="lazy"` to future images. Consider `defer` attribute on scripts.

### L6. Config.js Exposes Internal Data Structure
- **File:** `config.js` (entire file)
- **Issue:** Configuration including API endpoint structure, design tokens, and internal hospital IDs is exposed client-side.
- **Impact:** Low security concern for a static site, but reveals internal architecture to competitors.
- **Fix:** Move sensitive configuration to server-side. Keep only display-safe data client-side.

### L7. Heading Hierarchy Skip
- **File:** `index.html:94, 98, 103, 107`
- **Issue:** Feature cards jump from `<h2>` (section title) to `<h3>` which is correct, but within cards there is a `.feature-number` div styled like a heading without semantic heading markup. The visual hierarchy suggests it should be above h3.
- **Impact:** Minor semantic issue. Screen readers may not understand the visual hierarchy.
- **Fix:** Consider whether feature-number should be `aria-hidden="true"` (decorative) or given proper heading semantics.

### L8. Inline Styles Used for Layout
- **File:** `index.html:163, 251, 437`
- **Issue:** Several inline `style="text-align:center; margin-top:2rem;"` and `style="display:none;"` are used.
- **Impact:** Maintenance difficulty. Style inconsistency.
- **Fix:** Move to CSS classes. Replace inline display:none with a `.hidden` utility class toggled by JS.

---

## Missing Elements Checklist

| Element | Status | Priority |
|---------|--------|----------|
| OGP image | Missing | CRITICAL |
| Favicon / touch icons | Missing | CRITICAL |
| Analytics (GA4/GTM) | Missing | CRITICAL |
| Phone number / click-to-call | Missing | HIGH |
| Testimonials / success stories | Missing | HIGH |
| Partner hospital logos | Missing | HIGH |
| "XX nurses helped" counter | Missing | HIGH |
| Sticky mobile CTA | Missing | HIGH |
| FAQ section | Missing | MEDIUM |
| Company representative photo | Missing | MEDIUM |
| Blog / Content marketing links | Missing | MEDIUM |
| Newsletter signup | Missing | LOW |
| SNS links (LINE/Instagram) | Missing | LOW |
| Comparison with competitors section | Missing | LOW |
| Video introduction | Missing | LOW |

---

## Micro-Interactions Inventory

### Existing (Good)
- Button ripple effect on click (`style.css:220-236`)
- Nav link underline slide on hover (`style.css:311-328`)
- Feature card 3D tilt on hover (`script.js:352-371`)
- Particle canvas mouse interaction (`script.js:126-138`)
- Chat message entry animation (`chat.css:244-253`)
- Typing indicator bounce (`chat.css:358-367`)
- Loading screen fade-out (`style.css:106-124`)
- Count-up number animation (`script.js:319-348`)
- Scroll progress bar (`style.css:94-103`)
- Chat toggle pulse ring (`chat.css:40-64`)

### Missing (Should Add)
- Form input focus label animation (float label pattern)
- Button hover state with icon slide or arrow animation
- Scroll-triggered section header decoration (underline draw)
- Table row hover highlight with accent glow
- Feature card icon animation on hover
- Flow step connector animation (draw line on scroll)
- Trust item entrance with icon spin/scale
- Chat quick-reply button press effect
- Form field success checkmark animation
- Mobile menu slide-in animation (currently just display toggle)
- Footer link hover with arrow/underline slide

---

## Typography Assessment

### Current State
- **Font Stack:** Helvetica Neue, Arial, Hiragino Sans, Meiryo (system fonts)
- **Base Size:** 16px
- **Line Height:** 1.7 (body), 1.4 (hero title), 1.8 (hero subtitle), 1.9 (mission statement)
- **Heading Scale:** 3.2rem (hero desktop), 2.2rem (section desktop), 1.2rem (card h3), 1.1rem (flow step h3)
- **Weight Usage:** 500 (nav), 600 (buttons/labels), 700 (section titles), 800 (hero/logo/numbers)

### Issues
1. **No custom font** - System font stack works but lacks brand personality. Consider adding one display font for headings (e.g., Inter, Noto Sans JP).
2. **Letter-spacing inconsistent** - Only applied to hero-label (2px), table headers (1px), and cycle-label (1px). Section titles have none.
3. **Line-height variation** - Too many different line-heights (1.4, 1.6, 1.7, 1.8, 1.9). Simplify to 1.4 (headings) and 1.7 (body).
4. **Font-size scale jumps** - 0.8rem to 0.85rem to 0.9rem to 0.95rem to 1rem -- too many sizes too close together. Establish a clear type scale.

### Recommendation
Adopt a modular scale (1.25 ratio): 0.8rem, 1rem, 1.25rem, 1.563rem, 1.953rem, 2.441rem, 3.052rem. This creates clearer visual hierarchy.

---

## Performance Observations

1. **No render-blocking optimization** - 2 CSS files load synchronously
2. **Particle canvas is expensive** - O(n^2) per frame, runs at full refresh rate
3. **Multiple IntersectionObservers** - 3 separate observers (animations, counts, particles). Could consolidate to 1.
4. **No requestIdleCallback** usage for non-critical initializations
5. **backdrop-filter used extensively** - ~10 instances. Performance impact on mobile Safari.
6. **Will-change on feature cards** - `will-change: transform` on 4 cards promotes them to compositor layers permanently

---

## Color Palette Assessment

### Current Palette
- Primary BG: `#0D1B2A` (very dark navy)
- Secondary BG: `#1B2838` (dark navy)
- Card BG: `#152238` (medium-dark navy)
- Accent: `#00B4D8` (cyan)
- Accent Secondary: `#00D4AA` (teal/mint)
- Text Primary: `#E0E0E0` (light gray)
- Text Secondary: `#A0A0A0` (medium gray)
- Error: `#FF6B6B` (coral red)
- Success: `#4ECB71` (green)

### Assessment
- The palette is cohesive and professional for a tech-forward brand
- Dark mode is appropriate for the modern/AI positioning
- **Issue:** Only 2 accent colors. The page feels visually monotone. Adding a warm accent (gold/amber) for emphasis elements could break the coldness
- **Issue:** The gradient from cyan to teal (#00B4D8 to #00D4AA) is too subtle - colors are too close on the spectrum
- **Issue:** No use of accent-secondary in meaningful ways other than particle connections and gradient endpoint
- **Issue:** Error color (#FF6B6B) has low contrast ratio on dark backgrounds for small text

---

## Summary & Recommended Implementation Order

### Phase 1 - Critical Fixes (Deploy blockers)
1. C4: Fix license placeholder or mark as "申請中"
2. C5: Add company contact information
3. C1: Create and add OGP image, set og:url
4. C2: Add favicon and touch icons
5. C3: Remove slack-bot.env from web directory
6. C6: Add analytics tracking
7. H1: Configure Slack webhook for form data capture
8. H10: Fix form error handling (don't show thanks on failure)

### Phase 2 - High-Impact Improvements (Conversion boosters)
1. H2: Add testimonials section
2. H5: Add phone number + click-to-call
3. H7: Multi-step form or progressive disclosure
4. H8: Sticky mobile CTA
5. H9: Mobile-friendly hospital cards
6. H4: Improve hero typography impact
7. H6: Fix custom cursor UX
8. H3: Sync hospital data between config and HTML

### Phase 3 - Polish & Accessibility
1. M8: Skip-to-content link
2. M7: Focus traps for overlays
3. M9: Color contrast improvements
4. M11: Chat newline rendering
5. M1: Fix typing animation flash
6. M13: Mobile cycle diagram layout
7. Add missing micro-interactions

### Phase 4 - Optimization
1. L1: Build step with minification
2. L2: Particle performance optimization
3. M12: Resource preloading
4. M6: Z-index system cleanup
