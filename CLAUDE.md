# Club Piscine Marketing Mix Model (MMM)

## Use Case Definition

### Objective
Design a Marketing Mix Modeling (MMM) model to optimize media investment allocation and maximize sales and profitability. Specifically:
- Optimize advertising spending and budget allocation based on target groups and business objectives
- Analyze the impact of media investments (TV, radio, digital, social, display, SEM, etc.) on online and in-store sales
- Measure the effectiveness of traditional and digital marketing channels
- Recommend budget adjustments to maximize ROI

The ultimate objective is to provide management with a clear vision of the effectiveness and role of each marketing lever in order to: justify past investments, optimize the future mix, and make better strategic decisions.

### Classification
- **Category**: Middle-end, Mature
- **Type**: FE-DataDrivenDecisions, ME-Predictive
- **End Users**: Marketing Director and Internal Media Agency

### Pain Points
- Lack of clear visibility into the ROI of marketing channels (attribution problem)
- Media decisions are primarily based on experience or general trends, without solid analytical evidence
- Difficulty attributing sales to the right media investments (TV, radio, digital, etc.) versus in-store and online sales
- Technical complexity and lack of internal analytical resources to build an MMM

### Success Metrics / Deliverables
1. A **functional MMM model** (prototype in Python) integrating internal and external data
2. An **analysis report** highlighting:
   - The contribution of each media channel to sales
   - Seasonality and the impact of exogenous variables (weather, promotions, etc.)
   - Budget recommendations to improve ROI (e.g., a 10-15% reduction in the media budget for equivalent performance)
3. **Clear documentation** (code + methodology) to enable implementation by the internal team

### Required Data
- **Business performance data**: Sales (turnover, units sold, margins if possible), time-based data (weekly/daily), by product/category/region
- **Marketing and media spend**: Investments by channel (TV, radio, display, digital, social, search), value spent, impressions, GRPs, clicks
- **External data**: Weather data (weather feed), macroeconomic data (inflation, purchasing power, consumer indices), special events (holidays, sporting/local events, etc.)

### Academic Framing (from Professor Rob)
This problem is roughly in the category of **online optimization**: solve an optimization problem (maximize ROI) with data obtained from real-world information (historical sales data). Think of it as a two-step process:

1. **Step 1 — Estimate channel effectiveness**: How "effective" is a dollar in each channel at present.
   - "Effective" may have multiple measures, i.e. different customer groups
   - Effects may be non-linear (i.e., concave)

2. **Step 2 — Solve the optimization model**: Given goals, budget, aims, and dollar effectiveness, solve an optimization model.
   - Constraints may represent need to target different customer types or channels
   - Constraints would be budget as well
   - Objective coefficients would be spend effectiveness data

---

## Project Overview
- **Client**: Club Piscine — pool, spa, outdoor furniture & fitness retailer
- **Scope**: 42 stores across Quebec, Canada
- **Primary target**: Revenue ($), not units
- **Fiscal year**: November 1 → October 31 (FY2023 = Nov 2022 - Oct 2023)
- **Data span**: 3 fiscal years (FY2023-FY2025), 36 monthly observations
- **Total revenue (3Y)**: $512.4M
- **Total media spend (3Y)**: $10.3M ($284,931/month average)

## Notebook Pipeline
| NB | Name | Purpose | Key Output |
|----|------|---------|------------|
| 00 | Setup | Environment, dependencies, paths | requirements.txt |
| 01 | Data Audit | Raw data inspection, schema validation | interim preview CSVs |
| 02 | Data Cleaning | Store aggregation, fiscal year alignment, category consolidation | sales_clean.pkl |
| 03 | EDA | Exploratory analysis, distributions, correlations, seasonality | 15+ EDA figures |
| 04 | External Data | Weather features (sunshine, precipitation, days >25C) | external_weather.pkl |
| 05 | Feature Engineering | Adstock transformations, saturation functions, Fourier terms | sales_spend_weather.pkl (36x43) |
| 06 | Causal Inference | Ridge regression, LOOCV, bootstrap CIs, ROAS estimation | media_effectiveness_results.csv, saturation_curves.csv |
| 07 | Budget Optimization | Nonlinear optimization, scenario analysis, constrained allocation | mmm_optimization_results.csv, mmm_final_output.json |
| 08 | Bayesian MMM | PyMC-Marketing implementation (alternative model) | bayesian posteriors, comparison to Ridge |

## Data Sources
- **Sales**: `data/raw/Historical sales by store and by division for 2023-2024-2025.xlsx`
  - Sheet: "Ventes cumulatives par magasin", header=1
  - 6,336 weekly rows aggregated to 36 monthly rows
- **Budget**: `Budget_2023_.xlsx`, `Budget 2024`, `Budget 2025`
- **Tableau Medias**: `Recap_Tableau_Medias_2025.xlsx`
- **Weather**: Environment Canada via API (province-wide)

## Media Channel Groups (7 Consolidated)
1. **Television** — TV spots (brand building, early season)
2. **Radio** — Radio + Radio Numerique (tactical, regional, mid-season)
3. **Panneaux** — Panneaux + Panneaux et Affichages Numeriques / DOOH (commute-based awareness)
4. **Social_Media** — Facebook + Instagram + Pinterest + TikTok (targeting, growth)
5. **Preroll** — YouTube + Preroll premium / video content (highest ROAS, storytelling)
6. **Banniere_Web** — Premium Display + Google Ads + LaPresse + Brand content (mid-funnel)
7. **Circulaire_Digitale** — Digital flyers via Flipp, Reebee (conversion driver)
- **EXCLUDED**: Google Shopping, Programmatique, Audio et Podcast, Envois Postaux

## Product Categories (6, All Equal)
HT, CR, SP, ME&GA (combined `$-ME` & `$-GA`), FI, BQ
- `total_all_revenue` is the primary aggregate target
- Do NOT use separate `$-ME` and `$-GA` columns
- ALL 6 categories are treated equally — NO "main" vs "other" distinction

## Key Merge Patterns
- Sales `year` = fiscal year (no conversion needed)
- Budget `year` = fiscal year (no conversion needed)
- Both merge on `(year, month_num)` directly
- Calendar year: `calendar_year = year - 1 if month_num >= 11 else year`
- Weather uses calendar year → convert to fiscal year before merge

## Business Constraints (18 from Client)
See NB07, cell after `CLIENT_CONSTRAINTS` for full verbatim constraints, media strategy narrative, and classification table.

### Client Constraints Summary
| # | Constraint | Model Status |
|---|-----------|-------------|
| 1 | Structural media mix evolution (trad→digital shift) | Unmodeled Context |
| 2-5 | GRP/PEB comparability, target definitions, language | Not Applicable (model uses $ spend) |
| 6 | Impression quality variability | Partially Modeled (separate channel coefficients) |
| 7 | Traditional media spill effects | Unmodeled (may undervalue TV/Radio) |
| 8 | Digital precision & scale limits | Partially Modeled (saturation curves) |
| 9 | Creative execution unmodeled | Unmodeled (conflated with media efficiency) |
| 10 | Production vs media ratio (85/15) | Documented (spend data is media-only; production tracked separately) |
| 11 | Brand positioning & premium environments | Unmodeled (long-term brand building) |
| 12 | Strategic category visibility (40% furniture, 30% pools, 20% spas, 5% BBQ, 5% other) | **Optimizer Constraint** |
| 13 | Furniture as growth-led focus | **Optimizer Constraint** |
| 14 | Unobserved local store marketing | Unmodeled |
| 15 | Deliberate fitness overinvestment (off-season traffic) | **Optimizer Constraint** |
| 16 | Inventory/installation capacity constraints | **Optimizer Constraint** |
| 17 | Weather & regional climate variability | Partially Modeled (province-wide) |
| 18 | Competitive pressure (Trevi, Sima, big-box) | Unmodeled |

### Optimizer Constraints (Implemented in NB07)
- **Channel floors/ceilings**: TV $80-180K, Radio $30-90K, Panneaux $5-30K, Social $15-90K, Preroll $15-110K, Web Banners $20-80K, Digital Flyers $8-40K
- **Production ratio**: 85/15 documented but NOT applied as budget reduction (spend data is already media-only)
- **Traditional/digital mix**: 35-65% traditional (targeting ~50/50 equilibrium)
- **Confidence-based flexibility**: HIGH=1.0, MEDIUM=0.5, LOW=0.25, NONE=0.2 (constrains low-confidence channels near current spend)

## Media Strategy Context
- **Seasonality**: 85% of media budget deployed March-September
- **Consumer journey**: Inspiration phase (Mar-mid Jun) → Transaction phase (mid Jun-Sep)
- **TV role**: Brand rebuilding early season; creates halo effect amplifying ALL other channels
- **Radio**: Tactical mass medium, takes over as TV declines mid-May; regional; 3-day promo events with in-store remotes (Apr-Jul)
- **DOOH/Panneaux**: Digital billboards with dayparting; commute-targeted; dual role (inspiration + promo)
- **Digital flyer**: Most commercially oriented lever; Flipp/Reebee; conversion driver from mid-Jun onward
- **Preroll**: Flexible video (YouTube + Facebook); upper/mid funnel; shorter lag than TV
- **Premium partnerships**: Bell, Quebecor, La Presse; brand credibility in editorial environments
- **Display**: Google/Facebook ecosystems; amplification role; short-term effects
- **Performance marketing**: PMAX + lower-funnel Facebook; captures existing demand (not creates it)
- **Cross-media synergies**: No channel performs in isolation; the mix is an ecosystem
- **Pre-loading**: Media investment deliberately brought forward relative to demand peaks

## Model Results Summary (NB06)
- **Two-Stage Non-Negative Ridge R²**: 0.859 full, 0.835 seasonal (S1), 0.149 media (S2)
- **Adstock decay rates**: TV=0.2, Radio=0.5, Panneaux=0.4, Social=0.1, Preroll=0.3, Banniere=0.2, Circulaire=0.3
- **TV and Preroll** pass all 4 robustness checks (adstock, saturation, LOO, CI)
- **Channel ROAS (nonneg)**: Preroll $27.7, Social Media $16.3, Web Banners $12.2, TV $4.5, Radio $0, Panneaux $0, Circulaire $0
- **Media share of revenue**: ~10.9% ($55.7M of $512.4M over 3 years)
- **Non-negative constraint**: All media coefficients >= 0 (NNLS)

## Optimization Results (NB07, corrected response function + full budget)
- **Business-constrained**: +21.4% lift with confidence-aware bounds (same total budget, better allocation)
- **Budget cut feasibility**: A 15% cut with optimized allocation matches current performance (-0.1%); a 10% cut beats it (+8.9%)
- **Key recommendation**: Shift spend toward Preroll (+102% to $51K), Social Media (+56% to $36K), Web Banners (+32% to $30K); reduce TV to strategic floor ($80K), reduce zero-ROAS channels by 20%

## Known Model Limitations
- **Small sample**: N=36 months (3 fiscal years); 14 parameters (ratio 2.6:1 vs 5:1 standard)
- **TV confounding**: Negative/low coefficient likely due to seasonality correlation; narrative confirms TV's role is brand + halo, not direct sales
- **Weather proxy**: Single province-wide point for 42 geographically dispersed stores
- **No interaction terms**: Cross-media synergies (TV halo) not explicitly modeled
- **Weekly data available but unused**: 156 weekly observations exist but were aggregated to monthly

## Code Conventions
- **Paths**: `project_root / 'data' / 'processed'`, `project_root / 'reports' / 'figures'`
- **Data formats**: `.pkl` for intermediate data, `.csv` for outputs, `.json` for parameters
- **Figure naming**: `{topic}_{description}.png` (e.g., `optimization_response_curves.png`)
- **Config**: `config/params.yaml` for model parameters
- **Transformations**: `src/features/transformations.py` — single source of truth for adstock/saturation
- **The `~$` prefixed Excel files are lock files**, NOT actual data

## Critical Bugs to Avoid
- **LOOCV**: `cross_val_score(scoring='r2')` returns NaN for LOO → use `cross_val_predict` + `r2_score`
- **Budget "juillet" bug**: Month detection must take LAST matching column (event sub-columns appear before monthly totals)
- **Google Shopping**: Skip GOOGLE parent row, use sub-rows instead
- **Budget totals**: Corrected from $8.88M to $10.26M (event sub-columns were zeroing out data)
