"""Identity governance adapter (execution-only).

Translates approved actions into identity governance API calls.

No decision logic. No approvals. No identity discovery.
Returns execution result metadata only.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional


class IdentityGovernanceAdapter:
    """Execution-only adapter for midPoint's REST API.

    Notes:
    - `identity_ref` is opaque to the rest of the system.
      The adapter treats it as an engine-resolvable reference (e.g., an object identifier).
    - This module intentionally does not persist anything except execution result metadata.
    """

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout_seconds: int = 30,
        max_attempts: int = 1,
        storage_path: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), "data", "executions.json")
        self.storage_path = storage_path

    def execute(
        self,
        *,
        incident_id: str,
        action_id: str,
        identity_ref: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an approved action.

        Contract-oriented I/O:
        Input: incident_id, action_id, identity_ref (opaque), parameters (opaque map)
        Output: execution_id, status, reversible, revert_hint
        """
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be a dict")

        execution_id = str(uuid.uuid4())

        # Map action_id -> midPoint call.
        try:
            if action_id == "revoke_sessions":
                self._call_midpoint_revoke_sessions(identity_ref=identity_ref, parameters=parameters)
                result = {
                    "execution_id": execution_id,
                    "status": "success",
                    "reversible": True,
                    "revert_hint": {},
                }
            elif action_id == "disable_identity":
                self._call_midpoint_disable_identity(identity_ref=identity_ref, parameters=parameters)
                result = {
                    "execution_id": execution_id,
                    "status": "success",
                    "reversible": True,
                    "revert_hint": {},
                }
            elif action_id == "remove_role":
                self._call_midpoint_remove_role(identity_ref=identity_ref, parameters=parameters)
                result = {
                    "execution_id": execution_id,
                    "status": "success",
                    "reversible": True,
                    "revert_hint": {},
                }
            else:
                raise ValueError(f"unsupported action_id: {action_id}")
        except Exception:
            result = {
                "execution_id": execution_id,
                "status": "failed",
                "reversible": False,
                "revert_hint": {},
            }

        self._record_execution_result(
            incident_id=incident_id,
            action_id=action_id,
            identity_ref=identity_ref,
            parameters=parameters,
            execution_result=result,
        )
        return result

    def revert_execution(self, execution_id: str) -> Dict[str, Any]:
        """Rollback placeholder.

        Not implemented in this phase; rollback is execution-engine dependent.
        """
        raise NotImplementedError("revert_execution is execution-engine dependent and not implemented")

    # --- midPoint calls (minimal) ---

    def _call_midpoint_revoke_sessions(self, *, identity_ref: str, parameters: Dict[str, Any]) -> None:
        # Implementation intentionally minimal and configuration-driven.
        # Calls a generic endpoint that can be adapted to the deployed engine configuration.
        path = parameters.get("midpoint_path") or "/ws/rest/rpc/invalidateSessions"
        body = {"identity_ref": identity_ref}
        self._request(path, method="POST", body=body)

    def _call_midpoint_disable_identity(self, *, identity_ref: str, parameters: Dict[str, Any]) -> None:
        # Treat identity_ref as engine-side identifier.
        oid = urllib.parse.quote(identity_ref, safe="")
        path = parameters.get("midpoint_path") or f"/ws/rest/users/{oid}"
        body = parameters.get("midpoint_body") or {"operation": "disable"}
        self._request(path, method="POST", body=body)

    def _call_midpoint_remove_role(self, *, identity_ref: str, parameters: Dict[str, Any]) -> None:
        oid = urllib.parse.quote(identity_ref, safe="")
        role_ref = parameters.get("role_ref")
        path = parameters.get("midpoint_path") or f"/ws/rest/users/{oid}"
        body = parameters.get("midpoint_body") or {"operation": "remove_role", "role_ref": role_ref}
        self._request(path, method="POST", body=body)

    # --- http + persistence ---

    def _request(self, path: str, *, method: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        # Basic auth (midPoint commonly supports it); secrets come from config.
        auth = (f"{self.username}:{self.password}").encode("utf-8")
        headers["Authorization"] = "Basic " + _b64(auth)

        data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)

        last_exc: Optional[Exception] = None
        for attempt in range(1, max(1, self.max_attempts) + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    resp_body = resp.read().decode("utf-8")
                    return json.loads(resp_body) if resp_body else {}
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                last_exc = exc
                if attempt >= max(1, self.max_attempts):
                    raise
                time.sleep(0.5)
        raise RuntimeError("request failed") from last_exc

    def _record_execution_result(
        self,
        *,
        incident_id: str,
        action_id: str,
        identity_ref: str,
        parameters: Dict[str, Any],
        execution_result: Dict[str, Any],
    ) -> None:
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        existing = {}
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
                if not isinstance(existing, dict):
                    existing = {}

        existing.setdefault(incident_id, []).append(
            {
                "incident_id": incident_id,
                "action_id": action_id,
                "identity_ref": identity_ref,
                "parameters": parameters,
                "result": execution_result,
            }
        )

        tmp_path = f"{self.storage_path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, sort_keys=True)
        os.replace(tmp_path, self.storage_path)


def _b64(data: bytes) -> str:
    # Avoid importing base64 globally to keep the module small and explicit.
    import base64

    return base64.b64encode(data).decode("ascii")
