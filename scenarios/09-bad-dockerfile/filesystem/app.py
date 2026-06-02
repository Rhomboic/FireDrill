"""Tiny health/status web service. Containerised — see the Dockerfile.

The app is correct: it imports its routes from the routes module, reads the port
it should listen on from the PORT environment variable, and installs a SIGTERM
handler so it shuts down gracefully when the orchestrator stops the container.
How it gets built and run (which files end up in the image, which env is set,
and crucially whether the CMD process actually *receives* that SIGTERM) is the
Dockerfile's job.
"""

import os
import signal
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
    server = HTTPServer(("0.0.0.0", port), Handler)

    # Graceful shutdown: when the orchestrator stops the container it sends
    # SIGTERM to the CMD process. Stop serving, close the socket, and exit
    # cleanly (code 0) instead of waiting to be SIGKILLed. The handler runs in
    # the same (main) thread as serve_forever, so it raises SystemExit to break
    # out of the serve loop rather than calling server.shutdown() (which would
    # deadlock when invoked from within that thread). This only fires if the CMD
    # process is actually *us* — i.e. the Dockerfile uses exec-form CMD, not
    # shell form, which would deliver the SIGTERM to /bin/sh instead.
    def _shutdown(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _shutdown)

    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
