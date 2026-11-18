"""Recover the Web CLM pilot from its exact pre-dispatch session checkpoint."""

import argparse
import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path

from clm.context import Context

from resume_projection import maintain, restore_context
from run_pair import one_trial, sha, write_json


def read(path):
    return json.loads(path.read_text())


def clone_accepted(source, target, plan, receipts):
    target.mkdir(parents=True)
    for name in ("plan.json", "sessions.json", "offline.yaml"):
        shutil.copy2(source / name, target / name)
    shutil.copytree(source / "datasets", target / "datasets", symlinks=True)
    for arm in ("native", "clm"):
        shutil.copytree(source / arm / "home", target / arm / "home", symlinks=True)
    for attempt in receipts:
        arm = attempt["arm"]
        row = attempt["row"]
        label = f"{row['position']:03d}-{row['domain']}-{row['task']}"
        for subdir in ("trials", "evidence"):
            shutil.copytree(source / arm / subdir / label, target / arm / subdir / label, symlinks=True)


async def main(source, target, reuse_edit):
    plan = read(source / "plan.json")
    previous, row = plan["tasks"][2:]
    progress = read(source / "progress.json")["receipts"]
    accepted = [r for r in progress if r["accepted"]]
    failures = [r for r in progress if not r["accepted"]]
    if (
        plan["stage"] != "pilot" or len(accepted) != 7 or len(failures) != 1
        or failures[0]["arm"] != "clm" or failures[0]["row"] != row
        or failures[0]["wire"]["backend_requests"] != 0
    ):
        raise ValueError("Pilot did not stop in the expected pre-dispatch condition")
    label = f"{row['position']:03d}-{row['domain']}-{row['task']}"
    fail = source / "clm" / "trials" / label / "agent" / "cc-output.txt"
    if '"result":"Prompt is too long"' not in fail.read_text():
        raise ValueError("Local CLI capacity did not cause the stop")
    clone_accepted(source, target, plan, accepted)

    launch = read(source / "sessions.json")
    session = launch["sessions"]["clm"]
    name = f"{previous['position']:03d}-{previous['domain']}-{previous['task']}"
    prior = source / "clm" / "evidence" / name
    native = target / "clm" / "home" / "config" / "projects" / "-workspace" / f"{session}.jsonl"
    if not native.is_file() or native.is_symlink():
        raise ValueError("Original CLI session path is absent")
    shutil.copyfile(prior / "native-session.jsonl", native)
    state = target / "clm" / "context"
    shutil.copytree(prior / "context-after", state, symlinks=True)
    context = Context(state)
    restore_context(context, prior, [r for r in accepted if r["arm"] == "clm"])
    services = read(Path("/mount-data/Tools/services.json"))["services"]
    service = services["deepseek"]["base_url"]
    key = subprocess.check_output(
        ["/mount-data/Tools/skill-api", "_credential", "--service", "deepseek"], text=True
    ).strip()
    judge_key = subprocess.check_output(
        ["/mount-data/Tools/skill-api", "_credential", "--service", launch["judge_service"]], text=True
    ).strip()
    write_json(target / "recovery.json", {
        "original_run": str(source), "reused_accepted_trials": 7,
        "recovery_position": row["position"], "session": session,
        "unprojected_restore_sha256": sha(native), "original_failed_stream_sha256": sha(fail),
    })
    proof = maintain(context, prior, native, target / "clm" / "maintenance" / label, service, key, launch["model"], reuse_edit=reuse_edit)
    if not proof:
        raise ValueError("Missing CLM resume projection")
    print(json.dumps(proof), flush=True)
    receipt = await one_trial(
        target, row, previous, "clm", session, service, key, launch["model"],
        launch["judge_model"], context, judge_key,
    )
    write_json(target / "progress.json", {"completed_pairs": 4, "receipts": [*accepted, receipt]})
    if not receipt["accepted"]:
        raise RuntimeError("Recovered Web trial failed acceptance")
    write_json(target / "accepted.json", {
        "stage": "pilot", "pairs": len(plan["tasks"]), "plan_sha256": sha(target / "plan.json"),
        "sessions": launch["sessions"], "recovery": str(source),
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--reuse-edit", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    asyncio.run(main(args.source, args.target, args.reuse_edit))
