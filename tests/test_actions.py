import builtins
import types
import importlib

import pytest

from services import actions as actions_mod


def test_movement_traders_rule_triggers(monkeypatch):
    # Arrange rules: corn.us traders on movement>=60
    monkeypatch.setattr(
        actions_mod, "_RULES",
        {
            "corn.us": [
                {
                    "persona": "traders",
                    "when": {"pillar": "movement", "threshold": 60.0},
                    "do": ["act"],
                }
            ]
        },
        raising=True,
    )

    subscores = {"production": 10, "movement": 65.0, "policy": 0, "biosecurity": 0}
    actions = actions_mod.suggest("corn", "us", subscores, drivers=[], extras={}, persona="traders")
    assert actions and actions[0]["persona"] == "traders"
    assert actions[0]["why"].startswith("movement>=")


def test_biosecurity_weather_rule_requires_flag(monkeypatch):
    # Arrange: poultry.us operators require weather: conducive and threshold 40
    monkeypatch.setattr(
        actions_mod, "_RULES",
        {
            "poultry.us": [
                {
                    "persona": "operators",
                    "when": {"pillar": "biosecurity", "threshold": 40.0, "weather": "conducive"},
                    "do": ["tighten sops"],
                }
            ]
        },
        raising=True,
    )

    subscores = {"production": 0, "movement": 0, "policy": 0, "biosecurity": 45.0}

    # Without flag -> no action
    actions = actions_mod.suggest("poultry", "us", subscores, drivers=[], extras={}, persona="operators")
    assert actions == []

    # With conducive_weather flag -> action triggers
    actions2 = actions_mod.suggest(
        "poultry", "us", subscores, drivers=[], extras={"conducive_weather": True}, persona="operators"
    )
    assert actions2 and actions2[0]["persona"] == "operators"
