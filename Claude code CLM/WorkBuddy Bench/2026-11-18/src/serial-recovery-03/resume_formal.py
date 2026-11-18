"""Resume a verified formal CLM stop with no task dispatch in the interrupted arm."""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from clm.context import Context
from recover_pilot import clone_accepted, read
from resume_projection import maintain, restore_context
from run_pair import run_matched, sha
from wire import write_json


def label(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


def checkpoints(source, position):
    plan = read(source / "plan.json")
    launch = read(source / "sessions.json")
    progress = read(source / "progress.json")
    qualification = read(source / "qualification.json")
    if (
        plan["stage"] != "formal" or len(plan["tasks"]) != 60
        or (source / "exit-status.txt").read_text().strip() != "1"
        or qualification["formal_plan_sha256"] != sha(source / "plan.json")
        or not 2 <= position <= len(plan["tasks"])
        or progress["completed_pairs"] != position - 1 or (source / "accepted.json").exists()
    ):
        raise ValueError("Expected an exited formal run with the full accepted prefix")
    sessions = launch["sessions"]
    ready = {}
    for row in plan["tasks"][:position]:
        for arm, session in sessions.items():
            directory = source / arm / "evidence" / label(row)
            if row["position"] == position and arm == "clm":
                if directory.exists() or (source / arm / "trials" / label(row)).exists():
                    raise ValueError("CLM interrupted task has already been dispatched")
                continue
            receipt = read(directory / "receipt.json")
            if (
                not receipt["accepted"] or receipt["row"] != row or receipt["session"] != session
                or not receipt["wire"]["official_instruction_exact"]
                or not receipt["native"]["session_match"] or not receipt["session_saved"]
                or not (directory / "native-session.jsonl").is_file()
            ):
                raise ValueError(f"Unverified checkpoint for {arm} {label(row)}")
            ready[row["position"], arm] = receipt
    if list(ready.values())[:-1] != progress["receipts"]:
        raise ValueError("Trial receipts disagree with the accepted pair checkpoint")
    failed = source / "clm" / "maintenance" / label(plan["tasks"][position - 1])
    previous = source / "clm" / "evidence" / label(plan["tasks"][position - 2])
    if (
        (failed / "receipt.json").exists()
        or read(failed / "maintenance-transport.json")["status"] != 200
        or sha(failed / "native-session.before.jsonl") != sha(previous / "native-session.jsonl")
    ):
        raise ValueError("Expected a saved model selection and an untouched backup")
    for arm, pos in (("native", position), ("clm", position - 1)):
        session = source / arm / "home" / "config" / "projects" / "-workspace" / f"{sessions[arm]}.jsonl"
        snapshot = source / arm / "evidence" / label(plan["tasks"][pos - 1]) / "native-session.jsonl"
        if session.is_symlink() or snapshot.is_symlink() or sha(session) != sha(snapshot):
            raise ValueError(f"Checkpoint and live session differ for {arm}")
    return plan, launch, ready, previous, failed


def restored_context(state, previous, ready, source):
    shutil.copytree(previous / "context-after", state, symlinks=True)
    context = Context(state)
    restore_context(context, previous, [
        receipt for (_, arm), receipt in ready.items() if arm == "clm"
    ])
    for (_, arm), receipt in ready.items():
        if arm != "clm":
            continue
        ledger = source / "clm" / "maintenance" / label(receipt["row"]) / "receipt.json"
        if ledger.is_file():
            context.dropped.update(read(ledger)["edit"].get("dropped_ids", []))
    return context


def exact_probe(source, position):
    _, launch, ready, previous, failed = checkpoints(source, position)
    with tempfile.TemporaryDirectory(prefix="formal-resume-probe-") as tmp:
        work = Path(tmp)
        session = work / "test-session.jsonl"
        shutil.copy2(previous / "native-session.jsonl", session)
        context = restored_context(work / "context", previous, ready, source)
        receipt = maintain(
            context, previous, session, work / "replay", None, None, launch["model"],
            reuse_edit=failed,
        )
        if not receipt or receipt["status"] != "accepted" or sha(session) != receipt["projected_native_sha256"]:
            raise ValueError("Exact recovery probe did not apply the validated maintenance")
        return receipt


async def resume(source, target, inspector, position):
    plan, launch, ready, previous, failed = checkpoints(source, position)
    clone_accepted(source, target, plan, list(ready.values()))
    shutil.copy2(source / "qualification.json", target / "qualification.json")
    for previous_audit in [source / "first-three-audit.json", *source.glob("recovery-prefix-*-audit.json")]:
        if previous_audit.is_file():
            shutil.copy2(previous_audit, target / previous_audit.name)
    target_maintenance = target / "clm" / "maintenance"
    for (_, arm), receipt in ready.items():
        if arm == "clm":
            prior_maintenance = source / "clm" / "maintenance" / label(receipt["row"])
            if (prior_maintenance / "receipt.json").is_file():
                shutil.copytree(prior_maintenance, target_maintenance / prior_maintenance.name, symlinks=True)
    context = restored_context(target / "clm" / "context", previous, ready, source)
    write_json(target / "recovery.json", {
        "source": source.name,
        "plan_sha256": sha(target / "plan.json"),
        "first_unstarted_arm": "clm",
        "first_unstarted_position": position,
        "accepted_native_positions": list(range(1, position + 1)),
        "accepted_clm_positions": list(range(1, position)),
        "original_maintenance_response_sha256": sha(failed / "maintenance-response.raw"),
        "runtime_sha256": {
            name: sha(Path(__file__).with_name(name))
            for name in ("resume_formal.py", "resume_projection.py", "run_pair.py")
        },
    })

    def verify_prefix(run):
        output = subprocess.check_output([sys.executable, str(inspector), str(run), "--count", str(position)])
        observation = json.loads(output)
        (run / f"recovery-prefix-{position:03d}-audit.json").write_bytes(output)
        if observation["verified_pairs"] != list(range(1, position + 1)) or any(
            arm["judge_errors"] for arm in observation["cases"][-1]["arms"].values()
        ):
            raise ValueError("The independent audit failed for the recovered pair")
        earlier_judge_issues = [
            {"position": case["position"], "arm": arm, "attempts": trial["judge_errors"]}
            for case in observation["cases"][:-1] for arm, trial in case["arms"].items()
            if trial["judge_errors"]
        ]
        print(json.dumps({
            "recovered_pair_verified": position,
            "accepted_prefix": observation["verified_pairs"],
            "earlier_judge_issues": earlier_judge_issues,
        }), flush=True)

    await run_matched(target, launch["model"], launch["judge_model"], launch["judge_service"], {
        "sessions": launch["sessions"], "ready": ready, "context": context,
        "reuse_edits": {position: failed}, "verify_position": position, "verify_prefix": verify_prefix,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--target", type=Path)
    parser.add_argument("--inspector", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    if args.target is None:
        print(json.dumps(exact_probe(args.source, args.position), indent=2))
    else:
        if args.inspector is None or not args.inspector.is_file():
            parser.error("--inspector is needed to verify the first three pairs")
        asyncio.run(resume(args.source, args.target, args.inspector, args.position))
