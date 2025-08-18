from typing import Dict, List
from settings import USGS_BASE_URL, USGS_GAUGES
from .utils import fetch_json, clip_score

async def get_movement_score(region: str = "US") -> Dict:
    """
    Calculate movement risk score based on USGS gauge heights.
    Robust to missing gauges: skip failures, average available.
    """
    vals: List[float] = []
    fresh_min_list: List[int] = []  # minutes
    drivers: List[str] = []
    used, total = 0, 0

    for gauge_name, config in USGS_GAUGES.items():
        total += 1
        site_id = config["site_id"]
        low_thresh = config["low_threshold"]
        high_thresh = config["high_threshold"]

        params = {
            "format": "json",
            "sites": site_id,
            "parameterCd": "00065",
            "siteStatus": "active",
        }

        try:
            gauge_data = await fetch_json(USGS_BASE_URL, params)
            if not (gauge_data and "value" in gauge_data and "timeSeries" in gauge_data["value"] and gauge_data["value"]["timeSeries"]):
                continue
            ts = gauge_data["value"]["timeSeries"][0]
            if not ("values" in ts and ts["values"] and ts["values"][0]["value"]):
                continue
            values = ts["values"][0]["value"]
            current_height = float(values[-1]["value"])

            # Per-site risk in [0,1]
            if current_height <= low_thresh:
                ri = 1.0
                drivers.append(f"{gauge_name.replace('_',' ').title()}: critically low at {current_height}ft")
            elif current_height >= high_thresh:
                ri = 0.0
            else:
                ri = (high_thresh - current_height) / (high_thresh - low_thresh)

            vals.append(ri)
            fresh_min_list.append(120)  # assume ~2h old
            used += 1
        except Exception:
            continue

    if used == 0:
        return {
            "score": 0.0,
            "drivers": ["river gauges unavailable"],
            "data_age_hours": 99999 / 60.0,
            "freshness": {"age_min": 99999},
        }

    mr = round(100 * sum(vals) / used, 1)

    # Uncertainty via dispersion
    mean = sum(vals) / used
    var = sum((r - mean) ** 2 for r in vals) / used
    if var > 0.05 and not any("critically low" in d for d in drivers):
        drivers.append("High MR uncertainty (gauge dispersion)")

    # Drivers
    if mr >= 40 and not any("critically low" in d for d in drivers):
        drivers.append("low river stage limiting barge loads")
    if used < total:
        drivers.append(f"movement based on {used}/{total} gauges")

    freshness = {"age_min": max(fresh_min_list)}
    return {
        "score": mr,
        "drivers": drivers if drivers else ["Normal waterway conditions"],
        "data_age_hours": freshness["age_min"] / 60.0,
        "freshness": freshness,
    }
