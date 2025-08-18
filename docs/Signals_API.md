# Signals API

Purpose: translate FSRI + drivers into persona-specific suggested actions via declarative rules in `actions.yaml`.

## Endpoints

- GET `/signals?crop=corn&region=US&persona=traders[&state=IL&export_flag=false&county_fips=17031]`
  - Returns: `{ fsri, subScores, drivers, confidence, horizons, movement_event_7d, actions[] }`
  - `actions[]` items: `{ persona, do[], why, notify? }`

- POST `/admin/actions/reload` (requires header `ARGENTIS_API_KEY`)
  - Hot-reloads `actions.yaml`. Returns `{ status, rules, timestamp }`.

- Backwards-compatible: existing `GET /fsri` unchanged.

## Rules File: actions.yaml

Mapping of `<crop>.<region>` to rule list. Example:

```yaml
corn.us:
  - persona: traders
    when: { pillar: movement, threshold: 60 }
    do:
      - "Widen basis bids at river elevators by 3–8¢"
      - "Pre-allocate rail; reduce barge reliance next 7d"
    notify: ["#trading", "#logistics"]
  - persona: procurement
    when: { pillar: production, threshold: 65 }
    do:
      - "Increase hedge ratio by 5–10%"

poultry.us:
  - persona: operators
    when: { pillar: biosecurity, threshold: 40, weather: conducive }
    do:
      - "Tighten biosecurity SOPs"
      - "Freeze live-bird transfers 72h"
```

Validation rules:
- Keys must be `<crop>.<region>` (lower/upper allowed in file; normalized internally).
- `persona`: string
- `when.pillar`: one of `production|movement|policy|biosecurity`
- `when.threshold`: number
- Optional `when.weather`: `conducive`
- `do`: list of strings
- Optional `notify`: list of strings

## How actions are selected

- Compute sub-scores with existing services.
- Optional extras: `conducive_weather` inferred from Biosecurity drivers.
- Match rules for `crop.region` and requested `persona` (if provided).
- A rule triggers when `subscores[pillar] >= threshold` and optional weather flag satisfied.
- Results sorted by highest triggering pillar score first.

## Request/Response Example

Request:
```
GET /signals?crop=corn&region=US&persona=traders
```

Response (abridged):
```json
{
  "fsri": 51.2,
  "subScores": {"production": 38.5, "movement": 62.1, "policy": 0, "biosecurity": 20.3},
  "drivers": ["Low river levels", "Mild heat"],
  "confidence": "Medium",
  "horizons": {"d5": 50.8, "d15": 51.0, "d30": 51.2},
  "actions": [
    {"persona": "traders", "do": ["Widen basis bids..."], "why": "movement>=60", "notify": ["#trading","#logistics"]}
  ]
}
```

## Add/Edit Rules

1. Edit `actions.yaml` and commit.
2. Reload at runtime:
```
curl -X POST http://localhost:8000/admin/actions/reload -H "ARGENTIS_API_KEY: $ARGENTIS_API_KEY"
```

## Testing

- Unit tests: `tests/test_actions.py`
- E2E test: `tests/test_signals.py`

Run:
```
pytest -q
```
