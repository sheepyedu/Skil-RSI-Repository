"""Carry the verified pilot prefix across a correction to Web judge SSE handling."""

import argparse
import asyncio
import shutil
from pathlib import Path

from clm.context import digest, is_message, write_json
from relay import SeriesContext
from run import ARMS, code_sha, one_trial, provider, read, runtime_sha, sha, task_dir, wire_report


def instance_key(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


def restore_context(state, pilot, receipts):
    context = SeriesContext(state)
    saved = read(state / "LIVE_CTX_MAIN.json")
    context.revision = saved["revision"]
    context.note = saved["note"]
    context.visible = {x["id"] for x in saved["editable"]}
    anchor = None
    for receipt in receipts:
        for index, call in enumerate(receipt["wire"]["records"], 1):
            if "clm" not in call:
                continue
            directory = pilot / "clm" / "evidence" / instance_key(receipt["row"]) / "wire" / f"{index:05d}"
            items = read(directory / "request.raw.json")["input"]
            user = next(item for item in items if is_message(item, "user"))
            if digest(user) != anchor:
                context.dropped.clear()
                anchor = digest(user)
            context.dropped.update(call["clm"]["dropped_ids"])
    context.anchor = anchor
    if context.anchor is None or not context.revision:
        raise ValueError("No verifiable CLM context checkpoint")
    return context


async def recover(old, target):
    original, frozen = read(old / "plan.json"), read(target / "plan.json")
    if original["stage"] != "pilot" or frozen["stage"] != "pilot" or original["tasks"] != frozen["tasks"]:
        raise ValueError("Pilot changes the fixed task sequence")
    if read_val(old / "controller.exit") != 1:
        raise ValueError("Expected the original pilot to stop at the Web judge gate")
    if frozen["runtime_sha256"] != runtime_sha() or frozen["code_sha256"] != code_sha():
        raise ValueError("Recovery running against modified runtime")
    changed = {file for file,value in original["code_sha256"].items() if frozen["code_sha256"].get(file) != value}
    if changed != {"relay.py", "run.py"}:
        raise ValueError(f"Unexpected runtime change: {changed}")
    ordered = [(row, arm) for row in frozen["tasks"] for arm in ARMS]
    accepted = []
    previous = {}
    for row, arm in ordered[:-1]:
        evidence = old / arm / "evidence" / instance_key(row)
        receipt = read(evidence / "receipt.json")
        if receipt["row"] != row or receipt["arm"] != arm or sha(evidence / "native-session.jsonl") != receipt["session_sha256"]:
            raise ValueError("Source trial identity, plan entry, or session SHA does not match")
        prefix = previous.get(arm)
        if prefix and prefix["thread"] != receipt["thread"]:
            raise ValueError("Pilot native thread discontinuity")
        if row["position"] == 4:
            if arm != "native" or receipt["accepted"] or receipt["wire"]["successful_judge_calls"] != 0:
                raise ValueError("Unexpected failed Web trial")
            task = task_dir(Path(frozen["reference"]), row)
            report = wire_report(evidence / "wire", row, (task / "instruction.md").read_text(),
                                 prefix["marker"], True)
            if not (
                report["successful_judge_calls"] and report["responses_with_exact_task"] and report["tool_outputs"]
                and not report["missing_tool_host_outputs"] and receipt["exception"] is None
                and receipt["native"].get("native_exit") == 0 and receipt["native"].get("turn")
                and receipt["reward"] and receipt["native"].get("resumed")
            ):
                raise ValueError("Old native Web score has an unresolved execution or verifier failure")
            receipt.update(wire=report, accepted=True, recovery="Chat Completions SSE readback")
        elif not receipt["accepted"]:
            raise ValueError("An earlier pilot receipt failed")
        previous[arm] = receipt
        accepted.append(receipt)
    for arm in ARMS:
        shutil.copytree(old / arm, target / arm, symlinks=True)
    native_web = accepted[-1]
    write_json(target / "native" / "evidence" / instance_key(native_web["row"]) / "receipt.json", native_web)
    write_json(target / "adoption.json", {
        "from": str(old), "plan_sha256": sha(old / "plan.json"), "carried_trials": 7,
        "accounted_correction": "Chat Completions [DONE] recognition and original Web score readback",
        "new_trials": ["004/clm"],
    })
    progress = [{k: v for k, v in item.items() if k != "wire"} for item in accepted]
    write_json(target / "progress.json", progress)
    context = restore_context(target / "clm" / "context", old, [x for x in accepted if x["arm"] == "clm"])
    row, arm = ordered[-1]
    key, base_url = provider()
    receipt = await one_trial(target, frozen, row, arm, previous[arm], key, base_url, context)
    progress.append({k: v for k, v in receipt.items() if k != "wire"})
    write_json(target / "progress.json", progress)
    if not receipt["accepted"]:
        raise RuntimeError("Remaining CLM Web pilot trial did not pass")
    previous[arm] = receipt
    write_json(target / "accepted.json", {
        "pairs": len(frozen["tasks"]), "stage": frozen["stage"], "code_sha256": frozen["code_sha256"],
        "runtime_sha256": frozen["runtime_sha256"], "plan_sha256": sha(target / "plan.json"),
        "threads": {arm: item["thread"] for arm, item in previous.items()},
    })


def read_val(path):
    return int(path.read_text().strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    asyncio.run(recover(args.original, args.target))


if __name__ == "__main__":
    main()
