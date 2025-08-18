import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
ARGENTIS_API_KEY = os.getenv("ARGENTIS_API_KEY")
ALLOW_ORIGINS = os.getenv("ALLOW_ORIGINS", "http://localhost:3000").split(",")
NASS_API_KEY = os.getenv("NASS_API_KEY")
AL_ENABLED = os.getenv("AL_ENABLED", "false").lower() == "true"
BANDIT_ENABLED = os.getenv("BANDIT_ENABLED", "false").lower() == "true"

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# USGS Gauge Constants
USGS_GAUGES = {
    "mississippi_baton_rouge": {
        "site_id": "07374000",
        "low_threshold": 5.0,  # feet
        "high_threshold": 10.0  # feet
    },
    "ohio_cairo": {
        "site_id": "03612500", 
        "low_threshold": 5.0,
        "high_threshold": 10.0
    },
    # Additional representative gauges (extendable)
    "mississippi_memphis": {
        "site_id": "07032000",
        "low_threshold": 5.0,
        "high_threshold": 10.0
    },
    "illinois_river_peoria": {
        "site_id": "05567500",
        "low_threshold": 8.0,
        "high_threshold": 15.0
    }
}

# Scoring Constants
SCORING_WEIGHTS = {
    "production": 0.40,
    "movement": 0.35,
    "policy": 0.05,
    "biosecurity": 0.20
}

# Open-Meteo API
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

# USGS Water Services API
USGS_BASE_URL = "https://waterservices.usgs.gov/nwis/iv"
