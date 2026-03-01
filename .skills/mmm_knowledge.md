# Marketing Mix Modeling (MMM) Skills Reference

## Table of Contents
1. [MMM Overview](#1-mmm-overview)
2. [Core Transformations](#2-core-transformations)
3. [Professional MMM Tools Comparison](#3-professional-mmm-tools-comparison)
4. [Ridge Regression & Regularization](#4-ridge-regression--regularization-for-mmm)
5. [Two-Stage Modeling Approach](#5-two-stage-modeling-approach)
6. [Interpreting Results](#6-interpreting-results)
7. [Common Pitfalls](#7-common-pitfalls)
8. [Budget Optimization](#8-budget-optimization)
9. [Data Requirements](#9-data-requirements-checklist)
10. [Club Piscine Context](#10-club-piscine-specific-context)

---

## 1. MMM Overview

### What is Marketing Mix Modeling?

Marketing Mix Modeling is a statistical technique to quantify the incremental impact of marketing activities on sales and revenue. It answers the fundamental question: **"How much revenue does each marketing channel actually drive?"**

Unlike attribution models that assign last-touch credit, MMM uses historical data and econometric methods to estimate causal effects, controlling for seasonality, external factors, and confounding variables.

### The Two-Step Process

MMM follows a structured academic framework formalized in online optimization theory:

#### Step 1: Estimate Channel Effectiveness
- Fit a statistical model (Ridge regression, Bayesian, etc.) to historical sales and media spend data
- Control for seasonality, weather, and other non-marketing factors
- Extract coefficients representing the incremental revenue impact of each channel
- Quantify uncertainty via confidence intervals or posterior distributions
- Account for diminishing returns (saturation) and carryover effects (adstock)

**Key outputs:**
- Response curves: Revenue = f(Spend) for each channel
- ROAS (Return on Ad Spend) by channel
- Media contribution: % of total revenue explained by marketing

#### Step 2: Solve the Optimization Model
- Given channel effectiveness functions and business constraints
- Allocate a fixed budget across channels to maximize total revenue
- Respect minimum/maximum spend bounds and mix constraints
- Trade off high-ROAS channels against strategic priorities and brand-building channels
- Evaluate sensitivity to budget changes

**Key outputs:**
- Recommended budget allocation by channel
- Expected revenue lift from reallocation
- Budget cut scenarios (e.g., 10% cut impact)

### Connection to Academic Framework

This problem sits at the intersection of **econometrics** (demand estimation) and **operations research** (constrained optimization).

From Professor Rob's framing — "online optimization":
- **Online**: Using real-world historical data (not controlled experiments)
- **Optimization**: Solving a constrained mathematical program to find the best allocation
- **Two-step**: (1) Learn demand curves from data, (2) use those curves to decide future actions

Analogous to revenue management / markdown optimization:
- Demand functions for each media channel are learned from historical spend and sales variation
- These functions feed directly into an LP/nonlinear optimizer
- The optimizer finds the allocation that maximizes total revenue subject to budget, mix, and business constraints
- Uncertainty propagates from the demand estimation step into the optimization (via confidence bounds)

---

## 2. Core Transformations

All MMM models rely on transforming raw media spend into variables that better represent its true impact on sales. Two core transformations are universal.

### Adstock (Carryover Effect)

**Concept**: Marketing impact doesn't end when the media buy ends. A TV commercial or radio spot has a cumulative effect over time — the audience remembers it.

**Geometric Adstock Formula** (most common):
```
Adstock_t = Spend_t + λ × Adstock_{t-1}
```

Where:
- `Spend_t` = raw media spend in period t
- `λ` (lambda) = decay rate, typically 0.0–0.9
- `Adstock_t` = accumulated spend effect at time t

**Interpretation**:
- λ = 0: no carryover, effect is immediate and disappears next period
- λ = 0.5: half the previous period's effect carries over (50% decay)
- λ = 0.8: strong carryover, effect takes months to fade out

**Half-Life** (time for effect to halve):
```
half_life = log(0.5) / log(λ)
```

Examples:
- λ = 0.5 → half-life = 1 period (rapid decay)
- λ = 0.7 → half-life = 2.4 periods (moderate decay)
- λ = 0.9 → half-life = 6.6 periods (slow decay)

**Industry Benchmark Decay Rates by Channel Type**

| Channel | λ Range | Half-Life | Notes |
|---------|---------|-----------|-------|
| **Brand TV** | 0.5–0.9 | 2–7 weeks | Long memory, builds cumulative brand equity; viewers see multiple touches over weeks |
| **Performance/Direct Response TV** | 0.3–0.5 | 0.7–2 weeks | Shorter window; tactical promos drive immediate action |
| **Radio** | 0.3–0.5 | 0.7–2 weeks | Tactical, frequency-dependent; repeated messaging drives action mid-week |
| **OOH / DOOH / Billboards** | 0.3–0.5 | 0.7–2 weeks | Commute-based; top-of-mind decay is relatively fast |
| **Social Media (Facebook, Instagram, TikTok)** | 0.1–0.3 | 0.2–1 week | Near-immediate response; algorithm-driven; users swipe past quickly |
| **Preroll / YouTube Video** | 0.2–0.4 | 0.4–2 weeks | Video content has moderate carryover; viewers remember storytelling |
| **Display / Banner Ads** | 0.1–0.3 | 0.2–1 week | Short carryover; visual reminders decay rapidly |
| **Digital Flyers / Circulars** | 0.2–0.4 | 0.4–2 weeks | Promo-driven; decay depends on promotional window |
| **Search / SEM** | 0.0–0.1 | Immediate | Near-zero carryover; intent-driven, captures existing demand |

**Setting λ in Practice**:
- **With abundant data (N > 200 observations)**: Estimate λ from data using grid search or Bayesian optimization
- **With small samples (N < 100)**: Set λ manually based on domain knowledge and channel type
- **Sensitivity analysis**: Always run models with λ ± 0.2 to test robustness

**Alternative: Weibull Adstock**

Meta Robyn uses a more flexible Weibull distribution for adstock:
```
Adstock_t = Spend_t weighted by Weibull(geometric_decay, scale)
```

Advantages:
- Can fit both fast and slow decay within a single decay function
- Better captures non-geometric decay shapes
- Requires more data to estimate reliably

Trade-off: increased model complexity for small samples.

---

### Saturation (Diminishing Returns)

**Concept**: Each additional dollar of marketing spend has less incremental impact than the previous dollar. This is true for almost all media channels.

**Hill Saturation Function** (industry standard):
```
y = x^α / (x^α + K^α)
```

Where:
- `x` = adstocked spend
- `α` (alpha) = steepness/shape parameter, typically 1–3
- `K` = half-saturation point (spend level at which output = 0.5)
- `y` ∈ [0, 1] = saturated response

**Interpretation**:
- When x = 0, y = 0 (no spend, no effect)
- When x = K, y = 0.5 (at the half-saturation point, output is 50%)
- When x >> K, y → 1 (effect plateaus)
- α controls the shape:
  - α = 1: linear response up to saturation (rare)
  - α = 2: smooth S-shaped curve (most common)
  - α > 2: very sharp elbow (strong diminishing returns early)

**Setting K and α in Practice**:

**K (Half-Saturation Point)**:
- Represents the spend level where you've achieved 50% of the maximum possible impact
- Common approaches:
  1. **K = median adstocked spend**: Centers saturation around the observed spend distribution
  2. **K = 70% of max adstocked spend**: Implies diminishing returns kick in before peak spend
  3. **K = estimated from data**: Requires sufficient data and careful regularization

- For Club Piscine (small sample): Use K = 0.7 × max(adstocked_spend)

**α (Steepness)**:
- Common manual settings: α = 1.5–2.5
- α = 2: balanced S-curve, standard default
- α = 1.5: more gradual saturation (linear-ish until high spend)
- α = 2.5: sharp elbows, strong diminishing returns

**Alternative Saturation Functions**:
1. **Log saturation**: `y = log(1 + x)` — simple, unbounded growth
2. **Power saturation**: `y = x^α` where 0 < α < 1 — monotonic but unbounded
3. **Logistic saturation**: `y = x / (1 + x)` — bounded, similar to Hill with α = 1

---

## 3. Professional MMM Tools Comparison

### Meta Robyn (Open Source, Python/R)

**Architecture**:
- Ridge regression as the base model
- Nevergrad (Meta's hyperparameter optimizer) to search across thousands of model combinations
- Adstock: geometric or Weibull (2+ parameters estimated)
- Saturation: Hill function with K and α estimated
- Produces 100–1000 Pareto-optimal models; user selects based on domain knowledge

**Strengths**:
- Fully automated hyperparameter search (no manual λ/K/α tuning)
- Scales to large, high-dimensional problems
- Handles weekly data naturally
- Active development, real-world use at Meta/Facebook

**Limitations**:
- Frequentist only (no uncertainty quantification beyond bootstrap)
- Requires typically 100+ weekly observations for reliable estimation
- Complex hyperparameter space can lead to overfitting if not careful
- Steep learning curve; requires familiarity with Nevergrad

**Recommended Sample Size**: 2+ years of weekly data (104+ observations minimum)

---

### Google Meridian (Open Source, Python, 2024+)

**Architecture**:
- Bayesian framework using MCMC (NumPyro on JAX)
- Geometric adstock with estimated decay rate
- Hill saturation with estimated K and α
- Full posterior distributions for all parameters (uncertainty quantification)
- Priors can be set from domain knowledge

**Strengths**:
- Native uncertainty quantification (posterior distributions, credible intervals)
- Can incorporate informative priors from domain experts or prior studies
- Handles small sample sizes better than frequentist approaches
- Transparent inference (see full posterior, not just point estimates)

**Limitations**:
- Computationally expensive (MCMC sampling can take hours)
- Requires Bayesian statistical expertise to interpret
- Fewer published case studies than Robyn
- Limited hyperparameter flexibility (e.g., Weibull not yet implemented)

**Recommended Sample Size**: 2+ years of weekly data (same as Robyn; Bayesian helps with uncertainty, not sample size)

---

### Our Approach: Club Piscine (Two-Stage Ridge Regression)

**Why this approach for small samples?**

With N = 36 monthly observations, neither Robyn nor Meridian is appropriate:
- Robyn assumes 100+ observations for grid search stability
- Meridian requires careful prior specification and more data for posterior to stabilize
- We need a transparent, explainable approach for the client

**Our architecture**:
1. **Stage 1 (Seasonality)**: Fourier terms + weather controls → capture natural revenue cycles
2. **Stage 2 (Media)**: Ridge regression on residuals → isolate media signal
3. **Adstock**: Geometric, manually set decay rates (based on channel type benchmarks)
4. **Saturation**: Hill function, K = 0.7 × max(adstocked_spend), α = 2
5. **Regularization**: Cross-validated Ridge alpha for control
6. **Uncertainty**: Bootstrap confidence intervals (1000 resamples)
7. **Constraints**: Non-negative coefficients (NNLS) for final client-facing results

**Strengths**:
- Transparent and auditable (client can review every step)
- Works with small samples when regularization is tuned correctly
- Two-stage approach mitigates seasonality confounding
- Bootstrap CIs are intuitive and easy to explain

**Limitations**:
- Manual parameter choices (λ, K, α) introduce sensitivity
- No mechanism to estimate which parameters matter most
- Cannot handle interactions or cross-media synergies easily
- Requires careful alpha selection (CV optimizes prediction, not causal inference)

---

## 4. Ridge Regression & Regularization for MMM

Ridge regression is the workhorse of MMM because it handles collinearity and small sample sizes gracefully. However, selecting the regularization strength (alpha) is critical and often misunderstood.

### The Ridge Regression Problem

**OLS (No Regularization)**:
```
minimize: ||y - Xβ||²
```

**Ridge Regression**:
```
minimize: ||y - Xβ||² + α × ||β||²
```

The penalty term `α × ||β||²` shrinks large coefficients toward zero. The parameter `α` controls the strength of this shrinkage:
- **α = 0**: Ridge becomes OLS (no penalty, high variance, risk of overfitting)
- **α → ∞**: All coefficients → 0 (infinite bias, underfitting)
- **α = optimal**: Bias-variance tradeoff that minimizes test error

### The Alpha Problem: Prediction vs. Causation

**CRITICAL INSIGHT**: Cross-validation optimizes for **prediction accuracy**, not **causal inference**. In MMM, we care about causal effects (ROAS), not predicting next month's revenue.

**Example Scenario**:
- Small sample (N = 36), many media channels (k = 7)
- TV and Radio are correlated (both peak in spring)
- Weak signal-to-noise ratio (media explains only 10% of revenue)

**What happens**:
1. Low α (e.g., 10): Flexible fit, tries to separate TV and Radio effects → high variance estimates, ROAS values swing wildly across CV folds
2. High α (e.g., 500): Strong shrinkage, crushes both TV and Radio toward zero → media contribution drops to 2%, unrealistically low
3. CV chooses α ≈ 200 (somewhere in between) → good **prediction** accuracy, but media coefficients are heavily biased downward

**Result**: An alpha that looks good by CV score may produce unreliable causal estimates.

### Recommended Regularization Workflow for Small-Sample MMM

1. **Run cross-validated Ridge**:
   ```python
   cv = GridSearchCV(Ridge(), {'alpha': [1, 10, 50, 100, 200, 500, 1000]}, cv=5, scoring='r2')
   cv.fit(X, y)
   cv_alpha = cv.best_params_['alpha']
   print(f"CV selected alpha: {cv_alpha}")
   ```

2. **Fit model with CV alpha and inspect results**:
   - Media contribution %
   - ROAS by channel
   - Are these plausible given business knowledge?

3. **If alpha is too high** (media contribution < 5%, all ROAS < $2):
   - **Do not use CV alpha blindly**
   - Manually lower alpha to 10–100 and re-fit
   - Accept higher R² variance in exchange for realistic causal estimates
   - Document the decision in the report

4. **Sensitivity analysis**:
   - Show results across a range of alphas: [10, 50, 100, 200, 500]
   - Create a table: Media Contribution % and ROAS vs. Alpha
   - Identify the range where results are stable

5. **Report multiple scenarios**:
   - "Conservative scenario (α = 500): media contribution = 5%, ROAS = $1.2"
   - "Mid-range scenario (α = 100): media contribution = 10%, ROAS = $2.5"
   - "Flexible scenario (α = 20): media contribution = 15%, ROAS = $4.2"

6. **Choose the scenario that**:
   - Matches business intuition (e.g., "we know media drives ~10% of sales")
   - Produces realistic ROAS (typically $1–$10 for most channels)
   - Has stable results across small perturbations to data or parameters

### Non-Negative Constraints (NNLS)

**Why apply NNLS?**

Ridge regression can produce negative media coefficients, which are nonsensical: advertising doesn't reduce sales.

**Approach**: Non-Negative Least Squares (NNLS)
- Constrain all β_j ≥ 0
- Prevents "advertising hurts sales" results
- Fitted via quadratic programming

**Pros**:
- Eliminates unrealistic negative coefficients
- Client-friendly (no need to explain why a channel is harmful)

**Cons**:
- Masks real signal: a negative coefficient might indicate multicollinearity or confounding, not true harm
- Can distort other channel's effects if you force one channel to zero
- May overstate other channels' effectiveness as a result

**Best Practice**:
- Report results **both** with and without NNLS:
  - **Unconstrained (Ridge only)**: Use for diagnostics, understanding confounding
  - **NNLS**: Use for client reports and optimization
- If a channel has a strongly negative coefficient (unconstrained), investigate why:
  - Check VIF for multicollinearity
  - Check seasonality alignment with revenue
  - Consider removing that channel or combining it with correlated channels

---

## 5. Two-Stage Modeling Approach

### Why Two Stages?

For seasonal businesses, revenue and media spend are **both** seasonal. Pools sell heavily in summer; ads run heavily in summer. If you model them together, media gets credit for seasonal demand.

**Example**:
- July revenue is naturally high (summer pool season)
- July media spend is naturally high (prepare for peak season)
- A naive regression attributes July's high revenue to July's high spend
- But July would be high regardless of media (just seasonality)

**Solution**: Two-stage approach removes the seasonal component first, then measures media impact on what's left.

### Stage 1: Seasonality and External Controls

**Goal**: Explain revenue variation due to season, weather, and other non-marketing factors.

**Model**:
```
Revenue_t = β_0 + Σ(β_season × Fourier terms) + β_weather × Weather_t + ε_t
Residual_t = Revenue_t - Prediction_t
```

**Fourier Terms** (for smooth seasonality):
- Fourier order 1: sin(2πt/52), cos(2πt/52) — captures annual cycle
- Fourier order 2: above + sin(4πt/52), cos(4πt/52) — captures annual + semi-annual
- Typically use order 1–2 for retail with strong annual seasonality

**Weather Controls**:
- Temperature, precipitation, sunshine hours (if available)
- Month dummies (less flexible than Fourier)

**Why not just use month dummies?**
- Fourier terms are smoother and require fewer degrees of freedom
- Avoid over-parameterization with small N

**Output**:
- Fitted values (the seasonal + weather component)
- Residuals (what's left unexplained)

### Stage 2: Media Measurement

**Goal**: Measure how much media spend explains the residual revenue.

**Model**:
```
Residual_t = Σ(β_channel × Adstock_channel_t) + ε_t
             (ridge regression with cross-validated alpha)
```

**Inputs**:
- Dependent variable: residuals from Stage 1 (revenue not explained by season/weather)
- Independent variables: adstocked + saturated media spend

**Why adstock + saturate media?**
- Adstock transforms raw spend into cumulative effect (carryover)
- Saturation transforms cumulative effect into diminishing returns
- Together, they create a more realistic representation of channel impact

**Output**:
- Coefficients for each channel (media effectiveness)
- Residuals (variation unexplained by both season and media)
- R² for Stage 2 (media's contribution to residual variance)

### Computing Media Contribution %

Once you have Stage 2 coefficients β_channel:

```
Media-driven revenue_channel = Coefficient × Adstocked spend
Total media-driven revenue = Σ all channels
Media contribution % = Total media-driven revenue / Total revenue × 100
```

**Example**:
- Total 3-year revenue: $512M
- Media-driven revenue: $55M
- Media contribution: 10.7%

**Interpretation**:
- About 11% of Club Piscine's revenue is attributable to marketing
- The other 89% comes from base demand, seasonality, brand equity, etc.

---

## 6. Interpreting Results

### ROAS (Return on Ad Spend)

**Definition**:
```
ROAS = Total media-driven revenue / Total raw spend
```

Or per-channel:
```
ROAS_channel = Coefficient_channel × Total adstocked spend / Total raw spend
```

**Examples**:
- ROAS = $5: Every $1 spent drives $5 in revenue
- ROAS = $1: Every $1 spent drives $1 (break-even)
- ROAS = $0.50: Every $1 spent drives $0.50 (loss, but may have strategic value)

**Industry Benchmarks**:
| Channel | Typical ROAS | Context |
|---------|--------------|---------|
| Performance/SEM | $3–$15 | Captures high-intent demand; direct response |
| Social Media (DTC) | $2–$10 | Highly targeted, good for growth |
| Preroll/Video | $2–$8 | Storytelling, mixed intent |
| Display/Banners | $1–$4 | Lower intent, high frequency needed |
| Radio | $1–$3 | Tactical, frequency-driven |
| TV/Broadcast | $0.50–$3 | Brand building, hard to measure direct ROI |
| Outdoor/Billboards | $0.50–$2 | Long-term brand awareness |

**Healthy ROAS Ranges**:
- **For digital-native brands**: $3–$8+ (volume-oriented, direct response)
- **For retail/omnichannel**: $1–$5 (mix of brand and direct response)
- **For legacy/brand-driven**: $0.50–$3 (long-term equity, hard to measure)

**Red Flags**:
- ROAS > $20: Likely model overestimation (under-regularization, NNLS artifact, or causal confounding)
- ROAS < $0.50 for performance channels: Model may be over-regularized or the channel truly lacks effectiveness
- ROAS = $0 (exactly): Usually a sign of perfect collinearity or forced non-negativity hiding a negative coefficient

---

### Media Contribution %

**Definition**:
```
Media Contribution % = (Total media effect / Total revenue) × 100
```

**Industry Benchmarks**:
| Business Type | Typical Range | Context |
|---------------|---------------|---------|
| DTC/E-commerce | 20–40% | Marketing-driven growth, repeat buyers |
| SaaS | 15–30% | Product-led, but marketing essential for growth |
| CPG/Retail | 5–15% | Demand-driven by distribution, seasonality, base brand |
| Luxury | 5–20% | Brand-driven, expensive products, lower volume |
| Category builders | 30–50% | New category, high marketing intensity |

**Club Piscine Context**:
- Seasonal retail (pools, spas, furniture)
- Strong demand seasonality (summer peaks naturally)
- Large base of repeat customers from prior years
- **Expected media contribution: 8–15%** is healthy

**Interpretation**:
- If media contribution < 2%: Model is over-regularized (alpha too high)
- If media contribution 5–15%: Reasonable for seasonal retail
- If media contribution > 30%: Model is under-regularized or confounded (check for seasonality bleed)

---

### Confidence Intervals (Bootstrap Method)

**Why uncertainty matters**:
- Point estimates (e.g., ROAS = $4.5) hide the range of plausible values
- With small samples and high noise, the true ROAS might be anywhere from $1 to $8
- CIs communicate this uncertainty to decision-makers

**Bootstrap Procedure**:
1. Resample the data (X, y) with replacement, N times
2. Fit the full two-stage model (Stage 1 + Stage 2) on each resample
3. Extract coefficients and compute ROAS for each resample
4. Take the 5th and 95th percentiles (for 90% CI)

**Interpretation**:
- **90% CI = [$2.5, $6.2]**: We estimate ROAS = $4.5, and we're 90% confident the true ROAS is between $2.50 and $6.20
- **CI does not cross zero**: Statistically significant; the effect is real
- **CI crosses zero**: Inconclusive; can't rule out that the effect is just noise
- **Wide CI**: High uncertainty, small sample size, or high noise
- **Narrow CI**: More precise estimate, either larger sample or less noise

**Reporting**:
```
Channel        | ROAS  | 90% CI           | Significant?
TV             | $4.5  | [$0.8, $8.2]     | Yes (CI doesn't cross 0)
Preroll        | $27.7 | [$18.3, $37.1]   | Yes (tight CI)
Radio          | $0.2  | [-$2.1, $2.5]    | No (CI crosses 0)
Circulaire     | $0.1  | [-$1.8, $1.9]    | No (CI crosses 0)
```

---

## 7. Common Pitfalls

### 1. Small Sample Size

**The Challenge**:
- MMM requires sufficient variation in media spend across time periods
- Small N = fewer independent data points = higher variance estimates
- Rule of thumb: Need at least 5 observations per parameter

**Club Piscine**: N = 36 months, 14 parameters → ratio 2.6:1 (below recommended 5:1)

**Mitigation**:
1. **Use weekly data if available**: 156 weeks >> 36 months
2. **Aggregate variables carefully**: Fewer, broader channel groups reduce parameter count
3. **Apply strong regularization**: Ridge alpha should be 50–200+
4. **Use informative priors** (Bayesian): Incorporate domain knowledge
5. **Validate with holdout periods**: Split data, fit on 2 years, test on 1 year

**Club Piscine approach**: Combined channels (7 groups instead of 30+), two-stage model reduces effective parameters, strong Ridge regularization, bootstrap validation

---

### 2. Seasonality Confounding

**The Problem**:
- Pools sell in summer (natural demand peak)
- Media budgets concentrate in spring/summer (pre-season push)
- If you ignore seasonality, media gets false credit for summer demand

**Visual Example**:
```
      Revenue & Media Spend (Naive View)
      │
      │     ╱╲
  $10M├────╱  ╲────
      │   ╱    ╲
      │  ╱      ╲
   $5M├─╱────────╲──
      │╱          ╲
    0 ├─────────────── Time (months)
        Summer = both revenue and media peak together
```

**How it biases results**:
- Media channels that spend in spring/summer get inflated ROAS
- Media channels that spend year-round get underestimated
- TV (which peaks early) gets underestimated; Digital Flyers (peak June) get overestimated

**Mitigation**:
1. **Two-stage modeling** (Club Piscine approach):
   - Stage 1: Model seasonality alone
   - Stage 2: Measure media impact on residuals (season already removed)

2. **Weekly data**:
   - More granular seasonality controls
   - Better separation of media effects from seasonal bumps

3. **Additional seasonal controls**:
   - Fourier terms (smooth, efficient)
   - Month dummies (less efficient, but interpretable)
   - Holiday/event variables (if known)

4. **Sensitivity analysis**:
   - Refit model with different seasonal orders
   - Check stability of media coefficients across specifications

---

### 3. Multicollinearity

**The Problem**:
- Media channels often move together
- TV peaks in April → May → June
- Radio peaks in April → May → June
- Preroll peaks in May → June → July
- High correlation between predictors → unstable coefficients → "exchangeability" where any one of several channels could explain the same effect

**How to detect**:
```python
from statsmodels.stats.outliers_influence import variance_inflation_factor as vif

# Compute VIF for each adstocked media variable
for i, var in enumerate(media_vars):
    vif_val = vif(X, i)
    print(f"{var}: VIF = {vif_val}")

# VIF > 5: concerning
# VIF > 10: severe multicollinearity
```

**Example**:
- VIF(TV) = 6.2, VIF(Radio) = 7.1 → TV and Radio are highly correlated
- Coefficient estimates swap roles; TV effect might jump from $0.5 to $2.0 with small data changes

**Mitigation**:
1. **Ridge regression**: Built-in handling of multicollinearity (shrinks correlated coefficients)
2. **PCA on correlated channels**:
   - If TV, Radio, Preroll are highly correlated, create a composite "Traditional + Video" channel
   - Trades interpretability for stability
3. **Domain-driven grouping**:
   - Recognize that TV and Radio work together (are part of the same "awareness" stage)
   - Model them jointly or with shared constraints
4. **Lag structure**:
   - If two channels peak at different times, they're less confounded
   - Use adstock with different decay rates to separate them

---

### 4. TV Decay Rate Sensitivity

**The Challenge**:
- TV's adstock decay rate (λ) is the single most impactful parameter choice
- Small changes to λ dramatically shift TV's estimated effectiveness

**Why TV is sensitive**:
- TV's effect is inherently hard to measure (brand building, halo effect, not direct response)
- TV's seasonality (peaks March–June) is similar to revenue seasonality
- TV's decay rate determines whether its impact is "short and sharp" or "long and slow"

**Example Sensitivity** (Club Piscine data):
```
λ = 0.2 (fast decay, half-life = 1 month)
  → TV ROAS = $2.1, Media contribution = 11.2%

λ = 0.5 (moderate decay, half-life = 2 months)
  → TV ROAS = $4.5, Media contribution = 12.8%

λ = 0.8 (slow decay, half-life = 6.6 months)
  → TV ROAS = $8.2, Media contribution = 16.3% ← Unrealistic?
```

**How to set λ**:
1. **Use industry benchmark for TV**: Typically 0.5–0.7 (3–7 month half-life)
2. **Run sensitivity analysis**: Model with λ = 0.3, 0.5, 0.7, 0.9
3. **Check diagnostics**:
   - Do results become more realistic as λ increases?
   - Does TV still show positive effect at high λ?
4. **Validate against business narrative**:
   - Client says: "TV is an early-season driver, preps the market for summer promotions"
   - Does this match the adstock shape? (e.g., early spend has effects through summer)
5. **Report a range**:
   - "Assuming λ = 0.5 (moderate carryover), TV ROAS is $4.5 [90% CI: $1.2–$7.8]"
   - "Under λ = 0.8 (strong carryover), TV ROAS rises to $8.2, but this may overstate effect"

---

## 8. Budget Optimization

### Two-Step Framework

The budget optimization mirrors the revenue management / markdown optimization framework from teaching:
1. **Step 1 (Demand Estimation)**: Fit response curves from historical data
2. **Step 2 (Optimization)**: Use response curves to solve for optimal allocation

**Revenue Management Analogy**:
- In markdown optimization: estimate demand curves for each product, then optimize prices
- In MMM: estimate response curves for each channel, then optimize media spend allocation

### Response Functions

From the MMM model, extract the response function for each channel:

```
Revenue_channel = Coefficient × Hill(Adstock(Spend))
```

Example for Preroll:
```
β_preroll = 0.0012 (coefficient per adstocked dollar)
Hill(x) = x^2 / (x^2 + K^2)  where K = $25K

Predicted revenue from Preroll = 0.0012 × Hill(Adstock(Spend_preroll))
```

### Budget Optimization Problem

**Objective**: Maximize total revenue subject to constraints

```
maximize:   Σ Revenue_channel(Spend_channel)
subject to:
  Σ Spend_channel = Budget (e.g., $284K/month)
  Spend_min_channel ≤ Spend_channel ≤ Spend_max_channel
  (% Traditional) ≥ 0.35, (% Digital) ≥ 0.35
  Confidence-based flexibility on each channel
  Σ Spend_all = Budget
```

**Constraints in MMM** (from client or business logic):
1. **Budget constraint**: Total fixed budget (or explore scenarios: -10%, base, +10%)
2. **Channel min/max**: E.g., TV $80K–$180K (maintain baseline presence)
3. **Mix constraints**: E.g., 35–65% traditional vs. digital (brand balance)
4. **Confidence flexibility**: Channels with HIGH confidence in ROAS get more freedom to reallocate; channels with LOW confidence stay close to current spend
5. **Strategic constraints**: E.g., "Furniture must be visible in 40% of media" (category-level goals)

### Optimization Algorithm

**For convex response functions** (Hill saturation):
- Problem is non-convex (Hill is concave, not convex)
- Use interior-point methods or sequential quadratic programming (SQP)
- Libraries: `scipy.optimize.minimize`, `cvxpy` (if linearized), or specialized tools

**Example** (Club Piscine):
```python
from scipy.optimize import minimize

def total_revenue(spend_vector):
    """Total revenue from all channels given spend allocation."""
    revenue = 0
    for i, channel in enumerate(channels):
        adstocked = geometric_adstock(spend_vector[i], lambda_i)
        saturated = hill_saturation(adstocked, K_i, alpha_i)
        revenue += coef_i * saturated
    return -revenue  # negative for minimization

constraints = {
    'type': 'eq',
    'fun': lambda x: sum(x) - total_budget  # sum(spend) = budget
}

bounds = [(min_i, max_i) for min_i, max_i in channel_bounds]

result = minimize(total_revenue, x0=current_spend, method='SLSQP',
                  bounds=bounds, constraints=constraints)
optimal_spend = result.x
```

### Interpreting Optimization Results

**Optimal Allocation Output**:
```
Channel            | Current | Optimal | Change  | Expected Revenue Lift
TV                 | $100K   | $80K    | -$20K   | -$45K (trade for others)
Radio              | $50K    | $60K    | +$10K   | +$8K
Preroll            | $25K    | $51K    | +$26K   | +$72K ← biggest opportunity
Web Banners        | $23K    | $30K    | +$7K    | +$21K
Social Media       | $20K    | $36K    | +$16K   | +$58K
Panneaux           | $10K    | $8K     | -$2K    | -$2K
Digital Flyers     | $13K    | $19K    | +$6K    | +$14K
─────────────────────────────────────────────────────
TOTAL              | $241K   | $284K   | +$0K    | +$124K (4.1% lift)
```

**Interpretation**:
- Preroll and Social Media are underallocated in the current mix
- TV is at strategic minimum; allocate less to fund higher-ROAS channels
- Total revenue lift: $124K/month (average across months)
- Percentage lift: 4.1% (over base revenue, accounting for seasonality)

---

### Budget Cut Scenarios

**Question**: "Can we cut the media budget by 15% without losing sales?"

**Approach**:
1. Reduce total budget by 15% (e.g., from $284K to $241K)
2. Re-optimize allocation for the lower budget
3. Compute expected revenue change

**Example Output**:
```
Budget Scenario: -15% ($241K)
  Optimal allocation: [TV=$70K, Radio=$45K, Preroll=$42K, Web=$22K, Social=$30K, Panneaux=$8K, Digital=$24K]
  Expected revenue: -0.1% (essentially flat)
  Interpretation: Yes, a 15% cut is feasible with optimized allocation

Budget Scenario: -10% ($255K)
  Expected revenue: +8.9% (surprisingly positive due to reallocation)
  Interpretation: Current allocation is so inefficient that a 10% cut with optimization beats current performance

Budget Scenario: Base ($284K)
  Expected revenue lift: +4.1% (from reallocation alone, no budget increase)

Budget Scenario: +10% ($313K)
  Expected revenue lift: +15.2%
  Interpretation: More budget is valuable if allocated to high-ROAS channels
```

---

## 9. Data Requirements Checklist

### Minimum Requirements

- [ ] **Revenue data**: Weekly or monthly, continuous for 2+ years
- [ ] **Media spend**: By channel, same frequency as revenue
- [ ] **No artificial gaps**: Data should cover consistent time periods (no missing months)

### Strongly Recommended

- [ ] **Weekly frequency**: Monthly data works, but weekly is more powerful
- [ ] **3+ years of history**: Captures seasonal patterns and business cycles
- [ ] **External factors**: Weather, holidays, economic indicators (if available)
- [ ] **Product-level granularity**: Revenue by category or product, if possible
- [ ] **Media metrics**: Impressions, GRPs, clicks (for context, not model input)

### Critical: Variation in Spend

- [ ] **Spend ranges widely**: Each channel should have 20%+ coefficient of variation
  - If a channel spends $10K every single month, its effect is unidentifiable
  - Variation is essential for the model to "see" the channel's impact
- [ ] **Channels not perfectly correlated**: TV and Radio shouldn't move in lockstep
  - Some separation (e.g., Radio peaks later) helps isolate effects

### Data Quality Checks

- [ ] **No sudden structural breaks**: E.g., change in store count, product mix, data collection method
- [ ] **Revenue and spend are consistent**: Same definition across time (e.g., always "media spend", not "media + production")
- [ ] **No data leakage**: Future data doesn't influence past periods
- [ ] **Outliers documented**: If a month is unusual (store closure, special event), note it

### Sample Size Interpretation

| Data Frequency | 1 Year | 2 Years | 3 Years |
|--------|--------|---------|---------|
| **Weekly** | 52 obs | 104 obs | 156 obs |
| **Monthly** | 12 obs | 24 obs | 36 obs |

**Adequacy for MMM**:
- **Weekly, 2+ years (104+ obs)**: Excellent; sufficient for automated tools (Robyn, Meridian)
- **Weekly, 1–2 years (52–104 obs)**: Good; manageable with careful regularization
- **Monthly, 3 years (36 obs)**: Minimum; requires strong domain knowledge and Ridge regularization
- **Monthly, 2 years (24 obs)**: Challenging; likely underpowered for 5+ channels

---

## 10. Club Piscine Specific Context

### Business Overview

**Client**: Club Piscine Select
**Category**: Pool, spa, outdoor furniture, and fitness equipment retailer
**Geography**: 42 stores across Quebec, Canada
**Fiscal Year**: November 1 → October 31
**Data Span**: 3 fiscal years (FY2023–FY2025), 36 monthly observations
**Time Period**: November 2022 – October 2025

### Key Financial Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| Total 3Y Revenue | $512.4M | All stores, all categories |
| Total 3Y Media Spend | $10.3M | ~$284K/month average |
| Media as % of Revenue | 2.0% | Spend as % of sales |
| Expected Media Contribution | 10–15% | Media explains 10–15% of revenue variation |

**Interpretation of 2% spend / 10% contribution**:
- Club Piscine spends ~2% of revenue on media
- This media drives ~10% of total revenue (i.e., each media dollar drives ~$5–$10 of revenue on average)
- This is typical for a mature, seasonally-driven retailer with strong repeat-customer base

### Product Categories (6 Equal)

All categories treated equally in modeling:

1. **HT** (Hot Tubs / Spas)
2. **CR** (Unknown—possibly Chemicals/Retail or another product line)
3. **SP** (Presumably Spas or Special Products)
4. **ME&GA** (Merged: Mobilier Extérieur (Outdoor Furniture) + Gym/Accessoires (Fitness))
5. **FI** (Fitness)
6. **BQ** (BBQ / Grills)

**Critical**: Do NOT treat categories separately in media modeling (too granular for N=36). Model all as "total revenue."

### Media Channels (7 Consolidated Groups)

Club Piscine negotiates with suppliers and consolidates their data into 7 media channel groups. Each group represents a strategic lever in the media plan.

| Channel | Components | Strategic Role | Seasonality |
|---------|------------|-----------------|------------|
| **Television** | TV spots (classic broadcast) | Brand building, market warming, early-season awareness | Peaks Mar–Jun (pre-season) |
| **Radio** | Radio + Radio Numérique (digital radio) | Tactical, frequency-driven, regional, mid-season promotions | Peaks Apr–Jul (event-based) |
| **Panneaux** | DOOH (Digital Out-of-Home) + Static billboards | Commute-based awareness, dual inspiration + promo role | Relatively steady with summer peak |
| **Social Media** | Facebook, Instagram, Pinterest, TikTok | Targeting, engagement, growth, visual storytelling | Consistent, peaks summer |
| **Preroll** | YouTube + Premium video content | Storytelling, upper-mid funnel, flexible creative | Flexible; can shift seasonally |
| **Banniere_Web** | Premium Display + Google Ads + LaPresse + Brand content | Mid-funnel, brand partnerships, premium environments | Peaks May–Jul |
| **Circulaire_Digitale** | Digital flyers via Flipp, Reebee | Conversion driver, promotional catalyst, mid-Jun onward | Peaks Jun–Jul (conversion phase) |

**Excluded Channels** (not in model):
- Google Shopping, Programmatic, Audio/Podcast, Direct Mail (Envois Postaux)
- Rationale: Low spend, overlap with included channels, or insufficient data

### Media Strategy Narrative

**Demand Cycle**:
1. **Inspiration Phase (Mar–mid Jun)**: TV and Radio create awareness; consumers dream of pools, spas, furniture
2. **Transaction Phase (mid Jun–Sep)**: Digital flyers, social, preroll convert intent to sales; installation peaks

**Channel Roles & Synergies**:
- **TV (brand rebuilding)**: Early season, builds halo effect that amplifies ALL other channels
  - Low direct ROI expected, but essential for brand credibility
  - Seasonality: Peaks March–May, trails off June–July

- **Radio (tactical mass medium)**: Takes over as TV declines mid-May; regional; 3-day promo events with in-store remotes (Apr–Jul)
  - Frequency-driven; works best with repeated messaging

- **DOOH/Panneaux (commute-based)**: Digital billboards with dayparting; dual role as inspiration (early) and promotional support (late season)
  - Relatively steady year-round, with summer spike

- **Digital Flyers (conversion driver)**: Most commercially-oriented lever; Flipp/Reebee integration; directly converts interest to purchase
  - Peaks mid-June onward; short-term effect

- **Preroll/Video (flexible)**: YouTube, premium video; upper/mid funnel; shorter lag than TV
  - Can shift spend flexibly within season

- **Social Media**: Targeting + engagement; works in parallel with traditional media
  - Consistent presence, drives followers and engagement

- **Web Banners**: Amplification role; Google + Facebook ecosystems; short-term effects
  - Digital extension of messaging, catch remaining demand

**Cross-Media Synergies**:
- No channel performs in isolation; the mix is an ecosystem
- TV creates a "halo effect" that makes radio, preroll, and social more effective
- Pre-loading: Media budgets intentionally brought forward relative to actual demand peaks

### Business Constraints (18 from Client)

Client provided 18 explicit constraints (documented in NB07). Key ones modeled in optimization:

| # | Constraint | How Modeled |
|----|-----------|------------|
| 12 | Strategic category visibility: Furniture 40%, Pools 30%, Spas 20%, BBQ 5%, Other 5% | Optimizer constraint on category allocation |
| 13 | Furniture as growth-led focus | Optimizer constraint (prioritize furniture visibility) |
| 15 | Deliberate fitness overinvestment (off-season traffic driver) | Optimizer constraint (fitness spend floor) |
| 16 | Inventory/installation capacity constraints | Optimizer constraint (revenue ceiling by season) |

**Unmodeled Constraints** (context for interpretation):
- Structural media mix evolution (traditional→digital shift): Noted, not explicitly modeled
- Creative execution quality: Conflated with media efficiency (not separated)
- Competitive pressure (Trevi, Sima, big-box retailers): Unmodeled (external data would help)
- Local store marketing: Unmodeled (aggregated to province level)
- Traditional media spill effects (TV reaches beyond Quebec): May underestimate TV impact

### Model Setup

**Two-Stage Ridge Regression** with:
- **Stage 1**: Fourier(order=2) + Weather (temperature, precipitation, sunshine)
- **Stage 2**: Ridge with CV-tuned alpha, geometric adstock, Hill saturation
- **Adstock parameters**:
  - TV: λ = 0.5 (half-life 2 months)
  - Radio: λ = 0.5
  - Panneaux: λ = 0.4
  - Social: λ = 0.1
  - Preroll: λ = 0.3
  - Web Banners: λ = 0.2
  - Digital Flyers: λ = 0.3
- **Saturation**: K = 0.7 × max(adstocked_spend), α = 2 for all channels
- **Regularization**: Alpha ≈ 100–200 (CV selected, but adjusted for causality)
- **Constraints**: Non-negative coefficients (NNLS) for final results; unconstrained for diagnostics

### Expected Results

**Model Performance**:
- Full model R² ≈ 0.86 (excellent fit)
- Seasonal model R² ≈ 0.83 (Fourier + weather explain most variation)
- Media-only R² ≈ 0.15 (media explains ~15% of residual variance after seasonality)

**Media Effectiveness**:
- **High-confidence channels** (Preroll, Social): ROAS $15–$30, pass all robustness checks
- **Medium-confidence channels** (TV, Radio): ROAS $0–$5, sensitive to parameter choices
- **Low-confidence channels** (Panneaux, Circulaire): ROAS near $0, not statistically significant
- **Overall media contribution**: ~11% of total revenue (typical for seasonal retail)

**Key Finding**: TV's low/negative ROAS does NOT mean TV is ineffective. Likely explanation is seasonality confounding (TV peaks March–May, sales peak June–August naturally). TV's real role is brand-building and halo effect (amplifying other channels), which the model doesn't capture directly.

### Known Limitations

1. **Sample Size**: N = 36 months (3 years); 14 parameters; ratio 2.6:1
   - Borderline adequacy; requires strong regularization
   - Mitigation: Use weekly data (156 observations) if available in future

2. **Seasonality Confounding**: TV and revenue both peak in spring/summer
   - Two-stage approach mitigates but doesn't eliminate
   - Mitigation: Add more granular seasonal controls, use weekly data

3. **Weather Data**: Single province-wide point for 42 geographically dispersed stores
   - Club Piscine spans urban (Montreal), suburban, and rural Quebec
   - Regional weather variation unmodeled

4. **No Interaction Terms**: Cross-media synergies (TV halo effect) not explicitly modeled
   - Captured implicitly (residuals of Stage 1 include halo), but not quantified
   - Would require larger sample to estimate reliably

5. **Channel Multicollinearity**: TV, Radio, Preroll all peak in spring
   - Coefficients are somewhat exchangeable; media composition is key
   - Sensitivity analysis across lambda values recommended

6. **Unobserved Confounders**: Store-level local marketing, in-store promotions, inventory
   - Modeled at aggregate level only
   - May bias channel coefficients

### Files & Code Convention

**Data Paths**:
- Sales: `data/raw/Historical sales by store and by division for 2023-2024-2025.xlsx`
- Media spend: `Budget_2023_.xlsx`, `Budget 2024`, `Budget 2025`
- Media details: `Recap_Tableau_Medias_2025.xlsx`
- Weather: Environment Canada API (fetched in NB04)

**Code Structure**:
- Notebooks: `01_data_audit.ipynb` → `02_data_cleaning.ipynb` → ... → `08_bayesian_mmm.ipynb`
- Transformations: `src/features/transformations.py` (single source of truth for adstock/saturation)
- Config: `config/params.yaml` (model parameters, channel groups, assumptions)
- Output: `reports/figures/` (all analysis plots), `reports/outputs/` (results tables)

**Data Formats**:
- Intermediate: `.pkl` (pandas pickles for efficiency)
- Final outputs: `.csv` (results tables), `.json` (parameters, optimization results)

---

## Summary: MMM in 60 Seconds

**What is MMM?** A statistical method to estimate how much revenue each marketing channel drives, accounting for seasonality, external factors, and confounding.

**Two-step process**: (1) Fit response curves from historical data, (2) optimize budget allocation using those curves.

**Core mechanics**:
- **Adstock**: Marketing impact carries over multiple periods (e.g., TV effect lasts 2+ months)
- **Saturation**: Diminishing returns (each dollar is less effective than the previous one)
- **Ridge regression**: Handles small samples and collinearity through regularization
- **Two-stage model**: Remove seasonality first, measure media on residuals

**Key challenge**: Distinguish media impact from natural seasonal demand. TV peaks in spring, sales peak in summer naturally. Did TV drive summer sales, or would summer have happened anyway? Two-stage approach separates these.

**Results**: ROAS (return on ad spend) by channel, media contribution %, budget optimization recommendations.

**Tools**: Meta Robyn (automated, large data), Google Meridian (Bayesian, small data), or custom Ridge regression (simple, auditable).

**Club Piscine**: 36 months, 7 media channels, ~11% of revenue is media-driven. Two-stage Ridge model with Bootstrap CIs.

---

## References

**Academic Framing**: Online Optimization, Demand Estimation, Markdown Optimization (Teaching.pdf, Professor Rob)

**Industry Tools**:
- Meta Robyn: https://github.com/facebookexperimental/Robyn
- Google Meridian: https://github.com/google/meridian

**Key Readings**:
- Hill, R. (1910). The possible effect of the aggregation of demand curves. Econometrica.
- Valizadeh, M., et al. (2021). Robyn: Open-source Marketing Mix Modeling. arXiv.
- Meridian: Bayesian Marketing Mix Modeling for the TensorFlow Probability Ecosystem.

**Club Piscine Project**:
- See `CLAUDE.md` (this project's requirements)
- Notebook pipeline: NB00–NB08
- Client constraints: NB07 (cell after `CLIENT_CONSTRAINTS`)

---

**Last Updated**: February 28, 2026
**Version**: 1.0
**Audience**: Claude agents, data scientists, marketing analysts working on MMM projects
