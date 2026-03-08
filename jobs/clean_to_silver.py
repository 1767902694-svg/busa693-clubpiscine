"""
clean_to_silver.py
Bronze → Silver cleaning job for ClubPiscine MMM.

Direct conversion of NB02 (02_data_cleaning.ipynb).
Reads 9 raw Excel files from Azure Blob (bronze container),
cleans them, and writes CSVs to silver container.

Bronze inputs  (bronze/Mix_Media_Modeling/):
  - Historical sales by store and by division for 2023-2024-2025.xlsx
  - Budget 2023 .xlsx
  - Budget 2024 - REEL au 5 novembre.xlsx
  - Budget 2025 - 21 août.xlsx
  - Preroll 2025.xlsx
  - Recap_Tableau_Medias_2025.xlsx
  - CalendrierFiscal.xlsx
  - Rapport de soumissions 2024.xlsx
  - Rapport de soumissions 2025.xlsx

Silver outputs (silver/Mix_Media_Modeling/processed/):
  - sales_data.csv
  - budget_media_spend.csv
  - budget_media_spend_wide.csv
  - tableau_medias_performance.csv
  - calendrier_fiscal.csv
  - soumissions_2024.csv
  - soumissions_2025.csv
  - sales_spend_merged.csv

Environment variables required:
  AZURE_STORAGE_ACCOUNT_NAME
  AZURE_STORAGE_ACCOUNT_KEY
  BRONZE_CONTAINER      (default: bronze)
  SILVER_CONTAINER      (default: silver)
  BRONZE_INPUT_DIR      (default: Mix_Media_Modeling/)
  SILVER_OUTPUT_DIR     (default: Mix_Media_Modeling/processed/)
"""

import io
import os
import logging
import warnings

import pandas as pd
import numpy as np
from azure.storage.blob import BlobServiceClient

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


# ─── Azure helpers ─────────────────────────────────────────────────────────────

def get_client():
    name = os.environ['AZURE_STORAGE_ACCOUNT_NAME']
    key  = os.environ['AZURE_STORAGE_ACCOUNT_KEY']
    conn = (f"DefaultEndpointsProtocol=https;AccountName={name};"
            f"AccountKey={key};EndpointSuffix=core.windows.net")
    return BlobServiceClient.from_connection_string(conn)

def download(client, container, path):
    log.info(f'  ↓  {container}/{path}')
    return client.get_blob_client(container=container, blob=path).download_blob().readall()

def upload_csv(client, container, path, df):
    data = df.to_csv(index=False).encode('utf-8')
    client.get_blob_client(container=container, blob=path).upload_blob(data, overwrite=True)
    log.info(f'  ↑  {container}/{path}  ({len(df):,} rows)')

def read_excel(raw, **kwargs):
    return pd.read_excel(io.BytesIO(raw), **kwargs)


# ─── 1. Sales data (NB02 Cell 2) ───────────────────────────────────────────────

def extract_sales_data(raw):
    """
    Aggregate weekly store-level data → monthly company-level totals.
    6,336 rows × 42 stores → 36 monthly rows.
    6 product categories: HT, CR, SP (units+revenue), ME&GA, FI, BQ (revenue only).
    """
    df = read_excel(raw, sheet_name='Ventes cumulatives par magasin', header=1)
    log.info(f'    Raw sales: {df.shape[0]:,} rows × {df.shape[1]} cols')

    monthly = df.groupby(['Année fiscale', 'Month']).agg({
        'U-HT': 'sum', '$-HT': 'sum',
        'U-CR': 'sum', '$-CR': 'sum',
        'U-SP': 'sum', '$-SP': 'sum',
        '$-ME & $-GA': 'sum',
        '$-FI': 'sum',
        '$-BQ': 'sum'
    }).reset_index()

    monthly = monthly.rename(columns={
        'Année fiscale':  'year',
        'Month':          'month_num',
        'U-HT':           'piscines_hors_terre_units',
        '$-HT':           'piscines_hors_terre_revenue',
        'U-CR':           'piscines_creusees_units',
        '$-CR':           'piscines_creusees_revenue',
        'U-SP':           'spas_units',
        '$-SP':           'spas_revenue',
        '$-ME & $-GA':    'meubles_gazebo_revenue',
        '$-FI':           'fitness_revenue',
        '$-BQ':           'bbq_revenue'
    })

    monthly['total_all_revenue'] = (
        monthly['piscines_hors_terre_revenue'] +
        monthly['piscines_creusees_revenue'] +
        monthly['spas_revenue'] +
        monthly['meubles_gazebo_revenue'] +
        monthly['fitness_revenue'] +
        monthly['bbq_revenue']
    )
    monthly['total_units'] = (
        monthly['piscines_hors_terre_units'] +
        monthly['piscines_creusees_units'] +
        monthly['spas_units']
    )

    # Derive calendar year from fiscal year + month
    # Nov-Dec of FY X → calendar year X-1; Jan-Oct of FY X → calendar year X
    monthly['calendar_year'] = monthly.apply(
        lambda r: int(r['year']) - 1 if r['month_num'] >= 11 else int(r['year']), axis=1
    )
    monthly['date'] = pd.to_datetime(
        monthly['calendar_year'].astype(str) + '-' +
        monthly['month_num'].astype(str) + '-01'
    )
    monthly = monthly.sort_values('date').reset_index(drop=True)
    monthly['month'] = monthly['month_num'].map({
        1: 'Janvier',   2: 'Février',  3: 'Mars',     4: 'Avril',
        5: 'Mai',       6: 'Juin',     7: 'Juillet',  8: 'Août',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    })

    log.info(f'    → {len(monthly)} monthly rows | FYs: {sorted(monthly["year"].unique())}')
    return monthly


# ─── 2. Budget media spend (NB02 Cell 3) ───────────────────────────────────────

CHANNEL_GROUPS = {
    # 1. Television
    'TELEVISION': 'Television',
    # 2. Radio
    'RADIO': 'Radio',
    'RADIO NUMÉRIQUE': 'Radio',
    # 3. Panneaux
    'PANNEAUX': 'Panneaux',
    'PANNEAUX ET AFFICHAGES NUMÉRIQUES': 'Panneaux',
    # 4. Social Media
    'FACEBOOK': 'Social_Media',
    'FACEBOOK + INSTAGRAM (PROMO)': 'Social_Media',
    'FACEBOOK + INSTAGRAM (PRODUIT)': 'Social_Media',
    'PINTEREST': 'Social_Media',
    'TIKTOK': 'Social_Media',
    # 5. Preroll
    'PREROLL - PREMIUM': 'Preroll',
    'PREROLL - YOUTUBE': 'Preroll',
    # 6. Banniere_Web
    'BANNIÈRES WEB - PREMIUM': 'Banniere_Web',
    'BANNIERES WEB - PREMIUM': 'Banniere_Web',
    'BANNIERES WEB': 'Banniere_Web',
    'BANNIÈRES WEB': 'Banniere_Web',
    'LAPRESSE+': 'Banniere_Web',
    'LAPRESSE (LP+, PREROLL, DISPLAY)': 'Banniere_Web',
    'CONTENU DE MARQUE': 'Banniere_Web',
    # 7. Circulaire Digitale
    'CIRCULAIRE DIGITAL': 'Circulaire_Digitale',
    'CIRCULAIRE DIGITALE': 'Circulaire_Digitale',
}

EXCLUDE = [
    'PROGRAMMATIQUE', 'AUDIO ET PODCAST', 'ENVOIS POSTAUX',
    'COMMANDITES', 'GOOGLE SHOPPING', 'RECHERCHE DE MOTS',
]

SKIP_EXACT = {'FR', 'EN', 'ENG', 'TRADITIONNEL', 'NUMÉRIQUE', 'NUMERIQUE', 'AUTRES'}

SKIP_CONTAINS = [
    'TOTAL', 'DIFFÉRENCE', '% VS',
    'SEMAINE', 'CAMPAGNE', 'MEDIA', 'COOP', 'PRODUCTION', 'RÉSERVE',
    'CONTINGENCE', 'CIRCULAIRE PAPIER',
    'VIDEO ( PORTÉE', 'PERFORMANCE ( SOUMISSIONS',
    'GOOGLE DISPLAY + PREROLL',
]

MONTHS_INFO = [
    ('NOVEMBRE', 11), ('DECEMBRE', 12), ('JANVIER', 1),  ('FEVRIER', 2),
    ('MARS', 3),      ('AVRIL', 4),     ('MAI', 5),       ('JUIN', 6),
    ('JUILLET', 7),   ('AOUT', 8),      ('SEPTEMBRE', 9), ('OCTOBRE', 10),
]


def clean_budget_grouped(raw, year):
    """
    Parse one annual budget Excel file into long-format channel × month data.
    Key fix from NB02: take LAST matching month column (event sub-columns appear
    before the actual monthly total column).
    """
    df_raw = read_excel(raw, sheet_name=0, header=None)

    # Detect month columns from row 6 — take LAST match to skip event sub-columns
    row6 = df_raw.iloc[6, :].tolist()
    month_cols = {}
    for i, val in enumerate(row6[:70]):
        if pd.notna(val):
            v = str(val).upper().strip()
            for mname, mnum in MONTHS_INFO:
                if v == mname:
                    month_cols[mname] = (i, mnum)  # always overwrite → takes last

    log.info(f'    Budget {year}: {len(month_cols)} month columns found')

    media_data = []
    for row_idx in range(10, 42):
        media_name = df_raw.iloc[row_idx, 3]
        if pd.isna(media_name) or not str(media_name).strip():
            continue

        name_u = str(media_name).strip().upper()

        if name_u in SKIP_EXACT:
            continue
        if any(s in name_u for s in SKIP_CONTAINS):
            continue
        if any(e.upper() in name_u for e in EXCLUDE):
            continue

        # Skip plain BANNIÈRES WEB parent row — allow Google Display sub-row (col0='DISPLAY')
        if name_u == 'BANNIÈRES WEB':
            col0 = str(df_raw.iloc[row_idx, 0]).strip().upper() if pd.notna(df_raw.iloc[row_idx, 0]) else ''
            if col0 != 'DISPLAY':
                continue

        # Skip GOOGLE parent rows — use sub-rows to avoid Shopping contamination
        if name_u in ('GOOGLE ADS', 'GOOGLE'):
            continue

        channel = None
        for pattern, group in CHANNEL_GROUPS.items():
            if pattern == name_u or pattern in name_u:
                channel = group
                break
        if channel is None:
            continue

        for mname, (col_idx, mnum) in month_cols.items():
            spend = pd.to_numeric(df_raw.iloc[row_idx, col_idx], errors='coerce')
            if pd.notna(spend) and spend != 0:
                media_data.append({
                    'year': year, 'month': mname, 'month_num': mnum,
                    'channel_group': channel, 'spend': spend
                })

    df = pd.DataFrame(media_data)
    if df.empty:
        log.warning(f'    Budget {year}: no data extracted — check file name/structure')
        return df

    return df.groupby(['year', 'month', 'month_num', 'channel_group'], as_index=False)['spend'].sum()


def load_preroll_breakdown(raw):
    """
    Parse Preroll 2025.xlsx — Google Ads split file.
    Display_Cost → Banniere_Web
    Video_Cost   → Preroll
    Search, Shopping, PerfMax → excluded from MMM
    """
    df = read_excel(raw, header=2)
    df.columns = ['Month', 'Currency', 'Search_Cost', 'Display_Cost',
                  'Shopping_Cost', 'Video_Cost', 'PerfMax_Cost']
    for col in ['Display_Cost', 'Video_Cost']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    mmap = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    mfr = {
        1: 'JANVIER', 2: 'FEVRIER',   3: 'MARS',      4: 'AVRIL',
        5: 'MAI',     6: 'JUIN',      7: 'JUILLET',   8: 'AOUT',
        9: 'SEPTEMBRE', 10: 'OCTOBRE', 11: 'NOVEMBRE', 12: 'DECEMBRE'
    }

    records = []
    for _, row in df.iterrows():
        parts = str(row['Month']).strip().split()
        if len(parts) < 2:
            continue
        mnum = mmap.get(parts[0].lower())
        if mnum is None:
            continue
        cal_year = int(parts[1])
        fy = cal_year + 1 if mnum >= 11 else cal_year
        if row['Display_Cost'] > 0:
            records.append({'year': fy, 'month': mfr[mnum], 'month_num': mnum,
                            'channel_group': 'Banniere_Web', 'spend': row['Display_Cost']})
        if row['Video_Cost'] > 0:
            records.append({'year': fy, 'month': mfr[mnum], 'month_num': mnum,
                            'channel_group': 'Preroll', 'spend': row['Video_Cost']})
    return pd.DataFrame(records)


# ─── 3. Tableau Medias (NB02 Cell 4) ───────────────────────────────────────────

def clean_tableau_medias(raw):
    """Extract campaign-level KPIs from Recap_Tableau_Medias_2025.xlsx"""
    df_raw = read_excel(raw, sheet_name='MASTER-TOTAL', header=0)

    cols = {
        1: 'date_debut', 2: 'date_fin', 3: 'media_type', 5: 'support',
        11: 'cost_net', 19: 'occasions_reel', 20: 'impressions_reel',
        21: 'peb_reel', 27: 'vues_completees', 28: 'taux_vues',
        29: 'clics_reel', 30: 'taux_clics'
    }
    df = df_raw.iloc[:, list(cols.keys())].copy()
    df.columns = list(cols.values())
    df = df.dropna(how='all').dropna(subset=['date_debut', 'date_fin'], how='all')
    df['date_debut'] = pd.to_datetime(df['date_debut'], errors='coerce')
    df['date_fin']   = pd.to_datetime(df['date_fin'],   errors='coerce')

    for col in ['cost_net', 'occasions_reel', 'impressions_reel', 'peb_reel',
                'vues_completees', 'taux_vues', 'clics_reel', 'taux_clics']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    def map_channel(row):
        mt = str(row['media_type']).upper() if pd.notna(row['media_type']) else ''
        sp = str(row['support']).upper()     if pd.notna(row['support'])     else ''
        if mt == 'TÉLÉVISION': return 'Television'
        if mt == 'RADIO':      return 'Radio'
        if mt == 'AFFICHAGE':  return 'Panneaux'
        if mt == 'NUMÉRIQUE':
            if 'CIRCULAIRE' in sp or 'FLIPP' in sp:                                  return 'Circulaire_Digitale'
            if any(x in sp for x in ['FACEBOOK', 'INSTAGRAM', 'PINTEREST', 'TIKTOK']): return 'Social_Media'
            if any(x in sp for x in ['PREROLL', 'YOUTUBE']):                          return 'Preroll'
            return 'Banniere_Web'
        return 'Other'

    df['channel_group'] = df.apply(map_channel, axis=1)
    df['year']  = df['date_debut'].dt.year
    df['month'] = df['date_debut'].dt.month

    mask = (df['impressions_reel'] > 0) & df['cost_net'].notna()
    df.loc[mask, 'cpm_calculated'] = (
        df.loc[mask, 'cost_net'] / df.loc[mask, 'impressions_reel']
    ) * 1000

    log.info(f'    → {len(df):,} campaign rows')
    return df.reset_index(drop=True)


# ─── 4. Calendrier Fiscal (NB02 Cell 5) ────────────────────────────────────────

def clean_calendrier_fiscal(raw):
    """Parse CalendrierFiscal.xlsx fiscal calendar reference table."""
    df = read_excel(raw, sheet_name='CalendrierFiscal', header=0)
    keep = [
        'Date', 'Année', 'Mois', 'Nom Mois', 'Jour de la semaine',
        'Année fiscale', 'Trimestre', 'Semaine fiscale', 'Formule',
        'Semaine débutant le', 'Ordre du mois fiscal', 'Ordre semaine',
        'MoisFiscal', 'AnnéeNUM', 'Date début semaine'
    ]
    df = df[[c for c in keep if c in df.columns]].copy()
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    log.info(f'    → {len(df):,} calendar rows')
    return df


# ─── 5. Rapport de soumissions (new files not in original NB02) ────────────────

def clean_soumissions(raw, label):
    """
    Light cleaning for Rapport de soumissions files.
    Standardises column names and parses date columns.
    Missing values preserved as per client instructions.
    """
    df = read_excel(raw, sheet_name=0, header=0)
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(r'[\s\-\/\(\)]+', '_', regex=True)
        .str.replace(r'[^\w]', '', regex=True)
    )
    for col in df.columns:
        if isinstance(col, str) and ('date' in col or 'semaine' in col):
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                pass
    df = df.dropna(how='all').reset_index(drop=True)
    log.info(f'    → Soumissions {label}: {len(df):,} rows × {df.shape[1]} cols')
    return df


# ─── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    log.info('=' * 60)
    log.info('ClubPiscine MMM  —  Job 1: Bronze → Silver')
    log.info('=' * 60)

    bronze     = os.environ.get('BRONZE_CONTAINER',  'bronze')
    silver     = os.environ.get('SILVER_CONTAINER',  'silver')
    bronze_dir = os.environ.get('BRONZE_INPUT_DIR',  'Mix_Media_Modeling/').rstrip('/') + '/'
    silver_dir = os.environ.get('SILVER_OUTPUT_DIR', 'Mix_Media_Modeling/processed/').rstrip('/') + '/'

    client = get_client()
    log.info(f'Account : {os.environ["AZURE_STORAGE_ACCOUNT_NAME"]}')
    log.info(f'Bronze  : {bronze}/{bronze_dir}')
    log.info(f'Silver  : {silver}/{silver_dir}')

    def dl(name):
        return download(client, bronze, f'{bronze_dir}{name}')

    def dl_opt(name):
        try:
            return dl(name)
        except Exception:
            log.warning(f'  Optional file not found: {name} — skipping')
            return None

    # ── 1. Sales ──────────────────────────────────────────────────────────────
    log.info('\n[1/6] Sales data')
    sales_data = extract_sales_data(
        dl('Historical sales by store and by division for 2023-2024-2025.xlsx')
    )

    # ── 2. Budget media spend ─────────────────────────────────────────────────
    log.info('\n[2/6] Budget media spend')
    b2023 = clean_budget_grouped(dl('Budget 2023 .xlsx'), 2023)
    b2024 = clean_budget_grouped(dl('Budget 2024 - REEL au 5 novembre.xlsx'), 2024)
    b2025 = clean_budget_grouped(dl('Budget 2025 - 21 août.xlsx'), 2025)
    budget_combined = pd.concat([b2023, b2024, b2025], ignore_index=True)

    preroll_raw = dl_opt('Preroll 2025.xlsx')
    if preroll_raw:
        preroll = load_preroll_breakdown(preroll_raw)
        fy25 = preroll[preroll['year'] == 2025]
        budget_combined = pd.concat([budget_combined, fy25], ignore_index=True)
        budget_combined = budget_combined.groupby(
            ['year', 'month', 'month_num', 'channel_group'], as_index=False
        )['spend'].sum()
        log.info(f'    Preroll 2025 integrated ({len(fy25)} rows)')

    # Wide format for merging (NB02 Cell 3b)
    budget_wide = budget_combined.pivot_table(
        index=['year', 'month', 'month_num'],
        columns='channel_group',
        values='spend',
        aggfunc='sum',
        fill_value=0
    ).reset_index()
    budget_wide.columns = (
        ['year', 'month', 'month_num'] +
        [f'spend_{c.lower()}' for c in budget_wide.columns[3:]]
    )
    spend_cols = [c for c in budget_wide.columns if c.startswith('spend_')]
    budget_wide['spend_total'] = budget_wide[spend_cols].sum(axis=1)

    # ── 3. Tableau Medias ─────────────────────────────────────────────────────
    log.info('\n[3/6] Tableau Medias 2025')
    tableau_medias = clean_tableau_medias(dl('Recap_Tableau_Medias_2025.xlsx'))

    # ── 4. Calendrier Fiscal ──────────────────────────────────────────────────
    log.info('\n[4/6] Calendrier Fiscal')
    calendrier_fiscal = clean_calendrier_fiscal(dl('CalendrierFiscal.xlsx'))

    # ── 5. Soumissions ────────────────────────────────────────────────────────
    log.info('\n[5/6] Rapports de soumissions')
    soumissions_2024 = clean_soumissions(dl('Rapport de soumissions 2024.xlsx'), '2024')
    soumissions_2025 = clean_soumissions(dl('Rapport de soumissions 2025.xlsx'), '2025')

    # ── 6. Merge sales + media spend (NB02 Cell 6b) ───────────────────────────
    log.info('\n[6/6] Merging sales + media spend')
    merge_cols = ['year', 'month_num'] + [c for c in budget_wide.columns if c.startswith('spend_')]
    merged = sales_data.merge(budget_wide[merge_cols], on=['year', 'month_num'], how='inner')
    merged['fiscal_month_pos'] = merged['month_num'].apply(
        lambda m: m - 10 if m >= 11 else m + 2
    )
    log.info(f'    → {len(merged):,} merged rows')

    # ── Upload to silver ──────────────────────────────────────────────────────
    log.info('\n  Uploading to silver...')
    outputs = {
        'sales_data.csv':                 sales_data,
        'budget_media_spend.csv':         budget_combined,
        'budget_media_spend_wide.csv':    budget_wide,
        'tableau_medias_performance.csv': tableau_medias,
        'calendrier_fiscal.csv':          calendrier_fiscal,
        'soumissions_2024.csv':           soumissions_2024,
        'soumissions_2025.csv':           soumissions_2025,
        'sales_spend_merged.csv':         merged,
    }
    for filename, df in outputs.items():
        upload_csv(client, silver, f'{silver_dir}{filename}', df)

    log.info('\n' + '=' * 60)
    log.info('✅  Bronze → Silver complete')
    log.info('=' * 60)


if __name__ == '__main__':
    main()