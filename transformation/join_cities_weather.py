import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
import pandas as pd

from transformation.clean_cities import load_cities


SILVER_DIR = PROJECT_ROOT / "data" / "silver"
WEATHER_PATH = SILVER_DIR / "weather_clean.parquet"
OUTPUT_PATH = SILVER_DIR / "cities_weather.parquet"


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def load_weather() -> pd.DataFrame:
    if not WEATHER_PATH.exists():
        raise FileNotFoundError(
            f"{WEATHER_PATH} not found. Run transformation.clean_weather first."
        )
    df = pd.read_parquet(WEATHER_PATH)
    logger.info(f"Loaded weather: {len(df)} rows, {df['city'].nunique()} cities")
    return df


def join_cities_weather(
    cities: pd.DataFrame,
    weather: pd.DataFrame,
) -> pd.DataFrame:

    before = len(weather)

    df = weather.merge(
        cities[["city", "latitude", "longitude", "region"]],
        on="city",
        how="left",
        validate="many_to_one",
    )

    logger.info(f"Joined: {before} weather rows -> {len(df)} rows")

    unmatched = df[df["latitude"].isna()]["city"].unique()
    if len(unmatched) > 0:
        logger.warning(f"Cities without coordinates: {unmatched.tolist()}")
        df = df.dropna(subset=["latitude", "longitude"])
        logger.info(f"After dropping unmatched: {len(df)} rows")

    df = df[[
        "city", "region", "latitude", "longitude",
        "forecast_date",
        "temperature_max", "temperature_min",
        "precipitation_sum", "precipitation_probability_max",
        "wind_speed_max", "wind_gusts_max",
        "weather_code",
    ]]

    df = df.reset_index(drop=True)
    return df


def save_silver(df: pd.DataFrame, path: Path = OUTPUT_PATH) -> Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info(f"Saved Silver -> {path}")
    return path


if __name__ == "__main__":
    cities = load_cities()
    weather = load_weather()

    df = join_cities_weather(cities, weather)

    print("\n--- HEAD ---")
    print(df.head())
    print("\n--- SHAPE ---")
    print(df.shape)
    print("\n--- COLUMNS ---")
    print(df.columns.tolist())
    print("\n--- DTYPES ---")
    print(df.dtypes)
    print("\n--- NULLS ---")
    print(df.isna().sum())

    save_silver(df)