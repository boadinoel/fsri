from typing import Dict, List
import httpx
from datetime import datetime
from settings import OPEN_METEO_BASE_URL, NASS_API_KEY
from .utils import fetch_json, clip_score, get_state_coords

# Simple in-memory cache for weekly NASS lookups
_nass_cache: Dict[str, Dict] = {}

def _crop_to_nass(commodity: str) -> str:
    mapping = {
        "corn": "CORN",
        "srw_wheat": "WHEAT",
    }
    return mapping.get(commodity, commodity.upper())

async def _fetch_nass_gex(crop: str, state_alpha: str) -> float:
    """Return Good+Excellent percent for latest week, or -1 if unavailable."""
    if not NASS_API_KEY:
        return -1.0
    key = f"{crop}:{state_alpha}"
    if key in _nass_cache:
        return _nass_cache[key]["gex"]

    base_url = "https://quickstats.nass.usda.gov/api/api_GET/"
    commodity = _crop_to_nass(crop)

    async def _one(cond: str) -> float:
        current_year = datetime.utcnow().year
        
        # Try current year first
        params = {
            "key": NASS_API_KEY,
            "source_desc": "SURVEY",
            "commodity_desc": commodity,
            "statisticcat_desc": "CONDITION",
            "condition_cat_desc": cond,  # GOOD or EXCELLENT
            "state_alpha": state_alpha,
            "agg_level_desc": "STATE",
            "year": str(current_year),
            "format": "JSON",
        }
        data = await fetch_json(base_url, params)
        
        # If no data, try year range fallback
        if not data or "data" not in data or not data["data"]:
            params.pop("year")
            params["year__GE"] = str(current_year - 1)
            params["year__LE"] = str(current_year)
            data = await fetch_json(base_url, params)
            
        if not data or "data" not in data or not data["data"]:
            return -1.0
        # pick latest by week_ending
        rec = max(data["data"], key=lambda d: d.get("week_ending") or d.get("end_code") or "")
        try:
            return float(rec.get("Value", "-1").replace(",", ""))
        except Exception:
            return -1.0

    good = await _one("GOOD")
    exc = await _one("EXCELLENT")
    if good < 0 and exc < 0:
        return -1.0
    gex = max(0.0, (good if good > 0 else 0.0) + (exc if exc > 0 else 0.0))
    _nass_cache[key] = {"gex": gex}
    return gex

async def get_production_score(crop: str, state: str) -> Dict:
    """
    Calculate production risk score based on heat/humidity stress and crop conditions
    PR = clip(50 - 12*cond_z + 40*(heat_humid_hours/84), 0, 100)
    """
    lat, lon = get_state_coords(state)
    
    # Fetch 7-day hourly weather forecast from Open-Meteo
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m",
        "forecast_days": 7,
        "timezone": "UTC"
    }
    
    weather_data = await fetch_json(OPEN_METEO_BASE_URL, params)
    
    if not weather_data or "hourly" not in weather_data:
        return {
            "score": 50.0,
            "drivers": ["Weather data unavailable - using default"],
            "data_age_hours": 24
        }
    
    # Calculate heat-humidity stress hours (T≥32°C & RH≥50%)
    temps = weather_data["hourly"]["temperature_2m"]
    humidity = weather_data["hourly"]["relative_humidity_2m"]
    
    heat_humid_hours = 0
    first72 = 0
    max_h = min(len(temps), len(humidity), 168)
    for i in range(max_h):  # up to 7 days * 24 hours
        if temps[i] is not None and humidity[i] is not None:
            hit = 1 if (temps[i] >= 32.0 and humidity[i] >= 50.0) else 0
            heat_humid_hours += hit
            if i < 72:
                first72 += hit
    
    # NASS crop condition: if available, use latest %G+E; else baseline 60
    gex = await _fetch_nass_gex(crop, state)
    cond_gex = 60.0 if gex < 0 else gex
    cond_z = (cond_gex - 60.0) / 10.0
    
    # Calculate production risk score
    pr_score = clip_score(50 - 12 * cond_z + 40 * (heat_humid_hours / 84))
    
    drivers = []
    if heat_humid_hours > 20:
        drivers.append(f"High heat-humidity stress: {heat_humid_hours} hours forecast")
    if pr_score > 60:
        drivers.append("Elevated production risk conditions")
    # Uncertainty: divergence between 72h and 7d stress
    if abs(heat_humid_hours - first72) >= 10:
        drivers.append("High PR uncertainty (72h vs 7d divergence)")
    if gex < 0:
        drivers.append("NASS crop condition unavailable (baseline)")
    else:
        drivers.append(f"NASS %G+E: {cond_gex:.0f}%")
    
    return {
        "score": round(pr_score, 1),
        "drivers": drivers if drivers else ["Normal production conditions"],
        "data_age_hours": 1  # Fresh forecast data
    }
