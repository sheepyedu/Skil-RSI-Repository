"""Retry the failed native trial from its original accepted session."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from resume_formal import label, read, restored_context
from retry_pair_budget import clone_prefix
from run_pair import run_matched, sha
from serial_agent import NATIVE_AUTO_COMPACT_PERCENT
from wire import write_json


def checkpoints(source, position):
    plan = read(source / "plan.json")
    launch = read(source / "sessions.json")
    progress = read(source / "progress.json")
    if (
        plan["stage"] != "formal" or len(plan["tasks"]) != 60
        or read(source / "qualification.json")["formal_plan_sha256"] != sha(source / "plan.json")
        or not 2 <= position <= len(plan["tasks"]) or progress["completed_pairs"] != position
        or (source / "exit-status.txt").read_text().strip() != "1"
        or (source / "accepted.json").exists() or not (source / "trajectory-sha256.json").is_file()
    ):
        raise ValueError("Expected an archived formal run stopped at the failed native trial")

    ready = {}
    for row in plan["tasks"][:position]:
        for arm in ("native", "clm"):
            if row["position"] == position and arm == "native":
                continue
            evidence = source / arm / "evidence" / label(row)
            receipt = read(evidence / "receipt.json")
            if (
                not receipt["accepted"] or not receipt["session_saved"] or receipt["row"] != row
                or receipt["session"] != launch["sessions"][arm]
                or not receipt["native"]["session_match"] or not receipt["wire"]["official_instruction_exact"]
            ):
                raise ValueError("An earlier trial does not match the accepted checkpoint")
            ready[row["position"], arm] = receipt

    original = plan["tasks"][position - 1]
    failed = source / "native" / "evidence" / label(original)
    receipt = read(failed / "receipt.json")
    if (
        list(ready.values())[:-1] + [receipt, ready[position, "clm"]] != progress["receipts"]
        or receipt["accepted"] or receipt["reward"] is not None
        or receipt["session"] != launch["sessions"]["native"]
        or receipt["row"] != original or not receipt["session_saved"]
        or not receipt["native"]["terminal_error"]
    ):
        raise ValueError("The failed native receipt does not match the terminal progress")

    cli = source / "native" / "trials" / label(original) / "agent" / "cc-output.txt"
    terminals = [event for event in map(json.loads, cli.read_bytes().splitlines()) if event.get("type") == "result"]
    if (
        len(terminals) != 1 or not terminals[0].get("is_error")
        or terminals[0].get("session_id") != receipt["session"]
        or "Prompt is too long" not in terminals[0].get("result", "")
    ):
        raise ValueError("The original CLI did not stop on the observed prompt capacity error")
    calls = sorted((failed / "chat-gateway").glob("*/receipt.json"))
    calls_data = [read(path) for path in calls]
    if not calls_data or not all(call["complete"] and call["http_status"] == 200 for call in calls_data):
        raise ValueError("The failed trial also has an unresolved upstream request")
    return plan, launch, ready, failed, calls[-1], calls_data[-1]["usage"]["prompt_tokens"]


async def resume(source, target, position, inspector):
    plan, launch, ready, failed, last, last_tokens = checkpoints(source, position)
    lanes = clone_prefix(source, target, plan, launch, ready)
    previous = source / "clm" / "evidence" / label(plan["tasks"][position - 1])
    context = restored_context(target / "clm" / "context", previous, ready, source)
    write_json(target / "recovery.json", {
        "source": source.name, "position": position, "retried_arm": "native",
        "plan_sha256": sha(target / "plan.json"), "accepted_trials_retained": len(ready),
        "checkpoint_sessions": lanes, "failed_native_receipt_sha256": sha(failed / "receipt.json"),
        "failed_native_session_sha256": sha(failed / "native-session.jsonl"),
        "last_successful_request_sha256": sha(last.with_name("request.raw")),
        "last_successful_prompt_tokens": last_tokens,
        "native_auto_compaction_percentage": NATIVE_AUTO_COMPACT_PERCENT,
    })

    def verify_prefix(run):
        raw = subprocess.check_output([sys.executable, str(inspector), str(run), "--count", str(position)])
        if json.loads(raw)["verified_pairs"] != list(range(1, position + 1)):
            raise ValueError("Recovered trial did not pass independent prefix verification")
        (run / f"recovery-prefix-{position:03d}-audit.json").write_bytes(raw)

    await run_matched(target, launch["model"], launch["judge_model"], launch["judge_service"], {
        "sessions": launch["sessions"], "ready": ready, "context": context, "reuse_edits": {},
        "verify_position": position, "verify_prefix": verify_prefix,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--inspector", type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    asyncio.run(resume(args.source, args.target, args.position, args.inspector))
