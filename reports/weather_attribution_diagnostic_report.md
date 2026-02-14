# Club Piscine MMM: Weather Attribution Diagnostic Report

**Date:** February 13, 2026
**Prepared by:** AI Diagnostic Team
**Scope:** Full audit of data pipeline, model specification, and results + external research

---

## Executive Summary

After deploying three parallel analysis agents to audit the entire codebase, model outputs, and research similar projects, we identified **the root causes** of why weather receives zero attribution in your causal inference models. The problem is **not** in the raw data (which is properly collected and merged) but stems from **fundamental model design choices** that systematically prevent weather from being attributed.

**The 5 root causes, ranked by severity:**

1. **Weather is in the control set, not the attribution set** — The model treats weather as a confounder to "control away," not a driver to measure
2. **Fourier seasonality absorbs weather's signal** — VIF = 33 for sunshine, VIF = 43 for Fourier cosine; they compete for the same variance
3. **Saturation calculations are broken** — 5 of 7 channels show saturation > 100% (impossible values like 30,798%)
4. **Sample size is critically low** — 36 monthly observations with 14+ parameters (ratio = 2.6:1, needs >5:1)
5. **Bayesian model masks the problem** — HalfNormal priors force non-negative coefficients without fixing underlying confounding

---

## Part 1: Data Pipeline Audit

### What's Working

- **Weather data collection is sound**: Open-Meteo API, Greater Montreal Area (45.55N, 73.70W), daily data aggregated to monthly
- **Variables are appropriate**: Temperature (max/min/mean), precipitation, sunshine hours, degree days, days_above_15/20/25
- **Temporal alignment is correct**: Fiscal year conversion (Nov-Dec of calendar Y maps to FY Y+1) properly handled
- **No missing values**: All 36 months have complete weather data
- **Scaling is correct**: Z-score normalization applied properly

### What's Broken

**Issue 1: Weather placed in CONTROL_COLS (not MEDIA_COLS)**

In `05_feature_engineering.ipynb` (lines 1035-1049):
```python
CONTROL_COLS = ['sin_1', 'cos_1', 'sin_2', 'cos_2',
                'total_sunshine_hours_scaled', 'total_precipitation_scaled',
                'days_above_25_scaled']
```

The attribution pipeline only reports on media channels. Weather is explicitly excluded from ROI/contribution calculations. The `causal_model_params.json` only contains `media_channels` and `target_cols` for reporting.

**Issue 2: Fourier seasonality captures the same signal as weather**

Both Fourier terms and weather variables peak in summer and trough in winter for Montreal. With only 36 observations covering 3 seasonal cycles, the model cannot distinguish between:
- "Revenue increased because it was sunny" (weather)
- "Revenue increased because it was July" (Fourier)

This is confirmed by VIF analysis:
| Feature | VIF |
|---------|-----|
| total_sunshine_hours_scaled | **33.12** |
| cos_1 (Fourier) | **42.99** |
| sin_1 (Fourier) | 7.57 |
| total_precipitation_scaled | 3.96 |
| days_above_25_scaled | 2.57 |

**Issue 3: Only 3 weather features selected (post-hoc)**

The feature selection was based on de-seasonalized correlation analysis in NB03. While methodologically sound, selecting features post-hoc from a small sample risks overfitting.

---

## Part 2: Model Specification Audit

### Ridge Model (Notebook 06)

**Model structure:**
```
Revenue = Intercept + Sum(beta_i * media_i_saturated) + Sum(gamma_j * control_j)
```

**OLS baseline results for weather:**

| Variable | Coefficient | p-value | 95% CI |
|----------|------------|---------|--------|
| sunshine_hours | 3,988,465 | 0.084 (NS) | [-584M, 8.6B] |
| precipitation | 1,973,254 | 0.017 | [392M, 3.6B] |
| days_above_25 | -421,730 | 0.499 (NS) | [-1.7B, 852M] |

Sunshine is **not significant** (p=0.084) due to multicollinearity inflating standard errors by sqrt(33) = 5.7x. Days_above_25 has the **wrong sign** (negative, meaning hot days reduce pool sales — clearly wrong).

**Ridge regularization compounds the problem:**
- alpha = 0.41 (low regularization)
- TV coefficient = -$644K (negative — impossible for media)
- Digital Flyers coefficient = -$694K (negative — impossible)
- These negative coefficients indicate **uncontrolled confounding**, not that those channels hurt sales

**Media attribution from Ridge:**
- total_contribution for ALL channels ≈ 10^-9 (effectively ZERO)
- Model attributes essentially NO revenue to any media channel
- 100% of revenue attributed to "non-media" (baseline + seasonality + weather, lumped together)

### Bayesian Model (Notebook 08)

**Changes from Ridge:**
- Uses PyMC-Marketing framework
- HalfNormal priors enforce non-negative media coefficients
- Built-in `yearly_seasonality=2` replaces explicit Fourier terms
- Weather remains in `CONTROL_COLS`

**Results comparison:**

| Channel | Ridge ROAS | Bayesian ROAS |
|---------|-----------|---------------|
| Television | **-5.6** | 11.2 |
| Radio | 27.5 | 27.3 |
| Panneaux | 73.5 | 56.8 |
| Social Media | 145.4 | 75.3 |
| Preroll | 321.5 | 162.9 |
| Web Banners | 8.4 | 29.5 |
| Digital Flyers | **-69.9** | 48.3 |

The Bayesian model "fixes" negative coefficients by **construction** (HalfNormal priors block negative values). This is a **regularization choice**, not a causal identification fix. The underlying confounding is still present — it's just hidden.

**Weather in Bayesian output:** Still zero attribution. Weather coefficients collapse to near-zero posterior. No separate weather decomposition reported.

### Saturation Bug

5 of 7 channels show impossible saturation values:

| Channel | Saturation % |
|---------|-------------|
| radio | **30,798.8%** |
| social_media | **19,181.1%** |
| circulaire_digitale | **11,855.7%** |
| panneaux | **7,942.3%** |

Root cause: `saturation_level = df[sat_col].mean() * 100` treats the saturated feature value as a saturation rate, but most saturated features are on different scales due to Hill/log/power functions.

---

## Part 3: Research Findings — What the Literature Says

### The Core Insight: Model Weather DEVIATIONS, Not Absolutes

Every major framework and paper agrees: **don't use raw weather values as controls**. Instead, use **deviations from seasonal norms**:

```python
# WRONG (what your model does):
CONTROL_COLS = ['total_sunshine_hours_scaled', ...]

# RIGHT (what research recommends):
historical_avg = df.groupby('month_num')['total_sunshine_hours'].transform('mean')
df['sunshine_deviation'] = df['total_sunshine_hours'] - historical_avg
```

This separates "normal July sunshine" (captured by seasonality) from "unusually sunny July" (the actual weather signal). The deviation is orthogonal to Fourier terms, eliminating multicollinearity.

### Framework-Specific Best Practices

**PyMC-Marketing (your framework):**
- Control variables via `control_columns` parameter
- All controls must be standardized to [-1, 1]
- Temperature should NOT be population-scaled like media
- Use `model_config` to set proper priors for weather controls

**Meta's Robyn:**
- Uses Prophet decomposition for automatic trend/seasonality/holiday separation
- Context variables specified via `context_vars` parameter
- Automatic separation minimizes multicollinearity issues

**Google's Meridian:**
- Control variables must satisfy conditional exchangeability
- Must include all confounders, exclude all mediators
- Explicit causal identification through DAGs

### Key Academic Papers

- **"It's the Weather" (2021)** — Uses partial dependence plots for weather-retail relationships
- **"Accounting for Climate" (2023)** — Shows ignoring climate leads to misclassifying weather-sensitive categories
- **Recast blog on seasonality** — "If marketing is more effective in summer than winter, pulling out seasonality is actually a huge modeling mistake"

### The Multicollinearity Solution: Bayesian Uncertainty

The Bayesian approach doesn't eliminate multicollinearity — it **quantifies the uncertainty it creates**:
- Frequentist: Channel A = 0.8, Channel B = 0.2 (false confidence)
- Bayesian: Channel A = 0.5 +/- 0.4, Channel B = 0.5 +/- 0.4 (honest uncertainty)

Your current Bayesian model doesn't do this properly because it forces non-negative coefficients instead of allowing the uncertainty to propagate.

---

## Part 4: Recommended Fixes

### Fix 1: Use Weather Deviations Instead of Absolutes (CRITICAL)

```python
# Calculate historical average for each month
monthly_avg = df.groupby('month_num')['total_sunshine_hours'].transform('mean')
df['sunshine_deviation'] = df['total_sunshine_hours'] - monthly_avg

monthly_avg_precip = df.groupby('month_num')['total_precipitation'].transform('mean')
df['precip_deviation'] = df['total_precipitation'] - monthly_avg_precip

monthly_avg_hot = df.groupby('month_num')['days_above_25'].transform('mean')
df['hot_days_deviation'] = df['days_above_25'] - monthly_avg_hot
```

This makes weather features **orthogonal to seasonality**, eliminating VIF > 30.

### Fix 2: Reclassify Weather as a Primary Driver (CRITICAL)

For a pool company, weather is not a nuisance to control away — it's **the primary demand driver**. Restructure:

```python
# Current (wrong for pool company):
MEDIA_COLS = [saturated media channels]
CONTROL_COLS = [Fourier + weather]  # Weather buried here

# Recommended:
MEDIA_COLS = [saturated media channels]
WEATHER_COLS = ['sunshine_deviation_scaled', 'precip_deviation_scaled', 'hot_days_deviation_scaled']
SEASONALITY_COLS = ['sin_1', 'cos_1']  # Reduce to 1 harmonic
FEATURE_COLS = MEDIA_COLS + WEATHER_COLS + SEASONALITY_COLS
```

Then generate a separate weather attribution report alongside media attribution.

### Fix 3: Reduce Fourier Harmonics (HIGH)

```python
# Current: 2 harmonics (4 features)
sin_1, cos_1, sin_2, cos_2

# Recommended: 1 harmonic (2 features)
sin_1, cos_1
```

With only 36 observations, 2 harmonics is too many. One harmonic captures the primary annual cycle; the second harmonic absorbs weather's residual signal.

### Fix 4: Fix Saturation Calculation (HIGH)

```python
# Current (broken):
saturation_level = float(df[sat_col].mean()) * 100

# Fix: Use proper Hill saturation formula
if sat_type == 'hill':
    K = params['K']
    current_spend = df[raw_col].mean()
    saturation_level = (current_spend**alpha / (K**alpha + current_spend**alpha)) * 100
```

Add validation: `assert 0 <= saturation_level <= 100`

### Fix 5: Add Media x Weather Interaction Terms (MEDIUM)

```python
# Test if media effectiveness varies with weather
df['media_x_sunshine'] = df['media_total_saturated'] * df['sunshine_deviation_scaled']

# In model: coefficient on interaction term tells you
# "does an extra sunny day make your ads more effective?"
```

This is the PIMM approach — weather as a moderator of media effectiveness, not just a direct driver.

### Fix 6: Increase Sample Size (MEDIUM-TERM)

- **Option A:** Convert monthly to weekly data (~156 weeks vs 36 months)
- **Option B:** Collect store-level data (42 stores x 36 months = 1,512 observations)
- **Option C:** Wait for more data (need minimum 48-60 months for robust monthly estimation)

### Fix 7: Validate Weather Effect in Isolation (QUICK WIN)

Before fixing the full model, run a simple validation:

```python
# Model 1: Seasonality only
X1 = df[['sin_1', 'cos_1']]
r2_season = Ridge().fit(X1, y).score(X1, y)

# Model 2: Seasonality + Weather deviations
X2 = df[['sin_1', 'cos_1', 'sunshine_dev', 'precip_dev', 'hot_days_dev']]
r2_weather = Ridge().fit(X2, y).score(X2, y)

# Delta R-squared = weather's incremental contribution
print(f"Weather adds {r2_weather - r2_season:.1%} explained variance")
```

If this delta is near zero, weather deviations truly don't matter (unlikely for a pool company). If it's meaningful (>5%), your model specification is the problem.

### Fix 8: Use Proper Bayesian Priors for Weather (MEDIUM)

```python
model_config = {
    # Weather controls: weakly informative, allow positive AND negative
    "gamma_prior": {"dist": "Normal", "kwargs": {"mu": 0, "sigma": 2}},

    # Media: informative, non-negative (domain knowledge)
    "beta_prior": {"dist": "HalfNormal", "kwargs": {"sigma": 2}},

    # Adstock: media only (weather has no carryover)
    # Saturation: media only (weather is roughly linear)
}
```

Weather effects are **contemporaneous** (today's weather affects today's sales, not next week's), so do NOT apply adstock or saturation to weather variables.

---

## Part 5: Implementation Priority

| Priority | Fix | Effort | Impact |
|----------|-----|--------|--------|
| 1 | Weather deviations instead of absolutes | Low (1 day) | Eliminates VIF > 30 |
| 2 | Reclassify weather as primary driver | Low (1 day) | Enables weather attribution |
| 3 | Reduce Fourier to 1 harmonic | Trivial | Frees variance for weather |
| 4 | Fix saturation calculation | Medium (2 days) | Correct room-to-grow analysis |
| 5 | Validate weather in isolation | Low (hours) | Quick proof of concept |
| 6 | Add media x weather interactions | Medium (2 days) | PIMM-style moderator effects |
| 7 | Proper Bayesian priors | Medium (3 days) | Honest uncertainty quantification |
| 8 | Increase sample size | High (ongoing) | Long-term model robustness |

---

## Key Sources

- PyMC-Marketing MMM Documentation: https://www.pymc-marketing.io/en/stable/notebooks/mmm/mmm_example.html
- Meta Robyn Analyst's Guide: https://facebookexperimental.github.io/Robyn/docs/analysts-guide-to-MMM/
- Google Meridian Control Variables: https://developers.google.com/meridian/docs/advanced-modeling/control-variables
- Recast on Seasonality Modeling: https://getrecast.com/seasonality/
- "It's the Weather" (2021): https://link.springer.com/article/10.1007/s12061-021-09397-0
- PyMC-Marketing Causal Identification: https://www.pymc-marketing.io/en/latest/notebooks/mmm/mmm_causal_identification.html
- Multicollinearity in MMM: https://towardsdatascience.com/is-multi-collinearity-destroying-your-causal-inferences-in-marketing-mix-modelling-78cb56017c73/
