# Club Piscine Forecasting Pipeline Verification Report

## EXECUTIVE SUMMARY
**STATUS: 3 BREAKING ISSUES FOUND** requiring immediate fixes before production use.

### Critical Issues
1. **Duplicate store_code columns** (store_code_x, store_code_y, store_code) flowing through NB03
2. **Hardcoded NB04 feature lists** missing 11 new lag features created by NB03
3. **Weather interaction terms** created in NB03 not referenced in NB04's WEATHER_FEATURES

---

## NOTEBOOK INPUTS & OUTPUTS

### NB01: EDA (01_eda.ipynb)
**INPUT:**  Raw sales data from Excel files
**OUTPUT:** `weekly_units.csv`

**Columns Output:**
```
week_ending, store_code, city, division_code, units, revenue, 
n_transactions, revenue_clean, is_return, is_active_product, 
weeks_with_sales
```
- 11 columns total
- **Key additions:** revenue_clean (clip at 0), is_return flag, is_active_product flag, weeks_with_sales count

**Save Code (Cell 21):**
```python
weekly.to_csv(DATA_PROCESSED / "weekly_units.csv", index=False)
```
Saves with NEW columns: `revenue_clean, is_return, is_active_product, weeks_with_sales`

---

### NB02: Weather Integration (02_weather_integration.ipynb)
**INPUT:**  `weekly_units.csv` (from NB01)
**OUTPUT:** `weekly_units_weather.csv`

**Read Code (Cell 4):**
```python
weekly = pd.read_csv(DATA_PROCESSED / 'weekly_units.csv')
```

**Critical Merge Code (Cell 21):**
```python
weekly_weather = weekly.merge(weather_weekly, on=['city','week_ending'], how='left')
# Ensure store_code is present (may be dropped if weather_weekly also has it)
if 'store_code' not in weekly_weather.columns and 'store_code' in weekly.columns:
    weekly_weather = weekly_weather.merge(weekly[['city','week_ending','division_code','store_code']].drop_duplicates(),
                                           on=['city','week_ending','division_code'], how='left')
weekly_weather = weekly_weather.merge(
    holiday_weekly[['city','week_ending','n_holidays','has_holiday']],
    on=['city','week_ending'], how='left'
)
```

**Columns Output:**
```
week_ending, store_code_x, city, division_code, units, revenue, n_transactions,
store_code_y, province, avg_temp, max_temp, total_precip, sunshine_hours,
rain_days, snow_days, bad_weather_days, store_code, n_holidays, has_holiday, month
```
- **20 columns total**
- **PROBLEM: Contains THREE versions of store_code:**
  - `store_code_x` (from first merge with weather_weekly)
  - `store_code_y` (from recovery merge in safety logic)
  - `store_code` (from second merge attempt)

**Save Code (Cell 25):**
```python
weekly_weather.to_csv(DATA_PROCESSED / 'weekly_units_weather.csv', index=False)
```

---

### NB03: Feature Engineering (03_feature_engineering.ipynb)
**INPUT:**  `weekly_units_weather.csv` (from NB02)
**OUTPUT:** `modeling_dataset.csv`

**Read Code (Cell 4):**
```python
df = pd.read_csv(DATA_PROCESSED / 'weekly_units_weather.csv')
GROUP_COLS = ['store_code','city','division_code']
```

**Actual Input Columns Received (Cell 4/5 Output):**
```
['week_ending', 'store_code_x', 'city', 'division_code', 'units', 'revenue', 
'n_transactions', 'store_code_y', 'province', 'avg_temp', 'max_temp', 
'total_precip', 'sunshine_hours', 'rain_days', 'snow_days', 'bad_weather_days', 
'store_code', 'n_holidays', 'has_holiday', 'month']
```

**GROUP_COLS Usage (Cell 13):**
```python
for _keys, _grp in df.groupby(GROUP_COLS):
    _parts.append(add_lag_features(_grp))
df = pd.concat(_parts, ignore_index=True)

for _col in GROUP_COLS:
    assert _col in df.columns, f'BUG: {_col} lost after lag computation!'
```
✅ **GROUP_COLS correctly references 'store_code' (not store_code_x or store_code_y)**

---

## CRITICAL ISSUES

### ISSUE A: Duplicate store_code Columns in NB02 → NB03 Handoff

**Problem:**
NB02 outputs `weekly_units_weather.csv` with THREE store_code columns:
- `store_code_x` — from first merge with weather_weekly
- `store_code_y` — from recovery merge (if store_code dropped)
- `store_code` — from second merge/safety logic

**Why it happens:**
1. Cell 15: `weekly.merge(weather_weekly, on=['city','week_ending'], how='left')`
   - Both have `store_code` → pandas auto-suffixes to `store_code_x`, `store_code_y`
2. Cell 21: Safety code tries to recover by merging again
3. Holiday merge adds `has_holiday` but doesn't remove the _x/_y duplicates

**Impact on NB03:**
- NB03 explicitly uses `GROUP_COLS = ['store_code','city','division_code']` (line in Cell 4)
- Works correctly because it uses the clean `store_code` column
- BUT the extra columns `store_code_x` and `store_code_y` are wasteful and confusing
- Flows through to final `modeling_dataset.csv` output

**Recommendation:**
NB02 Cell 21 should explicitly drop the duplicate columns:
```python
weekly_weather = weekly_weather.drop(columns=['store_code_x', 'store_code_y'], errors='ignore')
```

---

### ISSUE B: NB03 Creates 11 New Lag Features Missing from NB04's Hardcoded Lists

**NB03 Creates (Cell 13):**
```python
LAG_FEATURES = [
    'units_lag_1w','units_lag_2w','units_lag_4w','units_lag_52w',              # ← 4 lags
    'units_roll4_mean','units_roll4_std',
    'units_roll8_mean','units_roll8_std',    # ← NEW: 8-week rolling
    'units_roll12_mean','units_roll12_std',  # ← NEW: 12-week rolling
    'units_volatility',                       # ← NEW: demand volatility
    'revenue_lag_1w','revenue_lag_4w','revenue_roll4_mean',  # ← NEW: revenue lags
    'avg_price_per_unit','price_lag_1w',     # ← NEW: price per unit
]
```
**15 lag features total**

**NB04 Hardcoded List (Cell 2):**
```python
LAG_FEATURES = [
    'units_lag_1w', 'units_lag_2w', 'units_lag_4w',
    'units_roll4_mean', 'units_roll4_std'
]
```
**Only 5 lag features expected**

**Missing Features (10 total, not 11 as reported earlier):**
- `units_lag_52w` (year-over-year lag)
- `units_roll8_mean`, `units_roll8_std` (8-week rolling window)
- `units_roll12_mean`, `units_roll12_std` (12-week rolling window)
- `units_volatility` (coefficient of variation)
- `revenue_lag_1w`, `revenue_lag_4w` (revenue lags)
- `revenue_roll4_mean` (revenue rolling mean)
- `avg_price_per_unit`, `price_lag_1w` (price per unit features)

**Impact:**
NB04 Cell 8 builds FINAL_FEATURES dynamically:
```python
ALL_FEATURE_CANDIDATES = (
    LAG_FEATURES + SEASONALITY_FEATURES + CALENDAR_FEATURES +
    WEATHER_FEATURES + DIVISION_FEATURES
)
available_features = [f for f in ALL_FEATURE_CANDIDATES if f in df.columns]
FINAL_FEATURES = available_features.copy()
```

**Outcome:**
- NB04 will skip the 10 missing features because they're not in `LAG_FEATURES` hardcoded list
- This is **NOT a crash** (dynamic build protects against it) but a **silent loss of features**
- The 10 new features NB03 creates will be ignored
- Model will train on only the 5 original lag features

---

### ISSUE C: Weather Interaction Terms Created in NB03 but Missing from NB04 WEATHER_FEATURES

**NB03 Creates (Cell 11):**
```python
WEATHER_FEATURES = (
    WEATHER_RAW                                   # 6 raw
    + [f'{c}_dev_z' for c in WEATHER_RAW]       # 6 dev_z (normalized deviations)
    + ['temp_above_20','temp_above_25','temp_below_0',
       'cooling_degree_days','heating_degree_days']  # 5 threshold flags
    + ['avg_temp_lag_1w','avg_temp_lag_2w','temp_shock','temp_warming']  # 4 lags/shocks
    + ['precip_x_summer','bad_wx_x_summer','sunshine_x_summer',
       'temp_above_25_x_sum','precip_x_spring','temp_warming_x_spr']  # 6 interactions
)
```
**27 weather features total, including 6 interaction terms**

**NB04 Hardcoded List (Cell 2):**
```python
WEATHER_FEATURES = [
    'avg_temp', 'total_precip', 'sunshine_hours',        # 3 raw
    'rain_days', 'snow_days', 'bad_weather_days',        # 3 raw
    'temp_above_20', 'temp_above_25',                    # 2 flags
    'cooling_degree_days', 'heating_degree_days',        # 2 CDD/HDD
    'avg_temp_dev_z', 'total_precip_dev_z'               # 2 dev_z
]
```
**12 weather features only (no interaction terms, no lags, minimal dev_z)**

**Mismatch (15 features created in NB03 but not in NB04 list):**
- `temp_below_0` (winter flag)
- `avg_temp_lag_1w`, `avg_temp_lag_2w` (temperature lags)
- `temp_shock`, `temp_warming` (temperature dynamics)
- `precip_x_summer`, `bad_wx_x_summer`, `sunshine_x_summer` (precipitation × season)
- `temp_above_25_x_sum` (heat × summer)
- `precip_x_spring`, `temp_warming_x_spr` (spring interactions)
- **Missing from NB03 but expected by NB04:**
  - `rain_days_dev_z`, `snow_days_dev_z`, `bad_weather_days_dev_z`, `sunshine_hours_dev_z` (3 more dev_z columns)

**Impact:**
Same as Issue B — the 15 weather interaction terms won't be in the hardcoded list, so they'll be skipped by the dynamic feature selection in NB04 Cell 8. Only the 12 hardcoded features will be used.

---

## VERIFICATION OF REVENUE COLUMN FLOW

**NB01 output:**
- `revenue` (raw, with negatives for returns)
- `revenue_clean` (clipped at 0)

**NB03 usage (Cell 13 of add_lag_features):**
```python
if 'revenue' in group.columns:
    for lag in [1, 4]:
        group[f'revenue_lag_{lag}w'] = group['revenue'].shift(lag)  # ← Uses raw 'revenue'
    group['revenue_roll4_mean'] = group['revenue'].shift(1).rolling(4, min_periods=2).mean()
    group['avg_price_per_unit'] = (
        group['revenue'] /                        # ← Uses raw 'revenue'
        group['units'].replace(0, np.nan)         # ← Divides by units (may cause inf if units=0)
    )
```

**Issues:**
1. NB03 uses raw `revenue`, not `revenue_clean`
2. Division by zero can produce `inf` values when units=0 but revenue>0 (service fees)
3. NB04 doesn't have special handling for these inf values in `avg_price_per_unit`

---

## SUMMARY TABLE

| Aspect | NB01 | NB02 | NB03 | NB04 | Status |
|--------|------|------|------|------|--------|
| **Input file** | Excel raw | weekly_units.csv | weekly_units_weather.csv | modeling_dataset.csv | ✓ |
| **Output file** | weekly_units.csv | weekly_units_weather.csv | modeling_dataset.csv | multiple .csv | ✓ |
| **Duplicate store_code** | No | **YES (3 versions)** | Passes through | — | ⚠️ Messy |
| **Lag features expected** | — | — | 15 created | 5 hardcoded | ❌ MISMATCH |
| **Weather features expected** | — | — | 27 created | 12 hardcoded | ❌ MISMATCH |
| **Interaction terms** | — | — | 6 created | 0 hardcoded | ❌ Lost feature |
| **Revenue handling** | raw + clean | passes through | uses raw (may cause inf) | processes via dynamic | ⚠️ Inconsistent |

---

## SPECIFIC CODE REFERENCES

### Breaking Issue: NB02 Cell 21 Merge Creates _x/_y Columns

```python
weekly_weather = weekly.merge(weather_weekly, on=['city','week_ending'], how='left')
# This creates store_code_x (from weekly) and store_code_y (from weather_weekly)
# because both have 'store_code' column

# Safety logic attempts recovery but doesn't clean up _x/_y:
if 'store_code' not in weekly_weather.columns and 'store_code' in weekly.columns:
    weekly_weather = weekly_weather.merge(...)  # Adds clean 'store_code'

# Result: all THREE columns remain in output
```

**Should be:**
```python
weekly_weather = weekly_weather.drop(columns=['store_code_x', 'store_code_y'], errors='ignore')
```

### Breaking Issue: NB04 Cell 2 Hardcoded Lists

```python
LAG_FEATURES = [
    'units_lag_1w', 'units_lag_2w', 'units_lag_4w',
    'units_roll4_mean', 'units_roll4_std'
]
# Missing: units_lag_52w, units_roll8_mean/std, units_roll12_mean/std, 
#          units_volatility, revenue_lag_1w/4w, revenue_roll4_mean,
#          avg_price_per_unit, price_lag_1w

WEATHER_FEATURES = [
    'avg_temp', 'total_precip', 'sunshine_hours',
    'rain_days', 'snow_days', 'bad_weather_days',
    'temp_above_20', 'temp_above_25',
    'cooling_degree_days', 'heating_degree_days',
    'avg_temp_dev_z', 'total_precip_dev_z'
]
# Missing: temp_below_0, avg_temp_lag_1w/2w, temp_shock, temp_warming,
#          precip_x_summer, bad_wx_x_summer, sunshine_x_summer, etc.
```

---

## RECOMMENDATIONS

1. **NB02 Fix:** Drop duplicate store_code columns in Cell 21 after merges complete
2. **NB04 Fix:** Update LAG_FEATURES and WEATHER_FEATURES lists to match NB03 output
   - OR change NB04 Cell 8 to read feature definitions from NB03's feature engineering steps
3. **NB03 Enhancement:** Create `revenue_clean` lags as alternative to raw revenue lags
4. **Data Quality:** Add check in NB03 for `inf` values in `avg_price_per_unit` and handle appropriately

---

## CONCLUSION

The pipeline has **no crashes** because NB04 uses dynamic feature selection (Cell 8). However, it **silently discards 25+ valuable features** created by NB03 because:
1. The hardcoded feature lists in NB04 Cell 2 are out of sync with NB03 output
2. NB02 leaves duplicate columns that are messy but not harmful

**Recommended action:** Update NB04's hardcoded lists to match NB03's feature engineering output before training production models.

