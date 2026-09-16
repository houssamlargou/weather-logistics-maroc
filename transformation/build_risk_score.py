import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
import numpy as np
import pandas as pd


SILVER_PATH = PROJECT_ROOT / "data" / "silver" / "cities_weather.parquet"
GOLD_DIR = PROJECT_ROOT / "data" / "gold"
GOLD_PATH = GOLD_DIR / "risk_score.parquet"


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


W_PRECIP = 0.40
W_WIND   = 0.30
W_TEMP   = 0.20
W_CODE   = 0.10


def precip_score(x: float) -> int:
    if pd.isna(x):      return 0
    if x < 1:           return 0
    if x < 5:           return 25
    if x < 15:          return 50
    if x < 30:          return 75
    return 100


def wind_score(x: float) -> int:
    if pd.isna(x):      return 0
    if x < 20:          return 0
    if x < 40:          return 25
    if x < 60:          return 50
    if x < 80:          return 75
    return 100


def temp_score(tmax: float, tmin: float) -> int:
    if pd.isna(tmax) or pd.isna(tmin):
        return 0
    if (15 <= tmax <= 30) and (5 <= tmin <= 20):
        return 0
    if (30 < tmax <= 35) or (0 <= tmin < 5):
        return 30
    if (35 < tmax <= 40) or (-5 <= tmin < 0):
        return 60
    if tmax > 40 or tmin < -5:
        return 100
    # cold days (tmax < 15) or cool nights (tmin 20+ but tmax low)
    if tmax < 15 or tmin > 20:
        return 30
    return 0


def code_score(code) -> int:
    if pd.isna(code):
        return 0
    code = int(code)
    if 0 <= code <= 3:    return 0
    if code in (45, 48):  return 40
    if 51 <= code <= 57:  return 30
    if 61 <= code <= 67:  return 50
    if 71 <= code <= 77:  return 80
    if 80 <= code <= 82:  return 60
    if code in (85, 86):  return 85
    if 95 <= code <= 99:  return 100
    return 0


def temp_category(tmax: float) -> str:
    if pd.isna(tmax):    return "Unknown"
    if tmax < 10:        return "Cold"
    if tmax < 25:        return "Mild"
    if tmax < 35:        return "Hot"
    return "Extreme"


def precip_category(x: float) -> str:
    if pd.isna(x):       return "None"
    if x == 0:           return "None"
    if x < 5:            return "Light"
    if x < 15:           return "Moderate"
    return "Heavy"


def wind_category(x: float) -> str:
    if pd.isna(x):       return "Calm"
    if x < 20:           return "Calm"
    if x < 40:           return "Moderate"
    if x < 60:           return "Strong"
    return "Dangerous"


def risk_level(score: int) -> str:
    if score < 25:  return "Low"
    if score < 50:  return "Moderate"
    if score < 75:  return "High"
    return "Extreme"


def build_gold(df: pd.DataFrame) -> pd.DataFrame:
    df["precip_score"] = df["precipitation_sum"].apply(precip_score)
    df["wind_score"]   = df["wind_gusts_max"].apply(wind_score)
    df["temp_score"]   = df.apply(
        lambda r: temp_score(r["temperature_max"], r["temperature_min"]), axis=1
    )
    df["code_score"]   = df["weather_code"].apply(code_score)

    df["risk_score"] = (
        W_PRECIP * df["precip_score"]
        + W_WIND * df["wind_score"]
        + W_TEMP * df["temp_score"]
        + W_CODE * df["code_score"]
    ).round().astype(int).clip(0, 100)

    df["risk_level"] = df["risk_score"].apply(risk_level)

    df["temperature_category"]   = df["temperature_max"].apply(temp_category)
    df["precipitation_category"] = df["precipitation_sum"].apply(precip_category)
    df["wind_category"]          = df["wind_gusts_max"].apply(wind_category)

    df["day_of_week"]  = df["forecast_date"].dt.day_name()
    df["is_weekend"]   = df["forecast_date"].dt.dayofweek >= 5
    df["days_ahead"]   = (df["forecast_date"] - df["forecast_date"].min()).dt.days

    return df


def save_gold(df: pd.DataFrame, path: Path = GOLD_PATH) -> Path:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    logger.info(f"Saved Gold -> {path}")
    return path


if __name__ == "__main__":
    if not SILVER_PATH.exists():
        raise FileNotFoundError(
            f"{SILVER_PATH} not found. Run transformation.join_cities_weather first."
        )

    df = pd.read_parquet(SILVER_PATH)
    logger.info(f"Loaded Silver: {len(df)} rows")

    df = build_gold(df)
    logger.info(f"Gold built: {len(df)} rows")

    print("\n--- HEAD ---")
    print(df[[
        "city", "forecast_date",
        "temperature_category", "precipitation_category", "wind_category",
        "risk_score", "risk_level"
    ]].head(10))

    print("\n--- RISK LEVEL DISTRIBUTION ---")
    print(df["risk_level"].value_counts())

    print("\n--- TOP 10 RISKIEST (city, date) ---")
    print(df.nlargest(10, "risk_score")[[
        "city", "forecast_date", "risk_score", "risk_level",
        "precipitation_sum", "wind_gusts_max", "temperature_max"
    ]])

    save_gold(df)