"""Compare saved WorkBuddy Chat input with the new converter without API requests."""

import argparse
import collections
import json
from pathlib import Path

from skillrl.chat_gateway import _strip_claude_billing_line, deepseek_request


def read(path):
    return json.loads(path.read_bytes())


def audit(run, limit):
    plan = read(run / "plan.json")
    summary = {}
    for arm in ("native", "clm"):
        counts = collections.Counter(other_payload_differences=0)
        for task in plan["tasks"]:
            name = f"{task['position']:03d}-{task['domain']}-{task['task']}"
            trial = run / arm / "evidence" / name
            if not read(trial / "receipt.json")["accepted"]:
                continue
            previous = None
            captures = sorted((trial / "chat-gateway").glob("*/request.raw"))[:limit]
            for capture in captures:
                original = read(capture)
                incoming = read(capture.parent / "request.messages.raw")
                new = deepseek_request(incoming)
                counts["examined_requests"] += 1
                old_system = original["messages"][0]["content"]
                stable_system = _strip_claude_billing_line(old_system)
                if stable_system != old_system:
                    counts["billing_lines_removed"] += 1
                original["messages"][0]["content"] = stable_system
                if original != new:
                    counts["other_payload_differences"] += 1
                if previous is not None:
                    counts["adjacent_pairs"] += 1
                    counts["old_identical_systems"] += previous[0] == old_system
                    counts["stable_identical_systems"] += previous[1] == stable_system
                previous = old_system, stable_system
        summary[arm] = dict(counts)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--per-trial", type=int, default=11)
    args = parser.parse_args()
    print(json.dumps(audit(args.run, args.per_trial), indent=2))
