import os
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Module-level cache
_RULES: Dict[str, List[Dict[str, Any]]] = {}
_ACTIONS_FILE = os.getenv("ACTIONS_FILE", os.path.join(os.path.dirname(os.path.dirname(__file__)), "actions.yaml"))


def _load_yaml(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError("actions.yaml must be a mapping of '<crop>.<region>' to rule lists")
            return data
    except FileNotFoundError:
        raise ValueError(f"actions.yaml not found at '{path}'")


def _validate_rules(data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    allowed_pillars = {"production", "movement", "policy", "biosecurity"}
    validated: Dict[str, List[Dict[str, Any]]] = {}

    for key, rules in data.items():
        if not isinstance(key, str) or "." not in key:
            raise ValueError(f"Invalid key '{key}'. Expected '<crop>.<region>' (e.g., 'corn.us').")
        if not isinstance(rules, list):
            raise ValueError(f"Rules for '{key}' must be a list")
        clean_rules: List[Dict[str, Any]] = []
        for idx, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise ValueError(f"Rule {idx} in '{key}' must be a mapping")
            persona = rule.get("persona")
            when = rule.get("when")
            actions = rule.get("do")
            if not persona or not isinstance(persona, str):
                raise ValueError(f"Rule {idx} in '{key}': 'persona' must be a non-empty string")
            if not isinstance(when, dict):
                raise ValueError(f"Rule {idx} in '{key}': 'when' must be a mapping")
            pillar = when.get("pillar")
            threshold = when.get("threshold")
            weather = when.get("weather", None)
            if pillar not in allowed_pillars:
                raise ValueError(f"Rule {idx} in '{key}': 'pillar' must be one of {sorted(allowed_pillars)}")
            if not isinstance(threshold, (int, float)):
                raise ValueError(f"Rule {idx} in '{key}': 'threshold' must be a number")
            if weather not in (None, "conducive"):
                raise ValueError(f"Rule {idx} in '{key}': unsupported weather flag '{weather}'")
            if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
                raise ValueError(f"Rule {idx} in '{key}': 'do' must be a list of strings")
            notify = rule.get("notify")
            if notify is not None and (not isinstance(notify, list) or not all(isinstance(n, str) for n in notify)):
                raise ValueError(f"Rule {idx} in '{key}': 'notify' must be a list of strings if provided")
            clean_rules.append({
                "persona": persona.lower(),
                "when": {"pillar": pillar, "threshold": float(threshold), **({"weather": weather} if weather else {})},
                "do": actions,
                **({"notify": notify} if notify else {}),
            })
        validated[key.lower()] = clean_rules
    return validated


def reload_actions() -> int:
    global _RULES
    data = _load_yaml(_ACTIONS_FILE)
    _RULES = _validate_rules(data)
    return sum(len(v) for v in _RULES.values())


# Load on import
try:
    if not _RULES:
        reload_actions()
except Exception:
    # Defer errors to first call site for clearer surfacing
    _RULES = {}


def suggest(
    crop: str,
    region: str,
    subscores: Dict[str, float],
    drivers: List[str],
    extras: Dict[str, Any],
    persona: Optional[str] = None,
) -> List[Dict[str, Any]]:
    key = f"{crop}.{region}".lower()
    rules = _RULES.get(key, [])
    if not rules:
        return []

    persona_filter = persona.lower() if isinstance(persona, str) else None

    out: List[Tuple[float, Dict[str, Any]]] = []
    for r in rules:
        if persona_filter and r["persona"] != persona_filter:
            continue
        cond = r["when"]
        pillar = cond["pillar"]
        threshold = cond["threshold"]
        weather = cond.get("weather")
        score = float(subscores.get(pillar, 0.0))

        # Weather flag handling (only enforced if present in rule)
        if weather == "conducive" and not extras.get("conducive_weather", False):
            continue

        if score >= threshold:
            why = f"{pillar}>={int(threshold)}"
            out.append((score, {"persona": r["persona"], "do": r["do"], "why": why, **({"notify": r.get("notify")} if r.get("notify") else {})}))

    # Sort by highest triggering pillar score first
    out.sort(key=lambda t: t[0], reverse=True)
    return [item for _, item in out]
