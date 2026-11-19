"""Resume the frozen formal sequence after a transport-only failure on a read-only prefix."""

import argparse
import asyncio
import hashlib
import json
import shutil
from pathlib import Path

import run
from clm.context import write_json
from recover_workbuddy_web_pilot import instance_key, restore_context


async def resume(old, target, gate, regrades=None):
    frozen = run.read(target / "plan.json")
    prior = run.read(old / "plan.json")
    if frozen != prior or frozen["code_sha256"] != run.code_sha():
        raise ValueError("Recovery changes the frozen experiment")
    proof = run.read(gate / "accepted.json")
    if (proof.get("pairs") != 4 or proof["code_sha256"] != frozen["code_sha256"]
            or frozen["runtime_sha256"] != run.runtime_sha()):
        raise ValueError("Recovery runtime differs from the verified pilot")
    if int((old / "controller.exit").read_text()) != 1:
        raise ValueError("Original controller must have exited")
    ordered = [(row, arm) for row in frozen["tasks"] for arm in run.ARMS]
    progress = run.read(old / "progress.json")
    good = [x for x in progress if x["accepted"]]
    bad = [x for x in progress if not x["accepted"]]
    if len(bad) != 1 or len(progress) != len(good) + 1:
        raise ValueError("Expected exactly one terminal failed trial")
    failed = bad[0]
    row, arm = ordered[len(good)]
    if failed["row"] != row or failed["arm"] != arm:
        raise ValueError("Failed source is not the next sequential task")
    source = old / arm / "evidence" / instance_key(row)
    calls = sorted((source / "wire").glob("*/request.raw.json"))
    last_input = run.read(calls[-1])["input"]
    marker = row["marker"]
    boundary = next(i for i, x in enumerate(last_input)
                    if x.get("role") == "user" and marker in json.dumps(x, ensure_ascii=False))
    tool_calls = [x for x in last_input[boundary + 1:]
                  if x.get("type") in ("function_call", "custom_tool_call")]
    expected = (
        'await Promise.allSettled(["find public-assets /serial-home/notes -type f",'
        '"for f in public-assets/extension/extension_src_snapshot/*; do printf \'\\\\n%s\\\\n\' \\"$f\\"; nl -ba \\"$f\\"; done",'
        '"for f in public-assets/policy/* public-assets/extension/*.md public-assets/evidence/*; do printf \'\\\\n%s\\\\n\' \\"$f\\"; nl -ba \\"$f\\"; done"]'
        '.map(async cmd=>text((await tools.exec_command({cmd})).output)))'
    )
    # This recovery is limited to the manually inspected third task's file-reading call.
    actual = tool_calls[0].get("input", "").strip() if tool_calls else ""
    if tool_calls and not (row["position"] == 3 and arm == "native" and len(tool_calls) == 1
                           and actual == expected):
        raise ValueError("Native tool prefix differs from the reviewed read-only call")
    snapshot = [json.loads(line) for line in (source / "native-session.jsonl").open()]
    items = [entry["payload"] for entry in snapshot if entry.get("type") == "response_item"]
    last_user = next(i for i, item in enumerate(items)
                     if item.get("role") == "user" and marker in json.dumps(item, ensure_ascii=False))
    native_calls = [item for item in items[last_user + 1:]
                    if item.get("type") in ("function_call", "custom_tool_call")]
    fields = ("type", "name", "call_id", "input", "arguments")
    if ([{k: item.get(k) for k in fields} for item in native_calls]
            != [{k: item.get(k) for k in fields} for item in tool_calls]):
        raise ValueError("Native history contains extra tool calls after the reviewed prefix")
    error = (failed.get("exception") or {}).get("exception_message", "")
    if "Codex task process exited" not in error or failed.get("reward"):
        raise ValueError("Unexpected trial failure")
    write_json(target / "recovery.json", {
        "source": str(old), "accepted_prefix": len(good), "failed_trial": failed,
        "readonly_tool_sha256": hashlib.sha256(actual.encode()).hexdigest(),
        "reason": "Incomplete upstream stream before next tool delivery",
        "pilot_gate": str(gate),
    })
    previous = {}
    receipts = []
    for item in good:
        p = old / item["arm"] / "evidence" / instance_key(item["row"])
        rec = run.read(p / "receipt.json")
        if run.sha(p / "native-session.jsonl") != rec["session_sha256"]:
            raise ValueError("Prefix session checksum differs")
        previous[item["arm"]] = rec
        receipts.append(rec)
    for name in run.ARMS:
        shutil.copytree(old / name, target / name, symlinks=True)
    if regrades:
        for name, correction in run.read(regrades).items():
            record = next(r for r in receipts if r["arm"] == name and r["row"] == correction["row"])
            private = target / name / "evidence" / instance_key(record["row"])
            patch = Path(correction["source_trial"]) / "verifier/agent.patch"
            if run.sha(patch) != correction["patch_sha256"]:
                raise ValueError("Original model patch differs from the rescored patch")
            shutil.copytree(Path(correction["rescore_trial"]), private / "regrade", symlinks=True)
            record["original_reward"] = record["reward"]
            record["reward"] = correction["reward"]
            record["regrade_result"] = "regrade/result.json"
            record["regrade_patch_sha256"] = correction["patch_sha256"]
            write_json(private / "receipt.json", record)
    failed_evidence = target / arm / "evidence" / instance_key(row)
    failed_evidence.rename(target / arm / ("prior-failed-task-from-" + old.name))
    context = restore_context(target / "clm" / "context", old, [x for x in receipts if x["arm"] == "clm"])
    key, base = run.provider()
    for row, arm in ordered[len(good):]:
        receipt = await run.one_trial(target, frozen, row, arm, previous.get(arm), key, base,
                                      context if arm == "clm" else None)
        output = target / arm / "trials" / receipt["trial_name"] / "verifier" / "test_output.txt"
        if output.exists() and "can't open file '/tests/verifier.py': [Errno 13]" in output.read_text(errors="replace"):
            receipt["accepted"] = False
            receipt["verifier_failure"] = "Generated verifier file was unreadable"
            write_json(target / arm / "evidence" / instance_key(row) / "receipt.json", receipt)
        receipts.append(receipt)
        write_json(target / "progress.json", [{k:v for k,v in x.items() if k!="wire"} for x in receipts])
        if not receipt["accepted"]:
            raise RuntimeError(f"Recovery halted at {row['position']} {arm}")
        previous[arm] = receipt
    write_json(target / "accepted.json", {
        "pairs": len(frozen["tasks"]), "stage": frozen["stage"], "code_sha256": frozen["code_sha256"],
        "runtime_sha256": frozen["runtime_sha256"], "plan_sha256": run.sha(target/"plan.json"),
        "threads": {name:rec["thread"] for name,rec in previous.items()},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("--pilot-gate", type=Path, required=True)
    parser.add_argument("--regrades-json", type=Path)
    args = parser.parse_args()
    asyncio.run(resume(args.original,args.target,args.pilot_gate,args.regrades_json))
