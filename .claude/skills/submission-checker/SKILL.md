---
name: submission-checker
description: "Submission Checker -- Validate all BUSA 693 deliverables against rubric requirements. Checks completeness, file organization, and rubric alignment for both client and academic submissions."
argument-hint: "[client|academic|all]"
allowed-tools: Read Grep Glob Bash
---

# Submission Checker -- BUSA 693 Deliverables Validator

Validates that all required deliverables are complete, properly formatted, and aligned with rubric criteria.

Checking: **$ARGUMENTS**

## How to Run

1. Scan the project directory for all deliverable files
2. Check each item against the requirements below
3. Output a checklist with PASS / FAIL / MISSING for each item
4. Flag any rubric criteria that lack supporting content in the deliverables
5. Suggest specific actions to fix any gaps

## Client Presentation Checklist (30% of grade, due April 20-26)

### Slide Deck
- [ ] Slide count <= 24 (body) + appendix clearly separated
- [ ] All 8 storyboard sections present: Exec Summary, Value Prop, Current User Journey, Use Cases, Data Prep, Analytics & Demo, Solution Architecture, New User Journey
- [ ] At least 1 live demo planned and rehearsed
- [ ] No section divider slides wasting count
- [ ] No footers on slides
- [ ] All 3 solutions represented (Marketing Optimization, E-Commerce Dashboards, Demand Forecasting)
- [ ] Never refers to "UC1/UC2/UC4" -- uses business titles
- [ ] Current state comes BEFORE value proposition
- [ ] Each use case has max ~3 slides
- [ ] Numbers are accurate and attributed to correct solution
- [ ] Submitted to myCourses by deadline

### Rubric Coverage (check slide content addresses each criterion)
- [ ] Pain points clearly defined and aligned (7.5%)
- [ ] Company/industry context integrated (7.5%)
- [ ] Value prop clear and believable (12.5%)
- [ ] KPIs/models address pressing problem (5%)
- [ ] KPIs/models thorough + unique + live demo (20%)
- [ ] Architecture practical short- and long-term (12.5%)
- [ ] Stakeholder analysis + adoption strategy (12.5%)
- [ ] Flow/style/recommendations engaging (10%)
- [ ] Q&A prep done, team balanced (12.5%)

### Presenter Assignments
- [ ] All 6 team members have assigned sections
- [ ] Presentation rehearsed with timing check (<=45 min)
- [ ] Q&A anchor designated for tough questions

---

## Academic Submission Checklist (60% of grade)

### Zip 1: Core Deliverables
- [ ] **Executive Summary** (1 slide, using template)
  - [ ] Project context (10%): Industry relevance, key drivers, pain points
  - [ ] Solution overview (40%): Visual element (screenshot), value drivers, modelling, KPI, UI/UX, architecture
  - [ ] Solution build & analysis (40%): Key elements of build, data/analysis review
  - [ ] Design & clarity (10%): Professional, not overcrowded
- [ ] **Final Solution Deck** (max 30 body slides + appendix)
  - [ ] Strategy/Value Prop content (15%): Industry overview, ROI, external data, quantified benefits
  - [ ] Analytic Modeling content (30%): Data prep, creative models, validation, documentation, assumptions, video links
  - [ ] Solution Architecture content (30%): Solves issues, scalability, future state, diagrams, deployment-ready
  - [ ] User Adoption content (25%): UI/UX justification, sophistication, aesthetics, stakeholder consideration
  - [ ] Important appendices referenced from body slides
  - [ ] Never uses "UC1/UC2/UC4" -- uses business titles
- [ ] **Team Project Contribution file** (1 Excel template)

### Zip 2: Supplementary Files
- [ ] All supplementary files present (code, Excel, notebooks, etc.)
- [ ] Well-organized folder structure with clear labels
- [ ] Includes: Model versions, wireframe iterations, architecture diagrams, data files
- [ ] UC4 notebooks: NB01 (EDA), NB02 (Weather), NB03 (Features), NB05 (Units), NB07 (Revenue)
- [ ] UC4 output CSVs present in data/processed/
- [ ] UC4 figures present in reports/figures/

### Zip 3: Video Assets
- [ ] Minimum 1 video per role (6 team members = at least 4 roles covered)
- [ ] Each video 2-4 minutes (<=4 min hard limit)
- [ ] Videos complement slides, not replace them
- [ ] Focus on complex aspects hard to explain in slides
- [ ] Professional delivery, clear audio/visuals
- [ ] Key elements: modeling explanation, architecture walkthrough, dashboard demo, data pipeline

### Cross-Deliverable Alignment (Synthesis 15%)
- [ ] Messaging consistent across exec summary, deck, videos, supplementary files
- [ ] Technical rigour consistent across all deliverables
- [ ] Strategic/stakeholder relevance maintained throughout
- [ ] Professional formatting and clear file organization
- [ ] Video assets referenced from deck slides (slide 21 or inline)

### Interview Readiness
- [ ] Each team member can explain full project scope
- [ ] Each member can articulate client value with examples
- [ ] Each member can describe data, architecture, modeling, UI
- [ ] Each member can connect project to business KPIs
- [ ] Each member claims ownership of at least 1 complex element

---

## Automated Checks (run these)

```
# Check UC4 output files exist
ls use_case_4_forecasting/data/processed/nb05_*.csv
ls use_case_4_forecasting/data/processed/nb07_*.csv

# Check figures exist
ls use_case_4_forecasting/reports/figures/ | wc -l

# Check notebooks exist
ls use_case_4_forecasting/notebooks/*.ipynb

# Check presentation files
ls *.pdf *.pptx 2>/dev/null
```

## Output Format

Present results as a table:

| Item | Status | Notes |
|------|--------|-------|
| Exec Summary | PASS/FAIL/MISSING | details |
| ... | ... | ... |

Then: **Priority fixes** (ordered by grade impact) and **Quick wins** (easy to fix, moderate impact).
