"""Forward verifier loopback traffic through the same Unix audit bridge."""

import socketserver
import sys

sys.path.insert(0, "/opt/clm/clm")
from container_entry import Relay

with socketserver.ThreadingTCPServer(("127.0.0.1", 19731), Relay) as server:
    server.daemon_threads = True
    server.serve_forever()
