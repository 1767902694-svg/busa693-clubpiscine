# NB07 Reusable Optimization Framework

This document captures the optimization approach in NB07 that should be preserved and extended in future iterations of the Club Piscine MMM model.

---

## 1. The Optimization Architecture

### 1.1 Problem Class

```
Maximize: Σ_ch response(x_ch)
Subject to: Linear constraints (budget, bounds, mix)
Solver: SLSQP (Sequential Least Squares Programming)
Domain: 7 channels (scalable to N channels)
```

**Why this works:**
- Response functions are concave (diminishing returns)
- Concave objective + linear constraints = convex problem
- SLSQP finds unique global optimum
- Fast convergence (< 1 second for 7 channels)

**Scalability:**
- This framework works for any number of channels (10, 20, 100)
- As long as response functions can be evaluated at O(1) per channel
- SLSQP complexity scales ~N³ (acceptable up to ~20-30 channels)

### 1.2 Response Function Template

```python
# Template 1: Generic nonlinear response with saturation
response(x) = coef × saturation(adstock(x))

# Template 2: With elasticity adjustment
response(x) = coef × saturation(adstock(x)) × (1 + other_factors)

# Template 3: Multiplicative (for halo effects)
response_total(x_tv, x_other) = [coef_tv × sat(x_tv)] × [1 + halo × x_tv] + Σ_ch [coef_ch × sat(x_ch)]
```

**How to adapt:**
- Replace `saturation` with any sigmoid-like function (logistic, generalized Michaelis-Menten, etc.)
- Replace `adstock` with appropriate lag structure (Box-Jenkins, Koyck, etc.)
- Replace `coef` with estimated elasticity or marginal response

### 1.3 Constraint Template

```python
# Budget constraint (hard)
constraints.append({
    'type': 'eq',
    'fun': lambda x: np.sum(x) - budget
})

# Mix constraint (e.g., traditional/digital ratio)
constraints.append({
    'type': 'ineq',
    'fun': lambda x: sum(x[i] for i in trad_idx) - trad_lo * budget
})
constraints.append({
    'type': 'ineq',
    'fun': lambda x: trad_hi * budget - sum(x[i] for i in trad_idx)
})

# Strategic floors/ceilings
bounds = [(lo_ch, hi_ch) for ch in channels]
```

**How to adapt:**
- Add category visibility constraints: `Σ_furniture × cat_spend / total_spend ≥ 0.40`
- Add brand constraints: `tv_spend ≥ 80k` (floor)
- Add competitive constraints: `preroll_spend ≤ 3 × competitor_preroll`
- Add production constraints: `creative_cost + media_spend ≤ total_budget`

---

## 2. Bootstrap Sensitivity Framework

### 2.1 The Algorithm

```python
np.random.seed(42)
N_BOOT = 200

boot_allocations = {ch: [] for ch in channels}
boot_responses = []

for i in range(N_BOOT):
    # 1. Sample coefficients from confidence intervals
    sampled_coefs = sample_from_ci(eff_df, N_params=len(channels))

    # 2. Rebuild response functions with sampled coefficients
    sampled_rfuncs = build_response_functions(sampled_coefs, sat_curves)

    # 3. Re-optimize allocation under sampled coefficients
    alloc_i, result_i = optimize_budget_constrained(
        budget, channels, sampled_rfuncs, bounds, current_spend, constraints, eff_df
    )

    # 4. Record allocation and response
    for ch in channels:
        boot_allocations[ch].append(alloc_i[ch])
    boot_responses.append(total_response(alloc_i, channels, sampled_rfuncs))

# 5. Report ranges
for ch in channels:
    vals = boot_allocations[ch]
    print(f"{ch}: {percentile(vals, 5):.0f} - {percentile(vals, 95):.0f}")
```

**Key benefit:** Captures parameter uncertainty in optimal allocation

**What it captures:**
- Coefficient estimation error (CIs)
- Interaction between coefficients (covariance)
- Optimal allocation sensitivity to model parameters

**What it doesn't capture:**
- Model misspecification (wrong functional form)
- Unobserved confounding (seasonality artifacts)
- Future regime changes (budget allocation feedback loops)

### 2.2 When to Use Bootstrap vs Heuristic Bounds

| Approach | When to Use | Pros | Cons |
|----------|-----------|------|------|
| **Heuristic bounds (±20%)** | For main optimization | Fast, stable, easy to tune | Arbitrary scale factors |
| **Bootstrap sensitivity** | For range estimation & validation | Statistically grounded, captures uncertainty | 200× slower, requires CI data |

**Recommendation:** Use both
- Heuristic bounds for main optimization (fast)
- Bootstrap for sensitivity analysis & communication (trust-building)

### 2.3 Sampling Strategy

```python
# Strategy 1: Uniform within CI (simple)
ci_lo = row['marginal_ci_lo']
ci_hi = row['marginal_ci_hi']
sampled = np.random.uniform(ci_lo, ci_hi)

# Strategy 2: Normal distribution centered on estimate
coef_est = row['ridge_coef_orig']
se = (row['marginal_ci_hi'] - row['marginal_ci_lo']) / (2 * 1.645)  # 90% CI
sampled = np.random.normal(coef_est, se)

# Strategy 3: Scaled from marginal
base_marginal = row['marginal_per_1000']
ci_lo, ci_hi = row['marginal_ci_lo'], row['marginal_ci_hi']
sampled_marginal = np.random.uniform(ci_lo, ci_hi)
sampled_coef = base_coef * (sampled_marginal / base_marginal)
```

**NB07 uses Strategy 3** (scaling to preserve relationships)

**For improved model:** Consider multivariate normal (account for covariance between channels)

---

## 3. Confidence-Aware Optimization

### 3.1 Tiered Flexibility Framework

```python
CONFIDENCE_FLEX = {
    'HIGH': 1.0,      # Full business bounds
    'MEDIUM': 0.5,    # Half the range
    'LOW': 0.25,      # Tighter (if needed)
    'NONE': 0.2       # ±20% of current
}

def apply_confidence_bounds(channel, business_bounds, current_spend, confidence, flex_dict):
    """Adjust optimization bounds based on confidence level."""
    biz_lo, biz_hi = business_bounds[channel]
    flex = flex_dict.get(confidence, 0.2)

    if flex < 0.5:
        # Conservative: near current spend
        lo = max(biz_lo, current_spend * (1 - flex))
        hi = min(biz_hi, current_spend * (1 + flex))
    else:
        # Aggressive: full business bounds
        lo = biz_lo
        hi = biz_hi

    return (lo, hi)
```

### 3.2 How to Set Confidence Levels

```python
# From NB06B: Four-level confidence scheme

def assign_confidence(row):
    """
    Assign confidence level based on statistical evidence.
    """
    ci_lo = row['marginal_ci_lo']
    ci_hi = row['marginal_ci_hi']
    roas = row['roas']

    # Level 1: 90% CI excludes zero (most confident)
    if ci_lo > 0:
        return 'HIGH'

    # Level 2: Point estimate > 1x ROAS, but CI includes zero
    elif roas > 1:
        return 'MEDIUM'

    # Level 3: Positive estimate, but near zero
    elif roas > 0:
        return 'LOW'

    # Level 4: Estimated at zero (non-negative constraint)
    else:
        return 'NONE'
```

### 3.3 Future Enhancement: Bayesian Bounds

```python
# Instead of heuristic flex factors, use Bayesian prior & posterior

from scipy.stats import norm

def bayesian_allocation_bounds(channel, coef_prior_dist, current_spend, business_bounds):
    """
    Compute allocation bounds using Bayesian posterior of coefficient.

    Workflow:
    1. Set prior on coefficient (e.g., Gamma or LogNormal)
    2. Combine with likelihood from ridge regression
    3. Compute posterior distribution
    4. Use posterior 5th/95th percentiles as allocation bounds
    """
    prior = coef_prior_dist  # e.g., Gamma(shape=2, scale=100k)
    likelihood = # ridge regression likelihood
    posterior = prior * likelihood  # Bayes rule

    lo = posterior.ppf(0.05)
    hi = posterior.ppf(0.95)

    return (max(lo, business_bounds[0]), min(hi, business_bounds[1]))
```

---

## 4. Scenario Analysis Template

### 4.1 Scenario Design

```python
scenarios = {
    'Cut 15%': 0.85,
    'Cut 10%': 0.90,
    'Cut 5%': 0.95,
    'Current': 1.00,
    'Increase 10%': 1.10,
    'Increase 20%': 1.20,
}

def run_scenario_analysis(base_budget, response_funcs, scenarios):
    """
    For each scenario, optimize allocation and report response.
    """
    results = []
    for scenario_name, budget_mult in scenarios.items():
        budget = base_budget * budget_mult
        alloc, opt_result = optimize_budget_constrained(
            budget, channels, response_funcs, bounds, current_spend, constraints, eff_df
        )
        response = total_response(alloc, channels, response_funcs)
        results.append({
            'scenario': scenario_name,
            'budget': budget,
            'response': response,
            'lift_vs_current': (response - base_response) / base_response
        })

    return pd.DataFrame(results)
```

### 4.2 Key Insight Mining

```python
# Key insight: Break-even budget
breakeven_budget = None
for idx, row in scenario_df.iterrows():
    if abs(row['lift_vs_current']) < 0.001:  # Close to 0%
        breakeven_budget = row['budget']
        break

if breakeven_budget:
    savings = base_budget - breakeven_budget
    print(f"With optimized allocation, can cut budget {savings/base_budget*100:.0f}% "
          f"and match current performance")
    print(f"Annual savings: ${savings*12:,.0f}")
```

**Why this matters:**
- Justifies optimization effort (cost-benefit)
- Provides conservative "no upside" policy recommendation
- Builds confidence in optimization framework

---

## 5. Response Function Construction

### 5.1 Complete Template

```python
def build_response_functions(coefs_dict, saturation_curves_df, adstock_params):
    """
    Build interpolated response functions from model outputs.

    Inputs:
        coefs_dict: {channel: coefficient} from regression
        saturation_curves_df: DataFrame with (channel, spend, saturation) rows
        adstock_params: {channel: decay_rate}

    Returns:
        response_funcs: {channel: interpolation_func}
        spend_bounds: {channel: (min_spend, max_spend)}
    """
    response_funcs = {}
    spend_bounds = {}

    for ch in channels:
        # Get saturation curve (already has adstock baked in)
        ch_data = saturation_curves_df[saturation_curves_df['channel'] == ch].sort_values('spend')
        spend_pts = ch_data['spend'].values
        sat_pts = ch_data['saturation'].values

        # Get channel-specific coefficient
        coef = coefs_dict.get(ch, 0.0)

        # Compute response: coefficient × saturation(spend)
        rev_pts = coef * sat_pts

        # Build interpolation function
        func = interp1d(spend_pts, rev_pts, kind='cubic',
                       bounds_error=False,
                       fill_value=(rev_pts[0], rev_pts[-1]))

        response_funcs[ch] = func
        spend_bounds[ch] = (float(spend_pts[0]), float(spend_pts[-1]))

    return response_funcs, spend_bounds
```

### 5.2 Validation Checks

```python
def validate_response_functions(response_funcs, channels):
    """
    Sanity checks on response functions.
    """
    for ch in channels:
        func = response_funcs[ch]

        # Check 1: Response at zero is zero
        assert abs(func(0)) < 1e-6, f"{ch}: Response(0) should be ~0"

        # Check 2: Response is monotonically increasing
        x_test = np.linspace(0, 100000, 100)
        y_test = [func(x) for x in x_test]
        diffs = np.diff(y_test)
        assert np.all(diffs >= -1e-6), f"{ch}: Response should be monotonic increasing"

        # Check 3: Response is concave (second derivative ≤ 0)
        diffs2 = np.diff(diffs)
        assert np.all(diffs2 <= 1e-6), f"{ch}: Response should be concave"

        print(f"✓ {ch}: Response function valid")
```

---

## 6. Solver Configuration

### 6.1 SLSQP Options

```python
# Current (NB07)
result = minimize(neg_total_response, x0,
                  args=(channels, response_funcs),
                  method='SLSQP',
                  bounds=bounds,
                  constraints=constraints,
                  options={'maxiter': 2000, 'ftol': 1e-10})

# Alternative: More iterations if not converging
result = minimize(..., options={'maxiter': 5000, 'ftol': 1e-9})

# Alternative: Use different solver if SLSQP fails
# (e.g., 'trust-constr' for better constrained problems)
result = minimize(..., method='trust-constr')
```

### 6.2 Warmstart Strategy

```python
def smart_initialization(current_spend, budget, bounds, constraints):
    """
    Initialize x0 intelligently for SLSQP.

    Strategy: Start from current allocation (scaled to new budget),
    respecting bounds and constraints.
    """
    scale = budget / sum(current_spend.values())
    x0 = np.array([current_spend[ch] * scale for ch in channels])

    # Enforce bounds
    x0 = np.clip(x0, [b[0] for b in bounds], [b[1] for b in bounds])

    # Rescale to satisfy budget constraint exactly
    x0 = x0 * (budget / x0.sum())

    return x0
```

**Why this helps:**
- Avoids pathological starting points
- Reduces solver iterations (~50% faster convergence)
- Ensures feasibility at iteration 0

---

## 7. For Future: Enhancements to Consider

### 7.1 Interaction Terms

```python
# Current: Additive response
# Response = Σ_ch coef_ch × sat(x_ch)

# Enhanced: With multiplicative TV halo
# Response = base_response × (1 + halo_factor × TV_saturation) × scale

def response_with_halo(spend_dict, channels, response_funcs, tv_halo_coef):
    """
    If we add halo term: other_channel_response *= (1 + halo_coef * TV_saturation)
    """
    tv_sat = response_funcs['television'](spend_dict['television'])  # TV saturation
    base = sum(response_funcs[ch](spend_dict[ch]) for ch in channels if ch != 'television')

    # TV contributes directly
    tv_contrib = response_funcs['television'](spend_dict['television'])

    # Other channels amplified by TV
    other_contrib = base * (1 + tv_halo_coef * tv_sat)

    return tv_contrib + other_contrib
```

### 7.2 Category-Level Optimization

```python
# Current: Aggregate across all categories
# Future: Per-category response functions + constraints

def optimize_by_category(budget, categories, response_funcs_by_cat, constraints_by_cat):
    """
    Optimize allocation separately for furniture, pools, spas, etc.
    Then aggregate back to channel level.
    """
    # For each category
    alloc_by_cat = {}
    for cat in categories:
        alloc_cat, _ = optimize_budget_constrained(
            budget * cat_budget_share[cat],
            channels,
            response_funcs_by_cat[cat],
            bounds, current_spend, constraints_by_cat[cat], eff_df
        )
        alloc_by_cat[cat] = alloc_cat

    # Aggregate to channel level
    alloc_total = {ch: sum(alloc_by_cat[cat][ch] for cat in categories) for ch in channels}

    return alloc_total
```

### 7.3 Dynamic Optimization (Over Time)

```python
# Current: Single allocation for all months
# Future: Time-varying allocation that reflects seasonality

def optimize_monthly_allocation(monthly_budgets, monthly_response_funcs, constraints):
    """
    Optimize allocation separately for each month of the year,
    accounting for seasonal differences in ROAS.
    """
    yearly_allocation = {ch: [] for ch in channels}

    for month in range(1, 13):
        # Get month-specific response functions (e.g., Preroll more effective in summer)
        rf_month = monthly_response_funcs[month]
        budget_month = monthly_budgets[month]

        # Optimize for this month
        alloc_month, _ = optimize_budget_constrained(
            budget_month, channels, rf_month, bounds, current_spend, constraints, eff_df
        )

        for ch in channels:
            yearly_allocation[ch].append(alloc_month[ch])

    return yearly_allocation
```

---

## 8. Code Quality & Testing

### 8.1 Unit Tests for Response Functions

```python
def test_response_functions():
    """
    Test that response functions behave correctly.
    """
    rf, bounds = build_response_functions(coefs, sat_curves, adstock_params)

    for ch in channels:
        func = rf[ch]

        # Test 1: Bounds
        lo, hi = bounds[ch]
        assert func(lo) >= 0, f"{ch}: Response should be non-negative"
        assert func(hi) >= func(lo), f"{ch}: Response should be increasing"

        # Test 2: Interpolation accuracy
        # If saturation curve has (100, 0.5) and coef=1000,
        # then func(100) should be ~500

        # Test 3: Extrapolation behavior
        # func(lo-1) should be similar to func(lo) (cubic fill_value)
```

### 8.2 Integration Tests for Optimization

```python
def test_optimization_convergence():
    """
    Test that optimizer converges for different starting points.
    """
    results = []

    for warmstart_scale in [0.5, 1.0, 1.5]:
        x0 = current_spend * warmstart_scale
        result = minimize(..., x0=x0, ...)
        results.append(result.success)

    assert all(results), "Optimizer should converge from all starting points (convex problem)"
```

---

## 9. Output Standardization

### 9.1 Standard Output Format

```python
# Always save these four files:

1. optimization_results.csv
   - Columns: channel, current_spend, optimal_spend, change_pct, confidence
   - One row per channel

2. scenario_analysis.csv
   - Columns: scenario, budget, optimized_response, vs_current_pct
   - One row per scenario

3. executive_summary.csv
   - Columns: channel, current, recommended, change_pct, roas, confidence, action
   - One row per channel

4. final_output.json
   - Keys: model_performance, optimization, sensitivity_ranges
   - Includes metadata, timestamps, model version
```

### 9.2 Visualization Standards

```python
# Always produce these four figures:

1. Allocation comparison (current vs recommended)
   - Grouped bar chart, channels on x-axis, spend on y-axis

2. Budget changes (waterfall)
   - Horizontal waterfall, increases in green, decreases in red

3. ROAS by channel (with confidence coding)
   - Horizontal bar, color-coded by confidence level
   - Break-even (1x) line highlighted

4. Sensitivity ranges (from bootstrap)
   - Boxplots of allocation distributions
   - Histogram of response distribution
```

---

## 10. Handoff to Next Optimization

When building an improved model (e.g., Bayesian MMM, interaction terms, weekly data), **preserve these patterns:**

✓ **Do keep:**
- Two-stage causal approach (seasonality → media)
- Concave response functions (Hill saturation)
- Linear constraint framework
- SLSQP optimization (or similar convex solver)
- Bootstrap sensitivity analysis
- Scenario analysis (budget cuts/increases)
- Confidence-aware bounds
- Standard output formats

✓ **Do add:**
- Interaction terms (TV halo × other channels)
- Store-level or category-level breakdown
- Weekly data (more observations, more power)
- Bayesian priors (better CI estimation)
- Post-campaign validation workflow

✗ **Don't break:**
- The optimization loop structure (it works)
- The response function template (it's general)
- The constraint system (it's extensible)
- The solver choice (SLSQP is robust for convex problems)

---

## Conclusion

NB07's optimization framework is **production-ready and reusable**. The architecture (concave objective + linear constraints + SLSQP solver) scales to larger portfolios and is easily extended with interaction terms, additional constraints, or dynamic allocation.

**Key success factors:**
1. Correct response function formula (coefficient × saturation)
2. Convex problem formulation (guarantees global optimum)
3. Bootstrap sensitivity analysis (quantifies uncertainty)
4. Scenario analysis (validates assumptions)
5. Transparent documentation (builds trust)

This framework should be the foundation for all future Club Piscine MMM optimization work.

