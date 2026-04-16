# Weather Integration Audit: Detailed Issues & Code Fixes

## ISSUE 1: Liquidation City Missing from Weather Mapping

### Location
- **Notebook Cell**: 4 (CITY_COORDS definition)
- **File**: `weekly_units.csv` contains city="Liquidation"
- **Data Impact**: 591 rows affected

### Description
Store CP07 (Laval) has rows labeled with `city='Liquidation'` from Feb 2024 onwards (representing a store liquidation sale period). However, `CITY_COORDS` dictionary only contains 27 cities, and "Liquidation" is not one of them.

### Root Cause
```python
# Cell 4 defines CITY_COORDS with 27 entries, e.g.:
'Laval': {'lat': 45.5833, 'lon': -73.7500, 'province': 'QC', 'store': 'CP07'},
# ... but does NOT include:
'Liquidation': {...}
```

When merging in Cell 21 on `['city', 'week_ending']`, the 591 Liquidation rows have no matching weather record.

### Detection
```python
# Check in weekly_units.csv
liquidation_count = weekly['city'].value_counts()['Liquidation']  # Returns 591

# Check in weather_by_city_week.csv
liquidation_in_weather = 'Liquidation' in weather_weekly['city'].values  # Returns False
```

### Evidence
```
Input:
  unique cities in weekly_units.csv:  28 (includes 'Liquidation')
  unique cities in CITY_COORDS:       27 (excludes 'Liquidation')

Output:
  missing weather rows after merge:   591
  rows with city='Liquidation':       591
  correlation:                         EXACT 1:1 match
```

### Fix Options

#### Option A: Map in Data Cleanup (NB01 or early NB02)
```python
# Cell 4 or Cell 5, after loading weekly
weekly['city'] = weekly['city'].replace('Liquidation', 'Laval')
```

#### Option B: Add to CITY_COORDS (not recommended)
```python
# Cell 4 - add duplicate entry
CITY_COORDS['Liquidation'] = {
    'lat': 45.5833, 'lon': -73.7500,  # Same as Laval
    'province': 'QC', 
    'store': 'CP07'
}
```
**Not recommended**: Inflates CITY_COORDS unnecessarily; creates duplicate weather fetch.

#### Option C: Post-Merge Imputation (not recommended)
```python
# Cell 21 - after merge, fill using Laval's weather
laval_weather = weather_weekly[weather_weekly['store_code'] == 'CP07']
liquidation_rows = weekly_weather[weekly_weather['city'] == 'Liquidation']
# Then join on week_ending...
```
**Not recommended**: Complex; error-prone.

### Recommended Implementation
```python
# In Cell 5 (validation block), after loading weekly_units.csv

# Remap liquidation store back to original city
weekly['city'] = weekly['city'].replace('Liquidation', 'Laval')

# Validation
assert weekly['city'].nunique() == 27, "Expected 27 cities after remapping"
assert 'Liquidation' not in weekly['city'].unique(), "Liquidation should be mapped"
print("✓ Liquidation store remapped to Laval")
```

### Impact if Not Fixed
- 591 rows remain with NaN weather (avg_temp, max_temp, total_precip, etc.)
- Gap filling in Cell 21 fails silently (no median to compute)
- Downstream ML models receive incomplete training data
- 2.4% data loss in effective sample size

---

## ISSUE 2: Duplicate Column Names (_x and _y suffixes)

### Location
- **Notebook Cell**: 21 (merge operation, lines 1–2)
- **Output File**: `weekly_units_weather.csv`
- **Columns Affected**: store_code_x, store_code_y, store_code

### Description
The first merge in Cell 21 joins on `['city', 'week_ending']` only, not on `store_code`. Since both left and right DataFrames have a `store_code` column, pandas automatically creates `store_code_x` and `store_code_y`. The remedial merge logic (lines 8–10) then adds a third `store_code` column.

### Root Cause
```python
# Cell 21, lines 1–2
weekly_weather = weekly.merge(
    weather_weekly, 
    on=['city','week_ending'],  # Missing: 'store_code'
    how='left'
)
# Result: store_code_x (from left/weekly), store_code_y (from right/weather_weekly)
```

### Evidence
```python
# Before merge:
weekly.columns:          ['week_ending', 'store_code', 'city', 'division_code', ...]
weather_weekly.columns:  ['store_code', 'city', 'province', 'week_ending', ...]

# After merge on ['city', 'week_ending']:
result.columns:  ['week_ending', 'store_code_x', 'city', 'division_code', 
                  'store_code_y', 'province', ...]

# After remedial merge (lines 8–10):
final.columns:   [..., 'store_code_x', ..., 'store_code_y', ..., 'store_code']
                 # Now 3 store_code columns!
```

### Data Quality Check
```python
# All three store_code columns should be identical (except for Liquidation NaNs)
weekly_weather['store_code_x'].equals(weekly_weather['store_code'])  # True
weekly_weather['store_code_y'].equals(weekly_weather['store_code'])  # True (mostly)

# For Liquidation rows:
liquidation_mask = weekly_weather['city'] == 'Liquidation'
weekly_weather.loc[liquidation_mask, 'store_code_y'].isna().all()  # True (all NaN)
weekly_weather.loc[liquidation_mask, 'store_code'].isna().all()    # False (has values)
```

### Fix

#### Clean Solution (Recommended)
```python
# Cell 21, after the holiday merge (line ~11)

# Drop duplicate columns
weekly_weather = weekly_weather.drop(
    columns=['store_code_x', 'store_code_y'], 
    errors='ignore'
)

# Verify single store_code column remains
assert 'store_code_x' not in weekly_weather.columns
assert 'store_code_y' not in weekly_weather.columns
assert 'store_code' in weekly_weather.columns
print("✓ Duplicate store_code columns removed")
```

#### Better Solution (Prevent _x/_y from the start)
```python
# Cell 21, line 1-2, replace with:
weekly_weather = weekly.merge(
    weather_weekly,
    on=['store_code', 'city', 'week_ending'],  # Include store_code in join keys
    how='left',
    validate='m:1'  # Ensure many sales rows : one weather row
)

# Now store_code won't get duplicated, and validate catches mismatches
```

### Impact if Not Fixed
- Schema bloat (24 columns instead of 21)
- Confusion about which store_code to use
- Potential errors in downstream processing (e.g., groupby on ambiguous column)
- Takes up storage unnecessarily in CSV output

---

## ISSUE 3: Gap Filling Fails Silently for Unmapped Cities

### Location
- **Notebook Cell**: 21 (lines ~13–18)
- **Function**: `groupby(['city','month']).transform('median')`
- **Affected Rows**: 591 (all Liquidation)

### Description
The gap filling strategy computes a monthly median for each city. For the "Liquidation" city, ALL values are initially missing (no weather was fetched), so `groupby(['city','month']).transform('median')` returns NaN for every row.

### Root Cause
```python
# Cell 21, lines 13–18
weekly_weather['month'] = weekly_weather['week_ending'].dt.month
for col in ['avg_temp','total_precip','rain_days',...]:
    if col in weekly_weather.columns:
        med = weekly_weather.groupby(['city','month'])[col].transform('median')
        weekly_weather[col] = weekly_weather[col].fillna(med)
```

For Liquidation city:
1. No matching weather_weekly rows (all were NaN after merge)
2. `groupby(['city','month'])` includes Liquidation group
3. Each Liquidation group has 100% NaN values
4. Median of all-NaN group = NaN
5. `fillna(NaN)` has no effect

### Evidence
```python
# Demonstration
liquidation_rows = weekly_weather[weekly_weather['city'] == 'Liquidation']

# Before gap filling:
liquidation_rows['avg_temp'].isna().all()  # True (all NaN)

# Compute monthly median (as the code does):
med = weekly_weather.groupby(['city','month'])['avg_temp'].transform('median')
liquidation_rows_med = med[liquidation_rows.index]

# Check result:
liquidation_rows_med.isna().all()  # Still True! (median of all-NaN = NaN)

# After fillna:
result = liquidation_rows['avg_temp'].fillna(liquidation_rows_med)
result.isna().all()  # Still True (fillna(NaN) does nothing)
```

### Fix

#### Solution 1: Fallback to Province-Level Median
```python
# Cell 21, lines 13–18, replace with:

weekly_weather['month'] = weekly_weather['week_ending'].dt.month

weather_cols = ['avg_temp','total_precip','rain_days','snow_days',
                'bad_weather_days','sunshine_hours']

for col in weather_cols:
    if col not in weekly_weather.columns:
        continue
    
    # Primary: city-month median
    med_city = weekly_weather.groupby(['city','month'])[col].transform('median')
    
    # Fallback: province-month median (for cities with all-NaN months)
    med_prov = weekly_weather.groupby(['province','month'])[col].transform('median')
    
    # Use city median where available, else province median
    med = med_city.fillna(med_prov)
    
    # Apply imputation
    weekly_weather[col] = weekly_weather[col].fillna(med)
    
    # Report any remaining gaps
    still_missing = weekly_weather[col].isna().sum()
    if still_missing > 0:
        print(f"⚠️  {col}: {still_missing} rows still missing after imputation")
```

#### Solution 2: Pre-Process (Best Practice)
Combine with Issue #1 fix (map Liquidation → Laval BEFORE merge):
```python
# Cell 5: Remap liquidation to Laval
weekly['city'] = weekly['city'].replace('Liquidation', 'Laval')

# Then the existing gap filling works perfectly
# (no all-NaN city anymore)
```

### Impact if Not Fixed
- 591 rows remain with NaN weather despite gap filling code
- Downstream imputation (global mean, forward fill) gives incorrect values
- ML models drop rows or fail
- Cumulative data loss across pipeline

---

## ISSUE 4: No Validation Warnings for Data Quality

### Location
- **Notebook Cell**: 21 (at the very end, no validation section)

### Description
Cell 21 performs critical merges and imputation but provides no validation output about:
- How many rows have missing weather
- Which cities/stores are affected
- Whether imputation succeeded

Cell 15 reports "Missing weather rows: 0" but this is from an intermediate merge (before the final merge on Cell 21). The final output has 591 missing rows, but no warning is issued.

### Evidence
```python
# Current Cell 21 ending:
print(f'Merged dataset: {weekly_weather.shape}')
# Prints only shape, no missing data check

# Should print (but doesn't):
# ✓ Merged dataset: (24323, 24)
# ⚠️  Missing weather: 591 rows (2.4%)
# ⚠️  Affected cities: ['Liquidation']
# ⚠️  Affected store-city combos: [('CP07', 'Liquidation')]
```

### Fix

Add validation block at the end of Cell 21:
```python
# Cell 21, after all merges and imputation

print("\n=== FINAL DATA QUALITY CHECK ===")

# Check for rows with all weather missing
weather_cols = ['avg_temp', 'max_temp', 'total_precip', 'sunshine_hours', 
                'rain_days', 'snow_days', 'bad_weather_days']
all_missing = weekly_weather[weather_cols].isna().all(axis=1)

if all_missing.any():
    n_missing = all_missing.sum()
    pct_missing = 100 * n_missing / len(weekly_weather)
    print(f"⚠️  {n_missing} rows ({pct_missing:.1f}%) missing all weather data")
    
    # Details
    missing_df = weekly_weather[all_missing][['store_code','city','week_ending']]
    missing_cities = missing_df['city'].unique()
    missing_stores = missing_df['store_code'].unique()
    print(f"  Cities affected: {list(missing_cities)}")
    print(f"  Stores affected: {list(missing_stores)}")
else:
    print("✓ All rows have weather data")

# Check for duplicate columns
dup_cols = [c for c in weekly_weather.columns if '_x' in c or '_y' in c]
if dup_cols:
    print(f"⚠️  Found duplicate column names: {dup_cols}")
else:
    print("✓ No duplicate columns")

# Check for partial missing (some columns missing)
partial_missing = weekly_weather[weather_cols].isna().any(axis=1) & ~all_missing
if partial_missing.any():
    n_partial = partial_missing.sum()
    print(f"⚠️  {n_partial} rows with partial weather missing")
else:
    print("✓ No partial missing weather data")

print(f"\nFinal output: {weekly_weather.shape[0]} rows × {weekly_weather.shape[1]} cols")
```

### Impact if Not Fixed
- Silent data quality issues go unnoticed
- Downstream failures seem mysterious (actually traceable to this step)
- Difficult to debug when models start failing
- Best practice violation (always validate after merges)

---

## ISSUE 5: Merge Should Use 3-Key Join with Validation

### Location
- **Notebook Cell**: 21 (line 1–2)

### Description
The merge on `['city', 'week_ending']` happens to work because city names are unique (1 city = 1 store). However, this is fragile:
1. If store A and store B were in the same city, the merge would create a cross-join (Cartesian product)
2. No validation that the merge is actually 1-to-many (1 weather row per many sales rows)
3. The resulting duplicate store_code columns make the issue apparent but silent

### Root Cause
```python
# Cell 21, line 1
weekly_weather = weekly.merge(
    weather_weekly,
    on=['city','week_ending'],  # Assumes city is unique identifier
    how='left'
)
# This works ONLY because CITY_COORDS enforces city=store uniqueness
```

### Better Practice
```python
# Cell 21, line 1 — improved version
weekly_weather = weekly.merge(
    weather_weekly,
    on=['store_code', 'city', 'week_ending'],  # 3-key join
    how='left',
    validate='m:1'  # Ensure many sales rows : one weather row
)
# This catches any structural mismatches
```

### Impact
- Robustness: Explicitly validates the relationship
- Debugging: `validate` parameter will raise error if relationship breaks
- Schema: Eliminates _x/_y columns since store_code is explicitly joined
- Clarity: Makes the intent clear (sales-to-weather is many-to-one)

---

## Summary Table: Issues & Fixes

| # | Issue | Severity | Cell | Fix Effort | Lines | Test |
|---|-------|----------|------|-----------|-------|------|
| 1 | Liquidation not in CITY_COORDS | 🔴 HIGH | 4–5 | 1 line | 1 | `assert 'Liquidation' not in weekly['city']` |
| 2 | Duplicate _x/_y columns | 🟠 MEDIUM | 21 | 1 line | 1 | `assert 'store_code_x' not in weekly_weather.columns` |
| 3 | Gap filling fails silently | 🟠 MEDIUM | 21 | ~8 lines | 8 | Check for remaining NaN after imputation |
| 4 | No validation output | 🟡 LOW | 21 | ~20 lines | 20 | Prints warning if missing weather |
| 5 | Merge not 3-key | 🟡 LOW | 21 | 2 lines | 2 | `validate='m:1'` catches errors |

---

## Implementation Order (Recommended)

1. **Fix #1** (Liquidation mapping) - solves #3 as side effect
2. **Fix #5** (3-key merge with validate) - prevents #2
3. **Fix #2** (drop duplicate columns) - cleanup
4. **Fix #4** (validation logging) - monitoring
5. **Fix #3** (province-level fallback) - robustness

**Estimated time**: 15–20 minutes
**Testing**: Re-run NB02 and check Cell 21 output

