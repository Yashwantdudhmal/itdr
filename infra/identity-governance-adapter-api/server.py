from __future__ import annotations

import importlib.util
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict


def _json_response(handler: BaseHTTPRequestHandler, *, status: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    data = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    return data


def _load_adapter(adapter_path: str):
    spec = importlib.util.spec_from_file_location("identity_governance_adapter", adapter_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load adapter")
    module = importlib.util.module_from_spec(spec)
    sys.modules["identity_governance_adapter"] = module
    spec.loader.exec_module(module)
    return module


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/execute":
            try:
                payload = _read_json_body(self)
                incident_id = payload.get("incident_id")
                action_id = payload.get("action_id")
                identity_ref = payload.get("identity_ref")
                parameters = payload.get("parameters") or {}

                if not isinstance(incident_id, str) or not incident_id:
                    raise ValueError("incident_id must be a non-empty string")
                if not isinstance(action_id, str) or not action_id:
                    raise ValueError("action_id must be a non-empty string")
                if not isinstance(identity_ref, str) or not identity_ref:
                    raise ValueError("identity_ref must be a non-empty string")
                if not isinstance(parameters, dict):
                    raise ValueError("parameters must be an object")

                adapter_path = os.environ.get("ADAPTER_PATH", "/app/client.py")
                adapter_module = _load_adapter(adapter_path)
                adapter = adapter_module.IdentityGovernanceAdapter(
                    base_url=os.environ.get("MIDPOINT_BASE_URL", "http://midpoint:8080"),
                    username=os.environ.get("MIDPOINT_USERNAME", "administrator"),
                    password=os.environ.get("MIDPOINT_PASSWORD", "5ecr3t"),
                    max_attempts=1,
                )

                result = adapter.execute(
                    incident_id=incident_id,
                    action_id=action_id,
                    identity_ref=identity_ref,
                    parameters=parameters,
                )
                _json_response(self, status=200, payload=result)
            except Exception as exc:
                _json_response(self, status=400, payload={"error": str(exc)})
            return

        _json_response(self, status=404, payload={"error": "not found"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/health":
            _json_response(self, status=200, payload={"status": "ok"})
            return
        _json_response(self, status=404, payload={"error": "not found"})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        # Keep logs quiet by default.
        return


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8090"))
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
