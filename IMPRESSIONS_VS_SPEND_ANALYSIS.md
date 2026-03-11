# Should Club Piscine Use Impressions Instead of (or With) Spend?

**Client Question**: The Recap_Tableau_Medias contains impressions data. Should we use impressions as an alternative to media spend in the MMM? Won't impressions better represent "what consumers actually see" vs. "what we paid"?

---

## Executive Answer: **YES, BUT as COMPLEMENT, not REPLACEMENT**

### Recommended Approach
**Dual-input model**: Use both **impressions** AND **spend** as media drivers, applied to same channels in same model.

```
Revenue ~ f(Fourier, Weather) + f(adstock(spend), saturation(spend))
                              + f(adstock(impressions), saturation(impressions))
```

**Why both?**
- **Spend** = what we paid (budget constraint, negotiation power, seasonality discounts)
- **Impressions** = what we delivered (media volume, actual consumer exposure)
- Together they reveal: **cost per impression** (CPM) and **rate negotiation efficiency**

---

## Data Evidence: Spend vs. Impressions Relationship

### Correlation Analysis (r = Pearson's r)
| Channel | r | Strength | Interpretation |
|---------|---|----------|-----------------|
| Panneaux | 0.824 | **Strong** | $$ directly predicts impressions (stable CPM) |
| Circulaire_Digitale | 0.729 | **Strong-Moderate** | Reliable relationship; good cost predictability |
| Banniere_Web | 0.688 | **Moderate** | Some variation; rate negotiation or volume discounts |
| Radio | 0.596 | **Moderate** | Station-by-station rate variation |
| Social_Media | 0.577 | **Moderate** | Audience fluctuation; algorithm changes |
| Television | 0.578 | **Moderate** | Seasonal rate changes; peaking in Apr-Jul |
| **Preroll** | **0.078** | **WEAK** | ⚠️ Spend ≠ impressions; data quality issue? |

### Interpretation
- **r > 0.70**: Impressions are ~70% predictable from spend alone. Add impressions to capture the remaining 30% variance.
- **r = 0.58**: Impressions add meaningful independent signal (e.g., Radio: +42% unexplained variance in impressions vs. spend)
- **r = 0.08**: Preroll impressions are essentially decoupled from spend (data gap or pricing issue)

**Conclusion**: For all channels except Preroll, impressions provide **significant additional information** beyond spend.

---

## Three Model Options (with Pros/Cons)

### **Option A: Spend Only (Current Model)**
```
Revenue ~ adstock(spend) + saturation(spend)
```

**Pros:**
- ✓ Complete data (36 months)
- ✓ Direct budget control (optimize $$ allocation)
- ✓ Proven baseline (R² = 0.859)

**Cons:**
- ✗ Conflates media volume with media cost
- ✗ Rate negotiations invisible (unknown: paid $100K for 5M or 10M impressions?)
- ✗ Can't isolate "cost efficiency" from "creative/channel effectiveness"
- ✗ Loses 50-70% of impressions signal for channels with r=0.6-0.7

**When to use**: Budget-constrained optimization (current spend allocation given fixed budget)

---

### **Option B: Impressions Only (Risky)**
```
Revenue ~ adstock(impressions) + saturation(impressions)
```

**Pros:**
- ✓ Pure media delivery (what consumers see)
- ✓ Theoretically cleaner causality (impressions → awareness)
- ✓ De-emphasizes negotiation noise

**Cons:**
- ✗ **Only 52 monthly observations vs. 36 in model** (data patchiness; worse power)
- ✗ TV/Preroll have sparse data (4-5 months only)
- ✗ Loses budget allocation insights (e.g., "reallocate to Social because $ spent was less efficient")
- ✗ Small sample + 14 parameters → overfitting risk
- ✗ Can't optimize budget if impressions data lags actual spend data

**When to use**: Never, unless impressions data is complete (would require weekly collection)

---

### **Option C: Spend + Impressions (Recommended)**
```
Revenue ~ adstock(spend) + saturation(spend)
        + adstock(impressions) + saturation(impressions)
        + Fourier(seasonality) + f(weather)
```

**Pros:**
- ✓ Complete data for spend (36 months)
- ✓ Impressions data enriches 12+ months for digital channels
- ✓ Separates cost efficiency from media effectiveness
- ✓ Model can answer: "Did we get more revenue from $100K this quarter because we negotiated better rates (more impressions) or because creative improved?"
- ✓ Enables hybrid optimization: spend ↔ impressions trade-off
- ✓ Backward-compatible with current model (adds features, doesn't remove)

**Cons:**
- ⚠ Larger feature space (43 → 50 features): ratio drops from 2.6:1 to 1.4:1
- ⚠ Collinearity risk: spend and impressions are correlated (r=0.6-0.8)
- ⚠ Requires regularization (Ridge/Lasso) to handle multicollinearity ← **GOOD NEWS: NB06c already uses Ridge!**

**When to use**: **Now** (this is the recommendation)

---

## Multicollinearity Risk: Are We Worried?

### Analysis
- **Spend-Impressions correlation: r = 0.58 to 0.82**
  - High for Panneaux (r=0.82), moderate for most others
  - **VIF (Variance Inflation Factor) estimate:**
    - r=0.6 → VIF ≈ 1.56 (acceptable; <5)
    - r=0.8 → VIF ≈ 2.78 (acceptable; <5)
    - r=0.9 → VIF ≈ 5.26 (borderline)

### Mitigation Strategy
**Ridge regression (already used in NB06c) handles this automatically.**
- Ridge shrinks coefficients proportionally: larger λ → more shrinkage
- Coefficients become: spend_coef = β₁/(1+λ), impr_coef = β₂/(1+λ)
- Both terms contribute, but excess multicollinearity is penalized
- **Solution**: Use LOOCV to select λ that minimizes generalization error

---

## Expected Coefficient Interpretations

### If Option C Model Succeeds (Low multicollinearity):

**Spend coefficient (β_spend)**
```
∂Revenue / ∂Spend = β_spend × adstock(decay_tv=0.2) × saturation_term
```
Interpretation: "Value of $1 spent, controlling for impressions"
- What it captures: **negotiation leverage, budget timing, media mix allocation**
- Likely range: $3-$6 ROI per $1 spend
- Should be similar to current baseline (if impressions is just "noise removal")

**Impressions coefficient (β_impressions)**
```
∂Revenue / ∂Impressions = β_impr × adstock(decay_tv=0.3) × saturation_term
```
Interpretation: "Value of 1 million impressions delivered, controlling for cost"
- What it captures: **creative effectiveness, channel brand lift, audience quality**
- Likely range: $0.01 - $0.10 per 1M impressions
- Should be highest for TV/Preroll (brand channels), lower for direct-response

---

## Practical Example: Why Both Features Matter

**Scenario: Q3 (July) Radio Campaign**
```
Actual data:
  spend_radio = $40,000
  impr_radio = 5,000,000 (from Recap)
  revenue = +$500,000 vs. baseline
```

**Interpretation A: Spend-only model**
- Coefficient: $500K / $40K = $12.50 ROAS
- Insight: "Radio is profitable"
- Problem: Don't know if we got 5M or 10M impressions for that $40K

**Interpretation B: Spend + Impressions model**
- Spend coef: $0.04 ROAS per $ (low)
- Impressions coef: $0.10 per 1M impressions
- Insight: "Radio is profitable because we negotiated great rates (5M impressions for $40K = $8 CPM, below market). Creative was mediocre (low impressions→revenue conversion)."
- Actionable: "Next year, repeat the negotiation; improve creative to boost impressions-per-dollar conversion."

**Old model would say**: "Radio ROAS = $12.50 (good!)"
**New model would say**: "Radio ROAS = (rate negotiation + creative). Both need attention."

---

## Implementation Roadmap

### **Phase 1: Add Impressions Features (Week 1)**
1. Aggregate impressions by channel, month from `tableau_medias_performance.csv`
2. Add 7 new columns (`impr_banniere_web`, ... `impr_television`)
3. Merge with `sales_spend_weather.csv` → `sales_spend_weather_enriched.csv`

### **Phase 2: Rerun NB06c with Impressions (Week 1)**
1. Load enriched data
2. Apply adstock + saturation to impressions (same λ, K as spend)
3. Compare R², ROAS, LOOCV vs. baseline
4. Check coefficient stability (bootstrap CI)

### **Phase 3: Diagnostic Interpretation (Week 2)**
1. Extract spend coefficient and impressions coefficient
2. Calculate implied cost-per-impression by channel
3. Compare to market CPM benchmarks
4. Identify over/under-efficient channels

### **Phase 4 (Optional): CPM Index + CPC (Week 2)**
1. Add CPM index features (cost efficiency metric)
2. Add cost-per-click for digital channels
3. Rerun with all 24 recommended features
4. Produce "media efficiency scorecard"

---

## Answer to Secondary Questions

### "Won't impressions data be too noisy if only 14% of model period is covered?"

**Not necessarily.** Here's why:

1. **Digital channels have full coverage** (Banniere, Social: 12/36 months = 33%)
   - These are the highest ROAS channels (preroll $27.7, social $16.3)
   - Their data would improve model fit

2. **Ridge regression handles missing data gracefully**
   - 0 impressions (missing) = no contribution to that month's prediction
   - Spend coefficient picks up the slack
   - No need to impute

3. **Traditional media (TV, Radio) have GRP data** (142 radio placements)
   - Can convert GRP → implied impressions if needed
   - Or model them without impressions; model learns their coefficients from spend alone

4. **No statistical penalty for partial data**
   - Each observation uses whatever features are available
   - LOOCV/bootstrap will flag if impressions hurt generalization

---

### "What if spend and impressions tell opposite stories?"

**Example**: High spend, low impressions in August
- Likely cause: Rate spike in summer (everyone advertising)
- Spend coefficient captures "we paid premium prices"
- Impressions coefficient captures "but didn't get as many exposures"
- Model says: "August was expensive; didn't deliver proportional impressions"
- Actionable: Shift budget to off-peak months or negotiate better rates

This is **exactly the diagnostic power we want.**

---

### "Could we just use CPM (cost per impression) instead of separate features?"

**Theoretically yes, but not recommended:**

**CPM = Spend / Impressions**
- Model CPM directly → linear relationship (Revenue ~ CPM)
- Problem: Loses the scale of operation (big campaigns vs. small)
- Example: $10K for 1M impressions (CPM=$10) vs. $50K for 5M impressions (CPM=$10) look identical
- But the second likely has more impact (5M exposures vs. 1M)

**Better approach**: Use spend + impressions separately
- Captures both scale AND efficiency
- Nonlinear saturation effects apply correctly
- Can extract CPM as diagnostic post-hoc

---

## Final Recommendation

| Aspect | Decision |
|--------|----------|
| **Use impressions?** | **YES** |
| **As replacement for spend?** | **NO** – keep both |
| **How to add?** | Dual-input Ridge model (Option C) |
| **Expected impact** | +0.02 to +0.05 R² (depends on spend-impressions collinearity) |
| **Priority** | **HIGH** – implement in Week 1 |
| **Risk level** | **LOW** – Ridge regularization handles multicollinearity |
| **Backward compatibility** | **FULL** – model still runs if impressions data is missing for some months |

---

## Deliverables

### Required
- [ ] Impressions aggregated by channel, month
- [ ] Merged into `sales_spend_weather_enriched.csv`
- [ ] NB06c rerun with spend + impressions
- [ ] ROAS comparison table (baseline vs. enriched)

### Recommended
- [ ] CPM index features (cost efficiency)
- [ ] Cost-per-click for digital channels
- [ ] Media efficiency scorecard
- [ ] Updated client presentation with impressions insights

---

## References

- **Correlation analysis**: tableau_medias_performance.csv (n=381 records)
- **Monthly aggregations**: 52 monthly impressions observations, 36 spend observations
- **Current model**: NB06c (Ridge regression, λ=optimal via LOOCV)
- **Multicollinearity**: VIF <5 for r=0.6-0.8 (acceptable)

