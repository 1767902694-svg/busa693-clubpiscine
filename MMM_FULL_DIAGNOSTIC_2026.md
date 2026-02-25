# MMM Full Diagnostic Report — Club Piscine
## 6-Agent Specialized Analysis: Why Media Contribution is 0% or 144%
**Date:** February 25, 2026
**Commissioned by:** TA (Tabarek Al-khalidi)
**Scope:** Complete root cause analysis of Marketing Mix Model failure

---

## EXECUTIVE SUMMARY

Six specialized diagnostic agents with deep ML/causal inference expertise have independently analyzed the Club Piscine MMM pipeline. **All six agents converge on the same diagnosis:** this is not a simple calculation bug — it is a compound failure with **three interlocking root causes** that must all be addressed together.

### The Three Root Causes

| # | Root Cause | Severity | Agent(s) |
|---|-----------|----------|----------|
| 1 | **Contribution calculation operates in wrong space** — Method A sums standardized features (=0 by math), Method B uses counterfactual with negative baseline (=144%) | CRITICAL | Agents 2, 3 |
| 2 | **Unbounded saturation transforms create 326x scale imbalance** — log/power transforms are not bounded [0,1] like Hill, causing StandardScaler to distort Ridge regularization unevenly across channels | CRITICAL | Agent 5 |
| 3 | **Fundamental under-identification** — N=36 with 12 features (3:1 ratio vs. 10:1 minimum), plus media-seasonality confounding means the model cannot reliably separate media from organic demand | STRUCTURAL | Agents 1, 4, 6 |

### Why Each Method Fails

**Method A (0% contribution):** StandardScaler centers features so `sum(X_scaled) = 0` for every feature. Therefore `sum(X_scaled × coef) = coef × 0 = 0`. This is a mathematical identity, not a model result.

**Method B (144% contribution):** Setting a channel to zero in original space maps to an extreme negative z-score in standardized space (e.g., radio maps to -2.05 SDs). The model's intercept in original space is **negative** (-$6.3M to -$8.3M depending on calculation), meaning the model claims revenue would be deeply negative without media. This is economically absurd and reveals model non-identification.

---

## DETAILED FINDINGS BY AGENT

### Agent 1: Data Quality & Preprocessing Audit

**Key findings:**
- **Data is clean** — no missing values, no zero-inflation issues, no outlier problems
- **The problem is NOT data quality but data ADEQUACY**
- N=36 with 12 features gives a 3:1 ratio (industry minimum is 10:1, requiring 120 observations)
- With only 23 degrees of freedom, R²=0.93 likely reflects overfitting (random data with 12 params on 36 obs would give R²≈0.33)
- **57% of channels (4 of 7) are confounded with seasonality** — the Frisch-Waugh analysis in the model found only TV, Preroll, and Web Banners are identifiable
- Media spend peaks in summer, same as revenue → the model cannot distinguish "people buy pools because it's summer" from "people buy pools because we advertised"

### Agent 2: Model Architecture & Optimization Review

**Key findings:**
- Ridge regression is a reasonable choice but insufficient for this problem
- The intercept in standardized space (14.2M) is mathematically correct but misleading
- When properly un-standardized: `intercept_original = 14.2M - sum(beta × mean/scale) ≈ -6.3M`
- A **negative baseline** means the model says Club Piscine would LOSE $6.3M/year without advertising — economically impossible for a retail chain
- LOOCV R² = 0.86 vs training R² = 0.93 → 7 percentage point gap confirms overfitting
- The model architecture itself (standardize → Ridge → decompose) is sound IF contributions are calculated correctly AND the model is properly identified

### Agent 3: Contribution Calculation Mathematics

**Key findings — the CORRECT formula:**

The model in standardized space:
```
y = intercept_std + Σ(beta_std_j × (x_j - mean_j) / scale_j)
```

Rearranging to original space:
```
y = [intercept_std - Σ(beta_std_j × mean_j / scale_j)] + Σ[(beta_std_j / scale_j) × x_j]
     \_____________________________________________/      \________________________/
              intercept_original                           original-space slopes
```

**Correct contribution for channel j:**
```
contribution_j = (beta_std_j / scale_j) × Σ(x_j_original over all time periods)
```

**Numerical results using model params:**
| Channel | beta_std | scale | beta_original | Estimated contribution offset |
|---------|----------|-------|---------------|-------------------------------|
| Television | 1,740,634 | 0.459 | 3,792,155 | Large |
| Radio | 1,193,229 | 149.87 | 7,961 | Small per unit (but high volume) |
| Panneaux | 261,412 | 84.98 | 3,076 | Small |
| Social Media | 1,317,357 | 30.32 | 43,442 | Moderate |
| Preroll | 2,192,998 | 0.399 | 5,501,000 | Very large |
| Web Banners | 1,410,944 | 0.270 | 5,225,348 | Very large |
| Digital Flyers | 762,924 | 60.41 | 12,631 | Small per unit |

**Critical: Even with correct decomposition, contributions still sum to >100% because the model coefficients are too large relative to the intercept. The correct formula reveals (not fixes) the underlying model identification problem.**

### Agent 4: Literature & Best Practices Review

**Key findings:**
- **Google (Meridian/LightweightMMM):** Uses Bayesian approach with adstock + Hill saturation, waterfall decomposition
- **Meta (Robyn):** Uses Ridge + Prophet time series decomposition FIRST, then media estimation — critical difference from current approach
- **PyMC-Marketing:** Bayesian with proper uncertainty quantification
- **Academic consensus:** For N < 50, Bayesian methods with informative priors are strongly preferred
- **Industry standard:** Media typically explains 10-40% of revenue for retail businesses — 144% is a red flag that should trigger automatic validation
- **Waterfall decomposition** (not sum-of-scaled-products) is the accepted method
- **Robyn's approach is most relevant:** Decompose seasonality with Prophet FIRST, then regress residuals on media. This directly addresses the confounding problem.

### Agent 5: Adstock/Saturation Transform Validation

**Key findings — CRITICAL DESIGN FLAW:**
- **Hill saturation** outputs values in [0, 1] — bounded, well-behaved
- **Log saturation** (`log(1 + x/scale)`) is **unbounded** — output grows without limit
- **Power saturation** (`x^0.5`) is **unbounded** — output grows as square root
- This creates a **326x magnitude difference** between channel features:
  - Television (log): mean=0.55, scale=0.46
  - Radio (power): mean=308, scale=150
- When StandardScaler normalizes these, the resulting z-scores have completely different physical meanings
- Ridge regularization applies the same penalty to all coefficients, but the 326x scale difference means radio coefficients are barely penalized while TV coefficients are heavily penalized
- **This is a fundamental pipeline design error that amplifies the identification problem**

### Agent 6: Fix Strategy Design

**Four strategies identified, ranked by preference:**

| Rank | Strategy | Time | Addresses Root Cause? | Expected Result |
|------|----------|------|----------------------|-----------------|
| 1 ⭐ | **Bayesian MMM** (PyMC-Marketing with informative priors) | 1-2 weeks | YES — incorporates domain knowledge | 30-50% media ± credible intervals |
| 2 | **Aggressive Regularization** (higher Ridge alpha via TimeSeriesSplit CV) | 4-8 hours | PARTIAL — reduces instability | ~55% media (more stable) |
| 3 | **Constrained Optimization** (bound media < 60% of revenue) | 2-4 hours | NO — masks symptom | Whatever you set as constraint |
| 4 | **Correct Decomposition** (un-standardize properly) | 30 min | NO — reveals problem clearly | Still ~144% (proves model is broken) |

---

## CONSENSUS DIAGNOSIS

### What Is Actually Wrong (Root Cause Chain)

```
1. UNBOUNDED SATURATION (log/power)
   → Creates 326x scale imbalance across channels
   → StandardScaler cannot equalize this properly
   → Ridge regularizes channels unequally

2. MEDIA-SEASONALITY CONFOUNDING
   → Media spend peaks when revenue peaks (summer)
   → Only 36 obs cannot disentangle the two
   → Model attributes seasonal demand to media

3. NEGATIVE ORIGINAL-SPACE INTERCEPT
   → Coefficients are too large (absorbing seasonality)
   → Intercept must compensate → goes negative
   → "Revenue without media = negative" is nonsensical

4. WRONG CONTRIBUTION CALCULATION
   → Method A: sum in standardized space = 0 (math identity)
   → Method B: counterfactual from negative baseline = 144%
   → Neither is correct; both are symptoms of #1-3
```

### What Is NOT Wrong
- Data quality is good (clean, no missing values, no outliers)
- Ridge regression as a technique is reasonable
- Adstock transforms are correctly implemented
- The transformation functions (code) are mathematically correct
- The notebook structure and pipeline logic are sound

---

## RECOMMENDED FIX PATH

### Immediate (This Week)
1. **Implement correct decomposition** (Strategy A from Agent 6) to demonstrate the problem transparently
2. **Replace log/power saturation with Hill saturation** for ALL channels (Agent 5's critical finding)
3. Re-run the model with bounded [0,1] features — this alone may fix the 326x imbalance

### Short-Term (2-3 Weeks)
4. **Implement Bayesian MMM** (Strategy C) using PyMC-Marketing:
   - Prior: media explains 20-40% of revenue (retail industry standard)
   - Prior: all media coefficients are non-negative
   - Prior: intercept is positive (baseline revenue exists)
   - Use NUTS sampler with proper convergence diagnostics

5. **Decompose seasonality first** (Meta/Robyn approach):
   - Fit Prophet or Fourier decomposition to revenue
   - Extract seasonal component
   - Regress DESEASONALIZED revenue on DESEASONALIZED media
   - This directly breaks the confounding

### Medium-Term (1-3 Months)
6. If possible, collect more data (target 60+ months minimum)
7. Design media "dark periods" (weeks with zero spend) for natural experiments
8. Consider weekly granularity instead of monthly (would give ~156 obs from 3 years)

### Long-Term
9. Implement proper MMM framework (PyMC-Marketing, Robyn, or Meridian)
10. Set up automated model validation (contributions must sum to ~100%, intercept must be positive, ROAS must be in plausible range)

---

## QUICK-START: The Minimum Fix

If you need a working model TODAY, here is the minimum viable fix:

```python
# Step 1: Replace ALL saturation with Hill (bounded [0,1])
for ch in MEDIA_CHANNELS:
    adstock_col = f'{ch}_adstock'
    nz = df[adstock_col][df[adstock_col] > 0]
    K = float(nz.median()) if len(nz) > 0 else 1.0
    df[f'{ch}_saturated'] = hill_saturation(df[adstock_col].values, K, alpha=2)

# Step 2: Fit Ridge as before
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[FEATURE_COLS].fillna(0))
model = Ridge(alpha=best_alpha).fit(X_scaled, y)

# Step 3: CORRECT contribution decomposition
beta_original = model.coef_ / scaler.scale_
intercept_original = model.intercept_ - np.sum(model.coef_ * scaler.mean_ / scaler.scale_)

# Step 4: Compute contributions in original space
for j, col in enumerate(FEATURE_COLS):
    contributions[col] = beta_original[j] * df[col].values  # per-period

# Step 5: VALIDATE
total_media = sum(contributions[col].sum() for col in SATURATED_COLS)
total_revenue = y.sum()
media_pct = total_media / total_revenue * 100
assert 0 < media_pct < 100, f"Media contribution {media_pct:.1f}% is out of bounds!"
```

---

## SUPPORTING DOCUMENTS

All agent reports are available for deep-dive review:

| File | Content | Size |
|------|---------|------|
| `agent1_data_quality.md` | Data adequacy audit, sample size analysis, confounding | ~19 KB |
| `agent2_model_architecture.md` | Ridge architecture, intercept analysis, overfitting | ~15 KB |
| `agent3_contribution_math.md` | Mathematical derivations, correct formulas, proofs | ~14 KB |
| `agent4_literature_review.md` | Google/Meta/PyMC best practices, academic consensus | ~12 KB |
| `agent5_transform_validation.md` | Saturation pipeline flaw, scale imbalance, fix | ~18 KB |
| `agent6_fix_strategy.md` | 4 fix strategies with code, comparison, roadmap | ~20 KB |

---

*Report generated by 6 specialized ML diagnostic agents, February 25, 2026*
