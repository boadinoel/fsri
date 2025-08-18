from fastapi.testclient import TestClient

from app import app


def test_signals_traders_actions_trigger(monkeypatch):
    client = TestClient(app)

    # Mock scorers to avoid network
    from services import movement, production, policy, biosecurity

    async def fake_get_movement_score(region: str):
        return {"score": 62.0, "drivers": ["Low river levels"], "data_age_hours": 1}

    async def fake_get_production_score(crop: str, state: str):
        return {"score": 20.0, "drivers": ["Mild heat"], "data_age_hours": 1}

    def fake_get_policy_score(flag: bool):
        return {"score": 0.0, "drivers": []}

    async def fake_get_biosecurity_score(county_fips: str, crop: str):
        return {"score": 0.0, "drivers": []}

    monkeypatch.setattr(movement, "get_movement_score", fake_get_movement_score, raising=True)
    monkeypatch.setattr(production, "get_production_score", fake_get_production_score, raising=True)
    monkeypatch.setattr(policy, "get_policy_score", fake_get_policy_score, raising=True)
    monkeypatch.setattr(biosecurity, "get_biosecurity_score", fake_get_biosecurity_score, raising=True)

    # Ensure rules exist for corn.us traders movement>=60 (from actions.yaml)
    resp = client.get("/signals", params={"crop": "corn", "region": "US", "persona": "traders"})
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "fsri" in data and "subScores" in data and "actions" in data
    assert isinstance(data["actions"], list)
    assert any(a.get("persona") == "traders" for a in data["actions"])  # action triggered
