"""Record every model request and response without giving the agent provider credentials."""

import datetime
import hashlib
import http.client
import json
import os
import secrets
import socketserver
import threading
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit

from clm.context import encode


def write_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


class Wire(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True

    def __init__(self, socket_path, evidence, endpoint, backend, model, judge_model, context, judge_key):
        self.evidence = Path(evidence)
        self.endpoint = urlsplit(endpoint)
        if self.endpoint.scheme != "https" or self.endpoint.username or self.endpoint.query:
            raise ValueError("An HTTPS provider origin is required")
        self.backend = backend
        self.agent_port = backend.server.server_address[1]
        self.timeout_replays = set()
        self.model = model
        self.judge_model = judge_model
        self.judge_token = secrets.token_urlsafe(32)
        self.judge_enabled = False
        self.context = context
        self.judge_key = judge_key
        self.lock = threading.Lock()
        self.sequence = 0
        self.active = 0
        self.evidence.mkdir(mode=0o700)
        super().__init__(str(socket_path), Handler)
        os.chmod(socket_path, 0o666)

    def start_request(self):
        with self.lock:
            self.sequence += 1
            self.active += 1
            path = self.evidence / f"{self.sequence:05d}"
            path.mkdir(mode=0o700)
            return path

    def close_audit(self):
        with self.lock:
            self.active -= 1


    def renew_unanswered_timeout(self, raw):
        identity = hashlib.sha256(raw).hexdigest()
        with self.backend.lock:
            if identity in self.timeout_replays or self.backend.identities.get(identity) != "unknown":
                return False
            for path in sorted(self.backend.path.glob("*/intent.json"), reverse=True):
                intent = json.loads(path.read_text())
                receipt = path.parent / "receipt.json"
                if intent.get("incoming_sha256") != identity or not receipt.is_file():
                    continue
                result = json.loads(receipt.read_text())
                if not result.get("forwarded"):
                    continue
                if (
                    result.get("http_status") is None
                    and (result.get("failure") or {}).get("kind") == "TimeoutError"
                    and not (path.parent / "response.raw").exists()
                ):
                    # Only an unanswered transport timeout is eligible, once per
                    # body. The first upstream attempt remains in the audit.
                    self.timeout_replays.add(identity)
                    del self.backend.identities[identity]
                    return True
                return False
        return False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def setup(self):
        self.request.settimeout(180)
        super().setup()

    def do_POST(self):
        directory = self.server.start_request()
        record = {
            "route": self.path,
            "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        try:
            self.forward(directory, record)
        except (BrokenPipeError, ConnectionResetError):
            record["client_disconnected"] = True
        finally:
            record["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            write_json(directory / "metadata.json", record)
            self.server.close_audit()

    def forward(self, directory, record):
        server = self.server
        route = urlsplit(self.path)
        is_judge = route.path == "/v1/chat/completions" and not route.query
        is_agent = route.path in ("/v1/messages", "/v1/messages/count_tokens") and route.query in ("", "beta=true")
        token = self.headers.get("Authorization", "").removeprefix("Bearer ")
        if is_judge and not (server.judge_enabled and secrets.compare_digest(token, server.judge_token)):
            self.send_error(403)
            return
        if is_agent and token != "clm-session-local" and self.headers.get("x-api-key") != "clm-session-local":
            self.send_error(403)
            return
        if not (is_agent or is_judge):
            self.send_error(404)
            return
        record["actor"] = "judge" if is_judge else "agent"
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 64 * 1024 * 1024:
                raise ValueError("body size outside relay limits")
            raw = self.rfile.read(size)
            (directory / "request.raw.json").write_bytes(raw)
            payload = json.loads(raw)
            model = server.judge_model if is_judge else server.model
            if payload["model"] != model:
                raise ValueError("unexpected request model")
            record["model"] = model
            if is_agent and server.context:
                with server.lock:
                    payload["messages"], record["context"] = server.context.apply(
                        payload["messages"], accept_edit=route.path == "/v1/messages"
                    )
                raw = encode(payload)
        except (KeyError, TypeError, ValueError, OSError) as error:
            record["validation_error"] = type(error).__name__
            self.send_error(400)
            return
        (directory / "request.upstream.json").write_bytes(raw)
        headers = {"content-type": "application/json", "accept-encoding": "identity"}
        if is_agent:
            conn = http.client.HTTPConnection("127.0.0.1", server.agent_port, timeout=server.timeout_sec)
            target = "/v1/messages"
            if route.path.endswith("/count_tokens"):
                record["handled_locally"] = True
                self.send_error(404, "DeepSeek Chat has no Count Tokens route")
                return
            if server.renew_unanswered_timeout(raw):
                record["replay_after_unanswered_timeout"] = True
        else:
            endpoint = server.endpoint
            conn = http.client.HTTPSConnection(endpoint.hostname, endpoint.port, timeout=server.timeout_sec)
            target = endpoint.path.rstrip("/") + self.path
            headers["authorization"] = "Bearer " + server.judge_key
        started = False
        try:
            conn.request("POST", target, body=raw, headers=headers)
            reply = conn.getresponse()
            record["http_status"] = reply.status
            self.send_response(reply.status)
            for key, value in reply.getheaders():
                if key.lower() in ("content-type", "content-encoding", "retry-after", "request-id", "x-request-id"):
                    self.send_header(key, value)
                    record[key.lower()] = value
            self.end_headers()
            started = True
            disconnected = False
            with (directory / "response.raw").open("wb") as out:
                while chunk := reply.read1(65536):
                    out.write(chunk)
                    out.flush()
                    if not disconnected:
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            disconnected = True
            record.update(transport="eof", client_disconnected=disconnected)
        except (OSError, http.client.HTTPException) as error:
            record["transport"] = type(error).__name__
            if not started:
                self.send_error(502)
        finally:
            conn.close()
