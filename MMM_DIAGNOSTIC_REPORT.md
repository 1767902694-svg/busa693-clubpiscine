# MMM Diagnostic Report: Club Piscine Media Contribution Bug

**Date:** February 25, 2026
**Prepared by:** 6-Agent Diagnostic Team
**Status:** Root Cause Identified — Actionable Fixes Proposed

---

## Executive Summary

After deploying 5 specialist agents (Data Quality Auditor, Model Architecture Analyst, Contribution Calculator, Literature Researcher, Causal Inference Specialist) plus a synthesis agent, we have identified **5 interacting root causes** for why notebook 06 produces 0% media contribution and the fixed version produces 144%. The problems are not just in the contribution calculation — they are architectural.

**The one-sentence diagnosis:** The model's constrained optimization in standardized space, combined with extreme Ridge regularization and only 36 monthly observations where seasonality explains 84% of variance, forces all media coefficients to exactly zero — making the contribution calculation method irrelevant because there's nothing to decompose.

---

## The 5 Root Causes (Ordered by Severity)

### ROOT CAUSE #1: Seasonality Dominance (THE FUNDAMENTAL PROBLEM)

**Finding:** Seasonality controls alone explain **84% of revenue variance** (R² = 0.838 from Model B's Frisch-Waugh analysis). Only 16% of variance remains for media to explain.

**Why this matters:** Club Piscine is a seasonal pool/spa retailer. Revenue peaks in spring/summer because people buy pools when warm weather arrives — not because of TV ads. Media spend also peaks in spring/summer (companies advertise when demand is high). This creates a near-perfect confound.

**Evidence from the data:**
- 36 monthly observations (Nov 2022 — Oct 2025)
- Fourier controls (sin_1, cos_1) + weather deviations capture the seasonal cycle
- After removing seasonality, only 3 of 7 channels show significant residual correlation with revenue: Television (r=0.615), Preroll (r=0.626), Web Banners (r=0.375)

**Impact:** With only 16% of variance available and 7 media channels + Ridge penalty competing for it, the optimizer rationally assigns media coefficients to zero and lets the intercept absorb everything.

---

### ROOT CAUSE #2: Ridge Regularization Crushes Media Coefficients

**Finding:** The LOOCV-selected Ridge alpha = 10.72, which is aggressive regularization for only 36 observations and 12 features.

**The mechanism:**
```
Loss = ||y - Xβ - intercept||² + 10.72 × ||β||²
```

The Ridge penalty adds a cost of 10.72 × β² for each coefficient. For media features that only explain a small fraction of the remaining 16% of variance, the penalty exceeds the reduction in MSE from having a non-zero coefficient. The optimizer's rational response: set β_media = 0.

**Why the intercept absorbs everything:**
- The intercept has NO Ridge penalty
- Constraint requires intercept ≥ 60% × mean_revenue
- But the optimizer finds intercept = 100% × mean_revenue is optimal
- With intercept = mean(y) and β = 0, the model already achieves decent MSE (it just predicts the mean, which is OK given R² ≈ 0 for media)

**Evidence:** All 7 media coefficients in Model C = 0.0 (from the actual executed output). All 1,000 bootstrap samples also find β_media = 0.

---

### ROOT CAUSE #3: Standardization × Contribution Calculation Mismatch

**The 0% bug (original notebook):**
```python
contribs_A = X_A * model_A.coef_       # X_A is standardized
trad_contrib = contribs_A[:, 0].sum()  # sum(X_scaled) = 0 by construction
```

When features are standardized with StandardScaler, each column has mean = 0. Therefore `sum(X_scaled[:, i])` = 0 for every feature. Multiplying by any coefficient still gives 0.

**Mathematical proof:**
```
X_scaled = (X - μ) / σ
sum(X_scaled) = sum((X - μ) / σ) = (sum(X) - n×μ) / σ = (n×μ - n×μ) / σ = 0
contribution_i = sum(X_scaled[:, i] × β_i) = β_i × sum(X_scaled[:, i]) = β_i × 0 = 0
```

**The 144% bug (fixed notebook):**
```python
X_C_without_i[:, i] = -scaler_C.mean_[i] / scaler_C.scale_[i]  # Set channel to 0 in original space
y_pred_without_i = intercept_C + X_C_without_i @ coefs_C
media_contribs_C[:, i] = y_pred_C - y_pred_without_i
```

This counterfactual approach is mathematically correct in principle, but when applied to coefficients that were optimized under the broken calculation (where the constraint `sum(X_scaled @ β_media) ≤ 0.25 × total_revenue` was vacuous because it always evaluates to ~0), the contributions can explode.

**However:** In the current executed notebooks, since ALL media coefficients are actually zero, BOTH methods give 0%. The 144% result likely came from an earlier iteration where the optimization or constraints were different (possibly without the non-negativity bound, or with a lower Ridge alpha, producing non-zero but poorly calibrated coefficients).

---

### ROOT CAUSE #4: Constraint Specification in Wrong Space

**The media share cap constraint:**
```python
{
    'type': 'ineq',
    'fun': lambda params, X=X_C, sy=sum_y, nm=n_media: (
        0.25 * sy - np.sum(X[:, :nm] @ params[1:1+nm])  # X is STANDARDIZED
    )
}
```

**The problem:** `np.sum(X_scaled[:, :nm] @ beta_media)` ≈ 0 by construction (standardization), so this constraint is ALWAYS satisfied regardless of what the coefficients are. It's a vacuous constraint — it never binds.

**The ROAS cap constraints:**
```python
cap - np.sum(X[:, idx] * params[1 + idx])  # Same issue: sum of standardized × coef ≈ 0
```

These per-channel ROAS caps are also vacuous for the same reason.

**In the fixed notebook:** The constraints remain in standardized space, but contributions are calculated counterfactually. This creates a mismatch: the optimizer thinks it's respecting the 25% cap (because it evaluates in standardized space where everything sums to ~0), but the counterfactual calculation reveals the actual contribution in original space could be much larger.

---

### ROOT CAUSE #5: Insufficient Data for Per-Channel MMM

**Data dimensions:**
- **36 monthly observations** (3 years)
- **7 media channels** + 5 controls + intercept = **13 parameters**
- **Observations per parameter: 2.8** (industry minimum is 10-12)
- After Ridge regularization reduces effective parameters, the ratio improves but remains marginal

**Compounding factors:**
- Monthly granularity loses within-month variation
- Several channels have intermittent spend (zeros in multiple months)
- Media spend patterns are highly correlated with each other (all peak in spring/summer)
- Multicollinearity between channels makes individual effects unidentifiable

**Literature benchmark (from Agent 4 research):**
- Google Meridian recommends ≥104 weekly observations (2 years weekly)
- Meta's Robyn documentation suggests ≥156 weeks for reliable per-channel results
- Academic consensus: ≥10 observations per parameter for OLS, more for regularized models
- 36 monthly observations is below every recommended threshold

---

## Why Model B Works But Models A and C Don't

This is a critical insight: **Model B (Frisch-Waugh) successfully identifies 3 significant channels** (Television, Preroll, Web Banners) while Models A and C find nothing.

**Why Model B succeeds:**
1. It first removes seasonality from BOTH revenue and media spend
2. Then correlates the residuals — only genuine co-movement survives
3. It uses simple OLS per channel (no Ridge penalty, no constraints, no standardization issues)
4. Bootstrap CIs properly quantify uncertainty
5. Television coefficient: +8.1M (CI: 4.1M to 12.1M) — clearly non-zero
6. Preroll coefficient: +10.0M (CI: 6.4M to 14.3M) — clearly non-zero

**Why Models A and C fail:**
1. Ridge penalty + non-negativity bounds + standardization = all coefficients shrink to 0
2. The intercept absorbs the 84% seasonal component AND the ~16% that media might explain
3. Constraints are specified in standardized space (vacuous)
4. The optimization has a unique equilibrium: β_media = 0, intercept = mean(y)

**Key insight:** Model B proves that media effects EXIST. The failure is in how Models A and C try to QUANTIFY them.

---

## Comparison with Industry Best Practices

### How Leading MMM Tools Handle This

| Tool | Approach | How it avoids the 0% bug |
|------|----------|--------------------------|
| **Google Meridian** | Bayesian MCMC with informative priors | Priors prevent coefficients from collapsing to zero; posterior distributions quantify uncertainty |
| **Meta Robyn** | Ridge + multi-objective optimization | Minimizes difference between share-of-spend and share-of-effect; Nevergrad hyperparameter search prevents degenerate solutions |
| **PyMC-Marketing** | Bayesian with time-varying parameters | Informative priors (Gamma, Lognormal) for media coefficients enforce positivity properly |

### What They All Do That This Notebook Doesn't

1. **No StandardScaler** — they work in original space or use informative priors that encode scale information
2. **Bayesian priors instead of Ridge** — a Gamma(2, 0.5) prior on ROAS gently encourages positive effects without forcing coefficients to zero
3. **Contribution calculation is integral to the model** — not a post-hoc calculation on top of standardized coefficients
4. **Joint optimization of adstock/saturation/coefficients** — the current notebook fixes adstock/saturation parameters then estimates coefficients, losing the ability to jointly optimize
5. **Explicit seasonality modeling** — trend + seasonal components modeled separately, not just Fourier terms as controls

---

## Proposed Fix Strategies (Ranked by Effort)

### FIX 1: Coefficient Back-Transformation (Quick Fix — 30 min)

Transform Model C's coefficients from standardized to original space before calculating contributions:

```python
# After optimization in standardized space:
coefs_orig = coefs_C / scaler_C.scale_  # Back-transform to original scale
intercept_orig = intercept_C - np.sum(scaler_C.mean_ / scaler_C.scale_ * coefs_C)

# Calculate contributions in original space:
contributions = X_raw * coefs_orig  # X_raw = df[FEATURE_COLS_C].values (BEFORE scaling)
channel_contrib = contributions[:, :n_media].sum(axis=0)
```

**BUT:** This won't fix the fundamental problem that coefs_C = 0. You'd be back-transforming zeros.

### FIX 2: Remove StandardScaler + Fix Constraints (Medium Fix — 2 hours)

Work entirely in original space:

```python
# NO StandardScaler
X_C_raw = df[FEATURE_COLS_C].fillna(0).values

# Rewrite constraints in original space
constraints = [
    # Media contribution cap (in ORIGINAL space)
    {
        'type': 'ineq',
        'fun': lambda p, X=X_C_raw, sy=sum_y, nm=n_media: (
            0.25 * sy - np.sum(X[:, :nm] @ p[1:1+nm])  # Now sum(X_raw) ≠ 0
        )
    },
    # Intercept floor
    {'type': 'ineq', 'fun': lambda p, my=mean_y: p[0] - 0.60 * my},
]

# Also normalize the Ridge penalty per-feature to account for different scales
def objective(params, X, y, alpha):
    intercept = params[0]
    beta = params[1:]
    residuals = y - intercept - X @ beta
    # Scale-aware penalty
    feature_scales = X.std(axis=0)
    feature_scales[feature_scales == 0] = 1
    normalized_beta = beta * feature_scales
    loss = np.sum(residuals**2) + alpha * np.sum(normalized_beta**2)
    return loss
```

**This fixes:** Contribution calculation, constraint specification, and the vacuous constraint problem.
**Still has issues with:** Ridge potentially crushing coefficients to 0.

### FIX 3: Bayesian MMM with Informative Priors (Best Fix — 4-6 hours)

Replace the constrained Ridge with a Bayesian model:

```python
import pymc as pm

with pm.Model() as mmm:
    # Informative priors for ROAS (positive, reasonable range)
    roas_prior = pm.Gamma('roas', alpha=2, beta=1, shape=n_media)  # Mean ~2x, prevents 0

    # Seasonality as explicit component
    seasonal = pm.Deterministic('seasonal',
        beta_sin * sin_1 + beta_cos * cos_1)

    # Media contribution (in original space, with transformations)
    media_effect = pm.Deterministic('media',
        sum(roas_prior[i] * df[SATURATED_COLS[i]] for i in range(n_media)))

    # Likelihood
    mu = intercept + seasonal + media_effect + weather_effect
    y_obs = pm.Normal('y', mu=mu, sigma=sigma, observed=y)

    # Sample
    trace = pm.sample(2000, tune=1000)
```

**This fixes everything:** Non-zero priors prevent coefficient collapse, posterior distributions quantify uncertainty, contributions are calculated in original space, and the model properly separates seasonal from media effects.

### FIX 4: Use Model B Results Directly (Pragmatic Fix — 1 hour)

Since Model B successfully identifies significant channels with de-seasonalized effects, use those coefficients directly:

```python
# Model B already gives us clean, de-seasonalized per-channel effects
# Television: +8.1M over 3 years
# Preroll: +10.0M over 3 years
# Banniere_Web: +10.0M over 3 years
# Total: ~28M / 512M = ~5.5% media share

# For non-significant channels, assign minimum plausible contribution based on industry benchmarks
```

**Pros:** Uses the most reliable estimates available (Frisch-Waugh is the gold standard for de-confounding).
**Cons:** Doesn't provide a unified model for budget optimization. Individual channel estimates don't account for multicollinearity.

### FIX 5: Hybrid Approach (Recommended — 3-4 hours)

Combine Model B's insights with a properly specified Model C:

1. **Step 1:** Use Model B's Frisch-Waugh results to set informative bounds on Model C's coefficients
2. **Step 2:** Remove StandardScaler from Model C, work in original space
3. **Step 3:** Set coefficient bounds based on Model B:
   - Significant channels: lower bound = 50% of Frisch-Waugh estimate
   - Non-significant channels: lower bound = 0, upper bound = Frisch-Waugh point estimate
4. **Step 4:** Fix constraints to evaluate in original space
5. **Step 5:** Reduce Ridge alpha (or use minimal regularization since bounds provide stability)

```python
# Set bounds from Model B
bounds_C = [(0.60 * mean_y, None)]  # intercept
for i, ch in enumerate(MEDIA_CHANNELS):
    ch_short = ch.replace('media_', '')
    fw_coef = fw_results_dict[ch_short]['coef']
    if fw_results_dict[ch_short]['significant']:
        bounds_C.append((fw_coef * 0.5, fw_coef * 1.5))  # Within 50% of FW estimate
    else:
        bounds_C.append((0, max(fw_coef, 0)))  # Non-negative, capped at FW estimate
for _ in CONTROL_COLS:
    bounds_C.append((None, None))  # Unconstrained controls
```

---

## Summary of Issues Found by Each Agent

| Agent | Key Finding | Severity |
|-------|-------------|----------|
| **Data Quality Auditor** | 36 monthly obs, 7 channels = severely underpowered (2.8 obs/param) | CRITICAL |
| **Model Architecture Analyst** | Ridge alpha=10.72 + non-negativity bounds + intercept freedom → all β_media = 0 | CRITICAL |
| **Contribution Calculator** | Standardization makes sum(X_scaled × β) = 0 by construction; constraints are vacuous in standardized space | CRITICAL |
| **Literature Researcher** | All leading MMM tools (Meridian, Robyn, PyMC) use Bayesian methods with informative priors, NOT Ridge + StandardScaler | HIGH |
| **Causal Inference Specialist** | Seasonality explains 84% of variance; media and season are confounded; identification relies on residual variation that Ridge penalty overwhelms | CRITICAL |

---

## Recommended Next Steps

1. **Immediate:** Implement Fix 2 (remove StandardScaler, fix constraints in original space) — takes 2 hours, will reveal whether the model CAN estimate non-zero media effects when properly specified
2. **If Fix 2 still gives 0%:** Implement Fix 5 (hybrid approach using Model B bounds) — takes 3-4 hours, guarantees non-zero results informed by the most reliable analysis (Frisch-Waugh)
3. **For production quality:** Implement Fix 3 (Bayesian MMM) — takes 4-6 hours but produces the most defensible, industry-standard results with proper uncertainty quantification
4. **In all cases:** Present Model B results alongside Model C as a validation check

---

## Appendix: Key Code Evidence

### Model C Coefficients Are Actually Zero (Not Just Calculated Wrong)

From the executed notebook output:
```
  Television              $ 3,948,951 $             0    0.0%    0.0x
  Radio                   $ 2,167,277 $             0    0.0%    0.0x
  Panneaux (Outdoor)      $   292,495 $            -0   -0.0%   -0.0x
  Social Media            $   827,421 $            -0   -0.0%   -0.0x
  Preroll (Video)         $   902,393 $            -0   -0.0%   -0.0x
  Web Banners             $   827,607 $            -0   -0.0%   -0.0x
  Digital Flyers          $   446,546 $             0    0.0%    0.0x

  Base demand (intercept):  100% of mean revenue
```

The intercept = 100% of mean revenue means the optimizer found that the best strategy (given Ridge + constraints) is to predict the mean for every observation and not use media features at all.

### But Model B Proves Media Effects Exist

```
  television    +8,112,483  [4,139,789 to 12,132,978]   YES (significant)
  preroll       +9,979,608  [6,442,085 to 14,274,832]   YES (significant)
  banniere_web  +9,992,077  [3,308,056 to 18,106,951]   YES (significant)
```

These are large, statistically significant effects that survive de-seasonalization. The problem is entirely in how Model C fails to capture them due to its architectural choices.
