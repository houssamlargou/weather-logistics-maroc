import os
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv
from sqlalchemy import create_engine


# ---------- Config ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

st.set_page_config(
    page_title="Weather Logistics Maroc",
    page_icon="🌦️",
    layout="wide",
)


# ---------- Database ----------
@st.cache_resource
def get_engine():
    user = os.getenv("POSTGRES_USER", "weather")
    password = os.getenv("POSTGRES_PASSWORD", "weather_pass")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "weather_db")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    query = """
        SELECT
            c.city,
            c.region,
            c.latitude,
            c.longitude,
            w.forecast_date,
            w.temperature_max,
            w.temperature_min,
            w.precipitation_sum,
            w.precipitation_probability_max,
            w.wind_speed_max,
            w.wind_gusts_max,
            w.weather_code,
            r.risk_score,
            r.risk_level,
            r.temperature_category,
            r.precipitation_category,
            r.wind_category
        FROM risk_score r
        JOIN cities c
          ON c.city_id = r.city_id
        JOIN weather_forecast w
          ON w.city_id = r.city_id
         AND w.forecast_date = r.forecast_date
        ORDER BY w.forecast_date, c.city
    """
    return pd.read_sql(query, get_engine())


# ---------- Load ----------
df = load_data()


# ---------- Header ----------
st.title("🌦️ Weather Logistics Maroc")
st.caption("Prévisions météo et niveaux de risque pour les villes marocaines")


# ---------- Sidebar filters ----------
st.sidebar.header("Filtres")

# City filter
cities = ["Toutes"] + sorted(df["city"].unique().tolist())
selected_city = st.sidebar.selectbox("Ville", cities)

# Date filter
dates = sorted(df["forecast_date"].unique())
date_options = ["Toutes"] + [str(d) for d in dates]
selected_date = st.sidebar.selectbox("Date", date_options)

# Risk level filter
levels = ["Tous", "Low", "Moderate", "High", "Extreme"]
selected_level = st.sidebar.selectbox("Niveau de risque", levels)

# Period filter (days ahead)
st.sidebar.subheader("Période")
min_date = df["forecast_date"].min()
max_date = df["forecast_date"].max()
date_range = st.sidebar.date_input(
    "Plage de dates",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)


# ---------- Apply filters ----------
filtered = df.copy()

if selected_city != "Toutes":
    filtered = filtered[filtered["city"] == selected_city]

if selected_date != "Toutes":
    filtered = filtered[filtered["forecast_date"] == pd.to_datetime(selected_date).date()]

if selected_level != "Tous":
    filtered = filtered[filtered["risk_level"] == selected_level]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start, end = date_range
    filtered = filtered[
        (filtered["forecast_date"] >= start) &
        (filtered["forecast_date"] <= end)
    ]


# ---------- KPI row ----------
st.subheader("Indicateurs clés")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Villes", filtered["city"].nunique())

with col2:
    max_temp = filtered["temperature_max"].max() if len(filtered) else 0
    st.metric("Température max", f"{max_temp:.1f} °C")

with col3:
    max_precip = filtered["precipitation_sum"].max() if len(filtered) else 0
    st.metric("Précipitations max", f"{max_precip:.1f} mm")

with col4:
    risky = filtered[filtered["risk_level"].isin(["High", "Extreme"])]
    st.metric("Périodes à risque", risky.shape[0])

with col5:
    if len(filtered) > 0:
        top = filtered.sort_values("risk_score", ascending=False).iloc[0]
        st.metric("Ville la plus risquée", top["city"], f"{int(top['risk_score'])}/100")
    else:
        st.metric("Ville la plus risquée", "—")


# ---------- Chart 1: risk by city ----------
st.subheader("Risque moyen par ville")

if len(filtered) > 0:
    risk_by_city = (
        filtered.groupby("city", as_index=False)["risk_score"]
        .mean()
        .sort_values("risk_score", ascending=False)
        .head(15)
    )
    fig = px.bar(
        risk_by_city,
        x="risk_score",
        y="city",
        orientation="h",
        color="risk_score",
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        labels={"risk_score": "Risque moyen", "city": "Ville"},
    )
    fig.update_layout(yaxis=dict(autorange="reversed"), height=500)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucune donnée pour ces filtres.")


# ---------- Chart 2: risk by date ----------
st.subheader("Risque moyen par jour")

if len(filtered) > 0:
    risk_by_date = (
        filtered.groupby("forecast_date", as_index=False)["risk_score"].mean()
    )
    fig2 = px.line(
        risk_by_date,
        x="forecast_date",
        y="risk_score",
        markers=True,
        labels={"forecast_date": "Date", "risk_score": "Risque moyen"},
    )
    st.plotly_chart(fig2, use_container_width=True)


# ---------- Chart 3: map of cities ----------
st.subheader("Carte des villes (risque moyen)")

if len(filtered) > 0:
    map_data = (
        filtered.groupby(["city", "latitude", "longitude"], as_index=False)["risk_score"]
        .mean()
    )
    fig3 = px.scatter_mapbox(
        map_data,
        lat="latitude",
        lon="longitude",
        size="risk_score",
        color="risk_score",
        hover_name="city",
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c"],
        zoom=4,
        height=500,
    )
    fig3.update_layout(mapbox_style="open-street-map")
    st.plotly_chart(fig3, use_container_width=True)


# ---------- Table: top riskiest pairs ----------
st.subheader("Top 20 des situations les plus risquées")

if len(filtered) > 0:
    top_table = (
        filtered.sort_values("risk_score", ascending=False)
        .head(20)[[
            "city", "region", "forecast_date",
            "risk_score", "risk_level",
            "temperature_max", "temperature_min",
            "precipitation_sum", "wind_gusts_max",
            "temperature_category", "precipitation_category", "wind_category",
        ]]
        .reset_index(drop=True)
    )
    st.dataframe(top_table, use_container_width=True)
else:
    st.info("Aucune donnée pour ces filtres.")


# ---------- Footer ----------
st.caption(f"Données: {len(filtered)} lignes affichées sur {len(df)} au total.")