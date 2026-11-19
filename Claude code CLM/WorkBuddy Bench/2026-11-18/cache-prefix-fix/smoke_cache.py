"""Validate WorkBuddy's DeepSeek request conversion with synthetic data."""

import argparse
import datetime
import http.client
import json
import socket
import subprocess
import tempfile
import threading
import time
import uuid
from pathlib import Path

from audit_run import cache_token_counts
from clm.context import Context
from skillrl.chat_gateway import ChatMessagesGateway, deepseek_request
from wire import Wire


MODEL = "deepseek-v4-1-flash-261017"


def billing_line(cch):
    return f"x-anthropic-billing-header: cc_version=2.1.160.f36; cc_entrypoint=sdk-cli; cch={cch};"


def payload(cch, system, tail):
    return {
        "model": MODEL,
        "max_tokens": 128,
        "stream": True,
        "system": [
            {"type": "text", "text": billing_line(cch)},
            {"type": "text", "text": system, "cache_control": {"type": "ephemeral"}},
        ],
        "messages": [
            {"role": "user", "content": "We will answer a series of short arithmetic questions."},
            {"role": "assistant", "content": "Ready."},
            {"role": "user", "content": tail},
        ],
    }


def check_conversion():
    test_system = "System instruction.\n" + billing_line("cdef1")
    user_text = billing_line("abcde")
    first = payload("abcde", test_system, user_text)
    second = payload("bbcde", test_system, user_text)
    first["tools"] = second["tools"] = [{
        "name": "read_label",
        "description": "Read a synthetic label.",
        "input_schema": {"type": "object", "properties": {"label": {"type": "string"}}},
    }]
    raw_before = json.dumps(first)
    converted = deepseek_request(first)
    assert converted == deepseek_request(second)
    assert json.dumps(first) == raw_before
    assert converted["messages"][0]["content"] == test_system
    assert converted["messages"][-1]["content"] == user_text
    assert converted["tools"][0]["function"]["name"] == "read_label"

    first["system"] = billing_line("abcde") + "\r\n" + test_system
    assert deepseek_request(first) == converted
    first["system"] = billing_line("abcde") + " ordinary prose\n" + test_system
    assert deepseek_request(first)["messages"][0]["content"] == first["system"]
    first["system"] = [{"type": "text", "text": billing_line("abcde")}]
    assert deepseek_request(first)["messages"][0]["role"] == "user"

    def usage(total, **fields):
        return cache_token_counts({"prompt_tokens": total, **fields})

    assert usage(4096, prompt_tokens_details={"cached_tokens": 4032}) == {
        "prompt_cache_hit_tokens": 4032, "prompt_cache_miss_tokens": 64,
    }
    assert usage(4096, prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=4096) == {
        "prompt_cache_hit_tokens": 0, "prompt_cache_miss_tokens": 4096,
    }
    assert usage(4096) == {"prompt_cache_unknown_input_tokens": 4096}
    assert usage(4096, prompt_cache_hit_tokens=4097) == {"prompt_cache_unknown_input_tokens": 4096}
    assert cache_token_counts({}) == {"cache_usage_missing": 1}


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost", timeout=90)
        self.path = path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(str(self.path))


def submit(path, request):
    raw = json.dumps(request).encode()
    conn = UnixHTTPConnection(path)
    try:
        conn.request("POST", "/v1/messages", body=raw, headers={
            "Content-Type": "application/json", "x-api-key": "clm-session-local",
        })
        reply = conn.getresponse()
        body = reply.read()
        assert reply.status == 200 and b"event: message_stop" in body
    finally:
        conn.close()


def live_arm(arm, service, key, root):
    root.mkdir()
    session = f"{arm}-{uuid.uuid4().hex}"
    system = "Synthetic arithmetic reference " + session + "\n"
    system += "\n".join(
        f"Fictional catalog row {row:03d}. The region is sample valley. "
        f"Its shelf count is {row % 27 + 1} and its identifier is neutral."
        for row in range(185)
    )
    context = None
    if arm == "clm":
        (root / "context").mkdir()
        context = Context(root / "context")

    backend = ChatMessagesGateway(service, key, MODEL, root / "chat-gateway", timeout=75)
    backend.start()
    with tempfile.TemporaryDirectory(prefix="wb-cache-") as socket_dir:
        path = Path(socket_dir) / "wire.sock"
        try:
            with Wire(path, root / "wire", "https://example.invalid", backend, MODEL, "", context, "") as wire:
                wire.timeout_sec = 80
                thread = threading.Thread(target=wire.serve_forever, daemon=True)
                thread.start()
                try:
                    submit(path, payload("2aa01", system, "Respond with only the answer to 2 + 2."))
                    time.sleep(4)
                    submit(path, payload("2aa02", system, "Respond with only the answer to 5 + 2."))
                finally:
                    wire.shutdown()
                    thread.join()
        finally:
            backend.close()

    metrics = []
    outbounds = []
    for index, cch in enumerate(("2aa01", "2aa02")):
        path = root / "chat-gateway" / f"{index:04d}"
        incoming = json.loads((path / "request.messages.raw").read_bytes())
        outbound = json.loads((path / "request.raw").read_bytes())
        assert incoming["system"][0]["text"] == billing_line(cch)
        assert outbound["messages"][0]["content"] == system
        outbounds.append(outbound)
        receipt = json.loads((path / "receipt.json").read_bytes())
        assert receipt["http_status"] == 200 and receipt["complete"]
        usage = receipt["usage"]
        metrics.append({
            "http_status": receipt["http_status"],
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            **cache_token_counts(usage),
        })
    assert outbounds[0]["messages"][:-1] == outbounds[1]["messages"][:-1]
    assert outbounds[0]["messages"][-1] != outbounds[1]["messages"][-1]
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", type=Path, help="Empty output directory for full synthetic traces")
    args = parser.parse_args()
    check_conversion()
    if args.live is None:
        print("WorkBuddy request conversion and cache usage regression passed")
    else:
        args.live.mkdir(mode=0o700)
        config = json.loads(Path("/mount-data/Tools/services.json").read_text())
        url = config["services"]["deepseek"]["base_url"]
        key = subprocess.check_output(
            ["/mount-data/Tools/skill-api", "_credential", "--service", "deepseek"], text=True,
        ).strip()
        summary = {"time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "model": MODEL}
        for arm in ("native", "clm"):
            summary[arm] = live_arm(arm, url, key, args.live / arm)
        (args.live / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        assert all(summary[arm][1].get("prompt_cache_hit_tokens", 0) > 0 for arm in ("native", "clm"))
