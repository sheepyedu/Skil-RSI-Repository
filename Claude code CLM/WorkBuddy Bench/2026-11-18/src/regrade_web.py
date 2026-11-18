"""Regrade an archived WorkBuddy Web criterion with its exact original request."""

import argparse
import hashlib
import http.client
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def read(path):
    return json.loads(path.read_bytes())


def parse_sse(raw):
    text = []
    errors = []
    usage = None
    finish = False
    done = False
    for line in raw.splitlines():
        if not line.startswith(b"data:"):
            continue
        data = line.partition(b":")[2].strip()
        if data == b"[DONE]":
            done = True
            continue
        try:
            event = json.loads(data)
        except ValueError:
            errors.append("invalid_sse_json")
            continue
        if event.get("error"):
            errors.append(event["error"].get("type", "upstream_error"))
        if event.get("usage"):
            usage = event["usage"]
        for choice in event.get("choices", []):
            content = (choice.get("delta") or {}).get("content")
            if isinstance(content, str):
                text.append(content)
            if choice.get("finish_reason") == "stop":
                finish = True
    return {"done": done, "finish": finish, "text": "".join(text).strip(), "errors": errors, "usage": usage}


def parse_response(raw, mode):
    if mode == "stream":
        return parse_sse(raw)
    try:
        document = json.loads(raw)
    except ValueError:
        return {"done": False, "finish": False, "text": "", "errors": ["invalid_json"], "usage": None}
    error = document.get("error") or {}
    choices = document.get("choices") or []
    first = choices[0] if choices else {}
    text = (first.get("message") or {}).get("content")
    return {
        "done": bool(choices), "finish": first.get("finish_reason") == "stop",
        "text": text.strip() if isinstance(text, str) else "",
        "errors": [error.get("type", "upstream_error")] if error else [],
        "usage": document.get("usage"),
    }


def replay(source, target, position, arm, first, last, mode):
    plan = read(source / "plan.json")
    launch = read(source / "sessions.json")
    row = plan["tasks"][position - 1]
    if row["position"] != position or row["domain"] != "web":
        raise ValueError("This replay only applies to a frozen Web task")
    name = f"{position:03d}-{row['domain']}-{row['task']}"
    trial = source / arm / "evidence" / name
    wire = trial / "wire"
    originals = []
    payload = None
    model = launch["judge_model"]
    if launch["judge_service"] != "gpt":
        raise ValueError("This replay requires the original GPT judging route")
    for request_id in range(first, last + 1):
        folder = wire / f"{request_id:05d}"
        metadata = read(folder / "metadata.json")
        body = (folder / "request.upstream.json").read_bytes()
        original_response = (folder / "response.raw").read_bytes()
        result = parse_sse(original_response)
        if (
            metadata["actor"] != "judge" or metadata["route"] != "/v1/chat/completions"
            or metadata["model"] != model or result["done"] or not result["errors"]
            or (payload is not None and body != payload)
        ):
            raise ValueError("Original records are not matching failed judge calls")
        payload = body
        originals.append({"request_id": folder.name, "response_sha256": sha(original_response)})
    request = json.loads(payload)
    if request["model"] != model or request.get("stream") is not True:
        raise ValueError("Expected the original streaming judge call")
    target.mkdir(parents=True)
    (target / "request.raw.json").write_bytes(payload)
    request_hash = sha(payload)
    if mode == "nonstream":
        request["stream"] = False
        payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode()
        (target / "request.nonstream.json").write_bytes(payload)
    transport_hash = sha(payload)
    write(target / "source.json", {
        "run": source.name, "position": position, "task": row["task"], "arm": arm,
        "request_sha256": request_hash, "model": model, "original_failed_attempts": originals,
        "transport_request_sha256": transport_hash, "mode": mode, "stream": mode == "stream",
        "plan_sha256": sha((source / "plan.json").read_bytes()),
        "trial_receipt_sha256": sha((trial / "receipt.json").read_bytes()),
    })
    services = read(Path("/mount-data/Tools/services.json"))["services"]
    endpoint = urlsplit(services["gpt"]["base_url"])
    if (endpoint.scheme, endpoint.hostname, endpoint.path.rstrip("/")) != (
        "https", "cn.affordablerouter.com", "/v1",
    ):
        raise ValueError("GPT service does not match the original judging destination")
    key = subprocess.check_output(
        ["/mount-data/Tools/skill-api", "_credential", "--service", "gpt"], text=True,
    ).strip()
    path = endpoint.path.rstrip("/") + "/chat/completions"
    attempts = []
    for number, delay in enumerate((0, 15, 45) if mode == "stream" else (0, 20), start=1):
        if delay:
            time.sleep(delay)
        directory = target / f"attempt-{number:02d}"
        directory.mkdir()
        write(directory / "intent.json", {
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "request_sha256": transport_hash, "model": model, "route": path,
        })
        conn = http.client.HTTPSConnection(endpoint.hostname, endpoint.port, timeout=120)
        status = None
        transport_error = None
        with (directory / "response.raw").open("wb") as raw:
            try:
                conn.request("POST", path, body=payload, headers={
                    "content-type": "application/json", "accept-encoding": "identity",
                    "authorization": f"Bearer {key}",
                })
                reply = conn.getresponse()
                status = reply.status
                while chunk := reply.read1(65536):
                    raw.write(chunk)
                    raw.flush()
            except (OSError, http.client.HTTPException) as error:
                transport_error = type(error).__name__
            finally:
                conn.close()
        data = (directory / "response.raw").read_bytes()
        parsed = parse_response(data, mode)
        closed = bool(
            status == 200 and transport_error is None and parsed["done"]
            and parsed["finish"] and not parsed["errors"] and parsed["text"]
        )
        receipt = {
            "attempt": number, "http_status": status, "transport_error": transport_error,
            "response_sha256": sha(data), "response_bytes": len(data),
            "done": parsed["done"], "finish_stop": parsed["finish"], "stream_errors": parsed["errors"],
            "complete_valid_stream": closed, "usage": parsed["usage"],
        }
        write(directory / "receipt.json", receipt)
        attempts.append(receipt)
        if closed:
            (target / "replayed-response.txt").write_text(parsed["text"] + "\n")
            break
        if status in {400, 401, 403, 404}:
            break
    summary = {"status": "closed" if attempts[-1]["complete_valid_stream"] else "unresolved",
               "request_sha256": request_hash, "transport_request_sha256": transport_hash,
               "mode": mode, "stream": mode == "stream", "model": model, "attempts": attempts}
    write(target / "transport-summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--arm", choices=("native", "clm"), required=True)
    parser.add_argument("--first", type=int, required=True)
    parser.add_argument("--last", type=int, required=True)
    parser.add_argument("--nonstream", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)
    mode = "nonstream" if args.nonstream else "stream"
    replay(args.source, args.target, args.position, args.arm, args.first, args.last, mode)
