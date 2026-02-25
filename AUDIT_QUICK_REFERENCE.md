# Club Piscine MMM Data Audit - Quick Reference Checklist

**Status:** PASSED (Grade: A)
**Date:** February 25, 2026

---

## Data Pipeline Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Raw Sales Data** | ✓ PASS | 6,336 weekly → 36 monthly |
| **Budget Files (3)** | ✓ PASS | Cleaned, consolidated, 7 groups |
| **Merge Logic** | ✓ PASS | 36/36 match on (year, month_num) |
| **Missing Values** | ✓ PASS | 0 in final dataset (100% complete) |
| **Bug Fixes** | ✓ PASS | July duplication + Google double-counting |
| **Channel Consolidation** | ✓ PASS | 7 groups, no double-counting verified |
| **Fiscal Year Alignment** | ✓ PASS | FY starts Nov 1, calendar months mapped correctly |

---

## Critical Bugs: Status

### 1. "Juillet" (July) Duplicate Month Columns
- **Severity:** CRITICAL
- **Status:** ✓ FIXED
- **Location:** NB02, cell `budget-cleaning`
- **Solution:** Code uses LAST matching column (overwrites previous)
- **Verification:** July spend non-zero in all 3 years ($280K + $233K + $257K)

### 2. Google Double-Counting & Shopping Contamination
- **Severity:** CRITICAL
- **Status:** ✓ FIXED
- **Location:** NB02, cell `budget-cleaning`
- **Solution:**
  - Parent "GOOGLE" row skipped
  - Sub-rows mapped: Video→Preroll, Display→Banniere_Web
  - Google Shopping explicitly excluded
  - Search spend excluded
- **Verification:** No double-counting; sum of 7 channels = spend_total ✓

---

## Data Quality Metrics

### Sales Data (6,336 weekly rows)
```
Completeness:    99.995% (5 NaN out of 101,376 cells)
Fiscal years:    3 (FY2023, FY2024, FY2025)
Stores:          42 (CP01-CP42, missing CP09)
Date span:       Oct 31, 2022 → Oct 27, 2025
Categories:      6 (HT, CR, SP, ME&GA, FI, BQ)
Revenue:         $512.4M total
```

### Budget Data (36 monthly rows)
```
Completeness:    100% (0 missing values)
Fiscal years:    3 (FY2023, FY2024, FY2025)
Months/year:     12 each
Channels:        7 consolidated groups
Spend:           $9.4M total
Exclusions:      Google Shopping, Search, Programmatic, Audio, Postal (~$900K)
```

### Merged Dataset (36 rows × 25 columns)
```
Completeness:    100% (0 missing values)
Rows:            36 (12 × 3 fiscal years)
Columns:         25 (16 sales + 8 spend + 1 date)
Merge key:       (year, month_num)
Match rate:      100% (36/36)
```

---

## 7-Channel Groups: Summary

| # | Channel | Spend | % | Key Raw Sources |
|---|---------|-------|---|-----------------|
| 1 | Television | $3.9M | 42% | TELEVISION |
| 2 | Radio | $2.2M | 23% | RADIO + RADIO NUMÉRIQUE |
| 3 | Preroll | $0.9M | 10% | PREROLL PREMIUM + YOUTUBE |
| 4 | Banniere_Web | $0.8M | 9% | GOOGLE DISPLAY + LAPRESSE + BANNIÈRES |
| 5 | Social_Media | $0.8M | 9% | FACEBOOK + INSTAGRAM + PINTEREST + TIKTOK |
| 6 | Circulaire_Digitale | $0.4M | 5% | CIRCULAIRE DIGITAL/DIGITALE |
| 7 | Panneaux | $0.3M | 3% | PANNEAUX + AFFICHAGES NUMÉRIQUES |

**Double-Counting Check:** ✓ PASS (Sum = Spend Total)

---

## Merge Validation

### Key Match on (year, month_num)
```
Sales data:   36 unique pairs → FY2023(1-12), FY2024(1-12), FY2025(1-12)
Budget wide:  36 unique pairs → FY2023(1-12), FY2024(1-12), FY2025(1-12)
Merge type:   INNER
Result:       36/36 rows matched (100%)
```

### Fiscal Year Logic
```
November (month_num=11):
  Calendar Nov 2022 → FY2023 (fiscal Nov)
  Calendar Nov 2023 → FY2024 (fiscal Nov)
  Calendar Nov 2024 → FY2025 (fiscal Nov)

December (month_num=12):
  Calendar Dec 2022 → FY2023 (fiscal Dec)
  Calendar Dec 2023 → FY2024 (fiscal Dec)
  Calendar Dec 2024 → FY2025 (fiscal Dec)

January-October (month_num=1-10):
  Calendar Jan-Oct 2023 → FY2023 (fiscal Jan-Oct)
  Calendar Jan-Oct 2024 → FY2024 (fiscal Jan-Oct)
  Calendar Jan-Oct 2025 → FY2025 (fiscal Jan-Oct)
```
✓ CORRECT

---

## Known Limitations (Documented)

| Issue | Severity | Mitigation | Status |
|-------|----------|-----------|--------|
| High sparsity in specialty categories (CR 83.5%) | Minor | Monthly aggregation dampens noise | Acceptable |
| Provincial weather (single point, not regional) | Minor | Acknowledged in CLAUDE.md | Trade-off |
| Small sample size (36 obs, 14+ params) | Warning | Ridge + LOOCV + bootstrap | Mitigated |
| Tableau Medias dates (1970 anomaly) | Minor | Not used in primary MMM | Separate issue |

---

## Files Generated

1. **AUDIT_REPORT.md** (Main report)
   - Comprehensive findings across 14 sections
   - Issue severity classification
   - Grade justification

2. **AUDIT_DETAILED_FINDINGS.md** (Technical deep-dive)
   - Data aggregation logic
   - Budget consolidation methodology
   - Bug analysis & fix verification
   - Schema validation

3. **AUDIT_EXECUTIVE_SUMMARY.txt** (One-page summary)
   - Key statistics
   - Critical findings
   - Verification checklist
   - Grade summary

4. **AUDIT_QUICK_REFERENCE.md** (This file)
   - Quick lookup for pass/fail status
   - Data quality metrics
   - Channel summary

---

## Sign-Off

**Overall Grade:** A (Production-Ready)

**Recommendation:** ✓ Proceed to NB03 (EDA)

**Next Phase:** Feature engineering (NB05), modeling (NB06-08)

**Audit Date:** February 25, 2026
**Auditor:** Senior Data Engineer

---

## Quick Checklist (For Model Development Team)

- [x] Sales data aggregated correctly (6,336 → 36)
- [x] Budget consolidation verified (no double-counting)
- [x] "Juillet" bug fixed
- [x] Google double-counting bug fixed
- [x] 36-month merged dataset complete (0 missing values)
- [x] Fiscal year alignment correct
- [x] 7-channel groups properly mapped
- [x] Ready for modeling

**GREEN LIGHT: All systems ready for production** ✓

