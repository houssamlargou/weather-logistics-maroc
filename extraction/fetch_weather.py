import requests
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

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

fee = fetch_city_weather(52.52, -13.41)
print(fee)