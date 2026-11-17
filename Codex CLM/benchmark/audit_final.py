"""Verify the final native timeline, scored order, and captured Responses wire."""
import collections
import hashlib
import json
import re
from pathlib import Path
import sys

from observe import jsonlines, root, view

MARKER = re.compile(rb"CODEX_CLBENCH_TASK_[0-9]{3}")


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def verify():
    aggregate = view()
    if aggregate["current_score"]["scored"] != 100 or (aggregate["native_exit"] or {}).get("status") != 0:
        raise SystemExit("Final audit requires official 100/100 and native exit 0")
    if aggregate["first_request_continuity"] != 100:
        raise ValueError("Missing full historical prefix in at least one task")
    assert aggregate["native_context_compactions"] == 0
    thread_id = aggregate["thread"]["thread_id"]
    turns, local_commands = [], []
    active_turn = None
    starting = 0
    for row in jsonlines(root / "native.jsonl"):
        data = row["data"]
        method = data.get("method")
        params = data.get("params") or {}
        if method == "thread/start" and row["direction"] == "to_codex":
            starting += 1
        if method in ("turn/started", "turn/completed"):
            assert params["threadId"] == thread_id
            turn_id = params["turn"]["id"]
            if method == "turn/started":
                assert active_turn is None
                active_turn = turn_id
            else:
                assert active_turn == turn_id and params["turn"]["status"] == "completed"
                turns.append(turn_id)
                active_turn = None
        if method == "item/completed" and params.get("item", {}).get("type") == "commandExecution":
            cmd = params["item"].get("command", "")
            local_commands.append({"turn_id": params.get("turnId"), "command": cmd, "status": params["item"].get("status")})
    if starting != 2:  # one startup probe without a turn, one formal session
        raise ValueError("Unexpected number of start operations")
    assert active_turn is None and len(turns) == len(set(turns)) >= 100

    run = Path((root / "native.stderr").read_text().split("CLM run: ")[-1].splitlines()[0])
    types = collections.Counter()
    fully_streamed = 0
    byte_savings = 0
    edited = 0
    for event in jsonlines(run / "responses.jsonl"):
        path = run / "wire" / f'{event["revision"]:05d}'
        raw = (path / "input.raw.json").read_bytes()
        upstream = json.loads((path / "request.responses.json").read_bytes())
        forwarded = dumps(upstream["input"])
        assert upstream["model"] == "gpt-6.1-sol" and upstream["store"] is False
        assert hashlib.sha256(raw).hexdigest() == event["raw_input_sha256"]
        assert hashlib.sha256(forwarded).hexdigest() == event["upstream_input_sha256"]
        assert event["before_input_bytes"] == len(raw)
        assert event["after_input_bytes"] == len(forwarded)
        assert event["http_status"] == 200 and event["transport"] == "eof"
        assert event["task_markers_before"] == event["task_markers_after"]
        assert sorted({
            marker.decode() for item in upstream["input"] if item.get("role") == "user"
            for marker in MARKER.findall(dumps(item))
        }) == event["task_markers_after"]
        ending = collections.Counter()
        with (path / "response.raw").open("rb") as stream:
            for line in stream:
                if line.startswith(b"event: "):
                    name = line[7:].strip().decode()
                    if name in ("response.completed", "response.failed", "response.incomplete"):
                        ending[name] += 1
        assert ending["response.completed"] == 1
        assert not ending["response.failed"] and not ending["response.incomplete"]
        fully_streamed += 1
        byte_savings += len(raw) - len(forwarded)
        if event["edit"] == "accepted":
            edited += 1
            current = collections.Counter(item.get("call_id") for item in upstream["input"] if item.get("call_id"))
            old = collections.Counter(item.get("call_id") for item in json.loads(raw) if item.get("call_id"))
            assert all(count == 2 for count in (old - current).values())
            types.update({str(event["revision"]): len(old - current)})
    return {
        "thread": thread_id, "official_turns": len(turns), "streamed_responses_verified": fully_streamed,
        "edited_requests_verified": edited, "wire_cumulative_input_bytes_removed": byte_savings,
        "latest_accepted_edit": aggregate["latest_edit"], "native_shell_calls": len(local_commands),
        "clm_commands": sum("clm-context" in item["command"] for item in local_commands),
        "score": aggregate["current_score"], "grouped": aggregate["grouped"],
        "request_usage": aggregate["sum_native_last_request_usage"],
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, indent=2))
