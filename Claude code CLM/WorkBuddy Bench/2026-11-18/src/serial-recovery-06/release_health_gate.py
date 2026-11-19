"""Release the staged WorkBuddy recovery using a verified private probe."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def release(experiment, probe):
    operator = (experiment / "operator-supervision").resolve(strict=True)
    probe = probe.resolve(strict=True)
    if probe.parent != operator or not probe.name.startswith("service-health-"):
        raise ValueError("Select a private service-health probe in this experiment")

    run = experiment / "formal-02-resume-06"
    sessions = json.loads((run / "sessions.json").read_bytes())
    recovery = json.loads((run / "recovery.json").read_bytes())
    if recovery["position"] != 27 or (run / "exit-status.txt").exists():
        raise ValueError("The staged task 27 recovery is unavailable")
    frozen_model = sessions["model"]
    receipt = probe / "receipt.json"
    if receipt.is_symlink() or not receipt.is_file() or receipt.stat().st_mode & 0o077:
        raise ValueError("The source receipt must be a private regular file")
    health = json.loads(receipt.read_bytes())
    raw_request = (probe / "request.json").read_bytes()
    raw_response = (probe / "response.json").read_bytes()
    if (
        health["exit_code"] != 0 or health.get("verified_ok") is not True
        or health["requested_model"] != frozen_model or health.get("actual_model") != frozen_model
        or health["request_sha256"] != hashlib.sha256(raw_request).hexdigest()
        or health["response_sha256"] != hashlib.sha256(raw_response).hexdigest()
        or health["response_bytes"] != len(raw_response)
    ):
        raise ValueError("The probe does not prove a successful response from the frozen model")

    request = json.loads(raw_request)
    response = json.loads(raw_response)
    answer = response["choices"][0]["message"]["content"]
    if (
        request["model"] != frozen_model or response["model"] != frozen_model
        or answer.strip().upper().strip(".!") != "OK"
    ):
        raise ValueError("The original probe payloads do not match the health receipt")

    gate = operator / "allow-formal-06.json"
    # The existing receipt stays private. Linking publishes it in one operation and cannot replace an existing gate.
    os.link(receipt, gate)
    return gate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", type=Path)
    parser.add_argument("probe", type=Path)
    args = parser.parse_args()
    print(release(args.experiment, args.probe))
