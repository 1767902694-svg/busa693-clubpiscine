"""
09 — Weather Attribution Validation
====================================
Quick diagnostic to prove that weather deviations fix the multicollinearity
problem and restore proper weather attribution.

Tests:
  1. Baseline: current model (Fourier + raw weather) → shows VIF > 30
  2. Fix A: Fourier only (no weather) → shows lost variance
  3. Fix B: Weather deviations + 1 Fourier harmonic → should show VIF < 5
  4. Incremental R² comparison
  5. Coefficient stability check
"""

# ── Imports ──────────────────────────────────────────────────────────
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.metrics import r2_score
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
import json, warnings
warnings.filterwarnings('ignore')

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({'figure.figsize': (14, 8), 'font.size': 11, 'figure.dpi': 120})

# ── Paths ────────────────────────────────────────────────────────────
project_root = Path(__file__).parent.parent
processed_path = project_root / 'data' / 'processed'
figures_path = project_root / 'reports' / 'figures'
figures_path.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(project_root))
from src.features.transformations import (
    geometric_adstock, hill_saturation, log_saturation, power_saturation
)

# ── Load data ────────────────────────────────────────────────────────
df = pd.read_csv(processed_path / 'sales_spend_weather.csv', parse_dates=['date'])
df = df.sort_values('date').reset_index(drop=True)

with open(processed_path / 'optimal_transformation_params.json') as f:
    CAUSAL_PARAMS = json.load(f)

DECAY_RATES = CAUSAL_PARAMS['decay_rates']
SATURATION_PARAMS_RAW = CAUSAL_PARAMS.get('saturation_params', {})
SATURATION_FUNCS = CAUSAL_PARAMS.get('saturation_functions', {})

SPEND_TO_MEDIA = {
    'media_television':          'spend_television',
    'media_radio':               'spend_radio',
    'media_panneaux':            'spend_panneaux',
    'media_social_media':        'spend_social_media',
    'media_preroll':             'spend_preroll',
    'media_banniere_web':        'spend_banniere_web',
    'media_circulaire_digitale': 'spend_circulaire_digitale',
}

MEDIA_CHANNELS = list(SPEND_TO_MEDIA.keys())

for media_col, spend_col in SPEND_TO_MEDIA.items():
    df[media_col] = df[spend_col].fillna(0)

# Apply adstock + saturation
for ch in MEDIA_CHANNELS:
    lam = DECAY_RATES[ch]
    df[f'{ch}_adstock'] = geometric_adstock(df[ch].fillna(0).values, lam)

for ch in MEDIA_CHANNELS:
    adstock_col = f'{ch}_adstock'
    sat_func = SATURATION_FUNCS.get(ch, 'hill')
    sat_p = SATURATION_PARAMS_RAW.get(ch, {})

    if sat_func == 'hill':
        K = sat_p.get('K', float(df[adstock_col][df[adstock_col] > 0].median()) if (df[adstock_col] > 0).any() else 1.0)
        alpha = sat_p.get('alpha', 2)
        df[f'{ch}_saturated'] = hill_saturation(df[adstock_col].values, K, alpha)
    elif sat_func == 'log':
        scale = sat_p.get('scale', float(df[adstock_col][df[adstock_col] > 0].median()) if (df[adstock_col] > 0).any() else 1.0)
        df[f'{ch}_saturated'] = log_saturation(df[adstock_col].values, scale)
    elif sat_func == 'power':
        beta = sat_p.get('beta', 0.5)
        df[f'{ch}_saturated'] = power_saturation(df[adstock_col].values, beta)

SATURATED_COLS = [f'{ch}_saturated' for ch in MEDIA_CHANNELS]

# Target
y = df['total_all_revenue'].values

print(f"Data loaded: {len(df)} observations, {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Revenue: mean=${y.mean():,.0f}, std=${y.std():,.0f}")
print()

# =====================================================================
# TEST 1: CURRENT MODEL (Fourier 2 harmonics + raw weather)
# =====================================================================
print("=" * 72)
print("  TEST 1: CURRENT MODEL (Fourier 2H + raw weather scaled)")
print("=" * 72)

df['sin_1'] = np.sin(2 * np.pi * df['month_num'] / 12)
df['cos_1'] = np.cos(2 * np.pi * df['month_num'] / 12)
df['sin_2'] = np.sin(4 * np.pi * df['month_num'] / 12)
df['cos_2'] = np.cos(4 * np.pi * df['month_num'] / 12)

for wcol in ['total_sunshine_hours', 'total_precipitation', 'days_above_25']:
    df[f'{wcol}_scaled'] = (df[wcol] - df[wcol].mean()) / df[wcol].std()

CONTROL_CURRENT = ['sin_1', 'cos_1', 'sin_2', 'cos_2',
                   'total_sunshine_hours_scaled',
                   'total_precipitation_scaled',
                   'days_above_25_scaled']

FEAT_CURRENT = SATURATED_COLS + CONTROL_CURRENT

X1 = sm.add_constant(df[FEAT_CURRENT].fillna(0))
vif1 = pd.DataFrame({
    'Feature': FEAT_CURRENT,
    'VIF': [variance_inflation_factor(X1.values, i+1) for i in range(len(FEAT_CURRENT))]
}).sort_values('VIF', ascending=False)

scaler1 = StandardScaler()
X1s = scaler1.fit_transform(df[FEAT_CURRENT].fillna(0))
ridge1 = RidgeCV(alphas=np.logspace(-2, 3, 100), cv=LeaveOneOut())
ridge1.fit(X1s, y)
y_pred_cv1 = cross_val_predict(Ridge(alpha=ridge1.alpha_), X1s, y, cv=LeaveOneOut())
r2_cv1 = r2_score(y, y_pred_cv1)
r2_1 = r2_score(y, ridge1.predict(X1s))

coefs1 = pd.DataFrame({'feature': FEAT_CURRENT, 'coef': ridge1.coef_})

print(f"\nVIF (top 5):")
for _, row in vif1.head(5).iterrows():
    flag = " ← SEVERE" if row['VIF'] > 10 else ""
    print(f"  {row['Feature']:40s}  VIF = {row['VIF']:8.1f}{flag}")

print(f"\nR² = {r2_1:.4f},  LOOCV R² = {r2_cv1:.4f},  alpha = {ridge1.alpha_:.2f}")
print(f"\nWeather coefficients (standardized):")
for _, row in coefs1[coefs1['feature'].str.contains('sunshine|precip|days_above')].iterrows():
    print(f"  {row['feature']:40s}  coef = {row['coef']:>12,.0f}")

# =====================================================================
# TEST 2: FOURIER ONLY (no weather)
# =====================================================================
print("\n" + "=" * 72)
print("  TEST 2: FOURIER ONLY (no weather)")
print("=" * 72)

CONTROL_FOURIER = ['sin_1', 'cos_1', 'sin_2', 'cos_2']
FEAT_FOURIER = SATURATED_COLS + CONTROL_FOURIER

scaler2 = StandardScaler()
X2s = scaler2.fit_transform(df[FEAT_FOURIER].fillna(0))
ridge2 = RidgeCV(alphas=np.logspace(-2, 3, 100), cv=LeaveOneOut())
ridge2.fit(X2s, y)
y_pred_cv2 = cross_val_predict(Ridge(alpha=ridge2.alpha_), X2s, y, cv=LeaveOneOut())
r2_cv2 = r2_score(y, y_pred_cv2)
r2_2 = r2_score(y, ridge2.predict(X2s))

print(f"\nR² = {r2_2:.4f},  LOOCV R² = {r2_cv2:.4f},  alpha = {ridge2.alpha_:.2f}")
print(f"Delta vs current: R² = {r2_2 - r2_1:+.4f},  LOOCV R² = {r2_cv2 - r2_cv1:+.4f}")

# =====================================================================
# TEST 3: WEATHER DEVIATIONS + 1 Fourier harmonic (THE FIX)
# =====================================================================
print("\n" + "=" * 72)
print("  TEST 3: WEATHER DEVIATIONS + 1 Fourier harmonic (THE FIX)")
print("=" * 72)

# Calculate monthly averages and deviations
for wcol in ['total_sunshine_hours', 'total_precipitation', 'days_above_25']:
    monthly_avg = df.groupby('month_num')[wcol].transform('mean')
    df[f'{wcol}_deviation'] = df[wcol] - monthly_avg
    dev_std = df[f'{wcol}_deviation'].std()
    if dev_std > 0:
        df[f'{wcol}_dev_scaled'] = df[f'{wcol}_deviation'] / dev_std
    else:
        df[f'{wcol}_dev_scaled'] = 0.0

CONTROL_FIX = ['sin_1', 'cos_1',  # only 1 harmonic
               'total_sunshine_hours_dev_scaled',
               'total_precipitation_dev_scaled',
               'days_above_25_dev_scaled']

FEAT_FIX = SATURATED_COLS + CONTROL_FIX

# VIF check
X3 = sm.add_constant(df[FEAT_FIX].fillna(0))
vif3 = pd.DataFrame({
    'Feature': FEAT_FIX,
    'VIF': [variance_inflation_factor(X3.values, i+1) for i in range(len(FEAT_FIX))]
}).sort_values('VIF', ascending=False)

scaler3 = StandardScaler()
X3s = scaler3.fit_transform(df[FEAT_FIX].fillna(0))
ridge3 = RidgeCV(alphas=np.logspace(-2, 3, 100), cv=LeaveOneOut())
ridge3.fit(X3s, y)
y_pred_cv3 = cross_val_predict(Ridge(alpha=ridge3.alpha_), X3s, y, cv=LeaveOneOut())
r2_cv3 = r2_score(y, y_pred_cv3)
r2_3 = r2_score(y, ridge3.predict(X3s))

coefs3 = pd.DataFrame({'feature': FEAT_FIX, 'coef': ridge3.coef_})

print(f"\nVIF (top 5):")
for _, row in vif3.head(5).iterrows():
    flag = " ← SEVERE" if row['VIF'] > 10 else (" ← elevated" if row['VIF'] > 5 else " ✓")
    print(f"  {row['Feature']:40s}  VIF = {row['VIF']:8.1f}{flag}")

print(f"\nR² = {r2_3:.4f},  LOOCV R² = {r2_cv3:.4f},  alpha = {ridge3.alpha_:.2f}")
print(f"Delta vs current: R² = {r2_3 - r2_1:+.4f},  LOOCV R² = {r2_cv3 - r2_cv1:+.4f}")

print(f"\nWeather DEVIATION coefficients (standardized):")
for _, row in coefs3[coefs3['feature'].str.contains('sunshine|precip|days_above')].iterrows():
    print(f"  {row['feature']:40s}  coef = {row['coef']:>12,.0f}")

print(f"\nMedia coefficients (standardized):")
for _, row in coefs3[coefs3['feature'].str.contains('saturated')].iterrows():
    label = row['feature'].replace('media_', '').replace('_saturated', '')
    sign = "+" if row['coef'] > 0 else "-"
    print(f"  {label:40s}  coef = {row['coef']:>12,.0f}  ({sign})")

# =====================================================================
# TEST 4: Weather deviations + 1 harmonic + weather as PRIMARY DRIVER
# =====================================================================
print("\n" + "=" * 72)
print("  TEST 4: Full model with weather as primary driver")
print("=" * 72)

# Also add raw weather (monthly seasonal effect) separately
# This captures "summer is good for pools" distinct from "unusually sunny helps more"
# Use month_num as a categorical feature via dummy encoding
month_dummies = pd.get_dummies(df['month_num'], prefix='month', drop_first=True)
# Only include if we have enough observations
# With 36 obs and 11 month dummies, too many params. Use just sin/cos instead.

# Alternative: Use sin/cos for annual cycle + weather deviations for anomalies
# This is already TEST 3. Let's try adding a trend.
df['trend'] = np.arange(len(df)) / len(df)

CONTROL_FIX_TREND = ['sin_1', 'cos_1', 'trend',
                     'total_sunshine_hours_dev_scaled',
                     'total_precipitation_dev_scaled',
                     'days_above_25_dev_scaled']

FEAT_FIX_TREND = SATURATED_COLS + CONTROL_FIX_TREND

scaler4 = StandardScaler()
X4s = scaler4.fit_transform(df[FEAT_FIX_TREND].fillna(0))
ridge4 = RidgeCV(alphas=np.logspace(-2, 3, 100), cv=LeaveOneOut())
ridge4.fit(X4s, y)
y_pred_cv4 = cross_val_predict(Ridge(alpha=ridge4.alpha_), X4s, y, cv=LeaveOneOut())
r2_cv4 = r2_score(y, y_pred_cv4)
r2_4 = r2_score(y, ridge4.predict(X4s))

coefs4 = pd.DataFrame({'feature': FEAT_FIX_TREND, 'coef': ridge4.coef_})

print(f"\nR² = {r2_4:.4f},  LOOCV R² = {r2_cv4:.4f},  alpha = {ridge4.alpha_:.2f}")
print(f"Delta vs current: R² = {r2_4 - r2_1:+.4f},  LOOCV R² = {r2_cv4 - r2_cv1:+.4f}")

print(f"\nAll coefficients (standardized):")
for _, row in coefs4.iterrows():
    label = row['feature'].replace('media_', '').replace('_saturated', '').replace('_dev_scaled', '_DEV')
    sign_flag = "NEG ←" if row['coef'] < 0 and 'saturated' in row['feature'] else ""
    print(f"  {label:40s}  coef = {row['coef']:>12,.0f}  {sign_flag}")

# =====================================================================
# COMPARISON SUMMARY
# =====================================================================
print("\n" + "=" * 72)
print("  SUMMARY: MODEL COMPARISON")
print("=" * 72)

print(f"\n{'Model':<45s} {'R²':>8s} {'LOOCV R²':>10s} {'Alpha':>8s} {'Max Weather VIF':>16s}")
print("-" * 90)

# Get max weather VIF for each model
max_vif_1 = vif1[vif1['Feature'].str.contains('sunshine|precip|days')]['VIF'].max()
max_vif_3 = vif3[vif3['Feature'].str.contains('sunshine|precip|days')]['VIF'].max()

print(f"{'1. Current (Fourier 2H + raw weather)':<45s} {r2_1:>8.4f} {r2_cv1:>10.4f} {ridge1.alpha_:>8.2f} {max_vif_1:>16.1f}")
print(f"{'2. Fourier only (no weather)':<45s} {r2_2:>8.4f} {r2_cv2:>10.4f} {ridge2.alpha_:>8.2f} {'N/A':>16s}")
print(f"{'3. FIX: 1 harmonic + weather deviations':<45s} {r2_3:>8.4f} {r2_cv3:>10.4f} {ridge3.alpha_:>8.2f} {max_vif_3:>16.1f}")
print(f"{'4. FIX + trend':<45s} {r2_4:>8.4f} {r2_cv4:>10.4f} {ridge4.alpha_:>8.2f} {'(same)':>16s}")

# Negative coefficient check
print(f"\nNegative media coefficients:")
for name, coefs in [("Current", coefs1), ("Fix (deviations)", coefs3), ("Fix + trend", coefs4)]:
    neg = coefs[(coefs['feature'].str.contains('saturated')) & (coefs['coef'] < 0)]
    if len(neg) > 0:
        channels = [r['feature'].replace('media_', '').replace('_saturated', '') for _, r in neg.iterrows()]
        print(f"  {name}: {', '.join(channels)}")
    else:
        print(f"  {name}: NONE (all positive)")

# =====================================================================
# VISUALIZATION
# =====================================================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Panel 1: VIF comparison
ax = axes[0, 0]
vif_compare = pd.DataFrame({
    'Feature': ['sunshine', 'precipitation', 'days_above_25'],
    'Current (raw)': [
        vif1[vif1['Feature'].str.contains('sunshine')]['VIF'].values[0],
        vif1[vif1['Feature'].str.contains('precip')]['VIF'].values[0],
        vif1[vif1['Feature'].str.contains('days_above')]['VIF'].values[0],
    ],
    'Fix (deviations)': [
        vif3[vif3['Feature'].str.contains('sunshine')]['VIF'].values[0] if len(vif3[vif3['Feature'].str.contains('sunshine')]) > 0 else 0,
        vif3[vif3['Feature'].str.contains('precip')]['VIF'].values[0] if len(vif3[vif3['Feature'].str.contains('precip')]) > 0 else 0,
        vif3[vif3['Feature'].str.contains('days_above')]['VIF'].values[0] if len(vif3[vif3['Feature'].str.contains('days_above')]) > 0 else 0,
    ],
})
x_pos = np.arange(len(vif_compare))
width = 0.35
bars1 = ax.bar(x_pos - width/2, vif_compare['Current (raw)'], width, label='Current (raw weather)', color='#e74c3c', alpha=0.8)
bars2 = ax.bar(x_pos + width/2, vif_compare['Fix (deviations)'], width, label='Fix (deviations)', color='#2ecc71', alpha=0.8)
ax.set_xticks(x_pos)
ax.set_xticklabels(vif_compare['Feature'], rotation=15)
ax.set_ylabel('VIF')
ax.set_title('VIF Comparison: Raw Weather vs Deviations')
ax.axhline(5, color='orange', linestyle='--', linewidth=1, label='VIF = 5 threshold')
ax.axhline(10, color='red', linestyle='--', linewidth=1, label='VIF = 10 threshold')
ax.legend(fontsize=9)

# Panel 2: R² comparison
ax = axes[0, 1]
models = ['Current\n(Fourier 2H + raw)', 'Fourier only\n(no weather)', 'FIX: 1H +\ndeviations', 'FIX +\ntrend']
r2s = [r2_1, r2_2, r2_3, r2_4]
r2_cvs = [r2_cv1, r2_cv2, r2_cv3, r2_cv4]
x_pos = np.arange(len(models))
ax.bar(x_pos - width/2, r2s, width, label='R² (in-sample)', color='steelblue', alpha=0.8)
ax.bar(x_pos + width/2, r2_cvs, width, label='LOOCV R²', color='coral', alpha=0.8)
ax.set_xticks(x_pos)
ax.set_xticklabels(models, fontsize=9)
ax.set_ylabel('R²')
ax.set_title('Model Fit Comparison')
ax.legend()
ax.set_ylim(0.85, 1.0)

# Panel 3: Media coefficients comparison (current vs fix)
ax = axes[1, 0]
labels_media = [ch.replace('media_', '').replace('_saturated', '') for ch in SATURATED_COLS]
coefs_current = [coefs1[coefs1['feature'] == ch]['coef'].values[0] for ch in SATURATED_COLS]
coefs_fix = [coefs3[coefs3['feature'] == ch]['coef'].values[0] for ch in SATURATED_COLS]
x_pos = np.arange(len(labels_media))
ax.barh(x_pos - 0.2, coefs_current, 0.4, label='Current model', color='#e74c3c', alpha=0.7)
ax.barh(x_pos + 0.2, coefs_fix, 0.4, label='Fix (deviations)', color='#2ecc71', alpha=0.7)
ax.set_yticks(x_pos)
ax.set_yticklabels(labels_media)
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Ridge Coefficient (standardized)')
ax.set_title('Media Coefficients: Current vs Fix')
ax.legend()

# Panel 4: Weather deviations time series
ax = axes[1, 1]
for wcol, color, label in [
    ('total_sunshine_hours_deviation', '#f39c12', 'Sunshine deviation'),
    ('total_precipitation_deviation', '#3498db', 'Precipitation deviation'),
    ('days_above_25_deviation', '#e74c3c', 'Hot days deviation'),
]:
    if wcol in df.columns:
        vals = df[wcol] / df[wcol].std() if df[wcol].std() > 0 else df[wcol]
        ax.plot(df['date'], vals, marker='o', markersize=3, label=label, alpha=0.8, linewidth=1.5)
ax.axhline(0, color='grey', linestyle='--', linewidth=0.8)
ax.set_xlabel('Date')
ax.set_ylabel('Deviation (standardized)')
ax.set_title('Weather Deviations from Monthly Normal')
ax.legend(fontsize=9)

plt.suptitle('Weather Attribution Validation — Club Piscine MMM', fontsize=14, y=1.01)
plt.tight_layout()
plt.savefig(figures_path / 'weather_validation_comparison.png', dpi=150, bbox_inches='tight')
print(f"\nFigure saved: {figures_path / 'weather_validation_comparison.png'}")

# =====================================================================
# WEATHER ATTRIBUTION ESTIMATE
# =====================================================================
print("\n" + "=" * 72)
print("  WEATHER ATTRIBUTION ESTIMATE")
print("=" * 72)

# Method: Compare R² of model WITH vs WITHOUT weather deviations
# Using same number of Fourier harmonics (1)
FEAT_NO_WEATHER = SATURATED_COLS + ['sin_1', 'cos_1']
FEAT_WITH_WEATHER = FEAT_FIX  # includes deviations

scaler_nw = StandardScaler()
X_nw = scaler_nw.fit_transform(df[FEAT_NO_WEATHER].fillna(0))
ridge_nw = RidgeCV(alphas=np.logspace(-2, 3, 100), cv=LeaveOneOut())
ridge_nw.fit(X_nw, y)
r2_nw = r2_score(y, ridge_nw.predict(X_nw))
y_cv_nw = cross_val_predict(Ridge(alpha=ridge_nw.alpha_), X_nw, y, cv=LeaveOneOut())
r2_cv_nw = r2_score(y, y_cv_nw)

delta_r2 = r2_3 - r2_nw
delta_r2_cv = r2_cv3 - r2_cv_nw

print(f"\nWithout weather deviations:  R² = {r2_nw:.4f},  LOOCV R² = {r2_cv_nw:.4f}")
print(f"With weather deviations:     R² = {r2_3:.4f},  LOOCV R² = {r2_cv3:.4f}")
print(f"Delta (weather contribution): R² = {delta_r2:+.4f},  LOOCV R² = {delta_r2_cv:+.4f}")
print(f"\nWeather deviations explain an additional {delta_r2*100:.1f}% of revenue variance")
print(f"(cross-validated: {delta_r2_cv*100:.1f}%)")

total_revenue = df['total_all_revenue'].sum()
weather_attributed = total_revenue * max(delta_r2, 0)
print(f"\nEstimated weather-attributable revenue (3yr total): ${weather_attributed:,.0f}")
print(f"Out of total revenue: ${total_revenue:,.0f}")

print("\n" + "=" * 72)
print("  VALIDATION COMPLETE")
print("=" * 72)
print("""
KEY FINDINGS:
  - If VIF dropped from >30 to <5: Weather deviations fix multicollinearity ✓
  - If LOOCV R² is comparable or better: No loss of predictive power ✓
  - If negative media coefficients reduced/eliminated: Better identification ✓
  - If weather deviation coefficients are non-zero: Weather is now attributed ✓

NEXT STEPS:
  1. Update NB06 to use weather deviations instead of raw weather
  2. Reduce Fourier to 1 harmonic (sin_1, cos_1)
  3. Re-run NB07 and NB08 with the fixed specification
  4. Report weather attribution separately from media attribution
""")
