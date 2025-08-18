import httpx
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd

def get_current_utc() -> str:
    """Get current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()

def clip_score(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clip score to valid range"""
    return max(min_val, min(max_val, value))

def determine_confidence(input_ages_hours: list) -> str:
    """Determine confidence level based on input data freshness"""
    if not input_ages_hours:
        return "Low"
    
    max_age = max(input_ages_hours)
    if max_age < 6:
        return "High"
    elif max_age < 24:
        return "Medium"
    else:
        return "Low"

async def fetch_json(url: str, params: Dict[str, Any] = None) -> Optional[Dict]:
    """Fetch JSON data from URL with error handling"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def load_hpai_data() -> pd.DataFrame:
    """Load HPAI county data from CSV"""
    try:
        return pd.read_csv("data/ap_hpai_counties.csv")
    except FileNotFoundError:
        print("HPAI data file not found, using empty dataset")
        return pd.DataFrame(columns=["county_fips", "first_seen_iso"])

def get_state_coords(state: str) -> tuple:
    """Get approximate center coordinates for US states"""
    state_coords = {
        "IL": (40.0, -89.0),
        "IA": (42.0, -93.5),
        "IN": (40.0, -86.0),
        "OH": (40.5, -82.5),
        "NE": (41.5, -99.5),
        "KS": (38.5, -98.0),
        "MO": (38.5, -92.5),
        "MN": (46.0, -94.0)
    }
    return state_coords.get(state, (39.0, -98.0))  # Default to center US

def get_state_fips_prefix(state: str) -> Optional[str]:
    """Return 2-digit FIPS prefix for a US state abbreviation (subset used)."""
    mapping = {
        "IL": "17",
        "IA": "19",
        "IN": "18",
        "OH": "39",
        "NE": "31",
        "KS": "20",
        "MO": "29",
        "MN": "27",
    }
    return mapping.get(state)

def get_state_from_fips_prefix(prefix: str) -> Optional[str]:
    """Return state abbreviation for a 2-digit FIPS prefix (subset used)."""
    rev = {
        "17": "IL",
        "19": "IA",
        "18": "IN",
        "39": "OH",
        "31": "NE",
        "20": "KS",
        "29": "MO",
        "27": "MN",
    }
    return rev.get(prefix)
