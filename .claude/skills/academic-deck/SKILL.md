---
name: academic-deck
description: "Academic Deck -- Build the 30-slide final academic submission deck (35% of academic grade, 60% of course). Graded by professors on technical depth, architecture maturity, documentation, and video integration."
argument-hint: "[section or deliverable to work on]"
allowed-tools: Read Grep Glob Agent WebSearch
---

# Academic Submission Deck -- Club Piscine Capstone

You are helping build the **academic** submission deck. This is NOT the client presentation. The audience is **professors** who grade on technical rigor, documentation quality, architecture maturity, and alignment across deliverables. They read body content fully and reference exec summaries heavily.

Working on: **$ARGUMENTS**

## Key Constraints
- Max **30 slides** body + unlimited appendix
- Deck is **35% of the academic grade** (academic submission = 60% of course)
- Other academic deliverables: exec summary (15%), videos (20%), interview (15%), synthesis (15%)
- Two grading lenses (Explanation + Build) but rubric says: "You don't need to divide into explanation and build sections. Organize for optimal format."
- Must reference video assets from slides
- Must include future state architecture

## Reference Files
- Full academic rubric: See [rubrics.md](rubrics.md) (section: "ACADEMIC SUBMISSION RUBRIC")
- Professor M05 guidance: See [prof-guidance.md](prof-guidance.md)
- Coach structural feedback: See [coach-feedback.md](coach-feedback.md)
- Technical docs: Read `CLAUDE.md` at project root for UC4 details
- Client pain points: Read `Unknown.pdf`
- Current draft: Read `Capstone_Presentation.pdf`
- UC4 outputs: `use_case_4_forecasting/data/processed/nb05_*.csv` and `nb07_*.csv`
- UC4 figures: `use_case_4_forecasting/reports/figures/`

## Academic Deck Rubric (what professors grade)

| Criteria | Weight | What earns top marks |
|----------|--------|---------------------|
| Strategy / Value Proposition | 15% | Industry overview, ROI quantified, external data, benefits linked to outcomes |
| **Analytic Modeling** | **30%** | Robust data prep, creative models, automated validation, clear documentation, assumptions stated, video links |
| **Solution Architecture** | **30%** | Solves issues, scalability + automation + data flow, future state + evolution, justified tech, diagrams, **deployment-ready** |
| User Adoption | 25% | UI/UX with justification, technical sophistication, aesthetics, stakeholder focus, video support |

**Critical difference from client deck**: Professors want to see methodology, documentation, assumptions, validation, and future-state architecture. The client wants to see results and demos.

## Deck Section Allocation (from rubric ranges)

| Topic | Min % of slides | Max % | Approx slides (of 30) |
|-------|----------------|-------|----------------------|
| Strategy / Value Prop | 15% | 25% | 4-8 |
| Analytic Modeling | 25% | 50% | 8-15 |
| Solution Architecture | 20% | 40% | 6-12 |
| User Adoption | 15% | 35% | 4-10 |

These overlap -- organize for optimal flow, not rigid sections.

## Agreed Academic Deck Structure

| # | Slide | Rubric Area | Video Reference? |
|---|-------|-------------|-----------------|
| 1-2 | Title, Team | -- | -- |
| 3 | Club Piscine business context | Strategy/VP | -- |
| 4 | Current operating environment (3-column) | Strategy/VP | -- |
| 5 | Value proposition (3-column mirror) | Strategy/VP | -- |
| 6-8 | Architecture Overview, Data Flow/Automation, Future State | **Architecture (30%)** | Yes -- architect videos |
| 9-11 | Marketing Spend Optimization (problem, model, results) | **Modeling (30%)** | Yes -- strategist video |
| 12-14 | E-Commerce Dashboards (problem, build, demo) | Modeling + **Adoption (25%)** | Yes -- UX video |
| 15-18 | Demand Forecasting (problem, model, results, demo) | **Modeling (30%)** | Yes -- modeler video |
| 19 | Adoption summary -- who uses what | **Adoption (25%)** | Yes -- UX video |
| 20 | Limitations & Next Steps | Architecture (future state) | -- |
| 21 | Video Asset Index | Synthesis | -- |
| 22+ | Appendix (unlimited) | Referenced from body | -- |

## Three Solutions (NEVER say UC1/UC2/UC4)

1. **Marketing Spend Optimization** -- Bayesian MMM, 7 channels, +29.4% media-driven revenue
2. **E-Commerce Performance Dashboards** -- Automated Power BI across 6 domains
3. **Demand Forecasting** -- LightGBM, 287 store-division groups, 21.2% wMAPE vs 47.2% naive

## What Professors Are Looking For (by section)

### Strategy / Value Prop (15%)
- Comprehensive industry/market overview with Club Piscine specifics
- Clear explanation of the solution developed
- Strategic relevance: industry context, pain points, and ROI
- External data sources explored AND used (weather, holidays, etc.)
- Benefits **quantified** and linked to client outcomes
- User scenarios that support claims

### Analytic Modeling (30%) -- HIGHEST WEIGHT
- Robust data preparation, transformation, cleansing (show the work)
- Data used is relevant -- justify data choices
- **Robust AND creative** model approaches (not just standard)
- Automated testing and validation incorporated
- **Clear explanation** of how each model works
- **Clear documentation** supporting model development
- Assumptions **clearly stated and supported**
- **Link modeling slides to video assets** (explicitly)

### Solution Architecture (30%) -- HIGHEST WEIGHT (tied)
- Project clearly solves key client issues
- Considers data flow, scalability, and automation
- Future state with **technical evolution** path (how project grows after implementation)
- Technology choices **creative, justified, and aligned** with client needs
- Includes diagrams/visuals
- Complex sections supported with **video assets**
- **Architecture sufficiently mature for immediate industry-level deployment**

### User Adoption (25%)
- Strong focus on user needs, UI/UX design, stakeholder engagement
- **Description AND justification** of UX/UI design choices
- Technical sophistication considered for adoption
- Aesthetics and creativity leveraged
- Stakeholders taken into consideration during development
- Video assets support stakeholder buy-in

## Mandatory Rules

### From Professor (M05)
1. Every build component answers: **"why is this useful to the solution?"**
2. Tangible, client-specific examples everywhere
3. Both **context** (revenue sizing, industry) AND **content** (model results, validation)
4. Client-specific references -- no generic external quotes
5. Section consistency: Model <-> Architecture <-> UX <-> Value Prop cycle -- update one, update all
6. Future state: model drift, data drift, root cause analysis, monitoring
7. Pain points map across all 4 categories (Strategy, Modeling, Architecture, UXUI)

### From Coach
1. Current state BEFORE value prop
2. No section dividers -- waste slide count
3. Frame pain points as "operating environment," not criticism
4. Numbers accurate and attributed to correct solution
5. No footers

### Academic-Specific Requirements
- **Must reference video assets from modeling and architecture slides**
- Architecture must show **future state and technical evolution**
- Architecture must be **deployment-ready** (not conceptual)
- Model documentation must be clear enough to reproduce
- Assumptions explicitly stated with supporting rationale
- Appendix referenced from body slides for technical detail

## Cross-Deliverable Alignment (Synthesis 15%)

The academic deck doesn't exist in isolation. When writing slides, ensure consistency with:
- **Executive Summary** (1 slide) -- messaging must match deck
- **Video Assets** -- slides must explicitly reference which videos support which sections
- **Supplementary Files** -- appendix should point to code, notebooks, data files
- **Interview answers** -- what's on the slides must match what team members will say

## When Generating Slide Content

1. **Read the data first** -- check CLAUDE.md, model CSVs, figures for real numbers
2. **Write for professors** -- show methodology depth, justify decisions, document assumptions
3. **Include for each slide**: Title, key content, talking points, rubric criteria addressed, video reference (if applicable)
4. **Show your work**: Data prep steps, feature engineering rationale, model selection process, validation results
5. **Flag gaps** rather than fabricating content
6. **Cross-reference**: Note which other sections/deliverables must stay consistent
