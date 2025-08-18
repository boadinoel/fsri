from typing import Dict

def get_policy_score(export_flag: bool = False) -> Dict:
    """
    Calculate policy risk score based on export restrictions
    PoR = 70 if export_flag=true else 0
    """
    score = 70.0 if export_flag else 0.0
    
    drivers = []
    if export_flag:
        drivers.append("Export restrictions in effect")
    else:
        drivers.append("No export restrictions")
    
    return {
        "score": score,
        "drivers": drivers,
        "data_age_hours": 0  # Manual/policy data is immediate
    }
