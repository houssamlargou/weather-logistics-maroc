import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "bronze" / "ma_cities.csv"



def load_cities(path: Path = CSV_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)

    df = df[["city", "lat", "lng", "admin_name"]].copy()

    df.columns = ["city", "latitude", "longitude", "region"]

    df = df.dropna(subset=["city", "latitude", "longitude"])
    df = df.drop_duplicates(subset=["city"])
    df = df.reset_index(drop=True)

    return df


if __name__ == "__main__":
    cities = load_cities()
    print(f"✅ Loaded {len(cities)} cities")
    print(cities.head())
    print("\nColumns:", cities.columns.tolist())
    print("Shape:", cities.shape)