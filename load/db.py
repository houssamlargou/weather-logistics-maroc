import os
from pathlib import Path
import psycopg2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        user=os.getenv("POSTGRES_USER", "weather"),
        password=os.getenv("POSTGRES_PASSWORD", "weather"),
        dbname=os.getenv("POSTGRES_DB", "weather_db"),
    )