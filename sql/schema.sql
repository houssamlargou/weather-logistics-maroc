CREATE TABLE IF NOT EXISTS cities (
    city_id     SERIAL PRIMARY KEY,
    city        TEXT NOT NULL UNIQUE,
    latitude    DOUBLE PRECISION NOT NULL,
    longitude   DOUBLE PRECISION NOT NULL,
    region      TEXT
);

CREATE TABLE IF NOT EXISTS weather_forecast (
    forecast_id                    SERIAL PRIMARY KEY,
    city_id                        INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    forecast_date                  DATE NOT NULL,
    temperature_max                DOUBLE PRECISION,
    temperature_min                DOUBLE PRECISION,
    precipitation_sum              DOUBLE PRECISION,
    precipitation_probability_max  DOUBLE PRECISION,
    wind_speed_max                 DOUBLE PRECISION,
    wind_gusts_max                 DOUBLE PRECISION,
    weather_code                   INTEGER,
    updated_at                     TIMESTAMP DEFAULT NOW(),
    UNIQUE (city_id, forecast_date)
);

CREATE TABLE IF NOT EXISTS risk_score (
    risk_id                 SERIAL PRIMARY KEY,
    city_id                 INTEGER NOT NULL REFERENCES cities(city_id) ON DELETE CASCADE,
    forecast_date           DATE NOT NULL,
    risk_score              INTEGER NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_level              TEXT NOT NULL,
    temperature_category    TEXT,
    precipitation_category  TEXT,
    wind_category           TEXT,
    updated_at              TIMESTAMP DEFAULT NOW(),
    UNIQUE (city_id, forecast_date)
);

CREATE TABLE IF NOT EXISTS weather_forecast_history (
    history_id                     SERIAL PRIMARY KEY,
    city_id                        INTEGER NOT NULL,
    forecast_date                  DATE NOT NULL,
    temperature_max                DOUBLE PRECISION,
    temperature_min                DOUBLE PRECISION,
    precipitation_sum              DOUBLE PRECISION,
    precipitation_probability_max  DOUBLE PRECISION,
    wind_speed_max                 DOUBLE PRECISION,
    wind_gusts_max                 DOUBLE PRECISION,
    weather_code                   INTEGER,
    risk_score                     INTEGER,
    fetched_at                     TIMESTAMP DEFAULT NOW()
);