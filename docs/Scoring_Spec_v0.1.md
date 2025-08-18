# FSRI-Lite: Scoring Specification v0.1

**Executive Summary:** This document provides the exact mathematical and logical specification for the FSRI-Lite v0.1 score. It details the equations for each of the four pillars, the logic for generating human-readable drivers, the rules for determining confidence, and the method for horizon forecasting. This specification serves as the ground truth for the current implementation. We also propose externalizing all key thresholds and weights into a `config.yaml` file to improve maintainability and allow for faster iteration without code changes.

---

### 1. Composite FSRI Score

The final FSRI score is a weighted linear combination of its four sub-scores.

*   **File**: `services/fuse.py:24`
*   **Equation**: `FSRI = (W_pr * PR) + (W_mr * MR) + (W_por * PoR) + (W_br * BR)`
*   **Weights (`settings.py:43`)**:
    *   `W_pr` (Production): `0.40`
    *   `W_mr` (Movement): `0.35`
    *   `W_por` (Policy): `0.05`
    *   `W_br` (Biosecurity): `0.20`

### 2. Sub-Score Specifications

#### Production Risk (PR)
*   **File**: `services/production.py:114`
*   **Equation**: `PR = clip(50 - 12*cond_z + 40*(heat_humid_hours / 84), 0, 100)`
*   **Thresholds & Constants**:
    *   NASS %G+E Baseline: `60.0`
    *   NASS Z-Score Divisor: `10.0`
    *   Heat/Humidity Temp Threshold: `32.0` °C
    *   Heat/Humidity RH Threshold: `50.0` %
    *   Normalization Period for Heat/Humidity: `84` hours (50% of 7 days)
*   **Driver Logic**:
    *   `"High heat-humidity stress: {h} hours forecast"` if `heat_humid_hours > 20`.
    *   `"NASS %G+E: {gex:.0f}%"` if NASS data is available.
    *   `"NASS crop condition unavailable (baseline)"` if NASS data is missing.

#### Movement Risk (MR)
*   **File**: `services/movement.py:41`
*   **Equation**: `MR = 100 * avg(site_risk_i)` where `site_risk_i = clip((H_high - H_current) / (H_high - H_low), 0, 1)`.
*   **Thresholds**: Defined per-gauge in `settings.py:18`. For example, `mississippi_memphis` has `low_threshold: 5.0` and `high_threshold: 10.0`.
*   **Driver Logic**:
    *   `"{gauge_name}: critically low at {h}ft"` if `H_current <= H_low`.
    *   `"{gauge_name}: data unavailable"` if the API call fails.
    *   `"High MR uncertainty (gauge dispersion)"` if variance of `site_risk_i` > `0.05`.

#### Policy Risk (PoR)
*   **File**: `services/policy.py:8`
*   **Equation**: `PoR = 70.0 if export_flag else 0.0`
*   **Driver Logic**:
    *   `"Export restrictions in effect"` if `export_flag` is true.

#### Biosecurity Risk (BR)
*   **File**: `services/biosecurity.py:72`
*   **Equation**: Tiered heuristic.
*   **Thresholds & Constants**:
    *   High Risk Score: `70.0`
    *   Moderate Risk Score: `40.0`
    *   Recent Outbreak Window: `30` days.
    *   Conducive Weather Temp Range: `2.0` to `20.0` °C.
    *   Conducive Weather RH Threshold: `60.0` %.
    *   Conducive Weather Duration: `6` hours over a 72-hour forecast.
*   **Driver Logic**:
    *   `"HPAI outbreak in county with conducive weather (next 72h)"` for high risk.
    *   `"HPAI outbreak in county (weather not conducive)"` for moderate risk.
    *   `"HPAI outbreaks detected in state"` for proximity-based moderate risk.

### 3. Confidence & Horizons

*   **Confidence (`services/utils.py:14`)**: Determined by the maximum age of any data input.
    *   `High`: Max age < 6 hours.
    *   `Medium`: Max age < 24 hours.
    *   `Low`: Max age >= 24 hours.
*   **Horizons (`services/fuse.py:88`)**: A 1D Kalman Filter with a constant velocity model projects the current FSRI score forward. The state transition matrix `F` is `[[1., 1.], [0., 1.]]`, effectively adding the estimated velocity to the position at each prediction step.

### 4. Proposal: Externalize Configuration

To improve maintainability, all magic numbers, weights, and thresholds should be moved from `settings.py` and service modules into a single `config.yaml` file.

**Proposed `config.yaml` structure:**

```yaml
# config.yaml

scoring_weights:
  production: 0.40
  movement: 0.35
  policy: 0.05
  biosecurity: 0.20

production_risk:
  nass_baseline_gex: 60.0
  nass_z_score_divisor: 10.0
  heat_stress_temp_c: 32.0
  heat_stress_rh_pct: 50.0
  heat_stress_norm_hours: 84
  driver_heat_hours_threshold: 20

movement_risk:
  driver_variance_threshold: 0.05
  default_risk_on_error: 0.3
  usgs_gauges:
    mississippi_memphis:
      site_id: "07032000"
      low_threshold: 5.0
      high_threshold: 10.0
    # ... other gauges

policy_risk:
  export_flag_score: 70.0

biosecurity_risk:
  high_risk_score: 70.0
  moderate_risk_score: 40.0
  outbreak_window_days: 30
  conducive_temp_min_c: 2.0
  conducive_temp_max_c: 20.0
  conducive_rh_min_pct: 60.0
  conducive_duration_hours: 6

confidence_rules:
  high_max_age_hours: 6
  medium_max_age_hours: 24
```

This change would require adding `PyYAML` to `requirements.txt` and creating a utility function to load this config at startup.
