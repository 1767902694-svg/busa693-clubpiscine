---
name: interview-prep
description: "Interview Prep -- Generate practice questions, talking points, and mock interview sessions for the BUSA 693 individual final interview (15% of academic grade)."
argument-hint: "[team-member-name or topic]"
allowed-tools: Read Grep Glob
---

# Interview Prep -- BUSA 693 Final Individual Interview

You are helping prepare a team member for their 1-hour final interview with professors and coaches. The interview evaluates whether each student deeply understands the entire project and can independently explain and defend it.

Preparing for: **$ARGUMENTS**

## Interview Format
- 1-hour meeting with the whole team
- Team reviews executive summary and describes individual contributions
- Professors ask for significant technical explanations
- Professors question decisions and assumptions made
- Individual assessment -- each person is graded independently

## Rubric (4 criteria, 25% each)

### 1. Importance and Value of Capstone to Clients (25%)
**What they're testing**: Can you articulate WHY this project matters to Club Piscine?
- Use client-specific terminology (not generic consulting speak)
- Give at least one concrete example of value delivered
- Reference specific stakeholders and their needs

**Key talking points for Club Piscine**:
- $3.14M marketing spend with no channel-level measurement -> now optimized with 29.4% revenue lift
- Manual e-commerce reporting across 6 domains -> automated Power BI dashboards
- No demand forecasting for 287 store-division groups -> 21.2% wMAPE (vs 47.2% naive baseline)
- Franchise network needs inventory planning support for seasonal business

### 2. Knowledge of Project Details (25%)
**What they're testing**: Can you accurately describe data sources, architecture, modeling, UI, and explain decisions?

**Data sources**: 68 Power BI slice exports, Open-Meteo weather API (5 cities), python-holidays (QC+ON), Table_Magasins.xlsx
**Architecture**: Azure Container Apps, medallion architecture (bronze/silver/gold), automated pipelines
**Modeling decisions to defend**:
- Why LightGBM over XGBoost/Prophet for UC4? (Global model handles 287 groups, MAE objective, early stopping)
- Why direct revenue model instead of units x price? (Price-per-unit swings with product mix, produces NaN)
- Why Bayesian MMM for UC1? (Handles multicollinearity in media channels, probabilistic framework)
- Why single global model instead of tiered? (Deprecated approach only covered 5.9% of groups)
- Why walk-forward CV? (Respects temporal ordering, tests across all seasons)

**Assumptions to state**:
- Weather data from 5 representative cities covers 27 store locations
- 125 weeks of history sufficient for seasonal patterns
- Store regroupments (CP77->CP07, CP100->CP10) don't distort patterns
- Lag warmup period (4 weeks) is adequate

### 3. Capstone Connection to Business Context (25%)
**What they're testing**: Can you link features to specific KPIs and business objectives?

**Pain point -> Solution mapping**:
| Pain Point | Solution Feature | Business KPI |
|-----------|-----------------|-------------|
| No channel-level ROAS measurement | Bayesian MMM with channel decomposition | Marketing ROI, Revenue per channel |
| Manual e-commerce reporting | Automated Power BI dashboards (6 domains) | Time saved, Decision speed |
| No demand forecasting | LightGBM 4-week ahead predictions | Inventory accuracy, Stockout reduction |
| Seasonal demand volatility | Weather-integrated features, seasonal models | Summer 12% error vs 47% naive |
| Franchise network coordination | Store-level forecasts with confidence intervals | Supply chain planning accuracy |

### 4. Overall Understanding and Individual Contribution (25%)
**What they're testing**: Do you own your work? Can you claim at least one complex element?

## Team Member Profiles (for targeted prep)

| Member | Role | Should claim ownership of |
|--------|------|--------------------------|
| Tab Alkhalidi | Lead/Strategist | Overall project architecture, UC1 MMM model, UC4 forecasting model, team coordination |
| Saffee Raza | UX/UI | E-commerce dashboard design, user adoption strategy |
| Pranav Kalra | UX/UI | Dashboard UX rationale, stakeholder workflow mapping |
| Lorena Preciado | Architect | Azure infrastructure, container deployment, scalability design |
| Angela Cheng | Architect | Data flow design, UC4 pipeline architecture |
| Sine Raoul | Modeler | Model validation, feature engineering support |

## Practice Question Bank

### Warm-up Questions
1. In your own words, what does Club Piscine do and why did they need this project?
2. Walk me through the three solutions at a high level.
3. What is your role on the team and what did you personally build?

### Technical Deep-Dives
4. Explain how the demand forecasting model works. What features does it use and why?
5. Why did you choose LightGBM over other algorithms? What alternatives did you test?
6. How do you handle the fact that some store-division combinations have very low volume?
7. Walk me through the feature engineering pipeline. Which features matter most and why?
8. How does the weather data integration work? Why those 5 cities?
9. Explain the walk-forward cross-validation approach. Why not a simple train/test split?
10. What are the confidence intervals telling us? How are they generated?

### Architecture Questions
11. Walk me through the data flow from raw data to final forecast.
12. Why Azure Container Apps? What alternatives did you consider?
13. How would this scale if Club Piscine opens 10 more stores?
14. What happens when the model needs retraining?

### Business Value Questions
15. If you were the CFO, would you trust these forecasts? Why or why not?
16. What's the ROI of implementing this forecasting system?
17. How does the 29.4% marketing revenue lift translate to dollars?
18. Which stakeholder benefits most from which solution?

### Tough/Curveball Questions
19. What didn't work? What approaches did you try and abandon?
20. If you had 6 more months, what would you improve?
21. Your winter wMAPE is 26.4% -- is that good enough for inventory decisions?
22. The CI coverage is 86.9% vs your 90% target -- what does that mean?
23. How do you handle model drift after deployment?
24. What happens if the weather API goes down?

## How to Use This Skill

When invoked with a team member's name:
1. Read CLAUDE.md and relevant notebooks to ensure technical accuracy
2. Generate a personalized set of 10-15 practice questions based on their role
3. For each question, provide a model answer that references specific numbers, decisions, and files
4. Flag any areas where the member's knowledge might be thin
5. Suggest 3 "power moves" -- impressive technical details they can proactively mention

When invoked with a topic:
1. Generate deep-dive questions on that topic
2. Provide comprehensive answers with specific references
3. Anticipate follow-up questions the professor might ask
