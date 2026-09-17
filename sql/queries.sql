SELECT
    c.city,
    c.region,
    w.forecast_date,
    w.temperature_max
FROM weather_forecast w
JOIN cities c ON c.city_id = w.city_id
ORDER BY w.temperature_max DESC
LIMIT 10;



SELECT
    c.city,
    c.region,
    w.forecast_date,
    w.precipitation_sum
FROM weather_forecast w
JOIN cities c ON c.city_id = w.city_id
ORDER BY w.precipitation_sum DESC
LIMIT 10;



SELECT
    c.city,
    c.region,
    ROUND(AVG(r.risk_score), 1) AS avg_risk,
    MAX(r.risk_score)           AS max_risk,
    COUNT(*)                    AS nb_days
FROM risk_score r
JOIN cities c ON c.city_id = r.city_id
GROUP BY c.city, c.region
ORDER BY avg_risk DESC
LIMIT 10;



SELECT
    r.forecast_date,
    ROUND(AVG(r.risk_score), 1) AS avg_risk,
    MAX(r.risk_score)           AS max_risk,
    COUNT(*) FILTER (WHERE r.risk_level IN ('High', 'Extreme')) AS nb_risky_cities
FROM risk_score r
GROUP BY r.forecast_date
ORDER BY r.forecast_date;


SELECT
    c.city,
    r.forecast_date,
    r.risk_score,
    r.risk_level
FROM risk_score r
JOIN cities c ON c.city_id = r.city_id
WHERE r.risk_score = (
    SELECT MAX(r2.risk_score)
    FROM risk_score r2
    WHERE r2.city_id = r.city_id
)
ORDER BY r.risk_score DESC;



SELECT
    r.forecast_date,
    c.city,
    r.risk_score,
    RANK() OVER (
        PARTITION BY r.forecast_date
        ORDER BY r.risk_score DESC
    ) AS rank_in_day
FROM risk_score r
JOIN cities c ON c.city_id = r.city_id
ORDER BY r.forecast_date, rank_in_day;


WITH ranked AS (
    SELECT
        r.forecast_date,
        c.city,
        r.risk_score,
        r.risk_level,
        ROW_NUMBER() OVER (
            PARTITION BY r.forecast_date
            ORDER BY r.risk_score DESC
        ) AS rn
    FROM risk_score r
    JOIN cities c ON c.city_id = r.city_id
)
SELECT
    forecast_date,
    city,
    risk_score,
    risk_level
FROM ranked
WHERE rn <= 3
ORDER BY forecast_date, rn;