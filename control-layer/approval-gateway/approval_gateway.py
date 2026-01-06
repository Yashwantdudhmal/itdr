from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

ApprovalStatus = Literal["approved", "rejected"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _read_json_or_default(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class ApprovalGateway:
    """File-backed approval ledger.

    - Records approvals/rejections for proposed actions.
    - Stores metadata only (who/when/what).
    - No execution implied.
    """

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path is None:
            storage_path = os.path.join(os.path.dirname(__file__), "data", "approvals.json")
        self._storage_path = storage_path

    def register_approval(self, incident_id: str, action_id: str, approver: str) -> Dict[str, Any]:
        return self._record(
            incident_id=incident_id,
            action_id=action_id,
            approver=approver,
            status="approved",
        )

    def reject_action(self, incident_id: str, action_id: str, approver: str) -> Dict[str, Any]:
        return self._record(
            incident_id=incident_id,
            action_id=action_id,
            approver=approver,
            status="rejected",
        )

    def list_approvals(self, incident_id: str) -> List[Dict[str, Any]]:
        store = self._load_store()
        entries = store.get(incident_id, [])
        if not isinstance(entries, list):
            raise ValueError("approval store corrupted: expected list")
        # Stable ordering: recorded_at asc
        entries.sort(key=lambda e: e.get("recorded_at") or "")
        return entries

    def _record(self, *, incident_id: str, action_id: str, approver: str, status: ApprovalStatus) -> Dict[str, Any]:
        if not incident_id or not isinstance(incident_id, str):
            raise ValueError("incident_id must be a non-empty string")
        if not action_id or not isinstance(action_id, str):
            raise ValueError("action_id must be a non-empty string")
        if not approver or not isinstance(approver, str):
            raise ValueError("approver must be a non-empty string")

        entry = {
            "incident_id": incident_id,
            "action_id": action_id,
            "approver": approver,
            "recorded_at": _utc_now_iso(),
            "status": status,
        }

        store = self._load_store()
        store.setdefault(incident_id, []).append(entry)
        self._save_store(store)
        return entry

    def _load_store(self) -> Dict[str, Any]:
        payload = _read_json_or_default(self._storage_path, default={})
        if not isinstance(payload, dict):
            raise ValueError("approval store corrupted: expected dict")
        return payload

    def _save_store(self, store: Dict[str, Any]) -> None:
        _atomic_write_json(self._storage_path, store)
