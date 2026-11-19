"""Run a loopback relay while the offline WorkBuddy container exists."""

from pathlib import Path
import socketserver
import sys

sys.path.insert(0, "/opt/codex-clm/clm")
from container_entry import Relay


with socketserver.ThreadingTCPServer(("127.0.0.1", 19731), Relay) as server:
    server.daemon_threads = True
    Path("/tmp/workbuddy-relay-ready").touch()
    server.serve_forever()
