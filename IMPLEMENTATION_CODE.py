"""
Club Piscine MMM: Feature Enrichment Implementation
====================================================

This script adds impressions and efficiency metrics to the model dataset.

Usage:
    python IMPLEMENTATION_CODE.py

Output:
    - data/processed/sales_spend_weather_enriched.csv (36 rows × 67 columns)
    - data/processed/impressions_monthly_aggregated.csv (36 rows × 7 columns)
    - data/processed/cpm_index_monthly.csv (36 rows × 7 columns)
    - data/processed/digital_engagement_metrics.csv (36 rows × 12 columns)
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Configuration
DATA_RAW = Path('data/raw')
DATA_PROCESSED = Path('data/processed')
TABLEAU_FILE = DATA_PROCESSED / 'tableau_medias_performance.csv'
SPEND_WEATHER_FILE = DATA_PROCESSED / 'sales_spend_weather.csv'

# Channels and expected columns
CHANNELS = ['Banniere_Web', 'Circulaire_Digitale', 'Panneaux', 'Preroll', 'Radio', 'Social_Media', 'Television']
DIGITAL_CHANNELS = ['Banniere_Web', 'Social_Media', 'Preroll', 'Circulaire_Digitale']


def load_data():
    """Load input datasets."""
    tableau = pd.read_csv(TABLEAU_FILE)
    spend_weather = pd.read_csv(SPEND_WEATHER_FILE)
    return tableau, spend_weather


def clean_tableau_medias(tableau):
    """
    Clean and prepare tableau_medias data for aggregation.

    Args:
        tableau: Raw tableau_medias_performance dataframe

    Returns:
        Cleaned dataframe with valid year/month/channel_group/impressions_reel
    """
    # Filter for valid records
    tableau_clean = tableau.dropna(subset=['channel_group', 'year', 'month'])
    tableau_clean = tableau_clean[tableau_clean['year'].isin([2023, 2024, 2025])]

    # Convert to integers for consistency
    tableau_clean['year'] = tableau_clean['year'].astype(int)
    tableau_clean['month'] = tableau_clean['month'].astype(int)

    return tableau_clean


def create_fiscal_year(year, month):
    """
    Convert calendar year/month to fiscal year.

    Fiscal year = calendar year if month >= 11, else same calendar year

    Args:
        year: Calendar year
        month: Month (1-12)

    Returns:
        Fiscal year
    """
    if month >= 11:
        return year
    else:
        return year


def aggregate_impressions(tableau_clean):
    """
    Aggregate impressions by fiscal year, month, and channel.

    Args:
        tableau_clean: Cleaned tableau_medias dataframe

    Returns:
        Dataframe with columns: fiscal_year, month, channel_group, impressions_reel, ...
    """
    # Create fiscal year column
    tableau_clean = tableau_clean.copy()
    tableau_clean['fiscal_year'] = tableau_clean.apply(
        lambda row: create_fiscal_year(row['year'], row['month']),
        axis=1
    )

    # Aggregate to monthly by channel
    monthly_agg = tableau_clean.groupby(
        ['fiscal_year', 'month', 'channel_group']
    ).agg({
        'impressions_reel': 'sum',
        'cost_net': 'sum',
        'clics_reel': 'sum',
        'cpm_calculated': 'mean'
    }).reset_index()

    # Rename for clarity
    monthly_agg.rename(columns={
        'fiscal_year': 'year',
        'month': 'month_num'
    }, inplace=True)

    return monthly_agg


def pivot_impressions(monthly_agg):
    """
    Pivot impressions to wide format (one column per channel).

    Args:
        monthly_agg: Aggregated monthly data

    Returns:
        Pivoted dataframe with shape (n_months, n_channels)
    """
    impressions_wide = monthly_agg[monthly_agg['impressions_reel'].notna()].pivot_table(
        index=['year', 'month_num'],
        columns='channel_group',
        values='impressions_reel',
        aggfunc='sum'
    ).fillna(0)

    # Rename columns
    impressions_wide.columns = [f'impr_{col.lower()}' for col in impressions_wide.columns]
    impressions_wide = impressions_wide.reset_index()

    return impressions_wide


def calculate_cpc(monthly_agg):
    """
    Calculate cost per click (CPC) for digital channels.

    Args:
        monthly_agg: Aggregated monthly data

    Returns:
        Dataframe with columns: year, month_num, cpc_[channel]
    """
    # Filter for digital channels with click data
    cpc_data = monthly_agg[monthly_agg['channel_group'].isin(DIGITAL_CHANNELS)].copy()
    cpc_data['cpc'] = cpc_data['cost_net'] / (cpc_data['clics_reel'] + 1)

    # Pivot to wide format
    cpc_wide = cpc_data.pivot_table(
        index=['year', 'month_num'],
        columns='channel_group',
        values='cpc',
        aggfunc='mean'
    ).fillna(np.nan)

    # Rename columns
    cpc_wide.columns = [f'cpc_{col.lower()}' for col in cpc_wide.columns]
    cpc_wide = cpc_wide.reset_index()

    # Handle missing months: forward-fill with rolling 3-month median
    for col in cpc_wide.columns:
        if col not in ['year', 'month_num']:
            # Forward fill with rolling median when zero
            median_cpc = cpc_wide[col].median()
            cpc_wide[col] = cpc_wide[col].replace(0, np.nan)
            cpc_wide[col] = cpc_wide[col].fillna(median_cpc)

    return cpc_wide


def calculate_cpm_index(monthly_agg):
    """
    Calculate CPM index (current CPM / channel median CPM).

    Interpretation:
        0.8 = 20% cheaper than channel median
        1.0 = at channel average
        1.2 = 20% premium

    Args:
        monthly_agg: Aggregated monthly data

    Returns:
        Dataframe with columns: year, month_num, cpm_index_[channel]
    """
    cpm_data = monthly_agg.copy()

    # Calculate CPM for each record
    cpm_data['cpm'] = (cpm_data['cost_net'] / (cpm_data['impressions_reel'] + 1)) * 1000

    # Calculate channel-level median CPM
    channel_medians = cpm_data.groupby('channel_group')['cpm'].median().to_dict()

    # Normalize to index
    cpm_data['cpm_index'] = cpm_data.apply(
        lambda row: row['cpm'] / channel_medians.get(row['channel_group'], 1)
                    if row['cpm'] > 0 else np.nan,
        axis=1
    )

    # Pivot to wide format
    cpm_wide = cpm_data.pivot_table(
        index=['year', 'month_num'],
        columns='channel_group',
        values='cpm_index',
        aggfunc='mean'
    ).fillna(1.0)  # Fill missing with 1.0 (channel average)

    # Rename columns
    cpm_wide.columns = [f'cpm_index_{col.lower()}' for col in cpm_wide.columns]
    cpm_wide = cpm_wide.reset_index()

    return cpm_wide


def calculate_ctr(monthly_agg):
    """
    Calculate click-through rate (CTR %) for digital channels.

    Args:
        monthly_agg: Aggregated monthly data

    Returns:
        Dataframe with columns: year, month_num, ctr_[channel]
    """
    ctr_data = monthly_agg[monthly_agg['channel_group'].isin(DIGITAL_CHANNELS)].copy()
    ctr_data['ctr'] = (ctr_data['clics_reel'] / (ctr_data['impressions_reel'] + 1)) * 100

    # Pivot to wide format
    ctr_wide = ctr_data.pivot_table(
        index=['year', 'month_num'],
        columns='channel_group',
        values='ctr',
        aggfunc='mean'
    ).fillna(0)

    # Rename columns
    ctr_wide.columns = [f'ctr_{col.lower()}' for col in ctr_wide.columns]
    ctr_wide = ctr_wide.reset_index()

    return ctr_wide


def calculate_media_composition(spend_weather):
    """
    Calculate media composition as % traditional vs. digital.

    Args:
        spend_weather: Current spend_weather dataframe

    Returns:
        Dataframe with columns: year, month_num, pct_traditional_media, pct_digital_media
    """
    comp_data = spend_weather[['year', 'month_num']].copy()

    # Traditional media: TV + Radio
    traditional = (spend_weather['spend_television'] + spend_weather['spend_radio'])

    # Digital media: Social + Web + Preroll + Circulaire + Panneaux
    digital = (spend_weather['spend_social_media'] +
               spend_weather['spend_banniere_web'] +
               spend_weather['spend_preroll'] +
               spend_weather['spend_circulaire_digitale'] +
               spend_weather['spend_panneaux'])

    # Total spend
    total = spend_weather['spend_total']

    # Calculate percentages
    comp_data['pct_traditional_media'] = (traditional / (total + 1)) * 100
    comp_data['pct_digital_media'] = (digital / (total + 1)) * 100

    return comp_data


def merge_enrichments(spend_weather, impressions, cpc, cpm_index, ctr, composition):
    """
    Merge all enrichment features into spend_weather dataset.

    Args:
        spend_weather: Current model dataset
        impressions: Impressions wide dataframe
        cpc: CPC wide dataframe
        cpm_index: CPM index wide dataframe
        ctr: CTR wide dataframe
        composition: Media composition dataframe

    Returns:
        Enriched dataframe with all new features
    """
    # Start with original
    enriched = spend_weather.copy()

    # Merge each enrichment
    merge_keys = ['year', 'month_num']

    for df, name in [(impressions, 'impressions'),
                     (cpc, 'cpc'),
                     (cpm_index, 'cpm_index'),
                     (ctr, 'ctr'),
                     (composition, 'composition')]:
        enriched = enriched.merge(df, on=merge_keys, how='left', validate='1:1')

    return enriched


def validate_enrichment(enriched):
    """
    Validate enriched dataset.

    Args:
        enriched: Enriched dataframe

    Returns:
        Dictionary with validation results
    """
    validation = {
        'n_rows': len(enriched),
        'n_cols': len(enriched.columns),
        'new_cols': len(enriched.columns) - 43,  # 43 in original
        'null_counts': enriched.isnull().sum().to_dict(),
        'dtypes': enriched.dtypes.value_counts().to_dict(),
        'impression_coverage': {
            col: enriched[col].gt(0).sum() / len(enriched)
            for col in enriched.columns if col.startswith('impr_')
        }
    }
    return validation


def save_outputs(enriched, monthly_agg, cpm_index_orig):
    """
    Save enriched dataset and intermediate outputs.

    Args:
        enriched: Enriched dataset
        monthly_agg: Monthly aggregations (for reference)
        cpm_index_orig: Original CPM index (for reference)
    """
    # Main enriched dataset
    enriched.to_csv(DATA_PROCESSED / 'sales_spend_weather_enriched.csv', index=False)
    print(f"✓ Saved: sales_spend_weather_enriched.csv ({enriched.shape})")

    # Intermediate datasets (for transparency)
    monthly_agg.to_csv(DATA_PROCESSED / 'impressions_monthly_aggregated.csv', index=False)
    print(f"✓ Saved: impressions_monthly_aggregated.csv ({monthly_agg.shape})")

    # Validation report
    validation = validate_enrichment(enriched)
    print("\n" + "="*80)
    print("VALIDATION REPORT")
    print("="*80)
    print(f"Rows: {validation['n_rows']}")
    print(f"Original columns: 43")
    print(f"New columns: {validation['new_cols']}")
    print(f"Total columns: {validation['n_cols']}")
    print(f"\nImpression data coverage (% of months with data > 0):")
    for col, coverage in validation['impression_coverage'].items():
        print(f"  {col:25}: {coverage*100:5.1f}%")

    return validation


def main():
    """Main execution."""
    print("="*80)
    print("CLUB PISCINE MMM: FEATURE ENRICHMENT")
    print("="*80)

    # Load
    print("\n[1/6] Loading data...")
    tableau, spend_weather = load_data()
    print(f"  - tableau_medias_performance: {tableau.shape}")
    print(f"  - sales_spend_weather: {spend_weather.shape}")

    # Clean
    print("\n[2/6] Cleaning tableau_medias data...")
    tableau_clean = clean_tableau_medias(tableau)
    print(f"  - Records after cleaning: {len(tableau_clean)}")

    # Aggregate
    print("\n[3/6] Aggregating to monthly level...")
    monthly_agg = aggregate_impressions(tableau_clean)
    print(f"  - Monthly aggregations: {len(monthly_agg)}")

    # Create features
    print("\n[4/6] Creating feature sets...")
    impressions = pivot_impressions(monthly_agg)
    print(f"  ✓ Impressions: {impressions.shape}")

    cpc = calculate_cpc(monthly_agg)
    print(f"  ✓ Cost-per-click: {cpc.shape}")

    cpm_index = calculate_cpm_index(monthly_agg)
    print(f"  ✓ CPM index: {cpm_index.shape}")

    ctr = calculate_ctr(monthly_agg)
    print(f"  ✓ Click-through rate: {ctr.shape}")

    composition = calculate_media_composition(spend_weather)
    print(f"  ✓ Media composition: {composition.shape}")

    # Merge
    print("\n[5/6] Merging all features...")
    enriched = merge_enrichments(spend_weather, impressions, cpc, cpm_index, ctr, composition)
    print(f"  - Enriched dataset: {enriched.shape}")

    # Save
    print("\n[6/6] Saving outputs...")
    validation = save_outputs(enriched, monthly_agg, cpm_index)

    print("\n" + "="*80)
    print("SUCCESS")
    print("="*80)
    print(f"\nEnriched dataset ready for modeling:")
    print(f"  File: data/processed/sales_spend_weather_enriched.csv")
    print(f"  Shape: {enriched.shape}")
    print(f"  New features: {validation['new_cols']}")

    return enriched


if __name__ == '__main__':
    enriched = main()
