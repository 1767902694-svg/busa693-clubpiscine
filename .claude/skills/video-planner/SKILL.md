---
name: video-planner
description: "Video Planner -- Plan and script video assets for BUSA 693 academic submission (20% of grade). Outlines content, timing, and key visuals for each role's 2-4 min video."
argument-hint: "[role or team-member-name]"
allowed-tools: Read Grep Glob
---

# Video Planner -- BUSA 693 Video Assets

You are helping plan video assets for the academic submission. Videos are worth **20% of the academic grade** (which is 60% of the course). Each role needs at least 1 video, 2-4 minutes, focused on complex aspects that are hard to explain in slides alone.

Planning for: **$ARGUMENTS**

## Rubric Summary

| Criteria | Weight | Good Performance |
|----------|--------|-----------------|
| Content Relevance | **60%** | Clearly complements slides. Explains complex aspects. Sparingly used, critically focused on key elements. |
| Technical Explanation | **20%** | Complex elements well-explained with visuals or examples. |
| Presentation Quality | **20%** | Professional delivery, clear audio/visuals, engaging, <=4 min, well-integrated. |

## Key Principles
- Videos **complement** slides, they don't replace them
- Focus on things that are **hard to explain in slides** (live demos, code walkthroughs, interactive dashboards)
- Use sparingly -- quality over quantity
- Each video should have a clear "this is what you should take away" message
- Can record what you will demo in the client presentation
- Can submit more than 1 video per role if desired

## Suggested Video Plan by Role

### Tab Alkhalidi -- Data Strategist & Team Lead
**Video 1: Marketing Spend Optimization Model Deep-Dive** (~3 min)
- 0:00-0:30 -- Problem framing: $3.14M spend, no channel-level ROAS measurement
- 0:30-1:30 -- Bayesian MMM methodology: de-seasonalization, adstock transformations, Ridge regression
- 1:30-2:30 -- Results walkthrough: channel decomposition, ROAS by channel, optimal allocation table
- 2:30-3:00 -- Key takeaway: 29.4% revenue lift from same budget, which channels to increase/decrease

**Video 2 (optional): Demand Forecasting Model** (~3 min)
- 0:00-0:30 -- Problem: 287 store-division groups, seasonal retail, no forecasting capability
- 0:30-1:30 -- LightGBM architecture: 71 features, walk-forward CV, quantile regression for CIs
- 1:30-2:30 -- Results: 21.2% wMAPE, seasonal breakdown, top features (show feature importance chart)
- 2:30-3:00 -- Key takeaway: model handles volume heterogeneity, summer at 12% error

### Saffee Raza -- UX/UI
**Video 1: E-Commerce Dashboard Demo** (~3 min)
- 0:00-0:30 -- Current pain: manual reporting across 6 domains, time-consuming, inconsistent
- 0:30-2:00 -- Live walkthrough of Power BI dashboards: sales, traffic, CWV, products, operations, customer service
- 2:00-2:30 -- Design decisions: why these KPIs, how stakeholders navigate
- 2:30-3:00 -- Key takeaway: hours of manual work replaced, consistent metrics across team

### Pranav Kalra -- UX/UI
**Video 1: User Adoption & Design Rationale** (~3 min)
- 0:00-0:30 -- Who are the users? (Veronique, Marie-Pier, Michele, franchisees)
- 0:30-1:30 -- UX design walkthrough: how each stakeholder's workflow is addressed
- 1:30-2:30 -- Design choices: accessibility, information hierarchy, decision-support focus
- 2:30-3:00 -- Key takeaway: adoption path from current manual processes to solution

### Lorena Preciado -- Solution Architect
**Video 1: Architecture & Infrastructure** (~3 min)
- 0:00-0:30 -- Current state: fragmented data, no automation, manual processes
- 0:30-1:30 -- Azure Container Apps setup: medallion architecture, container orchestration, data flow
- 1:30-2:30 -- Future state: scalability plan, monitoring, what happens when stores are added
- 2:30-3:00 -- Key takeaway: production-ready architecture that scales with business growth

### Angela Cheng -- Solution Architect
**Video 1: Data Pipeline & Automation** (~3 min)
- 0:00-0:30 -- Data challenge: 68 store slices, weather from 5 cities, holiday data
- 0:30-1:30 -- Pipeline walkthrough: UC4 5-step pipeline (Data Prep -> Weather -> Features -> Units Model -> Revenue Model)
- 1:30-2:30 -- Automation: how pipelines trigger, data validation, error handling
- 2:30-3:00 -- Key takeaway: end-to-end automated pipeline, no manual intervention needed

### Sine Raoul -- Modeler
**Video 1: Model Validation & Feature Engineering** (~3 min)
- 0:00-0:30 -- Challenge: 287 groups with different volumes, seasonal patterns, intermittent demand
- 0:30-1:30 -- Feature engineering deep-dive: weather derivatives, lag features, intermittency handling
- 1:30-2:30 -- Validation: walk-forward CV results (0.233 +/- 0.091 wMAPE), seasonal performance breakdown
- 2:30-3:00 -- Key takeaway: model robustly validated across all seasons, beats all baselines

## Script Template

When generating a script for a specific video:

```
VIDEO: [Title]
ROLE: [Team member]
DURATION: [X] minutes
COMPLEMENTS SLIDES: [Which slide numbers this video supports]

[TIMESTAMP] -- [Section title]
SHOW ON SCREEN: [What the viewer sees -- screenshot, code, dashboard, diagram]
SAY: "[Exact talking points]"
KEY TAKEAWAY: [What the viewer should remember]
```

## Recording Tips
- Record screen + voiceover (face optional but adds engagement)
- Use a clean desktop, close notifications
- Practice once before recording -- aim for natural, not scripted
- Highlight/annotate key areas on screen as you talk
- Keep a consistent volume and pace
- Export as MP4, reasonable quality (not 4K -- file size matters for submission)

## Quality Checklist Per Video
- [ ] <=4 minutes
- [ ] Complements specific slides (noted in script)
- [ ] Focuses on complex aspect hard to explain in slides
- [ ] Has clear "key takeaway" moment
- [ ] Audio is clear and professional
- [ ] Screen content is readable (font size, zoom level)
- [ ] No dead air or long pauses
- [ ] Introduces self and role at start
