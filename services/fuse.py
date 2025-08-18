from typing import Dict, List
import numpy as np
from filterpy.kalman import KalmanFilter
from settings import SCORING_WEIGHTS

def confidence(freshness: dict) -> str:
    """Confidence based on per-source freshness in minutes.
    High: all usable sources < 6h and at least 2 present
    Medium: any usable source < 24h
    Low: stale or empty
    """
    ages = []
    for _, meta in (freshness or {}).items():
        age = meta.get("age_min")
        if age is None:
            continue
        ages.append(age)
    if not ages:
        return "Low"
    max_age = max(ages)
    if max_age <= 360 and len(ages) >= 2:
        return "High"
    if max_age <= 1440:
        return "Medium"
    return "Low"

def calculate_composite_fsri(
    production_result: Dict,
    movement_result: Dict, 
    policy_result: Dict,
    biosecurity_result: Dict
) -> Dict:
    """
    Calculate composite FSRI score and determine top drivers
    FSRI = round(0.40*PR + 0.35*MR + 0.05*PoR + 0.20*BR, 1)
    """
    # Extract scores
    pr_score = production_result["score"]
    mr_score = movement_result["score"] 
    por_score = policy_result["score"]
    br_score = biosecurity_result["score"]
    
    # Calculate weighted composite score
    fsri_score = (
        SCORING_WEIGHTS["production"] * pr_score +
        SCORING_WEIGHTS["movement"] * mr_score +
        SCORING_WEIGHTS["policy"] * por_score +
        SCORING_WEIGHTS["biosecurity"] * br_score
    )
    
    # Collect all drivers with their weighted contributions
    driver_contributions = []
    
    # Add drivers from each component if they contribute significantly
    if pr_score > 30:  # Production threshold
        driver_contributions.extend([
            (d, SCORING_WEIGHTS["production"] * pr_score) 
            for d in production_result["drivers"]
        ])
    
    if mr_score > 30:  # Movement threshold
        driver_contributions.extend([
            (d, SCORING_WEIGHTS["movement"] * mr_score)
            for d in movement_result["drivers"]
        ])
    
    if por_score > 0:  # Policy (always include if active)
        driver_contributions.extend([
            (d, SCORING_WEIGHTS["policy"] * por_score)
            for d in policy_result["drivers"]
        ])
    
    if br_score > 30:  # Biosecurity threshold
        driver_contributions.extend([
            (d, SCORING_WEIGHTS["biosecurity"] * br_score)
            for d in biosecurity_result["drivers"]
        ])
    
    # Sort by contribution and take top 3
    driver_contributions.sort(key=lambda x: x[1], reverse=True)
    top_drivers = [d[0] for d in driver_contributions[:3]]
    
    # If no significant drivers, use defaults
    if not top_drivers:
        top_drivers = ["Normal conditions across all risk factors"]
    
    # Determine confidence using per-source freshness in minutes; don't punish single missing
    fresh = {
        "production": {"age_min": production_result.get("data_age_hours", None) * 60 if production_result.get("data_age_hours") is not None else None},
        "movement": {"age_min": movement_result.get("data_age_hours", None) * 60 if movement_result.get("data_age_hours") is not None else None},
        "policy": {"age_min": policy_result.get("data_age_hours", None) * 60 if policy_result.get("data_age_hours") is not None else None},
        "biosecurity": {"age_min": biosecurity_result.get("data_age_hours", None) * 60 if biosecurity_result.get("data_age_hours") is not None else None},
    }
    conf = confidence(fresh)
    
    return {
        "fsri": round(fsri_score, 1),
        "subScores": {
            "production": round(pr_score, 1),
            "movement": round(mr_score, 1),
            "policy": round(por_score, 1),
            "biosecurity": round(br_score, 1)
        },
        "drivers": top_drivers,
        "confidence": conf
    }

def apply_kalman_horizons(current_fsri: float) -> Dict:
    """
    Apply simple 1D Kalman smoothing for horizon forecasts
    Returns d5, d15, d30 day projections
    """
    # Simple Kalman filter for smoothing
    kf = KalmanFilter(dim_x=2, dim_z=1)
    
    # State transition matrix (position, velocity)
    kf.F = np.array([[1., 1.],
                     [0., 1.]])
    
    # Measurement function
    kf.H = np.array([[1., 0.]])
    
    # Process noise
    kf.Q = np.array([[0.1, 0.],
                     [0., 0.01]])
    
    # Measurement noise
    kf.R = np.array([[1.0]])
    
    # Initial state
    kf.x = np.array([[current_fsri], [0.]])
    kf.P *= 10.
    
    # Predict forward for horizons
    kf.predict()
    d5_fsri = float(kf.x[0])
    
    kf.predict()
    d15_fsri = float(kf.x[0])
    
    kf.predict()
    d30_fsri = float(kf.x[0])
    
    return {
        "d5": round(max(0, min(100, d5_fsri)), 1),
        "d15": round(max(0, min(100, d15_fsri)), 1),
        "d30": round(max(0, min(100, d30_fsri)), 1)
    }
