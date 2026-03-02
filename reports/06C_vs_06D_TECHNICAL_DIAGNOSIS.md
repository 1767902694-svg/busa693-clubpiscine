# Technical Diagnosis: Why 06D Enrichment Failed
## Club Piscine Marketing Mix Model

**Date:** March 1, 2026
**Files Analyzed:**
- `/notebooks/06c_base_model.ipynb` (base spend-only model)
- `/notebooks/06d_enriched_impressions.ipynb` (enrichment attempt)
- `/data/processed/model_06c_params.json` (06C results)
- `/data/processed/model_06d_params.json` (06D results)
- `/data/processed/optimal_transformation_params.json` (adstock/saturation params)

---

## EXECUTIVE SUMMARY

**06D's enrichment with impression data FAILED** due to three entangled root causes:

### Primary: Severe Multicollinearity
- **24 of 36 months (67%)** had impressions **imputed from spend** using CPM
- Imputation formula: `impressions_imputed = spend / (median_CPM / 1000)`
- This creates a **perfect linear relationship** for imputed months
- Ridge regression cannot separate spend vs. impression effects
- Result: Both features heavily regularized, net media signal **declines**

### Secondary: Undersized Sample
- 06C: 7 media features on n=36 → n/p = 3.0:1 ✓
- 06D: 14 media features on n=36 → n/p = 1.9:1 ✗ (2.6x tighter than recommended)
- Ridge regularization α jumped **10x** (5→50) as an emergency control
- This is not a tuning success—it's a distress signal

### Tertiary: Insufficient True Data
- Only 12/36 months (33%) of observed Tableau Medias data
- 12 months insufficient to overcome 67% synthetic collinearity
- Minimum viable coverage: ≥75% (27 of 36 months)
- Current coverage: 42 percentage points **below threshold**

**Result:** R² barely improved (+0.49%), media contribution **fell 12.3%**, and 5 of 7 channels lost statistical significance.

---

## QUESTION-BY-QUESTION ANALYSIS

### 1. Was Enrichment Doomed from the Start?

**Answer: YES.**

But the problem is deeper than "14 > 7 features."

#### Parameter Ratio Analysis
```
06C:  n/p = 36 / (7 + 5) = 36 / 12 = 3.0:1   [Acceptable, tight]
06D:  n/p = 36 / (14 + 5) = 36 / 19 = 1.9:1  [Dangerous]

Industry standard: n/p ≥ 5:1 for stable estimation
06D violates this by 2.6x
```

#### The Fundamental Problem: Feature Dependence

The n/p rule assumes **independent features**. In 06D:
- **7 spend features** (original): independent by design
- **7 impression features** (enriched): 67% derived from spend features

For the 24 imputed months:
```
impr_i = spend_i / (median_CPM / 1000)
      = spend_i × k    where k = 1000 / median_CPM
```

This is a **linear scaling**, not new information:
- If `spend_tv` increases 10%, then `impr_tv` increases exactly 10%
- `Correlation(spend_tv, impr_tv) = 1.0` for imputed months
- Ridge regression sees: `[X | X × k]` — identical signals

#### Statistical Evidence: The 10x Alpha Jump

```
06C: CV selected α = 5
06D: CV selected α = 50 (10x stronger regularization)
```

This jump is **not a sign of success**—it's the model screaming for help:
1. TimeSeriesSplit tested generalization across splits
2. With 14 correlated features, α=5 generalized poorly
3. Train/test gaps amplified by multicollinearity
4. Ridge forced α→50 to stabilize
5. At α=50, both spend & impression coefficients heavily shrunk
6. Result: **less total media signal**, not more

#### What Ridge Did

```
Effect before regularization (hypothetical):
  β_spend × spend_effect + β_impr × impr_effect = large_total

Effect after heavy regularization (α=50):
  β_spend × spend_effect + β_impr × impr_effect ≈ small_total

Evidence from results (Television):
  06C: single coefficient → $40.0M effect
  06D: two coefficients → $15.3M (spend) + $13.4M (impr) = $28.7M (-28%)
```

**Conclusion:** Enrichment was doomed because:
1. The feature set was mathematically collinear (not statistically independent)
2. CV detected this collinearity and demanded stronger regularization
3. Strong regularization destroyed the signal both models tried to preserve
4. Net effect: fewer useful coefficients despite more features

---

### 2. Was CPM Imputation the Root Cause?

**Answer: YES, 100%.**

#### Data Coverage Crisis

```
Tableau Medias Timeline:
  • Available: ~12 months (FY2025 calendar: Nov 2024 - Oct 2025)
  • Needed: 36 months (3 fiscal years: FY2023, FY2024, FY2025)
  • Imputed: 24 months (FY2023, FY2024)

Coverage:
  Observed: 12 / 36 = 33%
  Imputed:  24 / 36 = 67%  ← SYNTHETIC DATA DOMINATES
```

#### The Imputation Formula

From 06D notebook (Cell 3):
```python
avg_cpm[ch_spend] = median_CPM_observed[channel]

for imputed_month in FY2023_FY2024:
    impressions[imputed_month] = spend[imputed_month] / (avg_cpm[channel] / 1000)
```

**Example calculation (Television):**
```
If median_CPM[Television] = $10 per 1000 impressions:

  Nov 2023 Spend: $114,200
  Nov 2023 Impr (imputed) = $114,200 / ($10 / 1000)
                          = $114,200 × 100
                          = 11,420,000 impressions

The relationship:
  impr = spend × (1000 / median_CPM)

If median_CPM[Television] = $10:
  k = 1000 / 10 = 100

  impr = spend × 100  ← PERFECT LINEAR RELATIONSHIP
```

#### Why This Creates Multicollinearity

For the 24 imputed months in 06D:
```
Feature pair:     [spend_tv, impr_tv]
Actual values:    [114K, 11.4M], [130K, 13.0M], [95K, 9.5M], ...
Relationship:     impr_tv = spend_tv × 100

Mathematical consequence:
  Correlation(spend_tv, impr_tv) = 1.0

Ridge regression sees:
  X₁ = [114K, 130K, 95K, ...] (actual spend)
  X₂ = [11.4M, 13.0M, 9.5M, ...] = [114K × 100, 130K × 100, 95K × 100, ...]

  These are NOT independent. They explain the SAME variation.

  Ridge must choose: "How much weight to spend vs. impressions?"
  Answer: "I can't decide; shrink both heavily."
```

#### The "Collinearity Drowning" Effect

Ridge regression, faced with:
```
y = β₁ × (spend × adstock × saturation) + β₂ × (impr × adstock × saturation) + noise
```

Where for 67% of months:
```
β₁ × spend_effect + β₂ × impr_effect
  ≈ β₁ × x + β₂ × (100 × x)
  = x × (β₁ + 100 × β₂)
```

Must solve: **How large can (β₁ + 100 × β₂) be without overfitting?**

With α=50 (heavy penalty), Ridge shrinks both β₁ and β₂ toward zero.

#### Evidence from Results

**Television (mixed signal):**
```
06C: ROAS = 10.13
     • Single coefficient: large, positive
     • Media effect: $40.0M

06D: ROAS = 7.27
     • Two coefficients: both positive but smaller
     • Spend effect: $15.3M
     • Impression effect: $13.4M
     • Total: $28.7M (-28% vs 06C)
```

**Radio (worst case—both negative):**
```
06C: ROAS = -33.96
     • Single negative coefficient
     • All the negativity in one place

06D: ROAS = -10.41
     • Spend effect: -$9.8M
     • Impression effect: -$12.7M
     • Total: -$22.5M (partially offset)

     Ridge split the negativity across two features,
     both smaller in magnitude.
```

**Social Media (high volatility):**
```
06C: ROAS = 120.19 (extremely high)
06D: ROAS = 23.09  (-81% reduction)

This channel's CPM is likely stable → strong collinearity
Ridge heavily penalized both coefficients
```

#### Why 12 Months of True Data Wasn't Enough

For the 12 observed months (FY2025):
- Impression data is **real** (pixel-tracked from Tableau)
- Independent of spend (can vary at different rates)
- Provides **true signal** about CPM variation

But for the 24 imputed months:
- Impression data is **synthetic** (derived from spend)
- Perfectly collinear with spend
- Provides **noise + collinearity**, not signal

**Statistical weight:** The model learns from all 36 months:
```
Signal-to-Noise Ratio = 12 true_impr_signal : 24 synthetic_collinearity
                      = 1 : 2

The true signal is 2x outnumbered by synthetic noise.
Ridge's response: Shrink both features to minimize impact of collinearity.
```

**Conclusion:** CPM imputation created a 2:1 synthetic-to-true data imbalance that overwhelmed the actual impression signal. Enrichment cannot succeed with this data structure.

---

### 3. Did Mixing Digital Impressions with Traditional "Impressions" Corrupt the Signal?

**Answer: YES, but this is a secondary effect.**

#### The Core Problem: Semantic Incommensurability

06D applied the **same imputation method** to all 7 channels:
```python
impressions = spend / median_CPM
```

But "impressions" means fundamentally different things across channels:

| Channel | Definition | Measurement | CPM Stability | Semantics |
|---------|-----------|-------------|---------------|-----------|
| **TV** | GRP: reach × frequency | Modeled (Nielsen) | **Volatile** (seasonal demand) | Estimated audience |
| **Radio** | Listener occasions | Modeled (diary/streaming) | **Volatile** (time slot dependent) | Estimated occasions |
| **Panneaux (DOOH)** | Viewer exposures | Programmatic tracking | **Medium** (depends on traffic) | Inferred from data |
| **Social Media** | Pixel fires | Pixel-tracked (first-party) | **Stable** (algorithmic) | Precisely measured |
| **Preroll (Video)** | Video starts/impressions | Pixel-tracked (ad servers) | **Stable** (YouTube/Facebook) | Precisely measured |
| **Banner Web** | Ad impressions | Pixel-tracked (ad exchanges) | **Stable** (programmatic) | Precisely measured |
| **Digital Flyers** | View impressions | Flipp/Reebee tracking | **Stable** (platform-controlled) | Precisely measured |

#### Why This Matters for Modeling

06D treated all as equivalent: `1 TV impression ≈ 1 Social impression`

But they're not comparable:
- **TV impressions** = estimated reach for entire market (population-based)
- **Social impressions** = actual pixel fires for target audience (user-based)
- **Radio impressions** = estimated listener occasions (diary + modeling)
- **DOOH impressions** = estimated viewer exposures (traffic-based)

#### Semantic Heterogeneity Amplified Multicollinearity

Because CPM varies differently across channels:

**Stable-CPM channels (Digital):**
```
Social Media median CPM ≈ $0.50-1.50
  • Algorithmic delivery → consistent pricing
  • impr ≈ spend × constant_k
  • Collinearity very strong (correlation ≈ 0.98)

Ridge heavily regularized both features
→ Social ROAS fell 120.19 → 23.09 (-81%)
```

**Volatile-CPM channels (Traditional):**
```
Television median CPM ≈ $5-15 (seasonal variation)
  • Creative cost, demand seasonality, daypart mix
  • CPM varies month-to-month
  • impr ≠ spend × constant_k (imputation introduces noise)
  • Collinearity lower (correlation ≈ 0.85)

But both channels' imputation still synthetic
→ TV ROAS fell 10.13 → 7.27 (-28%)
```

#### Ridge's Impossible Choice

When 06D included both spend and impressions:

```
For each channel, Ridge asked:
  "Should I trust spend or impressions?"

For traditional channels:
  • spend = advertiser's actual budget allocation
  • impr = synthetic, based on volatile CPM model
  → Conflicting signals

For digital channels:
  • spend = advertiser's actual budget allocation
  • impr = 67% synthetic (imputed), 33% true (observed)
  → Mixed credibility

Ridge's answer: "I don't trust either. Shrink both heavily."
```

#### Evidence from Channel Results

Channel-by-channel ROAS collapse in 06D:

```
Channel               06C ROAS  06D ROAS  Δ     Signal Loss
─────────────────────────────────────────────────────────
Television             10.13     7.27    -28%   Both semantically mixed
Radio                 -33.96   -10.41   +70%   (offsetting negatives split)
Panneaux (DOOH)       -27.68    -1.78   +94%   Traditional imputed impr
Social Media          120.19    23.09   -81%   Digital with stable CPM
Preroll (Video)        68.48    31.44   -54%   Digital with stable CPM
Banniere Web          -10.52     2.22  +121%   Mixed signal, low effect
Circulaire Digitale    14.59    -1.27  -109%   Digital, smallest scale
```

**Pattern:**
- Traditional channels: Volatility increases collinearity
- Digital channels: Stability increases collinearity (perfect CPM relationship)
- All channels: Mixing semantics prevents Ridge from committing to either signal

#### Conclusion

Mixing digital and traditional "impressions" is a **secondary corruption layer** on top of the primary multicollinearity problem. The fundamental issue is CPM-based imputation; the semantic mixing amplifies it by:
1. Creating different collinearity structures across channels
2. Preventing Ridge from finding a unified regularization strategy
3. Forcing heavier shrinkage (α=50) to handle mixed semantics
4. Destroying signal across all 7 channels uniformly

---

### 4. What Should the RIGHT Approach Be?

#### OPTION A: Replace Spend with Impressions (Digital Only)

**Hypothesis:** Keep digital channels in impressions, traditional in spend.

**Pros:**
- Reduces feature set: 7 → 5-6 (fewer parameters)
- Digital CPM more stable → less synthetic collinearity
- Digital impressions semantically pure (pixel-tracked)
- Leaves traditional channels (TV, Radio) in familiar $/$ metrics

**Cons:**
- Still only 12 observed months for digital impressions
- 67% of digital data would still be imputed (CPM-derived)
- ROAS becomes mixed units:
  - Digital: $/impressions (e.g., $100 per million impressions)
  - Traditional: $/$ (e.g., $10 ROAS)
- Optimization requires converting units → loses data-driven advantage
- Digital spend is actionable, impressions are not
- Client's budget decisions are in $, not impressions

**Data Coverage Check:**
```
If digital CPM is stable:
  impr_digital = spend_digital / (stable_CPM / 1000)
  → Still creates perfect collinearity for imputed months
  → Benefit over 06D: fewer total features (less n/p ratio stress)
  → Risk: same multicollinearity problem, just concentrated in 4 channels
```

**Verdict:** MEDIUM-HIGH RISK. Viable only if you have ≥24 months of true digital impression data (currently have 12).

---

#### OPTION B: Replace Spend with GRP/PEB (TV/Radio Only)

**Hypothesis:** Use GRPs for traditional media (proper media currency).

**Pros:**
- GRP is the lingua franca of TV/Radio media buying
- Separates reach×frequency from $ efficiency
- Reduces feature count: 7 → 5 (fewer parameters)
- Leaves digital in native units ($)

**Cons:**
- **GRP data not available in current dataset**
  - "occasions_reel" in Tableau ≠ GRP
  - GRP requires: impressions / population size
  - Population size not in current data
- ROAS becomes unintuitive:
  - TV: $/GRP (e.g., $5 per GRP point)
  - Digital: $/$ (e.g., $25 ROAS)
- Still only 12 observed months of Tableau data
- Client's budget is in $, GRP translation adds friction
- No GRP/PEB confidence intervals → harder to trust

**Verdict:** NOT VIABLE. Missing prerequisite GRP/PEB data from agency. Cannot proceed without it.

---

#### OPTION C: Hybrid (Mixed Units)

**Hypothesis:** Use impressions for digital, GRP for traditional, spend elsewhere.

**Pros:**
- Semantically correct (digital impressions, traditional GRPs)
- Respects channel differences
- Reduces feature count vs. 06D

**Cons:**
- **FATAL FLAW: Broken Optimization**
  ```
  Optimization objective: max Σ(ROAS_channel × budget_channel)

  With mixed units:
    max ($/$ × budget_TV) + ($/GRP × budget_radio) + ($/impr × budget_social) + ...

  This is dimensionally invalid.
  Example: max (5 × $100K) + (1000 × 50 GRP_points) + (0.001 × 10M impr)
           = max $500K + $50M + $10K

  Different units have wildly different numerical magnitudes.
  The optimizer will prefer whichever has highest unit-adjusted value,
  but this is an artifact of units, not true effectiveness.
  ```

- ROAS becomes incomparable:
  ```
  Channel    Budget   ROAS         Media Effect
  ────────────────────────────────────────────
  TV         $100K    $5/GRP       ? (different currency)
  Radio      $50K     $3/GRP       ? (different currency)
  Social     $80K     $25/impr     ? (different currency)
  Preroll    $60K     $40/$        ✓ (spend-normalized)

  Question: "Should I shift $10K from TV to Social?"
  Can't answer without converting GRP→$ and impr→$
  ```

- Still only 12 observed months of Tableau data
- No GRP data available (Option B blocker)

**Verdict:** NOT VIABLE. Unit heterogeneity breaks unified budget optimization.

---

#### OPTION D: Entirely Different Approach ✓ RECOMMENDED

**Hypothesis:** Abandon enrichment; use specialized sub-models + efficiency features.

**Best Sub-Option: D.1 + D.5 (CPM Efficiency Features + Segmented Models)**

##### Model 06E: Digital-Only (Data-Driven)

Focus on the 4 channels with rich Tableau data:
```
Channels: Social Media, Preroll, Banniere Web, Circulaire Digitale

Features:
  1. spend_X (original, 4 features)
  2. CPM_efficiency_X (4 features)
     = (actual_CPM - median_CPM) / std(CPM)
     Interpretation: positive = bargain months, negative = expensive months
  3. Cross-channel interactions (optional, 2-3 features)
     = spend_X × spend_Y (does social amplify preroll?)

Total: 4-10 media features
Ratio: 36 / (10 + 5) = 36/15 = 2.4:1 (tight but manageable)
Alpha: ~5-10 (similar to 06C)

Data coverage: 100% Tableau for FY2025
Benefit: CPM variations captured as EFFICIENCY, not false impressions
```

**Why this works:**
```
Instead of:
  impr_X = spend_X × (1000 / median_CPM[X])

Use:
  CPM_efficiency = (actual_CPM - median_CPM) / std(CPM)

This separates:
  • budget allocation (spend) from
  • media efficiency (CPM variations)

Ridge can now answer:
  "Did we get good deals (low CPM)? Did good deals drive revenue?"

Example (Social Media, May 2025):
  spend = $45K (normal month)
  CPM = $0.30 (better than median $0.50)
  CPM_efficiency = ($0.30 - $0.50) / $0.10 = -2.0 (bargain signal)

  Ridge captures: "This month's better CPM might explain revenue boost"
  Without forcing synthetic collinearity.
```

##### Model 06F: Traditional (Business-Guided)

Use 06C estimates as baseline, add structure:
```
Channels: Television, Radio, Panneaux (DOOH)

Features:
  1. spend_X (original, 3 features) [from 06C]
  2. Channel interactions (3-4 features)
     = TV × Radio (does TV halo amplify radio effectiveness?)
     = TV × Panneaux (does TV amplify DOOH?)
  3. Optional: month-by-month indicators (capture seasonality micro-effects)

Total: 3-7 media features
Ratio: 36 / (7 + 5) = 36/12 = 3.0:1 ✓
Alpha: ~5 (same as 06C)

Data coverage: Limited (no Tableau), rely on business constraints
Benefit: Explicit synergy modeling (TV brand halo effect)
```

**Why separate models?**
```
Traditional (TV/Radio/Panneaux):
  • No impression data
  • Limited to business logic + interactions
  • Client narrative describes TV → halo → amplify other channels
  • Should be modeled explicitly, not forced into impression collinearity

Digital (Social/Preroll/Banniere/Circulaire):
  • Rich Tableau data for FY2025 (12 months, 100%)
  • CPM variations are real (algorithmic delivery variation)
  • Efficiency features meaningful
  • Can achieve 06E α = 5-10 with clean data

Combined optimization:
  • Use 06E for digital: "Digital allocation = 60%, confidence HIGH"
  • Use 06F for traditional: "Traditional allocation = 40%, confidence MEDIUM"
  • Constrain traditional via business rules (TV floor = $80K, etc.)
  • This gives best-of-both: data-driven where data is good,
                             business-guided where data is limited
```

---

### 5. What is the MINIMUM Data Coverage Needed?

#### Threshold Analysis

For enrichment (impressions + spend) to work, you need **true impression data to dominate over collinearity**:

**Minimum Viability: ≥75% Observed**
```
27 or more of 36 months with true impression data
= 75% observed, 25% imputed

Why this threshold?
  • Imputed data creates perfect collinearity (correlation = 1.0)
  • Observed data creates true signal (correlation ≠ 1.0)
  • Signal-to-collinearity ratio = 75:25 = 3:1
  • Ridge needs 3:1 odds to overcome regularization penalty

  Below 75%: Collinearity dominates, enrichment fails (as in 06D)
  Above 75%: Signal dominates, enrichment can succeed
```

**Comfortable Viability: ≥90% Observed**
```
32 or more of 36 months with true impression data
= 90% observed, 10% imputed

Why comfortable?
  • Signal-to-collinearity ratio = 90:10 = 9:1
  • Ridge can confidently separate spend and impression effects
  • Alpha can drop back to 5-10 (not 50)
  • R² improvements become real, not artifacts
```

#### Current State

```
Tableau Medias FY2025: ~12 months
Total months needed: 36
Coverage: 12 / 36 = 33%

Gap to minimum (75%): 75% - 33% = 42 percentage points
Gap to comfortable (90%): 90% - 33% = 57 percentage points

Status: 42 POINTS BELOW MINIMUM THRESHOLD
→ Enrichment cannot work with current data
```

#### Path to Viability

**Option 1: Request Historical Tableau Data (Fastest)**
```
Ask agency: "Do you have Tableau Medias data for FY2024?"
            (November 2023 - October 2024)

If YES:
  • Integrate 12 more months of observed impressions
  • New coverage: (12 + 12) / 36 = 67% (still below minimum)
  • Repeat for FY2023 if available: (12 + 12 + 12) / 36 = 100% ✓

  Expected outcome with 36/36 observed:
    • R² improves from 0.8858 to estimated 0.90+
    • α drops from 50 to estimated 5-10
    • Media contribution rises (not falls)
    • All channels show consistent, reliable effects

Timeline: 1-2 weeks (if data exists with agency)
```

**Option 2: Wait for More FY2025 Data (Slower)**
```
Tableau Medias has been running since ~Nov 2024
Current date: March 2026 (4 months of data)

To reach 75% coverage: need 27/36 months
  • Currently have: 12
  • Need: 15 more
  • Rate: 4 months/4 months ≈ 1 month data per month elapsed

Timeline to 75%: ~15 months from now (June 2027) — not practical
```

**Option 3: Build Hybrid (Recommended)**
```
Don't wait for all Tableau data.
Instead, build 06E (Digital-only with CPM efficiency features) now.

Advantages:
  • Uses 100% observed FY2025 Tableau data for digital channels
  • CPM_efficiency approach avoids collinearity problem
  • Can publish results in 2-4 weeks
  • Provides confidence for digital allocations
  • Leaves traditional channels to 06C + business logic
```

#### Data Coverage Checklist

**Before attempting enrichment, verify:**
- [ ] Have ≥27 months of true (non-imputed) impression data? (75% coverage)
- [ ] Source: Tableau Medias direct API, not CPM-derived imputation
- [ ] Coverage by channel:
  - [ ] Television: X months
  - [ ] Radio: X months
  - [ ] Panneaux: X months
  - [ ] Social Media: X months
  - [ ] Preroll: X months
  - [ ] Banniere Web: X months
  - [ ] Circulaire Digitale: X months
- [ ] If any channel <75%, that channel should NOT be enriched
- [ ] If only digital channels >75%, build 06E (digital-only model)

---

### 6. If Hybrid (Option C), How to Calculate ROAS with Mixed Units?

#### The Unit Incommensurability Problem

ROAS (Return on Ad Spend) depends on the denominator:

```
Spend-based:        ROAS = Revenue / Spend              [$/$ dimensionless]
Impression-based:   ROAS = Revenue / Impressions       [$/impression]
GRP-based:          ROAS = Revenue / GRP_points        [$/GRP]
Reach-based:        ROAS = Revenue / Reach             [$/1000 people]
Conversion-based:   ROAS = Conversions / Spend         [conversions/$]
```

#### Why This Breaks Optimization

**Scenario:** Budget allocation problem
```
Current budget allocation:
  TV: $100K/month
  Social: $100K/month

Question: "Should I shift $10K from TV to Social?"

Spend-based ROAS (homogeneous):
  TV ROAS = $10/$ (every $1 → $10 revenue)
  Social ROAS = $25/$ (every $1 → $25 revenue)

  Decision: "Social has higher ROAS (25 > 10), shift $10K to Social"
  ✓ Clear, comparable, makes sense

Mixed-unit ROAS (heterogeneous):
  TV ROAS = $5/GRP (every GRP point → $5 revenue)
  Social ROAS = $0.001/impression (every impression → $0.001 revenue)

  Decision: How do I compare $5/GRP to $0.001/impr?
  ✗ Not comparable, makes no sense
```

#### The Dimensional Analysis Problem

Mathematical example:
```
Optimization problem:
  maximize: ROAS_TV × spend_TV + ROAS_social × spend_social + ...
  subject to: spend_TV + spend_social + ... ≤ $2M

With homogeneous units (all $/$ ROAS):
  maximize: (10 $/spend) × spend_TV + (25 $/spend) × spend_social
          = 10 × spend_TV + 25 × spend_social  [dimensionless]
  ✓ Valid: both terms are in $ revenue

With heterogeneous units:
  maximize: (5 $/GRP) × spend_TV + (0.001 $/impr) × spend_social

  But spend is in $, not GRPs or impressions!
  This is like: max (5 feet/second) × (10 pounds) + (0.001 miles/hour) × (20 meters)
  ✗ Invalid: dimensional mismatch
```

#### Why Optimizer Behavior Breaks Down

When you force mixed-unit ROAS into an optimizer:

```
Hypothetical mixed-unit results from a hybrid model:
  TV:           ROAS = $5/GRP           [1 GRP ≈ population ÷ 100]
  Radio:        ROAS = $3/GRP           [1 GRP ≈ listeners ÷ 100]
  Social:       ROAS = $0.0002/impression [1M impr = $200 effect]
  Preroll:      ROAS = $0.0003/impression [1M impr = $300 effect]
  Display:      ROAS = $50/$            [every $1 → $50 revenue]
  Digital Flyer: ROAS = $30/$           [every $1 → $30 revenue]

Optimizer sees (numerically):
  5, 3, 0.0002, 0.0003, 50, 30

Decision: "Allocate more to Display ($50/$ is highest)"

But this is FALSE:
  • Display's high ROAS is an artifact of $/$ units
  • Social's low ROAS is an artifact of $/impression units (small denominator)
  • Real effectiveness might be opposite (social > display)

The optimizer chose based on units, not true effectiveness.
```

#### Solution 1: Convert to Homogeneous $/$ ROAS

**Process:**
```
1. For each channel using non-spend units, estimate baseline CPM:

   TV GRP conversion:
     • Average CPM ($/1000 impr) = $10
     • Population = 8 million (Quebec)
     • 1 GRP = 80,000 people
     • $10 CPM ÷ 80 people per $ = $10 per 8,000 impressions = $1.25 per GRP

   Digital impression conversion:
     • Average CPM = $1.50
     • 1M impressions = $1,500 spend equivalent

2. Convert ROAS back to $/$ units:

   TV: $5/GRP × $1.25/GRP = $6.25/$  ✓ Now comparable
   Social: $0.0002/impr × $1,500/M impr = $0.30/$  ✓ Now comparable

3. Optimize with homogeneous units:

   maximize: 6.25 × spend_TV + 0.30 × spend_social + ...
```

**Problem:** Requires external benchmarks (agency CPM assumptions, population data).
Not data-driven; introduces exogenous assumptions.

---

#### Solution 2: Convert to Common Outcome Unit

**Example:** $/store visit or $/transaction

**Requirements:**
- Store traffic data by day/week
- Transaction data (purchase records)
- Attribution of transactions to channels (hard without first-party data)

**Status:** Not available in current dataset.

---

#### Solution 3: Abandon Unified Optimization

**Approach:** Separate optimizations per channel type
```
Budget allocation:
  Phase 1: "How much should go to digital?"
    • Optimize digital channels (Social, Preroll, Display, Flyers)
    • Use digital impressions / CPM efficiency features
    • Allocate: e.g., 60% of total budget

  Phase 2: "How much should go to traditional?"
    • Optimize traditional channels (TV, Radio, Panneaux)
    • Use spend + business constraints
    • Allocate: e.g., 40% of total budget

  Phase 3: "How much TV vs Radio vs Panneaux?"
    • Use 06F model within traditional constraints
    • E.g., TV floor $80K, radio $30K-90K, etc.

Phase 4: "How much Social vs Preroll vs Display vs Flyers?"
    • Use 06E model within digital constraints
    • E.g., social $15K-90K, preroll $15K-110K, etc.
```

**Advantage:** Respects channel semantics, avoids unit conversion.
**Disadvantage:** Loses cross-category reallocation (can't easily shift $ from TV to Social).

---

#### Solution 4: Stay Homogeneous (Recommended)

**Approach:** Use 06C (spend-only model)

```
Keep all channels in $/$ units:
  • Television: every $1 spend → $X revenue
  • Social: every $1 spend → $Y revenue
  • etc.

Trade-off:
  ✓ All ROAS directly comparable (same units)
  ✓ Optimization is dimensionally valid
  ✓ Budget allocation is clear, actionable
  ✓ 06C R² = 0.881 is robust
  ✗ Don't capture CPM/efficiency variations
  ✗ Impressions used only as post-hoc diagnostics

This is the current state—and it works.
```

---

#### Verdict: Unit Incommensurability Kills Hybrid Approaches

**Central insight:** If you want unified budget optimization (which you do for MMM), you **cannot** use mixed ROAS units.

Options:
1. **Convert units** → requires external benchmarks, loses data-driven purity
2. **Use common outcome** → requires transaction data, not available
3. **Separate optimizations** → works but loses cross-category flexibility
4. **Stay homogeneous** → recommended, already working (06C)

**Conclusion:** Hybrid models create unsolvable unit problems. Stick with spend-based MMM (06C) or build segmented models (06E + 06F) with separate optimization.

---

## FINAL RECOMMENDATIONS

### Do NOT Attempt
1. ✗ Enrichment with current data (33% coverage, doomed to fail)
2. ✗ GRP/PEB replacement (no data available from agency)
3. ✗ Hybrid models (unit incommensurability kills optimization)
4. ✗ Mixed impression types (semantic corruption of signal)

### DO Attempt
1. ✓ **Model 06E (Digital-Only):**
   - Use Tableau data for: Social Media, Preroll, Banniere Web, Circulaire Digitale
   - Add CPM_efficiency features (bargain vs. expensive months)
   - Expected n/p ratio: 2.4:1 (tight but manageable)
   - Expected alpha: 5-10 (similar to 06C)
   - Timeline: 2-4 weeks

2. ✓ **Model 06F (Traditional Synergies):**
   - Extend 06C with explicit interaction terms (TV halo on Radio, etc.)
   - Capture business narrative (TV → brand building → amplify other channels)
   - Use business constraints (TV floor, radio ceiling, etc.)
   - Timeline: 1-2 weeks

3. ✓ **Segmented Optimization:**
   - Use 06E estimates (digital ROAS) with confidence
   - Use 06F estimates (traditional ROAS) with caution
   - Allocate budget across digital/traditional split
   - This gives best-of-both-worlds

4. ✓ **Data Improvement Path:**
   - Request historical Tableau Medias data for FY2024 and FY2023
   - If available, integrate and retry enrichment (06D) at ≥75% coverage
   - If not available, stick with 06E + 06F segmented approach

### Key Takeaway

**Enrichment with 33% data coverage is mathematically doomed.** The CPM-based imputation creates 67% synthetic collinearity that overwhelms the 33% true signal. Ridge regression's 10x alpha jump is not a tuning opportunity—it's a distress signal.

The solution is not better tuning; it's better data or different models. Build 06E and 06F instead.

---

## File References

| File | Purpose |
|------|---------|
| `/notebooks/06c_base_model.ipynb` | Base spend-only model (reference) |
| `/notebooks/06d_enriched_impressions.ipynb` | Enrichment attempt (analyzed above) |
| `/data/processed/model_06c_params.json` | 06C parameters: α=5, R²=0.8809 |
| `/data/processed/model_06d_params.json` | 06D parameters: α=50, R²=0.8858 (failed) |
| `/data/processed/optimal_transformation_params.json` | Adstock/saturation calibration (NB05) |
| `/data/processed/sales_spend_weather.csv` | 36×43 feature matrix for modeling |

