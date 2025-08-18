from typing import Dict, Any
from datetime import datetime
from supabase import create_client, Client
from settings import SUPABASE_URL, SUPABASE_KEY
from .utils import get_current_utc

# Initialize Supabase client
supabase: Client = None

def init_supabase():
    """Initialize Supabase client"""
    global supabase
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        print("Warning: Supabase credentials not configured")

async def upsert_daily_score(
    crop: str,
    region: str,
    production: float,
    movement: float,
    policy: float,
    biosecurity: float,
    fsri: float,
    drivers: list
) -> bool:
    """
    Upsert daily FSRI score to Supabase scores_daily table
    Idempotent - one row per day/crop/region
    """
    if not supabase:
        init_supabase()
        if not supabase:
            print("Supabase not configured, skipping database insert")
            return False
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        data = {
            "dt": today,
            "crop": crop,
            "region": region,
            "production": production,
            "movement": movement,
            "policy": policy,
            "biosecurity": biosecurity,
            "fsri": fsri,
            "drivers": drivers
        }
        
        result = supabase.table("scores_daily").upsert(
            data,
            on_conflict="dt,crop,region"
        ).execute()
        
        return True
    except Exception as e:
        print(f"Error upserting daily score: {e}")
        return False

async def log_decision(
    crop: str,
    region: str,
    fsri: float,
    drivers: list,
    action: str,
    notes: str = ""
) -> bool:
    """
    Log decision to Supabase decisions_log table
    """
    if not supabase:
        init_supabase()
        if not supabase:
            print("Supabase not configured, skipping decision log")
            return False
    
    try:
        data = {
            "ts": get_current_utc(),
            "crop": crop,
            "region": region,
            "fsri": fsri,
            "drivers": drivers,
            "action": action,
            "notes": notes
        }
        
        result = supabase.table("decisions_log").insert(data).execute()
        return True
    except Exception as e:
        print(f"Error logging decision: {e}")
        return False
