# MMM Pipeline Fixes — Implementation Plan

**Date**: March 6, 2026
**Scope**: Sections 9.1 + 9.2 from evaluation report (excluding weekly data migration)
**Constraint**: N=36 monthly observations (client decision — do NOT migrate to weekly)
**Primary model**: `notebooks/06c_base_model.ipynb`
**Key dependency**: `src/features/transformations.py` (single source of truth for adstock/saturation)

---

## Overview of All Changes

| # | Fix | Notebook(s) Affected | Priority |
|---|-----|---------------------|----------|
| 1 | Weather features: absolute → deviations | NB04, NB05 | Critical |
| 2 | Investigate negative ROAS (VIF/multicollinearity) | NB06C | Critical |
| 3 | Recalibrate TV decay rate | NB05, NB06C | Critical |
| 4 | Revise optimization claims to realistic range | NB07 | Critical |
| 5 | Add interaction terms (TV × Preroll, TV × Social) | NB05, NB06C | High |
| 6 | Create business calendar (holidays, promos, COVID) | NB04 or new NB04b, NB05 | High |
| 7 | Add second Fourier harmonic | NB05, NB06C | High |

---

## Fix 1: Weather Features — Absolute Values → Deviations from Monthly Means

### Problem
Weather variables (`sunshine_hours`, `precipitation_mm`, `days_gt_25c`) use absolute values. These are extremely collinear with Fourier seasonality terms because both spike in summer. VIF for `sunshine_hours` = 33.12, `fourier_cos_1` = 42.99. The model cannot separate "it's summer" (Fourier) from "it's sunny" (weather), so weather attribution is effectively zero.

### Solution
Replace absolute weather values with **deviations from historical monthly averages**. This isolates "unusually sunny for July" from "typical July sunshine," making weather orthogonal to Fourier. Expected VIF reduction: ~33 → ~2–3.

### Implementation (in NB04: `04_external_data.ipynb`)

**Step 1**: After loading the weather DataFrame (which has columns `calendar_year`, `month`, `sunshine_hours`, `precipitation_mm`, `days_gt_25c` with 36 rows), compute monthly means:

```python
# Compute historical monthly averages across all 3 years
weather_monthly_means = weather_df.groupby('month')[
    ['sunshine_hours', 'precipitation_mm', 'days_gt_25c']
].transform('mean')

# Create deviation columns
weather_df['sunshine_dev'] = weather_df['sunshine_hours'] - weather_monthly_means['sunshine_hours']
weather_df['precip_dev'] = weather_df['precipitation_mm'] - weather_monthly_means['precipitation_mm']
weather_df['hot_days_dev'] = weather_df['days_gt_25c'] - weather_monthly_means['days_gt_25c']
```

**Step 2**: Keep the original absolute columns for reference but mark them clearly:

```python
# Rename originals to indicate they're raw (not for modeling)
weather_df = weather_df.rename(columns={
    'sunshine_hours': 'sunshine_hours_raw',
    'precipitation_mm': 'precipitation_mm_raw',
    'days_gt_25c': 'days_gt_25c_raw'
})
```

**Step 3**: Save updated `external_weather.pkl` with both raw and deviation columns.

### Downstream Changes (in NB05: `05_feature_engineering.ipynb`)

When merging weather into the feature matrix, use the **deviation** columns (`sunshine_dev`, `precip_dev`, `hot_days_dev`) instead of the raw columns. Everywhere in NB05 and NB06C that references `sunshine_hours`, `precipitation_mm`, or `days_gt_25c` as model features, replace with the `_dev` versions.

In NB06C Stage 1, the control features become:
```python
control_features = ['fourier_sin_1', 'fourier_cos_1', 'fourier_sin_2', 'fourier_cos_2',
                    'sunshine_dev', 'precip_dev', 'hot_days_dev', 'trend']
```

### Verification
After the fix, compute VIF for all Stage 1 features. Every feature should have VIF < 10 (ideally < 5). If any weather deviation still has VIF > 10, consider dropping it.

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor
import pandas as pd

X = df[control_features]
vif = pd.DataFrame({
    'feature': X.columns,
    'VIF': [variance_inflation_factor(X.values, i) for i in range(X.shape[1])]
})
print(vif.sort_values('VIF', ascending=False))
# Target: ALL VIF < 10
```

---

## Fix 2: Investigate Negative ROAS Channels (VIF / Multicollinearity Diagnosis)

### Problem
The unconstrained Ridge model shows negative ROAS for Radio (−$33.96), Panneaux (−$27.68), and Banniere_Web (−$10.52). The current approach forces these to zero via NNLS, which masks the root cause rather than diagnosing it.

### Implementation (add new diagnostic cells in NB06C)

**Step 1**: Compute VIF for all Stage 2 media features (the 7 saturated channels):

```python
from statsmodels.stats.outliers_influence import variance_inflation_factor

media_features = ['TV_saturated', 'Radio_saturated', 'Panneaux_saturated',
                  'Social_Media_saturated', 'Preroll_saturated',
                  'Banniere_Web_saturated', 'Circulaire_Digitale_saturated']

X_media = df[media_features]
vif_media = pd.DataFrame({
    'channel': X_media.columns,
    'VIF': [variance_inflation_factor(X_media.values, i) for i in range(X_media.shape[1])]
})
print(vif_media.sort_values('VIF', ascending=False))
```

**Step 2**: Compute pairwise correlations between media channels:

```python
corr = df[media_features].corr()
print("\nHigh correlations (|r| > 0.5):")
for i in range(len(media_features)):
    for j in range(i+1, len(media_features)):
        r = corr.iloc[i, j]
        if abs(r) > 0.5:
            print(f"  {media_features[i]} vs {media_features[j]}: r={r:.3f}")
```

**Step 3**: Run sequential leave-one-channel-out analysis to identify which channel(s) cause sign flips:

```python
from sklearn.linear_model import Ridge
import numpy as np

y = residuals_stage1  # Post-seasonal residuals from Stage 1
alpha = 5.0  # Current Ridge alpha

print("Leave-one-channel-out coefficient stability:")
for drop_ch in media_features:
    remaining = [c for c in media_features if c != drop_ch]
    X_sub = df[remaining].values
    model = Ridge(alpha=alpha, fit_intercept=False)
    model.fit(X_sub, y)
    coefs = dict(zip(remaining, model.coef_))
    neg_channels = [k for k, v in coefs.items() if v < 0]
    print(f"  Drop {drop_ch.replace('_saturated','')}:")
    print(f"    Negative: {neg_channels if neg_channels else 'None'}")
    print(f"    Coefs: {', '.join(f'{k.replace(\"_saturated\",\"\")}={v:.2f}' for k,v in coefs.items())}")
```

**Step 4**: Document findings. If dropping Radio makes TV/Panneaux coefficients positive and stable, that indicates multicollinearity between those traditional channels. The documentation should explain:
- Which channels are collinear and why (shared seasonality, audience overlap)
- Whether NNLS is appropriate or whether channel grouping (e.g., merge Radio+Panneaux into "Traditional_Other") would be better
- A narrative reconciliation with the client's media strategy context

**Step 5**: Add a markdown cell summarizing the VIF analysis results and the justification for the NNLS approach (or the alternative grouping approach if warranted).

---

## Fix 3: Recalibrate TV Decay Rate

### Problem
Current TV decay λ=0.1 gives a half-life of ~6 days. Literature meta-analyses (Tellis 1999, Broadbent 1979) report TV carryover of 0.7–0.9 weekly (half-life 2–6 weeks). For monthly data, a decay of 0.1 means almost no carryover — the model treats TV as if its effect vanishes within the same month. This contradicts the client narrative that TV creates a "halo effect" and builds brand over the early season (March–June).

### Implementation (in NB05 and NB06C)

**Step 1**: In NB05, run a **TV-specific sensitivity analysis** across a range of decay rates:

```python
from src.features.transformations import geometric_adstock
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error
import numpy as np

tv_decay_candidates = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]
results = []

for tv_decay in tv_decay_candidates:
    # Apply adstock with candidate TV decay (other channels stay the same)
    df_test = df.copy()
    df_test['TV_adstock_test'] = geometric_adstock(df_test['TV'].values, tv_decay)

    # Apply same saturation as current
    # (use whatever saturation function TV currently uses — likely log with scale=127905)
    df_test['TV_saturated_test'] = np.log1p(df_test['TV_adstock_test'] / 127905)

    # Replace TV_saturated with test version
    X = df_test[media_features].copy()
    X['TV_saturated'] = df_test['TV_saturated_test']

    # Fit Ridge on Stage 2 residuals
    model = Ridge(alpha=5.0, fit_intercept=False)
    model.fit(X.values, residuals_stage1)

    tv_coef = model.coef_[media_features.index('TV_saturated')]
    rmse = np.sqrt(mean_squared_error(residuals_stage1, model.predict(X.values)))

    results.append({
        'tv_decay': tv_decay,
        'tv_coefficient': tv_coef,
        'tv_roas': tv_coef * np.mean(df_test['TV_saturated_test']) / np.mean(df_test['TV']),
        'rmse': rmse,
        'r2': 1 - (np.sum((residuals_stage1 - model.predict(X.values))**2) / np.sum(residuals_stage1**2))
    })

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
```

**Step 2**: Visualize the sensitivity:

```python
import matplotlib.pyplot as plt

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
axes[0].plot(results_df['tv_decay'], results_df['r2'], 'bo-')
axes[0].set_xlabel('TV Decay Rate'); axes[0].set_ylabel('Stage 2 R²'); axes[0].set_title('Model Fit')
axes[1].plot(results_df['tv_decay'], results_df['tv_coefficient'], 'ro-')
axes[1].set_xlabel('TV Decay Rate'); axes[1].set_ylabel('TV Coefficient'); axes[1].set_title('TV Coefficient')
axes[2].plot(results_df['tv_decay'], results_df['tv_roas'], 'go-')
axes[2].set_xlabel('TV Decay Rate'); axes[2].set_ylabel('Approx ROAS ($)'); axes[2].set_title('TV ROAS')
plt.tight_layout()
plt.savefig(project_root / 'reports' / 'figures' / 'tv_decay_sensitivity.png', dpi=150, bbox_inches='tight')
plt.show()
```

**Step 3**: Select the best TV decay rate. Criteria:
- Prefer λ in the 0.3–0.6 range (literature-aligned for monthly data)
- Among those, pick the one that minimizes RMSE (or maximizes Stage 2 R²)
- If all perform similarly, default to λ=0.4 (half-life ~1 month, reasonable for TV brand building on monthly data)

**Step 4**: Update the grid search in NB05 to use the new TV decay. Then update `optimal_transformation_params.json` and re-run NB06C with the updated features.

**Step 5**: Document the sensitivity analysis results and the rationale for the chosen value. Include the plot.

### IMPORTANT
After changing TV decay, ALL downstream outputs change: adstocked values, saturated values, Ridge coefficients, ROAS, bootstrap CIs, and optimization results. NB06C and NB07 must be re-run after this change.

---

## Fix 4: Revise Optimization Claims

### Problem
NB07 claims +21.4% lift from budget reallocation. Based on: (a) wide ROAS confidence intervals, (b) TV halo not modeled, (c) 3 channels at ROAS=0 via NNLS, the realistic range is +5–15%.

### Implementation (in NB07: `07_mmm_roi_optimization.ipynb`)

**Step 1**: Add a **sensitivity analysis** section after the main optimization. Perturb ROAS estimates by ±20% and re-optimize:

```python
import numpy as np
from copy import deepcopy

# Get base ROAS estimates from NB06C output
base_roas = {
    'TV': 8.78,  # NNLS values — update with actual post-fix values
    'Radio': 0.0,
    'Panneaux': 0.0,
    'Social_Media': 28.48,
    'Preroll': 33.89,
    'Banniere_Web': 21.44,
    'Circulaire_Digitale': 10.84
}

perturbation_levels = [-0.20, -0.10, 0.0, +0.10, +0.20]
sensitivity_results = []

for pct in perturbation_levels:
    perturbed_roas = {k: v * (1 + pct) for k, v in base_roas.items()}

    # Re-run optimizer with perturbed ROAS
    # (use the same optimization function already defined in NB07)
    result = run_optimization(perturbed_roas, constraints, total_budget)

    sensitivity_results.append({
        'perturbation': f"{pct:+.0%}",
        'optimal_lift': result['lift_pct'],
        'tv_alloc': result['allocation']['TV'],
        'preroll_alloc': result['allocation']['Preroll'],
        'social_alloc': result['allocation']['Social_Media'],
    })

sens_df = pd.DataFrame(sensitivity_results)
print(sens_df.to_string(index=False))
```

**Step 2**: Compute a **confidence-adjusted lift range**:

```python
# Use bootstrap CI bounds from NB06C
# Lower bound: use 5th percentile ROAS estimates
# Upper bound: use 95th percentile ROAS estimates
# Central: use median ROAS estimates

lower_lift = run_optimization(roas_5th_percentile, constraints, total_budget)['lift_pct']
central_lift = run_optimization(roas_median, constraints, total_budget)['lift_pct']
upper_lift = run_optimization(roas_95th_percentile, constraints, total_budget)['lift_pct']

print(f"\nRealistic lift range: {lower_lift:.1f}% to {upper_lift:.1f}%")
print(f"Central estimate: {central_lift:.1f}%")
print(f"\nRecommendation: Present '{max(0, lower_lift):.0f}–{upper_lift:.0f}%' as the achievable range")
```

**Step 3**: Update all narrative cells in NB07 that reference "+21.4%" to instead reference the confidence range. Replace language like "the model predicts +21.4% lift" with "the model suggests a potential +X–Y% lift, with the central estimate of Z%."

**Step 4**: Update `mmm_final_output.json` and `mmm_executive_summary.csv` with the revised range.

**Step 5**: Add a **caveats** section documenting:
- TV halo effect not captured → optimizer may undervalue TV
- Zero-ROAS channels at floor → may be spending more than needed OR model may be wrong
- N=36 creates wide CIs → allocation stability uncertain
- Recommendation: pilot test with 2 channels before full reallocation

---

## Fix 5: Add Interaction Terms (TV × Preroll, TV × Social)

### Problem
The client explicitly states TV creates a "halo effect amplifying ALL other channels" and that "no channel performs in isolation; the mix is an ecosystem." The model has zero interaction terms, contradicting this.

### Implementation (in NB05: `05_feature_engineering.ipynb`)

**Step 1**: After computing all `_saturated` columns, create interaction terms:

```python
# Interaction terms: product of saturated (not raw) spend
# Use saturated values so diminishing returns are captured in the interaction
df['TV_x_Preroll'] = df['TV_saturated'] * df['Preroll_saturated']
df['TV_x_Social'] = df['TV_saturated'] * df['Social_Media_saturated']

# Optional: TV × Banniere_Web (only add if VIF stays manageable)
# df['TV_x_Banniere'] = df['TV_saturated'] * df['Banniere_Web_saturated']
```

**Step 2**: Normalize interactions to prevent scale issues:

```python
from sklearn.preprocessing import StandardScaler

interaction_cols = ['TV_x_Preroll', 'TV_x_Social']
scaler = StandardScaler()
df[interaction_cols] = scaler.fit_transform(df[interaction_cols])

# Save scaler parameters for NB07 optimization
interaction_scaler_params = {
    col: {'mean': scaler.mean_[i], 'std': scaler.scale_[i]}
    for i, col in enumerate(interaction_cols)
}
```

**Step 3**: Save updated `sales_spend_weather.pkl` with the new interaction columns.

### Downstream Changes (in NB06C)

Add the interaction terms to Stage 2 media features:

```python
media_features = [
    'TV_saturated', 'Radio_saturated', 'Panneaux_saturated',
    'Social_Media_saturated', 'Preroll_saturated',
    'Banniere_Web_saturated', 'Circulaire_Digitale_saturated',
    'TV_x_Preroll', 'TV_x_Social'  # NEW
]
```

This adds 2 parameters, bringing the total from 14 to 16 (ratio 2.25:1 — tight but acceptable given Ridge regularization).

**Important**: After fitting, check if interaction coefficients are positive. Positive TV×Preroll means TV amplifies Preroll effectiveness (consistent with halo narrative). If negative, the interaction is absorbing confounding — investigate rather than forcing positive.

### Downstream Changes (in NB07)

The optimizer must account for interactions. The response function becomes:

```python
# Old: revenue_media = sum(coef_i * saturated_i)
# New: revenue_media = sum(coef_i * saturated_i) + coef_TV_x_Preroll * (TV_sat * Preroll_sat) + coef_TV_x_Social * (TV_sat * Social_sat)
```

This makes the optimization nonlinear even without saturation (the interaction creates a bilinear term). The scipy optimizer should handle this fine, but verify convergence.

---

## Fix 6: Create Business Calendar

### Problem
No holiday, promotional, or COVID phase indicators. Easter shifts 4+ weeks across years, Victoria Day is a major sales trigger for outdoor/pool season, and FY2023 was a COVID recovery year. These are confounded with media effects.

### Implementation (new section in NB04 or new NB04b)

**Step 1**: Create a calendar DataFrame with 36 rows (matching the existing fiscal monthly structure):

```python
import pandas as pd
from datetime import date

# Build fiscal calendar (already exists as calendrier_fiscal.pkl)
# Add event indicators

calendar_events = []
for year in [2023, 2024, 2025]:  # Fiscal years
    for month_num in range(1, 13):
        # Convert fiscal month to calendar month
        if month_num >= 1 and month_num <= 2:  # Nov, Dec
            cal_month = month_num + 10
            cal_year = year - 1
        else:  # Jan through Oct
            cal_month = month_num - 2
            cal_year = year

        row = {'year': year, 'month_num': month_num}

        # === HOLIDAYS ===
        # Victoria Day: Monday before May 25 (always in May = month_num 7 in fiscal calendar)
        row['has_victoria_day'] = 1 if cal_month == 5 else 0

        # Easter: varies (March or April)
        # 2023: April 9 → fiscal month 6 (April)
        # 2024: March 31 → fiscal month 5 (March)
        # 2025: April 20 → fiscal month 6 (April)
        easter_months = {
            2023: {4: 1},  # April 2023 (FY2023 month 6)
            2024: {3: 1},  # March 2024 (FY2024 month 5)
            2025: {4: 1},  # April 2025 (FY2025 month 6)
        }
        row['has_easter'] = easter_months.get(cal_year, {}).get(cal_month, 0)

        # Labour Day: First Monday in September (fiscal month 11)
        row['has_labour_day'] = 1 if cal_month == 9 else 0

        # Fête nationale du Québec: June 24 (fiscal month 8)
        row['has_fete_nationale'] = 1 if cal_month == 6 else 0

        # Black Friday: Late November (fiscal month 1)
        row['has_black_friday'] = 1 if cal_month == 11 else 0

        # === SEASONAL PHASE ===
        # Inspiration phase: Mar–mid Jun (fiscal months 5–8)
        # Transaction phase: mid Jun–Sep (fiscal months 8–11)
        row['is_inspiration_phase'] = 1 if cal_month in [3, 4, 5] else 0
        row['is_transaction_phase'] = 1 if cal_month in [6, 7, 8, 9] else 0

        # === COVID RECOVERY ===
        # FY2023 was recovery year — first 6 months may show catch-up demand
        row['is_covid_recovery'] = 1 if (year == 2023 and month_num <= 6) else 0

        # === PROMOTIONAL PERIODS ===
        # Client narrative: "3-day promo events with in-store remotes (Apr–Jul)"
        row['is_promo_season'] = 1 if cal_month in [4, 5, 6, 7] else 0

        calendar_events.append(row)

calendar_df = pd.DataFrame(calendar_events)
```

**Step 2**: Save to `data/processed/business_calendar.pkl` and `.csv`.

**Step 3**: Merge into NB05 feature matrix on `(year, month_num)`.

### Downstream Changes (NB06C)

Add selected calendar features to Stage 1 control variables:

```python
# Choose which calendar features to include based on VIF and significance
# Start conservative: Easter + Victoria Day + COVID recovery
# These are the most likely to confound with media effects

control_features = [
    'fourier_sin_1', 'fourier_cos_1', 'fourier_sin_2', 'fourier_cos_2',
    'sunshine_dev', 'precip_dev', 'hot_days_dev',
    'trend',
    'has_easter', 'has_victoria_day', 'is_covid_recovery'  # NEW
]
```

**Important**: Adding 3 calendar dummies to Stage 1 increases parameters from ~8 to ~11 in Stage 1. With N=36, that's still 3.3:1 — tight but workable with Ridge. Do NOT add all calendar features at once; start with the 3 above and check VIF.

---

## Fix 7: Add Second Fourier Harmonic

### Problem
The CLAUDE.md mentions 2 harmonics exist (`fourier_sin_2`, `fourier_cos_2`), but the evaluation found only 1 harmonic pair may be actively used in Stage 1. The dominant seasonal pattern for Club Piscine is a 6-month semi-annual cycle (March–September peak), which requires the second harmonic.

### Implementation

**Step 1**: Verify whether `fourier_sin_2` and `fourier_cos_2` already exist in `sales_spend_weather.pkl`. If yes, ensure they're included in Stage 1 features of NB06C. If no, create them in NB05:

```python
import numpy as np

# Fiscal month_num goes 1–12 (Nov=1, Oct=12)
t = df['month_num'].values / 12.0  # Normalize to [0, 1]

df['fourier_sin_1'] = np.sin(2 * np.pi * 1 * t)
df['fourier_cos_1'] = np.cos(2 * np.pi * 1 * t)
df['fourier_sin_2'] = np.sin(2 * np.pi * 2 * t)  # Semi-annual
df['fourier_cos_2'] = np.cos(2 * np.pi * 2 * t)  # Semi-annual
```

**Step 2**: In NB06C, ensure Stage 1 uses all 4 Fourier terms:

```python
control_features = [
    'fourier_sin_1', 'fourier_cos_1',
    'fourier_sin_2', 'fourier_cos_2',  # Ensure these are included
    'sunshine_dev', 'precip_dev', 'hot_days_dev',
    'trend',
    'has_easter', 'has_victoria_day', 'is_covid_recovery'
]
```

**Step 3**: After fitting Stage 1, verify that Stage 1 R² improves (expected: 0.83 → 0.85+). The semi-annual harmonic should capture the sharp March–September peak better than a single annual cycle.

---

## Execution Order

The fixes have dependencies. Execute in this order:

```
Step 1: Fix weather features (NB04)
          ↓
Step 2: Create business calendar (NB04 or new cells)
          ↓
Step 3: Add 2nd Fourier harmonic + interaction terms (NB05)
     +  TV decay sensitivity analysis (NB05)
          ↓
Step 4: Re-run feature engineering pipeline (NB05)
     → Produces updated sales_spend_weather.pkl
          ↓
Step 5: VIF/multicollinearity diagnosis (NB06C, new cells)
          ↓
Step 6: Re-fit primary model with all new features (NB06C)
     → New coefficients, ROAS, bootstrap CIs, LOOCV
          ↓
Step 7: Re-run optimization with updated model (NB07)
     +  Add sensitivity analysis
     +  Revise claims to confidence range
          ↓
Step 8: Update all output files:
     - optimal_transformation_params.json
     - model_06c_params.json / model_C_params.json
     - causal_model_params_nonneg.json
     - media_effectiveness_results_nonneg.csv
     - saturation_curves_nonneg.csv
     - robustness_summary_nonneg.csv
     - mmm_optimization_results.csv
     - mmm_final_output.json
     - mmm_executive_summary.csv
     - mmm_scenario_analysis.csv
```

---

## Verification Checklist

After all fixes are applied, verify:

- [ ] **VIF < 10** for all Stage 1 features (weather deviations + Fourier + calendar + trend)
- [ ] **VIF < 10** for all Stage 2 features (7 media channels + 2 interactions)
- [ ] **Stage 1 R² ≥ 0.83** (should improve with calendar + 2nd harmonic)
- [ ] **Stage 2 R² > 0.15** (target improvement from interactions + better TV decay)
- [ ] **TV decay rate** in range 0.3–0.6 with documented sensitivity analysis
- [ ] **TV ROAS positive** and consistent across unconstrained and NNLS models
- [ ] **Interaction terms** (TV×Preroll, TV×Social) have positive coefficients (halo confirmed) or documented explanation if negative
- [ ] **No channel flips sign** between unconstrained and NNLS (if they do, document why)
- [ ] **Bootstrap CIs** recalculated with all new features
- [ ] **LOOCV** re-run with updated feature set
- [ ] **Optimization sensitivity** shows allocation stable to ±20% ROAS perturbation
- [ ] **Lift claim** presented as a range (e.g., "+5–15%") not a point estimate
- [ ] **All output files** updated and internally consistent

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `notebooks/04_external_data.ipynb` | Weather deviations + business calendar |
| `notebooks/05_feature_engineering.ipynb` | 2nd Fourier, interaction terms, TV decay sensitivity |
| `notebooks/06c_base_model.ipynb` | VIF diagnostics, updated features, re-fit model |
| `notebooks/07_mmm_roi_optimization.ipynb` | Sensitivity analysis, revised claims, interaction response |
| `src/features/transformations.py` | No changes needed (existing functions are correct) |
| `data/processed/external_weather.pkl` | New deviation columns |
| `data/processed/business_calendar.pkl` | New file |
| `data/processed/sales_spend_weather.pkl` | Updated with all new features |
| `data/processed/*.json`, `*.csv` | All model outputs regenerated |

---

## What NOT to Change

- **Do NOT migrate to weekly data** (client decision)
- **Do NOT change Ridge alpha** unless VIF analysis reveals it should change
- **Do NOT remove NNLS constraint** — but add the diagnostic cells explaining WHY it's needed
- **Do NOT change the 7 channel groupings** (consolidation is correct)
- **Do NOT add NB06D impression features** (only 12 months available)
- **Do NOT change the two-stage architecture** (Frisch-Waugh-Lovell is sound)
- **src/features/transformations.py** — leave this as-is; all functions are verified correct
