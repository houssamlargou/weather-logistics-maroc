from pathlib import Path
import requests
import logging
import pandas as pd
import json
import time
import sys
from tenacity import retry, stop_after_attempt, wait_exponential

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from transformation.clean_cities import load_cities


BRONZE_WEATHER_DIR = BASE_DIR / "data" / "bronze" / "weather"

API_URL = "https://api.open-meteo.com/v1/forecast"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "weather_code",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, max=10))
def fetch_city_weather(latitude, longitude, forecast_days=7):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": ",".join(DAILY_VARS),
        "forecast_days": forecast_days,
        "timezone": "Africa/Casablanca",
    }

    response = requests.get(API_URL, params=params, timeout=15)
    response.raise_for_status()
    data = response.json()

    if "daily" not in data:
        raise ValueError(f"Réponse invalide : {data}")

    return data



def save_json(city, data):
    BRONZE_WEATHER_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = city.replace(" ", "_").replace("/", "_")
    path = BRONZE_WEATHER_DIR / f"{safe_name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def fetch_all_weather(cities: pd.DataFrame):
    total = len(cities)
    ok, fail = 0, 0

    for i, row in cities.iterrows():
        city = row["city"]
        lat = float(row["latitude"])
        lng = float(row["longitude"])

        logger.info(f"[{i+1}/{total}] {city} ({lat}, {lng})")

        try:
            data = fetch_city_weather(lat, lng)
            path = save_json(city, data)
            logger.info(f"✓ saved -> {path.name}")
            ok += 1
        except Exception as e:
            logger.error(f"  ✗ failed: {e}")
            fail += 1

        time.sleep(0.3)  

    logger.info(f"Done. Success: {ok} | Failed: {fail} | Total: {total}")

if __name__ == "__main__":
    cities = load_cities()
    logger.info(f"Loaded {len(cities)} cities")
    fetch_all_weather(cities)