"""Private transport for one trial. The control arm's request bytes pass through unchanged."""

import hashlib
import http.client
import json
import secrets
import shutil
import socketserver
import time
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

from clm.context import Context, digest, encode, is_message, write_json

MODEL = "gpt-6.1-sol"
LOCAL_TOKEN = "workbuddy-codex-local"
MAX_BODY = 64 * 1024 * 1024
COMPACT_BYTES = 3 * 1024 * 1024
COMPACT_TOKENS = 165_000
RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}
RETRYABLE_CODES = {"server_error", "internal_server_error", "rate_limit_exceeded", "overloaded_error"}


def stream_outcome(path, *, chat=False):
    """Inspect the terminal SSE event before letting Codex consume any output."""
    failures = {"response.failed", "response.incomplete", "error"}
    fields = []
    chat_finished = False
    with path.open("rb") as stream:
        for line in stream:
            if line.startswith(b"data:"):
                fields.append(line[5:].lstrip().rstrip(b"\r\n"))
            elif not line.strip() and fields:
                if chat and fields == [b"[DONE]"]:
                    return ("chat.done", None) if chat_finished else (None, None)
                try:
                    event = json.loads(b"\n".join(fields))
                except (ValueError, UnicodeError):
                    fields.clear()
                    continue
                fields.clear()
                if not isinstance(event, dict):
                    continue
                kind = event.get("type")
                if chat:
                    error = event.get("error")
                    if isinstance(error, dict):
                        return "error", error.get("code") or error.get("type")
                    chat_finished |= any(choice.get("finish_reason") for choice in event.get("choices", []))
                if kind == "response.completed":
                    return kind, None
                if kind in failures:
                    payload = event.get("response") or event
                    error = payload.get("error") or payload.get("incomplete_details") or payload
                    return kind, error.get("code") or error.get("type") or error.get("reason")
    return None, None


def temporary_provider_failure(path):
    """Recognize the provider's explicit retry instructions in failed SSE events."""
    messages = ("temporarily unavailable", "stream was interrupted", "上游服务暂时不可用", "上游响应中断")
    with path.open("rb") as stream:
        for line in stream:
            if not line.startswith(b"data:"):
                continue
            try:
                event = json.loads(line[5:])
            except (ValueError, UnicodeError):
                continue
            if not isinstance(event, dict) or event.get("type") not in ("response.failed", "error"):
                continue
            error = (event.get("response") or event).get("error") or {}
            if not isinstance(error, dict):
                continue
            code = error.get("code") or error.get("type")
            message = str(error.get("message", "")).lower()
            if code in ("bad_response", "bad_response_status_code", "upstream_error", "upstream_stream_read_error") and any(text in message for text in messages):
                return True
    return False


class SeriesContext(Context):
    """Keep the explicit CLM note across a native compaction, rebinding editable IDs."""

    def apply(self, items):
        first = next((x for x in items if is_message(x, "user")), None)
        if first is not None and self.anchor is not None and self.anchor != digest(first):
            self.anchor = digest(first)
            self.visible.clear()
            self.dropped.clear()
        return super().apply(items)


class Wire(socketserver.UnixStreamServer):
    def __init__(self, path, directory, base_url, key, context):
        self.directory = directory
        self.endpoint = urlsplit(base_url)
        if self.endpoint.scheme != "https" or not self.endpoint.hostname:
            raise ValueError("Expected a configured HTTPS provider")
        self.key = key
        self.context = context
        self.judge_token = secrets.token_urlsafe()
        self.judge_enabled = False
        self.requests = 0
        super().__init__(str(path), Handler)
        path.chmod(0o666)


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(930)
        super().setup()

    def log_message(self, *_):
        pass

    def error_json(self, status, reason):
        body = encode({"error": {"message": reason, "type": "invalid_request_error"}})
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def take_attempt(self, target, headers, wire, folder, is_stream, number):
        folder.mkdir()
        record = {"number": number, "started_ns": time.time_ns()}
        host = self.server.endpoint
        conn = http.client.HTTPSConnection(host.hostname, host.port, timeout=180)
        response_file = folder / "response.raw"
        try:
            conn.request("POST", target, body=wire, headers=headers)
            response = conn.getresponse()
            record["status"] = response.status
            record["headers"] = {k: v for k, v in response.getheaders()
                                 if k.lower() in ("content-type", "content-encoding", "x-request-id", "retry-after")}
            with response_file.open("wb") as out:
                while chunk := response.read1(65536):
                    out.write(chunk)
            record["eof"] = True
            if response.status == 200 and is_stream:
                record["terminal_sse"], record["error_code"] = stream_outcome(
                    response_file, chat=self.path == "/v1/chat/completions",
                )
                record["temporary_provider_failure"] = temporary_provider_failure(response_file)
        except (OSError, http.client.HTTPException) as err:
            record["transport_error"] = type(err).__name__
        finally:
            conn.close()
            if response_file.exists():
                with response_file.open("rb") as file:
                    record["response_sha256"] = hashlib.file_digest(file, "sha256").hexdigest()
                record["response_bytes"] = response_file.stat().st_size
            record["ended_ns"] = time.time_ns()
            write_json(folder / "receipt.json", record)
        return record

    def transfer(self, target, headers, wire, directory, event, is_stream):
        if self.path == "/v1/chat/completions":
            return self.transfer_judge(target, headers, wire, directory, event)
        event["attempts"] = []
        retry_root = directory / "attempts"
        retry_root.mkdir()
        for number in (1, 2, 3):
            folder = retry_root / str(number)
            attempt = self.take_attempt(target, headers, wire, folder, is_stream, number)
            event["attempts"].append(attempt)
            retry = (attempt.get("status") in RETRYABLE_HTTP or bool(attempt.get("transport_error"))
                     or attempt.get("error_code") in RETRYABLE_CODES
                     or attempt.get("temporary_provider_failure", False)
                     or (is_stream and attempt.get("status") == 200 and not attempt.get("terminal_sse")))
            if not retry or number == 3:
                break
            retry_after = next((v for k, v in attempt.get("headers", {}).items() if k.lower() == "retry-after"), "")
            retry_wait = min(60, int(retry_after)) if retry_after.isdecimal() else (2 ** number)
            time.sleep(retry_wait + secrets.randbelow(1000) / 1000)

        event.update({k: v for k, v in attempt.items() if k in ("status", "eof", "response_sha256",
                                                                "transport_error", "terminal_sse", "error_code")})
        raw = folder / "response.raw"
        if raw.exists():
            shutil.copyfile(raw, directory / "response.raw")
        valid_stream = not is_stream or attempt.get("terminal_sse") == "response.completed"
        if not raw.exists() or attempt.get("status") != 200 or not attempt.get("eof") or not valid_stream:
            event["delivered"] = False
            status = attempt.get("status")
            event["client_status"] = status if isinstance(status, int) and status != 200 else 502
            self.error_json(event["client_status"], "Trial provider did not return a complete successful response")
            return
        self.send_response(attempt["status"])
        for key, value in attempt.get("headers", {}).items():
            self.send_header(key, value)
        self.end_headers()
        try:
            with raw.open("rb") as response:
                shutil.copyfileobj(response, self.wfile, 65536)
            event["delivered"] = True
        except (BrokenPipeError, ConnectionResetError):
            event["delivered"] = False

    def transfer_judge(self, target, headers, wire, directory, event):
        host = self.server.endpoint
        conn = http.client.HTTPSConnection(host.hostname, host.port, timeout=120)
        raw = directory / "response.raw"
        try:
            conn.request("POST", target, body=wire, headers=headers)
            response = conn.getresponse()
            event["status"] = response.status
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() in ("content-type", "content-encoding", "x-request-id", "retry-after"):
                    self.send_header(key, value)
            self.end_headers()
            delivered = True
            with raw.open("wb") as out:
                while chunk := response.read1(65536):
                    out.write(chunk)
                    if delivered:
                        try:
                            self.wfile.write(chunk)
                            self.wfile.flush()
                        except (BrokenPipeError, ConnectionResetError):
                            delivered = False
            event.update(eof=True, delivered=delivered)
            event["terminal_sse"], event["error_code"] = stream_outcome(raw, chat=True)
        finally:
            conn.close()
            if raw.exists():
                with raw.open("rb") as file:
                    event["response_sha256"] = hashlib.file_digest(file, "sha256").hexdigest()

    def do_POST(self):
        server = self.server
        server.requests += 1
        directory = server.directory / f"{server.requests:05d}"
        directory.mkdir()
        event = {"path": self.path, "started_ns": time.time_ns()}
        try:
            judge = self.path == "/v1/chat/completions"
            if not judge and self.path not in ("/v1/responses", "/v1/responses/compact"):
                self.error_json(404, "Unsupported trial route")
                return
            token = server.judge_token if judge else LOCAL_TOKEN
            if (judge and not server.judge_enabled) or self.headers.get("Authorization") != f"Bearer {token}":
                self.error_json(403, "Trial route is not authorized")
                return
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY:
                raise ValueError("request body outside the trial's transport limit")
            original = self.rfile.read(length)
            (directory / "request.raw.json").write_bytes(original)
            if len(original) != length:
                raise ValueError("incomplete request")
            payload = json.loads(original)
            if not isinstance(payload, dict) or payload.get("model") != MODEL:
                raise ValueError("unexpected model")
            forwarded = original
            if not judge:
                raw = payload.get("input")
                if not isinstance(raw, list) or not all(isinstance(x, dict) for x in raw):
                    raise ValueError("expected Responses input item array")
                event["raw_input_bytes"] = len(encode(raw))
                event["raw_input_sha256"] = digest(raw)
                if server.context and any(is_message(x, "user") for x in raw):
                    if payload.get("previous_response_id") or payload.get("conversation"):
                        raise ValueError("CLM requires full Responses requests")
                    payload["input"], event["clm"] = server.context.apply(raw)
                    if payload["input"] != raw:
                        forwarded = encode(payload)
                event["sent_input_bytes"] = len(encode(payload["input"]))
            (directory / "request.sent.json").write_bytes(forwarded)
            event["raw_sha256"] = hashlib.sha256(original).hexdigest()
            event["sent_sha256"] = hashlib.sha256(forwarded).hexdigest()
            base = server.endpoint.path.rstrip("/")
            url = (base if base.endswith("/v1") else base + "/v1") + self.path[3:]
            headers = {"Authorization": f"Bearer {server.key}", "Content-Type": "application/json",
                       "Accept-Encoding": "identity", "Accept": self.headers.get("Accept", "*/*")}
            for name in ("OpenAI-Beta", "User-Agent"):
                if value := self.headers.get(name):
                    headers[name] = value
            self.transfer(url, headers, forwarded, directory, event, bool(payload.get("stream")))
        except ValueError as err:
            event.update(status=400, validation=str(err))
            self.error_json(400, "Invalid trial request")
        except (OSError, http.client.HTTPException) as err:
            event["transport_error"] = type(err).__name__
        finally:
            event["ended_ns"] = time.time_ns()
            write_json(directory / "receipt.json", event)
