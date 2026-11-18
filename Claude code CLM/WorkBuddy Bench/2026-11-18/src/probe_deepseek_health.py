"""Check the existing DeepSeek service with one benign generation."""

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


MODEL = "deepseek-v4-1-flash-261017"
ZONE = ZoneInfo("Asia/Shanghai")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def probe(output):
    output.mkdir(parents=True)
    packet = {
        "model": MODEL, "messages": [{"role": "user", "content": "Reply with only OK."}],
        "max_tokens": 128, "thinking": {"type": "disabled"}, "stream": False,
    }
    raw = (json.dumps(packet, separators=(",", ":")) + "\n").encode()
    (output / "request.json").write_bytes(raw)
    started = datetime.now(ZONE).isoformat(timespec="seconds")
    result = subprocess.run(
        ["/mount-data/Tools/skill-api", "request", "--service", "deepseek",
         "--protocol", "chat", "--timeout", "45"],
        input=raw, capture_output=True, check=False,
    )
    (output / "response.json").write_bytes(result.stdout)
    (output / "error.txt").write_bytes(result.stderr)
    record = {
        "started_at": started, "finished_at": datetime.now(ZONE).isoformat(timespec="seconds"),
        "requested_model": MODEL, "exit_code": result.returncode,
        "response_bytes": len(result.stdout), "request_sha256": digest(raw),
        "response_sha256": digest(result.stdout),
    }
    if result.returncode == 0:
        document = json.loads(result.stdout)
        option = document["choices"][0]
        record.update(
            actual_model=document.get("model"), finish=option["finish_reason"],
            verified_ok=option["message"]["content"].strip().upper().strip(".!") == "OK",
        )
    else:
        error = result.stderr.lower()
        record["timed_out"] = b"timed out" in error or b"timeout" in error
    text = json.dumps(record, indent=2) + "\n"
    (output / "receipt.json").write_text(text)
    print(text, end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    probe(args.output)
