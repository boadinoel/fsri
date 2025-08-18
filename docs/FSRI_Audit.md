# FSRI-Lite v0.1: Technical Audit

**Executive Summary:** This audit inventories the FSRI-Lite v0.1 system. The codebase consists of a FastAPI application with four distinct risk pillars (Production, Movement, Policy, Biosecurity), each driven by heuristics and external data sources. Scoring is a weighted average of these pillars, with a simple Kalman filter for forecasting. The system relies on environment variables for secrets and has a permissive CORS policy. While functional, the system lacks robust error handling, historical data integration, and a formal testing harness, which are key areas for v1.0 improvement.

---

### 1. Model, Heuristic, and Equation Inventory

This section details every calculation and logical model in the codebase.

*   **Final FSRI Score (`services/fuse.py:24`)**
    *   **Equation**: `FSRI = 0.40*PR + 0.35*MR + 0.05*PoR + 0.20*BR`
    *   **Description**: A weighted average of the four sub-scores. Weights are defined in `settings.py:43`.

*   **Production Risk (PR) (`services/production.py:114`)**
    *   **Equation**: `PR = clip(50 - 12*cond_z + 40*(heat_humid_hours / 84), 0, 100)`
    *   **`cond_z`**: Z-score of NASS %G+E data vs. a 60% baseline. `cond_z = (cond_gex - 60.0) / 10.0` (`services/production.py:111`).
    *   **`heat_humid_hours`**: Count of hours in next 7 days where Temp ≥ 32°C and RH ≥ 50% (`services/production.py:98`).

*   **Movement Risk (MR) (`services/movement.py:59`)**
    *   **Equation**: `MR = 100 * avg(site_risk_i)`
    *   **`site_risk_i`**: Normalized risk for a single USGS river gauge. `site_risk_i = clip((high_thresh - current_height) / (high_thresh - low_thresh), 0, 1)` (`services/movement.py:47`).
    *   **Description**: Averages the normalized risk across all monitored gauges. A value of `1.0` represents the highest risk (water level at or below `low_thresh`).

*   **Policy Risk (PoR) (`services/policy.py:8`)**
    *   **Equation**: `PoR = 70.0 if export_flag else 0.0`
    *   **Description**: A binary score triggered by a manual `export_flag` query parameter.

*   **Biosecurity Risk (BR) (`services/biosecurity.py`)**
    *   **Equation**: A tiered heuristic model:
        *   `70.0`: HPAI outbreak in the specified county AND conducive weather forecast (`services/biosecurity.py:72`).
        *   `40.0`: HPAI outbreak in county (weather not conducive) OR in the same state (`services/biosecurity.py:84`, `services/biosecurity.py:96`).
        *   `0.0`: Otherwise.
    *   **`Conducive Weather`**: At least 6 hours in the next 72 with Temp between 2-20°C and RH ≥ 60% (`services/biosecurity.py:61-67`).

*   **Kalman Filter Horizons (`services/fuse.py:88`)**
    *   **Model**: A simple 1D Kalman Filter (`filterpy.kalman.KalmanFilter`) with a constant velocity model.
    *   **Description**: Takes the current FSRI score as the initial state and predicts forward 3 steps to generate 5, 15, and 30-day horizons. This is a smoothing/trend-following model, not a true forecast incorporating new information.

*   **Movement Event 7-Day Prediction (`services/ml.py:17`)**
    *   **Equation**: `p = 1.0 / (1.0 + np.exp(-(0.08 * (MR - 50.0))))`
    *   **Description**: A logistic calibration function that transforms the current Movement Risk (MR) score into a probability. It is not a trained model but a fixed transform to map the `0-100` MR score to a `0-1` probability space.

### 2. Data Sources & Ingestion

| Data Source                 | Service Module              | Cadence / Latency                                       | Error Handling                                                                 |
| --------------------------- | --------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **Open-Meteo**              | `production`, `biosecurity` | On-demand fetch (fresh). 7-day forecast.                | Returns `None` on `httpx` error (`utils.py:34`). Callers use default/baseline values. |
| **USGS Water Services**     | `movement`                  | On-demand fetch (~2 hr old). Current conditions.        | Returns `None` on `httpx` error. Callers use a default risk of `0.3` per gauge.    |
| **NASS QuickStats**         | `production`                | On-demand fetch (weekly). In-memory cache per run.      | Returns `None` on `httpx` error. Callers use a baseline of `60%` G+E.             |
| **APHIS HPAI Data**         | `biosecurity`               | Pre-loaded from `data/ap_hpai_counties.csv`. Stale. | `FileNotFoundError` returns an empty DataFrame (`utils.py:42`). Callers score 0. |
| **Manual Input (`/fsri`)**  | `policy`, `biosecurity`     | Per-request. Immediate.                                 | FastAPI handles type validation.                                               |

### 3. Security Posture

*   **Secrets Management**
    *   Secrets (`ARGENTIS_API_KEY`, `NASS_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`) are loaded from a `.env` file via `python-dotenv` (`settings.py:4`). This is standard for development but requires a secure injection method (e.g., environment variables in a container) for production.

*   **API Authentication & Authorization**
    *   The primary `/fsri` endpoint is public and requires no authentication.
    *   The `/log-decision` endpoint is protected by a static API key (`ARGENTIS_API_KEY`) checked via an `X-Header` (`app.py:112`, `app.py:118`). This provides basic protection but is vulnerable if the key is exposed.

*   **CORS (Cross-Origin Resource Sharing)**
    *   CORS is configured in `app.py:24` via `fastapi.middleware.cors.CORSMiddleware`.
    *   `ALLOW_ORIGINS` is loaded from an environment variable, defaulting to `http://localhost:3000`. It allows all methods and headers (`allow_methods=["*"], allow_headers=["*"]`), which is permissive but acceptable for this stage.

*   **Database Security**
    *   The Supabase connection uses the `anon` key (`SUPABASE_KEY`), which is standard for client-side access.
    *   The schema (`supabase_schema.sql`) enables Row Level Security (RLS) on both tables and creates basic policies to allow public read and authenticated writes. This is a good security foundation.
