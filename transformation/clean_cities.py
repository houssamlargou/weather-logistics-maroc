import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from extraction.fetch_cities import load_cities_raw

SILVER_DIR = PROJECT_ROOT / "data" / "silver"


def clean_cities(df: pd.DataFrame) -> pd.DataFrame:

    df = df[["city", "lat", "lng", "admin_name"]].copy()

    df = df.rename(columns={
        "lat": "latitude",
        "lng": "longitude",
        "admin_name": "region",
    })

    df = df.dropna(subset=["city", "latitude", "longitude"])

    df = df.drop_duplicates(subset=["city"])

    df = df.reset_index(drop=True)

    return df


def load_cities() -> pd.DataFrame:
    raw = load_cities_raw()
    return clean_cities(raw)


def save_silver(df: pd.DataFrame, name: str = "cities_clean.parquet") -> Path:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    path = SILVER_DIR / name
    df.to_parquet(path, index=False)
    return path


if __name__ == "__main__":
    df = load_cities()
    print(f"Clean cities: {len(df)} rows")
    print(df.head())
    print("\nColumns:", df.columns.tolist())
    print("Shape:", df.shape)

    path = save_silver(df)
    print(f"\nSaved -> {path}")