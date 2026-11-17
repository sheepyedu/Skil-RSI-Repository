"""Read-only aggregation of official scores and scoped Codex context edits."""
import collections
import json
from pathlib import Path
import sys

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def jsonlines(path):
    if path.exists():
        with path.open() as stream:
            for line in stream:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    if line.endswith("\n"):
                        raise


def view():
    plan = read(root / "PLAN.json")
    thread = read(root / "THREAD.json")
    planned = plan["grouped_order"]
    results = [read(path) for path in sorted((root / "cases").glob("*/result.json"))]
    assert [row["task"]["id"] for row in results] == planned[:len(results)]
    assert all(row["thread_id"] == thread["thread_id"] for row in results)
    grouped = collections.defaultdict(lambda: {"scored": 0, "passed": 0, "rewards": []})
    for row in results:
        one, = row["objective"]["instance_outcomes"]
        bucket = grouped[row["task"]["family"]]
        bucket["scored"] += 1
        bucket["passed"] += bool(one["success"])
        bucket["rewards"].append(one["reward"])
    status = (root / "native.stderr").read_text()
    runs = [line.split("CLM run: ", 1)[1] for line in status.splitlines() if "CLM run: " in line]
    audit = list(jsonlines(Path(runs[-1]) / "responses.jsonl")) if runs else []
    usage = {"inputTokens": 0, "cachedInputTokens": 0, "outputTokens": 0, "reasoningOutputTokens": 0}
    peak = 0
    action_requests = 0
    compact_items = 0
    usage_events = 0
    for row in jsonlines(root / "native.jsonl"):
        event = row["data"]
        method = event.get("method")
        if method == "thread/tokenUsage/updated" and thread and event["params"]["threadId"] == thread["thread_id"]:
            values = event["params"]["tokenUsage"]["last"]
            peak = max(peak, values["inputTokens"])
            usage_events += 1
            for name in usage:
                usage[name] += values.get(name, 0)
        elif row["direction"] == "from_codex" and method == "item/tool/call":
            action_requests += 1
        elif method == "item/completed" and event["params"]["item"]["type"] == "contextCompaction":
            compact_items += 1
    marked = {}
    for row in audit:
        markers = row.get("task_markers_after", [])
        if markers:
            marked.setdefault(markers[-1], markers)
    continuity = sum(
        set(f"CODEX_CLBENCH_TASK_{number:03d}" for number in range(1, index + 1))
        <= set(marked.get(f"CODEX_CLBENCH_TASK_{index:03d}", []))
        for index in range(1, len(results) + 1) if not results[index - 1]["initialization_terminal"]
    )
    edits = [row for row in audit if row.get("edit") == "accepted"]
    active = sorted((root / "cases").glob("*/intent.json"))
    return {
        "latest_task": read(active[-1])["task"]["id"] if active else None,
        "current_score": {"scored": len(results), "passed": sum(bucket["passed"] for bucket in grouped.values()), "planned": len(planned)},
        "grouped": grouped,
        "thread": thread,
        "first_request_continuity": continuity,
        "http_200_complete": sum(row.get("http_status") == 200 and row.get("transport") == "eof" for row in audit),
        "api_receipts": len(audit),
        "official_dynamic_calls": action_requests,
        "native_context_compactions": compact_items,
        "accepted_context_edits": len(edits),
        "first_edit": edits[0] if edits else None,
        "latest_edit": edits[-1] if edits else None,
        "edit_statuses": collections.Counter(row.get("edit") for row in audit if row.get("edit")),
        "native_usage_events": usage_events,
        "sum_native_last_request_usage": usage,
        "peak_native_input_tokens": peak,
        "failure": read(root / "FAILURE.json"),
        "native_exit": read(root / "NATIVE_EXIT.json"),
        "result": read(root / "RESULT.json"),
    }


if __name__ == "__main__":
    print(json.dumps(view(), ensure_ascii=False, indent=2))
