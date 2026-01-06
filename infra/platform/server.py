from __future__ import annotations

import importlib.util
import json
import os
import urllib.request
from urllib.parse import parse_qs
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple


def _load_module(module_name: str, file_path: str):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b"{}"
    data = json.loads(raw.decode("utf-8")) if raw else {}
    if not isinstance(data, dict):
        raise ValueError("body must be a JSON object")
    return data


def _wants_html(handler: BaseHTTPRequestHandler) -> bool:
    accept = (handler.headers.get("Accept") or "").lower()
    # Browser navigation defaults to HTML; fetch can request JSON explicitly.
    return "text/html" in accept or "*/*" in accept or accept == ""


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    body = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _send_html(handler: BaseHTTPRequestHandler, status: int, html: str) -> None:
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html>
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{title}</title>
</head>
<body>
    <p>
        <a href=\"/platform/\">Platform Home</a> |
        <a href=\"/platform/incidents\">View Incidents</a> |
        <a href=\"/platform/incidents/new\">Create Incident</a> |
        <a href=\"/ui/explore\">Open Investigation View (BloodHound)</a>
    </p>
  <h1>{title}</h1>
  {body}
</body>
</html>"""


def _call_adapter_execute(adapter_base_url: str, payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{adapter_base_url.rstrip('/')}/execute",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, (json.loads(resp_body) if resp_body else {})
    except Exception as exc:
        return 502, {"error": str(exc)}


class Platform:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        self._incident_mod = _load_module(
            "incident_coordinator",
            os.path.join(repo_root, "control-layer", "incident-coordinator", "incident_coordinator.py"),
        )
        self._approval_mod = _load_module(
            "approval_gateway",
            os.path.join(repo_root, "control-layer", "approval-gateway", "approval_gateway.py"),
        )

        self.incidents = self._incident_mod.IncidentCoordinator()
        self.approvals = self._approval_mod.ApprovalGateway()

    def list_incidents(self) -> List[Dict[str, Any]]:
        return self.incidents.list_incidents()

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        return self.incidents.get_incident(incident_id)

    def create_incident(self, identity_ref: str, assumption: str, source: str) -> str:
        return self.incidents.create_incident(identity_ref=identity_ref, assumption=assumption, source=source)

    def list_approvals(self, incident_id: str) -> List[Dict[str, Any]]:
        return self.approvals.list_approvals(incident_id)

    def approve(self, incident_id: str, action_id: str, approver: str) -> Dict[str, Any]:
        return self.approvals.register_approval(incident_id, action_id, approver)

    def reject(self, incident_id: str, action_id: str, approver: str) -> Dict[str, Any]:
        return self.approvals.reject_action(incident_id, action_id, approver)

    def list_executions(self, incident_id: str) -> List[Dict[str, Any]]:
        path = os.path.join(
            self.repo_root,
            "integrations",
            "identity-governance-adapter",
            "data",
            "executions.json",
        )
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return []
        entries = data.get(incident_id, [])
        if not isinstance(entries, list):
            return []
        return entries


class Handler(BaseHTTPRequestHandler):
    platform: Platform

    def do_GET(self) -> None:  # noqa: N802
        try:
            path_only = self.path.split("?", 1)[0]
            normalized = path_only.rstrip("/")

            if normalized == "/platform":
                body = "".join(
                    [
                        "<h2>Identity Risk Response &amp; Control Platform</h2>",
                        "<p>Assume compromise → understand impact → act safely → prove what happened</p>",
                        "<h2>Feature Status</h2>",
                        "<ul>",
                        "<li>✅ Assumption-Based Incident Creation (LIVE)</li>",
                        "<li>⏳ Identity Blast Radius Analysis (NEXT)</li>",
                        "<li>⏳ Guided Decisions</li>",
                        "<li>⏳ Approval Workflow</li>",
                        "<li>⏳ Controlled Execution</li>",
                        "<li>⏳ Rollback &amp; Audit</li>",
                        "</ul>",
                        "<h2>Primary Actions</h2>",
                        "<p>",
                        "<a href=\"/platform/incidents\">View Incidents</a><br />",
                        "<a href=\"/platform/incidents/new\">Create Incident</a><br />",
                        "<a href=\"/ui/explore\">Open Investigation View (BloodHound)</a>",
                        "</p>",
                        "<h2>Integration Status</h2>",
                        "<ul>",
                        "<li>BloodHound: Connected</li>",
                        "<li>Azure AD: Not connected (testing later)</li>",
                        "</ul>",
                        "<p><i>No detection. No syncing. No live checks.</i></p>",
                    ]
                )
                html = _html_page("Platform Home", body)
                _send_html(self, 200, html)
                return

            if normalized == "/platform/incidents":
                incidents = self.platform.list_incidents()
                if not _wants_html(self):
                    _send_json(self, 200, incidents)
                    return

                if not incidents:
                    html = _html_page("Incident List", "<p>No incidents.</p>")
                    _send_html(self, 200, html)
                    return

                rows = "".join(
                    f"<tr><td>{i.get('incident_id','')}</td><td>{i.get('status','')}</td><td>{i.get('source','')}</td></tr>"
                    for i in incidents
                )
                html = _html_page(
                    "Incident List",
                    f"<table border=\"1\" cellpadding=\"6\"><tr><th>incident_id</th><th>status</th><th>source</th></tr>{rows}</table>",
                )
                _send_html(self, 200, html)
                return

            if normalized == "/platform/incidents/new":
                html = _html_page(
                    "New Incident",
                    """
<form method=\"post\" action=\"/platform/incidents\">
    <p>
        <label>identity_ref<br />
            <input type=\"text\" name=\"identity_ref\" size=\"60\" />
        </label>
    </p>
    <p>
        <label>assumption<br />
            <textarea name=\"assumption\" rows=\"6\" cols=\"60\"></textarea>
        </label>
    </p>
    <p>
        <label>source<br />
            <select name=\"source\">
                <option value=\"manual\">manual</option>
                <option value=\"api\">api</option>
                <option value=\"soc_tool\">soc_tool</option>
            </select>
        </label>
    </p>
    <p><button type=\"submit\">Create incident</button></p>
</form>
""",
                )
                _send_html(self, 200, html)
                return

            if path_only.startswith("/platform/incidents/"):
                incident_id = path_only.split("/platform/incidents/")[-1]
                if not incident_id:
                    _send_json(self, 404, {"error": {"code": "not_found", "message": "Not found"}})
                    return

                incident = self.platform.get_incident(incident_id)
                if not _wants_html(self):
                    _send_json(self, 200, incident)
                    return

                body = "".join(
                    [
                        f"<p><b>incident_id</b>: {incident.get('incident_id','')}</p>",
                        f"<p><b>status</b>: {incident.get('status','')}</p>",
                        f"<p><b>source</b>: {incident.get('source','')}</p>",
                        f"<p><b>created_at</b>: {incident.get('created_at','')}</p>",
                        f"<p><b>identity_ref</b>: {incident.get('identity_ref','')}</p>",
                        f"<p><b>assumption</b>: {incident.get('assumption','')}</p>",
                    ]
                )
                html = _html_page("Incident Detail", body)
                _send_html(self, 200, html)
                return

            _send_json(self, 404, {"error": {"code": "not_found", "message": "Not found"}})
        except Exception as exc:
            incident_mod = getattr(self.platform, "_incident_mod", None)
            IncidentError = getattr(incident_mod, "IncidentError", None) if incident_mod else None
            if IncidentError is not None and isinstance(exc, IncidentError):
                _send_json(self, 404 if getattr(exc, "code", "") == "incident_not_found" else 400, exc.to_dict())
                return
            _send_json(self, 400, {"error": {"code": "bad_request", "message": "Bad request"}})

    def do_POST(self) -> None:  # noqa: N802
        try:
            if self.path.rstrip("/") == "/platform/incidents":
                content_type = (self.headers.get("Content-Type") or "").lower()
                is_json = "application/json" in content_type

                if is_json:
                    data = _read_json_body(self)
                else:
                    length = int(self.headers.get("Content-Length") or "0")
                    raw = self.rfile.read(length).decode("utf-8") if length else ""
                    parsed = parse_qs(raw, keep_blank_values=True)
                    data = {k: (v[0] if v else "") for k, v in parsed.items()}

                incident_id = self.platform.create_incident(
                    identity_ref=str(data.get("identity_ref", "")),
                    assumption=str(data.get("assumption", "")),
                    source=str(data.get("source", "")),
                )

                if not is_json:
                    self.send_response(303)
                    self.send_header("Location", "/platform/incidents")
                    self.end_headers()
                    return

                _send_json(self, 201, {"incident_id": incident_id})
                return

            _send_json(self, 404, {"error": {"code": "not_found", "message": "Not found"}})
        except Exception as exc:
            incident_mod = getattr(self.platform, "_incident_mod", None)
            IncidentError = getattr(incident_mod, "IncidentError", None) if incident_mod else None
            if IncidentError is not None and isinstance(exc, IncidentError):
                _send_json(self, 404 if getattr(exc, "code", "") == "incident_not_found" else 400, exc.to_dict())
                return
            _send_json(self, 400, {"error": {"code": "bad_request", "message": "Bad request"}})

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    repo_root = os.environ.get("REPO_ROOT")
    if not repo_root:
        # Default assumes repo mounted at /repo in container.
        repo_root = "/repo"

    Handler.platform = Platform(repo_root)

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8081"))
    print(f"platform-app listening on http://{host}:{port}", flush=True)
    server = ThreadingHTTPServer((host, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
