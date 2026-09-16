import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
import logging
import pandas as pd


BRONZE_WEATHER_DIR = PROJECT_ROOT / "data" / "bronze" / "weather"
SILVER_DIR = PROJECT_ROOT / "data" / "silver"


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def load_raw_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def flatten_city_json(city_file: Path) -> pd.DataFrame:
    data = load_raw_json(city_file)

    city = city_file.stem.replace("_", " ")

    daily = data.get("daily", {})
    if not daily or "time" not in daily:
        logger.warning(f"No daily data in {city_file.name}")
        return pd.DataFrame()

    df = pd.DataFrame(daily)
    df["city"] = city
    return df


def clean_weather(df: pd.DataFrame) -> pd.DataFrame:

    df = df.rename(columns={
        "time": "forecast_date",
        "temperature_2m_max": "temperature_max",
        "temperature_2m_min": "temperature_min",
        "precipitation_sum": "precipitation_sum",
        "precipitation_probability_max": "precipitation_probability_max",
        "wind_speed_10m_max": "wind_speed_max",
        "wind_gusts_10m_max": "wind_gusts_max",
        "weather_code": "weather_code",
    })

    df["forecast_date"] = pd.to_datetime(df["forecast_date"], errors="coerce")

    numeric_cols = [
        "temperature_max", "temperature_min",
        "precipitation_sum", "precipitation_probability_max",
        "wind_speed_max", "wind_gusts_max",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "weather_code" in df.columns:
        df["weather_code"] = pd.to_numeric(
            df["weather_code"], errors="coerce"
        ).astype("Int64")

    df = df.dropna(subset=["city", "forecast_date", "temperature_max", "temperature_min"])

    df = df.drop_duplicates(subset=["city", "forecast_date"])

    df = quality_checks(df)

    df = df.reset_index(drop=True)

    return df


def quality_checks(df: pd.DataFrame) -> pd.DataFrame:

    bad_temp = df[
        (df["temperature_max"] < -20) | (df["temperature_max"] > 60) |
        (df["temperature_min"] < -30) | (df["temperature_min"] > 50)
    ]
    if len(bad_temp) > 0:
        logger.warning(f"[QC] {len(bad_temp)} rows with impossible temperatures")
        df = df.drop(bad_temp.index)

    bad_order = df[df["temperature_min"] > df["temperature_max"]]
    if len(bad_order) > 0:
        logger.warning(f"[QC] {len(bad_order)} rows where temp_min > temp_max")
        df = df.drop(bad_order.index)

    for col in ["precipitation_sum", "wind_speed_max", "wind_gusts_max"]:
        if col in df.columns:
            bad = df[df[col] < 0]
            if len(bad) > 0:
                logger.warning(f"[QC] {len(bad)} negative values in {col}")
                df = df[df[col] >= 0]

    return df


def build_silver_weather() -> pd.DataFrame:
    files = sorted(BRONZE_WEATHER_DIR.glob("*.json"))
    logger.info(f"Found {len(files)} JSON files in Bronze")

    if not files:
        raise FileNotFoundError(f"No JSON files in {BRONZE_WEATHER_DIR}")

    all_dfs = []
    for f in files:
        df_city = flatten_city_json(f)
        if not df_city.empty:
            all_dfs.append(df_city)

    df = pd.concat(all_dfs, ignore_index=True)
    logger.info(f"Flattened: {len(df)} rows from {len(all_dfs)} cities")

    df = clean_weather(df)
    logger.info(f"After cleaning: {len(df)} rows")

    return df


def save_silver(df: pd.DataFrame, name: str = "weather_clean.parquet") -> Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    path = SILVER_DIR / name
    df.to_parquet(path, index=False)
    logger.info(f"Saved Silver -> {path}")
    return path


if __name__ == "__main__":
    df = build_silver_weather()

    print("\n--- HEAD ---")
    print(df.head())
    print("\n--- SHAPE ---")
    print(df.shape)
    print("\n--- COLUMNS ---")
    print(df.columns.tolist())
    print("\n--- DTYPES ---")
    print(df.dtypes)

    path = save_silver(df)
    print(f"\nSaved -> {path}")