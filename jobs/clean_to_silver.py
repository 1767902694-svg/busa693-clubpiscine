# Data Cleaning - Club Piscine MMM
# Bronze (raw excel) -> Silver (processed csv + pkl)

import os
import io
import re
import warnings
from pathlib import Path
import pickle

import pandas as pd
import numpy as np
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import ContentSettings

warnings.filterwarnings("ignore")

# Display options
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", 100)
pd.set_option("display.width", None)

# =========================
# Azure Storage (Bronze/Silver)
# =========================
STORAGE_ACCOUNT = os.environ.get("STORAGE_ACCOUNT", "mcgillclubpiscine")
BRONZE_CONTAINER = os.environ.get("BRONZE_CONTAINER", "bronze")
SILVER_CONTAINER = os.environ.get("SILVER_CONTAINER", "silver")

# Optional: keep the same names as in Bronze. These match your screenshot.
BRONZE_FILES = {
    "soumissions_2024": os.environ.get("BRONZE_SOUMISSIONS_2024", "Rapport de soumissions 2024.xlsx"),
    "soumissions_2025": os.environ.get("BRONZE_SOUMISSIONS_2025", "+Rapport de soumissions 2025.xlsx"),
    "budget_2024": os.environ.get("BRONZE_BUDGET_2024", "Budget 2024 - REEL au 5 novembre.xlsx"),
    "budget_2025": os.environ.get("BRONZE_BUDGET_2025", "Budget 2025 - 21 août.xlsx"),
    "tableau_2025": os.environ.get("BRONZE_TABLEAU_2025", "Recap_Tableau_Medias_2025.xlsx"),
    "calendrier": os.environ.get("BRONZE_CALENDRIER", "CalendrierFiscal.xlsx"),
}

def _blob_service_client() -> BlobServiceClient:
    url = f"https://{STORAGE_ACCOUNT}.blob.core.windows.net"
    cred = DefaultAzureCredential()
    return BlobServiceClient(account_url=url, credential=cred)

def read_excel_from_bronze(blob_name: str, **read_excel_kwargs) -> pd.DataFrame:
    """
    Download an Excel blob from Bronze and read with pandas.
    """
    bsc = _blob_service_client()
    bronze = bsc.get_container_client(BRONZE_CONTAINER)
    data = bronze.get_blob_client(blob_name).download_blob().readall()
    return pd.read_excel(io.BytesIO(data), **read_excel_kwargs)

def upload_bytes_to_silver(blob_path: str, content: bytes, content_type: str | None = None) -> None:
    """
    Upload raw bytes to Silver.
    """
    bsc = _blob_service_client()
    silver = bsc.get_container_client(SILVER_CONTAINER)
    blob_client = silver.get_blob_client(blob_path)

    if content_type:
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
    else:
        blob_client.upload_blob(
            content,
            overwrite=True
        )
def save_df_to_silver_csv(df: pd.DataFrame, blob_path: str) -> None:
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    upload_bytes_to_silver(blob_path, csv_bytes, content_type="text/csv")

def save_df_to_silver_pickle(df, blob_path: str) -> None:
    """
    Save dataframe as a pickle file into Silver container.
    """
    pkl_bytes = pickle.dumps(df)
    upload_bytes_to_silver(blob_path, pkl_bytes, content_type="application/octet-stream")

def list_bronze_files() -> None:
    bsc = _blob_service_client()
    bronze = bsc.get_container_client(BRONZE_CONTAINER)
    print("\nBronze blobs (first 50):")
    count = 0
    for blob in bronze.list_blobs():
        print(f"  - {blob.name}")
        count += 1
        if count >= 50:
            break

print(f"Storage account: {STORAGE_ACCOUNT}")
print(f"Bronze container: {BRONZE_CONTAINER}")
print(f"Silver container: {SILVER_CONTAINER}")
list_bronze_files()

# ============================================================
# 1. Rapport de Soumissions (Quote Requests) - 2024 & 2025
# ============================================================

def clean_soumissions(blob_name, year, start_row, end_row):
    """
    Clean the Rapport de Soumissions file.

    Extracts monthly quote data from the RECAP sheet.
    """
    df_raw = read_excel_from_bronze(blob_name, sheet_name="RECAP", header=None)

    months = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]

    data = []
    for i, row_idx in enumerate(range(start_row, end_row)):
        if i < len(months):
            row_data = {
                "year": year,
                "month": months[i],
                "month_num": i + 1,
                "piscines_hors_terre": df_raw.iloc[row_idx, 2],  # Column C
                "piscines_creusees": df_raw.iloc[row_idx, 6],    # Column G
                "spas": df_raw.iloc[row_idx, 10],                # Column K
            }

            if year == 2025:
                row_data["autres_produits"] = df_raw.iloc[row_idx, 18]  # Column S
                row_data["services"] = df_raw.iloc[row_idx, 22]         # Column W
                row_data["autre"] = df_raw.iloc[row_idx, 26]            # Column AA
            else:  # 2024
                row_data["autres_produits"] = df_raw.iloc[row_idx, 14]  # Column O
                row_data["services"] = df_raw.iloc[row_idx, 18]         # Column S
                row_data["autre"] = df_raw.iloc[row_idx, 22]            # Column W

            data.append(row_data)

    df_clean = pd.DataFrame(data)

    numeric_cols = [
        "piscines_hors_terre", "piscines_creusees", "spas",
        "autres_produits", "services", "autre"
    ]

    for col in numeric_cols:
        if col in df_clean.columns:
            df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    main_cols = ["piscines_hors_terre", "piscines_creusees", "spas"]
    df_clean["total_main_quotes"] = df_clean[main_cols].sum(axis=1, skipna=True)
    df_clean["total_all_quotes"] = df_clean[numeric_cols].sum(axis=1, skipna=True)

    return df_clean

soumissions_2024 = clean_soumissions(
    BRONZE_FILES["soumissions_2024"], year=2024, start_row=17, end_row=29
)

soumissions_2025 = clean_soumissions(
    BRONZE_FILES["soumissions_2025"], year=2025, start_row=20, end_row=32
)

soumissions_combined = pd.concat([soumissions_2024, soumissions_2025], ignore_index=True)

print("=" * 70)
print("SOUMISSIONS COMBINED")
print("=" * 70)
print(soumissions_combined.head(5).to_string(index=False))
print(f"\nMissing values: {soumissions_combined.isna().sum().to_dict()}")

# ============================================================
# 2. Budget Media Spend - 2024 & 2025
# ============================================================

def clean_budget(blob_name, year):
    df_raw = read_excel_from_bronze(blob_name, sheet_name=0, header=None)

    exclude_patterns = ["PROGRAMMATIQUE", "AUDIO ET PODCAST", "ENVOIS POSTAUX"]
    social_media_patterns = ["FACEBOOK", "INSTAGRAM", "PINTEREST", "TIKTOK"]

    skip_exact = ["FR", "EN", "TRADITIONNEL", "NUMÉRIQUE", "AUTRES"]
    skip_contains = [
        "TOTAL", "DIFFÉRENCE", "% VS",
        "SEMAINE", "CAMPAGNE", "MEDIA", "COOP", "PRODUCTION", "RÉSERVE",
        "CONTINGENCE", "CIRCULAIRE PAPIER",
        "RECHERCHE DE MOTS CLÉS",
        "PREROLL - YOUTUBE",
    ]

    months_info = [
        ("NOVEMBRE", 11), ("DECEMBRE", 12), ("JANVIER", 1), ("FEVRIER", 2),
        ("MARS", 3), ("AVRIL", 4), ("MAI", 5), ("JUIN", 6),
        ("JUILLET", 7), ("AOUT", 8), ("SEPTEMBRE", 9), ("OCTOBRE", 10),
    ]

    row6 = df_raw.iloc[6, :].tolist()
    month_cols = {}
    for i, val in enumerate(row6[:70]):
        if pd.notna(val):
            val_upper = str(val).upper().strip()
            for month_name, month_num in months_info:
                if val_upper == month_name and month_name not in month_cols:
                    month_cols[month_name] = (i, month_num)
                    break

    print(f"  Found {len(month_cols)} months for {year}")
    data_rows = list(range(10, 37))

    media_data = []
    for row_idx in data_rows:
        media_name = df_raw.iloc[row_idx, 3]  # Column D
        if pd.isna(media_name) or not str(media_name).strip():
            continue

        media_name_str = str(media_name).strip()
        media_name_upper = media_name_str.upper()

        if media_name_upper in skip_exact:
            continue
        if any(skip in media_name_upper for skip in skip_contains):
            continue
        if year == 2024 and media_name_upper == "BANNIÈRES WEB":
            continue
        if any(excl.upper() in media_name_upper for excl in exclude_patterns):
            continue

        if any(sm.upper() in media_name_upper for sm in social_media_patterns):
            channel_category = "SOCIAL MEDIA"
        elif "GOOGLE" in media_name_upper and "SHOPPING" not in media_name_upper:
            channel_category = "GOOGLE ADS"
        else:
            channel_category = media_name_upper

        for month_name, (col_idx, month_num) in month_cols.items():
            spend = df_raw.iloc[row_idx, col_idx]
            spend_value = pd.to_numeric(spend, errors="coerce")

            if pd.notna(spend_value) and spend_value != 0:
                media_data.append(
                    {
                        "year": year,
                        "month": month_name,
                        "month_num": month_num,
                        "media_channel": channel_category,
                        "spend": spend_value,
                    }
                )

    df_clean = pd.DataFrame(media_data)
    if df_clean.empty:
        return df_clean

    df_agg = df_clean.groupby(
        ["year", "month", "month_num", "media_channel"], as_index=False
    )["spend"].sum()

    return df_agg

print("Processing Budget 2024...")
budget_2024 = clean_budget(BRONZE_FILES["budget_2024"], 2024)

print("Processing Budget 2025...")
budget_2025 = clean_budget(BRONZE_FILES["budget_2025"], 2025)

budget_combined = pd.concat([budget_2024, budget_2025], ignore_index=True)

# ============================================================
# 3. Tableau Medias 2025 - Campaign Performance
# ============================================================

def clean_tableau_medias(blob_name):
    df_raw = read_excel_from_bronze(blob_name, sheet_name="MASTER-TOTAL", header=0)

    cols_to_extract = {
        1: "date_debut",
        2: "date_fin",
        3: "media_type",
        5: "support",
        11: "cost_net",
        19: "occasions_reel",
        20: "impressions_reel",
        21: "peb_reel",
        27: "vues_completees",
        28: "taux_vues",
        29: "clics_reel",
        30: "taux_clics",
    }

    df_clean = df_raw.iloc[:, list(cols_to_extract.keys())].copy()
    df_clean.columns = list(cols_to_extract.values())

    df_clean = df_clean.dropna(how="all")
    df_clean = df_clean.dropna(subset=["date_debut", "date_fin"], how="all")

    df_clean["date_debut"] = pd.to_datetime(df_clean["date_debut"], errors="coerce")
    df_clean["date_fin"] = pd.to_datetime(df_clean["date_fin"], errors="coerce")

    numeric_cols = [
        "cost_net",
        "occasions_reel",
        "impressions_reel",
        "peb_reel",
        "vues_completees",
        "taux_vues",
        "clics_reel",
        "taux_clics",
    ]
    for col in numeric_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors="coerce")

    df_clean["year"] = df_clean["date_debut"].dt.year
    df_clean["month"] = df_clean["date_debut"].dt.month

    mask = (df_clean["impressions_reel"] > 0) & df_clean["cost_net"].notna()
    df_clean.loc[mask, "cpm_calculated"] = (
        df_clean.loc[mask, "cost_net"] / df_clean.loc[mask, "impressions_reel"]
    ) * 1000

    df_clean = df_clean.reset_index(drop=True)
    return df_clean

tableau_medias = clean_tableau_medias(BRONZE_FILES["tableau_2025"])

# ============================================================
# 4. Calendrier Fiscal (Fiscal Calendar)
# ============================================================

def clean_calendrier_fiscal(blob_name):
    df_raw = read_excel_from_bronze(blob_name, sheet_name="CalendrierFiscal", header=0)

    columns_to_keep = [
        "Date",
        "Année",
        "Mois",
        "Nom Mois",
        "Jour de la semaine",
        "Année fiscale",
        "Trimestre",
        "Semaine fiscale",
        "Formule",
        "Semaine débutant le",
        "Ordre du mois fiscal",
        "Ordre semaine",
        "MoisFiscal",
        "AnnéeNUM",
        "Date début semaine",
    ]

    columns_to_keep = [c for c in columns_to_keep if c in df_raw.columns]
    df_clean = df_raw[columns_to_keep].copy()

    df_clean["Date"] = pd.to_datetime(df_clean["Date"], errors="coerce")
    df_clean = df_clean[df_clean["Année"].isin([2021, 2022, 2023, 2024, 2025, 2026])]
    return df_clean

calendrier_fiscal = clean_calendrier_fiscal(BRONZE_FILES["calendrier"])

# ============================================================
# 5. Save Cleaned DataFrames -> Silver
# ============================================================

# CSV
save_df_to_silver_csv(soumissions_combined, "processed/soumissions_quotes.csv")
save_df_to_silver_csv(budget_combined, "processed/budget_media_spend.csv")
save_df_to_silver_csv(tableau_medias, "processed/tableau_medias_performance.csv")
save_df_to_silver_csv(calendrier_fiscal, "processed/calendrier_fiscal.csv")

# Pickle
save_df_to_silver_pickle(soumissions_combined, "processed/soumissions_quotes.pkl")
save_df_to_silver_pickle(budget_combined, "processed/budget_media_spend.pkl")
save_df_to_silver_pickle(tableau_medias, "processed/tableau_medias_performance.pkl")
save_df_to_silver_pickle(calendrier_fiscal, "processed/calendrier_fiscal.pkl")

print("=" * 60)
print("FILES SAVED TO SILVER")
print("=" * 60)
print("Saved to: silver/processed/")
print("Created:")
print("  - processed/soumissions_quotes.csv / .pkl")
print("  - processed/budget_media_spend.csv / .pkl")
print("  - processed/tableau_medias_performance.csv / .pkl")
print("  - processed/calendrier_fiscal.csv / .pkl")

# ============================================================
# 6. Data Quality Summary
# ============================================================

print("=" * 70)
print("DATA QUALITY SUMMARY")
print("=" * 70)

datasets = {
    "Soumissions (Quotes)": soumissions_combined,
    "Budget (Media Spend)": budget_combined,
    "Tableau Medias": tableau_medias,
    "Calendrier Fiscal": calendrier_fiscal,
}

for name, df in datasets.items():
    print(f"\n{'-' * 40}")
    print(name)
    print(f"{'-' * 40}")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")

    total_cells = df.size
    missing_cells = df.isna().sum().sum()
    missing_pct = (missing_cells / total_cells) * 100
    print(f"  Missing values: {missing_cells:,} ({missing_pct:.1f}%)")

    missing_cols = df.columns[df.isna().any()].tolist()
    if missing_cols:
        print(f"  Columns with NaN: {missing_cols}")

print("\n" + "=" * 70)
print("NOTE: Missing values (NaN) are intentionally preserved as per client")
print("instructions - they represent data that was not available/collected.")
print("=" * 70)
