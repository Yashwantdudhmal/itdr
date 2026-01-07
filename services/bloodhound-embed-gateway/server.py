from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        accel_target: str | None = None

        if parsed.path == "/embed/bloodhound":
            qs = parse_qs(parsed.query, keep_blank_values=True)
            identity = (qs.get("identity") or [""])[0]
            identity_enc = quote(identity, safe="")
            accel_target = f"/_internal/bloodhound/?identity={identity_enc}"
        elif parsed.path == "/embed/midpoint" or parsed.path.startswith("/embed/midpoint/"):
            # Preserve any subpath for MidPoint static assets and navigation.
            suffix = parsed.path[len("/embed/midpoint") :]
            if suffix == "":
                suffix = "/"
            accel_target = f"/_internal/midpoint{suffix}"

        if not accel_target:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("X-Accel-Redirect", accel_target)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8082"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"bloodhound-embed-gateway listening on http://{host}:{port}", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
