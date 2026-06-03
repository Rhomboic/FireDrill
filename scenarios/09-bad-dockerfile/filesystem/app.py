"""Tiny health/status web service. Containerised — see the Dockerfile.

The app is correct. It imports its routes from the routes module, reads the port
it should listen on from the PORT environment variable, and serves two endpoints:

  GET /health   -> 200 {"status":"ok"}              (a pure in-process check)
  GET /version  -> 200 {"service":...,"version":...} read from a packaged asset

The /version payload is NOT hardcoded — it is read at request time from the
templates/version.json asset that ships alongside the code. Which files end up in
the image (the app module, the routes module, AND that templates/ asset dir) and
which env is set is the Dockerfile's job. If an asset the app reads at runtime is
not COPYed into the image, the process still starts and /health still answers —
the missing file only surfaces when that endpoint is actually hit.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from routes import HEALTH_BODY  # provided by routes.py — must be in the image

# The version asset is resolved relative to this module, so it is found wherever
# the app is run from — but only if the Dockerfile actually COPYs templates/ in.
VERSION_ASSET = Path(__file__).resolve().parent / "templates" / "version.json"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(HEALTH_BODY)
        elif self.path == "/version":
            # Read the packaged asset on every request. If templates/version.json
            # was never COPYed into the image this raises and we answer 500 —
            # the endpoint is broken even though the container is up and /health
            # is green.
            try:
                body = VERSION_ASSET.read_bytes()
            except OSError:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"version asset missing"}')
                return
            # Validate/normalize so a corrupt asset is also a 500, not a 200.
            try:
                data = json.loads(body)
                payload = json.dumps(
                    {"service": data["service"], "version": data["version"]}
                ).encode()
            except (ValueError, KeyError):
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"version asset malformed"}')
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # keep stdout clean
        pass


def main() -> None:
    port = int(os.environ["PORT"])  # the container is expected to provide PORT
    server = HTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
