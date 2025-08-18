from typing import Dict
import pandas as pd
from datetime import datetime, timedelta, timezone
from settings import OPEN_METEO_BASE_URL
from .utils import load_hpai_data, fetch_json, get_state_from_fips_prefix, get_state_coords

async def get_biosecurity_score(county_fips: str = None, crop: str = "corn") -> Dict:
    """
    Calculate biosecurity risk score based on HPAI outbreak proximity
    BR = 70 if outbreak within X km and ≤Y days & weather conducive
    BR = 40 if outbreak nearby only
    BR = 0 otherwise
    """
    if crop not in ["poultry", "corn", "srw_wheat"]:
        return {
            "score": 0.0,
            "drivers": ["No biosecurity risk for this crop"],
            "data_age_hours": 0
        }
    
    # Load HPAI outbreak data
    hpai_data = load_hpai_data()
    
    if hpai_data.empty:
        return {
            "score": 0.0,
            "drivers": ["No HPAI outbreak data available"],
            "data_age_hours": 24
        }
    
    # Check for recent outbreaks (within 30 days) - use UTC-aware cutoff
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
    recent_outbreaks = hpai_data[
        pd.to_datetime(hpai_data['first_seen_iso']) >= cutoff_date
    ]
    
    if county_fips and not recent_outbreaks.empty:
        # Check if outbreak in same county (high risk)
        county_outbreak = recent_outbreaks[
            recent_outbreaks['county_fips'].astype(str) == str(county_fips)
        ]

        # Determine approximate coords using state centroid (FIPS prefix)
        state = get_state_from_fips_prefix(str(county_fips)[:2]) if county_fips else None
        lat, lon = get_state_coords(state) if state else get_state_coords("IL")

        # Conducive weather in next 72h: RH>=60% and 2<=T<=20C for >=6 hours
        conducive = False
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m,relative_humidity_2m",
            "forecast_days": 3,
            "timezone": "UTC"
        }
        weather = await fetch_json(OPEN_METEO_BASE_URL, params)
        if weather and "hourly" in weather:
            temps = weather["hourly"].get("temperature_2m", [])
            rhs = weather["hourly"].get("relative_humidity_2m", [])
            hours = min(len(temps), len(rhs), 72)
            hits = 0
            for i in range(hours):
                t = temps[i]
                rh = rhs[i]
                if t is not None and rh is not None and (2.0 <= t <= 20.0) and rh >= 60.0:
                    hits += 1
            conducive = hits >= 6
            borderline = 4 <= hits < 6

        if not county_outbreak.empty:
            if conducive:
                return {
                    "score": 70.0,
                    "drivers": [
                        "HPAI outbreak in county with conducive weather (next 72h)"
                    ],
                    "data_age_hours": 12
                }
            else:
                drivers = ["HPAI outbreak in county (weather not conducive)"]
                if 'borderline' in locals() and borderline:
                    drivers.append("BR uncertainty (weather near threshold)")
                return {
                    "score": 40.0,
                    "drivers": drivers,
                    "data_age_hours": 12
                }

    # Check for nearby outbreaks (moderate risk)
    if not recent_outbreaks.empty:
        # Same-state proximity (lightweight proxy for distance)
        if county_fips:
            target_prefix = str(county_fips)[:2]
            if any(str(cf).startswith(target_prefix) for cf in recent_outbreaks['county_fips'].astype(str)):
                return {
                    "score": 40.0,
                    "drivers": ["HPAI outbreaks detected in state"],
                    "data_age_hours": 12
                }
        return {
            "score": 40.0,
            "drivers": ["HPAI outbreaks detected in region"],
            "data_age_hours": 12
        }
    
    return {
        "score": 0.0,
        "drivers": ["No recent HPAI outbreaks detected"],
        "data_age_hours": 12
    }
