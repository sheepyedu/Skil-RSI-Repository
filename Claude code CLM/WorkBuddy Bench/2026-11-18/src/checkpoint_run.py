"""Read a point-in-time WorkBuddy status without executing or publishing tasks."""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def read(path):
    return json.loads(path.read_bytes()) if path.is_file() else None


def label(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


def trial(run, arm, row):
    evidence = run / arm / "evidence" / label(row)
    receipt_path = evidence / "receipt.json"
    receipt = read(receipt_path)
    if receipt is not None:
        wire = receipt["wire"]
        return {
            "state": "accepted" if receipt["accepted"] else "failed",
            "reward": (receipt.get("reward") or {}).get("reward"),
            "deepseek_requests": wire.get("backend_requests"),
            "deepseek_completed": wire.get("backend_complete"),
            "web_grade_requests": wire.get("successful_judge_responses"),
            "original_instruction_verified": wire["official_instruction_exact"],
            "session_verified": receipt["native"]["session_match"],
            "native_compactions": receipt["native"]["native_compactions"],
            "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
            "exception_type": (receipt.get("exception") or {}).get("exception_type"),
        }
    timeline = evidence / "timeline.jsonl"
    events = [
        json.loads(line) for line in timeline.read_text().splitlines(keepends=True)
        if line.endswith("\n")
    ] if timeline.is_file() else []
    progress = {
        "state": "in_progress" if events else "pending",
        "last_event": events[-1] if events else None,
    }
    if events:
        transport = evidence / "chat-gateway"
        progress["deepseek_attempts_observed"] = sum(p.is_dir() for p in transport.iterdir()) if transport.is_dir() else 0
    if arm == "clm":
        maintenance = run / arm / "maintenance" / label(row)
        if maintenance.is_dir():
            proof = read(maintenance / "receipt.json")
            progress["maintenance"] = {
                "status": proof["status"] if proof else "no_final_receipt",
                "native_preview_message_bytes": (proof or {}).get("native_preview_message_bytes"),
                "projected_bytes": (proof or {}).get("projected_bytes"),
            }
    return progress


def checkpoint(run, pid_path):
    plan_path = run / "plan.json"
    plan = read(plan_path)
    rows = [
        {**{key: row[key] for key in ("position", "domain", "task")},
         "arms": {arm: trial(run, arm, row) for arm in ("native", "clm")}}
        for row in plan["tasks"]
    ]
    paired = [
        row["position"] for row in rows
        if all(arm["state"] == "accepted" for arm in row["arms"].values())
    ]
    current = next((row for row in rows if row["position"] not in paired), None)
    pid = int(pid_path.read_text().strip())
    try:
        proc_status = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[-1].split()[0]
    except FileNotFoundError:
        proc_status = None
    exit_path = run / "exit-status.txt"
    saved_exit = exit_path.read_text().strip() if exit_path.is_file() else None
    launch = read(run / "sessions.json")
    return {
        "observed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "run": run.name,
        "plan_sha256": hashlib.sha256(plan_path.read_bytes()).hexdigest(),
        "model": launch["model"],
        "judge_model": launch["judge_model"],
        "controller_alive": proc_status not in (None, "Z"),
        "exit_status": int(saved_exit) if saved_exit else None,
        "accepted_pairs": len(paired),
        "total_pairs": len(rows),
        "in_progress_or_first_unaccepted_pair": current,
        "closed_trials": [
            row for row in rows
            if any(arm["state"] in ("accepted", "failed") for arm in row["arms"].values())
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("controller_pid_file", type=Path)
    args = parser.parse_args()
    print(json.dumps(checkpoint(args.run, args.controller_pid_file), ensure_ascii=False, indent=2))
