from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse


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


def _read_form_body(handler: BaseHTTPRequestHandler) -> Dict[str, str]:
    length = int(handler.headers.get("Content-Length") or "0")
    raw = handler.rfile.read(length) if length else b""
    parsed = parse_qs(raw.decode("utf-8"), keep_blank_values=True)
    return {k: (v[0] if v else "") for k, v in parsed.items()}


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


def _redirect(handler: BaseHTTPRequestHandler, location: str) -> None:
    handler.send_response(303)
    handler.send_header("Location", location)
    handler.end_headers()


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


def _is_form_post(handler: BaseHTTPRequestHandler) -> bool:
    content_type = (handler.headers.get("Content-Type") or "").lower()
    return content_type.startswith("application/x-www-form-urlencoded") or content_type.startswith(
        "multipart/form-data"
    )


class PlatformApp:
    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root
        incident_path = os.path.join(repo_root, "control-layer", "incident-coordinator", "incident_coordinator.py")
        self._incident_mod = _load_module("incident_coordinator_feature1", incident_path)
        self.incidents = self._incident_mod.IncidentCoordinator()

    def create_incident(self, identity_ref: str, assumption: str, source: str) -> str:
        return self.incidents.create_incident(identity_ref=identity_ref, assumption=assumption, source=source)

    def get_incident(self, incident_id: str) -> Dict[str, Any]:
        return self.incidents.get_incident(incident_id)

    def list_incidents(self) -> List[Dict[str, Any]]:
        return self.incidents.list_incidents()


class Handler(BaseHTTPRequestHandler):
    platform: PlatformApp

    def do_GET(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path in ("", "/"):
                _redirect(self, "/platform/")
                return

            if parsed.path == "/platform/":
                body = "".join(
                    [
                        "<h2>Identity Risk Response & Control Platform</h2>",
                        "<p>Assume compromise → understand impact → act safely → prove what happened</p>",
                        "<h2>Feature Status</h2>",
                        "<ul>",
                        "<li>✅ Assumption-Based Incident Creation (LIVE)</li>",
                        "<li>⏳ Identity Blast Radius Analysis (NEXT)</li>",
                        "<li>⏳ Guided Decisions</li>",
                        "<li>⏳ Approval Workflow</li>",
                        "<li>⏳ Controlled Execution</li>",
                        "<li>⏳ Rollback & Audit</li>",
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

            if path == "/platform/incidents":
                incidents = self.platform.list_incidents()
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
                    """<table border=\"1\" cellpadding=\"6\">
<tr><th>incident_id</th><th>status</th><th>source</th></tr>
"""
                    + rows
                    + "</table>",
                )
                _send_html(self, 200, html)
                return

            if path == "/platform/incidents/new":
                html = _html_page(
                    "New Incident",
                    """
<form method=\"post\" action=\"/api/incidents\">
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

            if path == "/api/incidents":
                _send_json(self, 200, self.platform.list_incidents())
                return

            if path.startswith("/api/incidents/"):
                incident_id = path.split("/api/incidents/")[-1]
                incident = self.platform.get_incident(incident_id)
                _send_json(self, 200, incident)
                return

            _send_json(self, 404, {"error": {"code": "not_found", "message": "Not found"}})
        except Exception as exc:
            self._send_exception(exc)

    def do_POST(self) -> None:  # noqa: N802
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")

            if path != "/api/incidents":
                _send_json(self, 404, {"error": {"code": "not_found", "message": "Not found"}})
                return

            if _is_form_post(self):
                data = _read_form_body(self)
            else:
                data = _read_json_body(self)

            incident_id = self.platform.create_incident(
                identity_ref=str(data.get("identity_ref", "")),
                assumption=str(data.get("assumption", "")),
                source=str(data.get("source", "")),
            )

            if _is_form_post(self):
                _redirect(self, "/platform/incidents")
                return

            _send_json(self, 201, {"incident_id": incident_id})
        except Exception as exc:
            self._send_exception(exc)

    def _send_exception(self, exc: Exception) -> None:
        incident_mod = getattr(self.platform, "_incident_mod", None)
        if incident_mod is not None:
            IncidentError = getattr(incident_mod, "IncidentError", None)
            if IncidentError is not None and isinstance(exc, IncidentError):
                _send_json(self, 400 if getattr(exc, "code", "") != "incident_not_found" else 404, exc.to_dict())
                return

        if isinstance(exc, ValueError):
            _send_json(self, 400, {"error": {"code": "bad_request", "message": str(exc)}})
            return

        _send_json(self, 500, {"error": {"code": "internal_error", "message": "Internal error"}})


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Platform App (Feature #1: assumption-based incidents)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args(argv)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    platform = PlatformApp(repo_root)

    Handler.platform = platform
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Platform app listening on http://{args.host}:{args.port}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
