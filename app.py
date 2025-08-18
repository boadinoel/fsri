from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import asyncio
from datetime import datetime

from settings import ALLOW_ORIGINS, ARGENTIS_API_KEY
from services.production import get_production_score
from services.movement import get_movement_score
from services.policy import get_policy_score
from services.biosecurity import get_biosecurity_score
from services.fuse import calculate_composite_fsri, apply_kalman_horizons
from services.ml import predict_movement_event_7d
from services.supa import upsert_daily_score, log_decision
from services.utils import get_current_utc
from services.actions import suggest as suggest_actions
from services.actions import reload_actions
from services.history import aggregate_freshness_latency

app = FastAPI(
    title="Argentis FSRI-Lite Pro",
    description="Food-System Risk Index API",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/status")
async def get_status():
    """Health check endpoint"""
    return {
        "ok": True,
        "time": get_current_utc()
    }

@app.get("/fsri")
async def get_fsri(
    crop: str = Query(..., description="Crop type: corn, srw_wheat"),
    region: str = Query(default="US", description="Region code"),
    state: str = Query(default="IL", description="State code for weather data"),
    export_flag: bool = Query(default=False, description="Export restriction flag"),
    county_fips: Optional[str] = Query(default=None, description="County FIPS code for biosecurity")
):
    """
    Get FSRI score and risk breakdown for specified crop and region
    """
    # Validate crop type
    if crop not in ["corn", "srw_wheat"]:
        raise HTTPException(status_code=400, detail="Invalid crop. Must be 'corn' or 'srw_wheat'")
    
    try:
        t0 = asyncio.get_event_loop().time()
        # Get scores from all risk components
        t_p0 = asyncio.get_event_loop().time(); production_result = await get_production_score(crop, state); t_p1 = asyncio.get_event_loop().time()
        t_m0 = asyncio.get_event_loop().time(); movement_result = await get_movement_score(region); t_m1 = asyncio.get_event_loop().time()
        t_po0 = asyncio.get_event_loop().time(); policy_result = get_policy_score(export_flag); t_po1 = asyncio.get_event_loop().time()
        t_b0 = asyncio.get_event_loop().time(); biosecurity_result = await get_biosecurity_score(county_fips, crop); t_b1 = asyncio.get_event_loop().time()
        
        # Calculate composite FSRI
        composite_result = calculate_composite_fsri(
            production_result,
            movement_result,
            policy_result,
            biosecurity_result
        )
        
        # Apply Kalman horizons
        horizons = apply_kalman_horizons(composite_result["fsri"])
        
        # Predict movement event
        movement_event = predict_movement_event_7d(movement_result["score"])

        # Freshness/latency
        freshness, latency_ms = aggregate_freshness_latency(
            {
                "production": production_result,
                "movement": movement_result,
                "policy": policy_result,
                "biosecurity": biosecurity_result,
            },
            {
                "production": (t_p1 - t_p0) * 1000.0,
                "movement": (t_m1 - t_m0) * 1000.0,
                "policy": (t_po1 - t_po0) * 1000.0,
                "biosecurity": (t_b1 - t_b0) * 1000.0,
            }
        )
        
        # Prepare response
        response = {
            "fsri": composite_result["fsri"],
            "subScores": composite_result["subScores"],
            "drivers": composite_result["drivers"],
            "timestamp": get_current_utc(),
            "confidence": composite_result["confidence"],
            "horizons": horizons,
            "movement_event_7d": movement_event,
            "freshness": freshness,
            "latency_ms": latency_ms,
        }
        
        # Upsert to database (fire and forget)
        asyncio.create_task(upsert_daily_score(
            crop=crop,
            region=region,
            production=composite_result["subScores"]["production"],
            movement=composite_result["subScores"]["movement"],
            policy=composite_result["subScores"]["policy"],
            biosecurity=composite_result["subScores"]["biosecurity"],
            fsri=composite_result["fsri"],
            drivers=composite_result["drivers"]
        ))
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating FSRI: {str(e)}")

@app.get("/signals")
async def get_signals(
    crop: str = Query(..., description="Crop type: corn, srw_wheat, poultry"),
    region: str = Query(default="US", description="Region code"),
    persona: Optional[str] = Query(default=None, description="Persona filter (e.g., traders)"),
    state: str = Query(default="IL", description="State code for weather data"),
    export_flag: bool = Query(default=False, description="Export restriction flag"),
    county_fips: Optional[str] = Query(default=None, description="County FIPS code for biosecurity")
):
    """Compute FSRI and return persona-specific suggested actions."""
    if crop not in ["corn", "srw_wheat", "poultry"]:
        raise HTTPException(status_code=400, detail="Invalid crop. Must be 'corn', 'srw_wheat', or 'poultry'")

    try:
        # Compute sub-scores using existing services
        t_p0 = asyncio.get_event_loop().time(); production_result = await get_production_score(crop if crop != "poultry" else "corn", state); t_p1 = asyncio.get_event_loop().time()
        t_m0 = asyncio.get_event_loop().time(); movement_result = await get_movement_score(region); t_m1 = asyncio.get_event_loop().time()
        t_po0 = asyncio.get_event_loop().time(); policy_result = get_policy_score(export_flag); t_po1 = asyncio.get_event_loop().time()
        t_b0 = asyncio.get_event_loop().time(); biosecurity_result = await get_biosecurity_score(county_fips, crop); t_b1 = asyncio.get_event_loop().time()

        composite_result = calculate_composite_fsri(
            production_result,
            movement_result,
            policy_result,
            biosecurity_result
        )
        horizons = apply_kalman_horizons(composite_result["fsri"])

        # Extras flags (e.g., conducive weather from biosecurity drivers)
        drivers = composite_result["drivers"]
        extras = {
            "conducive_weather": any("conducive weather" in d.lower() for d in drivers)
        }

        # Suggest actions
        actions = suggest_actions(
            crop=crop,
            region=region.lower(),
            subscores=composite_result["subScores"],
            drivers=drivers,
            extras=extras,
            persona=persona,
        )

        movement_event = predict_movement_event_7d(movement_result["score"])

        freshness, latency_ms = aggregate_freshness_latency(
            {
                "production": production_result,
                "movement": movement_result,
                "policy": policy_result,
                "biosecurity": biosecurity_result,
            },
            {
                "production": (t_p1 - t_p0) * 1000.0,
                "movement": (t_m1 - t_m0) * 1000.0,
                "policy": (t_po1 - t_po0) * 1000.0,
                "biosecurity": (t_b1 - t_b0) * 1000.0,
            }
        )

        return {
            "fsri": composite_result["fsri"],
            "subScores": composite_result["subScores"],
            "drivers": drivers,
            "timestamp": get_current_utc(),
            "confidence": composite_result["confidence"],
            "horizons": horizons,
            "movement_event_7d": movement_event,
            "actions": actions,
            "freshness": freshness,
            "latency_ms": latency_ms,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating signals: {str(e)}")

@app.post("/admin/actions/reload")
async def reload_actions_endpoint(
    argentis_api_key: str = Header(alias="ARGENTIS_API_KEY")
):
    """Hot-reload actions.yaml rules (admin, requires API key)."""
    if not ARGENTIS_API_KEY or argentis_api_key != ARGENTIS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    try:
        count = reload_actions()
        return {"status": "reloaded", "rules": count, "timestamp": get_current_utc()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload actions: {str(e)}")

@app.post("/log-decision")
async def log_decision_endpoint(
    crop: str,
    region: str,
    fsri: float,
    drivers: list,
    action: str,
    notes: str = "",
    argentis_api_key: str = Header(alias="ARGENTIS_API_KEY")
):
    """
    Log decision with FSRI context (requires API key)
    """
    # Validate API key
    if not ARGENTIS_API_KEY or argentis_api_key != ARGENTIS_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    try:
        success = await log_decision(crop, region, fsri, drivers, action, notes)
        
        if success:
            return {"status": "logged", "timestamp": get_current_utc()}
        else:
            raise HTTPException(status_code=500, detail="Failed to log decision")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error logging decision: {str(e)}")

@app.get("/export")
async def export_csv(
    crop: str = Query(..., description="Crop type"),
    region: str = Query(default="US", description="Region code"),
    days: int = Query(default=30, description="Number of days to export")
):
    """
    Export daily scores as CSV (bonus endpoint)
    """
    # This would query historical data from Supabase in production
    # For now, return a simple CSV structure
    csv_content = "date,crop,region,fsri,production,movement,policy,biosecurity\n"
    csv_content += f"2024-08-18,{crop},{region},45.2,38.5,52.1,0.0,35.8\n"
    
    return {
        "csv_data": csv_content,
        "rows": 1,
        "generated_at": get_current_utc()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
