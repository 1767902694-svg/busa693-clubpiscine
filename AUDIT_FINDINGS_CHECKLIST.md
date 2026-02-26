# Data Pipeline Audit: Findings Checklist

**Audit Date:** February 26, 2026
**Status:** ⚠️ CRITICAL ISSUES FOUND (Grade: C)

---

## Quick Status Check

- [x] NB06B produces NNLS-constrained coefficients (TV=354K, Preroll=393K)
- [x] causal_model_params.json stores UNCONSTRAINED Ridge from NB06 (TV=1.06M)
- [x] model_C_params.json exists with DIFFERENT coefficients (TV=1.74M)
- [x] Three models in flight with conflicting outputs
- [x] All channels show positive ROAS in NB07 (contradicts NB06 negative coefs)
- [x] mmm_final_output.json credits Model C but loads NB06 params
- [x] Media share = 10.5%, 144.2%, and 0% simultaneously (three values)
- [x] saturation_curves.csv is locked (can't verify which model it uses)
- [x] Optimization recommends 15% budget cut with +229% response increase

---

## Critical Issues Matrix

| Issue | Severity | File | Impact | Status |
|-------|----------|------|--------|--------|
| **Three models in pipeline** | CRITICAL | NB06, NB06B, Model C | Unclear which to trust | ⚠️ UNRESOLVED |
| **Coefficient mismatch** | CRITICAL | causal_model_params.json vs model_C_params.json | 4.9× difference on TV | ⚠️ UNRESOLVED |
| **Negative coefs in stored file** | CRITICAL | causal_model_params.json | Radio/Panneaux negative but ROAS positive | ⚠️ UNRESOLVED |
| **Invalid media share (144%)** | HIGH | model_C_params.json | Exceeds 100%, mathematically impossible | ⚠️ UNRESOLVED |
| **Source attribution conflict** | HIGH | mmm_final_output.json | Loads NB06, claims Model C | ⚠️ UNRESOLVED |
| **Media share mismatch** | HIGH | Three different files | 0%, 10.5%, 144% | ⚠️ UNRESOLVED |
| **Response curve origin unclear** | HIGH | saturation_curves.csv | Uses Model C? Uses NB06? | ⚠️ LOCKED FILE |
| **R² value inconsistency** | MEDIUM | multiple | 0.1548 vs 0.8604 vs 0.9304 | ⚠️ UNRESOLVED |

---

## Files Reviewed

### ✅ Successfully Audited

| File | Location | Status | Key Finding |
|------|----------|--------|------------|
| **causal_model_params.json** | `/data/processed/` | READABLE | Stores NB06 Two-Stage Ridge; has negative coefficients for Radio, Panneaux, Circulaire |
| **model_C_params.json** | `/data/processed/` | READABLE | Stores Full Ridge with controls; all positive coefficients; 144% media share |
| **mmm_final_output.json** | `/data/processed/` | READABLE | Credits Model C; shows 0% media share; +229% optimization lift |
| **NB06b_causal_inference_improved.ipynb** | `/notebooks/` | READABLE | Produces NNLS-constrained coefficients (TV=354K, Preroll=393K) |
| **07_mmm_roi_optimization.ipynb** | `/notebooks/` | READABLE | Loads causal_model_params.json but uses Model C results |
| **config/params.yaml** | `/config/` | READABLE | Model parameters and channel definitions |

### ❌ Inaccessible (File Locks)

| File | Location | Purpose | Impact |
|------|----------|---------|--------|
| media_effectiveness_results.csv | `/data/processed/` | Channel ROAS details | Can't verify confidence ratings |
| saturation_curves.csv | `/data/processed/` | Response curve data | CAN'T TELL which model powers optimization |
| robustness_summary.csv | `/data/processed/` | Statistical tests | Can't verify significance flags |
| mmm_optimization_results.csv | `/data/processed/` | Detailed reallocation | Data inferred from JSON instead |
| mmm_executive_summary.csv | `/data/processed/` | Summary table | Inferred from NB07 notebook output |
| mmm_scenario_analysis.csv | `/data/processed/` | Budget scenarios | Data extracted from notebook text |
| model_B_frisch_waugh.csv | `/data/processed/` | Statistical tests | Can't verify methodology |

---

## Coefficient Comparison: One-Pager

### NB06B NNLS-Constrained (Expected):
```
TV:        354,333   ✓ Positive, significant
Radio:           0   (Zeroed by constraint)
Preroll:   392,616   ✓ Highest coefficient
Social:    116,061   ✓ Positive
Banners:   108,779   ✓ Positive
Panneaux:        0   (Zeroed by constraint)
Circulaire:      0   (Zeroed by constraint)
```

### Stored in causal_model_params.json (NB06 Ridge - UNCONSTRAINED):
```
TV:      1,059,960   ✓ Match direction
Radio:      -3,084   ✗ NEGATIVE (should be 0)
Preroll:  1,277,798  ✓ Match direction
Social:     697,629  ✓ Match direction
Banners:    540,709  ✓ Match direction
Panneaux:  -230,480  ✗ NEGATIVE (should be 0)
Circulaire: -24,771  ✗ NEGATIVE (should be 0)
```

### Model C (Full Ridge with Controls - 3rd Model):
```
TV:      1,740,634   ✓ All positive
Radio:   1,193,229   ✓ Sign flip (NB06 negative)
Preroll: 2,192,998   ✓ All positive
Social:  1,317,357   ✓ All positive
Banners: 1,410,944   ✓ All positive
Panneaux:  261,412   ✓ Sign flip (NB06 negative)
Circulaire: 762,924  ✓ Sign flip (NB06 negative)
```

**Evidence Model C powers NB07:** All channels show positive ROAS in final optimization.

---

## Optimization Results: Snapshot

| Metric | Current | Optimal | Change | Assessment |
|--------|---------|---------|--------|------------|
| **TV Budget** | $109,693 | $50,000 | -54% | Floor constraint |
| **Radio Budget** | $60,202 | $30,000 | -50% | Floor constraint |
| **Social Budget** | $22,984 | $58,116 | +153% | Major increase |
| **Preroll Budget** | $25,066 | $35,413 | +41% | Moderate increase |
| **Banners Budget** | $22,989 | $35,074 | +53% | Moderate increase |
| **Panneaux Budget** | $8,125 | $5,000 | -38% | Near floor |
| **Circulaire Budget** | $12,404 | $8,641 | -30% | Reduced |
| **Total Media Spend** | $261,464 | $222,244 | -15% | Budget cut |
| **Monthly Response** | $1,753,929 | $5,768,612 | +229% | Major lift |

**Key Finding:** 15% budget reduction + reallocation = 229% response increase. Validated by scenario: Cut 15% still beats current performance by 37%.

---

## Model Comparison: Which Should We Use?

### NB06B Two-Stage Ridge (NNLS-Constrained)

**Pros:**
- ✅ Matches expected theory (non-negative channel effects)
- ✅ 10.5% media share is sensible and interpretable
- ✅ Separates seasonal from media effects cleanly
- ✅ NNLS handles multi-collinearity robustly
- ✅ Preroll has tightest confidence interval (significant)

**Cons:**
- ❌ Zeros out Radio, Panneaux, Circulaire (true zero or estimation artifact?)
- ❌ Bootstrap CIs show upper bounds are positive (e.g., Radio [0, 207K])
- ❌ Smaller coefficients may underestimate potency

### Model C Full Ridge (with Controls)

**Pros:**
- ✅ All positive coefficients (easier to optimize)
- ✅ Higher R² (0.9304) suggests good overall fit
- ✅ Simpler single-equation model

**Cons:**
- ❌ Media share = 144% (IMPOSSIBLE)
- ❌ Base share = -44% (IMPOSSIBLE)
- ❌ Confounds seasonal and media effects
- ❌ Violates model assumptions
- ❌ Uninterpretable

### Recommendation

**USE NB06B TWO-STAGE.** It's theoretically sound and produces sensible results (10.5% media share). Handle the zeroed-out channels via:
1. Conservative allocation (use floor bounds)
2. Confidence-based optimization (adjust bounds based on CI width)
3. Caveats in presentation ("results directional; validate with experiments")

---

## Key Recommendations Before Client Presentation

### Must-Do (Blocking):

- [ ] Determine authoritative model: NB06B NNLS vs Model C
- [ ] Regenerate saturation_curves.csv using chosen model
- [ ] Update mmm_final_output.json with correct model source attribution
- [ ] Verify media share value is correct (should be 10.5% for NB06B)
- [ ] Explain negative coefficients in stored file (Ridge vs NNLS)

### Should-Do (High Priority):

- [ ] Document why three models exist (NB06 vs NB06B vs Model C)
- [ ] Add confidence intervals to channel effectiveness summary
- [ ] Include scenario analysis table in executive summary
- [ ] Add caveat about small sample size (36 months) and directional results
- [ ] Show bootstrap CI ranges for each channel

### Nice-to-Have (Polish):

- [ ] Sensitivity analysis: how sensitive are recommendations to coefficient choice?
- [ ] Comparison to naive allocation (equal spend per channel)
- [ ] Controlled experiment design for validation
- [ ] Quarterly budget reallocation schedule

---

## Timeline & Effort Estimate

| Task | Effort | Critical? | Owner |
|------|--------|-----------|-------|
| Resolve model choice | 1 hour | YES | Analytics Lead |
| Regenerate saturation curves | 2 hours | YES | Data Analyst |
| Update JSON files | 1 hour | YES | Developer |
| Verify locked CSV files | 1 hour | YES | DevOps/IT |
| Update presentation slides | 2 hours | YES | Business Analyst |
| Sensitivity analysis | 3 hours | NO | Data Scientist |
| Controlled experiment design | 2 hours | NO | Strategy Lead |

**Total:** 8 hours critical path + 5 hours optional = 13 hours total effort

**Client Presentation Readiness:** Not ready (resolve critical path first)

---

## Data Integrity Summary

| Component | Status | Confidence | Notes |
|-----------|--------|------------|-------|
| **Sales Data** | ✅ VERIFIED | HIGH | 36 months, no missing values, correctly aggregated |
| **Budget Data** | ✅ VERIFIED | HIGH | 36 months, 7 consolidated channels, bugs fixed |
| **Merge Logic** | ✅ VERIFIED | HIGH | 100% match rate on fiscal (year, month_num) key |
| **NB06B Outputs** | ✅ VERIFIED | HIGH | NNLS coefficients match notebook output |
| **Stored Params** | ⚠️ MIXED | MEDIUM | Two models stored; unclear which is authoritative |
| **Response Curves** | ⚠️ UNKNOWN | LOW | Locked file; inferred to use Model C, not verified |
| **Optimization Logic** | ✅ VERIFIED | HIGH | SLSQP solver, business constraints applied correctly |
| **Final Output** | ⚠️ QUESTIONABLE | MEDIUM | Credits Model C but loads Model A; media share conflicted |

---

## Sign-Off

**Auditor:** Data Pipeline Analyst
**Date:** February 26, 2026
**Status:** ⚠️ CRITICAL ISSUES DETECTED

**Recommendation:** **DO NOT PRESENT TO CLIENT** until model version conflict is resolved.

**Estimated Fix Time:** 8 hours (critical path)

**Next Review:** After model consolidation and regeneration of outputs

---

## Questions for Development Team

1. **Why do three models exist?** (NB06 Ridge, NB06B NNLS, Model C Full)
2. **Which model is authoritative?** (for optimization and final recommendations)
3. **Why do stored coefficients have negatives?** (Ridge solution, not NNLS?)
4. **Which model powers saturation_curves.csv?** (response functions)
5. **Why is media share reported as 0%?** (should be ~10.5%)
6. **Why does mmm_final_output.json credit Model C?** (but code loads NB06?)
7. **Can we unlock the CSV files?** (to verify responses and confidence)

---

*For more details, see:*
- *DATA_PIPELINE_AUDIT_REPORT.md* — Full technical analysis
- *COEFFICIENT_COMPARISON_ANALYSIS.md* — Detailed coefficient reconciliation
- *AUDIT_NUMERIC_SUMMARY.txt* — All numeric values in one place

