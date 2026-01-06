from __future__ import annotations

import importlib.util
import json
import os
from typing import Any, Dict, List, Optional


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_adapter(adapter_path: str):
    spec = importlib.util.spec_from_file_location("identity_governance_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute_approved_actions_once(
    *,
    midpoint_base_url: str,
    midpoint_username: str,
    midpoint_password: str,
) -> List[Dict[str, Any]]:
    """One-way orchestration path: approval -> execution.

    - Execution happens only after approval.
    - No retries/no loops beyond processing the current ledger snapshot.
    - No background jobs.
    """

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    approvals_path = os.path.join(repo_root, "control-layer", "approval-gateway", "data", "approvals.json")
    incidents_path = os.path.join(repo_root, "control-layer", "incident-coordinator", "data", "incidents.json")
    adapter_path = os.path.join(repo_root, "integrations", "identity-governance-adapter", "client.py")

    approvals_by_incident = _load_json(approvals_path, default={})
    incidents_by_id = _load_json(incidents_path, default={})

    adapter_module = _load_adapter(adapter_path)
    adapter = adapter_module.IdentityGovernanceAdapter(
        base_url=midpoint_base_url,
        username=midpoint_username,
        password=midpoint_password,
        max_attempts=1,
    )

    supported = {"revoke_sessions", "disable_identity", "remove_role"}
    results: List[Dict[str, Any]] = []

    for incident_id, entries in approvals_by_incident.items():
        if not isinstance(entries, list):
            continue
        incident = incidents_by_id.get(incident_id)
        if not isinstance(incident, dict):
            continue
        identity_ref = incident.get("identity_ref")
        if not isinstance(identity_ref, str) or not identity_ref:
            continue

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("status") != "approved":
                continue

            action_id = entry.get("action_id")
            if action_id not in supported:
                continue

            exec_result = adapter.execute(
                incident_id=incident_id,
                action_id=action_id,
                identity_ref=identity_ref,
                parameters={},
            )
            results.append(
                {
                    "incident_id": incident_id,
                    "action_id": action_id,
                    "execution": exec_result,
                }
            )

    return results


if __name__ == "__main__":
    base_url = os.environ.get("MIDPOINT_BASE_URL", "http://midpoint:8080")
    username = os.environ.get("MIDPOINT_USERNAME", "administrator")
    password = os.environ.get("MIDPOINT_PASSWORD", "5ecr3t")
    out = execute_approved_actions_once(
        midpoint_base_url=base_url,
        midpoint_username=username,
        midpoint_password=password,
    )
    print(json.dumps(out, indent=2))
