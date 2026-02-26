# Club Piscine MMM: Data Pipeline Audit Report (NB06/NB06B → NB07)

**Audit Date:** February 26, 2026
**Auditor:** Data Pipeline Analyst
**Status:** CRITICAL INCONSISTENCY DETECTED
**Grade:** C (Multiple version conflicts require clarification)

---

## Executive Summary

The Club Piscine MMM project has **THREE DIFFERENT MODELS** in flight, each producing different coefficients and recommendations:

1. **NB06 (Two-Stage Ridge)** — Original causal inference model
2. **NB06B (Two-Stage Ridge Improved)** — Refined version with NNLS bootstrap
3. **NB07 (Budget Optimization)** — Loads from both, but defaults to Model C (unconstrained Ridge)

**Critical Issue:** The data pipeline shows **coefficient mismatches** between NB06B's direct output and what is stored in the saved parameter files. Additionally, NB07's optimization uses **Model C (a third independent Ridge model)** rather than NB06B's coefficients directly.

---

## 1. EXPECTED vs ACTUAL COEFFICIENTS

### 1.1 NB06B Coefficients (From Notebook Output)

Per the NB06B notebook cell output (Bootstrap 90% CI section):

| Channel | NB06B Coefficient | CI (90%) | Notes |
|---------|------------------|----------|-------|
| **television** | 354,333 | [82,025, 568,346] | Positive, significant CI |
| **radio** | 0 | [0, 207,512] | Zero by NNLS constraint |
| **panneaux** | 0 | [0, 161,850] | Zero by NNLS constraint |
| **social_media** | 116,061 | [0, 349,621] | Positive |
| **preroll** | 392,616 | [203,830, 543,347] | **HIGHEST**, tightest CI |
| **banniere_web** | 108,779 | [0, 290,246] | Positive |
| **circulaire_digitale** | 0 | [0, 226,184] | Zero by NNLS constraint |

**Source:** NB06B notebook output, cell "Bootstrap done (1,000 resamples...)"

---

### 1.2 Coefficients Stored in `causal_model_params.json`

**File:** `/data/processed/causal_model_params.json`

This file stores the **Two-Stage Ridge model** (NB06) parameters:

#### Stage 2 Coefficients (Standardized Scale):
| Channel | Coefficient |
|---------|------------|
| television_saturated | 357,026.87 |
| radio_saturated | **-976.26** (NEGATIVE) |
| panneaux_saturated | **-100,167.26** (NEGATIVE) |
| social_media_saturated | 121,553.23 |
| preroll_saturated | 400,323.42 |
| banniere_web_saturated | 119,843.31 |
| circulaire_digitale_saturated | **-8,252.57** (NEGATIVE) |

#### Stage 2 Coefficients (Original Scale):
| Channel | Coefficient |
|---------|------------|
| television_saturated | 1,059,960.34 |
| radio_saturated | **-3,084.26** (NEGATIVE) |
| panneaux_saturated | **-230,479.61** (NEGATIVE) |
| social_media_saturated | 697,629.23 |
| preroll_saturated | 1,277,797.77 |
| banniere_web_saturated | 540,708.85 |
| circulaire_digitale_saturated | **-24,771.09** (NEGATIVE) |

**Critical Finding:** The stored coefficients in the JSON show **NEGATIVE coefficients for Radio, Panneaux, and Circulaire_Digitale** in the saturated (Hill-transformed) space. This is the **unconstrained Ridge solution**, NOT the NNLS-constrained version from NB06B.

**Model Metadata in JSON:**
- `model_type`: "two_stage_ridge"
- `media_share_pct`: 10.5045% ✓ (matches narrative)
- `Ridge R² (Total Revenue)`: 0.8604
- `Ridge R² S1 (Seasonal)`: 0.8348
- `Ridge R² S2 (Media on residuals)`: 0.1548

---

### 1.3 Coefficients Stored in `model_C_params.json`

**File:** `/data/processed/model_C_params.json`

This file stores a **DIFFERENT model**: a full Ridge with controls (not two-stage), producing very different coefficients:

| Channel | Model C Coefficient | Notes |
|---------|-------------------|-------|
| television_saturated | **1,740,633.80** | 4.9x higher than NB06 |
| radio_saturated | **1,193,228.90** | POSITIVE (vs negative in NB06) |
| panneaux_saturated | **261,412.23** | POSITIVE (vs negative in NB06) |
| social_media_saturated | 1,317,356.66 | 6.0x higher than NB06 |
| preroll_saturated | 2,192,998.40 | 1.7x higher than NB06 |
| banniere_web_saturated | 1,410,943.56 | 2.6x higher than NB06 |
| circulaire_digitale_saturated | **762,923.67** | POSITIVE (vs negative in NB06) |

**Model C Metadata:**
- Model type: Unconstrained Ridge with seasonal controls (NOT two-stage)
- R² (in-sample): 0.9304 ✓ (matches mmm_final_output)
- Media share: **144.26%** (IMPLAUSIBLE — more than 100% of revenue from media)
- Base (seasonal) share: **-44.26%** (IMPLAUSIBLE — negative baseline)
- Frisch-Waugh significant channels: [television, preroll, banniere_web]

**Critical Finding:** Model C is a **full model with controls included in the same equation**, which inflates coefficients by attempting to absorb seasonal effects + media effects simultaneously. This violates the two-stage design and produces an **uninterpretable 144% media share**.

---

## 2. WHAT NB07 LOADS AND USES

**NB07 Loading Sequence:**

```python
# Cell: "Load NB06 outputs"
eff_df = pd.read_csv(processed_path / 'media_effectiveness_results.csv')
sat_curves_df = pd.read_csv(processed_path / 'saturation_curves.csv')
with open(processed_path / 'causal_model_params.json') as f:
    model_params = json.load(f)  # ← Loads NB06 Two-Stage params
robust_df = pd.read_csv(processed_path / 'robustness_summary.csv')
df = pd.read_csv(processed_path / 'sales_spend_weather.csv')
```

**What it displays in Executive Summary:**
- R²: 0.930 (**NOT from causal_model_params.json**, which stores 0.8604)
- Media share: 0.0% (literally `5.554820791533802e-15`, approximately zero)
- Lift: +228.9%
- **Source comment in mmm_final_output.json:** "NB07 (Model C constrained Ridge)"

**Critical Issue:** NB07's mmm_final_output.json **explicitly credits Model C**, not the Two-Stage Ridge from NB06/NB06B. But the notebook code shows it loading `causal_model_params.json` (which contains NB06 two-stage parameters).

---

## 3. MODEL COMPARISON MATRIX

| Aspect | NB06 (Two-Stage Ridge) | NB06B (NNLS Bootstrap) | Model C (Full Ridge) | NB07 Output |
|--------|----------------------|----------------------|----------------------|-----------|
| **Approach** | Ridge on Stage 2 residuals | NNLS-constrained bootstrap | Ridge with all features | Loads NB06, displays Model C |
| **TV Coef** | 1,059,960 (orig scale) | 354,333 (direct) | 1,740,634 | N/A (uses curves) |
| **Radio Coef** | -3,084 (NEGATIVE) | 0 (NNLS zero) | 1,193,229 (POSITIVE) | Uses response curves |
| **Preroll Coef** | 1,277,798 (orig scale) | 392,616 (direct) | 2,192,998 | Uses response curves |
| **R²** | 0.8604 | Not stored | 0.9304 | 0.9304 |
| **Media Share** | 10.5% | ~10% (implied) | 144.2% (INVALID) | 0.0% (practically zero) |
| **Significant Channels** | All except those NNLS-zeroed | TV, Preroll mostly | TV, Preroll, Banners | Uses confidence ratings |

---

## 4. RESPONSE CURVES: HOW ARE THEY BUILT?

**File:** `/data/processed/saturation_curves.csv`

NB07 builds optimization using **interpolated response curves** from saturation_curves.csv. These curves are:
1. Derived from the Ridge coefficients (which model?)
2. Transformed through Hill saturation functions
3. Used to create piecewise cubic interpolations

**Key Question:** Which model produced `saturation_curves.csv`?
- **If NB06:** The negative coefficients (Radio, Panneaux, Circulaire) will produce **downward-sloping response curves**, causing the optimizer to hold these channels at minimum bounds.
- **If Model C:** The positive coefficients will produce **upward-sloping response curves**, allowing these channels to scale.

**Observed Behavior in NB07 Output:**
```
ROAS values:
  Social Media:      157.8x (HIGH)
  Preroll:           119.8x (HIGH)
  Web Banners:       128.2x (HIGH)
  Panneaux:           36.2x (MEDIUM)  ← Positive, but held low
  Radio:              23.8x (HIGH)     ← Positive, but held low
  Television:         16.0x (HIGH)
  Digital Flyers:     76.8x (HIGH)
```

**Inference:** The response curves show **positive ROAS for all channels**, suggesting they came from **Model C (full Ridge), not NB06 (which has negative coefs for Radio, Panneaux, Circulaire).**

---

## 5. OPTIMIZATION RESULTS: CURRENT STATE

### mmm_final_output.json (Authoritative Output)

**Source:** NB07, cell "SAVE OUTPUTS"

```json
{
  "source": "NB07 (Model C constrained Ridge)",
  "created": "2026-02-24 23:54",
  "model_performance": {
    "r2_model_C": 0.9304113874435695,
    "r2_cv_model_A": 0.8855423562737514,
    "media_share_pct": 5.554820791533802e-15
  },
  "optimization": {
    "current_response": 1753928.7103872206,
    "optimal_response": 5768612.456373521,
    "lift_pct": 228.89663201305174,
    "current_allocation": {
      "television": 109693.09,
      "radio": 60202.13,
      "panneaux": 8124.86,
      "social_media": 22983.91,
      "preroll": 25066.48,
      "banniere_web": 22989.09,
      "circulaire_digitale": 12404.05
    },
    "optimal_allocation": {
      "television": 50000.0,
      "radio": 30000.0,
      "panneaux": 5000.0,
      "social_media": 58116.09,
      "preroll": 35413.39,
      "banniere_web": 35073.76,
      "circulaire_digitale": 8640.82
    }
  }
}
```

**Monthly Budget Change:** $261,464 → $222,244 (-15%)
**Monthly Response Lift:** $1.75M → $5.77M (+229%)

---

## 6. CRITICAL INCONSISTENCIES IDENTIFIED

### 6.1 Model Version Confusion
- **Issue:** NB07 loads from `causal_model_params.json` (Two-Stage Ridge) but outputs reference Model C (Full Ridge).
- **Impact:** Unclear which coefficients the response curves actually use.
- **Severity:** CRITICAL

### 6.2 Negative Coefficients in NB06
- **Issue:** `causal_model_params.json` shows negative coefficients for Radio (-3,084), Panneaux (-230,480), and Circulaire (-24,771) in original scale.
- **Expected:** NB06B applies NNLS constraint, zeroing these out.
- **Stored:** The unconstrained Ridge solution, which includes negatives.
- **Impact:** Response curves will be downward-sloping for these channels.
- **Severity:** CRITICAL

### 6.3 Media Share Discrepancy
- **NB06/causal_model_params.json:** 10.5% (correct, sensible)
- **Model C params:** 144.2% (implausible, violates model assumptions)
- **mmm_final_output.json:** 5.5e-15 ≈ 0% (practically zero, masking the true attribution)
- **Severity:** HIGH

### 6.4 R² Value Conflict
- **causal_model_params.json (Stage 2 R²):** 0.1548 (media explains 15% of residuals)
- **causal_model_params.json (Full R²):** 0.8604 (full model fit)
- **mmm_final_output.json (reported):** 0.9304 (Model C, which includes controls)
- **Severity:** HIGH

### 6.5 Response Curves Origin Unclear
- **Observation:** All channels show positive ROAS in NB07.
- **Expected from NB06:** Radio, Panneaux, Circulaire should be negative or zero.
- **Inferred:** Curves are from Model C, not NB06.
- **Severity:** HIGH

---

## 7. DATA FILES AUDIT

### 7.1 Readable Files

✓ `causal_model_params.json` — Complete, stores Two-Stage Ridge
✓ `model_C_params.json` — Complete, stores Full Ridge with controls
✓ `mmm_final_output.json` — Complete, stores optimization results

### 7.2 Unreadable Files (Resource Deadlock)

✗ `media_effectiveness_results.csv` — Persistent file lock
✗ `saturation_curves.csv` — Persistent file lock
✗ `robustness_summary.csv` — Persistent file lock
✗ `mmm_optimization_results.csv` — Persistent file lock
✗ `mmm_executive_summary.csv` — Persistent file lock
✗ `mmm_scenario_analysis.csv` — Persistent file lock
✗ `model_B_frisch_waugh.csv` — Persistent file lock

**Note:** These files likely contain the intermediate results and scenario analysis. The lock prevents direct inspection but the JSON outputs provide key summary data.

---

## 8. VERIFICATION AGAINST NB06B EXPECTED OUTPUTS

| Expected (NB06B) | Actual (Stored) | Match? | Issue |
|------------------|-----------------|--------|-------|
| TV coef: 354,333 | causal_model_params: 1,059,960 | NO | Different scale/model |
| Radio coef: 0 | causal_model_params: -3,084 | NO | Unconstrained Ridge vs NNLS |
| Preroll coef: 392,616 | causal_model_params: 1,277,798 | NO | Different scale/model |
| Media share: ~10% | causal_model_params: 10.5% | YES ✓ | Correct |
| Significant channels (CI) | Not compared | UNKNOWN | Files locked |
| Bootstrap CIs | Not stored | UNKNOWN | Not persisted |

---

## 9. RECOMMENDATIONS

### Immediate Actions Required

1. **Clarify Model Selection**
   - [ ] Document whether NB07 should use NB06 Two-Stage Ridge or Model C Full Ridge
   - [ ] Update `mmm_final_output.json` source attribution to be unambiguous
   - [ ] Add model version comment to JSON files

2. **Resolve Coefficient Mismatch**
   - [ ] Verify which coefficients are actually used by saturation_curves.csv
   - [ ] If NB06 (negative coefs), regenerate curves with NNLS-constrained coefficients
   - [ ] If Model C, document why Full Ridge is preferred and update causal_model_params.json metadata

3. **Validate Response Curves**
   - [ ] Extract and verify saturation_curves.csv coefficients match the source model
   - [ ] Confirm all channels have sensible response functions (no unexpected inversions)

4. **Media Share Attribution**
   - [ ] Investigate why mmm_final_output.json shows 0% media share (should be 10.5%)
   - [ ] Update presentation to use correct 10.5% figure from causal_model_params

5. **Bootstrap Results**
   - [ ] Verify that 90% CIs from NB06B bootstrap are reflected in robustness_summary.csv
   - [ ] Ensure confidence ratings in NB07 match robustness results

### For Client Presentation

**Current Recommendation:** DO NOT PRESENT until above issues are resolved.

**Key Talking Points Once Fixed:**
- "The two-stage approach isolates seasonal demand (89.5% of revenue) from media effects (10.5%)"
- "Preroll and Televison are most statistically robust; Digital Flyers and Panneaux are high-ROAS but lower confidence"
- "Recommended reallocation would enable a 15% budget cut while maintaining or exceeding current performance"

---

## 10. FILES REVIEWED

### Notebooks
- ✓ `06b_causal_inference_improved.ipynb` — NB06B two-stage Ridge with NNLS bootstrap
- ✓ `07_mmm_roi_optimization.ipynb` — Budget optimization and scenario analysis

### Parameter Files
- ✓ `/data/processed/causal_model_params.json` — Two-Stage Ridge parameters (NB06)
- ✓ `/data/processed/model_C_params.json` — Full Ridge parameters (Model C)
- ✓ `/data/processed/mmm_final_output.json` — Final optimization summary

### CSV Files (Locked)
- ✗ `/data/processed/media_effectiveness_results.csv`
- ✗ `/data/processed/saturation_curves.csv`
- ✗ `/data/processed/robustness_summary.csv`
- ✗ `/data/processed/mmm_optimization_results.csv`
- ✗ `/data/processed/mmm_executive_summary.csv`
- ✗ `/data/processed/mmm_scenario_analysis.csv`
- ✗ `/data/processed/model_B_frisch_waugh.csv`

### Config
- ✓ `/config/params.yaml` — Model hyperparameters and channel definitions

---

## 11. CONCLUSION

The Club Piscine MMM data pipeline is **functional but contains model version conflicts** that must be resolved before client presentation.

**Key Findings:**
1. Three models are in flight: NB06 Two-Stage Ridge, NB06B NNLS-constrained, and Model C Full Ridge
2. NB07 loads NB06 parameters but appears to use Model C results in optimization
3. Negative coefficients in NB06 contradict the positive ROAS shown in NB07
4. Media share attribution varies wildly (0%, 10.5%, 144.2%) depending on which model is referenced
5. CSV files containing scenario analysis and confidence ratings are inaccessible due to file locks

**Audit Grade: C**
- Data quality: A (verified in prior AUDIT_QUICK_REFERENCE)
- Model implementation: C (inconsistent versions)
- Parameter documentation: D (conflicting files)
- Output clarity: D (mixed source attribution)

**Blocker Status:** YES — Resolve model version conflict before final sign-off.

---

**Audit Sign-Off:** Data pipeline requires clarification on model versions before client presentation.

**Next Steps:** Consolidate models (choose single reference model) and regenerate output files with consistent metadata.
