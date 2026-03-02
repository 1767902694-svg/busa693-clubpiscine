# Club Piscine MMM: Unused Data & Feature Enrichment Opportunities

**Date**: 2026-03-01
**Objective**: Identify unused data in raw files that could improve the Marketing Mix Model (NB06c)

---

## Executive Summary

The current model uses only **media spend ($) and weather** as media drivers. However, the `Recap_Tableau_Medias_2025.xlsx` file contains **rich performance data** (impressions, clicks, GRPs, engagement rates, CPM) that is **NOT being used**. This analysis identifies **4 major categories of unused data** and recommends **specific features** that could improve model power.

**Key Finding**: Impressions data is available for **52 monthly observations** (14% of the model period) and shows **moderate-to-strong correlations** with spend (r = 0.58 to 0.82), suggesting that using impressions as an alternative or complement to spend could decouple **media volume from media cost** and improve attribution.

---

## 1. Current Model Architecture

### Data Currently Used
- **Target**: `total_all_revenue` (monthly, 36 observations, fiscal years 2023–2025)
- **Media Features**: 7 channels × spend ($) only
  - `spend_television`, `spend_radio`, `spend_panneaux`, `spend_social_media`, `spend_preroll`, `spend_banniere_web`, `spend_circulaire_digitale`
- **Weather Features**: 12 variables
  - Temperature (mean, max, min, rolling 7d), precipitation, sunshine hours, degree days, days above temperature thresholds
- **Seasonality**: Fourier order 1 (sin/cos annual cycle)
- **Total features**: ~43 columns, 36 monthly rows

### Model Pipeline
1. NB02: Data Cleaning (stores aggregated to monthly, categories consolidated)
2. NB04: Weather feature engineering (province-wide, calendar-to-fiscal conversion)
3. NB05: Adstock & saturation transformations (Ridge regression with L2 penalty)
4. NB06c: Causal inference & ROAS estimation

---

## 2. Unused Data Source: `Recap_Tableau_Medias_2025.xlsx`

### File Structure
- **Processed as**: `tableau_medias_performance.csv` (383 records, 16 columns)
- **Coverage**: Nov 2024 – Oct 2025 (FY2025) + partial FY2024 data
- **Granularity**: Campaign-level (individual media placements)
- **Aggregation needed**: Campaign → channel → month (for model merge)

### Available Metrics

#### **A. Volume Metrics** (Currently Unused)
| Metric | Description | Coverage | Values |
|--------|-------------|----------|--------|
| `impressions_reel` | Actual impressions delivered | 89/383 (23%) | Up to 34M per placement (Panneaux digital) |
| `occasions_reel` | Advertising opportunities/OTS | 296/383 (77%) | Media volume metric |
| `peb_reel` | **GRP (Gross Rating Points)** for traditional | 168/383 (44%) | TV, Radio, DOOH placements |
| `clics_reel` | Digital clicks | 94/383 (25%) | Web Banner (490K total), Social (203K) |
| `vues_completees` | Video views (complete placements) | 30/383 (8%) | Digital video/preroll |

#### **B. Engagement Metrics** (Currently Unused)
| Metric | Description | Coverage | Usage |
|--------|-------------|----------|-------|
| `taux_clics` | Click-through rate (%) | 94/383 (25%) | Digital performance proxy |
| `taux_vues` | Video completion rate (%) | 30/383 (8%) | Preroll/video engagement |
| `cpm_calculated` | Cost per 1,000 impressions | 294/383 (77%) | Media cost efficiency |

#### **C. Quality Indicators**
| Metric | What It Reveals |
|--------|-----------------|
| Support-level details (TV station, radio station, platform) | Channel-specific performance variance |
| Date ranges (`date_debut`, `date_fin`) | Campaign timing & overlap |
| Media type classification | Traditional vs. digital distinction |

---

## 3. Monthly Data Availability Assessment

### Impressions Coverage
**Total monthly impressions aggregations: 52 observations** (vs. 36 in model)

| Channel | Months with Data | Coverage | Sample Size |
|---------|-----------------|----------|------------|
| **Banniere_Web** | 12 | ~33% of model | Web banners, Google Ads |
| **Social_Media** | 12 | ~33% of model | Facebook, Instagram, Pinterest, TikTok |
| **Television** | 4 | ~11% of model | Q1–Q2 FY2025 (seasonal) |
| **Panneaux** | 5 | ~14% of model | Digital billboards, DOOH |
| **Radio** | 7 | ~19% of model | Station-level GRP data |
| **Circulaire_Digitale** | 7 | ~19% of model | Digital flyers (Flipp, Reebee) |
| **Preroll** | 5 | ~14% of model | YouTube, video placements |

**Key Insight**: Digital channels (Web, Social) have the most complete impressions data (12 months). Traditional media (TV, Radio) have partial coverage but rich GRP data.

### Correlation: Spend vs. Impressions

| Channel | r | Interpretation |
|---------|---|-----------------|
| Panneaux | 0.824 | Strong: spend reliably predicts impressions |
| Circulaire_Digitale | 0.729 | Strong: cost-per-impression stable |
| Banniere_Web | 0.688 | Moderate-strong: some cost variation |
| Radio | 0.596 | Moderate: rate negotiation/bonus spots |
| Social_Media | 0.577 | Moderate: audience fluctuation |
| Television | 0.578 | Moderate: seasonal rate variation |
| Preroll | 0.078 | **Weak: spend ≠ impressions** (data quality or pricing issues) |

**Strategic Implication**: For channels with r < 0.65 (TV, Radio, Social), impressions as a **separate input** would capture media delivery independent of negotiated rates.

---

## 4. Proposed New Features

### **PRIORITY 1: HIGH IMPACT (Recommended for Implementation)**

#### **Feature Set A: Monthly Impressions by Channel** ✓
**File Location**: Create from `tableau_medias_performance.csv`
**Columns to Add**: 7 columns, one per channel
```
impr_banniere_web         # Millions of impressions
impr_circulaire_digitale
impr_panneaux
impr_preroll
impr_radio                # GRP-based impressions for traditional media
impr_social_media
impr_television
```

**Rationale**:
- Impressions measure **consumer exposure** (what people see), independent of rate negotiations
- Separates **media volume** from **media cost**: same $100K budget could deliver 2M or 5M impressions
- Reduces endogeneity from budget gouging/rate discounts in individual months
- Strong correlation (r=0.73–0.82) for digital channels suggests reliable signal

**Implementation**:
- Aggregate campaign-level `impressions_reel` to monthly by channel
- Forward-fill missing months (e.g., TV off-season) with 0 or lagged values
- Scale by 1M for readability (impressions in units of millions)

**Model Integration**:
- Add as Stage 2 features alongside spend (or as replacement for spend in robustness check)
- Apply same adstock & saturation transformations as spend

---

#### **Feature Set B: Cost-per-Click (CPC) by Digital Channel** ✓
**Columns to Add**: 4 columns (digital channels only)
```
cpc_banniere_web         # Cost per click ($)
cpc_social_media
cpc_preroll
cpc_circulaire_digitale
```

**Rationale**:
- Measures **engagement quality**: clicks indicate actual user interest
- Digital channels have rich click data (756K clicks across Web, Social, Preroll, Flyer)
- CPC fluctuations reflect:
  - Audience quality (high CPC = smaller, more qualified audience)
  - Seasonal competition (April-May: peak seasonality, possible higher CPC)
  - Platform algorithm changes (CTR compression, CPM inflation)

**Interpretation as Model Feature**:
- Lower CPC = more efficient engagement (complements ROAS)
- Could interact with spend (spend × CPC might proxy for "engagement volume")
- Median CPC: Web $1.05, Social $1.99, Preroll $10.50

**Implementation**:
- Monthly CPC = total monthly spend ÷ total monthly clicks
- Handle zeros: use rolling 3-month median CPC when current month has 0 clicks

---

#### **Feature Set C: CPM (Cost per 1,000 Impressions) Index by Channel** ✓
**Columns to Add**: 7 columns (normalized CPM ratio)
```
cpm_index_television      # CPM / channel_median_CPM (ratio < 1 = below-market)
cpm_index_radio           # Signals rate negotiation success or audience shifts
cpm_index_panneaux        # (etc.)
```

**Rationale**:
- CPM shows **media cost efficiency**: channels paying below-market rates are getting better deals
- Useful for traditional media (TV, Radio) where GRP quality varies by placement
- Index form (current CPM ÷ median) is scale-free and interpretable
  - 0.8 = 20% cheaper than channel median (good negotiation)
  - 1.2 = 20% premium (might reflect premium placements or peak season)

**Data Quality**:
- Radio has rich GRP data (142 records): can calculate reliable CPM benchmarks
- TV has seasonal CPM variation (low Jan-Feb, high Apr-Jul)

**Implementation**:
- Calculate channel-level median CPM across all months
- Monthly CPM index = actual CPM ÷ median
- Fills partially for traditional media (TV, Radio with GRP data)

---

### **PRIORITY 2: MEDIUM IMPACT (Useful Diagnostics)**

#### **Feature Set D: Click-Through Rate (CTR) for Digital Channels**
**Columns to Add**: 4 columns
```
ctr_banniere_web         # Clicks / impressions (%)
ctr_social_media
ctr_preroll
ctr_circulaire_digitale
```

**Rationale**:
- Measures **creative effectiveness**: higher CTR = compelling ad message
- Complements spend & impressions with **engagement quality**
- Can diagnose whether low ROAS is due to poor creative (low CTR) vs. poor conversion (high CTR, low sales)

**Data Quality**:
- Available for 36 monthly observations (all digital channels combined)
- Range: 0.003% to 0.071% (typical for digital display)

**Caution**:
- CTR is NOT correlated with sales (clicks ≠ conversions; conversions ≠ revenue)
- Use as **diagnostic** only, not primary model feature

---

#### **Feature Set E: Media Budget Composition (% Traditional vs. Digital)**
**Columns to Add**: 1 column
```
pct_traditional_media    # (TV + Radio) / total_spend
pct_digital_media        # (Web + Social + Preroll + Circulaire) / total_spend
```

**Rationale**:
- Client constraint #1 notes **structural media mix evolution** (traditional → digital shift)
- This captures the shift as an input feature
- Helps model understand **changing channel ecosystem**

**Current Trajectory**:
- FY2023: ~45% traditional, 55% digital
- FY2025: ~35% traditional, 65% digital (trend toward digital)

---

### **PRIORITY 3: EXPLORATORY (Low Priority, Requires Further Investigation)**

#### **Feature Set F: Seasonal Impression Index**
- Peak months for impressions (May: 164M impressions vs. Oct: 5M impressions)
- Could create impression seasonality separate from spend seasonality
- Would help identify whether media volume or cost is the driver of seasonal variation

#### **Feature Set G: Campaign Overlap / Multi-Channel Synergy Indicator**
- Days when multiple channels ran simultaneously
- Could proxy for cross-media halo effects (TV + Radio + Social in same week)
- Requires detailed campaign calendars (date_debut, date_fin by channel)

---

## 5. Data Quality & Gaps

### Strengths
| Aspect | Status | Impact |
|--------|--------|--------|
| Digital impressions | Complete for Web, Social (12 months) | Can use as primary model feature |
| Click data | 756K clicks, granular | Good for engagement diagnostics |
| GRP data for traditional | 142 radio placements, TV data | Bridges traditional media to impressions |
| CPM calculation | 294/383 records | Cost efficiency indexing viable |

### Limitations
| Gap | Reason | Workaround |
|-----|--------|-----------|
| TV impressions sparse (4 months) | Seasonal (Mar-Jul only) | Use GRP ↔ impressions conversion; or skip TV impressions |
| Preroll impressions missing | Data collection gap | Use clicks + CPC proxy; or use GRP estimates |
| No weekly data in Tableau | Aggregated to monthly | Use weekly data from sales file (156 rows) if higher frequency model needed |
| Single province weather | 42 stores geographically dispersed | Current proxy acceptable; store clustering needed for future |

---

## 6. Answer to Client Question: "Should we use impressions instead of spend?"

### **Recommendation: BOTH, as complementary inputs**

**Option 1: Impressions + Spend (Recommended)**
- Use **impressions** for channels with r > 0.65 (Panneaux, Circulaire, Banniere, Social, Radio)
- Use **spend** for channels with low r (Preroll) or incomplete data (TV)
- Model structure:
  ```
  Revenue ~ Fourier + Weather + adstock(spend) + adstock(impressions) + saturation_terms
  ```
- Interpretation:
  - Spend coefficient = "value of $1 negotiation margin"
  - Impressions coefficient = "value of 1M delivered impressions"
  - Both in same unit of analysis (month)

**Option 2: Impressions Only (Risky)**
- Pros: Cleaner interpretation (media delivery, not cost)
- Cons:
  - Only 52/36 months have data (sample mismatch)
  - Loses information about cost-side optimization (e.g., Q1 low cost-per-impression)
  - Model would have sparse feature matrix for TV/Preroll

**Option 3: Cost-per-Impression (CPM) Instead of Spend**
- Transform spend into **implied impressions** via month-level CPM
- Better than spend alone if CPM varies significantly
- **Data supports this**: CPM varies 50% month-to-month for radio

---

## 7. Implementation Roadmap

### **Phase 1: Quick Wins (1–2 hours)**
1. **Aggregate impressions by channel, month** from `tableau_medias_performance.csv`
   - Output: `impressions_monthly_aggregated.csv` (36 rows × 7 channels)
   - Add to `sales_spend_weather.csv` as 7 new columns

2. **Calculate CPM index** (CPM / channel_median)
   - Output: `cpm_index_monthly.csv`
   - Add as 7 new columns

3. **Rerun NB06c with new features**
   - Compare model R² with vs. without impressions
   - Check coefficients stability

### **Phase 2: Engagement Diagnostics (2–3 hours)**
4. **Add CPC by digital channel** (4 columns)
5. **Add CTR by digital channel** (4 columns)
6. **Run LOOCV robustness checks** with new features

### **Phase 3: Strategic Analysis (Optional, 2–4 hours)**
7. **Decompose traditional media** using GRP → impressions conversion
8. **Create media mix composition index** (traditional vs. digital %)
9. **Interaction terms**: spend × impressions × CPM (synergy effects)

---

## 8. Specific SQL/Python Recipe for Feature Engineering

### **Create Monthly Impressions Dataset**
```python
import pandas as pd

# Load tableau_medias_performance
tableau = pd.read_csv('data/processed/tableau_medias_performance.csv')

# Clean and aggregate
tableau_clean = tableau.dropna(subset=['channel_group', 'year', 'month', 'impressions_reel'])
tableau_clean = tableau_clean[tableau_clean['impressions_reel'] > 0]

# Create fiscal year
tableau_clean['fiscal_year'] = tableau_clean.apply(
    lambda x: x['year'] if x['month'] >= 11 else x['year'], axis=1
)

# Aggregate to monthly
impressions_monthly = tableau_clean.groupby(
    ['fiscal_year', 'month', 'channel_group']
)['impressions_reel'].sum().reset_index()

# Pivot to wide format
impressions_wide = impressions_monthly.pivot_table(
    index=['fiscal_year', 'month'],
    columns='channel_group',
    values='impressions_reel',
    aggfunc='sum'
).fillna(0)

# Rename columns
impressions_wide.columns = [f'impr_{col.lower()}' for col in impressions_wide.columns]

# Merge with sales_spend_weather
spend_weather = pd.read_csv('data/processed/sales_spend_weather.csv')
enriched = spend_weather.merge(
    impressions_wide,
    left_on=['year', 'month_num'],
    right_index=True,
    how='left'
)
```

---

## 9. Files & References

### Source Files
- **Raw**: `/sessions/clever-peaceful-edison/mnt/busa693-clubpiscine/data/raw/Recap_Tableau_Medias_2025.xlsx`
- **Processed**: `/sessions/clever-peaceful-edison/mnt/busa693-clubpiscine/data/processed/tableau_medias_performance.csv` (383 rows, 16 columns)
- **Current Model Data**: `sales_spend_weather.csv` (36 rows, 43 columns)

### Notebooks
- **NB05**: Feature engineering (adstock, saturation)
- **NB06c**: Base MMM model (Ridge regression, ROAS)
- **NB07**: Budget optimization (future work)

### Output Deliverables (Recommended)
1. `impressions_monthly_enriched.csv` — new impressions feature set
2. `cpm_index_monthly.csv` — cost efficiency indices
3. `mmm_enriched_model_results.csv` — NB06c rerun with new features
4. `feature_comparison_report.csv` — R² and coefficient changes

---

## 10. Summary Table: Recommended Features for Implementation

| Feature Name | Data Source | Channels | Months | Priority | Expected ROI |
|---|---|---|---|---|---|
| **impr_banniere_web** through **impr_television** | Tableau Medias | 7 | 52 available | **HIGH** | Separate volume from cost; improve spend efficiency attribution |
| **cpc_banniere_web** through **cpc_circulaire_digitale** | Tableau Medias clicks | 4 (digital) | 36 | **HIGH** | Engagement quality proxy; diagnose creative issues |
| **cpm_index_[channel]** | Tableau Medias CPM | 7 | 36+ | **MEDIUM** | Cost negotiation visibility; seasonal rate changes |
| **ctr_[digital_channels]** | Tableau Medias | 4 (digital) | 36 | **MEDIUM** | Diagnostic only; not primary driver |
| **pct_traditional_media** | Budget data | 1 aggregate | 36 | **MEDIUM** | Capture media mix evolution constraint |

---

## Conclusion

**The model is leaving significant value on the table.** The `Recap_Tableau_Medias_2025.xlsx` file contains **52 monthly impressions observations, 756K clicks, and rich GRP data** that directly measure media delivery independent of spend. Adding impressions as a feature would:

1. **Improve attribution**: Separate media volume (impressions) from media cost (spend)
2. **Reduce confounding**: Rate negotiations, seasonal discounts, and bundle deals are now visible
3. **Enable diagnostics**: CPC and CTR reveal engagement quality
4. **Strengthen recommendations**: Budget optimization can trade spend for impressions (e.g., "negotiate better rates in Q3 to deliver 30% more impressions at same cost")

**Recommended first step**: Implement Phase 1 (impressions + CPM index aggregation) and rerun NB06c to quantify impact.

