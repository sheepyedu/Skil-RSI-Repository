"""Verify actual chronology and original session IDs for accepted WorkBuddy trials."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def trial_interval(evidence):
    interval = {}
    for line in (evidence / "timeline.jsonl").read_bytes().splitlines():
        event = json.loads(line)
        name = event["event"]
        if name in {"start", "agent-start", "agent-end", "verification-start", "end"}:
            if name in interval:
                raise ValueError(f"Duplicated timeline event {name} in {evidence.name}")
            interval[name] = datetime.fromisoformat(event["timestamp"])
    ordered = [interval[n] for n in ("start", "agent-start", "agent-end", "verification-start", "end")]
    if ordered != sorted(ordered):
        raise ValueError(f"The accepted trial has a reversed timeline in {evidence.name}")
    return ordered[0], ordered[-1]


def audit(run, original):
    plan = read(run / "plan.json")
    launch = read(run / "sessions.json")
    progress = read(run / "progress.json")
    plan_hash = sha(run / "plan.json")
    if (
        plan["stage"] != "formal" or len(plan["tasks"]) != 60
        or plan_hash != sha(original / "plan.json")
        or read(run / "qualification.json")["formal_plan_sha256"] != plan_hash
        or launch != read(original / "sessions.json")
    ):
        raise ValueError("The active run does not share the frozen plan and original session configuration")

    count = progress["completed_pairs"]
    pairs = plan["tasks"][:count]
    if len(pairs) != count or len(progress["receipts"]) != 2 * count:
        raise ValueError("The accepted progress does not contain exactly two trials per pair")

    intervals = []
    for index, row in enumerate(pairs, 1):
        if row["position"] != index:
            raise ValueError("The task is out of frozen order")
        label = f"{index:03d}-{row['domain']}-{row['task']}"
        for arm_index, arm in enumerate(("native", "clm")):
            evidence = run / arm / "evidence" / label
            path = evidence / "receipt.json"
            receipt = read(path)
            expected_session = launch["sessions"][arm]
            if (
                receipt != progress["receipts"][2 * (index - 1) + arm_index]
                or receipt["row"] != row or receipt["arm"] != arm or not receipt["accepted"]
                or receipt["session"] != expected_session
                or not receipt["native"]["session_match"] or not receipt["session_saved"]
                or not receipt["wire"]["official_instruction_exact"]
                or receipt["reward"] is None
            ):
                raise ValueError(f"Mismatched accepted receipt for task {index} {arm}")
            started, ended = trial_interval(evidence)
            intervals.append((started, ended, index, arm, sha(path)))

    result = []
    clm_first = []
    prior_end = None
    prior_position = 0
    for started, ended, index, arm, receipt_hash in sorted(intervals):
        if (prior_end is not None and started < prior_end) or index < prior_position:
            raise ValueError(f"Overlapping or out-of-order accepted trials at task {index} {arm}")
        if index != prior_position and arm == "clm":
            clm_first.append(index)
        prior_end = ended
        prior_position = index
        result.append({
            "position": index, "arm": arm, "started_at": started.isoformat(),
            "ended_at": ended.isoformat(), "receipt_sha256": receipt_hash,
        })

    accepted_path = run / "accepted.json"
    terminal = read(accepted_path) if accepted_path.is_file() else None
    complete = terminal is not None
    if complete and (
        count != len(plan["tasks"]) or terminal["pairs"] != count
        or terminal["plan_sha256"] != plan_hash or terminal["sessions"] != launch["sessions"]
        or (run / "exit-status.txt").read_text().strip() != "0"
    ):
        raise ValueError("The final controller record disagrees with the verified trials")
    return {
        "run": run.name, "reference_run": original.name, "plan_sha256": plan_hash,
        "model": launch["model"], "accepted_pairs": count, "complete": complete,
        "same_original_sessions": True, "accepted_clm_before_native_positions": clm_first,
        "verified_serial_trials": result,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("original", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.run, args.original), ensure_ascii=False, indent=2))
