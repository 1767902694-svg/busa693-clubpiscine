import os
import json
import time
import re
import unicodedata
import requests
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient

CITY_COORDS = {
    "Blainville": {"lat": 45.6668, "lon": -73.8825},
    "Drummondville": {"lat": 45.8834, "lon": -72.4824},
    "Sherbrooke": {"lat": 45.4042, "lon": -71.8929},
    "Granby": {"lat": 45.4034, "lon": -72.7323},
    "Laval": {"lat": 45.6066, "lon": -73.7124},
    "Longueuil": {"lat": 45.5312, "lon": -73.5181},
    "Saint-Jérôme": {"lat": 45.7804, "lon": -74.0036},
    "St-Georges-de-Beauce": {"lat": 46.1142, "lon": -70.6745},
    "Victoriaville": {"lat": 46.0581, "lon": -71.9592},
    "Repentigny": {"lat": 45.7422, "lon": -73.4501},
    "Chicoutimi": {"lat": 48.4289, "lon": -71.0684},
    "Trois-Rivières": {"lat": 46.3430, "lon": -72.5433},
    "Val-d'Or": {"lat": 48.0974, "lon": -77.7974},
    "Nepean": {"lat": 45.3464, "lon": -75.7560},
    "Pointe-aux-Trembles": {"lat": 45.6417, "lon": -73.5075},
    "St-Hyacinthe": {"lat": 45.6308, "lon": -72.9560},
    "Sorel-Tracy": {"lat": 46.0418, "lon": -73.1139},
    "Saint-Jean-sur-Richelieu": {"lat": 45.3071, "lon": -73.2626},
    "Saint-Eustache": {"lat": 45.5650, "lon": -73.9050},
    "Gatineau": {"lat": 45.4765, "lon": -75.7013},
    "Joliette": {"lat": 46.0230, "lon": -73.4410},
    "Thetford Mines": {"lat": 46.0936, "lon": -71.3054},
    "St-Constant": {"lat": 45.3668, "lon": -73.5659},
    "Cowansville": {"lat": 45.2001, "lon": -72.7491},
    "Sainte-Agathe-des-Monts": {"lat": 46.0501, "lon": -74.2825},
    "Riviere-du-Loup": {"lat": 47.8350, "lon": -69.5376},
    "Beloeil": {"lat": 45.5668, "lon": -73.1998},
}

import os

CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not conn_str:
    raise ValueError("AZURE_STORAGE_CONNECTION_STRING is not set")
CONTAINER_NAME = "bronze"

service = BlobServiceClient.from_connection_string(CONN_STR)
container = service.get_container_client(CONTAINER_NAME)


def slugify_city(city: str) -> str:
    s = unicodedata.normalize("NFKD", city)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def fetch_daily_json(lat: float, lon: float, target_date: str, max_retries: int = 4) -> dict:
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": target_date,
        "end_date": target_date,
        "hourly": [
            "temperature_2m",
            "precipitation",
            "rain",
            "snowfall",
            "windspeed_10m",
        ],
        "timezone": "America/Toronto",
    }

    for attempt in range(max_retries):
        r = requests.get(url, params=params, timeout=30)

        if r.status_code == 429:
            wait = 2 ** (attempt + 2)
            print(f"Rate limited — waiting {wait}s...")
            time.sleep(wait)
            continue

        r.raise_for_status()
        return r.json()

    raise Exception(f"Failed after {max_retries} retries for lat={lat}, lon={lon}, date={target_date}")


def main():
    # 每天抓昨天，比较稳
    target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Target date: {target_date}")

    for city, coords in CITY_COORDS.items():
        city_slug = slugify_city(city)
        blob_name = f"weather/open-meteo/{city_slug}/{target_date}.json"
        blob_client = container.get_blob_client(blob_name)

        if blob_client.exists():
            print(f"Skip existing: {blob_name}")
            continue

        try:
            payload = fetch_daily_json(coords["lat"], coords["lon"], target_date)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            blob_client.upload_blob(body, overwrite=False)
            print(f"Uploaded: {blob_name}")
        except Exception as e:
            print(f"Failed for {city}: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main()