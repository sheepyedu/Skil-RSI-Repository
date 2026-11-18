"""Retry the first output-limit failure under a shared larger output budget."""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from resume_formal import label, read, restored_context
from run_pair import run_matched, sha
from wire import write_json


ARMS = ("native", "clm")
ORIGINAL_BUDGET = 8192
REVISED_BUDGET = 16384


def read_failed_pair(source, position):
    plan = read(source / "plan.json")
    progress = read(source / "progress.json")
    launch = read(source / "sessions.json")
    if (
        plan["stage"] != "formal" or len(plan["tasks"]) != 60
        or read(source / "qualification.json")["formal_plan_sha256"] != sha(source / "plan.json")
        or (source / "exit-status.txt").read_text().strip() != "1"
        or progress["completed_pairs"] != position or (source / "accepted.json").exists()
    ):
        raise ValueError("Expected the complete terminal pair at the frozen failure position")
    ready = {}
    original = {}
    for row in plan["tasks"][:position]:
        for arm in ARMS:
            path = source / arm / "evidence" / label(row) / "receipt.json"
            trial = read(path)
            if trial["session"] != launch["sessions"][arm] or trial["row"] != row:
                raise ValueError("The retained receipt does not match the frozen session and task")
            if row["position"] == position:
                original[arm] = path
            else:
                if not trial["accepted"] or not trial["session_saved"]:
                    raise ValueError("A previous task is missing an accepted checkpoint")
                ready[row["position"], arm] = trial
    if [*ready.values(), *(read(original[a]) for a in ARMS)] != progress["receipts"]:
        raise ValueError("The retained receipts disagree with the controller's terminal progress")

    failed = read(original["native"])
    task_label = label(plan["tasks"][position - 1])
    if failed["accepted"] or failed["reward"] is not None or not failed["native"]["terminal_error"]:
        raise ValueError("The native trial does not match the original unscored CLI failure")
    output = source / "native" / "trials" / task_label / "agent" / "cc-output.txt"
    if b"response exceeded the 8192 output token maximum" not in output.read_bytes():
        raise ValueError("The original failure was not the declared output-limit error")
    tickets = sorted((original["native"].parent / "chat-gateway").glob("*/receipt.json"))
    tail = []
    for ticket in tickets[-3:]:
        response = read(ticket)
        payload = read(ticket.with_name("request.raw"))
        if (
            response["finish_reason"] != "length" or payload.get("max_tokens") != ORIGINAL_BUDGET
            or response["usage"]["completion_tokens"] != ORIGINAL_BUDGET
            or response["usage"]["completion_tokens_details"]["reasoning_tokens"] != ORIGINAL_BUDGET
        ):
            raise ValueError("The last three provider attempts do not confirm the output cap")
        tail.append({"request": ticket.parent.name, "request_sha256": sha(ticket.with_name("request.raw"))})
    if len(tail) != 3:
        raise ValueError("The three original exhausted attempts are required")
    return plan, launch, ready, original, tail


def clone_prefix(source, target, plan, launch, ready, position):
    target.mkdir(parents=True)
    for name in ("plan.json", "sessions.json", "offline.yaml", "qualification.json"):
        shutil.copy2(source / name, target / name)
    shutil.copytree(source / "datasets", target / "datasets", symlinks=True)
    earlier_audits = [source / "first-three-audit.json", *source.glob("recovery-prefix-*-audit.json")]
    for audit in earlier_audits:
        if audit.is_file():
            shutil.copy2(audit, target / audit.name)
    for (number, arm), receipt in ready.items():
        tag = label(receipt["row"])
        for folder in ("trials", "evidence"):
            shutil.copytree(source / arm / folder / tag, target / arm / folder / tag, symlinks=True)
        maintenance = source / arm / "maintenance" / tag
        if (maintenance / "receipt.json").is_file():
            shutil.copytree(maintenance, target / arm / "maintenance" / tag, symlinks=True)

    checkpoints = {}
    previous = label(plan["tasks"][position - 2])
    for arm, session in launch["sessions"].items():
        evidence = source / arm / "evidence" / previous
        snapshot = evidence / "native-session.jsonl"
        if not snapshot.is_file() or snapshot.is_symlink():
            raise ValueError("Missing regular checkpoint from the last accepted task")
        native = target / arm / "home" / "config" / "projects" / "-workspace" / f"{session}.jsonl"
        native.parent.mkdir(parents=True)
        shutil.copy2(snapshot, native)
        attachments = evidence / "native-session-attachments"
        if attachments.is_dir():
            shutil.copytree(attachments, native.with_suffix(""), symlinks=True)
        shutil.copytree(evidence / "memory-notes", target / arm / "home" / "notes", symlinks=True)
        checkpoints[arm] = {"position": position - 1, "session_sha256": sha(native)}
    return checkpoints


async def resume(source, target, position, inspector):
    plan, launch, ready, original, exhausted = read_failed_pair(source, position)
    checkpoints = clone_prefix(source, target, plan, launch, ready, position)
    previous = source / "clm" / "evidence" / label(plan["tasks"][position - 2])
    context = restored_context(target / "clm" / "context", previous, ready, source)
    old_maintenance = source / "clm" / "maintenance" / label(plan["tasks"][position - 1])
    reuse = {position: old_maintenance} if (old_maintenance / "model-edit.json").is_file() else {}
    write_json(target / "recovery.json", {
        "source": source.name, "position": position, "plan_sha256": sha(target / "plan.json"),
        "shared_output_budget_before": ORIGINAL_BUDGET, "shared_output_budget_after": REVISED_BUDGET,
        "original_trial_receipt_sha256": {arm: sha(path) for arm, path in original.items()},
        "original_trial_accepted": {arm: read(path)["accepted"] for arm, path in original.items()},
        "original_native_exhausted_requests": exhausted,
        "prior_checkpoints": checkpoints,
        "serial_agent_sha256": sha(Path(__file__).with_name("serial_agent.py")),
        "accepted_trials_retained": len(ready),
    })

    def verify_pair(run):
        raw = subprocess.check_output([sys.executable, str(inspector), str(run), "--count", str(position)])
        audit = json.loads(raw)
        if audit["verified_pairs"] != list(range(1, position + 1)):
            raise ValueError("The recovered pair did not pass independent verification")
        budgets = {}
        row = plan["tasks"][position - 1]
        for arm in ARMS:
            gateway = run / arm / "evidence" / label(row) / "chat-gateway"
            matched = next(
                raw_path for raw_path in sorted(gateway.glob("*/request.raw"))
                if row["marker"].encode() in raw_path.read_bytes()
            )
            budgets[arm] = {
                "max_tokens": read(matched)["max_tokens"],
                "request_sha256": sha(matched),
            }
            if budgets[arm]["max_tokens"] != REVISED_BUDGET:
                raise ValueError("The provider did not receive the shared output budget")
        audit["recovery_provider_output_budgets"] = budgets
        write_json(run / f"recovery-prefix-{position:03d}-audit.json", audit)
        print(json.dumps({"recovered_pair": position, "provider_output_budgets": budgets}), flush=True)

    await run_matched(target, launch["model"], launch["judge_model"], launch["judge_service"], {
        "sessions": launch["sessions"], "ready": ready, "context": context,
        "reuse_edits": reuse, "verify_position": position, "verify_prefix": verify_pair,
    })


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("source", type=Path)
    options.add_argument("--target", type=Path, required=True)
    options.add_argument("--position", type=int, required=True)
    options.add_argument("--inspector", type=Path, required=True)
    args = options.parse_args()
    os.umask(0o077)
    asyncio.run(resume(args.source, args.target, args.position, args.inspector))
