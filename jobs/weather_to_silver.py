"""
weather_to_silver.py
Weather ingestion job for ClubPiscine MMM.

Direct conversion of NB04 (04_external_data.ipynb).

Reads sales_spend_merged.csv from silver, fetches historical weather
from Open-Meteo API (free, no API key), merges them, and writes
sales_spend_weather.csv back to silver.

Run AFTER clean_to_silver and BEFORE silver_to_gold.

Silver input  (silver/Mix_Media_Modeling/processed/):
  sales_spend_merged.csv

Silver output (silver/Mix_Media_Modeling/processed/):
  sales_spend_weather.csv

Environment variables required:
  AZURE_STORAGE_ACCOUNT_NAME
  AZURE_STORAGE_ACCOUNT_KEY
  SILVER_CONTAINER   (default: silver)
  SILVER_INPUT_DIR   (default: Mix_Media_Modeling/processed/)
"""

import io
import os
import logging
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from azure.storage.blob import BlobServiceClient

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# Montreal GMA coordinates (NB04)
LATITUDE      = 45.55
LONGITUDE     = -73.70
START_DATE    = "2022-11-01"   # FY2023 start


# Azure helpers

def get_client():
    name = os.environ['AZURE_STORAGE_ACCOUNT_NAME']
    key  = os.environ['AZURE_STORAGE_ACCOUNT_KEY']
    conn = (f"DefaultEndpointsProtocol=https;AccountName={name};"
            f"AccountKey={key};EndpointSuffix=core.windows.net")
    return BlobServiceClient.from_connection_string(conn)

def download_csv(client, container, path):
    log.info(f'  down  {container}/{path}')
    raw = client.get_blob_client(container=container, blob=path).download_blob().readall()
    return pd.read_csv(io.BytesIO(raw))

def upload_csv(client, container, path, df):
    data = df.to_csv(index=False).encode('utf-8')
    client.get_blob_client(container=container, blob=path).upload_blob(data, overwrite=True)
    log.info(f'  up    {container}/{path}  ({len(df):,} rows x {df.shape[1]} cols)')


# 1. Fetch weather from Open-Meteo (NB04 Cell 6)

def fetch_weather(start_date, end_date):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude":   LATITUDE,
        "longitude":  LONGITUDE,
        "start_date": start_date,
        "end_date":   end_date,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "sunshine_duration",
        ],
        "timezone": "America/Montreal",
    }
    log.info(f'    Open-Meteo API: {start_date} to {end_date}')
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()['daily']

    df = pd.DataFrame({
        'date':            pd.to_datetime(data['time']),
        'temp_max':        data['temperature_2m_max'],
        'temp_min':        data['temperature_2m_min'],
        'temp_mean':       data['temperature_2m_mean'],
        'precipitation':   data['precipitation_sum'],
        'sunshine_hours':  [s / 3600 if s else 0 for s in data['sunshine_duration']],
    }).fillna(0)

    log.info(f'    Fetched {len(df):,} daily records')
    return df


# 2. Derive daily features (NB04 Cell 8)

def add_daily_features(df):
    df = df.copy()
    df['year']      = df['date'].dt.year
    df['month_num'] = df['date'].dt.month

    df['temp_above_15'] = (df['temp_mean'] > 15).astype(int)
    df['temp_above_20'] = (df['temp_mean'] > 20).astype(int)
    df['temp_above_25'] = (df['temp_mean'] > 25).astype(int)
    df['rain_day']      = (df['precipitation'] > 1.0).astype(int)

    df['heating_degree_days'] = (18 - df['temp_mean']).clip(lower=0)
    df['cooling_degree_days'] = (df['temp_mean'] - 18).clip(lower=0)
    df['rolling_temp_7d']     = df['temp_mean'].rolling(7, min_periods=1).mean()
    return df


# 3. Aggregate to monthly (NB04 Cell 11)

def aggregate_to_monthly(df):
    monthly = df.groupby(['year', 'month_num']).agg(
        avg_temp_max=('temp_max', 'mean'),
        avg_temp_min=('temp_min', 'mean'),
        avg_temp_mean=('temp_mean', 'mean'),
        total_precipitation=('precipitation', 'sum'),
        total_sunshine_hours=('sunshine_hours', 'sum'),
        days_above_15=('temp_above_15', 'sum'),
        days_above_20=('temp_above_20', 'sum'),
        days_above_25=('temp_above_25', 'sum'),
        rain_days=('rain_day', 'sum'),
        heating_degree_days=('heating_degree_days', 'sum'),
        cooling_degree_days=('cooling_degree_days', 'sum'),
        rolling_temp_7d_eom=('rolling_temp_7d', 'last'),
    ).reset_index()

    num_cols = monthly.select_dtypes(include=[np.number]).columns
    monthly[num_cols] = monthly[num_cols].round(2)
    log.info(f'    Aggregated to {len(monthly)} monthly rows')
    return monthly


# 4. Quebec holidays (NB04 Cell 13)

def get_quebec_holidays(years):
    try:
        import holidays as holidays_lib
        qc = holidays_lib.Canada(prov='QC', years=years)
        records = []
        for date, name in sorted(qc.items()):
            m = date.month
            if m in [6, 7, 8]:                                                   season = 'peak'
            elif m in [11, 12, 1, 2]:                                            season = 'low'
            elif m == 9 and 'Labour' in name:                                    season = 'pool_closing'
            elif m == 5 and any(k in name for k in ['Victoria','Patriots','Patriotes']): season = 'pool_opening'
            elif m == 10:                                                         season = 'end_season'
            elif m in [3,4] and any(k in name for k in ['Easter','Good Friday','Pâques','Vendredi']): season = 'spring_start'
            else:                                                                 season = 'neutral'
            records.append({'date': pd.Timestamp(date), 'holiday_name': name,
                            'year': date.year, 'month_num': m, 'season_impact': season})
        return pd.DataFrame(records)
    except ImportError:
        log.warning('    python-holidays not installed — holiday features skipped')
        return pd.DataFrame()

def aggregate_holidays_monthly(holidays_df):
    if holidays_df.empty:
        return pd.DataFrame()
    counts = holidays_df.groupby(['year', 'month_num']).size().reset_index(name='n_holidays')
    flags  = holidays_df.pivot_table(
        index=['year', 'month_num'], columns='season_impact',
        aggfunc='size', fill_value=0
    ).reset_index()
    flags.columns = ['year', 'month_num'] + [f'holiday_{c}' for c in flags.columns[2:]]
    monthly = counts.merge(flags, on=['year', 'month_num'], how='outer')
    flag_cols = [c for c in monthly.columns if c.startswith('holiday_')]
    monthly[flag_cols] = (monthly[flag_cols] > 0).astype(int)
    return monthly


# 5. Merge weather + holidays into sales_spend (NB04 Cell 17)

def merge_external_data(sales_spend, weather_monthly, holidays_monthly):
    """
    Fiscal year alignment:
      Nov-Dec of calendar year Y -> fiscal year Y+1
      Jan-Oct of calendar year Y -> fiscal year Y
    """
    sales   = sales_spend.copy()
    weather = weather_monthly.copy()

    weather['fiscal_year'] = weather.apply(
        lambda r: int(r['year']) + 1 if r['month_num'] >= 11 else int(r['year']), axis=1
    )
    sales['year'] = sales['year'].astype(int)

    merged = sales.merge(
        weather.drop(columns=['year']),
        left_on=['year', 'month_num'],
        right_on=['fiscal_year', 'month_num'],
        how='left'
    )
    if 'fiscal_year' in merged.columns:
        merged = merged.drop(columns=['fiscal_year'])

    log.info(f'    After weather merge: {merged.shape[0]} rows x {merged.shape[1]} cols')

    if not holidays_monthly.empty:
        holidays = holidays_monthly.copy()
        holidays['fiscal_year'] = holidays.apply(
            lambda r: int(r['year']) + 1 if r['month_num'] >= 11 else int(r['year']), axis=1
        )
        merged = merged.merge(
            holidays.drop(columns=['year']),
            left_on=['year', 'month_num'],
            right_on=['fiscal_year', 'month_num'],
            how='left'
        )
        if 'fiscal_year' in merged.columns:
            merged = merged.drop(columns=['fiscal_year'])
        hcols = [c for c in merged.columns if c.startswith('holiday_')]
        merged[hcols] = merged[hcols].fillna(0).astype(int)
        if 'n_holidays' in merged.columns:
            merged['n_holidays'] = merged['n_holidays'].fillna(0).astype(int)
        log.info(f'    After holiday merge: {merged.shape[0]} rows x {merged.shape[1]} cols')

    missing = merged[[c for c in merged.columns if 'temp' in c or 'sunshine' in c]].isna().sum().sum()
    if missing > 0:
        log.warning(f'    {missing} missing weather values — check date coverage')
    else:
        log.info('    No missing weather values')

    return merged


# MAIN

def main():
    log.info('=' * 60)
    log.info('ClubPiscine MMM  -  Weather to Silver')
    log.info('=' * 60)

    silver     = os.environ.get('SILVER_CONTAINER', 'silver')
    silver_dir = os.environ.get('SILVER_INPUT_DIR',
                                'Mix_Media_Modeling/processed/').rstrip('/') + '/'

    client = get_client()
    log.info(f'Account : {os.environ["AZURE_STORAGE_ACCOUNT_NAME"]}')

    # 1. Load sales_spend_merged
    log.info('\n[1/5] Loading sales_spend_merged.csv')
    sales_spend = download_csv(client, silver, f'{silver_dir}sales_spend_merged.csv')
    sales_spend['date'] = pd.to_datetime(sales_spend['date'], errors='coerce')
    log.info(f'    Shape: {sales_spend.shape}  |  FYs: {sorted(sales_spend["year"].unique())}')

    # 2. Fetch weather
    log.info('\n[2/5] Fetching weather from Open-Meteo API')
    end_date      = min(datetime.now(), datetime(2025, 10, 31)).strftime('%Y-%m-%d')
    weather_daily = fetch_weather(START_DATE, end_date)
    weather_daily = add_daily_features(weather_daily)

    # 3. Aggregate to monthly
    log.info('\n[3/5] Aggregating to monthly')
    weather_monthly = aggregate_to_monthly(weather_daily)

    # 4. Holidays
    log.info('\n[4/5] Quebec holiday calendar')
    fiscal_years     = sorted(sales_spend['year'].unique())
    calendar_years   = list(range(min(fiscal_years) - 1, max(fiscal_years) + 1))
    holidays_df      = get_quebec_holidays(calendar_years)
    holidays_monthly = aggregate_holidays_monthly(holidays_df)
    if not holidays_monthly.empty:
        log.info(f'    {len(holidays_df)} holiday records')

    # 5. Merge and upload
    log.info('\n[5/5] Merging and uploading')
    result = merge_external_data(sales_spend, weather_monthly, holidays_monthly)

    upload_csv(client, silver, f'{silver_dir}sales_spend_weather.csv', result)

    log.info('\n' + '=' * 60)
    log.info('Done  -  Weather to Silver complete')
    log.info(f'    Output: {result.shape[0]} rows x {result.shape[1]} cols')
    log.info('=' * 60)


if __name__ == '__main__':
    main()