"""Read saved evidence and report paired completion, official scores and trace coverage."""

import argparse
import collections
import hashlib
import json
import statistics
from pathlib import Path

from wire import write_json


def read(path):
    return json.loads(path.read_text())


def inventory(run, data):
    entries = []
    for path in sorted(run.glob("*")):
        if path.is_symlink() or path.name not in {"native", "clm"}:
            continue
        for directory in ("evidence", "trials", "maintenance", "home/config/projects"):
            for item in sorted((path / directory).rglob("*")):
                if not item.is_file() or item.is_symlink():
                    continue
                with item.open("rb") as stream:
                    checksum = hashlib.file_digest(stream, "sha256").hexdigest()
                entries.append({"path": str(item.relative_to(run)), "bytes": item.stat().st_size, "sha256": checksum})
    write_json(data, entries)
    return {"files": len(entries), "bytes": sum(e["bytes"] for e in entries)}


def audit(run):
    plan = read(run / "plan.json")
    sessions = read(run / "sessions.json") if (run / "sessions.json").exists() else {}
    summary = {
        "stage": plan["stage"], "total_pairs": len(plan["tasks"]), "sessions": sessions,
        "complete_pairs": 0, "accepted_pairs": 0, "by_domain": {},
        "arm": {}, "rows": [],
    }
    arm_counts = {arm: collections.Counter() for arm in ("native", "clm")}
    scores = collections.defaultdict(list)
    for row in plan["tasks"]:
        name = f"{row['position']:03d}-{row['domain']}-{row['task']}"
        item = {"row": row, "arms": {}}
        for arm, counts in arm_counts.items():
            p = run / arm / "evidence" / name
            t = run / arm / "trials" / name
            path = p / "receipt.json"
            if not path.exists():
                item["arms"][arm] = {"state": "incomplete" if p.exists() else "not_started"}
                continue
            obj = read(path)
            counts["completed_trials"] += 1
            counts["accepted_trials"] += bool(obj["accepted"])
            counts["launches_with_native_session"] += bool(obj["session_saved"])
            counts["native_stdout_logs"] += (t / "agent" / "cc-output.txt").exists()
            counts["atif_trajectories"] += (t / "agent" / "trajectory.json").exists()
            counts["native_compactions"] += obj["native"].get("native_compactions", 0)
            calls = obj["wire"]
            if "official_instruction_exact" in calls:
                counts["exact_instruction_trials"] += bool(calls["official_instruction_exact"])
            for key in ("backend_requests", "backend_complete", "recorded_http_requests"):
                counts[key] += calls.get(key, 0)
            counts["accepted_context_edits"] += sum(e.get("edit") == "accepted" for e in calls["context_events"])
            counts["context_applied_requests"] += sum(e.get("removed_this_request", 0) > 0 for e in calls["context_events"])
            for usage in calls.get("provider_usage", []):
                for field in ("prompt_tokens", "completion_tokens", "prompt_cache_hit_tokens", "prompt_cache_miss_tokens"):
                    counts[field] += usage.get(field) or 0
            exception = (obj["exception"] or {}).get("exception_type")
            item["arms"][arm] = {
                "state": "accepted" if obj["accepted"] else "failed",
                "official_rewards": obj["reward"], "exception": exception,
                "session_match": obj["native"]["session_match"],
                "previous_marker": calls["previous_marker_in_first_success"],
                "official_instruction_exact": calls.get("official_instruction_exact"),
                "backend_complete": calls.get("backend_complete", 0),
                "backend_requests": calls.get("backend_requests", 0),
            }
        arms = item["arms"].values()
        if all(a["state"] in ("accepted", "failed") for a in arms):
            summary["complete_pairs"] += 1
        if all(a["state"] == "accepted" for a in arms):
            summary["accepted_pairs"] += 1
            pair = tuple(a["official_rewards"].get("reward") for a in arms)
            if all(isinstance(x, (float, int)) for x in pair):
                scores[row["domain"]].append(pair)
        summary["rows"].append(item)
    summary["arm"] = {arm: dict(c) for arm, c in arm_counts.items()}
    for domain, pairs in scores.items():
        summary["by_domain"][domain] = {
            "paired": len(pairs),
            "native_mean_reward": statistics.mean(pair[0] for pair in pairs),
            "clm_mean_reward": statistics.mean(pair[1] for pair in pairs),
            "mean_paired_difference": statistics.mean(pair[1] - pair[0] for pair in pairs),
        }
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--save", type=Path)
    parser.add_argument("--inventory", type=Path)
    args = parser.parse_args()
    report = audit(args.run)
    if args.inventory:
        report["file_inventory"] = inventory(args.run, args.inventory)
    if args.save:
        write_json(args.save, report)
    else:
        print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
