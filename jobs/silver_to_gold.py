"""
silver_to_gold.py
Silver → Gold modeling job for ClubPiscine MMM.

Direct conversion of NB06b (causal_inference_improved) + NB07 (mmm_roi_optimization).

Silver inputs (silver/Mix_Media_Modeling/processed/):
  REQUIRED:
    sales_spend_merged.csv              ← from clean_to_silver job
  OPTIONAL (used if present):
    sales_spend_weather.csv             ← from weather-ingest-gma job (NB04)
    optimal_transformation_params.json  ← from NB05 (calibrated adstock/saturation)
                                           If missing → industry-default decay rates used

Gold outputs (gold/Mix_Media_Modeling/reports/):
  media_effectiveness_results.csv
  mmm_optimization_results.csv
  mmm_scenario_analysis.csv
  mmm_executive_summary.csv
  causal_model_params.json
  mmm_final_output.json

Environment variables required:
  AZURE_STORAGE_ACCOUNT_NAME
  AZURE_STORAGE_ACCOUNT_KEY
  SILVER_CONTAINER      (default: silver)
  GOLD_CONTAINER        (default: gold)
  SILVER_INPUT_DIR      (default: Mix_Media_Modeling/processed/)
  GOLD_OUTPUT_DIR       (default: Mix_Media_Modeling/reports/)
"""

import io
import os
import json
import logging
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.optimize import nnls, minimize
from scipy.interpolate import interp1d
from sklearn.linear_model import Ridge, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
from azure.storage.blob import BlobServiceClient

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


# ─── Channel definitions ────────────────────────────────────────────────────────

MEDIA_CHANNELS = [
    'media_television',
    'media_radio',
    'media_panneaux',
    'media_social_media',
    'media_preroll',
    'media_banniere_web',
    'media_circulaire_digitale',
]

SPEND_TO_MEDIA = {
    'media_television':          'spend_television',
    'media_radio':               'spend_radio',
    'media_panneaux':            'spend_panneaux',
    'media_social_media':        'spend_social_media',
    'media_preroll':             'spend_preroll',
    'media_banniere_web':        'spend_banniere_web',
    'media_circulaire_digitale': 'spend_circulaire_digitale',
}

CHANNEL_LABELS = {
    'television':          'Television',
    'radio':               'Radio',
    'panneaux':            'Panneaux (Outdoor)',
    'social_media':        'Social Media',
    'preroll':             'Preroll (Video)',
    'banniere_web':        'Web Banners',
    'circulaire_digitale': 'Digital Flyers',
}

TARGET_COLS = [
    'total_all_revenue',
    'piscines_hors_terre_revenue',
    'piscines_creusees_revenue',
    'spas_revenue',
    'meubles_gazebo_revenue',
    'fitness_revenue',
    'bbq_revenue',
]

PRODUCT_LABELS = {
    'total_all_revenue':           'Total Revenue',
    'piscines_hors_terre_revenue': 'Above-Ground Pools (HT)',
    'piscines_creusees_revenue':   'In-Ground Pools (CR)',
    'spas_revenue':                'Spas (SP)',
    'meubles_gazebo_revenue':      'Furniture & Gazebo (ME&GA)',
    'fitness_revenue':             'Fitness (FI)',
    'bbq_revenue':                 'BBQ (BQ)',
}

# Used when optimal_transformation_params.json is missing
INDUSTRY_DEFAULT_DECAY = {
    'media_television':          0.7,
    'media_radio':               0.5,
    'media_panneaux':            0.4,
    'media_social_media':        0.4,
    'media_preroll':             0.5,
    'media_banniere_web':        0.3,
    'media_circulaire_digitale': 0.3,
}

BUSINESS_CONSTRAINTS = {
    'channel_bounds': {
        'television':          (80_000,  180_000),
        'radio':               (30_000,   90_000),
        'panneaux':             (5_000,   30_000),
        'social_media':        (15_000,   90_000),
        'preroll':             (15_000,  110_000),
        'banniere_web':        (20_000,   80_000),
        'circulaire_digitale':  (8_000,   40_000),
    },
    'traditional_channels':  ['television', 'radio', 'panneaux'],
    'traditional_pct_range': (0.35, 0.65),
}


# ─── Azure helpers ──────────────────────────────────────────────────────────────

def get_client():
    name = os.environ['AZURE_STORAGE_ACCOUNT_NAME']
    key  = os.environ['AZURE_STORAGE_ACCOUNT_KEY']
    conn = (f"DefaultEndpointsProtocol=https;AccountName={name};"
            f"AccountKey={key};EndpointSuffix=core.windows.net")
    return BlobServiceClient.from_connection_string(conn)

def download_bytes(client, container, path):
    log.info(f'  ↓  {container}/{path}')
    return client.get_blob_client(container=container, blob=path).download_blob().readall()

def try_download(client, container, path, kind='csv'):
    """Return None instead of raising if blob doesn't exist."""
    try:
        raw = download_bytes(client, container, path)
        if kind == 'json':
            return json.loads(raw.decode('utf-8'))
        return pd.read_csv(io.BytesIO(raw))
    except Exception:
        log.warning(f'  Optional file not found: {path}')
        return None

def upload_csv(client, container, path, df):
    data = df.to_csv(index=False).encode('utf-8')
    client.get_blob_client(container=container, blob=path).upload_blob(data, overwrite=True)
    log.info(f'  ↑  {container}/{path}  ({len(df):,} rows)')

def upload_json(client, container, path, obj):
    data = json.dumps(obj, indent=2, default=str).encode('utf-8')
    client.get_blob_client(container=container, blob=path).upload_blob(data, overwrite=True)
    log.info(f'  ↑  {container}/{path}')


# ─── Transformation functions (NB06b inline) ───────────────────────────────────

def geometric_adstock(x, decay_rate):
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(x)
    out[0] = x[0]
    for t in range(1, len(x)):
        out[t] = x[t] + decay_rate * out[t - 1]
    return out

def hill_saturation(x, K, alpha=2):
    x = np.asarray(x, dtype=float)
    return np.where(x > 0, x**alpha / (x**alpha + K**alpha), 0.0)

def hill_derivative(x, K, alpha):
    x = np.asarray(x, dtype=float)
    denom = (x**alpha + K**alpha) ** 2
    numer = alpha * K**alpha * x**(alpha - 1)
    return np.where(denom > 0, numer / denom, 0.0)


# ─── Non-negative Ridge (NB06b Fix 6) ──────────────────────────────────────────

class NNRidgeResult:
    def __init__(self, coef, intercept):
        self.coef_      = coef
        self.intercept_ = intercept
    def predict(self, X):
        return X @ self.coef_ + self.intercept_

def nonneg_ridge_fit(X, y, alpha):
    n, p   = X.shape
    X_aug  = np.vstack([X, np.sqrt(alpha) * np.eye(p)])
    y_aug  = np.concatenate([y, np.zeros(p)])
    coef, _ = nnls(X_aug, y_aug)
    intercept = y.mean() - X.mean(axis=0) @ coef
    return coef, intercept


# ─── Feature engineering (NB06b Cells 10-13) ───────────────────────────────────

def engineer_features(df, causal_params):
    """
    NB06b Fix 1 : All Hill saturation → bounded [0,1] for all channels.
    NB06b Fix   : 1 Fourier harmonic + weather DEVIATIONS (not raw values).
    Falls back gracefully when weather columns are absent.
    """
    df = df.copy()

    decay_rates    = causal_params.get('decay_rates', INDUSTRY_DEFAULT_DECAY)
    sat_params_raw = causal_params.get('saturation_params', {})

    # Rename spend_ → media_
    for media_col, spend_col in SPEND_TO_MEDIA.items():
        df[media_col] = df[spend_col].fillna(0) if spend_col in df.columns else 0.0

    # Adstock
    for ch in MEDIA_CHANNELS:
        lam = decay_rates.get(ch, INDUSTRY_DEFAULT_DECAY.get(ch, 0.4))
        df[f'{ch}_adstock'] = geometric_adstock(df[ch].fillna(0).values, lam)

    # Hill saturation
    saturation_params = {}
    for ch in MEDIA_CHANNELS:
        sp    = sat_params_raw.get(ch, {})
        K     = sp.get('K', None)
        if K is None:
            nz = df[f'{ch}_adstock'][df[f'{ch}_adstock'] > 0]
            K  = float(nz.median()) if len(nz) > 0 else 1.0
        alpha = sp.get('alpha', 2)
        saturation_params[ch] = {'type': 'hill', 'K': K, 'alpha': alpha}
        df[f'{ch}_saturated']  = hill_saturation(df[f'{ch}_adstock'].values, K, alpha)

    saturated_cols = [f'{ch}_saturated' for ch in MEDIA_CHANNELS]

    # Control features: 1 Fourier harmonic + weather deviations when available
    df['sin_1'] = np.sin(2 * np.pi * df['month_num'] / 12)
    df['cos_1'] = np.cos(2 * np.pi * df['month_num'] / 12)
    control_cols = ['sin_1', 'cos_1']

    for wcol in ['total_sunshine_hours', 'total_precipitation', 'days_above_25']:
        if wcol in df.columns:
            avg = df.groupby('month_num')[wcol].transform('mean')
            dev = df[wcol] - avg
            std = dev.std()
            df[f'{wcol}_dev_scaled'] = dev / std if std > 0 else 0.0
            control_cols.append(f'{wcol}_dev_scaled')

    if len(control_cols) == 2:
        log.warning('    No weather data — Fourier seasonality only (run weather job to improve fit)')

    log.info(f'    Controls : {control_cols}')
    log.info(f'    Saturated channels : {len(saturated_cols)}')
    return df, saturated_cols, control_cols, saturation_params, decay_rates


# ─── Two-Stage Non-Negative Ridge (NB06b Cell 23) ──────────────────────────────

def fit_model(df, saturated_cols, control_cols):
    tscv   = TimeSeriesSplit(n_splits=5)
    ALPHAS = np.logspace(-2, 4, 200)

    scaler_ctrl   = StandardScaler()
    X_ctrl        = scaler_ctrl.fit_transform(df[control_cols].fillna(0))
    scaler_media  = StandardScaler()
    X_media       = scaler_media.fit_transform(df[saturated_cols].fillna(0))

    stage1    = {}
    residuals = {}

    # Stage 1: seasonal baseline
    for t in TARGET_COLS:
        y   = df[t].values
        rcv = RidgeCV(alphas=ALPHAS, scoring='neg_mean_squared_error', cv=tscv)
        rcv.fit(X_ctrl, y)
        m1  = Ridge(alpha=rcv.alpha_).fit(X_ctrl, y)
        y_s = m1.predict(X_ctrl)
        stage1[t]    = {'model': m1, 'y_seasonal': y_s, 'r2': r2_score(y, y_s)}
        residuals[t] = y - y_s

    # Stage 2: media lift on residuals (non-negative)
    results = {}
    for t in TARGET_COLS:
        y_r  = residuals[t]
        rcv2 = RidgeCV(alphas=ALPHAS, scoring='neg_mean_squared_error', cv=tscv)
        rcv2.fit(X_media, y_r)
        coef, intercept = nonneg_ridge_fit(X_media, y_r, rcv2.alpha_)
        m2   = NNRidgeResult(coef, intercept)
        y_med = m2.predict(X_media)
        y_s   = stage1[t]['y_seasonal']
        y_pred = y_s + y_med
        y_act  = df[t].values

        r2   = r2_score(y_act, y_pred)
        r2m  = r2_score(y_r, y_med) if y_r.std() > 0 else 0.0
        mae  = mean_absolute_error(y_act, y_pred)
        n, p = len(y_act), len(control_cols) + len(saturated_cols)
        adj  = 1 - (1 - r2) * (n - 1) / (n - p - 1)

        results[t] = {
            'model_s1':   stage1[t]['model'],
            'model_s2':   m2,
            'best_alpha': rcv2.alpha_,
            'r2':         r2,
            'r2_s1':      stage1[t]['r2'],
            'r2_s2':      r2m,
            'adj_r2':     adj,
            'mae':        mae,
            'y_pred':     y_pred,
            'y_seasonal': y_s,
            'y_media':    y_med,
        }
        log.info(f'      {PRODUCT_LABELS[t]:30s}  R²={r2:.3f}  R²_s1={stage1[t]["r2"]:.3f}  '
                 f'R²_s2={r2m:.3f}  MAE=${mae:,.0f}')

    return results, residuals, scaler_ctrl, scaler_media


# ─── Effectiveness (NB06b Cell 36) ─────────────────────────────────────────────

def compute_effectiveness(df, results, saturated_cols, scaler_media,
                          saturation_params, decay_rates):
    rows = []
    for t in TARGET_COLS:
        beta_orig = results[t]['model_s2'].coef_ / scaler_media.scale_
        for i, ch in enumerate(MEDIA_CHANNELS):
            ch_short = ch.replace('media_', '')
            b        = beta_orig[i]
            nz       = df[f'{ch}_adstock'][df[f'{ch}_adstock'] > 0]
            a_eval   = float(nz.median()) if len(nz) > 0 else 0.0
            K, ah    = saturation_params[ch]['K'], saturation_params[ch]['alpha']
            dS       = float(hill_derivative(a_eval, K, ah))
            lam      = decay_rates.get(ch, 0.4)
            gain     = 1.0 / (1.0 - lam) if lam < 1.0 else 1.0
            m1k      = b * dS * gain * 1000
            roas     = b * dS * gain
            spend_col = SPEND_TO_MEDIA[ch]
            total_spend = float(df[spend_col].sum()) if spend_col in df.columns else 0.0
            contrib  = b * float(df[saturated_cols[i]].sum())
            rows.append({
                'product':           PRODUCT_LABELS[t],
                'channel':           ch_short,
                'channel_label':     CHANNEL_LABELS.get(ch_short, ch_short),
                'total_spend':       total_spend,
                'marginal_per_1000': round(m1k, 2),
                'marginal_ci_lo':    round(m1k * 0.6, 2),
                'marginal_ci_hi':    round(m1k * 1.4, 2),
                'roas':              round(roas, 4),
                'total_contribution': round(contrib, 2),
                'contribution_pct':  round(contrib / float(df[t].sum()) * 100, 2)
                                     if df[t].sum() > 0 else 0.0,
            })
    return pd.DataFrame(rows)


# ─── Response functions (NB07 Cell 5) ──────────────────────────────────────────

def build_response_funcs(df, results, saturated_cols, scaler_media,
                         saturation_params, decay_rates):
    beta_orig = results['total_all_revenue']['model_s2'].coef_ / scaler_media.scale_
    funcs, bounds, curve_rows = {}, {}, []

    for i, ch in enumerate(MEDIA_CHANNELS):
        ch_short  = ch.replace('media_', '')
        K, ah     = saturation_params[ch]['K'], saturation_params[ch]['alpha']
        lam       = decay_rates.get(ch, 0.4)
        gain      = 1.0 / (1.0 - lam) if lam < 1.0 else 1.0
        spend_col = SPEND_TO_MEDIA[ch]
        max_sp    = max(float(df[spend_col].max()) * 1.5 if spend_col in df.columns else 1000, 1000)
        sg        = np.linspace(0, max_sp, 100)
        rv        = beta_orig[i] * hill_saturation(sg * gain, K, ah)
        funcs[ch_short]  = interp1d(sg, rv, kind='cubic', bounds_error=False,
                                     fill_value=(rv[0], rv[-1]))
        bounds[ch_short] = (float(sg[0]), float(sg[-1]))
        for s, r in zip(sg, rv):
            curve_rows.append({'channel': ch_short, 'spend': round(s, 2), 'revenue': round(r, 2)})

    return funcs, bounds, pd.DataFrame(curve_rows)


# ─── Optimizer + scenarios (NB07 Cells 7-11) ───────────────────────────────────

def run_optimizer(channels, funcs, bounds, current_spend, total_budget):
    bc       = BUSINESS_CONSTRAINTS
    ch_bounds = [(max(bc['channel_bounds'].get(ch, (0, total_budget))[0],
                      bounds.get(ch, (0, total_budget))[0]),
                  min(bc['channel_bounds'].get(ch, (0, total_budget))[1],
                      bounds.get(ch, (0, total_budget))[1]))
                 for ch in channels]
    trad_idx  = [i for i, ch in enumerate(channels) if ch in bc['traditional_channels']]
    tlo, thi  = bc['traditional_pct_range']
    constraints = [
        {'type': 'eq',   'fun': lambda x: x.sum() - total_budget},
        {'type': 'ineq', 'fun': lambda x: sum(x[i] for i in trad_idx) - tlo * total_budget},
        {'type': 'ineq', 'fun': lambda x: thi * total_budget - sum(x[i] for i in trad_idx)},
    ]
    x0 = np.array([current_spend.get(ch, total_budget / len(channels)) for ch in channels])
    x0 = np.clip(x0, [b[0] for b in ch_bounds], [b[1] for b in ch_bounds])
    x0 = x0 * total_budget / x0.sum()
    res = minimize(lambda x: -sum(float(funcs[ch](x[i])) for i, ch in enumerate(channels)),
                   x0, method='SLSQP', bounds=ch_bounds, constraints=constraints,
                   options={'maxiter': 2000, 'ftol': 1e-10})
    alloc = {ch: max(res.x[i], ch_bounds[i][0]) for i, ch in enumerate(channels)}
    return alloc, res.success

def run_scenarios(channels, funcs, bounds, current_spend, total_budget, current_response):
    rows = []
    for name, mult in [('Cut 20%', 0.80), ('Cut 15%', 0.85), ('Cut 10%', 0.90),
                       ('Cut 5%',  0.95), ('Current', 1.00), ('Increase 5%',  1.05),
                       ('Increase 10%', 1.10), ('Increase 15%', 1.15), ('Increase 20%', 1.20)]:
        budget = total_budget * mult
        alloc, ok = run_optimizer(channels, funcs, bounds, current_spend, budget)
        resp = sum(float(funcs[ch](alloc[ch])) for ch in channels)
        rows.append({
            'scenario':           name,
            'budget_multiplier':  mult,
            'total_budget':       round(budget, 2),
            'optimized_response': round(resp, 2),
            'vs_current_pct':     round((resp - current_response) / abs(current_response) * 100, 2)
                                  if current_response != 0 else 0.0,
            'converged':          ok,
        })
    return pd.DataFrame(rows)


# ─── MAIN ───────────────────────────────────────────────────────────────────────

def main():
    log.info('=' * 65)
    log.info('ClubPiscine MMM  —  Job 2: Silver → Gold')
    log.info('=' * 65)

    silver     = os.environ.get('SILVER_CONTAINER', 'silver')
    gold       = os.environ.get('GOLD_CONTAINER',   'gold')
    silver_dir = os.environ.get('SILVER_INPUT_DIR',
                                'Mix_Media_Modeling/processed/').rstrip('/') + '/'
    gold_dir   = os.environ.get('GOLD_OUTPUT_DIR',
                                'Mix_Media_Modeling/reports/').rstrip('/') + '/'

    client = get_client()
    log.info(f'Account : {os.environ["AZURE_STORAGE_ACCOUNT_NAME"]}')

    # ── 1. Load data ──────────────────────────────────────────────────────────
    log.info('\n[1/5] Loading from silver')

    df = try_download(client, silver, f'{silver_dir}sales_spend_weather.csv')
    if df is not None:
        log.info('    ✓ Using sales_spend_weather.csv (weather-enriched)')
    else:
        log.warning('    sales_spend_weather.csv missing — using sales_spend_merged.csv')
        raw = download_bytes(client, silver, f'{silver_dir}sales_spend_merged.csv')
        df  = pd.read_csv(io.BytesIO(raw))

    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.sort_values('date').reset_index(drop=True)
    log.info(f'    Shape: {df.shape}  |  FYs: {sorted(df["year"].unique())}')

    causal_params = try_download(client, silver,
                                 f'{silver_dir}optimal_transformation_params.json', 'json')
    if causal_params:
        log.info(f'    ✓ Calibrated params loaded')
    else:
        log.warning('    optimal_transformation_params.json missing — using industry defaults')
        causal_params = {
            'decay_rates':        INDUSTRY_DEFAULT_DECAY,
            'saturation_params':  {},
            'calibration_method': 'industry_defaults',
            'calibration_date':   'N/A',
        }

    # ── 2. Feature engineering ────────────────────────────────────────────────
    log.info('\n[2/5] Feature engineering (adstock + Hill saturation)')
    df, saturated_cols, control_cols, sat_params, decay_rates = \
        engineer_features(df, causal_params)

    # ── 3. Fit Two-Stage Non-Negative Ridge ───────────────────────────────────
    log.info('\n[3/5] Two-Stage Non-Negative Ridge MMM (NB06b)')
    results, residuals, scaler_ctrl, scaler_media = \
        fit_model(df, saturated_cols, control_cols)

    # ── 4. Effectiveness + response curves ───────────────────────────────────
    log.info('\n[4/5] Effectiveness + response functions')
    eff_df = compute_effectiveness(
        df, results, saturated_cols, scaler_media, sat_params, decay_rates)
    response_funcs, spend_bounds, _ = build_response_funcs(
        df, results, saturated_cols, scaler_media, sat_params, decay_rates)

    # ── 5. Optimization + scenarios ───────────────────────────────────────────
    log.info('\n[5/5] Budget optimization + scenarios (NB07)')

    channels      = [ch.replace('media_', '') for ch in MEDIA_CHANNELS]
    current_spend = {ch: float(df[f'spend_{ch}'].mean())
                     for ch in channels if f'spend_{ch}' in df.columns}
    total_budget  = sum(current_spend.values())

    current_response = sum(float(response_funcs[ch](current_spend.get(ch, 0)))
                           for ch in channels)
    optimal_alloc, converged = run_optimizer(
        channels, response_funcs, spend_bounds, current_spend, total_budget)
    optimal_response = sum(float(response_funcs[ch](optimal_alloc[ch])) for ch in channels)
    lift_pct = ((optimal_response - current_response) / abs(current_response) * 100
                if current_response != 0 else 0.0)

    log.info(f'    Optimizer converged : {converged}')
    log.info(f'    Current response    : ${current_response:,.0f}/month')
    log.info(f'    Optimal response    : ${optimal_response:,.0f}/month')
    log.info(f'    Lift                : {lift_pct:+.1f}%')

    scenario_df = run_scenarios(
        channels, response_funcs, spend_bounds,
        current_spend, total_budget, current_response)

    # ── Build output DataFrames ───────────────────────────────────────────────
    eff_total = eff_df[eff_df['product'] == 'Total Revenue'].set_index('channel')

    def confidence(row):
        if row.get('marginal_ci_lo', 0) > 0: return 'HIGH'
        if row.get('roas', 0) > 1:           return 'MEDIUM'
        if row.get('roas', 0) > 0:           return 'LOW'
        return 'NONE'
    eff_total = eff_total.copy()
    eff_total['confidence'] = eff_total.apply(confidence, axis=1)

    opt_rows = []
    for ch in channels:
        cur    = current_spend.get(ch, 0)
        opt    = optimal_alloc[ch]
        chg    = (opt - cur) / cur * 100 if cur > 0 else 0.0
        opt_rows.append({
            'channel':       ch,
            'channel_label': CHANNEL_LABELS.get(ch, ch),
            'current_spend': round(cur, 2),
            'optimal_spend': round(opt, 2),
            'change_pct':    round(chg, 1),
            'confidence':    str(eff_total.loc[ch, 'confidence']) if ch in eff_total.index else 'LOW',
            'action':        'INCREASE' if chg > 10 else ('DECREASE' if chg < -10 else 'MAINTAIN'),
        })
    opt_df = pd.DataFrame(opt_rows)

    total_revenue = float(df['total_all_revenue'].sum())
    beta_orig_tot = results['total_all_revenue']['model_s2'].coef_ / scaler_media.scale_
    total_media_contrib = sum(beta_orig_tot[i] * float(df[saturated_cols[i]].sum())
                              for i in range(len(saturated_cols)))
    media_share_pct = total_media_contrib / total_revenue * 100 if total_revenue > 0 else 0.0

    summary_rows = []
    for ch in channels:
        cur = current_spend.get(ch, 0)
        rec = optimal_alloc[ch]
        chg = (rec - cur) / cur * 100 if cur > 0 else 0.0
        summary_rows.append({
            'channel':                ch,
            'channel_label':          CHANNEL_LABELS.get(ch, ch),
            'current_monthly_spend':  round(cur, 2),
            'recommended_spend':      round(rec, 2),
            'change_pct':             round(chg, 1),
            'roas':   round(float(eff_total.loc[ch, 'roas']), 4) if ch in eff_total.index else 0.0,
            'confidence': str(eff_total.loc[ch, 'confidence']) if ch in eff_total.index else 'LOW',
            'action': 'INCREASE' if chg > 10 else ('DECREASE' if chg < -10 else 'MAINTAIN'),
        })
    summary_df = pd.DataFrame(summary_rows)

    # model params JSON
    model_params_out = {
        'model_type':               'two_stage_nonneg_ridge',
        'calibration_params_source': causal_params.get('calibration_method', 'industry_defaults'),
        'run_date':                  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'decay_rates':    {k.replace('media_', ''): v for k, v in decay_rates.items()},
        'saturation_params': {k.replace('media_', ''): v for k, v in sat_params.items()},
        'ridge_r2_full':  {PRODUCT_LABELS[t]: round(results[t]['r2'], 4) for t in TARGET_COLS},
        'ridge_r2_s1':    {PRODUCT_LABELS[t]: round(results[t]['r2_s1'], 4) for t in TARGET_COLS},
        'ridge_r2_s2':    {PRODUCT_LABELS[t]: round(results[t]['r2_s2'], 4) for t in TARGET_COLS},
        'adj_r2':         {PRODUCT_LABELS[t]: round(results[t]['adj_r2'], 4) for t in TARGET_COLS},
        'mae':            {PRODUCT_LABELS[t]: round(results[t]['mae'], 2) for t in TARGET_COLS},
        'media_share_pct': round(media_share_pct, 2),
        'seasonal_share_pct': round(
            float(results['total_all_revenue']['y_seasonal'].sum()) / total_revenue * 100, 2)
            if total_revenue > 0 else 0.0,
        'media_channels': channels,
        'control_cols':   control_cols,
        'scaler_media_mean':  scaler_media.mean_.tolist(),
        'scaler_media_scale': scaler_media.scale_.tolist(),
        'coefs_s2_orig':  {saturated_cols[i]: round(float(beta_orig_tot[i]), 6)
                           for i in range(len(saturated_cols))},
    }

    mmm_final = {
        'source':  'silver_to_gold.py (NB06b + NB07)',
        'created':  datetime.now().strftime('%Y-%m-%d %H:%M'),
        'model_performance': {
            'r2_full':         model_params_out['ridge_r2_full'].get('Total Revenue', 0),
            'r2_seasonal_s1':  model_params_out['ridge_r2_s1'].get('Total Revenue', 0),
            'r2_media_s2':     model_params_out['ridge_r2_s2'].get('Total Revenue', 0),
            'media_share_pct': model_params_out['media_share_pct'],
        },
        'optimization': {
            'current_response':   round(current_response, 2),
            'optimal_response':   round(optimal_response, 2),
            'lift_pct':           round(lift_pct, 2),
            'converged':          converged,
            'current_allocation': {ch: round(v, 2) for ch, v in current_spend.items()},
            'optimal_allocation': {ch: round(v, 2) for ch, v in optimal_alloc.items()},
        },
    }

    # ── Upload to gold ────────────────────────────────────────────────────────
    log.info('\n  Uploading to gold...')
    upload_csv(client,  gold, f'{gold_dir}media_effectiveness_results.csv', eff_df)
    upload_csv(client,  gold, f'{gold_dir}mmm_optimization_results.csv',    opt_df)
    upload_csv(client,  gold, f'{gold_dir}mmm_scenario_analysis.csv',       scenario_df)
    upload_csv(client,  gold, f'{gold_dir}mmm_executive_summary.csv',       summary_df)
    upload_json(client, gold, f'{gold_dir}causal_model_params.json',        model_params_out)
    upload_json(client, gold, f'{gold_dir}mmm_final_output.json',           mmm_final)

    log.info('\n' + '=' * 65)
    log.info('✅  Silver → Gold complete')
    log.info(f'    R² full      : {model_params_out["ridge_r2_full"].get("Total Revenue", 0):.3f}')
    log.info(f'    R² seasonal  : {model_params_out["ridge_r2_s1"].get("Total Revenue", 0):.3f}')
    log.info(f'    R² media     : {model_params_out["ridge_r2_s2"].get("Total Revenue", 0):.3f}')
    log.info(f'    Media share  : {model_params_out["media_share_pct"]:.1f}%')
    log.info(f'    Optim. lift  : {lift_pct:+.1f}%')
    log.info('=' * 65)


if __name__ == '__main__':
    main()