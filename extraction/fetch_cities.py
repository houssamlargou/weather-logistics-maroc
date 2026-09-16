import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "bronze" / "ma_cities.csv"

def load_cities_raw(path: Path = CSV_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


if __name__ == "__main__":
    df = load_cities_raw()
    print(f"Raw cities: {len(df)} rows, {len(df.columns)} columns")
    print("Columns:", df.columns.tolist())
    print(df.head())
