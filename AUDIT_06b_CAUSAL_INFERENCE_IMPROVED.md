# AUDIT: Notebook 06b — Causal Inference: Media Effectiveness Analysis (Improved)

## Executive Summary

**Assessment Level: CONDITIONAL ACCEPT with significant caveats**

Notebook 06b represents a methodologically sound two-stage regression approach with important constraints (non-negative media coefficients). However, the small-sample regime (N=36, 14 parameters), wide confidence intervals, and high number of channels zeroed out raise serious concerns about generalizability and statistical power. The model is suitable for *exploratory insight and relative ranking*, but NOT for precise ROI claims or optimization-based decisions without substantial caveats in the client presentation.

**Key Findings:**
- ✅ Non-negative constraint properly implemented via NNLS augmented matrix trick
- ✅ Two-stage Frisch-Waugh decomposition is theoretically sound
- ✅ Bootstrap CI methodology is standard
- ⚠️ 3 of 7 channels (Radio, Panneaux, Circulaire_Digitale) zeroed out due to non-negativity constraint
- ⚠️ Preroll is only channel passing all 4 robustness checks for Total Revenue
- ⚠️ Small-sample ratio (2.6:1 vs 5:1 standard) introduces overfitting and inference risk
- ⚠️ Media-only R² extremely low (0.149 for Total Revenue)
- ⚠️ Seasonal controls dominate (83% of R²); media contributes ~15%

---

## 1. STATISTICAL VALIDITY & FRISCH-WAUGH IMPLEMENTATION

### Assessment: ✅ THEORETICALLY SOUND

The two-stage approach is correctly implemented:

**Stage 1 (Seasonality Baseline):**
- Regresses `Revenue ~ Controls` (Fourier + 3 weather features)
- Uses RidgeCV with TimeSeriesSplit (5-fold) for alpha selection
- Produces residuals orthogonal to seasonal/weather variation

**Stage 2 (Media Incremental Lift):**
- Regresses `Residuals ~ Saturated Media Channels`
- Uses same RidgeCV + TimeSeriesSplit protocol for alpha selection
- Non-negativity constraint applied via augmented matrix trick (see below)

**Frisch-Waugh-Lovell Theorem Compliance:**
The residuals from Stage 1 are orthogonal to control features by construction (property of OLS/Ridge residuals). Stage 2 coefficients measure the incremental media effect after removing seasonality. This decomposition is standard practice in MMM (Robyn, Meta, Google LW).

**Verification Outputs (from model params JSON):**
```
Stage 1 R² (Total Revenue):  0.8347  ← Seasonality alone
Stage 2 R² (Media only):     0.1488  ← Media on residuals
Full R²:                     0.8593  ← Additive (approximately)
```

The R² values are additive (not exactly, due to Ridge shrinkage), confirming proper residual decomposition.

**Concern:** Stage 1 R² is very high (83%), implying that seasonality + weather explain most of the variance. This is reasonable for a retail business, but it means media effects are being extracted from a heavily de-trended signal (residuals with low variance). This increases noise relative to signal.

---

## 2. NON-NEGATIVE CONSTRAINT IMPLEMENTATION

### Assessment: ✅ METHODOLOGICALLY SOUND, ⚠️ AGGRESSIVE APPLICATION

**How It Works:**

The notebook implements the non-negative Ridge constraint using the augmented matrix trick:

```python
def nonneg_ridge_fit(X, y, alpha):
    """
    Solve: argmin ||Xb - y||² + alpha||b||² s.t. b >= 0

    Implementation: Stack augmented matrix
    X_aug = [X; sqrt(alpha)*I]
    y_aug = [y; 0]

    Then solve: nnls(X_aug, y_aug)
    """
    n, p = X.shape
    X_aug = np.vstack([X, np.sqrt(alpha) * np.eye(p)])
    y_aug = np.concatenate([y, np.zeros(p)])
    coef, residual_norm = nnls(X_aug, y_aug)
    intercept = y.mean() - X.mean(axis=0) @ coef
    return coef, intercept
```

**Verification:** This is a standard trick in constrained optimization literature. The augmented rows act as soft penalties on b; `nnls()` from scipy.optimize is the canonical non-negative least squares solver.

**Soundness Assessment:**

✅ **Theoretically Valid:**
- Augmented matrix approach is mathematically equivalent to Lagrangian dual formulation
- No approximation error (unlike post-hoc clipping)
- Widely used in MMM (Meta Robyn, Google LW use similar constraints)

⚠️ **Aggressive Application:**
The constraint forces coefficients to be exactly zero if the solver deems them uninformative, rather than allowing small negative values that might represent noise. This is appropriate for MMM (advertising cannot reduce sales in theory), but it creates a **zero-floor bias**: channels with weak or confounded signals get eliminated entirely.

**Evidence from Results:**

For Total Revenue, 3 of 7 channels were zeroed out:
- **Radio**: $2.17M spend (21% of budget) → coef=0 → marginal effect = $0
- **Panneaux**: $0.29M spend (3% of budget) → coef=0 → marginal effect = $0
- **Circulaire_Digitale**: $0.45M spend (4% of budget) → coef=0 → marginal effect = $0

**Total spend on zeroed channels: $2.91M (28% of media budget)**

This is a major result. Three interpretations:

1. **These channels truly have no incremental effect** (they're redundant with TV/Preroll/Social)
2. **Confounding/multicollinearity** masks their true signal
3. **The constraint is too aggressive** given small N and high feature correlation

---

## 3. ADSTOCK DECAY RATES

### Assessment: ⚠️ REASONABLE BUT UNDER-DOCUMENTED

**Specified Rates (from config/params.json):**
```
Television:          λ = 0.2  (short-term, brand building)
Radio:              λ = 0.5  (tactical, mid-term)
Panneaux (Outdoor): λ = 0.4  (commute-based, mid-term)
Social Media:       λ = 0.1  (rapid feedback, immediate)
Preroll (Video):    λ = 0.3  (upper-funnel, short-to-mid)
Web Banners:        λ = 0.2  (short-term, display)
Circulaire (Flyers):λ = 0.3  (conversion, mid-term)
```

**Interpretation:**
- Low λ (Social=0.1) = fast decay; effect concentrated in current week
- High λ (Radio=0.5) = sustained decay; effect spreads over ~3-4 weeks
- Geometric adstock: `adstock[t] = spend[t] + λ*adstock[t-1]`
- Half-life ≈ ln(0.5)/ln(λ)

**Reasonableness Check:**

| Channel | λ | Half-life (weeks) | Typical Industry |
|---------|---|------------------|------------------|
| Social | 0.1 | 0.6 | 0-1 (immediate) |
| TV | 0.2 | 2.4 | 2-3 (brand carry-over) |
| Radio | 0.5 | 1.0 | 1-2 (tactical) |
| Preroll | 0.3 | 1.8 | 1-2 (video engagement) |

✅ **For Consumer Retail (Pool/Spa Business):** These decay rates are plausible. Immediate channels (Social, Digital Flyers) decay fast; traditional/brand channels (TV, Radio) persist longer.

⚠️ **Concerns:**

1. **TV λ=0.2 is LOW** — Industry standards suggest λ=0.7-0.9 for TV (4-7 week half-life). The notebook acknowledges this in a "TV Decay Sensitivity Analysis" (Cell 30), showing that TV ROAS ranges from 1.4 (λ=0.8) to 4.5 (λ=0.2). This is a 3× sensitivity.

2. **Fixed, Not Estimated** — Decay rates were "calibrated" in NB05 using a data-driven median method, NOT optimized as part of the model fitting. This is standard in MMM (Robyn also uses pre-specified decay rates), but it's a **hidden assumption**. Changing TV λ to 0.7 would likely zero out TV entirely (already borderline with ROAS=4.5).

3. **Calibration Source Not Transparent** — The JSON says `"calibration_method": "data-driven median"`, but the exact method is not documented in 06b. NB05 should be consulted for validation.

**Recommendation for Client Presentation:**
- **Disclose** that TV decay is aggressively low (λ=0.2 vs 0.7-0.9 industry norm)
- **Show** the sensitivity table (Cell 30) with TV ROAS under different decay assumptions
- **Caveat:** TV ROAS is highly sensitive to decay rate assumption; results should not be treated as definitive

---

## 4. SATURATION CURVES (HILL FUNCTION)

### Assessment: ✅ APPROPRIATE, ⚠️ CALIBRATION CONCERNS

**Specified Parameters:**

All 7 channels use Hill saturation with α=2 (exponent) and data-driven K (half-saturation point):

```json
"television":       {"type": "hill", "K": 146394,  "alpha": 2}
"radio":            {"type": "hill", "K": 109086,  "alpha": 2}
"panneaux":         {"type": "hill", "K": 4876,    "alpha": 2}
"social_media":     {"type": "hill", "K": 22731,   "alpha": 2}
"preroll":          {"type": "hill", "K": 32335,   "alpha": 2}
"banniere_web":     {"type": "hill", "K": 25147,   "alpha": 2}
"circulaire_digitale": {"type": "hill", "K": 13398, "alpha": 2}
```

**Hill Function Definition:**
```
S(x) = x^α / (x^α + K^α)   , output ∈ [0, 1]
```

With α=2:
```
S(x) = x² / (x² + K²)
```

**Reasonableness Check:**

✅ **Bounded [0,1]:** All saturated values are in [0,1] after adstock transformation. This ensures balanced regularization across channels (FIX 1 from 06b notes).

✅ **Non-linear Diminishing Returns:** Hill function exhibits concavity (characteristic of media saturation: extra spend has smaller marginal effect as volume increases).

✅ **Interpretation of K:** K is the adstock value where S(K) = 0.5 (50% saturation). By setting K to the median of non-zero adstock values, the notebook centers saturation at the typical operating point for each channel.

**Validation from Notebook (Cell 12):**
```
Saturation range check:
  television:  range=[0.368, 1.0]   ← nearly saturated
  radio:       range=[0.448, 1.0]
  panneaux:    range=[0.405, 1.0]
  social_media: range=[0.519, 1.0]
  preroll:     range=[0.454, 1.0]
  banniere_web: range=[0.498, 1.0]
  circulaire:  range=[0.469, 1.0]
```

⚠️ **Concerns:**

1. **K Calibration Method:** K is set to the **median of non-zero adstock**, not optimized. This is a heuristic. Alternative methods (e.g., Michaelis-Menten curve fitting, Bayesian prior) might yield different K values.

2. **All Channels Nearly Saturated:** Saturation ranges are [0.4, 1.0], meaning most channels operate in the saturated region (dS/dx approaching 0). This implies marginal effects are small, which could explain why some channels get zeroed out by the non-negativity constraint.

3. **α=2 Fixed:** The exponent α controls curvature. α=2 is a moderate choice. Higher α (e.g., 3-4) would make saturation more abrupt; lower α (e.g., 1) would make it more gradual. No sensitivity analysis provided.

4. **Adstock→Saturation Conversion:** The notebook computes `adstock_gain = 1.0 / (1.0 - λ)` to convert spend to adstock for saturation evaluation. This is correct:
   - Geometric adstock sum: Σ(λ^t) = 1/(1-λ)
   - So, spend of $X yields adstock of X/(1-λ)
   - This is properly used in the marginal effects calculation.

**Recommendation for Client Presentation:**
- Disclose that saturation parameters are data-driven heuristics, not optimized
- Show the saturation curve plots (saved in `saturation_curves_nonneg.csv`)
- Caveat: K values are set to operational medians, not fitted to frequency-response data

---

## 5. BOOTSTRAP CONFIDENCE INTERVALS

### Assessment: ✅ STANDARD METHODOLOGY, ⚠️ RELIABILITY CONCERNS WITH N=36

**Implementation (Cell 24):**

```python
N_BOOT = 1000  # resamples
n = 36  # original sample size

for target in TARGET_COLS:
    for b in range(N_BOOT):
        idx = np.random.choice(n, size=n, replace=True)  # resample with replacement
        X_b, y_b = X_media_scaled[idx], y_resid[idx]
        coef_b, _ = nonneg_ridge_fit(X_b, y_b, alpha_best)
        coefs.append(coef_b)

    # 90% CI: [5th percentile, 95th percentile]
    ci_lower = np.percentile(coefs, 5)
    ci_upper = np.percentile(coefs, 95)
```

**Methodology Assessment:**

✅ **Correct Implementation:**
- Resampling with replacement (standard bootstrap)
- Uses the same Ridge alpha as the full-sample fit (appropriate)
- Maintains non-negativity constraint in each bootstrap iteration
- Percentile CI is empirical (no distributional assumptions)

✅ **Parallelized:** Uses joblib for multi-core efficiency (good practice for N_BOOT=1000)

⚠️ **Reliability with N=36:**

The delta method or analytical CI would be preferable with N=36 due to small-sample considerations. Bootstrap CI requires the bootstrap distribution to be a good approximation of the true sampling distribution. With only 36 original observations:

1. **Bootstrap resamples are recycled subsets** of 36 points, with many duplicates
2. **Effective sample size per bootstrap iteration is lower**
3. **Percentile CI may under-cover** (i.e., true CI might be wider)

**Practical Check from Results (Total Revenue):**

| Channel | Coef | 90% CI Lower | 90% CI Upper | Width | Significance |
|---------|------|--------------|--------------|-------|--------------|
| Television | 354,333 | 1,040 | 7,204 | 6,164 | YES |
| Radio | 0 | 0 | 6,010 | 6,010 | NO |
| Panneaux | 0 | 0 | 63,652 | 63,652 | NO |
| Social_Media | 116,061 | 0 | 49,041 | 49,041 | NO |
| Preroll | 392,616 | 14,372 | 38,312 | 23,940 | YES |
| Banniere_Web | 108,778 | 0 | 32,547 | 32,547 | NO |
| Circulaire | 0 | 0 | 36,194 | 36,194 | NO |

**Observations:**

- **Only TV and Preroll have CIs excluding zero** (statistically significant at 90% level)
- **5 of 7 channels have CI lower bound = 0** (due to non-negativity constraint)
- **Very wide CIs for small coefficients** (e.g., Radio: 0 ± 6010; width 6× the point estimate of 0)

This reflects the small-sample problem: with N=36, individual channel effects are hard to pin down.

**Recommendation for Client Presentation:**
- **Emphasize uncertainty:** Only TV and Preroll are statistically significant
- **Warn:** Channels with zero coef but non-zero upper CI bound have ambiguous evidence
- **Caveat:** With N=36, these CIs should be treated as illustrative, not definitive

---

## 6. SMALL-SAMPLE RATIO & OVERFITTING RISK

### Assessment: ⚠️ SERIOUS CONCERN

**The Problem:**

| Metric | Value | Standard | Status |
|--------|-------|----------|--------|
| N (observations) | 36 | — | |
| p (parameters, Stage 2) | 7 | — | |
| Full model (Stage 1 + 2) | 12 | — | |
| N/p ratio (media only) | 5.1 | ≥ 5 | OK |
| N/p ratio (full) | 3.0 | ≥ 5 | ⚠️ BORDERLINE |
| Adjusted R² (media) | -0.064 | > 0 | ❌ NEGATIVE |

With N=36, the model is in a **small-sample regime** where:

1. **Ridge regularization is essential** (not optional)
2. **Coefficient estimates have high variance**
3. **Cross-validation becomes noisy** (only 5 folds in TimeSeriesSplit)
4. **Inference (CIs, p-values) is approximate**
5. **Overfitting risk is real**, despite Ridge shrinkage

**Evidence of Overfitting:**

| Product | R² (Full) | R² (Media) | Adj R² (Media) | Issue |
|---------|-----------|-----------|----------------|-------|
| Total Revenue | 0.859 | 0.149 | -0.064 | Negative adj R²! |
| HT | 0.751 | 0.122 | -0.098 | Negative adj R² |
| CR | 0.558 | 0.016 | -0.230 | Severely negative |
| SP | 0.831 | 0.210 | 0.013 | Marginal |
| Furniture | 0.847 | 0.059 | -0.176 | Negative adj R² |
| Fitness | 0.577 | 0.0 | -0.25 | No signal |
| BBQ | 0.796 | 0.001 | -0.249 | No signal |

**The Adjusted R² column is alarming:** 5 of 7 product categories have negative adjusted R² for the media-only model. This means that **the media covariates explain less variance than a simple mean model** after penalizing for parameter count.

**What This Means:**

- The media terms are fitting noise, not real signal
- With only 36 observations, the model cannot reliably estimate the effect of 7 media channels
- The high in-sample R² (0.859) is driven by Stage 1 (seasonality), not media effects

**Why Did Ridge Not Fix This?**

Ridge shrinkage is a trade-off: it reduces variance but increases bias. For Total Revenue, the Ridge alpha is 89.07, which heavily shrinks media coefficients. This prevents overfitting but also reduces effect magnitudes.

**Recommendation for Client Presentation:**

This is the **most critical finding** to communicate:
- **The model is seasonal-driven, not media-driven**
- Stage 1 (seasonality) explains 83% of variance; media explains ~3% (incremental)
- **The N=36 constraint is fundamental:** More data is needed for reliable media effect estimation
- **Results are more suitable for ranking channels than for absolute ROI claims**
- **Do NOT use these coefficients for budget optimization without sensitivity analysis**

---

## 7. ROAS ORDERING & INTUITION

### Assessment: ⚠️ PLAUSIBLE BUT SUSPICIOUS

**Observed Ordering (Total Revenue):**

| Rank | Channel | ROAS | Total Spend | Notes |
|------|---------|------|-------------|-------|
| 1 | Preroll (Video) | 27.68 | $902K | Highest ROAS |
| 2 | Social Media | 16.28 | $827K | Second highest |
| 3 | Web Banners | 12.20 | $828K | Third |
| 4 | Television | 4.49 | $3.95M | Lowest positive |
| 5 | Radio | 0 | $2.17M | Zeroed out |
| 6 | Panneaux | 0 | $292K | Zeroed out |
| 7 | Circulaire_Digitale | 0 | $447K | Zeroed out |

**Intuition Check:**

✅ **Plausible Orderings:**
- Preroll (high-intent video) outperforming display (banniere) makes sense
- Social media strong makes sense for brand awareness in retail
- TV having lower ROAS than digital is consistent with modern trends

❌ **Suspicious Patterns:**
1. **Three channels completely zeroed** — unusual. Suggests multicollinearity or confounding, not market reality
2. **Radio = 0 despite 21% of budget** — Radio is a major tactical medium for pool retail (promo events, regional targeting). Industry analysis suggests Radio should be non-zero
3. **Preroll massively outperforming TV** — With TV spending $3.95M (4.3× Preroll's $902K), if Preroll is truly 6.2× more efficient, the budget allocation is severely suboptimal. Yet optimization in NB07 did not fully correct this (see constraints)
4. **Decay Rate Sensitivity** — Changing TV λ from 0.2 to 0.8 would drop TV ROAS from 4.49 to 1.4, inverting the ranking

**Root Cause Analysis:**

The zeroing of 3 channels is likely due to:

1. **Multicollinearity:** Most channels peak together (seasonal campaign bursts), so the model cannot isolate individual effects
2. **Confounding:** Spend decisions are endogenous (management chooses channel mix based on expected ROI), not exogenous
3. **The Non-Negativity Constraint:** Acts as a "variable selection" mechanism, eliminating channels with weak or negative signals. These are often the ones with:
   - Small coefficients (likely noise)
   - High multicollinearity with other channels
   - Confounded with seasonality (residual correlation)

**Practical Implication:**

The ROAS ordering should be interpreted as **relative ranking of estimated effects**, not absolute ROI. A 6× difference in ROAS between Preroll and TV could reflect:
- A real efficiency advantage of Preroll, OR
- Endogeneity/confounding in the allocation of TV spend, OR
- Measurement error in media spend amounts

---

## 8. OUTPUT FILES & DELIVERABLES

### Assessment: ✅ COMPLETE

The notebook generates four main output files in `/data/processed/`:

**1. media_effectiveness_results_nonneg.csv**
- **Rows:** 42 (6 products × 7 channels)
- **Columns:** channel, total_spend, ridge_coef_std, ridge_coef_orig, marginal_per_1000, marginal_ci_lo, marginal_ci_hi, roas, total_contribution, contribution_pct, saturation_pct
- **Purpose:** Main effectiveness table for each product-channel pair
- **Sample (Total Revenue):**
  ```
  TV:       ROAS=4.49,  CI=[1040, 7204],  Contribution=2.7% revenue
  Preroll:  ROAS=27.68, CI=[14372, 38312], Contribution=4.0% revenue
  Radio:    ROAS=0,     CI=[0, 6010]
  ```

**2. saturation_curves_nonneg.csv**
- **Rows:** 700 (7 channels × 100 spend points)
- **Columns:** channel, spend, saturation
- **Purpose:** Hill saturation curves (spend vs incremental lift) for plotting
- **Fixed:** FIX D1 ensures x-axis is raw spend ($), not adstock values

**3. causal_model_params_nonneg.json**
- **Comprehensive model specification:**
  - Decay rates for all 7 channels
  - Saturation parameters (K, α)
  - Ridge alphas for each target product
  - R² values (Stage 1, Stage 2, Full)
  - Adjusted R² values
  - Scaler means/scales (for later prediction)
  - All control features and media channels

**4. robustness_summary_nonneg.csv**
- **Rows:** 7 channels
- **Columns:** Adstock-stable, Saturation-stable, LOO-stable, CI-excludes-0
- **Summary:**
  | Channel | Checks Passed | Significance |
  |---------|---------------|--------------|
  | Television | 4/4 | ✅ ROBUST |
  | Radio | 3/4 | ⚠️ |
  | Panneaux | 3/4 | ⚠️ |
  | Social_Media | 2/4 | ⚠️ |
  | Preroll | 4/4 | ✅ ROBUST |
  | Banniere_Web | 2/4 | ⚠️ |
  | Circulaire | 3/4 | ⚠️ |

**Only TV and Preroll pass all 4 robustness checks.**

**5. ridge_results.pkl** (cached)
- **Purpose:** Cached model fits to speed up notebook iterations
- **Contains:** Stage 1 & Stage 2 models, alphas, R² values, scalers

**6. boot_summary.pkl** (cached)
- **Purpose:** Cached bootstrap coefficient distributions (N_BOOT=1000)
- **Contains:** 1000 resampled coefficient vectors for each target, used to compute 90% CIs

All outputs follow the naming convention `*_nonneg.csv` to distinguish from the original 06.ipynb results.

---

## 9. KEY RED FLAGS FOR CLIENT PRESENTATION

### 🚩 Critical Issues

1. **Only 36 Monthly Observations**
   - Adjusted R² is negative for 5/7 product categories in media-only model
   - This indicates the media terms are overfitting noise
   - **Recommendation:** Acquire multi-year weekly data (150+ observations) for robust estimation

2. **Three Channels Completely Zeroed (28% of Budget)**
   - Radio ($2.17M), Panneaux ($0.29M), Circulaire_Digitale ($0.45M) → ROAS = 0
   - This is implausible; these are real business channels with known engagement
   - **Root cause:** Likely multicollinearity + non-negativity constraint eliminating weak signals
   - **Recommendation:** Treat zeroed coefficients as "insufficient evidence" not "no effect"

3. **Media Explains Only 3% of Revenue Variance**
   - Seasonality dominates (Stage 1 R² = 83%)
   - Media incremental R² = 14% (in-sample), but negative adjusted R²
   - **Interpretation:** The model is a seasonal forecaster, not a media effectiveness model
   - **Recommendation:** For media insights, use a longer time series or experimental design

4. **TV Decay Rate (λ=0.2) is Unusually Low**
   - Industry standard: λ=0.7-0.9 (4-7 week carryover)
   - At λ=0.8, TV ROAS drops to 1.4 (vs 4.49 at λ=0.2)
   - **Recommendation:** Sensitivity analysis critical; do not present TV ROAS as fixed

5. **Only 2 Channels Statistically Significant at 90% Level**
   - TV: CI=[1040, 7204]
   - Preroll: CI=[14372, 38312]
   - All others: lower CI = 0 (constrained) or crosses wide range
   - **Interpretation:** High uncertainty; treat as exploratory ranking, not definitive allocation

### ⚠️ Moderate Issues

6. **Bootstrap CI Reliability with N=36**
   - Percentile CI may under-cover true sampling distribution
   - Consider reporting wider intervals (e.g., 80% instead of 90%)

7. **Saturation Calibration Opaque**
   - K values set to median adstock, not optimized
   - α=2 (exponent) not sensitivity tested
   - Different K values could change relative rankings

8. **Endogeneity Not Addressed**
   - Spend is likely endogenous (allocation decisions driven by expected ROI)
   - OLS/Ridge cannot distinguish causality from reverse causality
   - Instrumental variables or quasi-experimental design would be needed for true causal claims

9. **No Interaction Terms**
   - TV halo effect (synergy with other channels) mentioned in context but not modeled
   - Model assumes channels act independently

---

## 10. RECOMMENDATIONS FOR CLIENT PRESENTATION

### What to Emphasize

✅ **Strengths:**
- Proper two-stage decomposition isolates media from seasonality
- Non-negative constraint prevents unrealistic negative media effects
- Bootstrap CIs quantify uncertainty (even if wide)
- Ranking of channels (Preroll > Social > Web > TV > zeroed) is likely directionally correct

✅ **Appropriate Use Cases:**
- Exploratory ranking of channels (relative effectiveness)
- Hypothesis testing ("Does TV have any effect?" → Yes, barely)
- Identify underperforming channels for deeper analysis (Radio, Panneaux)
- Input to sensitivity analyses and scenario planning

### What to De-Emphasize or Caveat

❌ **Do NOT:**
- Use as sole basis for budget reallocation
- Treat ROAS values as precise ROI guarantees
- Claim TV decay (λ=0.2) is well-calibrated
- Suggest media accounts for significant revenue variance (it doesn't)

❌ **Do Caveat:**
- "With only 36 months of data, these results are exploratory"
- "Three channels (Radio, Panneaux, Circulaire) have insufficient evidence; their zero ROAS does not mean they have no effect"
- "Media effects are difficult to isolate from seasonality in this dataset; causal interpretation requires additional evidence"
- "Bootstrap CIs are wide due to small sample size; treat as illustrative ranges"

### Suggested Next Steps

1. **Acquire More Data**
   - Weekly observations (150+ months) or daily data (2+ years)
   - Geographically granular (by store cluster if possible)

2. **Experimental Design**
   - Test-and-control store groups to validate media effectiveness
   - A/B testing on digital channels (easier to execute)

3. **Alternative Methods**
   - Bayesian hierarchical MMM (pooling across products)
   - Time series methods (ARIMAX, Granger causality)
   - Quasi-experimental (DiD, RDD if natural experiments available)

4. **Refine Model Assumptions**
   - Re-estimate decay rates with longer series
   - Include brand lift or awareness metrics (if available)
   - Model channel interactions (TV × Preroll synergy)

---

## 11. SUMMARY TABLE: STATISTICAL QUALITY ASSESSMENT

| Criterion | Rating | Evidence | Caveat |
|-----------|--------|----------|--------|
| **Methodology** | ✅ Good | Two-stage Frisch-Waugh, proper Ridge CV, NNLS constraint | Small sample limits reliability |
| **Implementation** | ✅ Good | Code is clean, caching proper, diagnostics included | Limited sensitivity analysis |
| **Residual Orthogonality** | ✅ Good | Stage 1 R²=83%, Stage 2 on residuals | Residuals have low variance (noisy) |
| **Constraint Soundness** | ✅ Good | Augmented matrix trick, no approximation | Aggressive (3 channels zeroed) |
| **Adstock Calibration** | ⚠️ Fair | Data-driven median | TV λ=0.2 unusually low; sensitive to choice |
| **Saturation Calibration** | ⚠️ Fair | Hill function reasonable; K is heuristic | No optimization or sensitivity test |
| **Statistical Power** | ❌ Poor | N=36, p=7-12; ratio 3-5:1 | Adjusted R² negative for 5/7 products |
| **Inference (CIs)** | ⚠️ Fair | Bootstrap with 1000 resamples; percentile CI | CIs very wide; under-coverage risk with N=36 |
| **Generalizability** | ❌ Poor | Single 3-year window, province-wide only | Risk of regime change, seasonal shift |
| **Robustness Checks** | ⚠️ Fair | Adstock, saturation, LOO, CI included | Only 2/7 channels pass all 4 checks |
| **Causal Interpretation** | ❌ Poor | No causal design; observational only | Endogeneity and confounding not addressed |
| **Client Readiness** | ⚠️ Fair | Outputs complete and well-documented | Requires significant caveating |

---

## CONCLUSION

Notebook 06b represents a **methodologically sound** but **limited application** of two-stage Ridge regression for MMM. The non-negative constraint is properly implemented and addresses a real problem (unrealistic negative media effects). However, the small-sample regime (N=36, p=7-12), high multicollinearity, seasonal dominance, and resulting negative adjusted R² values raise serious questions about statistical power and generalizability.

**Recommended Interpretation:**
- ✅ Use as **exploratory channel ranking** (Preroll > Social > Web > TV)
- ✅ Use as **diagnostic** (only TV and Preroll show consistent evidence)
- ❌ Do NOT use as sole basis for budget optimization
- ❌ Do NOT present ROAS values as precise ROI guarantees

The path forward is clear: **acquire more data** (weekly/daily, 2+ years) and/or **use experimental methods** (test-and-control). The current 36-month aggregation is too coarse to reliably separate media effects from confounding factors.

**For the client presentation:** Frame this as the beginning of the analysis, not the end. It provides strategic insight (media matters, but channels matter unequally) but not operational precision (exact ROI per channel).

---

## APPENDIX: CODE QUALITY NOTES

✅ **Strengths:**
- Well-commented, clear variable names
- Proper use of caching (pickle) to speed iterations
- Joblib parallelization for bootstrap
- Defensive programming (e.g., checking for zero variance)

✅ **Best Practices:**
- Config file (JSON) for parameters (good for reproducibility)
- Seed setting for reproducible bootstrap
- TimeSeriesSplit for temporal data (not random K-fold)
- Separate scalers for controls and media

⚠️ **Areas for Improvement:**
- Limited sensitivity analysis (only TV decay in Cell 30)
- No cross-validation on full pipeline (only media stage)
- Intercept computation in `nonneg_ridge_fit()` uses empirical mean; could use proper projection
- No diagnostic plots (residual QQ-plots, leverage plots, etc.)

**Overall Code Grade: B+** (Good quality, well-organized, suitable for reproducible research)

