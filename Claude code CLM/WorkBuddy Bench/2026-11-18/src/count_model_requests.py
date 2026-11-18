"""Count model requests in formal WorkBuddy trials and explicitly identified regrades."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(path.read_bytes())


def stream_closed(file):
    with file.open("rb") as response:
        response.seek(max(0, file.stat().st_size - 16384))
        return b"data: [DONE]" in response.read()


def trial_start(timeline):
    with timeline.open() as records:
        for line in records:
            if not line.endswith("\n"):
                continue
            event = json.loads(line)
            if event["event"] == "environment-start":
                return event["timestamp"]
    return None


def count(experiment):
    trials_seen = set()
    maintenance_seen = set()
    deepseek, judge, maintenance, regrade = (Counter() for _ in range(4))
    for run in sorted(experiment.glob("formal-*"), reverse=True):
        if not (run / "plan.json").is_file() or not (run / "sessions.json").is_file():
            continue
        judge_model = read(run / "sessions.json")["judge_model"]
        for arm in ("native", "clm"):
            for trial in sorted((run / arm / "evidence").glob("*/timeline.jsonl")):
                directory = trial.parent
                started = trial_start(trial)
                trial_key = arm, directory.name, started
                if started is None or trial_key in trials_seen:
                    continue
                trials_seen.add(trial_key)
                for intent in (directory / "chat-gateway").glob("*/intent.json"):
                    deepseek["attempts"] += 1
                    outcome = intent.with_name("receipt.json")
                    if outcome.is_file():
                        deepseek["terminal"] += 1
                        deepseek["complete"] += bool(read(outcome).get("complete"))
                if "-web-" not in directory.name:
                    continue
                for request in (directory / "wire").glob("*/request.upstream.json"):
                    metadata = request.with_name("metadata.json")
                    if not metadata.is_file():
                        try:
                            request_model = read(request).get("model")
                        except (OSError, ValueError):
                            continue
                        if request_model == judge_model:
                            judge["attempts"] += 1
                        continue
                    details = read(metadata)
                    if details.get("actor") != "judge":
                        continue
                    judge["attempts"] += 1
                    judge["terminal"] += 1
                    response = request.with_name("response.raw")
                    if details.get("http_status") == 200 and response.is_file() and stream_closed(response):
                        judge["complete"] += 1
        for request in (run / "clm" / "maintenance").glob("*/maintenance-request.json"):
            data = request.read_bytes()
            key = (request.parent.name, request.stat().st_mtime_ns, hashlib.sha256(data).hexdigest())
            if key in maintenance_seen:
                continue
            maintenance_seen.add(key)
            maintenance["attempts"] += 1
            response = request.with_name("maintenance-transport.json")
            if response.is_file():
                maintenance["terminal"] += 1
                maintenance["complete"] += read(response)["status"] == 200
    for intent in (experiment / "regrades").glob("*/attempt-*/intent.json"):
        regrade["attempts"] += 1
        receipt = intent.with_name("receipt.json")
        if receipt.is_file():
            regrade["terminal"] += 1
            regrade["complete"] += bool(read(receipt).get("complete_valid_stream"))
    return {
        "observed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "formal_agent": deepseek, "formal_judge": judge, "formal_maintenance": maintenance,
        "supplemental_regrade": regrade,
        "formal_total_attempts": deepseek["attempts"] + judge["attempts"] + maintenance["attempts"],
        "total_including_regrades": deepseek["attempts"] + judge["attempts"] + maintenance["attempts"] + regrade["attempts"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    args = parser.parse_args()
    print(json.dumps(count(args.experiment), indent=2))
