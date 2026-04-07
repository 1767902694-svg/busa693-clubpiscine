---
name: client-deck
description: "Client Deck -- Build the 24-slide Club Piscine client presentation (30% of grade). Scored by client on a scorecard. Focus on results, demos, and the sell."
argument-hint: "[section or slide to work on]"
allowed-tools: Read Grep Glob Agent WebSearch
---

# Client Presentation Deck -- Club Piscine

You are helping build the **client-facing** presentation. This is NOT the academic deck. The audience is Club Piscine stakeholders who will score you on a client scorecard. They care about **results, adoption, and business impact** -- not methodology depth.

Working on: **$ARGUMENTS**

## Key Constraints
- Max **24 slides** body + unlimited appendix
- **45 min** presentation + **15 min Q&A**
- At least **1 live demo** required
- All 6 team members must present equally
- **Due: April 20-26, 2026** (30% of course grade)
- Graded by client via scorecard, submitted to professor for finalization

## Reference Files
- Full client rubric: See [rubrics.md](../academic-deck/rubrics.md) (top section: "CLIENT PRESENTATION RUBRIC")
- Professor storyboard & tips: See [prof-guidance.md](../academic-deck/prof-guidance.md)
- Coach structural fixes: See [coach-feedback.md](../academic-deck/coach-feedback.md)
- Technical details for accuracy: Read `CLAUDE.md` at project root
- Client's own pain points: Read `Unknown.pdf`
- Current draft: Read `Capstone_Presentation.pdf`

## Client Scorecard Rubric (what the client scores you on)

| Criteria | Weight | What earns top marks |
|----------|--------|---------------------|
| Analytic Issues / Pain Points | 7.5% | Clearly defined, aligned with CLIENT needs |
| Company/Industry Context | 7.5% | Consistently integrates relevant CP insights |
| Value Prop Clarity & Believability | **12.5%** | Benefits clearly communicated, convincingly justified |
| Effectiveness of KPIs / Models | 5% | Directly address a pressing organizational problem |
| Quality of KPIs / Models / Demos | **20%** | Thorough, unique. Live demo clearly illustrates accurate results |
| Architecture Insightfulness & Realism | **12.5%** | Practical, useful short- and long-term |
| Stakeholder/User Analysis & Adoption | **12.5%** | Clear analysis, compelling adoption strategy |
| Presentation Flow & Recommendations | 10% | Well-structured, engaging, persuasive |
| Q&A Performance & Team Balance | **12.5%** | Confident, well-balanced participation |

**Total: 100%**. Heaviest: KPI/Model/Demo quality (20%), then VP + Architecture + Adoption + Q&A (12.5% each).

## Professor's Storyboard (follow this flow)

| # | Section | Focus | Approx Slides |
|---|---------|-------|---------------|
| 1 | Executive Summary | Templated, high-level | 1 |
| 2 | Value Proposition | Quantitative + qualitative benefits | 1-2 |
| 3 | Current User Journey | Pain points linked to objectives | 1-2 |
| 4 | Use Cases | How each solution solves the problem | 9 (3 per UC) |
| 5 | Data Prep | Brief discussion only | 0-1 |
| 6 | Analytics & Demo | KPIs, diagnostics, predictions, LIVE DEMO | 3-4 |
| 7 | Solution Architecture | Current state, production, future | 2-3 |
| 8 | New User Journey | Highlight solution benefits, adoption | 1-2 |
| - | Appendix | Supplementary -- use in Q&A | unlimited |

## Three Solutions (NEVER say UC1/UC2/UC4)

1. **Marketing Spend Optimization** -- Bayesian MMM, 7 channels, +29.4% media-driven revenue
2. **E-Commerce Performance Dashboards** -- Automated Power BI across 6 domains
3. **Demand Forecasting** -- LightGBM, 287 store-division groups, 21.2% wMAPE

## Key Stakeholders (your audience)
- **Veronique Dion** -- Marketing Director (cares about: channel ROAS, budget allocation)
- **Marie-Pier Theberge** -- E-commerce & Digital Marketing Director (cares about: dashboard usability, reporting speed)
- **Michele Belanger** -- Data Manager (cares about: infrastructure, data pipeline reliability)
- **Franchisee Network** -- Store operators (care about: inventory accuracy, demand visibility)

## Presenter Assignments

| Member | Role | Presents |
|--------|------|----------|
| Tab Alkhalidi | Lead | Opening, Marketing Optimization, Demand Forecasting, Closing |
| Saffee Raza | UX/UI | E-Commerce Dashboards, adoption |
| Pranav Kalra | UX/UI | Adoption, design rationale |
| Lorena Preciado | Architect | Architecture, Azure infrastructure |
| Angela Cheng | Architect | Data flow, UC4 architecture |
| Sine Raoul | Modeler | Supports modeling slides |

## Mandatory Rules for Client Deck

### Framing (coach feedback)
- **Current state BEFORE value prop** -- establish baseline, then show improvement
- Frame pain points as "operating environment," NEVER as criticism
- Use Club Piscine's own language from their project proposal
- Don't deep-dive methodology in value prop -- save for use case sections

### Content (professor guidance)
- Every build component must answer: **"why is this useful to the solution?"**
- Give client-specific examples everywhere -- never generic
- Numbers must be accurate and attributed to the correct solution
- Connect pain points across Strategy, Modeling, Architecture, UXUI
- Define future state briefly (model monitoring, scaling)

### Structure (coach feedback)
- **No section divider slides** -- they waste slide count
- **No footers** on any slides
- Max **3 slides per use case** (10-11 total across all 3)
- De-seasonalization and Ridge regression are UC1's most impressive aspects -- highlight
- Pipeline/architecture details too granular? Focus on model type, accuracy, UI

### Live Demo
- At least 1 required (rubric mandate)
- If demoing multiple UCs, do ALL or just 1 well -- inconsistent quality looks worse
- Best candidates: UC4 web-based forecast tool, UC2 Power BI dashboard
- Rehearse to avoid technical failures mid-presentation
- Screenshots as backup for other use cases

### Q&A Prep
- Cover 5 questions > 2 -- keep answers concise
- Share answer-time equally among all 6 members
- Designate an "anchor" for tough/unexpected questions
- Prep for: "What would you do differently?", "How does this scale?", "What's the ROI?"
- Be ready if NO questions -- have topics to proactively discuss

## When Generating Slide Content

1. **Read data first** -- check CLAUDE.md, CSVs, figures for accurate numbers
2. **Write for the client audience** -- business language, results over methodology, impact over process
3. **Include for each slide**: Title, key message, talking points, which team member presents
4. **Flag if content is missing** rather than fabricating
5. **Keep slides rich but easy to follow** -- clients care about results, not process/proofs
