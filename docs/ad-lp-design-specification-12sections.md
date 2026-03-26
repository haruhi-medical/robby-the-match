# 12-SECTION AD-SPECIFIC LP DESIGN SPECIFICATION
## 神奈川ナース転職 — 広告専用LP設計書

**Created**: 2026-03-26
**Status**: Design specification complete, awaiting implementation
**Path**: `/lp/ad/index.html` (not yet created)

---

## EXECUTIVE SUMMARY

This document specifies the complete 12-section landing page design for ad-driven traffic (Meta Ads, Instagram). The design is adapted from **Withmal** (veterinary recruitment LP), which shares identical go-to-market dynamics: medical sector + LINE-only CTA + lightweight entry diagnostic.

**Key Design Philosophy**:
- Mobile-first (480px max-width, portrait-optimized)
- 6 LINE CTAs distributed throughout (no forms)
- Robby (AI character) as personality driver
- Factual HelloWork salary data (visible as "参考値", source never mentioned)
- Minimize "転職" language (use "働き方チェック", "お給料チェック")
- NO personal names or corporate details visible to user

---

## REFERENCE ANALYSIS: WITHMAL (最も参考になるモデル)

### Withmal Situation (同じ構図)
- **Target**: Medical professionals (獣医師)
- **Offer**: Job placement × LINE-based consultation
- **Entry**: Lightweight "相性診断" (compatibility check)
- **No forms**: All CTAs point to LINE friend addition only
- **CTA frequency**: 6 times throughout the page

### Withmal's 11-Section Structure

```
1. Hero
   Copy: 「理想のキャリア、Withmalで叶えませんか？」
   CTA#1: LINE CTA

2. 悩み共感 (Empathy)
   4 cards addressing target pain points
   CTA#2: Soft conversion

3. 会社紹介 (Company)
   「全国45院・獣医師110名」
   4 features of white environment

4. 求める人材 (Talent profile)
   4 patterns

5. 募集病院一覧 (Job carousel)
   Prefecture + hospital name + salary + benefits

6. スタッフインタビュー (Testimonials)
   3 Q&A interviews

7. 中間CTA (Mid-page CTA)
   「相性度LINE診断」
   CTA#3: Conversion trigger

8. 1日スケジュール (Daily schedule)
   8:30-20:00 timeline

9. 募集要項・待遇 (Recruitment details)
   Application flow (4 steps) + FAQ (5 questions)

10. LINE CTA手順図解 (LINE instruction diagram)
    3-step visual guide
    CTA#4-6: Reinforcement CTAs

11. 会社情報 (Footer)
    Company info, contact, legal
```

### 7 Key Learnings Applied to 神奈川ナース転職

| # | Learning | Application |
|---|----------|-------------|
| 1 | Lightweight entry via diagnosis | "転職しませんか" → "あなたに合う職場、30秒で診断" |
| 2 | Empathy-driven FV | 4 pain points (夜勤/人間関係/給与/キャリア) |
| 3 | CTA repetition (6x) | Reinforce throughout, not just 2-3 times |
| 4 | Concrete job carousel | Hospital cards: salary × accessibility × facility type |
| 5 | Staff testimonials | Future: real conversion stories (first placement pending) |
| 6 | Application flow diagram | LINE追加→AI相談→求人紹介→面接→内定 |
| 7 | LINE-only conversion | No forms, no email capture, just LINE friend add |

### Why Withmal is the Best Model
- **医療職採用**: Same sector as us (high trust, risk-averse audience)
- **LINE導線**: Identical primary CTA mechanism
- **相性診断**: Lightweight entry point matches our LINE Bot flow
- **全国展開**: Multi-region recruitment (like our 神奈川県全域)
- **ホワイト環境訴求**: Both emphasize work environment quality

---

## 12-SECTION AD-SPECIFIC LP DESIGN (神奈川ナース転職)

### DESIGN SPECIFICATIONS

| Specification | Value |
|---------------|-------|
| **Target Device** | Mobile only (portrait) |
| **Max-width** | 480px |
| **CTA Strategy** | 6 CTAs, all LINE friend addition |
| **Forms** | 0 (LINE only) |
| **Primary Personality** | Robby (AI character) |
| **Data Source Visibility** | Hidden (shown as "参考値", source never revealed) |
| **Tone** | Supportive, empathetic, factual |
| **Conversion Goal** | LINE friend addition (first micro-conversion) |

---

## SECTION-BY-SECTION SPECIFICATION

### **SECTION 1: HERO**

**Purpose**: Stop scroll, establish emotional resonance, light entry point

**Copy Spec**:
- Headline: `「今の働き方、ずっと続けられますか？」`
- Subheader: TBD (final copy pending hero image)
- Tone: Question-based (open uncertainty), not confrontational

**Visual Spec**:
- **PC**: 1500px × 837px (landscape)
- **SP**: 837px × 1500px (portrait, primary)
- Format: JPG or WebP
- Text overlay: None (NO baked-in text, use HTML text layer)
- Alt text: Required for accessibility

**CTA#1**:
- Text: `LINEで相談する` or `LINEでチェック` (finalize based on subheader)
- Color: TBD (match hero dominant color)
- Position: Below hero, sticky-friendly
- Action: `window.location.href = LINE_ADD_URL`

**Design Decisions**:
- NO text on image (prevent accessibility issues, allow A/B text testing)
- Portrait for mobile (native aspect ratio)
- Question format (Withmal uses "理想のキャリア〜叶えませんか", ours softens to "ずっと続けられますか")

---

### **SECTION 2: 悩み共感 (EMPATHY CARDS)**

**Purpose**: Mirror user pain, trigger recognition moment, prepare for Robby intro

**Copy Spec**: 4 empathy pain points (from Misaki A/B/C personas)

```
Card 1: 夜勤がきつい
Subtitle: 「体力が持つかな…」

Card 2: 人間関係
Subtitle: 「先輩との関係、辛い…」

Card 3: 給与が低い
Subtitle: 「手取りが厳しい…」

Card 4: キャリアが見えない
Subtitle: 「このままでいいのかな…」
```

**Visual Design**:
- 4-column grid (SP: 2×2 stacked)
- Each card: Icon (SVG, not emoji) + title + subtitle
- Icons: Use existing SVG library from main site
- Card color: Light background (white or very light gray)
- Border: Subtle (1px light gray)

**CTA#2** (soft):
- Text: `このお悩みに応えます` or `あなたの働き方、一緒に考えませんか？`
- Position: Below cards
- Style: Secondary button (outline)
- Action: Link to Robby section (anchor link)

**Design Decisions**:
- 4 cards matches Withmal structure
- Pain points from actual persona research (not generic)
- Light CTA (not pushing LINE add yet)

---

### **SECTION 3: ロビー登場 (ROBBY CHARACTER INTRO)**

**Purpose**: Build brand personality, establish AI trust, humanize service

**Copy Spec**:
```
Title: 「あなたの転職相談相手、ロビーです」
Description: 「AIなのに、プロなのに、あなたのペースで相談できる。
            忙しい今、LINEで24時間サポート。
            あなたに合う職場、見つけるまで一緒に」
```

**Visual Design**:
- Robby character image (illustration, not photo)
- Size: 300px × 300px (centered, portrait crop)
- Background: Light gradient (not solid white)
- Border: Rounded corners (20px)

**CTA#3**:
- Text: `ロビーに相談する` (linked to LINE)
- Color: Primary brand color (match hero)
- Position: Below character intro
- Action: LINE friend addition

**Design Decisions**:
- Robby is core differentiator (vs Withmal's company intro)
- Emphasize AI + human support combo
- Character image builds trust with visual persona
- "相談" framing (advisory, not "recruiting")

---

### **SECTION 4: エリア別お給料チェック (SALARY DATA EXPLORER)**

**Purpose**: Provide concrete value, show market position, engage with interactive element

**Data Spec**:
- **Source**: HelloWork API filtered data (1,364 nurse jobs in Kanagawa)
- **Dimensions**:
  - Geography (9 regions: 横浜, 川崎, 相模原, etc.)
  - Facility type (hospital, clinic, care facility)
  - Role type (full-time RN, part-time, night shift)
- **Metrics**: Monthly salary median, min/max range
- **Data Quality**: N-count filtering (show ranges only if N≥5, no individual values if N<5)

**UI Design** (one of two approaches):

**Option A: Map-based selector**
```
[神奈川県地図 with 9 region clickable areas]
↓
Selected region → Facility selector
↓
「横浜 × 病院 × 常勤」: 31万-36万円 (参考値)
```

**Option B: Tab-based selector**
```
[地域: 横浜 | 川崎 | 相模原...]
[施設: 病院 | クリニック | 訪問看護...]
[勤務: 常勤 | 夜勤専従...]
↓
Results displayed below
```

**Copy Spec**:
```
Title: 「あなたの地域の平均はいくら？」
Description: 「20代看護師の給与実績。
             同じ地域・施設の給与が見える」
Disclaimer: 「※毎週更新・ハローワーク公開求人データに基づく参考値です」
```

**CTA#4**:
- Text: `あなたの給料、相場と比べてみませんか？`
- Position: Below results
- Action: LINE friend addition (handoff to AI consultation)

**Design Decisions**:
- **NOT a "diagnosis"** (avoid 景表法 fraud risk)
- Data shown as "参考値" (reference value, not diagnostic)
- No individual salary promises
- HelloWork source never mentioned (data only, clean stats)
- Interactive element improves engagement vs static content
- Regional focus (神奈川県全域) differentiator

**Implementation Notes**:
- Data must be in `/data/salary_stats.json` (generated by `hellowork_salary_stats.py`)
- JS UI in separate `salary_explorer.js` module
- Data updated weekly via cron
- No personal data stored (view-only)

---

### **SECTION 5: 3つの「ない」宣言 (THREE "NO" PROMISE)**

**Purpose**: Differentiate from traditional recruitment (telephone, pressure, cost), address Misaki concerns

**Copy Spec**:

```
Headline: 「転職するなら、こんなんじゃない。」

Card 1: 電話なし
        「営業電話は来ません。
         LINEで、あなたのペースで。」

Card 2: 営業なし
        「無理な営業はしません。
         選べる、やめられる。」

Card 3: 費用なし
        「あなたには費用がかかりません。
         手数料は病院が負担。」
```

**Visual Design**:
- 3 equal-width cards (SP: stacked)
- Each card: Bold "✕" or "なし" icon + copy
- Background: White/light with colored accent top bar
- Accent colors: Use 3 different brand colors (diversity)

**CTA**: None in this section (content-driven)

**Design Decisions**:
- "ない" (negation) is powerful messaging for Misaki
- Addresses specific fears (phone calls from recruiters)
- Differentiates from Withmal (which doesn't highlight this)
- Builds on "お金がない" complaint from earlier

---

### **SECTION 6: 利用者の声 (TESTIMONIALS)**

**Purpose**: Social proof, build confidence, showcase Misaki post-placement success

**Copy Spec**:
```
Headline: 「実際に使った人の声」
Subtitle: 「転職を決めた看護師たちの、
         本当のコメント」
```

**Card Design** (2-3 testimonials):
```
[Profile photo]
Name, Age, Hospital before → Hospital after
Quote: 「前は夜勤ばっかだったけど、
       ここは融通がきく。
       給料も上がった。」
Rating: ⭐⭐⭐⭐⭐ 5/5
```

**Current Status**:
- Placeholder design complete
- Actual testimonials: Awaiting first successful placement
- Plan: Collect via post-placement survey

**CTA**: None (content-only)

**Design Decisions**:
- **Real testimonials only** (no fake personas)
- Withmal uses 3, we use 2-3 (can grow over time)
- Rotate testimonials monthly (freshness)
- Photo + name + detail (builds credibility vs anonymous)

---

### **SECTION 7: 手数料10%の仕組み (FEE STRUCTURE EXPLANATION)**

**Purpose**: Explain value proposition, justify 10% (vs 20-30% market), show cost reduction chain

**Copy Spec**:
```
Headline: 「手数料10%？なんで安い？」

Explanation:
「ハローワーク求人 + AIマッチング で
 採用コストを削減。
 その削減分を、あなたの給与に還元する。

 医療の質・設備・働く環境の向上に。」

Flow diagram (3 step):
1. 「AIが自動マッチング」
   ↓
2. 「採用コスト削減（手数料20%→10%）」
   ↓
3. 「病院が短期間に採用できる」
   ↓
4. 「→ あなたの待遇が良い」
```

**Visual Design**:
- 4-step horizontal flow (SP: vertical stack)
- Each step: Icon + copy (centered)
- Arrows between steps
- Accent color: Brand primary

**CTA#5**:
- Text: `この仕組みに納得した。ロビーに相談`
- Position: Below diagram
- Action: LINE friend addition

**Design Decisions**:
- Address implicit question: "手数料安すぎないか？"
- Show business model transparency
- Emphasize AI cost reduction (core differentiator)
- 10% justified by HelloWork + automation (not VC subsidy)

---

### **SECTION 8: マーケットデータ (MARKET STATISTICS)**

**Purpose**: Establish Kanagawa context, show Misaki has negotiating power, build confidence

**Data Spec** (from earlier research):

```
統計タイトル: 「神奈川県の看護師市場、知っていますか？」

Stat 1: 看護師数
        「神奈川県：77,188人」
        Icon: people

Stat 2: 人口比
        「人口10万人あたり813.2人」
        Icon: map-pin
        Copy: 「これは全国ワースト3位。
              つまり、売り手市場。」

Stat 3: 求人数
        「2,000件以上の公開求人」
        Icon: briefcase
        Copy: 「毎月更新。
              あなたの条件に合う職場がある。」

Stat 4: 平均給与
        「月給 30万-35万円」
        Icon: yen
        Copy: 「夜勤手当込み。
              経験・資格で更に上乗せ可能。」
```

**Visual Design**:
- 4-stat grid (SP: 2×2)
- Each stat: Icon (SVG) + number + description
- Stat font size: Large and bold (for emphasis)
- Background: Light accent color per card
- Data sourced from HelloWork (source NOT visible)

**CTA**: None (informational section)

**Design Decisions**:
- Build Misaka confidence ("売り手市場")
- Concrete numbers (not abstract promises)
- Kanagawa-specific (competitive advantage vs national ads)
- Data from public sources (HelloWork = credible)

---

### **SECTION 9: 利用の流れ (4-STEP APPLICATION FLOW)**

**Purpose**: Demystify process, show lightweight entry, clarify LINE-to-placement journey

**Flow Spec**:

```
Step 1: LINE友だち追加
        Visual: LINE icon + phone silhouette
        Copy: 「ロビーを友だち追加。
               5秒で完了。」

Step 2: AIで相談
        Visual: Chat bubble icon
        Copy: 「あなたの条件をロビーに相談。
               24時間対応。」

Step 3: 求人紹介
        Visual: Document/card icon
        Copy: 「あなたに合った求人を紹介。
               複数社から選べる。」

Step 4: 面接・内定
        Visual: Handshake icon
        Copy: 「直接交渉。給与・休暇など
               あなたのペースで。」
```

**Visual Design**:
- Horizontal flow (SP: vertical)
- Step number + icon + copy (centered)
- Arrow/connector between steps
- Accent color: Brand primary

**CTA#5** (重複なし):
- Text: `この流れなら、大丈夫。`
- Position: Below flow
- Action: Soft CTA (anchor link to final CTA section)

**Design Decisions**:
- 4 steps (matches Withmal structure)
- "相談→紹介→交渉" emphasizes user control (vs "apply→wait→interview")
- No form submission (LINE-only)
- Emphasizes speed ("5秒")

---

### **SECTION 10: FAQ (5 QUESTIONS)**

**Purpose**: Address residual objections, reduce friction to LINE conversion

**FAQ Spec**:

```
Q1: 「本当に無料ですか？」
A: 「あなたには費用はかかりません。
   手数料は採用側の病院が負担。
   求人紹介までは完全無料。」

Q2: 「どこの地域に対応していますか？」
A: 「神奈川県全域対応。
   横浜・川崎から相模原、県西まで。
   地方からの検討も歓迎です。」

Q3: 「マッチング成功率は？」
A: 「現在、データを集計中です。
   最初の成功事例が完成次第、
   リアルタイムで公開予定。」

Q4: 「LINE登録後、どのくらいで求人が来ますか？」
A: 「平均 1-3日以内に初回紹介。
   あなたの条件による。
   条件が多いと、時間がかかる場合もあります。」

Q5: 「今の病院にバレませんか？」
A: 「バレません。
   LINE相談は秘密。
   実際の応募までは、あなたが決定。」
```

**Visual Design**:
- Accordion UI (click to expand)
- Q in bold, A in regular weight
- Border: Subtle divider per Q-A pair
- No icons (clean, text-focused)

**CTA**: None in FAQ (already have 5 CTAs by this point)

**Design Decisions**:
- Address fear objections (cost, privacy, timeline)
- Honest on data gaps (no success rate until first placement)
- Emphasis on user control (LINE is private, you decide)

---

### **SECTION 11: 最終CTA (FINAL CONVERSION PUSH)**

**Purpose**: Last opportunity to convert before footer, emotional close

**Copy Spec**:
```
Headline: 「次の一歩を踏み出そう」

Subheader: 「今は迷っている。でも、
           このままもずっと同じ。

           5秒で変わる。」

Button Text: 「ロビーに無料で相談する」
             (or match hero CTA text for consistency)
```

**Visual Design**:
- Full-width section (edge-to-edge SP)
- Background: Contrasting color (light accent or gradient)
- Button: Prominent (large padding, solid color)
- Button position: Center, sticky-friendly

**CTA#6** (Primary conversion):
- Text: `ロビーに無料で相談する`
- Color: Brand primary (most prominent button on page)
- Size: XL (60px+ height)
- Action: LINE friend addition (analytics tagged as "cta_final")
- Accessibility: High contrast, large touch target

**Design Decisions**:
- "無料で相談" emphasizes low barrier
- "次の一歩" + "5秒で変わる" uses behavioral psychology
- Contrasting background ensures visibility
- Large button increases mobile conversion (easier tap)

---

### **SECTION 12: フッター (FOOTER)**

**Purpose**: Legal compliance, brand closure, mobile navigation

**Content Spec**:

```
Company Name:
「神奈川ナース転職」
(or「神奈川ナース転職編集部」for content)

Links:
- プライバシーポリシー → /privacy.html
- 利用規約 → /terms.html
- お問い合わせ → /proposal.html

Copyright:
「© 2026 神奈川ナース転職 All Rights Reserved.」

Compliance Notes:
✕ NO「平島禎之」
✕ NO「はるひメディカルサービス」
✕ NO personal email or phone
✓ Company name only
✓ Links to legal docs (noindex/nofollow)
```

**Visual Design**:
- Background: Dark gray or light gray (contrast footer from content)
- Text: Small (12px), muted color
- Spacing: Adequate padding (mobile-friendly)
- Link colors: Subtle, underline on hover

**Technical Notes**:
- Footer links marked with `rel="noindex, nofollow"`
- Policy pages not in sitemap
- No tracking pixel in footer (Meta Pixel in header)

**Design Decisions**:
- Clean footer (no logo, no company history)
- Legal compliance only (no brand storytelling)
- NoFollow prevents SEO credit to policy pages

---

## DESIGN DECISIONS SUMMARY

### CTA Placement & Frequency

| CTA# | Section | Text | Style | Target |
|------|---------|------|-------|--------|
| 1 | Hero | TBD (primary) | Button (primary color) | Line add |
| 2 | Empathy | Soft (outline) | Link or secondary | Section 3 anchor |
| 3 | Robby | ロビーに相談する | Button (secondary) | Line add |
| 4 | Salary | あなたの給料、相場と比べてみませんか？ | Button (secondary) | Line add |
| 5 | Flow | この流れなら、大丈夫 | Link or outline | Section 11 anchor |
| 6 | Final CTA | ロビーに無料で相談する | Button (primary, XL) | Line add |

**Total**: 6 CTAs (matches Withmal structure)
**All**: Point to LINE friend addition (no forms, no email capture)

### Color & Typography Decisions

**Pending**: Final color decisions await hero image creation

**Guidelines**:
- Primary CTA button: Dominant brand color (high contrast)
- Secondary buttons: Light outline or secondary color
- Text: Dark gray on light bg, light gray on dark bg
- Links: Underline for clarity (mobile accessibility)
- Headings: Bold, 24px+ (SP readable)
- Body: Regular weight, 16px+ (SP readable)

### Responsive Design Constraints

**Mobile-first approach**:
- Base design: 480px max-width (portrait)
- No desktop version in Phase 1
- Landscape orientation: Not tested initially
- Tablets (iPad): Scale to 480px constraint

**Touch targets**:
- All buttons: Minimum 48px × 48px (mobile standard)
- Links: Minimum 44px height
- CTA buttons: 60px+ height for easy mobile tapping

### Content Priorities (per user feedback)

✅ **DO**:
- Emphasize AI differentiation (not just job matching)
- Show Kanagawa-specific market data
- Robby as personality throughline
- Factual salary statistics only
- HelloWork data quality (filtered to full-time RN)

❌ **DON'T**:
- Show HelloWork source explicitly (reference value only)
- Mention "平島禎之" or corporate details
- Use heavy "転職" language (prefer "働き方", "お給料チェック")
- Make salary promises (fraud risk)
- Show N-count < 5 as specific values
- Create fake testimonials

---

## IMPLEMENTATION ROADMAP

### Phase 1: Design Review & Approval
1. Present 12-section design to user for feedback
2. Finalize Section 1 copy (hero subheader)
3. User creates hero images (PC 1500×837, SP 837×1500)
4. Confirm color palette

### Phase 2: Data & Backend
1. Complete `hellowork_salary_stats.py` (HelloWork → salary aggregate)
2. Generate `/data/salary_stats.json` (weekly cron)
3. Test salary data quality (N-count filtering)
4. Deploy updated worker.js (if needed for salary lookups)

### Phase 3: Frontend Development
1. Create `/lp/ad/index.html` (12-section structure)
2. Implement salary explorer UI (`salary_explorer.js`)
3. Test all 6 CTAs (analytics tagging)
4. Mobile responsive testing (480px, landscape)
5. Accessibility audit (WCAG 2.1 AA)

### Phase 4: Analytics & QA
1. Set up Meta Pixel tracking (PageView + Lead events)
2. Configure GA4 custom events (each CTA section)
3. Test LINE handoff code generation
4. User acceptance testing (ad flow → LINE placement)

### Phase 5: Launch & A/B Testing
1. Deploy `/lp/ad/index.html` to production
2. Update Meta Ads to point to new LP URL
3. Run 7-day A/B test (ad LP vs main HP)
4. Monitor bounce rate, conversion rate, CTA heatmap
5. Iterate based on user feedback

### Phase 6: Optimization (ongoing)
1. Collect real testimonials (post-first-placement)
2. Update Section 6 with actual voices
3. Monitor salary data quality (refine filters)
4. Update market statistics monthly
5. Rotate testimonials, refresh testimonial photos

---

## FILE REFERENCE

**Input Files** (to be created):
- Hero images: `lp/ad/hero-pc.jpg` (1500×837) and `lp/ad/hero-sp.jpg` (837×1500)
- Salary data: `data/salary_stats.json` (generated by hellowork_salary_stats.py)

**Output Files** (to be created):
- Main LP: `/lp/ad/index.html` (complete 12-section page)
- Salary UI: `/lp/ad/salary_explorer.js` (interactive explorer)
- Styles: `/lp/ad/ad-lp-styles.css` (mobile-optimized, 480px max)

**Configuration**:
- Meta Ads: Update destination URL to `https://quads-nurse.com/lp/ad/`
- GA4: Create custom events for each CTA section
- LINE: Ensure LINE_ADD_URL is in `.env` and deployed to worker.js

---

## APPROVAL CHECKLIST

- [ ] User confirms 12 sections are correct structure
- [ ] User approves Section 1 copy & subheader
- [ ] User provides hero images (PC + SP)
- [ ] Design team approves color palette
- [ ] Data team confirms salary_stats.json is ready
- [ ] QA team verifies mobile responsiveness (480px)
- [ ] Analytics team sets up GA4 events
- [ ] Meta Ads team tests LINE handoff flow
- [ ] Final user acceptance testing complete
- [ ] Deploy to production

---

## APPENDIX: WITHMAL REFERENCE LINKS

**Source**: https://withmal-hd.co.jp/withmal-recruit/

**Key Features Copied**:
1. Hero → Empathy → Character → Market Data → Flow → FAQ → Final CTA
2. 6 CTA repetitions throughout
3. LINE-only conversion (no forms)
4. Section 3: Character introduction (獣医師向け Withmal = AI agent in our case)
5. Section 4: Region-specific job carousel (Withmal) = salary explorer (ours)
6. Section 9: Application flow diagram (4 steps)

**Adaptation Notes**:
- Withmal is 11 sections → We extended to 12 (added explicit fee structure)
- Withmal: "求める人材" (talent profile) → Ours: "3つのない" (differentiator)
- Withmal: "会社紹介" → Ours: "ロビー登場" (personality-driven)
- Withmal: "1日スケジュール" → Ours: "マーケットデータ" (market proof)

---

**Document Version**: 1.0
**Last Updated**: 2026-03-26
**Next Review**: After user approval
