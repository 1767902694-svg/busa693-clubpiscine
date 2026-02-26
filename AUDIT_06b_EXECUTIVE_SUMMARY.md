# AUDIT: Notebook 06b — Executive Summary

**Status:** CONDITIONAL ACCEPT with Major Caveats
**Use Case:** Exploratory channel ranking; NOT for operational budget optimization

---

## Critical Findings

### 1. The Model is Seasonal, Not Media-Driven
- **Stage 1 (Seasonality) R² = 83%** ← Explains most variance
- **Stage 2 (Media) R² = 15%** ← Weak explanatory power
- **Adjusted R² (Media) = -6%** ← Negative! Media terms are overfitting noise

**Implication:** This is a seasonal forecast with a weak media adjustment, not a causal media effectiveness model.

---

### 2. Small-Sample Problem is Severe
| Metric | Value | Standard | Status |
|--------|-------|----------|--------|
| Observations | 36 months | 3+ years min | ⚠️ Borderline |
| Parameters | 7 media + 5 controls | — | — |
| N/p ratio | 3.0 | ≥5 | ❌ Below standard |
| **Adjusted R² (media)** | **-6%** | **>0%** | **❌ Failed** |

**Implication:** With only 36 observations, the model cannot reliably estimate 7 channel effects. The negative adjusted R² indicates media terms are fitting noise, not signal.

---

### 3. Three Channels Completely Zeroed (28% of Budget)
| Channel | Spend | ROAS | Notes |
|---------|-------|------|-------|
| Radio | $2.17M (21%) | 0 | 🚩 Zeroed despite major budget |
| Panneaux | $0.29M (3%) | 0 | 🚩 Zeroed |
| Circulaire_Digitale | $0.45M (4%) | 0 | 🚩 Zeroed |
| **Total Zeroed** | **$2.91M (28%)** | — | — |

**Root Cause:** Non-negativity constraint eliminates weak signals. This likely reflects multicollinearity and confounding, not market reality.

**Implication:** Zero ROAS does NOT mean "no effect"—it means "insufficient evidence." Radio is a real tactical medium for pool retail; treating it as worthless would be strategically misguided.

---

### 4. Only 2 Channels Statistically Significant
At 90% confidence level (CI excluding zero):

| Channel | ROAS | 90% CI | Significant? |
|---------|------|--------|--------------|
| Television | 4.49 | [1,040, 7,204] | ✅ YES |
| Preroll | 27.68 | [14,372, 38,312] | ✅ YES |
| Social Media | 16.28 | [0, 49,041] | ❌ NO (lower bound=0) |
| Web Banners | 12.20 | [0, 32,547] | ❌ NO |
| Radio | 0 | [0, 6,010] | ❌ NO |
| Panneaux | 0 | [0, 63,652] | ❌ NO |
| Circulaire | 0 | [0, 36,194] | ❌ NO |

**Implication:** High statistical uncertainty. Ranking is directional (Preroll likely best), but magnitudes are unreliable.

---

### 5. TV Decay Rate is Unusually Low and Sensitive
- **Current assumption:** λ_TV = 0.2 (half-life ~ 2.4 weeks)
- **Industry standard:** λ_TV = 0.7-0.9 (half-life ~ 4-7 weeks)
- **Sensitivity:** TV ROAS ranges from 1.4 (λ=0.8) to 4.49 (λ=0.2) — **3.2× change**

**Implication:** TV ROAS is not robust. Changing decay rate from 0.2 to a more realistic 0.8 would cut TV effectiveness by 69%, potentially eliminating TV from the optimized budget (see NB07 results).

---

## What the Model Does Well

✅ **Methodologically Sound**
- Two-stage Frisch-Waugh decomposition is correct (season first, then media)
- Non-negativity constraint via NNLS is standard MMM practice
- Bootstrap CIs with 1,000 resamples quantify uncertainty

✅ **Proper Implementation**
- Ridge with TimeSeriesSplit CV for alpha selection
- Caching and parallelization for efficiency
- Clear separation of Stage 1 (controls) and Stage 2 (media)

✅ **Complete Diagnostics**
- Robustness checks (adstock, saturation, LOO, CI)
- VIF analysis for multicollinearity
- Adjusted R² reported

---

## What the Model Does NOT Provide

❌ **Causal Insight**
- Observational data, no experimental control
- Reverse causality (management chooses channel mix based on expected ROI)
- Endogeneity not addressed

❌ **Operational Precision**
- Media effects difficult to isolate from seasonality
- Wide confidence intervals (factor of 2-10× coefficient magnitude)
- Generalization risk (only 3 fiscal years; regime could shift)

❌ **Reliable Budget Optimization**
- Too few degrees of freedom (36 obs, 7 channels)
- Results would change materially with different decay/saturation assumptions
- Multicollinearity prevents isolating individual channel contributions

---

## Output Files (All Generated)

1. **media_effectiveness_results_nonneg.csv** — Marginal effects, ROAS, CIs per product-channel
2. **saturation_curves_nonneg.csv** — Hill saturation curves for plotting
3. **causal_model_params_nonneg.json** — Full model specification (decay rates, K values, alphas, R²)
4. **robustness_summary_nonneg.csv** — Summary: only TV and Preroll pass all 4 robustness checks

---

## Recommendations for Client Presentation

### DO:
- Present as **exploratory channel ranking** (Preroll > Social > Web > TV > Zeroed)
- Highlight **uncertainty** (wide CIs, small sample size)
- Use for **hypothesis generation** ("Should we test Preroll more? Does Radio deserve investment?")
- Frame as **beginning of analysis**, not definitive conclusion

### DO NOT:
- Present ROAS values as precise ROI guarantees
- Use as sole basis for budget reallocation
- Claim TV decay (λ=0.2) is well-calibrated without sensitivity analysis
- Suggest media accounts for significant revenue variance (seasonality dominates)

### Caveats to Include:
1. "With only 36 months of data, these results are exploratory and subject to sampling error."
2. "Three channels (Radio, Panneaux, Circulaire) show zero ROAS, but this reflects insufficient statistical power, not market reality."
3. "Media effects are difficult to isolate from seasonality. These estimates should be validated with experimental evidence (test-and-control stores)."
4. "TV ROAS is sensitive to assumed decay rate (λ). Under industry-standard assumptions, TV effectiveness would be 70% lower."
5. "Only TV and Preroll are statistically significant at 90% confidence. All other channels have ambiguous evidence."

---

## Path Forward

**Immediate (For This Project):**
- Use 06b results as **diagnostic tool** to identify high-potential channels (Preroll, Social)
- Support NB07 optimization with sensitivity analysis (especially TV decay)
- Caveat all client presentations heavily

**Medium-term (1-2 Quarters):**
- Collect **weekly data** (150+ observations) to improve statistical power
- Isolate channel effects at **store/region level** (reduce seasonality confound)

**Long-term (1+ Year):**
- Design **randomized test-and-control** store groups for causal validation
- Implement **marketing mix modeling with Bayesian priors** (e.g., PyMC-Marketing) to borrow strength across products
- Integrate **real-time tracking** (daily sales, web traffic, store footfall) to reduce aggregation bias

---

## Bottom Line

**06b is a competent but under-powered media effectiveness model.** It correctly identifies that Preroll and Social perform well relative to TV, and that seasonality dominates the variance structure. However, with only 36 observations and high multicollinearity, it cannot reliably answer "what is the true ROI of each channel?" That question requires more data, experimental design, or both.

**Use this model for strategic direction (which channels to emphasize), not tactical allocation (exactly how much to spend on each).**

