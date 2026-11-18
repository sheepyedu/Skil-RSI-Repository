"""Read WorkBuddy transport, session and grader evidence without printing payload content."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as data:
        return hashlib.file_digest(data, "sha256").hexdigest()


def response_closed(path):
    # The normal endpoint is SSE. The gateway also accepts a complete JSON reply.
    with path.open("rb") as stream:
        start = stream.read(160).lstrip()
        if start.startswith(b"{"):
            document = read(path)
            return any(choice.get("finish_reason") is not None for choice in document.get("choices", []))
        stream.seek(max(0, path.stat().st_size - 16384))
        return any(line.partition(b":")[2].strip() == b"[DONE]"
                   for line in stream.read().splitlines() if line.startswith(b"data:"))


def user_text(body):
    for message in body.get("messages", []):
        if message.get("role") != "user":
            continue
        value = message.get("content")
        if isinstance(value, str):
            yield value
        elif isinstance(value, list):
            yield from (item.get("text", "") for item in value if item.get("type") == "text")


def external_judge(directory, model):
    path = directory / "wire"
    completed, problems = 0, 0
    for file in sorted(path.glob("*/metadata.json")):
        record = read(file)
        if record.get("actor") != "judge":
            continue
        response = file.with_name("response.raw")
        if record.get("http_status") != 200 or not response.is_file() or response.stat().st_size == 0:
            problems += 1
            continue
        if record.get("transport") != "eof":
            problems += 1
            continue
        request = file.with_name("request.upstream.json")
        if request.is_file() and read(request).get("model") != model:
            problems += 1
            continue
        completed += 1
    return completed, problems


def trial(root, arm, row, previous, model, judge_model):
    name = f"{row['position']:03d}-{row['domain']}-{row['task']}"
    directory = root / arm / "evidence" / name
    timeline = directory / "timeline.jsonl"
    if not timeline.is_file():
        return {"state": "pending"}
    entries = [json.loads(l) for l in timeline.read_text().splitlines() if l]
    receipt_path = directory / "receipt.json"
    receipt = read(receipt_path) if receipt_path.is_file() else {}
    attempts = sorted((directory / "chat-gateway").glob("*/intent.json"))
    outcomes = Counter()
    exact = None
    previous_found = None
    first_input = None
    in_flight = []
    complete = []
    errors = []
    instruction = (
        root / "datasets" / f"wb-bench-{row['domain']}-v1.0" / "tasks" / row["task"] / "instruction.md"
    ).read_text().strip()
    for intent in attempts:
        parent = intent.parent
        done = parent / "receipt.json"
        if not done.is_file():
            in_flight.append({"attempt": parent.name, "created": datetime.fromtimestamp(intent.stat().st_mtime, ZoneInfo("Asia/Shanghai")).isoformat()})
            continue
        result = read(done)
        if not result.get("complete"):
            outcomes[result.get("disposition") or "unknown"] += 1
            errors.append({"attempt": parent.name, "status": result.get("http_status"), "forwarded": result.get("forwarded"), "kind": (result.get("failure") or {}).get("kind")})
            continue
        request = parent / "request.raw"
        response = parent / "response.raw"
        if not request.is_file() or not response.is_file() or not response.stat().st_size:
            outcomes["missing_input_output"] += 1
            continue
        if result.get("http_status") != 200 or result.get("reported_model") != model:
            outcomes["unexpected_status_or_model"] += 1
            continue
        if not response_closed(response):
            outcomes["missing_stream_terminator"] += 1
            continue
        outcomes["complete"] += 1
        complete.append({"attempt": parent.name, "request_sha256": sha(request), "response_sha256": sha(response),
                         "request_bytes": request.stat().st_size, "response_bytes": response.stat().st_size,
                         "input_tokens": (result.get("usage") or {}).get("prompt_tokens"),
                         "output_tokens": (result.get("usage") or {}).get("completion_tokens"),
                         "finish_reason": result.get("finish_reason")})
        if exact is None:
            payload = read(request)
            texts = list(user_text(payload))
            exact = payload.get("model") == model and any(
                row["marker"] in value and instruction in value for value in texts
            )
            previous_found = any(previous["marker"] in value for value in texts) if previous else None
            first_input = (result.get("usage") or {}).get("prompt_tokens")
    local = root / arm / "trials" / name
    score = receipt.get("reward")
    grader_results = sorted(p.name for p in (local / "verifier").iterdir() if p.is_file()) if (local / "verifier").is_dir() else []
    judges, judge_errors = external_judge(directory, judge_model)
    native = receipt.get("native") or {}
    expected_session = read(root / "sessions.json")["sessions"][arm]
    saved_transcript = directory / "native-session.jsonl"
    cli_output = local / "agent" / "cc-output.txt"
    observed_sessions = set()
    terminal_errors = []
    if receipt and cli_output.is_file():
        with cli_output.open() as stream:
            for line in stream:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get("type") == "system" and item.get("subtype") == "init":
                    observed_sessions.add(item.get("session_id"))
                if item.get("type") == "result":
                    terminal_errors.append(item.get("is_error"))
    return {
        "state": "accepted" if receipt.get("accepted") else "failed" if receipt else entries[-1]["event"],
        "last_event": entries[-1], "request_outcomes": dict(outcomes), "requests_in_flight": in_flight,
        "first_actual_input_tokens": first_input, "first_actual_input_exact": exact,
        "previous_marker_in_first_actual_input": previous_found,
        "native_session_match": observed_sessions == {expected_session} if receipt else None,
        "native_terminal": bool(terminal_errors) if receipt else None,
        "native_terminal_error": terminal_errors[-1] if terminal_errors else None,
        "native_stream_sha256": sha(cli_output) if receipt and cli_output.is_file() else None,
        "native_transcript_sha256": sha(saved_transcript) if receipt and saved_transcript.is_file() else None,
        "native_compactions": native.get("native_compactions"),
        "session_saved": receipt.get("session_saved"), "reward": score,
        "grader_files": grader_results, "judge_complete": judges, "judge_errors": judge_errors,
        "exception_type": (receipt.get("exception") or {}).get("exception_type"),
        "request_errors": errors, "requests_completed": complete,
    }


def main():
    options = argparse.ArgumentParser()
    options.add_argument("root", type=Path)
    options.add_argument("--count", type=int, default=3)
    args = options.parse_args()
    root = args.root
    plan = read(root / "plan.json")
    sessions = read(root / "sessions.json")
    cases = []
    for i,row in enumerate(plan["tasks"][:args.count]):
        cases.append({"position":row["position"], "domain":row["domain"], "task":row["task"],
                      "arms": {arm: trial(root,arm,row,plan["tasks"][i-1] if i else None,
                                          sessions["model"],sessions["judge_model"]) for arm in ("native","clm")}})
    progress = read(root / "progress.json") if (root / "progress.json").is_file() else {}
    exit_path = root / "exit-status.txt"
    verified = [
        case["position"] for case in cases
        if all(
            item["state"] == "accepted" and item["first_actual_input_exact"]
            and item["native_session_match"] and item["native_terminal"] and not item["native_terminal_error"]
            and item["native_transcript_sha256"] and item["reward"] is not None and not item["requests_in_flight"]
            and item["request_outcomes"].get("complete", 0) > 0
            and not any(item["request_outcomes"].get(k) for k in ("missing_input_output", "missing_stream_terminator", "unexpected_status_or_model"))
            and (case["position"] == 1 or item["previous_marker_in_first_actual_input"] or item["native_compactions"])
            and (case["domain"] != "web" or item["judge_complete"] > 0)
            for item in case["arms"].values()
        )
    ]
    print(json.dumps({"observed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
                      "model":sessions["model"], "judge_model":sessions["judge_model"], "plan_sha256":sha(root/"plan.json"),
                      "controller_completed_pairs":progress.get("completed_pairs",0),
                      "exit_status":int(exit_path.read_text()) if exit_path.is_file() else None,
                      "verified_pairs":verified, "cases":cases}, indent=2))


if __name__ == "__main__":
    main()
