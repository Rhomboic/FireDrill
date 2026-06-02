"""Tiny health/status web service. Containerised — see the Dockerfile.

The app is correct: it imports its routes from the routes module and reads the
port it should listen on from the PORT environment variable. How it gets built
and run (which files end up in the image, which env is set) is the Dockerfile's
job.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from routes import HEALTH_BODY  # provided by routes.py — must be in the image


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(HEALTH_BODY)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # keep stdout clean
        pass


def main() -> None:
    port = int(os.environ["PORT"])  # the container is expected to provide PORT
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
