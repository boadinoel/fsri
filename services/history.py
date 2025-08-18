from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

import httpx
import pandas as pd
import numpy as np
import os
from settings import USGS_GAUGES, OPEN_METEO_BASE_URL
from .utils import get_state_coords


async def get_usgs_history(site_id: str, days: int = 90) -> Optional[dict]:
    """Fetches daily average gauge height from USGS Water Services for a given site.

    Args:
        site_id: The USGS site identifier.
        days: The number of past days of data to retrieve.

    Returns:
        A dictionary containing the JSON response from the API, or None on error.
    """
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    # Parameter '00065' is gauge height in feet.
    url = (
        f"https://waterservices.usgs.gov/nwis/dv/"
        f"?format=json&sites={site_id}"
        f"&startDT={start_date.isoformat()}&endDT={end_date.isoformat()}"
        f"&parameterCd=00065"
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        print(f"HTTP error fetching USGS history for site {site_id}: {e}")
        return None
    except httpx.RequestError as e:
        print(f"Request error fetching USGS history for site {site_id}: {e}")
        return None


async def _fetch_openmeteo_daily(lat: float, lon: float, days: int = 90) -> Optional[dict]:
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    # Use archive API for historical ranges; forecast API only for near-present
    if start_date < (end_date - timedelta(days=7)):
        base_url = "https://archive-api.open-meteo.com/v1/archive"
    else:
        base_url = OPEN_METEO_BASE_URL
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "precipitation_sum,temperature_2m_mean,relative_humidity_2m_mean",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(base_url, params=params, timeout=20.0)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"Error fetching Open-Meteo daily: {e}")
        return None


def _spi_30(precip: pd.Series) -> pd.Series:
    # 30-day rolling z-score of cumulative precip anomaly
    roll = precip.rolling(window=30, min_periods=15).sum()
    mean = roll.rolling(window=180, min_periods=60).mean()
    std = roll.rolling(window=180, min_periods=60).std()
    z = (roll - mean) / (std.replace(0, np.nan))
    return z


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute movement features on a daily dataframe with columns:
    ['gauge_ft','precip_mm','temp_c','rh'] and a DatetimeIndex (date).
    """
    out = df.copy().sort_index()
    # Ensure DatetimeIndex for rolling and isocalendar
    out.index = pd.to_datetime(out.index)
    out["ma_7"] = out["gauge_ft"].rolling(7, min_periods=3).mean()
    out["ma_30"] = out["gauge_ft"].rolling(30, min_periods=10).mean()
    out["delta_3"] = out["gauge_ft"].diff(3)
    out["delta_7"] = out["gauge_ft"].diff(7)
    out["spi_30"] = _spi_30(out["precip_mm"].fillna(0.0))
    # Seasonality: week-of-year sin/cos
    woy = out.index.isocalendar().week.astype(float)
    out["woy_sin"] = np.sin(2 * np.pi * woy / 52.0)
    out["woy_cos"] = np.cos(2 * np.pi * woy / 52.0)
    return out


async def fetch_history(days: int = 180, state: str = "IL", out_dir: str = "data") -> Dict[str, str]:
    """Fetch USGS and Open-Meteo history, compute features, persist CSV/Parquet per site.
    Returns mapping of site_id -> saved CSV path.
    """
    os.makedirs(out_dir, exist_ok=True)
    lat, lon = get_state_coords(state)

    om = await _fetch_openmeteo_daily(lat, lon, days)
    if not om or "daily" not in om:
        raise RuntimeError("Open-Meteo daily fetch failed")
    days_list = [datetime.fromisoformat(d).date() for d in om["daily"]["time"]]
    precip = om["daily"].get("precipitation_sum", [])
    tmean = om["daily"].get("temperature_2m_mean", [])
    rhmean = om["daily"].get("relative_humidity_2m_mean", [])
    wx_df = pd.DataFrame({
        "date": days_list,
        "precip_mm": precip,
        "temp_c": tmean,
        "rh": rhmean,
    }).set_index("date")

    results: Dict[str, str] = {}
    for g in list(USGS_GAUGES.values())[:4]:  # limit 2–4 sites
        raw = await get_usgs_history(g["site_id"], days)
        if not raw or "value" not in raw:
            continue
        # Parse USGS daily values
        ts = raw["value"].get("timeSeries", [])
        values = []
        for series in ts:
            pts = series.get("values", [])
            if not pts:
                continue
            for v in pts[0].get("value", []):
                try:
                    d = datetime.fromisoformat(v["dateTime"]).date()
                except Exception:
                    d = datetime.strptime(v["dateTime"].split("T")[0], "%Y-%m-%d").date()
                values.append((d, float(v.get("value") or np.nan)))
        if not values:
            continue
        usgs_df = pd.DataFrame(values, columns=["date", "gauge_ft"]).set_index("date")
        df = usgs_df.join(wx_df, how="left")
        feat = build_features(df)

        base = os.path.join(out_dir, f"usgs_{g['site_id']}_{days}d")
        csv_path = f"{base}.csv"
        parquet_path = f"{base}.parquet"
        feat.to_csv(csv_path, index=True)
        try:
            feat.to_parquet(parquet_path, index=True)
        except Exception:
            # Parquet optional
            parquet_path = ""
        results[g["site_id"]] = csv_path

    return results


def aggregate_freshness_latency(component_results: Dict[str, Dict], latencies_ms: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Helper to build freshness (hours) and latency_ms maps from service outputs.
    component_results: keys like 'production','movement','policy','biosecurity' with optional data_age_hours.
    latencies_ms: measured wall-clock ms for each component.
    """
    freshness = {}
    for k, v in component_results.items():
        if isinstance(v, dict) and "data_age_hours" in v:
            freshness[k] = float(v.get("data_age_hours", 0))
    return freshness, {k: float(lat) for k, lat in latencies_ms.items()}
