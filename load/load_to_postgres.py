import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
import pandas as pd
from psycopg2.extras import execute_values

from load.db import get_connection

GOLD_PATH = PROJECT_ROOT / "data" / "gold" / "risk_score.parquet"

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)


def upsert(conn, table, columns, conflict_cols, rows, has_updated_at=True):
    cols = ", ".join(columns)
    updates = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c not in conflict_cols)

    if has_updated_at:
        updates += ", updated_at = NOW()"

    sql = f"""
        INSERT INTO {table} ({cols})
        VALUES %s
        ON CONFLICT ({', '.join(conflict_cols)})
        DO UPDATE SET {updates}
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()


def clean(value):
    return None if pd.isna(value) else value


def main():
    df = pd.read_parquet(GOLD_PATH)
    logger.info(f"Loaded Gold: {len(df)} rows")

    conn = get_connection()

    cities = df[["city", "latitude", "longitude", "region"]].drop_duplicates("city")
    rows = [
        (r["city"], float(r["latitude"]), float(r["longitude"]), r["region"])
        for _, r in cities.iterrows()
    ]
    upsert(conn, "cities",
       ["city", "latitude", "longitude", "region"],
       ["city"],
       rows,
       has_updated_at=False)
    logger.info(f"Upserted {len(rows)} cities")

    with conn.cursor() as cur:
        cur.execute("SELECT city, city_id FROM cities")
        city_ids = {name: cid for name, cid in cur.fetchall()}

    rows = [
        (
            city_ids[r["city"]],
            r["forecast_date"].date(),
            clean(r["temperature_max"]),
            clean(r["temperature_min"]),
            clean(r["precipitation_sum"]),
            clean(r["precipitation_probability_max"]),
            clean(r["wind_speed_max"]),
            clean(r["wind_gusts_max"]),
            clean(r["weather_code"]),
        )
        for _, r in df.iterrows()
    ]
    upsert(conn, "weather_forecast",
           ["city_id", "forecast_date",
            "temperature_max", "temperature_min",
            "precipitation_sum", "precipitation_probability_max",
            "wind_speed_max", "wind_gusts_max", "weather_code"],
           ["city_id", "forecast_date"],
           rows)
    logger.info(f"Upserted {len(rows)} weather rows")

    rows = [
        (
            city_ids[r["city"]],
            r["forecast_date"].date(),
            int(r["risk_score"]),
            r["risk_level"],
            r["temperature_category"],
            r["precipitation_category"],
            r["wind_category"],
        )
        for _, r in df.iterrows()
    ]
    upsert(conn, "risk_score",
           ["city_id", "forecast_date", "risk_score", "risk_level",
            "temperature_category", "precipitation_category", "wind_category"],
           ["city_id", "forecast_date"],
           rows)
    logger.info(f"Upserted {len(rows)} risk rows")

    # 6. Append history (no upsert, just INSERT)
    with conn.cursor() as cur:
        for _, r in df.iterrows():
            cur.execute("""
                INSERT INTO weather_forecast_history (
                    city_id, forecast_date,
                    temperature_max, temperature_min,
                    precipitation_sum, precipitation_probability_max,
                    wind_speed_max, wind_gusts_max, weather_code, risk_score
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                city_ids[r["city"]],
                r["forecast_date"].date(),
                clean(r["temperature_max"]),
                clean(r["temperature_min"]),
                clean(r["precipitation_sum"]),
                clean(r["precipitation_probability_max"]),
                clean(r["wind_speed_max"]),
                clean(r["wind_gusts_max"]),
                clean(r["weather_code"]),
                int(r["risk_score"]),
            ))
    conn.commit()
    logger.info(f"Appended {len(df)} history rows")

    conn.close()
    logger.info("Load complete.")


if __name__ == "__main__":
    main()