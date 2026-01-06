from typing import Any, Dict, List


def decide(input_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Decision Engine v0 (pure, deterministic).

    Constraints:
      - Stateless
      - No file I/O
      - No time/randomness
      - No side effects

    Input shape (example):
      {"identity_ref": "opaque", "reachable_assets": [], "critical_paths": []}

    Output shape:
      {"recommendations": [{"action": "revoke_sessions", ...}]}
    """
    if not isinstance(input_payload, dict):
        raise ValueError("input_payload must be a dict")
    identity_ref = input_payload.get("identity_ref")
    reachable_assets = input_payload.get("reachable_assets")
    critical_paths = input_payload.get("critical_paths")

    if not isinstance(identity_ref, str) or not identity_ref:
        raise ValueError("identity_ref must be a non-empty string")
    if not isinstance(reachable_assets, list):
        raise ValueError("reachable_assets must be a list")
    if not isinstance(critical_paths, list):
        raise ValueError("critical_paths must be a list")

    # Static, hard-coded ordering. No asset inspection logic.
    return {
        "recommendations": [
            {
                "action": "revoke_sessions",
                "safety": "safe",
                "reversible": True,
                "impact": "No service disruption expected",
            },
            {
                "action": "remove_specific_role",
                "safety": "medium",
                "reversible": True,
                "impact": "Some access may be removed for the identity",
            },
            {
                "action": "disable_identity",
                "safety": "high_risk",
                "reversible": True,
                "impact": "Identity will be unable to authenticate",
            },
        ]
    }
