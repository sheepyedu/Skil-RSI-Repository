"""Retry a failed pilot position from each arm's last accepted native checkpoint."""

import argparse
import asyncio
import json
import os
import shutil
from pathlib import Path

from clm.context import Context

from recover_pilot import clone_accepted
from resume_projection import restore_context
from run_pair import run_matched, sha
from wire import write_json


def read(path):
    return json.loads(path.read_text())


def label(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


async def main(source, target):
    plan = read(source / "plan.json")
    launch = read(source / "sessions.json")
    if plan["stage"] != "pilot" or (source / "accepted.json").exists():
        raise ValueError("Only a failed pilot is eligible")
    receipts = []
    for row in plan["tasks"]:
        tag = label(row)
        for arm in ("native", "clm"):
            receipt = source / arm / "evidence" / tag / "receipt.json"
            if receipt.is_file():
                receipts.append(read(receipt))
    failed = [r for r in receipts if not r["accepted"]]
    if not failed:
        raise ValueError("The source has no terminal failed position")
    failed_position = min(r["row"]["position"] for r in failed)
    ready = {}
    for arm in launch["sessions"]:
        for pos in range(1, failed_position + 1):
            passed = next(
                (r for r in receipts if r["arm"] == arm and r["row"]["position"] == pos
                 and r["accepted"] and r["wire"].get("official_instruction_exact")),
                None,
            )
            if not passed:
                break
            ready[pos, arm] = passed
    accepted = list(ready.values())
    if any((pos, arm) not in ready for pos in range(1, failed_position) for arm in launch["sessions"]):
        raise ValueError("The accepted prefix is incomplete")

    clone_accepted(source, target, plan, accepted)
    state = target / "clm" / "context"
    context = Context(state)
    retained = []
    for arm, session in launch["sessions"].items():
        old = sorted((r for r in accepted if r["arm"] == arm), key=lambda r: r["row"]["position"])
        home = target / arm / "home"
        if not old:
            shutil.rmtree(home)
            continue
        last = old[-1]["row"]
        path = source / arm / "evidence" / label(last)
        raw = path / "native-session.jsonl"
        native = home / "config" / "projects" / "-workspace" / f"{session}.jsonl"
        if native.is_symlink() or raw.is_symlink():
            raise ValueError("Unexpected session symlink")
        shutil.copyfile(raw, native)
        notes = home / "notes"
        if notes.exists():
            shutil.rmtree(notes)
        shutil.copytree(path / "memory-notes", notes, symlinks=True)
        attached = native.with_suffix("")
        if attached.exists():
            shutil.rmtree(attached)
        old_attachment = path / "native-session-attachments"
        if old_attachment.exists():
            shutil.copytree(old_attachment, attached, symlinks=True)
        if arm == "clm":
            shutil.copytree(path / "context-after", state, symlinks=True)
            restore_context(context, path, old)
            for completed in old:
                maintenance = source / arm / "maintenance" / label(completed["row"])
                if maintenance.is_dir():
                    new = target / arm / "maintenance" / maintenance.name
                    shutil.copytree(maintenance, new, symlinks=True)
                    edit = read(new / "receipt.json")["edit"]
                    context.dropped.update(edit.get("dropped_ids", []))
        retained.append({"arm": arm, "position": last["position"], "session_sha256": sha(raw)})
    write_json(target / "recovery.json", {
        "source": str(source), "failed_position": failed_position,
        "reused": retained, "accepted_trials_retained": len(accepted),
        "failed": [
            {"arm": r["arm"], "row": r["row"], "exception": r["exception"],
             "backend_requests": r["wire"].get("backend_requests")}
            for r in failed
        ],
    })
    await run_matched(
        target, launch["model"], launch["judge_model"], launch["judge_service"],
        {"sessions": launch["sessions"], "ready": ready, "context": context},
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    asyncio.run(main(args.source, args.target))
