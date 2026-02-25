#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fetch daily weather data from Open-Meteo and upload to Azure Blob Storage (ADLS Gen2 uses same Blob API).

Required env var:
  - AZURE_STORAGE_CONNECTION_STRING

Optional env vars:
  - STORAGE_CONTAINER_NAME        (default: "bronze")
  - STORAGE_BLOB_PREFIX           (default: "weather/open-meteo")
  - OPEN_METEO_TIMEZONE           (default: "America/Toronto")
  - OPEN_METEO_UNITS              (default: "metric")  # metric|imperial (Open-Meteo mostly uses metric params)
  - TARGET_DATE                   (default: today in timezone)  # YYYY-MM-DD
"""

import os
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from azure.storage.blob import BlobServiceClient, ContentSettings


# ----- Config -----
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Montreal / Laval / Longueuil (approx city centers)
CITIES = [
    {"name": "Montreal", "slug": "montreal", "lat": 45.5017, "lon": -73.5673},
    {"name": "Laval", "slug": "laval", "lat": 45.6066, "lon": -73.7124},
    {"name": "Longueuil", "slug": "longueuil", "lat": 45.5312, "lon": -73.5181},
]


def must_get_env(name: str) -> str:
    v = os.getenv(name, "").strip()
    if not v:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return v


def get_target_date_str(tz_name: str) -> str:
    # Allow override
    override = os.getenv("TARGET_DATE", "").strip()
    if override:
        return override
    now = datetime.now(ZoneInfo(tz_name))
    return now.strftime("%Y-%m-%d")


def fetch_open_meteo_daily(lat: float, lon: float, date_str: str, tz_name: str) -> dict:
    """
    Fetch daily weather for the given date.
    Using Open-Meteo archive is also possible, but forecast works for "today/next".
    We request daily aggregates + hourly precipitation/temp/wind (optional).
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": tz_name,
        "start_date": date_str,
        "end_date": date_str,
        # Daily summary fields
        "daily": ",".join(
            [
                "temperature_2m_max",
                "temperature_2m_min",
                "temperature_2m_mean",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum",
                "windspeed_10m_max",
                "windgusts_10m_max",
            ]
        ),
        # Hourly fields (optional, but often useful)
        "hourly": ",".join(
            [
                "temperature_2m",
                "precipitation",
                "rain",
                "snowfall",
                "windspeed_10m",
            ]
        ),
    }

    r = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()

    # Attach metadata
    data["_meta"] = {
        "source": "open-meteo",
        "fetched_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_date": date_str,
        "timezone": tz_name,
        "latitude": lat,
        "longitude": lon,
    }
    return data


def upload_bytes(
    blob_service_client: BlobServiceClient,
    container_name: str,
    blob_name: str,
    content: bytes,
    content_type: str,
) -> None:
    container_client = blob_service_client.get_container_client(container_name)
    # Create container if not exists (safe-ish)
    try:
        container_client.create_container()
    except Exception:
        # If it already exists or cannot create, ignore here; upload will fail if truly not accessible.
        pass

    blob_client = container_client.get_blob_client(blob_name)

    # ✅ FIX: content_settings must be ContentSettings object, not dict
    blob_client.upload_blob(
        content,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
    )


def main() -> int:
    conn_str = must_get_env("AZURE_STORAGE_CONNECTION_STRING")

    container_name = os.getenv("STORAGE_CONTAINER_NAME", "bronze").strip() or "bronze"
    prefix = os.getenv("STORAGE_BLOB_PREFIX", "weather/open-meteo").strip() or "weather/open-meteo"
    tz_name = os.getenv("OPEN_METEO_TIMEZONE", "America/Toronto").strip() or "America/Toronto"

    date_str = get_target_date_str(tz_name)

    svc = BlobServiceClient.from_connection_string(conn_str)

    for c in CITIES:
        name = c["name"]
        slug = c["slug"]
        lat = c["lat"]
        lon = c["lon"]

        print(f"=== {name} ({slug}) ===", flush=True)

        payload = fetch_open_meteo_daily(lat, lon, date_str, tz_name)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        # Example blob path:
        # weather/open-meteo/montreal/2026-02-25.json
        blob_name = f"{prefix}/{slug}/{date_str}.json"

        upload_bytes(
            blob_service_client=svc,
            container_name=container_name,
            blob_name=blob_name,
            content=body,
            content_type="application/json",
        )

        print(f"Uploaded: container={container_name} blob={blob_name}", flush=True)

    print("Done.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        # Make sure the error shows in Container Apps logs
        print("ERROR:", repr(e), file=sys.stderr, flush=True)
        raise
