from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

IncidentSource = Literal["manual", "api", "soc_tool"]
IncidentStatus = Literal["open"]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class IncidentError(Exception):
    code: str = "incident_error"
    message: str = "Incident error"

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message}}


class IncidentNotFound(IncidentError):
    code = "incident_not_found"
    message = "Incident not found"


class InvalidSource(IncidentError):
    code = "invalid_source"
    message = "source must be one of: manual | api | soc_tool"


class IncidentCoordinator:
    """Assumption-based incident declaration (Feature #1 only).

    - identity_ref is stored as an opaque string (no parsing, no validation).
    - assumption is free text.
    - source is constrained to: manual | api | soc_tool.
    - status is always: open.
    - persisted as JSON files (file-backed).
    """

    _ALLOWED_SOURCES: set[str] = {"manual", "api", "soc_tool"}

    def __init__(self, storage_dir: Optional[str] = None) -> None:
        if storage_dir is None:
            storage_dir = os.path.join(os.path.dirname(__file__), "data", "incidents")
        self._storage_dir = storage_dir

    def create_incident(self, identity_ref: str, assumption: str, source: str) -> str:
        if source not in self._ALLOWED_SOURCES:
            raise InvalidSource()

        incident_id = str(uuid.uuid4())
        record: Dict[str, Any] = {
            "incident_id": incident_id,
            "identity_ref": identity_ref,
            "assumption": assumption,
            "source": source,
            "status": "open",
            "created_at": _utc_now_iso(),
        }
        _atomic_write_json(self._incident_path(incident_id), record)
        return incident_id

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        path = self._incident_path(incident_id)
        if not os.path.exists(path):
            raise IncidentNotFound()
        raw = _read_json(path)
        if not isinstance(raw, dict):
            raise IncidentError("incident record corrupted")
        return self._normalize_record(raw)

    def list_incidents(self) -> List[Dict[str, Any]]:
        if not os.path.isdir(self._storage_dir):
            return []

        incidents: List[Dict[str, Any]] = []
        for name in os.listdir(self._storage_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self._storage_dir, name)
            try:
                raw = _read_json(path)
                if isinstance(raw, dict):
                    incidents.append(self._normalize_record(raw))
            except Exception:
                continue

        incidents.sort(key=lambda r: r.get("created_at", ""))
        return incidents

    def _incident_path(self, incident_id: str) -> str:
        return os.path.join(self._storage_dir, f"{incident_id}.json")

    @staticmethod
    def _normalize_record(raw: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "incident_id": str(raw.get("incident_id", "")),
            "identity_ref": str(raw.get("identity_ref", "")),
            "assumption": str(raw.get("assumption", "")),
            "source": str(raw.get("source", "")),
            "status": "open",
            "created_at": str(raw.get("created_at", "")),
        }
