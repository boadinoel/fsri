from typing import Dict
import numpy as np
import os
import json

CAL_PATH = os.path.join("data", "movement_calibration.json")


def _load_calibration(default_a: float = 0.08, default_b: float = 0.0) -> Dict[str, float]:
    if os.path.exists(CAL_PATH):
        try:
            with open(CAL_PATH, "r", encoding="utf-8") as f:
                js = json.load(f)
                a = float(js.get("a", default_a))
                b = float(js.get("b", default_b))
                return {"a": a, "b": b}
        except Exception:
            pass
    return {"a": default_a, "b": default_b}


_CAL = _load_calibration()


def predict_movement_event_7d(current_mr_score: float, historical_data: list = None) -> Dict:
    """
    Predict 7-day low-water likelihood using a calibrated logistic transform of MR.
    Returns probability and concise reasoning.
    """
    if historical_data is None:
        historical_data = []

    # Logistic calibration: p = 1 / (1 + exp(-(a*(mr-50)+b)))
    a = float(_CAL.get("a", 0.08))  # slope around decision region
    b = float(_CAL.get("b", 0.0))   # bias
    x = a * (float(current_mr_score) - 50.0) + b
    probability = 1.0 / (1.0 + np.exp(-x))

    # Reason string based on calibrated band
    if probability >= 0.75:
        reason = "Disruption likely given current MR calibration"
    elif probability >= 0.5:
        reason = "Elevated disruption chance from MR calibration"
    elif probability >= 0.25:
        reason = "Some disruption potential"
    else:
        reason = "Minimal disruption expected"

    return {
        "p": float(np.round(probability, 2)),
        "reason": reason,
    }

def train_movement_model(historical_data: list) -> object:
    """
    Train ML model for movement risk prediction (stub for future implementation)
    Would use features like: gauge heights, seasonal patterns, weather forecasts
    """
    # Placeholder for future ML model training
    # In production: use historical USGS data, weather patterns, seasonal cycles
    # Lazy import to avoid import cost at app startup
    from sklearn.linear_model import LinearRegression
    model = LinearRegression()
    
    # Stub training data
    if len(historical_data) > 10:
        X = np.array([[d.get('gauge_height', 7.0), d.get('temp', 20.0)] for d in historical_data[-100:]])
        y = np.array([d.get('disruption_occurred', 0) for d in historical_data[-100:]])
        model.fit(X, y)
    
    return model
