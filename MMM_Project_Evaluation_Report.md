# Club Piscine MMM Project — Comprehensive Evaluation Report

**Prepared for:** Compass Data / Club Piscine
**Date:** February 14, 2026
**Scope:** Full audit of Media Mix Modeling project against industry standards

---

## Executive Summary

This report evaluates the Club Piscine MMM project across every dimension: raw data, cleaning pipeline, feature engineering, modeling approaches (Ridge regression and Bayesian MMM), parameter choices, results, and validation — all benchmarked against industry standards from Google Meridian, Meta Robyn, PyMC-Marketing, academic literature, and practitioner communities.

**Overall verdict:** The project is **well-structured and methodologically informed**, but suffers from **four critical implementation issues** that currently undermine the reliability of the results. All issues are fixable, and the project's own diagnostic reports already identify most of them. Once addressed, this work can deliver real business value.

**Scorecard at a glance:**

| Area | Grade | Summary |
|------|-------|---------|
| Data quality & cleaning | A- | Clean, complete, well-documented. Minor: single weather point for 42 stores |
| Feature engineering | B+ | Adstock + saturation properly calibrated via LOOCV. Fourier/weather overlap issue |
| Ridge regression model | C+ | Good R² (0.916) but negative TV coefficient; media contribution ≈ zero |
| Bayesian MMM model | B- | Properly uses PyMC-Marketing; priors mask confounding rather than solving it |
| Validation & QC | B | LOOCV done, bootstrap CIs computed; missing holdout test and MAPE |
| Parameters & config | B | Mostly aligned with industry; adstock inconsistency between notebooks |
| Business deliverables | C | ROAS estimates unreliable due to confounding; only Preroll is significant |
| Documentation | A | Excellent: 9 notebooks, 2 diagnostic reports, config files, README |

---

## 1. Data Assessment

### 1.1 What You Have

The project uses 36 monthly observations across 3 fiscal years (FY2023–FY2025), covering 42 stores, 6 product categories (above-ground pools, in-ground pools, spas, furniture/gazebos, fitness, BBQ), and 7 consolidated media channels. Total revenue analyzed: ~$512M. Total media spend: ~$10.3M.

**Raw files (8 Excel workbooks):** Historical sales by store, budget files for 2023/2024/2025, media performance recap, fiscal calendar, and submission reports.

### 1.2 What the Industry Expects

Google Meridian and Meta Robyn both require a **minimum of 2 years of weekly data** (104+ observations). The standard rule of thumb is at least 10x more observations than channels, or 3–5x more observations than total parameters.

**Your situation:** 36 monthly observations with 14 parameters gives a ratio of 2.6:1 — below the recommended minimum of 5:1. This is the single most constraining factor in the project. The data exists at weekly granularity (6,336 weekly store-level rows) but was aggregated to monthly during cleaning.

### 1.3 What You Did Right

The data cleaning pipeline is solid. Zero missing values in the final dataset. Fiscal year mapping (Nov–Dec → FY+1) is correctly implemented. The decision to consolidate 20+ media sub-rows into 7 strategic channel groups is smart — it reduces multicollinearity and aligns with how media buying actually works. Excluding problematic channels (Google Shopping, Programmatic, Postal) was the right call given data sparsity.

The switch from quote requests (soumissions, 19 usable months) to actual sales revenue (36 complete months) was a good pragmatic decision that nearly doubled the sample size.

### 1.4 What Needs Improvement

The Greater Montreal Area (GMA) single-point weather proxy is a simplification. About 50% of stores are outside GMA. Industry practice for geo-diverse retailers is to use a weighted weather index across store locations.

The Tableau Medias dataset (383 campaign records) was collected but never used for validation against the budget totals. This is a missed opportunity for cross-checking data quality.

**Critical gap:** The data was aggregated to monthly level when weekly data was available. Moving to weekly would give 156 observations — bringing the observation-to-parameter ratio to a much healthier 11:1.

---

## 2. Feature Engineering Evaluation

### 2.1 Adstock (Carryover Effects)

**Your approach:** Geometric adstock with channel-specific decay rates calibrated via LOOCV grid search over λ ∈ {0.1, 0.2, ..., 0.8}.

**Industry standard:** Geometric adstock is the most common starting point. Both Robyn and Meridian use it as default. Robyn recommends TV at 0.3–0.8, digital at 0.0–0.3, radio/outdoor at 0.1–0.4.

**Your results vs. industry ranges:**

| Channel | Your λ | Industry Range | Assessment |
|---------|--------|---------------|------------|
| TV | 0.2 | 0.3–0.8 | **Below range** — TV typically has longer carryover |
| Radio | 0.5 | 0.1–0.4 | Slightly above range but reasonable |
| Social | 0.1 | 0.0–0.3 | Within range — good |
| Preroll | 0.4 | 0.0–0.3 | Slightly above typical digital range |
| Panneaux | 0.4 | 0.1–0.4 | At upper bound — reasonable for outdoor |
| Banniere | 0.3 | 0.0–0.3 | At boundary — acceptable |
| Circulaire | 0.3 | 0.0–0.3 | At boundary — acceptable |

**Key concern:** TV at λ=0.2 is unusually low. Industry consensus is that TV has the longest carryover of any channel (0.3–0.8). This may indicate the LOOCV optimization is finding a spurious minimum due to small sample size. Furthermore, Notebook 08 (Bayesian) uses λ=0.1 for TV — even lower, and inconsistent with the λ=0.2 calibrated in Notebook 05.

**Recommendation:** Consider constraining TV adstock to ≥0.3 based on industry priors, or use Weibull adstock (2-parameter) which Robyn recommends for more flexible decay modeling.

### 2.2 Saturation (Diminishing Returns)

**Your approach:** Tested three functional forms per channel (Hill, Log, Power) and selected the best via LOOCV.

**Industry standard:** Hill function is the dominant choice. Both Google Meridian and Meta Robyn use Hill exclusively. PyMC-Marketing supports multiple forms but defaults to Hill/logistic.

**Your selections:** TV and Preroll use Log, Radio/Social/Panneaux/Circulaire use Power (β=0.5), Banniere uses Hill.

**Assessment:** The mixed approach is more flexible than industry standard but introduces complexity. The Power function (y = x^0.5) is unbounded — it never reaches a ceiling, which may be unrealistic for saturated channels. The Hill function is preferred precisely because it enforces an upper bound, making saturation interpretable ("this channel is at X% of its maximum effect").

**Critical bug:** The saturation level calculation in Notebook 07 is broken. Radio shows 30,799% saturation, which is impossible. The formula `saturation_pct = saturated_feature_mean × 100` misinterprets the feature scale. This invalidates all "room-to-grow" analysis.

### 2.3 Seasonality Controls

**Your approach:** 2 Fourier harmonics (sin₁, cos₁, sin₂, cos₂) = 4 features.

**Industry standard:** Fourier terms are the recommended approach (used by Prophet, Robyn, and academic literature). However, the number of harmonics should be justified. With only 36 monthly observations and 3 complete seasonal cycles, 2 harmonics may over-parameterize.

**The confounding problem:** Your own Weather Attribution Diagnostic Report identified VIF=33 for sunshine hours and VIF=43 for Fourier cos₁. This means seasonality and weather are nearly indistinguishable in the model — the Fourier terms absorb weather effects, and the model cannot attribute any revenue to weather.

**Recommendation:** Reduce to 1 harmonic (2 features instead of 4). Use weather **deviations from monthly norms** rather than raw values to orthogonalize weather from seasonality. This is the single most impactful fix available.

### 2.4 Weather Features

**Your approach:** 3 weather features (sunshine hours, precipitation, hot days deviation) sourced from Open-Meteo ERA5 API for Greater Montreal.

**Industry standard:** Weather is commonly included as a control variable in MMM, especially for weather-sensitive categories like pools. The approach of using degree-days and threshold days (days_above_25°C) is well-aligned with industry practice.

**The problem:** Raw weather values correlate strongly with Fourier seasonality terms (of course — summer is both sunny and high-season). As a result, the model attributes zero revenue to weather and lumps everything into the Fourier baseline.

**Fix:** Replace raw values with deviations: `sunshine_deviation = actual_sunshine - avg_sunshine_for_that_month`. This captures "was this month unusually sunny?" rather than "is it summer?" and eliminates the VIF problem.

---

## 3. Modeling Approaches Evaluation

### 3.1 Approach 1: Ridge Regression (Notebook 06)

**What it does:** Fits `Revenue = β₀ + Σ(β_j × media_j_transformed) + Σ(γ_k × control_k) + ε` with L2 regularization. Cross-validated alpha per product category. 1,000 bootstrap resamples for 90% CIs.

**In-sample R²:** 0.916 (total revenue). **LOOCV R²:** 0.856.

**Industry benchmark:** R² > 0.8 on training is considered good. The 6% gap between in-sample and LOOCV is acceptable for 36 observations.

**What's wrong:**

**Negative TV coefficient (−$644K):** This is a classic sign of confounding, not a true negative effect. TV spend peaks in certain months that also happen to be lower-revenue months (or correlate with other factors the model can't disentangle). Industry practice is to enforce sign constraints (all media ≥ 0). Robyn does this by construction. PyMC-Marketing uses HalfNormal priors. Ridge regression alone does not prevent negatives.

**Media contribution ≈ zero:** The model attributes essentially no revenue to any media channel. The entire ~$512M in revenue is attributed to baseline (Fourier seasonality + weather + intercept). This means the model cannot identify any media effect — it's saying "sales happen because of the season, not because of advertising." This is the confounding problem in full expression.

**Only Preroll is statistically significant** at 90% confidence. All other channels have CIs that include zero (or negative values for TV and Circulaire).

**Assessment against industry standards:**

| Criterion | Industry Standard | Your Result | Pass? |
|-----------|------------------|-------------|-------|
| Sign constraints | Media coefficients ≥ 0 | TV = −$644K | **Fail** |
| Media attribution | Media should explain 10–40% of revenue | ~0% | **Fail** |
| Significant channels | Multiple channels expected | Only 1 of 7 | **Marginal** |
| R² | > 0.8 | 0.916 | Pass |
| Validation | Holdout MAPE 5–10% | LOOCV only | **Incomplete** |

### 3.2 Approach 2: Bayesian MMM (Notebook 08)

**What it does:** Uses PyMC-Marketing with geometric adstock + logistic saturation. HalfNormal(σ=2) priors force non-negative media coefficients. Beta(1,3) priors on adstock decay. MCMC sampling with posterior inference.

**ROAS results:** Similar ranking to Ridge (Preroll highest, TV lowest) but all values are non-negative. Only Preroll's HDI excludes zero.

**What it does right:**

Using PyMC-Marketing is an excellent tool choice — it's the most popular open-source Bayesian MMM framework and actively maintained. The HalfNormal prior for media coefficients is standard practice (enforces the domain knowledge that advertising shouldn't decrease sales). The Beta(1,3) prior on adstock is reasonable (skewed toward lower decay, allowing the data to push toward higher values if warranted).

**What it masks:**

The HalfNormal prior forces TV's coefficient to be ≥ 0, but this doesn't solve the underlying confounding — it just hides the symptom. Where Ridge honestly shows a negative coefficient (signaling a problem), Bayesian shrinks it toward zero without explanation. The posterior for TV concentrates near zero, which is interpreted as "TV has minimal effect" when the real answer may be "we can't tell because of confounding."

**Missing from the Bayesian implementation:**

| Feature | Industry Best Practice | Your Implementation | Gap |
|---------|----------------------|--------------------|----|
| Adstock estimation | Estimate λ from posterior | Fixed λ (not estimated) | **Major** — loses key Bayesian benefit |
| Lift test calibration | Use experiment results as priors | Not done | Moderate — may not have lift test data |
| Geo-level modeling | Hierarchical across regions | National-level only | Moderate — Meridian's core advantage |
| Time-varying coefficients | Coefficients can change over time | Static coefficients | Minor — advanced feature |
| Convergence diagnostics | Report R-hat, ESS, trace plots | Not shown in outputs | **Should be reported** |

### 3.3 Ridge vs. Bayesian Comparison

Both approaches agree on the ranking: Preroll > Social > Circulaire > Panneaux > Radio > Banniere > TV. Both identify only Preroll as statistically significant. The Bayesian ROAS estimates are 10–20% lower due to prior shrinkage.

The fact that both approaches agree is actually informative — it suggests the data genuinely supports Preroll as the highest-performing channel and TV as underperforming relative to its budget share. The disagreement on sign (Ridge allows negative TV, Bayesian forces positive) is purely a modeling choice, not a data insight.

---

## 4. Parameters & Configuration Assessment

### 4.1 Configuration File (params.yaml)

The project has a well-structured params.yaml with documented parameters. This is good practice — it separates configuration from code and enables reproducibility.

### 4.2 Parameter Inconsistencies

There's a notable inconsistency between Notebook 05 (feature engineering/calibration) and Notebook 08 (Bayesian MMM):

| Channel | NB05 Optimal λ | NB08 Used λ | Discrepancy |
|---------|----------------|-------------|-------------|
| TV | 0.2 | 0.1 | Different |
| Preroll | 0.4 | 0.1 | **Very different** |
| Social | 0.1 | 0.3 | Different |
| Banniere | 0.3 | 0.3 | Same |

This suggests manual adjustment between notebooks without documented rationale. Industry best practice is to either use the calibrated values consistently, or let the Bayesian model estimate them from the posterior.

### 4.3 Ridge Alpha Selection

Ridge alphas range from 5.9 (Spas) to 30.5 (In-Ground Pools). Higher alpha means stronger regularization. The variation makes sense — noisier product categories (fitness, in-ground pools) need more shrinkage. However, the method for selecting alpha (cross-validation within each product model) is standard and appropriate.

---

## 5. Industry Benchmarking

### 5.1 How Leading MMM Tools Would Handle This Data

**Google Meridian** would insist on geo-level data. With 42 stores across Quebec, you could build a hierarchical model with 42 geographic units, each contributing monthly observations. This would give 42 × 36 = 1,512 data points — dramatically improving statistical power. Meridian would also use its binomial adstock and Hill saturation by default.

**Meta Robyn** would use Ridge regression (same as your Approach 1) but with Nevergrad multi-objective optimization to find Pareto-optimal models balancing fit (NRMSE) and business plausibility (DECOMP.RSSD). Robyn would also decompose seasonality using Prophet rather than raw Fourier terms, which may better separate seasonal baseline from media effects. Critically, Robyn would present multiple candidate models on a Pareto frontier rather than a single "best" model.

**PyMC-Marketing** (which you already use) would ideally estimate adstock parameters from the posterior rather than fixing them. It would also benefit from informative priors based on historical campaign performance or industry benchmarks, rather than generic HalfNormal(σ=2).

### 5.2 ROAS Benchmarks

Your Preroll ROAS of 150–166× is extremely high. Industry benchmarks for video advertising ROAS are typically 2–8×. Even top-performing digital channels rarely exceed 10–15×.

**Why this matters:** An ROAS of 166 means $1 of Preroll spend generates $166 in revenue. For a pool retailer, this would mean a $5,000 Preroll campaign drives $830,000 in sales. This is almost certainly inflated by confounding — Preroll spend likely correlates with periods of naturally high demand.

**Realistic ROAS ranges for your channels:**

| Channel | Your Ridge ROAS | Industry Typical | Assessment |
|---------|----------------|-----------------|------------|
| TV | 14.0 | 1.5–4.0 | Inflated (3–10× too high) |
| Radio | 30.2 | 2.0–6.0 | Inflated (5–15× too high) |
| Social | 135.2 | 2.0–5.0 | **Extremely inflated** |
| Preroll | 165.7 | 3.0–8.0 | **Extremely inflated** |
| Banniere | 21.2 | 1.5–4.0 | Inflated |
| Panneaux | 60.1 | 1.0–3.0 | **Extremely inflated** |
| Circulaire | 66.9 | 2.0–6.0 | **Extremely inflated** |

The uniformly inflated ROAS values suggest a systemic issue — likely the small sample size and confounding are inflating all estimates. This is consistent with the media contribution being near-zero: if the model can't reliably attribute revenue to media, the marginal ROAS calculations become unstable.

### 5.3 What Reddit and Practitioners Say

The practitioner community consistently emphasizes several points that are relevant to your project. First, 36 monthly observations is considered dangerously low — most practitioners recommend a hard minimum of 2 years of weekly data (104 observations). Second, negative media coefficients are the most commonly reported problem in MMM and almost always indicate confounding or multicollinearity, not actual negative effects. Third, Bayesian approaches (especially PyMC-Marketing) are increasingly preferred because they handle small samples better through informative priors and produce uncertainty estimates that are more interpretable than bootstrap CIs. Fourth, budget optimization recommendations from MMM should be treated as directional guidance, not precise prescriptions — recommending a 95% cut to TV is a red flag that the model is unreliable for optimization.

---

## 6. What Was Done Right

1. **Project structure is excellent.** Nine sequential notebooks with clear purpose, a config-driven pipeline, separate src/features module, diagnostic reports. This is production-quality organization.

2. **Channel consolidation is smart.** Grouping 20+ media lines into 7 strategic channels reduces multicollinearity and aligns with how the business actually makes decisions.

3. **LOOCV-based parameter calibration** (Notebook 05) is a rigorous approach. Testing multiple saturation functions per channel and selecting based on out-of-sample performance is better than assuming a single form.

4. **Using PyMC-Marketing** for the Bayesian approach is the right tool choice. It's the most actively maintained open-source Bayesian MMM framework.

5. **The Weather Attribution Diagnostic Report** is outstanding. It correctly identifies the root causes of the model's problems (VIF, confounding, Fourier overlap) and provides actionable recommendations. The fact that this self-diagnostic exists demonstrates strong analytical judgment.

6. **Bootstrap uncertainty quantification** (1,000 resamples, 90% CIs) for the Ridge model goes beyond what many MMM implementations provide.

7. **Data quality is impeccable.** Zero missing values, correct fiscal year mapping, proper handling of event sub-columns in budget files.

---

## 7. What Was Not Done Right

1. **Monthly aggregation when weekly data was available.** This is the project's biggest missed opportunity. Weekly data would give 156 observations instead of 36, dramatically improving statistical power.

2. **No sign constraints in Ridge model.** Allowing negative media coefficients (TV = −$644K) produces results that are not actionable. Every major MMM framework enforces non-negativity.

3. **Saturation calculation is broken.** Values exceeding 100% (Radio at 30,799%) indicate a formula error that invalidates the "room-to-grow" analysis.

4. **Weather features not orthogonalized from seasonality.** Raw weather values overlap with Fourier terms (VIF > 30), preventing the model from distinguishing weather effects from seasonal patterns.

5. **Adstock parameters fixed in Bayesian model** instead of estimated from posterior. This defeats a core advantage of Bayesian inference — letting the data inform parameter uncertainty.

6. **No holdout validation.** Only LOOCV was performed. Industry standard requires a contiguous holdout period (last 15–20% of data) with MAPE < 10–15%.

7. **No MAPE reported.** R² alone is insufficient — MAPE on a holdout set is the primary metric for predictive accuracy.

8. **Budget optimization recommendations are extreme.** Suggesting −95% TV and +200% Preroll violates practical business constraints and signals model instability.

---

## 8. Limitations

1. **Sample size (n=36)** is the fundamental constraint. With 14 parameters, the model is statistically underpowered. Expanding to weekly data or store-level data would resolve this.

2. **No causal identification.** The project uses observational data without experimental variation. Without lift tests or geographic experiments, ROAS estimates are correlational, not causal.

3. **Single geography for weather.** GMA weather may not represent stores in Sherbrooke, Trois-Rivières, Gatineau, or other Quebec cities.

4. **No competitive data.** Competitor advertising spend and pricing are unmeasured confounders that could bias media effect estimates.

5. **No promotion/pricing data.** Promotions, discounts, and price changes are mentioned in the use case but not included in the model.

6. **Static coefficients.** Both models assume media effectiveness is constant over 3 years. In reality, channel effectiveness changes as consumer behavior evolves.

7. **No cross-channel interactions.** The config file mentions interaction terms (TV×Radio, TV×Google), but these were never implemented. Synergies between channels are unmeasured.

---

## 9. Roadmap to Delivering Business Value

### Phase 1: Critical Fixes (1–2 weeks)

**Fix the saturation calculation.** Replace the broken formula with proper Hill saturation: `saturation_pct = (x^α / (K^α + x^α)) × 100`. Add validation that 0 ≤ saturation ≤ 100.

**Orthogonalize weather from seasonality.** Replace raw weather values with monthly deviations (e.g., `sunshine_deviation = actual - monthly_average`). Recompute VIF to confirm < 5.

**Reduce Fourier to 1 harmonic.** Drop sin₂/cos₂ to free 2 degrees of freedom and reduce parameter count from 14 to 12.

**Enforce sign constraints in Ridge.** Use scipy's constrained optimization or switch to non-negative least squares (NNLS) to prevent negative media coefficients.

### Phase 2: Model Improvement (2–4 weeks)

**Move to weekly data.** Re-aggregate the raw sales data to weekly level (the data already exists at this granularity). This gives 156 observations, bringing the ratio to 11:1.

**Estimate adstock in Bayesian model.** Update PyMC-Marketing to estimate λ from the posterior rather than fixing it. Compare estimated values to LOOCV calibration.

**Add holdout validation.** Hold out the last 6 months (or 26 weeks if using weekly data). Report MAPE on holdout. Target: < 15%.

**Report convergence diagnostics.** For the Bayesian model, show R-hat (should be < 1.01), effective sample size (> 400), and trace plots for all parameters.

### Phase 3: Enhanced Modeling (1–2 months)

**Try Robyn.** Run Meta's Robyn on the same data to get a second opinion. Robyn's multi-objective optimization may find models that balance fit and business plausibility better than manual Ridge tuning.

**Add store-level variation.** Build a hierarchical Bayesian model with store-level random effects. With 42 stores × 36 months = 1,512 observations, the model will be much better powered.

**Include promotions and holidays.** Add holiday dummies (Canada Day, construction holiday, Fête nationale) and any available promotion data.

**Test interaction terms.** Add media × media interactions (TV×Radio, TV×Social) and test statistical significance.

### Phase 4: Validation & Deployment (1–3 months)

**Design a lift test.** Run a controlled experiment: reduce TV spend in a subset of stores for one quarter. Compare sales to control stores. Use results to calibrate Bayesian priors.

**Build a scenario simulator.** Create an interactive tool where the marketing director can input budget allocations and see predicted revenue with confidence intervals.

**Document the methodology.** Produce a clear, non-technical summary for management explaining what the model says, what it can't say, and what decisions it supports.

---

## 10. Key Recommendations Summary

| Priority | Action | Impact | Effort |
|----------|--------|--------|--------|
| **Critical** | Fix saturation calculation bug | Enables room-to-grow analysis | 2 hours |
| **Critical** | Orthogonalize weather from Fourier | Enables weather attribution; reduces VIF | 1 day |
| **Critical** | Move to weekly data | Triples sample size (36 → 156) | 2–3 days |
| **High** | Enforce sign constraints (Ridge) | Eliminates negative TV coefficient | 1 day |
| **High** | Estimate adstock in Bayesian model | Proper uncertainty on carryover | 1 day |
| **High** | Add holdout validation + MAPE | Industry-standard model evaluation | 1 day |
| **Medium** | Run Robyn as second opinion | Cross-validates results | 1 week |
| **Medium** | Build hierarchical store-level model | 42× more observations | 2 weeks |
| **Medium** | Add holiday/promotion controls | Reduces confounding | 3 days |
| **Lower** | Design lift test for TV | Causal validation of model | 1 quarter |
| **Lower** | Build scenario simulator | Business value delivery | 1–2 weeks |

---

## 11. Conclusion

This project represents a strong foundation for MMM at Club Piscine. The data pipeline is clean, the methodology is well-documented, and the right tools (PyMC-Marketing) are being used. The diagnostic reports demonstrate that the team already understands the model's limitations.

The path to business value is clear: fix the four critical issues (saturation bug, weather confounding, sample size, sign constraints), then validate with holdout testing. Once the model produces reliable ROAS estimates with proper uncertainty bounds, it can meaningfully guide the marketing director's budget allocation decisions.

The current results should be treated as **exploratory**, not definitive. Preroll's strong performance is the most robust finding, but even that estimate is likely inflated. The recommendation to cut TV by 95% should not be acted upon without further validation.

With the Phase 1 and Phase 2 improvements implemented, this project can deliver on its promise: a clear vision of each marketing channel's effectiveness that justifies past investments, optimizes the future mix, and supports better strategic decisions.
