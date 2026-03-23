# 02 - Weather Integration Notebook: DETAILED AUDIT REPORT

**Notebook**: `/sessions/laughing-tender-wright/mnt/busa693-clubpiscine/use_case_4_forecasting/notebooks/02_weather_integration.ipynb`

**Audit Date**: 2026-03-22  
**Status**: All 13 code cells executed successfully  
**Output Files Generated**: 
- `data/processed/weather_by_city_week.csv` (3456 rows × 11 cols)
- `data/processed/weekly_units_weather.csv` (24323 rows × 24 cols)

---

## CRITICAL FINDINGS

### 🔴 ISSUE #1: "Liquidation" City Has No Weather Data (591 Rows Unmatched)

**Severity**: HIGH  
**Location**: Cell 21 (final merge)  
**Root Cause**: The city "Liquidation" exists in `weekly_units.csv` but is NOT in `CITY_COORDS` dictionary

**Details**:
- Store CP07 (Laval) has a data quality issue: starting Feb 2024, some rows are labeled with `city='Liquidation'` instead of `city='Laval'`
- These represent a Laval store liquidation sale period (Feb 2024 → Mar 2026)
- CITY_COORDS contains 27 cities; weekly_units contains 28 cities (includes "Liquidation")
- When merging on `['city', 'week_ending']`, the 591 Liquidation rows have NO matching weather records
- Result: **591 rows of sales data lack all 7 weather features** (avg_temp, max_temp, total_precip, sunshine_hours, rain_days, snow_days, bad_weather_days)

**Evidence**:
```
Liquidation rows: 591 (store_code='CP07', weeks from 2024-02-11 to 2026-03-22)
Missing weather rows in output: 591
Month-based gap filling fails: Cannot compute monthly median if ALL city-months are missing
Final output: avg_temp = NaN for all 591 Liquidation rows
```

**Recommended Fix**:
Option A (PREFERRED): Map "Liquidation" → "Laval" in NB01 cleanup
Option B: Pre-merge fix in Cell 4 or Cell 5:
```python
weekly['city'] = weekly['city'].replace('Liquidation', 'Laval')
```
Option C: Post-merge imputation using Laval's weather for the same weeks

---

### 🔴 ISSUE #2: Duplicate Column Names After Merge (_x and _y Suffixes)

**Severity**: MEDIUM  
**Location**: Cell 21 (first merge operation)  
**Lines of Code**:
```python
weekly_weather = weekly.merge(weather_weekly, on=['city','week_ending'], how='left')
```

**Problem**:
- Both `weekly` and `weather_weekly` have a `store_code` column
- Merge on only `['city', 'week_ending']` (not on store_code) → creates `store_code_x` and `store_code_y`
- Output has BOTH columns, along with a third `store_code` column added later
- Final output has: `['store_code_x', 'store_code_y', 'store_code']` (24323 rows × 24 cols)

**Evidence**:
```
Merge input columns:
  weekly: ['week_ending', 'store_code', 'city', 'division_code', ...]
  weather_weekly: ['store_code', 'city', 'province', 'week_ending', ...]

Merge output columns:
  ['week_ending', 'store_code_x', 'city', 'division_code', ..., 
   'store_code_y', 'province', ..., 'store_code']  # 3 store_code columns!

Redundancy check:
  - store_code_x: Always matches store_code (from weekly side)
  - store_code_y: All 591 Liquidation rows are NaN; others match store_code
  - store_code: Identical to store_code_x
```

**Remedial Code (Cell 21, lines 8-10)**:
```python
if 'store_code' not in weekly_weather.columns and 'store_code' in weekly.columns:
    weekly_weather = weekly_weather.merge(...)  # Triggers, but doesn't fully fix it
```
This logic attempts to fix the issue but doesn't clean up the _x/_y columns afterward.

**Recommended Fix**:
- Drop `store_code_x` and `store_code_y` after merge
- Keep only `store_code` (verified to match)
```python
weekly_weather = weekly_weather.drop(columns=['store_code_x', 'store_code_y'], errors='ignore')
```

---

### 🟠 ISSUE #3: Gap Filling Strategy Fails for Unmapped Cities

**Severity**: MEDIUM  
**Location**: Cell 21 (gap filling loop)  
**Lines of Code**:
```python
for col in ['avg_temp','total_precip','rain_days',...]:
    if col in weekly_weather.columns:
        med = weekly_weather.groupby(['city','month'])[col].transform('median')
        weekly_weather[col] = weekly_weather[col].fillna(med)
```

**Problem**:
- Gap filling uses monthly median **per city**
- For "Liquidation" city: ALL values are missing for ALL 11 months present
- `groupby(['city','month']).transform('median')` returns NaN for every Liquidation row
- Imputation has ZERO effect on the 591 missing weather values

**Evidence**:
```
Before fillna: avg_temp has 591 NaNs (all Liquidation)
After fillna:  avg_temp still has 591 NaNs
  → median computation returns NaN for Liquidation (no non-null values to compute from)
```

**Why This Matters**:
- The code *appears* to handle missing weather, but silently fails for entire cities
- Downstream notebooks (03_feature_engineering, 06_causal_inference) may error or produce unreliable results
- No warning or logging issued

**Recommended Fix**:
- Pre-process weekly_units to map Liquidation → Laval before any merge
- OR add fallback imputation: use province-wide median if city-month median is unavailable
```python
med = weekly_weather.groupby(['city','month'])[col].transform('median')
if med.isna().any():
    prov_med = weekly_weather.groupby(['province','month'])[col].transform('median')
    med = med.fillna(prov_med)
weekly_weather[col] = weekly_weather[col].fillna(med)
```

---

## DETAILED SECTION AUDITS

### 1. Weather Data Source

**Cell 2: Imports** ✓ PASS
- All required packages imported: pandas, numpy, requests, holidays, matplotlib
- Paths configured: `DATA_PROCESSED = PROJECT_ROOT / 'data' / 'processed'`

**Cell 4–5: City Configuration** ⚠️ PARTIAL
- 27 cities defined in CITY_COORDS dictionary
- Coordinates appear reasonable (lat/lon pairs for Quebec & Ontario)
- Store codes match 42-store network from CLAUDE.md (consolidated to 27 active stores after NB01 regrouping)
- **Missing**: Liquidation city is in raw data but not in CITY_COORDS

**Cells 9–11: API Fetching**
- **Historical data**: Uses `https://archive-api.open-meteo.com/v1/archive` (Free tier, reliable)
- **Forecast data**: Uses `https://api.open-meteo.com/v1/forecast` (Free tier, 16-day forward)
- Rate limit handling: Exponential backoff (4s, 8s, 16s, 32s) with max 4 retries
- **Reliability**: Both APIs are industry-standard, free, and well-documented
- **Timezone**: "America/Toronto" (correct for Quebec/Ontario)

**Data Range Fetched**:
```
Historical: 2023-11-05 → date.today() - 1 day (archive API limit)
Forecast:   today → +16 days forward
Final coverage: 2023-11-05 → 2026-04-12
```

✓ Covers full sales period (2023-11-05 to 2026-03-22) plus forecast buffer

---

### 2. Geographic Granularity

**Scope**: 27 active stores across Quebec (25 QC, 1 ON/Nepean, 1 ON/Gatineau area)

**Granularity Level**: **STORE-LEVEL** ✓
- Each store's latitude/longitude in CITY_COORDS is precise to ~0.001 degrees (~100m accuracy)
- Weather API fetches daily data for each store's exact coordinates
- No province-wide averaging used in fetch phase

**Aggregation to Weekly**: 
- Cell 13 aggregates daily weather → weekly by `groupby(['store_code', 'city', 'province'])`
- Each store gets distinct weather series
- Output: `weather_by_city_week.csv` has 27 stores × 128 weeks = 3456 rows (✓ correct math)

**Accuracy Assessment**:
- Club Piscine stores are retail locations (fixed addresses)
- Store coordinates are assigned once at CITY_COORDS definition
- No updating or dynamic location mapping
- **Potential Issue**: If a store relocates, coordinates become stale (not addressed in notebook)

---

### 3. Temporal Alignment

**Date Format & Consistency**: ✓ EXCELLENT
- All datasets use `week_ending` with format: Timestamp('YYYY-MM-DD 00:00:00')
- `resample('W')` in pandas defaults to **Sunday** as week end
- Weekly dates: 2023-11-05 (Sun) → 2023-11-12 (Sun) → ... (all Sundays) ✓

**Week Definition**:
- Sales data: 24,323 rows across 125 unique week_ending dates (27 stores × ~125 weeks)
- Weather data: 3,456 rows across 128 unique week_ending dates (27 stores × ~128 weeks)
- **Forecast weeks extend beyond sales**: Last 3 forecast weeks (2026-03-29, 2026-04-05, 2026-04-12) have no matching sales data

**Off-by-One Risks**: ✓ NONE DETECTED
- No shifted dates or misaligned weeks
- Both daily → weekly aggregations use same resample('W') logic
- Merge on exact `week_ending` matches correctly

**Note**: The sales data is WEEKLY, not monthly (despite CLAUDE.md mentioning 36 monthly observations for the MMM phase). This notebook produces weekly granularity; downstream notebooks may aggregate to monthly.

---

### 4. Weather Features Created

**Classification Function (Cell 7)**: ✓ WELL-DESIGNED
```python
def classify_weather(df):
    # Maps WMO codes to meaningful categories
    weather_condition: Clear, Cloudy, Fog, Rain, Snow, Thunderstorm, Other
    is_rain: 1/0 flag
    is_snow: 1/0 flag
    is_bad_weather: 1/0 (Rain, Snow, Thunderstorm, Fog)
```
- WMO classification uses open-meteo standard (codes 0–99)
- Appropriate for pool/spa business (bad weather reduces retail foot traffic)

**Features Aggregated to Weekly (Cell 13)**:

| Feature | Aggregation | Business Relevance | Data Quality |
|---------|-------------|-------------------|--------------|
| `avg_temp` | Mean | Pool water heating demand ✓ | No nulls |
| `max_temp` | Max | Peak heat events (comfort factor) ✓ | No nulls |
| `total_precip` | Sum | Rainy day avoidance ✓ | No nulls |
| `sunshine_hours` | Sum | Outdoor pool/spa appeal ✓ | No nulls |
| `rain_days` | Sum | Binary daily counts | No nulls |
| `snow_days` | Sum | Winter accessibility | No nulls |
| `bad_weather_days` | Sum | Combined adverse condition | No nulls |

**Assessment**: Features are intuitive and well-suited to the business (seasonal outdoor entertainment products). No missing feature classes (e.g., wind, humidity not available from free API, acceptable trade-off).

---

### 5. Missing Weather Data Handling

**Identification (Cell 21)**:
```python
# Missing values explicitly checked:
missing_weather_rows = weekly_sales_weather['avg_temp'].isna().sum()
# Cell 15 output: "Missing weather rows: 0"  [MISLEADING — see Issue #1]
```

**Imputation Strategy (Cell 21, lines 13–18)**:
```python
weekly_weather['month'] = weekly_weather['week_ending'].dt.month
for col in ['avg_temp','total_precip',...]:
    if col in weekly_weather.columns:
        med = weekly_weather.groupby(['city','month'])[col].transform('median')
        weekly_weather[col] = weekly_weather[col].fillna(med)
```

**Effectiveness**:
- ✓ Works perfectly for valid city-month combinations (matched stores)
- 🔴 Fails for Liquidation city (all 591 rows remain NaN)

**Alternative Imputation Options NOT Used**:
- Province-wide median (not implemented)
- Year-over-year median (not implemented)
- Forward/backward fill (not implemented)
- Interpolation (not implemented)

**Recommendation**: 
Before gap filling, detect and warn about completely unmapped cities:
```python
unmapped_cities = weekly_weather[weekly_weather[weather_cols].isna().all(axis=1)]['city'].unique()
if len(unmapped_cities) > 0:
    print(f"⚠️ WARNING: {len(unmapped_cities)} cities have NO weather data: {unmapped_cities}")
```

---

### 6. Merge Logic & Data Loss

**Cell 15: First Weather Merge (Sales ← Weather)**
```python
merge_keys = ['week_ending', 'store_code', 'city']
weekly_sales_weather = weekly.merge(
    weather_weekly,
    on=merge_keys,
    how='left'
)
```
- **Result**: All 24,323 sales rows preserved (left join)
- **Missing weather**: 0 reported (but this is WRONG; see Issue #2)

**Cell 21: Corrected Merge (using city, week_ending only)**
```python
weekly_weather = weekly.merge(
    weather_weekly, 
    on=['city','week_ending'],  # Note: NOT store_code
    how='left'
)
```
- **Result**: 24,323 rows, but creates `store_code_x` and `store_code_y`
- **Missing weather AFTER merge**: 591 rows (all Liquidation)

**Merge Key Selection Issue**:
- City names are unique identifiers (1 city = 1 store in CITY_COORDS)
- **BUT**: The merge should explicitly include `store_code` to validate consistency
```python
# Better approach:
weekly_weather = weekly.merge(
    weather_weekly,
    on=['store_code', 'city', 'week_ending'],  # 3-key join
    how='left',
    validate='m:1'  # Ensure m:1 relationship (multiple sales rows per weather row)
)
```

**Holiday Merge (Cell 21, lines 9–11)**:
```python
weekly_weather = weekly_weather.merge(
    holiday_weekly[['city','week_ending','n_holidays','has_holiday']],
    on=['city','week_ending'], 
    how='left'
)
```
- ✓ Correct join keys
- ✓ Fills gaps with 0 for n_holidays and has_holiday
- No data loss

---

### 7. Output Files Quality

**File 1: `weather_by_city_week.csv`**
```
Shape:     3456 rows × 11 columns
Stores:    27 unique store_codes (all expected stores)
Cities:    27 unique cities (no Liquidation)
Weeks:     128 unique week_ending dates (2023-11-05 → 2026-04-12)
Columns:   ['store_code', 'city', 'province', 'week_ending', 'avg_temp', 
            'max_temp', 'total_precip', 'sunshine_hours', 'rain_days', 
            'snow_days', 'bad_weather_days']
Missing:   ZERO (no NaN values)
```
✓ CLEAN: This is a complete, aggregated weather dataset for 27 valid stores.

**File 2: `weekly_units_weather.csv`**
```
Shape:     24,323 rows × 24 columns
Columns:   (includes store_code_x, store_code_y, store_code — REDUNDANT)
Missing:   591 rows missing all weather features (province, avg_temp, max_temp, 
           total_precip, sunshine_hours, rain_days, snow_days, bad_weather_days)
Row Composition:
  - 23,732 rows (27 stores × ~125 weeks): Complete weather data ✓
  - 591 rows (Liquidation city): All weather NaN ✗
```

**Data Loss in Output**:
- 591 rows (2.4% of total) have incomplete weather
- Downstream ML models will either:
  - Fail (if they don't handle NaN)
  - Drop rows (loss of sales data)
  - Impute incorrectly (if they use global mean)

---

### 8. Errors & Warnings

**Execution Status**: All 13 code cells executed without errors ✓

**Cells with Output**:
- Cell 2: Imports complete ✓
- Cell 4–5: Data loaded (weekly: 24,323 rows) ✓
- Cell 7: Function defined ✓
- Cell 9: Historical weather fetched (all cities) ✓
- Cell 11: Forecast weather fetched (all cities) ✓
- Cell 13: Weekly aggregation (3456 rows) ✓
- Cell 14: Column summary ✓
- Cell 15: Merge complete, reports "Missing weather rows: 0" ⚠️ [FALSE]
- Cell 19: Holiday records created ✓
- Cell 21: Final merge, final report printed ✓
- Cell 23: Visualizations generated ✓
- Cell 25: Files saved ✓

**Silent Data Quality Issues**:
- ⚠️ Cell 15 reports "Missing weather rows: 0" but this is from an intermediate merge
- ⚠️ Cell 21 does NOT report the 591 missing rows in final output
- ⚠️ No validation checks for unmapped cities
- ⚠️ No warnings about duplicate column names (_x/_y)

**Recommended Logging (Cell 21)**:
```python
# After holiday merge:
unmapped = weekly_weather[weather_cols].isna().all(axis=1)
print(f"Final validation: {unmapped.sum()} rows missing all weather ({100*unmapped.sum()/len(weekly_weather):.1f}%)")
if unmapped.any():
    print(f"  Affected cities: {weekly_weather[unmapped]['city'].unique()}")
    print(f"  Affected store-city combos: {weekly_weather[unmapped][['store_code','city']].drop_duplicates().values.tolist()}")

# Check for _x/_y columns
dup_cols = [c for c in weekly_weather.columns if '_x' in c or '_y' in c]
if dup_cols:
    print(f"⚠️  Found duplicate column names: {dup_cols}")
```

---

### 9. Unexecuted Cells

**Status**: NONE  
All 13 code cells (cells 2, 4–5, 7, 9, 11, 13–16, 19, 21, 23, 25) have been executed and have output.

---

## SUMMARY OF ISSUES

| # | Issue | Severity | Type | Rows Affected | Fix Effort |
|---|-------|----------|------|---------------|-----------|
| 1 | Liquidation city not in CITY_COORDS | 🔴 HIGH | Data Quality | 591 | Easy |
| 2 | Duplicate _x/_y columns in final output | 🟠 MEDIUM | Schema | 24,323 | Easy |
| 3 | Gap filling fails for unmapped cities | 🟠 MEDIUM | Logic | 591 | Medium |
| 4 | No validation warnings for missing weather | 🟡 LOW | Logging | 591 | Easy |
| 5 | Store code merge should use 3-key join | 🟡 LOW | Robustness | 0 (works by luck) | Easy |

---

## RECOMMENDATIONS (Priority Order)

### P0 (Must Fix Before Downstream Notebooks)
1. **Map Liquidation → Laval** in NB01 or at start of NB02
   - Add to Cell 4 or Cell 5:
     ```python
     weekly['city'] = weekly['city'].replace('Liquidation', 'Laval')
     ```
   - OR add "Liquidation" to CITY_COORDS with Laval's coordinates

2. **Drop duplicate store_code columns** in Cell 21:
   ```python
   weekly_weather = weekly_weather.drop(columns=['store_code_x', 'store_code_y'], errors='ignore')
   ```

### P1 (Improve Robustness)
3. **Add validation check** at end of Cell 21:
   ```python
   missing_weather = weekly_weather[['avg_temp','max_temp','total_precip']].isna().all(axis=1)
   if missing_weather.any():
       print(f"⚠️ {missing_weather.sum()} rows missing all weather data")
       print(f"   Cities: {weekly_weather[missing_weather]['city'].unique()}")
   ```

4. **Enhance merge logic** in Cell 21:
   ```python
   weekly_weather = weekly.merge(
       weather_weekly,
       on=['store_code', 'city', 'week_ending'],  # 3-key join
       how='left',
       validate='m:1'
   )
   ```

5. **Improve gap filling** to handle unmapped cities:
   ```python
   for col in weather_cols:
       med_city = weekly_weather.groupby(['city','month'])[col].transform('median')
       # Fallback to province median if city-month is all NaN
       med_prov = weekly_weather.groupby(['province','month'])[col].transform('median')
       med = med_city.fillna(med_prov)
       weekly_weather[col] = weekly_weather[col].fillna(med)
   ```

### P2 (Documentation)
6. Document the data quality issue in CLAUDE.md or a README
7. Add comments explaining why some store-weeks may have missing weather

---

## PASS/FAIL ASSESSMENT

| Criterion | Result | Notes |
|-----------|--------|-------|
| Weather data source reliable | ✓ PASS | Free tier APIs (open-meteo) are industry-standard |
| Covers full date range | ✓ PASS | 2023-11-05 → 2026-04-12 (includes forecast) |
| Geographic granularity adequate | ✓ PASS | Store-level; 27 stores mapped with coordinates |
| Temporal alignment correct | ✓ PASS | Sunday week-ending, consistent with sales weeks |
| Features appropriate for business | ✓ PASS | Temp, precip, sunshine, rain/snow days all relevant to pools/spas |
| Missing data handled | ⚠️ PARTIAL | Gap filling works for valid cities; fails for Liquidation (591 rows) |
| Merge logic correct | ⚠️ PARTIAL | Works but creates redundant columns; no 3-key validation |
| Output schema clean | ✗ FAIL | Contains store_code_x, store_code_y, store_code (3x redundancy) |
| Downstream-ready | ✗ FAIL | 591 rows with missing weather will break ML models unless handled |

**Overall**: **FUNCTIONAL BUT REQUIRES FIXES BEFORE USE**

The notebook successfully fetches, classifies, and aggregates weather data from reliable APIs. However, it fails to handle the "Liquidation" city properly, leaving 591 rows (2.4%) with missing weather data. The output schema contains redundant columns. These issues must be resolved before feeding the data to downstream ML models (NB03–NB07).

