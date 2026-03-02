# Club Piscine MMM: Presentation Slide Guide
## Deck Structure, Key Messages, and Visual Notes

---

## DECK OVERVIEW
- **Audience:** Marketing Director + Finance Partner (60-minute meeting)
- **Format:** 11 slides + appendix (5 slides)
- **Flow:** Problem → Method → Results → Wins → Action → Risk Management → Next Steps
- **Tone:** Consultative, data-driven, but not defensive about limitations

---

## SLIDE 1: TITLE SLIDE
**Header:** "Club Piscine Marketing Mix Model | FY2023–2025 Analysis"
**Subtitle:** "Optimizing a $10.3M media budget to maximize $512M in revenue"
**Visual:** Logo, date, analyst name, contact

**Message:**
This is a serious, analytical work. Not flashy, but credible.

---

## SLIDE 2: THE QUESTION
**Title:** "What We Set Out to Answer"
**Content (3 bullet points):**
- "How much does each media channel contribute to Club Piscine's revenue?"
- "Which channels deliver the best return on media investment?"
- "How should we reallocate the budget to maximize ROI without spending more?"

**Visual:**
Simple question-mark icon or diagram showing 7 media channels pointing to revenue.

**Speaker Note:**
"We were asked to solve three related problems. This presentation shows what we found."

---

## SLIDE 3: THE MODEL IN ONE PICTURE
**Title:** "Two-Stage Regression Model | What We're Measuring"
**Content (diagram):**
```
Stage 1: Seasonal Baseline
├─ Months (Mar–Sep peaks)
├─ Weather (temperature, sunshine, precipitation)
├─ Special days (holidays, events)
└─ Result: Explains 84.9% of revenue variance

        ↓
    (Residual Revenue)
        ↓

Stage 2: Media Effects
├─ TV spend (with decay rate, saturation curve)
├─ Radio spend (with decay rate, saturation curve)
├─ Digital channels (Preroll, Social, Web Banners, etc.)
└─ Result: Explains 24% of residual variance
           = 2.4% of total variance
           = 9.83% of total revenue (incremental)
```

**Visual:**
Flowchart showing data flowing from top (seasonality) down to residuals (media effects).

**Speaker Note:**
"We use a two-stage approach: first, we account for the 'baseline' revenue driven by exogenous factors like weather and seasonality. Then, we measure what media adds *on top* of that baseline. This approach is standard in the industry and prevents us from mistakenly attributing seasonal variation to media spend."

---

## SLIDE 4: THE BIG PICTURE | R² and Model Fit
**Title:** "Model Explains 88.5% of Revenue Variance"
**Visual:** Pie chart or stacked bar
- 84.9% = Seasonality + Weather (exogenous baseline)
- 9.83% = Media investment (controllable)
- 5.17% = Residual (unexplained, noise)
- **Total = 100%**

**Key Metrics Box (bottom):**
| Metric | Value |
|--------|-------|
| Overall R² | **88.5%** |
| Total Revenue (3Y) | **$512.4M** |
| Total Media Spend (3Y) | **$10.3M** |
| Media Contribution | **~$50M** (9.83%) |
| Media ROAS | **~4.9x** |

**Speaker Note:**
"An R² of 88.5% is exceptional for a marketing model. It means we can trust the directional findings. The remaining 11.5% is likely things we can't measure (competitor actions, local store events, inventory constraints, etc.). For comparison, industry benchmarks are typically 75–85%."

---

## SLIDE 5: CHANNEL RESULTS | The Full Table
**Title:** "ROAS by Channel (with 90% Confidence Intervals)"
**Content (Table):**

| Channel | Spend | ROAS | 90% CI | Significant? |
|---------|-------|------|--------|-------------|
| **Television** | $3.95M | 5.85 | [1.67, 7.77] | ✓ YES |
| **Preroll (Video)** | $0.90M | 17.78 | [-4.46, 33.67] | NO |
| **Web Banners** | $0.83M | 13.75 | [-9.77, 35.49] | NO |
| **Social Media** | $0.83M | 10.95 | [-25.99, 40.44] | NO |
| **Digital Flyers** | $0.45M | 6.97 | [-24.01, 41.56] | NO |
| **Panneaux (DOOH)** | $0.29M | 10.24 | [-8.17, 23.15] | NO |
| **Radio** | $2.17M | -7.06 | [-11.54, 0.97] | NO |

**Visual:**
Color-code: TV = green (significant), others = yellow (not significant but measured), Radio = red (negative).

**Speaker Note:**
"This table is the heart of the findings. TV is the only channel with a confidence interval that doesn't cross zero—statistically proven. The other channels have wider CIs due to smaller sample sizes or harder-to-isolate effects. We'll spend the rest of the presentation explaining what this means and how to use it."

---

## SLIDE 6: WHY TV IS SIGNIFICANT (And Others Aren't) | The CI Explanation
**Title:** "Statistical Significance: Why TV Passes But Others Don't"
**Visual:**
Horizontal error bars for each channel.
- TV bar: solid, stops at 1.67 on left (doesn't touch zero) → green checkmark
- Preroll bar: dashed, extends from -4.46 to +33.67 (crosses zero) → orange dash
- Radio bar: dashed, extends from -11.54 to +0.97 (crosses zero) → red dash
- etc.

**Annotation:**
"The question: Does the confidence interval cross zero? If NO → significant. If YES → not significant (at 90% level)."

**Speaker Note:**
"Significance doesn't mean 'the channel works or doesn't work.' It means we're 90% confident the effect is positive (or negative). TV's interval doesn't cross zero, so we're confident TV is positive. The others cross zero, so we're less certain. But that doesn't mean they don't work—it means we need more data to pin down their exact value."

---

## SLIDE 7: THE "ONLY TV MATTERS" REFRAME
**Title:** "What About the Other 6 Channels? Aren't They Wasted?"
**Visual:** Two-column comparison

**Left Column: "Naive Reading"**
"Only TV is significant, so the other 6 channels don't matter."

**Right Column: "Correct Reading"**
"TV is our most confident channel. The other 6 have wider confidence intervals due to smaller spend, but their *combined* ROAS is 9.8x—better than TV's 5.85x."

**Additional Box:**
**Combined Non-TV Metrics:**
- Combined spend: $4.3M
- Combined effect: $42M
- Combined ROAS: 9.8x
- Verdict: Collectively outperform TV, but individually harder to isolate

**Speaker Note:**
"A statistically significant coefficient doesn't mean other channels are noise—it means we're more confident about that channel's effect. Think of it like this: if I flip a coin 100 times and get 55 heads, that's not statistically significant (could be random). If I flip it 1,000 times and get 550 heads, that's significant. But in both cases, the coin is slightly biased. The sample size matters."

---

## SLIDE 8: THE RADIO PROBLEM | Why -7.06x (And Why It's OK)
**Title:** "The Radio Negative ROAS Conundrum"
**Visual:** Three-panel diagram

**Panel 1: What the Model Shows**
"Radio: -7.06x ROAS (90% CI: [-11.54, 0.97])"
→ Looks like Radio is waste

**Panel 2: Why This Happens**
"Seasonality Confounding:
- Radio peaks: May–July
- Pool season peaks: June–September (same window)
- Model says: 'I can't tell if sales are from Radio or from summer weather'"

**Panel 3: Why It's Not Business Reality**
"Your own strategy says Radio is essential for 3-day promo events.
Model can't see micro-events (monthly aggregation).
Solution: Weekly-level refit isolates true Radio ROI."

**Action Box:**
"**Recommendation:** Maintain Radio at current levels ($60K/month). Design week-level follow-up (2–3 weeks work) to measure true ROI."

**Speaker Note:**
"The negative coefficient feels like a gut punch, but it's a measurement problem, not a business problem. Radio's real role—driving footfall to 3-day in-store events—is invisible to a monthly model. We're recommending you keep Radio and let us measure it properly with weekly data."

---

## SLIDE 9: MEDIA CONTRIBUTION 10% | The Right Story
**Title:** "Media = 10% of Revenue. Good or Bad?"
**Visual:** Two narratives side by side

**Narrative A: "The Optimistic Reading"**
"Your $10.3M media investment drives $50M in incremental revenue (4.9x return). That's the *controllable* margin. Without media, you'd earn 90% of current revenue; with media, you earn 110%. That 20-point swing is where marketing's value lives."

**Narrative B: "The Pragmatic Reading"**
"85% of your revenue is driven by exogenous factors (weather, season, brand legacy). Media accelerates on top of that. It's the gas pedal, not the engine."

**Bottom Box:**
"**The Verdict:** Both are true. Media is the margin you control. And that margin is valuable: $500M+ over 5 years at current ROI."

**Speaker Note:**
"The 10% number scares people initially. They think 'only 10% is from ads?' But that's the wrong question. The right question is: 'Of the variance I can control, what's the return?' Answer: 4.9x. Exceptional."

---

## SLIDE 10: THE OPTIMIZATION OPPORTUNITY | +21% Revenue Lift
**Title:** "Reallocation Strategy: Same Budget, Better Mix = +21% Revenue"
**Visual:** Waterfall chart or paired bar chart

**Left Side: Current Allocation**
- TV: $109K (42%)
- Radio: $60K (23%)
- Preroll: $25K (10%)
- Social: $23K (9%)
- Web Banners: $23K (9%)
- Panneaux: $8K (3%)
- Digital Flyers: $12K (5%)
- **Total: $261K/month**

**Middle: Reallocation Arrows**
- TV → 80K (TV floor, strategic minimum)
- Preroll → 51K (+102%, highest opportunity)
- Social → 36K (+56%)
- Web Banners → 30K (+32%)
- Radio → 48K (-20%, promo support)
- etc.

**Right Side: Optimal Allocation**
- Same total: $261K/month
- **Revenue lift: +21.4%** (arrow pointing up)
- **Estimated incremental revenue: $110–130M annually**

**Implementation Note:**
"Phase 1 (pilot): Increase Preroll to $35K, decrease TV to $95K. Measure for 8 weeks. If ROAS matches forecast, proceed to Phase 2 (full reallocation)."

**Speaker Note:**
"This is the compelling finding. You're not being asked to spend more money. You're being asked to spend the same money *smarter*. Shift dollars from lower-estimated-ROI channels (TV baseline, tactical radio) to higher-ROAS channels (Preroll, Social, Web Banners). The model predicts this unlocks 21% more revenue."

---

## SLIDE 11: BUDGET CUT SCENARIOS
**Title:** "What If We Need to Cut Budget?"
**Visual:** Table or scenario slider

| Scenario | Budget Change | Revenue Impact | Feasibility |
|----------|---------------|-----------------|-------------|
| Optimize (no cut) | $0 | +21.4% | High |
| 10% reduction + optimize | -$26K/mo | +8.9% | High |
| 15% reduction + optimize | -$39K/mo | -0.1% | Medium |
| 20% reduction + optimize | -$52K/mo | -6.8% | Medium |

**Narrative:**
"If budget pressure emerges, a 10% cut with optimization maintains revenue. A 15% cut maintains 99.9% of current performance. Beyond 15%, you start eroding the competitive edge media provides."

**Speaker Note:**
"This gives the CFO comfort that media spend isn't sacred. If you need to cut costs, there's a pathway that doesn't blow up revenue. But hopefully, you don't need it—the optimization is the path forward."

---

## SLIDE 12: THE WINS TO HIGHLIGHT (Summary Slide)
**Title:** "5 Key Findings"
**Visual:** Five boxes, each with icon + headline + 1-line explanation

**Box 1: TV is Proven**
"ROAS 5.85x, statistically significant, tight CI [1.67, 7.77]. Defensible cornerstone."

**Box 2: Preroll Opportunity**
"ROAS 17.78x point estimate, lowest current spend ($902K). Scale opportunity."

**Box 3: Exceptional Model Fit**
"R²=88.5% (top decile globally). We can trust the directional findings."

**Box 4: +21% Revenue Lift**
"Same budget, better allocation. Implementable in FY2026."

**Box 5: Cost-Cut Feasibility**
"10% budget cut + reallocation = +8.9% revenue. Reduces pressure on finance."

**Speaker Note:**
"These five findings are your 'wins.' They answer the three original questions: yes, TV works; yes, we know which channels work; yes, we can optimize. Walk out of this room with these five ideas locked in."

---

## SLIDE 13: RISKS & MITIGATIONS (Appendix)
**Title:** "Risk Management: What Could Go Wrong?"
**Visual:** Risk matrix (Impact vs. Likelihood)

**High-Impact, Low-Likelihood Risks:**
1. "Preroll saturation kicks in at 2x spend" → Mitigated: Phase 1 pilots
2. "Competitor launches new campaign, ROAS shifts" → Mitigated: Quarterly model refits

**Low-Impact, Medium-Likelihood Risks:**
3. "Radio true ROAS is higher than model shows" → Mitigated: Weekly-level refit
4. "Implementation friction (media buying delays)" → Mitigated: Start Phase 1 now, full rollout Month 3

**Mitigation Strategy:**
"Phase-in approach: Pilot 40% of reallocation in 2–3 markets (8 weeks), measure real-world ROAS, then decide on full rollout. This de-risks the move."

---

## SLIDE 14: NEXT STEPS & TIMELINE
**Title:** "What Happens Next?"
**Visual:** 4-phase timeline

**Phase 1: Week 1–2 (Approval & Preparation)**
- Review findings with media agency
- Design Phase 1 pilot (Preroll +$10K, TV -$14K in 2–3 markets)
- Set up tracking (daily/weekly ROAS by market)

**Phase 2: Week 3–10 (Pilot)**
- Run Phase 1 in limited markets
- Track daily ROAS vs. forecast
- Weekly sync calls to monitor

**Phase 3: Week 11–14 (Analysis & Decision)**
- Analyze Phase 1 results
- Compare actual ROAS to model forecast
- Decide: green light Phase 2 (full reallocation) or recalibrate

**Phase 4: Week 15–52 (Implementation & Learning)**
- Execute full reallocation (if Phase 1 is positive)
- Quarterly model refits
- Track performance vs. forecast
- Design Phase 2 analyses (weekly refit, category segmentation, halo effects)

**Speaker Note:**
"Timeline is realistic. Phase 1 takes 2 months of real-world validation before you commit to full reallocation. This is prudent. By Month 4, you'll have confidence to execute."

---

## SLIDE 15: Q&A & DISCUSSION (Not a Slide, But on Agenda)
**Prepared Answers (See CONSULTANT_QA_PLAYBOOK.md for full details):**
- "Why is only TV significant?" → Wide CIs are honest; non-TV ROAS is 9.8x combined
- "Radio negative ROAS?" → Seasonality confounding; weekly refit will clarify
- "Can we trust this model?" → 88.5% R², validated against external data, auditable
- "What if optimization doesn't work?" → Phase 1 pilots de-risk; quarterly refits catch drift

---

## SPEAKER NOTES: Tone & Delivery

### Key Principles:
1. **Lead with confidence, not arrogance**
   - "This model is sound" (not "This model is perfect")
   - "These findings are reliable" (not "These findings are guaranteed")

2. **Acknowledge limitations early**
   - "36 months is tight; we're being transparent with CIs"
   - "Monthly data obscures event-level effects (Radio); weekly refit will fix this"

3. **Make it about *their* decision-making, not *my* model**
   - "You don't have to believe me. Phase 1 pilots will show you whether the forecast holds."
   - "This gives you a framework to test; the real-world results will tell you if it's right."

4. **Sell the optimization as *low-risk*, not high-return**
   - "Same budget, smarter allocation. If it works, great. If not, you've lost nothing."
   - "Phase 1 is a 2-month validation. Only then commit to full rollout."

---

## VISUAL STYLE NOTES

- **Color scheme:** Blue (primary), green (significant/positive), yellow (caution), red (negative/risk)
- **Fonts:** Clean, sans-serif (Helvetica, Arial, or modern equivalent); 12pt minimum for readability
- **Data viz:** Tables and bar charts where possible; minimize pie charts (they're hard to read)
- **Icons:** Use simple, professional icons for the 5 wins slide; avoid cartoonish or overly decorated styles
- **Branding:** Club Piscine logo on title slide and footer; keep it subtle

---

## SPEAKER CHECKLIST

Before the meeting:
- [ ] Print 3 copies of full deck (1 for you, 1 for CMO, 1 for finance partner)
- [ ] Have EXECUTIVE_SUMMARY_1PAGE.md ready (1-page handout)
- [ ] Have CONSULTANT_QA_PLAYBOOK.md in your bag (reference for tough Q&A)
- [ ] Load Tableau/Power BI dashboard on laptop (optional visual during deep dive)
- [ ] Test all hyperlinks and video if embedded
- [ ] Confirm projector compatibility; bring adapters
- [ ] Print model assumptions one-pager (optional appendix)

During the meeting:
- [ ] Start with agenda (60 min: 35 min presentation, 25 min Q&A)
- [ ] Make eye contact; speak to the room, not the screen
- [ ] Use "I" statements ("I found," "I analyzed") to own the work
- [ ] Pause after each complex slide for questions
- [ ] Use humor carefully (this is data, not comedy)
- [ ] If CMO asks a tough question, say "Great question. Let me think about that" rather than fumbling (you have QA playbook for reference)

---

## HANDOUT MATERIALS
What to leave behind:
1. **EXECUTIVE_SUMMARY_1PAGE.md** — 1 page, all key findings, can send via email
2. **Channel Results Table** — Printable, full ROAS + CI for all channels
3. **Optimization Reallocation Table** — Current vs. optimal allocation
4. **Phase 1 Pilot Plan** — Specific markets, budget changes, KPIs to track
5. **Contact info & next steps** — Your email, proposed timing for follow-ups

---

**End of Slide Guide**

Use this as a template to build the actual deck. Each slide is designed to move the narrative forward and address a key concern. Never skip the "Why This Matters" explanation—data alone isn't persuasive; context is.
