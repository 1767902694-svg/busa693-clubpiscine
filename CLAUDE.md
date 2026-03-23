# Club Piscine — Use Case 4: Weekly Demand Forecasting

## Objective
Build a weekly demand forecasting system for Club Piscine's 27 stores across 11 product divisions (~287 store-division groups). The goal is to predict unit demand and revenue 4-8 weeks ahead to support inventory planning and supply chain decisions.

## Project Overview
- **Client**: Club Piscine — pool, spa, outdoor furniture & fitness retailer
- **Scope**: 27 active stores across Quebec (+ 1 Ontario), 11 product divisions
- **Primary target**: `units` (weekly net units sold)
- **Secondary target**: `revenue` (CAD)
- **Data granularity**: Week x Store x Division
- **History**: ~125 weeks (Nov 2023 - Mar 2026)
- **Store-division groups**: 287 (27 stores x 11 divisions, not all combinations active)

## Product Divisions (11)
FI, BQ, GA, ME, PA, CH, HT, TO, PC, LO, SP

## Notebook Pipeline
| NB | Name | Purpose | Key Output | Status |
|----|------|---------|------------|--------|
| 01 | EDA | Load 68 store slices, store regrouping, weekly aggregation | `weekly_units.csv` | Executed |
| 02 | Weather Integration | Open-Meteo API fetch, holiday flags, merge to sales | `weekly_units_weather.csv` | Executed |
| 03 | Feature Engineering | Lags, rolling stats, Fourier, weather derivatives (69+2 features) | `modeling_dataset.csv` | Executed |
| 04 | Forecast Model | Tiered XGBoost + Prophet (REPLACED by NB05) | `forecast_output_stratified.csv` | Deprecated |
| 05 | Global Forecast Model | Single global LightGBM for units + direct revenue model | `nb05_*.csv` (7 files) | **Active** |

## Data Sources
- **Sales**: 68 Power BI slice exports in `data/raw/slices/` (store-level Excel files)
- **Store master**: `data/raw/Table_Magasins.xlsx`
- **Weather**: Open-Meteo Archive + Forecast API (5 cities: Longueuil, Gatineau, St-Constant, Beloeil, Nepean)
- **Holidays**: python-holidays (Quebec + Ontario statutory)

## Key Store Regroupments (NB01)
- CP77 (Liquidation) -> CP07 (Laval) — both store_code AND city must be remapped
- CP100 (Liquidation) -> CP10 (Saint-Jerome)
- 11 stores excluded (CP01, CP03, CP11, CP20, CP21, CP23, CP29, CP31, CP41, CP43, CP49)

## Feature Groups (NB03 → NB05, 71 features total)
1. **Sales lags & rolling** (11): units_lag_1/2/4/52w, units_roll4/8/12_mean/std, units_volatility
2. **Revenue/price** (5): revenue_lag_1/4w, revenue_roll4_mean, avg_price_per_unit, price_lag_1w
3. **Seasonality** (4): Fourier terms (sin/cos_week_1, sin/cos_week_2)
4. **Calendar** (10): year_idx, quarter, week_of_yr, month, is_summer_peak, is_spring_opening, is_fall_closing, is_winter_off, n_holidays, has_holiday
5. **Weather raw** (7): avg_temp, max_temp, total_precip, sunshine_hours, rain_days, snow_days, bad_weather_days
6. **Weather derived** (17): deviation z-scores (12), temperature thresholds & degree days (5)
7. **Weather lags & interactions** (10): temp lags, shock, warming, season interactions
8. **Activity** (3): n_transactions, is_active_product, weeks_with_sales
9. **Intermittency** (2): cumulative_sales_count, zero_frac_12w (added in NB05)
10. **Categorical encodings** (2): store_enc, div_enc (LabelEncoded in NB05)

## Model Architecture

### NB04 — Tiered Strategy (DEPRECATED — replaced by NB05)
| Tier | Model | Scope |
|------|-------|-------|
| Tier 1 | XGBoost (global) | 17 high-volume groups only |
| Tier 2 | Prophet + regressors | 3-5 groups comparison |
| Tier 3 | Last-4-week average | Fallback (no output saved) |

**Why deprecated:** Only 17/287 groups forecasted (5.9% coverage), 1-week test set, 45.8% wMAPE.

### NB05 — Global LightGBM (ACTIVE)
- **Units model**: LightGBM regression (MAE objective), 500 trees, max_depth=6, lr=0.05, early stopping at 50 rounds
- **Revenue model**: Separate direct LightGBM (not units x price — avoids price-mix volatility)
- **Confidence intervals**: Quantile regression (P5, P95) for 90% prediction intervals, coherence-enforced
- **Validation**: Walk-forward CV, 6 folds across all seasons (52-week minimum train)
- **Train/Test split**: 19,012 / 3,576 rows, cutoff at week 2025-09-28 (26-week holdout)
- **Coverage**: 284/287 groups (100% of active store-division combinations)

## Key Results (Verified March 22, 2026)

### Units Forecasting
- **Overall wMAPE**: 0.212 (21.2%)
- **Overall R²**: 0.936
- **Overall MAE**: 9.06 units
- **CV wMAPE**: 0.233 ± 0.091 (6-fold walk-forward)
- **90% CI coverage**: 86.9% (target 90%), 0.4% incoherence

### Revenue Forecasting (Direct LightGBM)
- **Overall wMAPE**: 0.329 (32.9%)
- **Overall R²**: 0.805
- **Overall MAE**: $1,032
- **90% CI coverage**: 86.8%

### Seasonal Performance (Units wMAPE)
- Summer (Jun-Aug): 12.0% — R²=0.980 (excellent)
- Fall (Sep-Oct): 18.6% — R²=0.948 (good)
- Winter (Nov-Mar): 26.4% — R²=0.821 (weak)
- Spring (Apr-May): 30.8% — R²=0.673 (weak, limited data: 462 rows)

### Division Performance (Units wMAPE, sorted by revenue)
- **Strong**: PC 15.0%, FI 34.0%, SP 58.2%
- **Weak**: ME 68.3%, GA 67.4%, BQ 52.8%, CH 46.1%
- **Poor**: HT 89.2%, TO 96.4%, PA 113.0%, LO 39.2% (but LO revenue wMAPE=184.9%)

### Top Features (Units model)
n_transactions, units_lag_1w, avg_price_per_unit, units_lag_52w, units_lag_2w, units_roll4_std

### Baselines Beaten
- LightGBM 21.2% vs Seasonal Naive 47.2% vs Moving Average 48.3% vs Division Mean 294.7%

## Tiering Decision (NB01 EDA Output — Historical Reference)
- **Tier 1** (>=20 units/week): 78 groups, 95% of units, 42% of revenue
- **Tier 2** (<20 units/week): 209 groups, 5% of units, 58% of revenue
- **Decision**: Single global model (NB05) handles all tiers. No separate tiering needed — LightGBM with store/division encodings and intermittency features handles volume heterogeneity.

## Key Merge Patterns
- Sales and weather merge on `['week_ending', 'store_code', 'city']`
- Weather uses real city coordinates (Open-Meteo), not province-wide
- Lag warmup period (first 4 weeks) is dropped before modeling

## Code Conventions
- **Paths**: `DATA_RAW`, `DATA_PROCESSED`, `FIGURES` defined at top of each notebook
- **Data formats**: `.csv` for all outputs (no .pkl in UC4)
- **Figure naming**: saved to `use_case_4_forecasting/reports/figures/`
- **Notebook outputs**: prefixed with notebook number (e.g., `nb05_forecast_output.csv`)

## Known Issues & Bugs to Avoid
- **Liquidation city**: CP77's city label is "Liquidation" from store name parse — must remap to "Laval" after city assignment (NB01 cell 19). Currently causes 591 rows to get NULL weather in NB02.
- **Duplicate store_code columns**: NB02 merge on [city, week_ending] creates store_code_x, store_code_y, store_code. Should merge on [city, week_ending, store_code].
- **Revenue forecasting**: Do NOT use units x price — use direct revenue model (price-per-unit swings with product mix). Verified: units x price produces NaN for some groups.
- **Lag leakage**: Features must be computed per (store_code x division_code) group, not globally. NB03 does this correctly.
- **NB05 hardcoded paths**: Original NB05 referenced `/sessions/laughing-tender-wright/`. Fixed to use dynamic path resolution.
- **is_active_product**: Zero-variance feature (all 1.0) — should be dropped in future runs.
- **is_winter_off**: Created in NB03 but was NOT in original CALENDAR_FEATURES list — now included in NB05.
- **CI coverage below target**: 86.9% units / 86.8% revenue vs 90% target. Intervals slightly too narrow.
- **Winter/Spring weakness**: wMAPE degrades to 26-31% in off-season. Consider holiday-type features or seasonal ensemble.

## NB05 Output Files (in data/processed/)
- `nb05_model_accuracy.csv` — per store-division group accuracy
- `nb05_division_accuracy.csv` — per division summary
- `nb05_cv_results.csv` — 6-fold walk-forward CV results
- `nb05_feature_importance.csv` — units model feature importance
- `nb05_revenue_feature_importance.csv` — revenue model feature importance
- `nb05_summary.csv` — single-row summary of all key metrics
