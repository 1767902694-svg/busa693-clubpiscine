import os
import json
import io
from datetime import datetime, timezone
import requests
import pandas as pd
from azure.storage.blob import BlobServiceClient

# -----------------------------
# Config via env vars
# -----------------------------
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("Missing env var: AZURE_STORAGE_CONNECTION_STRING")

BRONZE_CONTAINER = os.environ.get("BRONZE_CONTAINER", "bronze")
SILVER_CONTAINER = os.environ.get("SILVER_CONTAINER", "silver")

# Optional folder prefix inside containers
BRONZE_PREFIX = os.environ.get("BRONZE_PREFIX", "weather/open-meteo")
SILVER_PREFIX = os.environ.get("SILVER_PREFIX", "weather/open-meteo")

# How many days to fetch (rolling window). Default 14 for robustness
PAST_DAYS = int(os.environ.get("PAST_DAYS", "14"))

# Only Greater Montreal Area per client decision
LOCATIONS = [
    {"name": "Montreal", "key": "montreal", "lat": 45.5017, "lon": -73.5673},
    {"name": "Laval", "key": "laval", "lat": 45.6066, "lon": -73.7124},
    {"name": "Longueuil", "key": "longueuil", "lat": 45.5312, "lon": -73.5181},
]


def utc_ts():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def fetch_open_meteo_daily(lat: float, lon: float, past_days: int):
    """
    Returns raw JSON payload from Open-Meteo daily endpoint.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max",
        "timezone": "America/Toronto",
        "past_days": past_days,
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def to_daily_df(payload: dict, location_key: str, location_name: str) -> pd.DataFrame:
    daily = payload.get("daily", {})
    times = daily.get("time", [])
    if not times:
        return pd.DataFrame()

    df = pd.DataFrame({
        "date": times,
        "temperature_2m_max": daily.get("temperature_2m_max", []),
        "temperature_2m_min": daily.get("temperature_2m_min", []),
        "precipitation_sum": daily.get("precipitation_sum", []),
        "windspeed_10m_max": daily.get("windspeed_10m_max", []),
    })
    df.insert(0, "location_key", location_key)
    df.insert(1, "location_name", location_name)
    return df


def upload_bytes(container_client, blob_name: str, data: bytes, content_type: str):
    bc = container_client.get_blob_client(blob_name)
    bc.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})


def main():
    ts = utc_ts()
    svc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    bronze_cc = svc.get_container_client(BRONZE_CONTAINER)
    silver_cc = svc.get_container_client(SILVER_CONTAINER)

    all_rows = []

    for loc in LOCATIONS:
        print(f"=== {loc['name']} ({loc['key']}) ===")

        payload = fetch_open_meteo_daily(loc["lat"], loc["lon"], PAST_DAYS)

        # Bronze: raw JSON (timestamped)
        bronze_blob = f"{BRONZE_PREFIX}/{loc['key']}/open_meteo_raw_{ts}.json"
        upload_bytes(
            bronze_cc,
            bronze_blob,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json",
        )
        print(f"Uploaded bronze: {bronze_blob}")

        df_loc = to_daily_df(payload, loc["key"], loc["name"])
        if not df_loc.empty:
            all_rows.append(df_loc)

    if not all_rows:
        raise RuntimeError("No daily data returned for any location; silver not written.")

    df_all = pd.concat(all_rows, ignore_index=True)

    # Silver: snapshot + latest
    silver_snapshot = f"{SILVER_PREFIX}/open_meteo_daily_gma_{ts}.csv"
    silver_latest = f"{SILVER_PREFIX}/open_meteo_daily_gma_latest.csv"

    buf = io.StringIO()
    df_all.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    upload_bytes(silver_cc, silver_snapshot, csv_bytes, "text/csv")
    upload_bytes(silver_cc, silver_latest, csv_bytes, "text/csv")

    print(f"\nSUCCESS -> silver snapshot: {silver_snapshot}")
    print(f"SUCCESS -> silver latest:   {silver_latest}")
    print(f"Rows: {len(df_all)}  Cols: {len(df_all.columns)}")


if __name__ == "__main__":
    main()
