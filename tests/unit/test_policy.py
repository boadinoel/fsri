from services.policy import get_policy_risk

def test_get_policy_risk_with_flag():
    """Test that policy risk is high when the export flag is true."""
    risk, drivers = get_policy_risk(export_flag=True)
    assert risk == 70.0
    assert len(drivers) == 1
    assert "Export restrictions in effect" in drivers[0]

def test_get_policy_risk_without_flag():
    """Test that policy risk is zero when the export flag is false."""
    risk, drivers = get_policy_risk(export_flag=False)
    assert risk == 0.0
    assert len(drivers) == 0
