# 🌦️ Weather Logistics Maroc

Pipeline de données météo pour l'aide à la décision logistique.

## 📋 Description

Ce projet construit un pipeline de données complet (**Bronze → Silver → Gold**) permettant d'analyser les prévisions météorologiques des villes marocaines et d'identifier les risques pour optimiser les opérations de livraison.

**Question métier :**

> Quelles villes et quelles périodes présentent le plus grand risque météorologique dans les prochains jours ?

Le résultat permet à un responsable opérationnel de :

- Comparer les conditions météorologiques entre les villes
- Identifier les périodes défavorables
- Anticiper les risques pour les livraisons
- Adapter l'organisation des opérations

---

## 🗂️ Sources de données

| Source         | Type            | Description                               | Lien                                  |
| -------------- | --------------- | ----------------------------------------- | ------------------------------------- |
| **SimpleMaps** | CSV             | Villes marocaines + coordonnées (lat/lng) | https://simplemaps.com/data/ma-cities |
| **Open-Meteo** | API REST (JSON) | Prévisions météo quotidiennes sur 7 jours | https://open-meteo.com/               |

### Variables météorologiques utilisées

- `temperature_2m_max` — Température maximale
- `temperature_2m_min` — Température minimale
- `precipitation_sum` — Somme des précipitations
- `precipitation_probability_max` — Probabilité maximale de précipitation
- `wind_speed_10m_max` — Vitesse maximale du vent
- `wind_gusts_10m_max` — Rafales maximales
- `weather_code` — Code météo WMO

---

## 🏗️ Architecture

Le projet suit l'architecture **médaillon** :

```
Sources          BRONZE              SILVER                  GOLD
─────────        ──────              ──────                  ────

SimpleMaps   →   ma_cities.csv  →   cities_clean.parquet
(CSV)
                                     ────────────►  cities_weather.parquet  →  risk_score.parquet
Open-Meteo   →   weather/*.json  →  weather_clean.parquet
(JSON)
```

### Détail des couches

| Couche     | Rôle                               | Format     | Stockage       |
| ---------- | ---------------------------------- | ---------- | -------------- |
| **Bronze** | Données brutes, non modifiées      | CSV + JSON | `data/bronze/` |
| **Silver** | Données nettoyées, typées, jointes | Parquet    | `data/silver/` |
| **Gold**   | Features + Risk Score              | Parquet    | `data/gold/`   |

---

## 📁 Structure du projet

```
weather-logistics-maroc/
│
├── extraction/                  ← Bronze : récupération des données
│   ├── __init__.py
│   ├── fetch_cities.py          → lecture du CSV SimpleMaps
│   └── fetch_weather.py         → appels API Open-Meteo
│
├── transformation/              ← Silver + Gold
│   ├── __init__.py
│   ├── clean_cities.py          → nettoyage des villes
│   ├── clean_weather.py         → nettoyage de la météo
│   ├── join_cities_weather.py   → jointure villes + météo
│   └── build_risk_score.py      → features + score de risque
│
├── load/                        ← Chargement PostgreSQL
│   ├── __init__.py
│   ├── db.py                    → connexion
│   └── load_to_postgres.py      → upsert pipeline
│
├── dashboard/                   ← Streamlit
│   ├── __init__.py
│   └── app.py                   → dashboard interactif
│
├── dags/                        ← Airflow
│   └── weather_pipeline.py      → DAG quotidien
│
├── sql/
│   ├── schema.sql               → schéma de la base
│   └── queries.sql              → 7 requêtes d'analyse
│
├── docker/
│   ├── postgres/init.sql        → script d'init automatique
│   ├── airflow/Dockerfile
│   └── streamlit/Dockerfile
│
├── data/
│   ├── bronze/                  → données brutes
│   ├── silver/                  → données nettoyées
│   └── gold/                    → données enrichies
│
├── docker-compose.yml
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 🗄️ Schéma du Data Warehouse

### Table `cities`

| Colonne    | Type             | Contrainte       |
| ---------- | ---------------- | ---------------- |
| city_id    | SERIAL           | PRIMARY KEY      |
| city       | TEXT             | NOT NULL, UNIQUE |
| latitude   | DOUBLE PRECISION | NOT NULL         |
| longitude  | DOUBLE PRECISION | NOT NULL         |
| region     | TEXT             |                  |
| updated_at | TIMESTAMP        | DEFAULT NOW()    |

### Table `weather_forecast`

| Colonne                             | Type             | Contrainte       |
| ----------------------------------- | ---------------- | ---------------- |
| forecast_id                         | SERIAL           | PRIMARY KEY      |
| city_id                             | INTEGER          | FK → cities      |
| forecast_date                       | DATE             | NOT NULL         |
| temperature_max                     | DOUBLE PRECISION |                  |
| temperature_min                     | DOUBLE PRECISION |                  |
| precipitation_sum                   | DOUBLE PRECISION |                  |
| precipitation_probability_max       | DOUBLE PRECISION |                  |
| wind_speed_max                      | DOUBLE PRECISION |                  |
| wind_gusts_max                      | DOUBLE PRECISION |                  |
| weather_code                        | INTEGER          |                  |
| updated_at                          | TIMESTAMP        | DEFAULT NOW()    |
| **UNIQUE (city_id, forecast_date)** |                  | **clé d'upsert** |

### Table `risk_score`

| Colonne                             | Type      | Contrainte       |
| ----------------------------------- | --------- | ---------------- |
| risk_id                             | SERIAL    | PRIMARY KEY      |
| city_id                             | INTEGER   | FK → cities      |
| forecast_date                       | DATE      | NOT NULL         |
| risk_score                          | INTEGER   | CHECK (0–100)    |
| risk_level                          | TEXT      | NOT NULL         |
| temperature_category                | TEXT      |                  |
| precipitation_category              | TEXT      |                  |
| wind_category                       | TEXT      |                  |
| updated_at                          | TIMESTAMP | DEFAULT NOW()    |
| **UNIQUE (city_id, forecast_date)** |           | **clé d'upsert** |

### Table `weather_forecast_history` (bonus)

Historique append-only des prévisions (une ligne par exécution du pipeline).

---

## 🎯 Weather Risk Score

### Formule

```
risk_score = 0.40 × precipitation_score
           + 0.30 × wind_score
           + 0.20 × temperature_score
           + 0.10 × weather_code_score
```

### Justification des poids

| Variable              | Poids | Justification                                             |
| --------------------- | ----- | --------------------------------------------------------- |
| Précipitations        | 40%   | Impact direct sur la circulation et les livraisons        |
| Rafales de vent       | 30%   | Danger pour les véhicules, surtout sur les ponts et côtes |
| Températures extrêmes | 20%   | Sécurité des livreurs, chaîne du froid                    |
| Weather code          | 10%   | Signal global (brouillard, orage, neige)                  |

### Seuils

**Précipitations (mm/jour) :** 0–1 → 0 · 1–5 → 25 · 5–15 → 50 · 15–30 → 75 · >30 → 100

**Rafales (km/h) :** 0–20 → 0 · 20–40 → 25 · 40–60 → 50 · 60–80 → 75 · >80 → 100

**Températures :** confortable → 0 · modéré → 30 · élevé → 60 · extrême → 100

**Weather code :** clair → 0 · brouillard → 40 · pluie → 50 · neige → 80 · orage → 100

### Niveaux de risque

| Score  | Niveau      |
| ------ | ----------- |
| 0–25   | 🟢 Low      |
| 25–50  | 🟡 Moderate |
| 50–75  | 🟠 High     |
| 75–100 | 🔴 Extreme  |

---

## ⚙️ Installation

### Prérequis

- Python 3.10+
- Docker Desktop
- Git

### Étapes

```bash
# 1. Cloner le projet
git clone <votre-repo>
cd weather-logistics-maroc

# 2. Créer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate      # Linux/macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
# Éditez .env avec vos valeurs
```

### Fichier `.env`

```env
POSTGRES_USER=weather
POSTGRES_PASSWORD=weather_pass
POSTGRES_DB=weather_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin123
AIRFLOW_ADMIN_EMAIL=admin@example.com
```

---

## 🚀 Exécution

### Option 1 — Tout via Docker (recommandé)

```bash
docker compose up -d
```

Cela lance :

- **PostgreSQL** → `localhost:5432`
- **Airflow** → http://localhost:8080 (admin / admin123)
- **Streamlit** → http://localhost:8501
- **pgAdmin** (bonus) → http://localhost:5050

### Option 2 — Manuellement, étape par étape

```bash
# 1. Démarrer PostgreSQL
docker compose up -d postgres

# 2. Charger les villes (Bronze)
python -m extraction.fetch_cities

# 3. Récupérer la météo (Bronze)
python -m extraction.fetch_weather

# 4. Nettoyer les villes (Silver)
python -m transformation.clean_cities

# 5. Nettoyer la météo (Silver)
python -m transformation.clean_weather

# 6. Joindre villes + météo (Silver)
python -m transformation.join_cities_weather

# 7. Construire le Risk Score (Gold)
python -m transformation.build_risk_score

# 8. Charger dans PostgreSQL
python -m load.load_to_postgres

# 9. Lancer le dashboard
python -m streamlit run dashboard/app.py
```

---

## 🐳 Services Docker

| Service               | Image                | Port | URL                   |
| --------------------- | -------------------- | ---- | --------------------- |
| **postgres**          | postgres:16          | 5432 | —                     |
| **airflow-webserver** | apache/airflow:2.9.0 | 8080 | http://localhost:8080 |
| **airflow-scheduler** | apache/airflow:2.9.0 | —    | —                     |
| **streamlit**         | python:3.11-slim     | 8501 | http://localhost:8501 |
| **pgadmin** (bonus)   | dpage/pgadmin4       | 5050 | http://localhost:5050 |

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f airflow-scheduler
docker compose logs -f streamlit

# Arrêter
docker compose down

# Arrêter + supprimer les volumes (fresh start)
docker compose down -v

# Redémarrer
docker compose restart

# Entrer dans un container
docker exec -it weather_postgres psql -U weather -d weather_db
```

---

## 📊 Dashboard Streamlit

Le dashboard est accessible sur **http://localhost:8501** une fois lancé.

### KPI affichés

- Nombre de villes
- Température maximale
- Précipitations maximales
- Nombre de périodes à risque
- Ville présentant le risque le plus élevé

### Filtres

- Ville
- Date
- Plage de dates
- Niveau de risque

### Visualisations

- **Bar chart** — Risque moyen par ville
- **Line chart** — Risque moyen par jour
- **Carte géographique** — Risque par ville
- **Table** — Top 20 des situations les plus risquées

### Capture d'écran

![Dashboard Streamlit](docs/dashboard.png)

---

## 🔍 Requêtes SQL d'analyse

Le fichier `sql/queries.sql` contient 7 requêtes métier :

| #   | Question                                                                         |
| --- | -------------------------------------------------------------------------------- |
| 1   | Quelles villes auront les températures les plus élevées ?                        |
| 2   | Quelles villes auront les plus fortes précipitations ?                           |
| 3   | Quelles villes présentent le risque moyen le plus élevé ?                        |
| 4   | Quelles périodes présentent le risque maximal ?                                  |
| 5   | Pour chaque ville, quelle période présente le plus grand risque ? (sous-requête) |
| 6   | Classement des villes par risque chaque jour (RANK - Window Function)            |
| 7   | Top 3 des villes les plus risquées par jour (ROW_NUMBER + CTE)                   |

### Exécution

```bash
# Toutes les requêtes
Get-Content sql\queries.sql | docker exec -i weather_postgres psql -U weather -d weather_db

# Une requête spécifique
docker exec -it weather_postgres psql -U weather -d weather_db -c "SELECT ..."
```

---

## ⚙️ Orchestration Airflow

Le DAG `dags/weather_pipeline.py` automatise :

```
extract_cities → extract_weather → clean_cities → clean_weather
        → join_cities_weather → build_risk_score → load_to_postgres
```

### Configuration

- **Schedule :** `@daily`
- **Retries :** 3
- **Retry delay :** 5 minutes
- **Catchup :** désactivé

### Accès

- URL : http://localhost:8080
- Login : `admin` / `admin123`

---

## 🗺️ Diagrammes UML

### Diagramme de cas d'utilisation

![Use Case Diagram](docs/usecase.png)

### Diagramme de classes

![Class Diagram](docs/class.png)

---

## 🧪 Vérifications

### Vérifier les tables PostgreSQL

```bash
docker exec -it weather_postgres psql -U weather -d weather_db -c "\dt"
```

Attendu : `cities`, `weather_forecast`, `risk_score`, `weather_forecast_history`

### Vérifier les données

```bash
docker exec -it weather_postgres psql -U weather -d weather_db -c "SELECT COUNT(*) FROM cities;"
docker exec -it weather_postgres psql -U weather -d weather_db -c "SELECT COUNT(*) FROM weather_forecast;"
docker exec -it weather_postgres psql -U weather -d weather_db -c "SELECT COUNT(*) FROM risk_score;"
```

Attendu : `120`, `840`, `840`

### Vérifier l'upsert (idempotence)

Relancer `python -m load.load_to_postgres`. Les compteurs doivent rester identiques (`cities`, `weather_forecast`, `risk_score`). Seul `weather_forecast_history` grandit (append-only).

---

## 🛠️ Technologies utilisées

| Technologie             | Usage                   |
| ----------------------- | ----------------------- |
| Python 3.10+            | Langage principal       |
| pandas                  | Manipulation de données |
| requests + tenacity     | Appels API avec retries |
| pyarrow                 | Format Parquet          |
| PostgreSQL 16           | Data Warehouse          |
| SQLAlchemy + psycopg2   | Connexion DB            |
| Apache Airflow 2.9      | Orchestration           |
| Streamlit + Plotly      | Dashboard               |
| Docker + Docker Compose | Conteneurisation        |

---

## 📚 Auteur

Projet individuel — Certification RNCP Développeur.se en intelligence artificielle (2023)

**Auteur :** [Votre Nom]

**Date :** 14–18 Septembre 2026

---

## 📄 Licence

Projet pédagogique — libre d'utilisation pour l'apprentissage.
