#!/usr/bin/env python3
"""
Script to create nb05_part1.ipynb — Global LightGBM Demand Forecast Model (Part 1)
Uses nbformat to construct the notebook with markdown and code cells.
"""

from pathlib import Path
import nbformat as nbf

# Create a new notebook
nb = nbf.v4.new_notebook()

# ============================================================================
# CELL 1: Markdown Title
# ============================================================================
cell_1 = nbf.v4.new_markdown_cell(
    """# NB05 — Global LightGBM Demand Forecast Model

**Single global model across all 287 store×division groups**

## Approach
- One LightGBM model trained on all store×division×week observations
- Unified feature set: seasonality, calendar, weather, demand lags, and activity indicators
- Walk-forward validation to simulate real forecasting scenarios
- Quantile regression (10th, 50th, 90th percentiles) for prediction intervals
- Revenue conversion using predicted units × observed/modeled price
- Model comparison against naive and seasonal baselines
"""
)
nb.cells.append(cell_1)

# ============================================================================
# CELL 2: Imports and Setup
# ============================================================================
cell_2 = nbf.v4.new_code_cell(
    """import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, r2_score
from sklearn.preprocessing import LabelEncoder
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Paths
from pathlib import Path
project_root = Path('.').resolve().parent
data_dir = project_root / 'data' / 'processed'
fig_dir = project_root / 'reports' / 'figures'
fig_dir.mkdir(parents=True, exist_ok=True)

print("NB05 — Global LightGBM Demand Forecast Model")
print("=" * 50)"""
)
nb.cells.append(cell_2)

# ============================================================================
# CELL 3: Load Data
# ============================================================================
cell_3 = nbf.v4.new_code_cell(
    """df = pd.read_csv(data_dir / 'modeling_dataset.csv', parse_dates=['week_ending'])
print(f"Raw dataset: {df.shape[0]:,} rows × {df.shape[1]} columns")
print(f"Date range: {df['week_ending'].min().date()} to {df['week_ending'].max().date()}")
print(f"Stores: {df['store_code'].nunique()}, Divisions: {df['division_code'].nunique()}")
print(f"Groups (store × division): {df.groupby(['store_code', 'division_code']).ngroups}")"""
)
nb.cells.append(cell_3)

# ============================================================================
# CELL 4: Markdown Section Header
# ============================================================================
cell_4 = nbf.v4.new_markdown_cell(
    """## 1. Data Preparation"""
)
nb.cells.append(cell_4)

# ============================================================================
# CELL 5: Fix Known Data Issues
# ============================================================================
cell_5 = nbf.v4.new_code_cell(
    """# Fix 1: Map Liquidation city to Laval (591 missing weather rows)
df['city'] = df['city'].replace('Liquidation', 'Laval')

# Fix 2: Drop merge artifacts
drop_cols = [c for c in df.columns if c.endswith('_x') or c.endswith('_y')]
if drop_cols:
    # Keep store_code (from store_code_x if store_code exists)
    df = df.drop(columns=[c for c in drop_cols if c != 'store_code_x'], errors='ignore')
    if 'store_code_x' in df.columns:
        df = df.rename(columns={'store_code_x': 'store_code'})
    print(f"Dropped merge artifacts: {drop_cols}")

# Fix 3: Fill remaining weather NaNs with city-week medians
weather_cols = ['avg_temp', 'max_temp', 'total_precip', 'sunshine_hours', 'rain_days',
                'snow_days', 'bad_weather_days']
for col in weather_cols:
    if col in df.columns:
        city_medians = df.groupby(['city', df['week_ending'].dt.isocalendar().week])[col].transform('median')
        df[col] = df[col].fillna(city_medians)

weather_nulls = df[weather_cols].isna().sum().sum()
print(f"Remaining weather nulls after fix: {weather_nulls}")
print(f"Dataset after fixes: {df.shape}")"""
)
nb.cells.append(cell_5)

# ============================================================================
# CELL 6: Define Feature Sets
# ============================================================================
cell_6 = nbf.v4.new_code_cell(
    """# Target
TARGET = 'units'
REVENUE_COL = 'revenue'

# Identity columns (not features, used for grouping)
ID_COLS = ['week_ending', 'store_code', 'division_code', 'city']

# Categorical features (will be label-encoded for LightGBM)
CAT_FEATURES = ['store_code', 'division_code', 'city']

# All numeric features from NB03
# Seasonality
SEASON_FEATS = ['sin_week_1', 'cos_week_1', 'sin_week_2', 'cos_week_2',
                'sin_month_1', 'cos_month_1']

# Calendar
CALENDAR_FEATS = ['year_idx', 'quarter', 'month', 'week_of_yr',
                  'n_holidays', 'has_holiday',
                  'is_summer_peak', 'is_spring_opening', 'is_fall_closing', 'is_winter_off']

# Weather (raw + derived)
WEATHER_RAW = ['avg_temp', 'max_temp', 'total_precip', 'sunshine_hours',
               'rain_days', 'snow_days', 'bad_weather_days']
WEATHER_DEV = ['avg_temp_dev', 'avg_temp_dev_z', 'total_precip_dev', 'total_precip_dev_z',
               'sunshine_hours_dev', 'sunshine_hours_dev_z', 'rain_days_dev', 'rain_days_dev_z',
               'snow_days_dev', 'snow_days_dev_z', 'bad_weather_days_dev', 'bad_weather_days_dev_z']
WEATHER_THRES = ['temp_above_20', 'temp_above_25', 'temp_below_0',
                 'cooling_degree_days', 'heating_degree_days']
WEATHER_LAG = ['avg_temp_lag_1w', 'avg_temp_lag_2w', 'temp_shock', 'temp_warming']
WEATHER_INTERACT = ['precip_x_summer', 'bad_wx_x_summer', 'sunshine_x_summer',
                    'temp_above_25_x_sum', 'precip_x_spring', 'temp_warming_x_spr']

# Demand lags and rolling stats
DEMAND_FEATS = ['units_lag_1w', 'units_lag_2w', 'units_lag_4w', 'units_lag_52w',
                'units_roll4_mean', 'units_roll4_std', 'units_roll8_mean', 'units_roll8_std',
                'units_roll12_mean', 'units_roll12_std', 'units_volatility']

# Revenue/price lags
REVENUE_FEATS = ['revenue_lag_1w', 'revenue_lag_4w', 'revenue_roll4_mean',
                 'avg_price_per_unit', 'price_lag_1w']

# Activity features
ACTIVITY_FEATS = ['n_transactions', 'is_active_product', 'weeks_with_sales']

# Combine all features
ALL_FEATURES = (SEASON_FEATS + CALENDAR_FEATS + WEATHER_RAW + WEATHER_DEV +
                WEATHER_THRES + WEATHER_LAG + WEATHER_INTERACT +
                DEMAND_FEATS + REVENUE_FEATS + ACTIVITY_FEATS)

# Filter to features that actually exist in data
FEATURES = [f for f in ALL_FEATURES if f in df.columns]
missing_feats = [f for f in ALL_FEATURES if f not in df.columns]
if missing_feats:
    print(f"⚠ Missing features (will skip): {missing_feats}")
print(f"Using {len(FEATURES)} numeric features + {len(CAT_FEATURES)} categorical features")
print(f"Total model inputs: {len(FEATURES) + len(CAT_FEATURES)}")"""
)
nb.cells.append(cell_6)

# ============================================================================
# CELL 7: Encode Categoricals and Prepare Model Data
# ============================================================================
cell_7 = nbf.v4.new_code_cell(
    """# Label encode categorical features
label_encoders = {}
for col in CAT_FEATURES:
    le = LabelEncoder()
    df[f'{col}_enc'] = le.fit_transform(df[col].astype(str))
    label_encoders[col] = le
    print(f"  {col}: {len(le.classes_)} categories")

CAT_ENC = [f'{c}_enc' for c in CAT_FEATURES]

# Drop rows with NaN in critical lag features (warmup period)
required_cols = ['units_lag_4w', 'avg_temp_lag_2w']
mask = df[required_cols].notna().all(axis=1)
df_model = df[mask].copy()
print(f"\\nAfter dropping lag warmup: {len(df_model):,} rows ({len(df_model)/len(df)*100:.1f}%)")
print(f"Groups remaining: {df_model.groupby(['store_code', 'division_code']).ngroups}")

# Fill remaining NaN in non-critical features with 0
for col in FEATURES + CAT_ENC:
    if col in df_model.columns:
        nulls = df_model[col].isna().sum()
        if nulls > 0:
            df_model[col] = df_model[col].fillna(0)
            print(f"  Filled {nulls} NaNs in {col}")"""
)
nb.cells.append(cell_7)

# ============================================================================
# CELL 8: Revenue and Units Distribution
# ============================================================================
cell_8 = nbf.v4.new_code_cell(
    """fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# Revenue by division
rev_div = df_model.groupby('division_code')['revenue'].mean().sort_values(ascending=False)
rev_div.plot.bar(ax=axes[0], color='steelblue')
axes[0].set_title('Avg Weekly Revenue by Division')
axes[0].set_ylabel('$ Revenue')
axes[0].tick_params(axis='x', rotation=45)

# Units by division
units_div = df_model.groupby('division_code')['units'].mean().sort_values(ascending=False)
units_div.plot.bar(ax=axes[1], color='coral')
axes[1].set_title('Avg Weekly Units by Division')
axes[1].set_ylabel('Units')
axes[1].tick_params(axis='x', rotation=45)

# Revenue vs Units scatter by group
grp = df_model.groupby(['store_code', 'division_code']).agg(
    avg_units=('units', 'mean'), avg_revenue=('revenue', 'mean')
).reset_index()
axes[2].scatter(grp['avg_units'], grp['avg_revenue'], alpha=0.5, s=20)
axes[2].set_xlabel('Avg Weekly Units')
axes[2].set_ylabel('Avg Weekly Revenue ($)')
axes[2].set_title('Revenue vs Units by Group')

plt.tight_layout()
plt.savefig(fig_dir / 'nb05_revenue_units_distribution.png', dpi=150, bbox_inches='tight')
plt.show()
print(f"\\nRevenue range: ${df_model['revenue'].min():,.0f} to ${df_model['revenue'].max():,.0f}")
print(f"Units range: {df_model['units'].min():.0f} to {df_model['units'].max():.0f}")"""
)
nb.cells.append(cell_8)

# ============================================================================
# Save the notebook
# ============================================================================
output_path = Path('/sessions/laughing-tender-wright') / 'mnt' / 'busa693-clubpiscine' / 'use_case_4_forecasting' / 'nb05_part1.ipynb'
with open(output_path, 'w') as f:
    nbf.write(nb, f)

print(f"✓ Notebook created: {output_path}")
print(f"✓ Total cells: {len(nb.cells)}")
print(f"  - Markdown: {sum(1 for c in nb.cells if c.cell_type == 'markdown')}")
print(f"  - Code: {sum(1 for c in nb.cells if c.cell_type == 'code')}")
