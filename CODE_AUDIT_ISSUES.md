# Code Audit: Detailed Issues & Recommendations

## Overview
This document provides line-by-line code review of notebooks 06b and 07, identifying specific issues (if any) and recommending improvements.

---

## NB06b (Causal Inference) - Code Audit

### File Location
`/sessions/busy-zealous-turing/mnt/busa693-clubpiscine/notebooks/06b_causal_inference_improved.ipynb`

---

### Issue 1: NNLS Helper Function Definition

**Location**: Cell 23, function `nonneg_ridge_fit`

**Code**:
```python
def nonneg_ridge_fit(X, y, alpha):
    """
    Solve Ridge regression with non-negativity constraint on coefficients.
    """
    n, p = X.shape
    X_aug = np.vstack([X, np.sqrt(alpha) * np.eye(p)])
    y_aug = np.concatenate([y, np.zeros(p)])
    coef, residual_norm = nnls(X_aug, y_aug)
    intercept = y.mean() - X.mean(axis=0) @ coef
    return coef, intercept
```

**Finding**: ✅ CORRECT
- NNLS augmented matrix trick correctly implements Ridge constraint
- sqrt(alpha) scaling is mathematically sound
- Intercept recovery is correct (residual mean = y.mean - X.mean @ coef)

**Recommendation**: Add docstring note explaining the augmented matrix approach for clarity:
```python
def nonneg_ridge_fit(X, y, alpha):
    """
    Solve Ridge regression with non-negativity constraint.

    Uses augmented matrix trick:
        min ||X @ b - y||^2 + alpha * ||b||^2  subject to b >= 0

    by solving NNLS on:
        [X                    ] [b]   [y    ]
        [sqrt(alpha) * I      ] [b] = [0    ]

    This is equivalent to the standard Ridge problem with non-negativity.
    """
    ...
```

---

### Issue 2: Cache Loading & Scaler Initialization

**Location**: Cell 23, cache loading block

**Code**:
```python
if cache_file.exists():
    print(f'Loading ridge results from cache ({cache_file.name})')
    with open(cache_file, 'rb') as f:
        ridge_results = pickle.load(f)
    scalers = ridge_results.get('scalers', {})
    scaler_ctrl = scalers.get('ctrl')
    scaler_media = scalers.get('media')
    scaler = scalers.get('combined')

    # FIX A1: always compute these — fallback to fresh fit if cached scalers are None
    if scaler_media is None:
        scaler_media = StandardScaler()
        scaler_media.fit(df[SATURATED_COLS].fillna(0))
```

**Finding**: ⚠️ PARTIAL ISSUE
- **Good**: Fallback for missing scalers prevents crashes
- **Concern**: If cache is stale but scalers exist, old scalers are used instead of re-fitting
- **Risk**: Running notebook on NEW data but old cache would silently use wrong scaler

**Recommendation**: Add data integrity check:
```python
if cache_file.exists():
    with open(cache_file, 'rb') as f:
        cached_ridge = pickle.load(f)

    # Verify cache is from same data period
    cached_date = cached_ridge.get('fit_date', None)
    if cached_date:
        print(f'Cache created: {cached_date}')
        # Add user prompt: "Use cached results? (y/n)"

    ridge_results = cached_ridge
```

---

### Issue 3: Bootstrap Parallelization

**Location**: Cell 24, joblib parallelization

**Code**:
```python
def compute_boot(target, seed):
    """Each target gets its own RNG seed for independent resamples."""
    rng = np.random.RandomState(seed)
    al = ridge_results[target]['best_alpha']
    y_res = residuals[target]
    coefs = []
    for b in range(N_BOOT):
        idx = rng.choice(n, size=n, replace=True)
        X_b = X_media_scaled[idx]
        y_b = y_res[idx]
        coef_b, _ = nonneg_ridge_fit(X_b, y_b, al)
        coefs.append(coef_b)
    arr = np.vstack(coefs)
    return target, arr

# Each target gets a distinct seed so bootstrap samples are independent
target_seeds = {t: 42 + i for i, t in enumerate(TARGET_COLS)}
results = Parallel(n_jobs=-1)(
    delayed(compute_boot)(t, target_seeds[t]) for t in TARGET_COLS
)
```

**Finding**: ✅ CORRECT
- Parallelization is efficient and correct
- Distinct seeds per target ensure independent resamples
- joblib handles thread safety properly for numpy operations

**Minor Improvement**: Could add progress bar for long-running bootstrap:
```python
from tqdm import tqdm
results = Parallel(n_jobs=-1, verbose=10)(  # verbose=10 shows progress
    delayed(compute_boot)(t, target_seeds[t]) for t in TARGET_COLS
)
```

---

### Issue 4: Two-Stage Ridge Alpha Selection

**Location**: Cell 23, Stage 2 alpha selection

**Code**:
```python
for target in TARGET_COLS:
    y_resid = residuals[target]

    # Use RidgeCV to select alpha (same as before)
    ridge_s2_cv = RidgeCV(alphas=ALPHAS, scoring='neg_mean_squared_error', cv=tscv)
    ridge_s2_cv.fit(X_media_scaled, y_resid)
    best_alpha = ridge_s2_cv.alpha_

    # FIX 6: Fit with non-negative constraint using selected alpha
    coef_nn, intercept_nn = nonneg_ridge_fit(X_media_scaled, y_resid, best_alpha)
```

**Finding**: ⚠️ SUBTLE ISSUE
- RidgeCV selects alpha WITHOUT the non-negative constraint
- Then non-negative Ridge is fit using that alpha
- **Problem**: The optimal alpha for unconstrained Ridge may not be optimal for non-negative Ridge

**Implication**: The selected alpha may not minimize CV error under the non-negative constraint.

**Severity**: LOW-MEDIUM (probably doesn't materially affect results, but inconsistent)

**Recommendation**: Either:
1. Select alpha WITH non-negative constraint (wrap nonneg_ridge_fit in cross-validation):
```python
def cv_nonneg_ridge(alpha, X, y, cv):
    """CV objective for non-negative Ridge."""
    r2_scores = []
    for train_idx, test_idx in cv.split(X):
        coef, _ = nonneg_ridge_fit(X[train_idx], y[train_idx], alpha)
        pred = X[test_idx] @ coef + y[train_idx].mean()
        r2 = r2_score(y[test_idx], pred)
        r2_scores.append(r2)
    return -np.mean(r2_scores)  # negative because minimize

best_alpha = minimize_scalar(
    lambda a: cv_nonneg_ridge(a, X_media_scaled, y_resid, tscv),
    bounds=(0.01, 100), method='bounded'
).x
```

2. OR use unconstrained alpha as initialization and accept it's approximate:
```python
# Current approach is acceptable if documented:
print("Note: Alpha selected via RidgeCV (unconstrained)")
print("      Then used for non-negative Ridge fit.")
print("      Optimal alpha under non-negative constraint may differ.")
```

---

### Issue 5: Adjusted R² Calculation

**Location**: Cell 23, adjusted R² computation

**Code**:
```python
adj_r2_full = 1 - (1 - r2_full) * (n - 1) / (n - p_full - 1)
adj_r2_media = 1 - (1 - r2_media) * (n - 1) / (n - p_media - 1)
```

**Finding**: ⚠️ FORMULA ISSUE
- Standard adjusted R² formula: `1 - (1-R²)(n-1)/(n-p-1)`
- This calculates penalty for total parameters, not incremental
- **Problem**: For two-stage model, p_full includes controls + media, but Stage 2 should only count media parameters

**Implication**: Adjusted R² for full model slightly overstates adjustment factor.

**Severity**: LOW (affects reporting only, not model fitting)

**Fix**: For two-stage, adjust only on media parameters:
```python
# Stage 1 has p_ctrl parameters, Stage 2 has p_media additional
# For full model, effective parameters is sum, but adjustment could be:
# Option 1: Count only media parameters
adj_r2_full_media_only = 1 - (1 - r2_full) * (n - 1) / (n - len(SATURATED_COLS) - 1)

# Option 2: Use full count but document
print("Note: Adjusted R² uses all control+media parameters")
```

---

### Issue 6: Column Naming Consistency

**Location**: Throughout notebooks

**Issue**:
- Column names mix underscore styles: `media_television_saturated` vs `television_adstock`
- Makes it hard to map between raw features and computed features

**Example**:
```python
SATURATED_COLS = [f'{ch}_saturated' for ch in MEDIA_CHANNELS]
# Produces: ['media_television_saturated', 'media_radio_saturated', ...]

# But earlier:
for ch in MEDIA_CHANNELS:
    df_tmp[f'{ch}_adstock'] = geometric_adstock(...)
# Produces: ['media_television_adstock', 'media_radio_adstock', ...]
```

**Recommendation**: Standardize naming convention:
```python
# Option 1: Drop 'media_' prefix throughout
SATURATED_COLS = [f'{ch.replace("media_", "")}_saturated' for ch in MEDIA_CHANNELS]

# Option 2: Add _saturated suffix consistently
df[f'{ch}_saturated'] = hill_saturation(df[f'{ch}_adstock'], K, alpha)
```

---

### Issue 7: Missing Unit Documentation in Outputs

**Location**: Output CSVs in `/data/processed/`

**File**: `media_effectiveness_results_nonneg.csv`

**Columns**:
```
marginal_per_1000    <- What does this mean? $/1000? Or per 1000 impressions?
marginal_ci_lo       <- CI for what quantity? Same units as marginal_per_1000?
roas                 <- $/$ or dimensionless multiplier?
saturation_pct       <- Percentage of what? Current saturation value × 100?
```

**Finding**: ⚠️ CLARITY ISSUE
- Column names are ambiguous without documentation
- Stakeholders could misinterpret units

**Recommendation**: Add header metadata to CSV:
```python
# Before writing CSV:
header_lines = [
    "# MODEL: Two-Stage Non-Negative Ridge (NB06b)",
    "# FIT_DATE: 2026-02-26",
    "# OBSERVATIONS: 36 monthly (FY2023-FY2025)",
    "# COLUMN DEFINITIONS:",
    "# - marginal_per_1000: Incremental revenue per $1,000 spend at median saturation point",
    "# - roas: Marginal revenue per $1 spend (same as marginal_per_1000 / 1000)",
    "# - saturation_pct: Current saturation = Hill(median_adstock; K, alpha) × 100",
    "# - marginal_ci_lo/hi: 90% bootstrap confidence interval on marginal effect",
]
```

Or create a separate `METADATA.json`:
```json
{
  "model": "Two-Stage Non-Negative Ridge",
  "fit_date": "2026-02-26",
  "columns": {
    "marginal_per_1000": "Incremental revenue per $1,000 spend",
    "roas": "Return on Ad Spend (dimensionless multiplier)",
    "saturation_pct": "Current saturation as % of maximum"
  }
}
```

---

### Issue 8: Hard-coded Paths

**Location**: Multiple cells

**Code**:
```python
processed_path = project_root / 'data' / 'processed'
figures_path   = project_root / 'reports' / 'figures'
```

**Finding**: ⚠️ PORTABILITY
- Assumes specific project structure
- Will break if run on different machine or with different folder layout

**Recommendation**: Use environment variables:
```python
import os
from pathlib import Path

DATA_DIR = Path(os.getenv('DATA_DIR', project_root / 'data'))
FIGURES_DIR = Path(os.getenv('FIGURES_DIR', project_root / 'reports' / 'figures'))

processed_path = DATA_DIR / 'processed'
figures_path = FIGURES_DIR
```

---

## NB07 (Optimization) - Code Audit

### File Location
`/sessions/busy-zealous-turing/mnt/busa693-clubpiscine/notebooks/07_mmm_roi_optimization.ipynb`

---

### Issue 1: Response Function Interpolation Bounds

**Location**: Cell 5

**Code**:
```python
func = interp1d(spend_pts, rev_pts, kind='cubic', bounds_error=False,
                fill_value=(rev_pts[0], rev_pts[-1]))
```

**Finding**: ⚠️ ASSUMPTION
- Assumes saturation curve is monotonically increasing (flat endpoints)
- `fill_value=(min, max)` extrapolates constant beyond saturation curve bounds

**Risk**: If optimization suggests spend outside the curve's range, it extrapolates using endpoint values (likely incorrect)

**Severity**: LOW (typically spend stays within observed range)

**Recommendation**:
1. Add warning if optimizer tries to spend outside curve bounds:
```python
def total_response(allocation, channels, response_funcs, spend_bounds):
    total = 0
    for ch, spend in zip(channels, allocation):
        if spend > spend_bounds[ch][1]:
            print(f"⚠️ WARNING: {ch} spend ${spend:.0f} exceeds curve bounds ${spend_bounds[ch][1]:.0f}")
        total += float(response_funcs[ch](spend))
    return total
```

2. OR extend saturation curves to cover wider spend range in NB06b

---

### Issue 2: Confidence Mapping Logic

**Location**: Cell 3

**Code**:
```python
if 'confidence' not in eff_total.columns:
    if 'confidence' in robust_df.columns:
        conf_map = robust_df.set_index('channel')['confidence'].to_dict()
        eff_total['confidence'] = eff_total.index.map(
            lambda ch: conf_map.get(ch, conf_map.get('media_' + ch, 'LOW'))
        )
    else:
        # Derive: significant CI = MEDIUM, positive ROAS = LOW, else NONE
        def derive_confidence(row):
            ...
```

**Finding**: ⚠️ FRAGILE LOGIC
- Falls back to deriving confidence if column doesn't exist
- Channel name mapping ('media_' prefix) may be inconsistent
- No error if channel not found in mapping

**Recommendation**: Be explicit about data sources:
```python
# Load confidence from upstream NB06 output
try:
    confidence_map = robust_df.set_index('channel')['confidence'].to_dict()
    eff_total['confidence'] = eff_total.index.map(confidence_map)
except KeyError as e:
    raise ValueError(f"Missing channel in robustness summary: {e}")
```

---

### Issue 3: Budget Constraint Handling

**Location**: Cell 7, constraint definition

**Code**:
```python
constraints = [
    {'type': 'eq', 'fun': lambda x: np.sum(x) - effective_budget},
    {'type': 'ineq', 'fun': lambda x, idx=trad_idx, lo=trad_lo, b=effective_budget:
        sum(x[i] for i in idx) - lo * b},
    {'type': 'ineq', 'fun': lambda x, idx=trad_idx, hi=trad_hi, b=effective_budget:
        hi * b - sum(x[i] for i in idx)},
]
```

**Finding**: ⚠️ LAMBDA CLOSURE ISSUE
- Default arguments (`idx=trad_idx`) are evaluated once at function definition
- If `trad_idx` or `effective_budget` change, constraints won't update
- Multiple lambda functions with mutable defaults can cause confusion

**Severity**: LOW (works correctly but fragile)

**Better Practice**:
```python
def make_trad_lower_bound(trad_idx, effective_budget, trad_lo):
    return lambda x: sum(x[i] for i in trad_idx) - trad_lo * effective_budget

def make_trad_upper_bound(trad_idx, effective_budget, trad_hi):
    return lambda x: trad_hi * effective_budget - sum(x[i] for i in trad_idx)

constraints = [
    {'type': 'eq', 'fun': lambda x: np.sum(x) - effective_budget},
    {'type': 'ineq', 'fun': make_trad_lower_bound(trad_idx, effective_budget, trad_lo)},
    {'type': 'ineq', 'fun': make_trad_upper_bound(trad_idx, effective_budget, trad_hi)},
]
```

---

### Issue 4: Optimizer Starting Point Scaling

**Location**: Cell 7

**Code**:
```python
scale = effective_budget / sum(current_spend[ch] for ch in channels)
x0 = np.array([current_spend[ch] * scale for ch in channels])
x0 = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])
x0 = x0 * effective_budget / x0.sum()
```

**Finding**: ✅ CORRECT BUT COMPLEX
- Double-scaling ensures x0 sums to effective_budget even after clipping
- Logic is correct but could be clearer

**Recommendation**: Add comments:
```python
# Initialize from current allocation, scaled to new budget
scale = effective_budget / sum(current_spend[ch] for ch in channels)
x0 = np.array([current_spend[ch] * scale for ch in channels])

# Enforce bounds (may break budget constraint temporarily)
x0 = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])

# Re-scale to match exact budget after clipping
x0 = x0 * effective_budget / x0.sum()
```

---

### Issue 5: Scenario Analysis Loop

**Location**: Cell 11

**Code**:
```python
scenarios = {
    'Cut 15%': 0.85, 'Cut 10%': 0.90, 'Cut 5%': 0.95,
    'Current': 1.00, 'Increase 10%': 1.10, 'Increase 20%': 1.20,
}

scenario_results = []
for name, mult in scenarios.items():
    budget = TOTAL_MONTHLY_BUDGET * mult
    alloc, res = optimize_budget_constrained(
        budget, CHANNELS, response_funcs, spend_bounds,
        CURRENT_SPEND, BUSINESS_CONSTRAINTS, eff_total
    )
    opt_resp = total_response([alloc[ch] for ch in CHANNELS], CHANNELS, response_funcs)
    scenario_results.append({...})
```

**Finding**: ✅ CORRECT
- Loop structure is clear
- Multiple optimizer runs reasonable for scenario analysis

**Enhancement**: Add convergence monitoring:
```python
scenario_results = []
convergence_issues = []
for name, mult in scenarios.items():
    budget = TOTAL_MONTHLY_BUDGET * mult
    alloc, res = optimize_budget_constrained(...)

    if not res.success:
        convergence_issues.append((name, res.message))
        print(f"⚠️ Scenario '{name}' did not converge: {res.message}")

    scenario_results.append({...})

if convergence_issues:
    print(f"\n⚠️  {len(convergence_issues)} scenarios had convergence issues:")
    for name, msg in convergence_issues:
        print(f"  - {name}: {msg}")
```

---

### Issue 6: Missing Error Handling for Zero Coefficients

**Location**: Cell 5, response function building

**Code**:
```python
coef = coefs_orig.get(coef_key, 0.0)
...
rev_pts = coef * sat_pts  # If coef=0, response is zero everywhere
func = interp1d(spend_pts, rev_pts, kind='cubic', ...)
```

**Finding**: ⚠️ SILENT FAILURE
- If coef=0 (non-significant channel), the interpolation still creates a function
- The function returns constant zero, which is correct but silent

**Risk**: No warning that this channel has zero contribution

**Recommendation**: Add informational logging:
```python
print(f'Response Functions:')
for ch in CHANNELS:
    coef = coefs_orig.get(f'media_{ch}_saturated', 0.0)
    if coef == 0:
        print(f'  {ch:20s} → ZERO coefficient (non-significant channel)')
    else:
        print(f'  {ch:20s} → coef=${coef:>12,.0f}')
```

---

## Summary of Code Issues

### Critical Issues (Require Fix)
None found. Code is implementationally sound.

### Medium Issues (Should Address)
1. **NB06b Issue 4**: Alpha selection for non-negative Ridge (currently uses unconstrained optimal alpha)
2. **NB07 Issue 2**: Confidence mapping logic is fragile

### Low Issues (Nice to Have)
1. **NB06b Issue 2**: Cache staleness detection
2. **NB06b Issue 5**: Adjusted R² formula for two-stage model
3. **NB06b Issue 6**: Column naming consistency
4. **NB06b Issue 7**: Missing metadata in output CSVs
5. **NB06b Issue 8**: Hard-coded paths
6. **NB07 Issue 1**: Response function extrapolation warning
7. **NB07 Issue 3**: Lambda closure clarity
8. **NB07 Issue 5**: Scenario convergence monitoring
9. **NB07 Issue 6**: Zero-coefficient logging

### Best Practices
- Add comprehensive docstrings to helper functions
- Include data provenance in output files
- Add progress monitoring for long-running operations
- Create config.yaml for hardcoded values (channel names, constraints, parameters)

---

## Conclusion

The code is **well-implemented with no critical errors**. The issues identified are mostly around documentation, robustness, and edge-case handling. The model's mathematical foundations are sound.
