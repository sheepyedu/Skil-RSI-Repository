"""Continue a pinned serial experiment with lossless, bounded transport recovery."""

import argparse
import asyncio
import hashlib
import json
import shutil
from pathlib import Path

import run
from checkpoint import restore_context
from clm.context import write_json
from relay import temporary_provider_failure


def instance_key(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


def validate_upgrade(base, original, pilot, regression):
    frozen = run.read(original / "plan.json")
    proof = run.read(pilot / "accepted.json")
    checks = run.read(regression / "RESULT.json")
    original_code = frozen.get("version_upgrade", {}).get("original_code_sha256", frozen["code_sha256"])
    if (proof["pairs"] != 4 or proof["stage"] != "pilot"
            or proof["code_sha256"] != original_code
            or run.runtime_sha() != frozen["runtime_sha256"]):
        raise ValueError("Original four-category pilot or pinned native runtime changed")
    current = run.code_sha()
    if checks["code_sha256"] != current:
        raise ValueError("Recovery regression source differs from the deployed code")
    if "actual_stream_read_error" in checks and (
            checks["actual_stream_read_error"] != {"attempts": 2, "statuses": [200], "delivered": True}
            or not checks["last_attempt_controls_task_recovery"]):
        raise ValueError("The actual stream-read error regression failed")
    if "actual_bad_status_temporary" in checks and checks["actual_bad_status_temporary"] != {
            "attempts": 2, "statuses": [200], "delivered": True}:
        raise ValueError("The actual temporary bad-status regression failed")
    if "dns_service" in checks:
        path = Path(checks["dns_service"]["result"])
        dns = run.read(path)
        if (run.sha(path) != checks["dns_service"]["sha256"] or dns["code_sha256"] != current
                or dns["api_calls"] != 0 or not dns["initial_dns_healthy"]
                or not dns["restored_dns_healthy"] or not dns["active_zone_preserved"]):
            raise ValueError("DNS startup and checkpoint restoration qualification changed")
    changed = {name for name in current if current[name] != original_code.get(name)}
    if changed != {"relay.py", "run.py", "agent.py", "checkpoint.py", "restore_state.py"}:
        raise ValueError(f"Unexpected code delta outside the reviewed recovery change: {changed}")
    if (checks["retry_then_deliver_once"] != {"attempts": 2, "statuses": [200], "delivered": True}
            or checks["failed_stream_suppressed"] != {"attempts": 3, "statuses": [502], "delivered": False}
            or not checks["clm_projection_restored"]["matches"]
            or not checks["permanent_failure_rejected"]
            or not checks["checkpoint"]["root_file_restored"]
            or not checks["checkpoint"]["artifact_restored"]
            or checks["checkpoint"]["api_calls"] != 0):
        raise ValueError("Recovery regression is incomplete")
    return {"original_code_sha256": original_code, "previous_code_sha256": frozen["code_sha256"],
            "code_sha256": current,
            "pilot": str(pilot), "pilot_sha256": run.sha(pilot / "accepted.json"),
            "regression": str(regression), "regression_sha256": run.sha(regression / "RESULT.json"),
            "qualification": "Original four-category pilot plus targeted zero-API recovery regression"}


def assert_task006_prefix(base, source, row):
    wires = sorted((source / "wire").glob("*/request.raw.json"))
    inputs = run.read(wires[-1])["input"]
    boundary = next(i for i, item in enumerate(inputs)
                    if item.get("role") == "user" and row["marker"] in run.message_text(item))
    calls = [item for item in inputs[boundary + 1:]
             if item.get("type") in ("function_call", "custom_tool_call")]
    actual = [{"call_id": item["call_id"],
               "input_sha256": hashlib.sha256(item.get("input", item.get("arguments", "")).encode()).hexdigest()}
              for item in calls]
    if actual != run.read(base / "task006-restore/reviewed-calls.json"):
        raise ValueError("Task 006 completed calls differ from the reviewed prefix")
    snapshot = [json.loads(line) for line in (source / "native-session.jsonl").open()]
    items = [entry["payload"] for entry in snapshot if entry.get("type") == "response_item"]
    start = next(i for i, item in enumerate(items)
                 if item.get("role") == "user" and row["marker"] in run.message_text(item))
    native = [item for item in items[start + 1:]
              if item.get("type") in ("function_call", "custom_tool_call")]
    fields = ("type", "name", "call_id", "input", "arguments")
    if ([{key: item.get(key) for key in fields} for item in calls]
            != [{key: item.get(key) for key in fields} for item in native]):
        raise ValueError("Native history includes extra operations beyond the reviewed prefix")
    restored = run.read(base / "task006-restore/cpu-state.json")
    if not restored["postpatch_observation_matched"] or restored["patch_engine_exit"]:
        raise ValueError("Reviewed patch restoration was not verified")
    return {"patch_directory": str(base / "task006-restore"),
            "reviewed_calls_sha256": run.sha(base / "task006-restore/reviewed-calls.json"),
            "cpu_restoration": restored}


def eligible_checkpoint(private, receipt):
    checkpoint_path = private / "checkpoint/receipt.json"
    if not checkpoint_path.exists() or receipt.get("reward"):
        return None
    events = sorted((private / "wire").glob("*/receipt.json"))
    if not events:
        return None
    final = run.read(events[-1])
    attempts = sorted((events[-1].parent / "attempts").glob("*/receipt.json"))
    temporary = False
    if attempts:
        value = run.read(attempts[-1])
        status = value.get("status") or 0
        temporary = bool(value.get("temporary_provider_failure") or status in (408, 429, 500, 502, 503, 504)
                         or value.get("transport_error"))
        raw = attempts[-1].parent / "response.raw"
        if raw.exists():
            temporary |= temporary_provider_failure(raw)
    if final.get("delivered") or not temporary:
        return None
    saved = run.read(checkpoint_path)
    if saved["row"] != receipt["row"] or saved["thread"] != receipt["thread"]:
        raise ValueError("Failed-task checkpoint has wrong row or thread")
    if receipt["row"].get("task") == "bb-bin-dns-parse-010":
        state = saved.get("services", {}).get("named", {})
        if not state or state.get("running") != state.get("healthy"):
            return None
    return saved


async def resilient_trial(root, frozen, row, arm, previous, key, base_url, context, initial=None):
    recovery = initial
    for attempt in range(1, 5):
        receipt = await run.one_trial(root, frozen, row, arm, previous, key, base_url,
                                      context, recovery=recovery, attempt=attempt)
        private = root / arm / "evidence" / instance_key(row)
        output = root / arm / "trials" / receipt["trial_name"] / "verifier/test_output.txt"
        if output.exists() and "can't open file '/tests/verifier.py': [Errno 13]" in output.read_text(errors="replace"):
            receipt["accepted"] = False
            receipt["verifier_failure"] = "Generated verifier file was unreadable"
            write_json(private / "receipt.json", receipt)
        if receipt["accepted"]:
            return receipt
        saved = eligible_checkpoint(private, receipt)
        if not saved or attempt == 4:
            return receipt
        archive = root / arm / "failed-attempts" / instance_key(row) / f"attempt-{attempt:02d}"
        archive.parent.mkdir(parents=True, exist_ok=True)
        private.rename(archive)
        saved["artifacts"] = str(archive / "checkpoint/artifacts")
        saved["archive"] = str(archive / "checkpoint/image.tar")
        recovery = {"checkpoint": saved, "failed_evidence": str(archive), "attempt": attempt + 1}
        write_json(archive / "recovery-intent.json", recovery)
        print(f"RECOVER {row['position']} {arm} checkpoint {saved['image_id']}", flush=True)
        await asyncio.sleep(min(30 * 2 ** (attempt - 1), 300))
    raise AssertionError("unreachable")


async def execute(base, old, target, pilot, regression):
    upgrade = validate_upgrade(base, old, pilot, regression)
    if int((old / "controller.exit").read_text()) != 1:
        raise ValueError("Original controller is not terminal")
    prior = run.read(old / "plan.json")
    ordered = [(row, arm) for row in prior["tasks"] for arm in run.ARMS]
    progress = run.read(old / "progress.json")
    good = [item for item in progress if item["accepted"]]
    if (len(progress) != len(good) + 1 or progress[-1]["accepted"]
            or not all(item["accepted"] for item in progress[:-1])):
        raise ValueError("Expected a completed prefix and exactly one terminal interrupted task")
    row, arm = ordered[len(good)]
    if progress[-1]["row"] != row or progress[-1]["arm"] != arm:
        raise ValueError("Unexpected failed task")
    source = old / arm / "evidence" / instance_key(row)
    saved = eligible_checkpoint(source, progress[-1])
    if saved:
        initial = {"checkpoint": saved}
    elif old.name == "formal-12" and row["position"] == 6 and arm == "native" and len(good) == 10:
        initial = assert_task006_prefix(base, source, row)
    else:
        raise ValueError("Failed task lacks a verified recoverable workspace checkpoint")
    target.mkdir(mode=0o700)
    frozen = {**prior, "code_sha256": run.code_sha(), "version_upgrade": upgrade}
    write_json(target / "plan.json", frozen)
    shutil.copy2(old / "offline.yaml", target / "offline.yaml")
    for name in run.ARMS:
        shutil.copytree(old / name, target / name, symlinks=True)
    failed = target / arm / "evidence" / instance_key(row)
    archive = target / arm / "failed-attempts" / instance_key(row) / ("source-" + old.name)
    archive.parent.mkdir(parents=True, exist_ok=True)
    failed.rename(archive)
    if saved:
        saved["artifacts"] = str(archive / "checkpoint/artifacts")
        saved["archive"] = str(archive / "checkpoint/image.tar")
    write_json(target / "recovery.json", {"source": str(old), "accepted_prefix": len(good),
                                          "failed_evidence": str(archive), "initial": initial, "upgrade": upgrade})
    receipts, previous = [], {}
    for item, (expected_row, expected_arm) in zip(good, ordered):
        private = target / expected_arm / "evidence" / instance_key(expected_row)
        record = run.read(private / "receipt.json")
        if (record["row"] != expected_row or record["arm"] != expected_arm or not record["accepted"]
                or run.sha(private / "native-session.jsonl") != record["session_sha256"]):
            raise ValueError("Accepted prefix changed")
        receipts.append(record)
        previous[expected_arm] = record
    context = restore_context(target / "clm/context", target / "clm")
    key, base_url = run.provider()
    for index, (row, arm) in enumerate(ordered[len(good):]):
        print(f"START {row['position']:03d} {row['domain']} {arm} {row['task']}", flush=True)
        receipt = await resilient_trial(target, frozen, row, arm, previous[arm], key, base_url,
                                         context if arm == "clm" else None, initial if index == 0 else None)
        receipts.append(receipt)
        write_json(target / "progress.json", [{k: v for k, v in value.items() if k != "wire"} for value in receipts])
        if not receipt["accepted"]:
            raise RuntimeError(f"Continuation halted at {row['position']} {arm}")
        previous[arm] = receipt
    write_json(target / "accepted.json", {
        "pairs": len(frozen["tasks"]), "stage": frozen["stage"], "code_sha256": frozen["code_sha256"],
        "runtime_sha256": frozen["runtime_sha256"], "plan_sha256": run.sha(target / "plan.json"),
        "threads": {name: record["thread"] for name, record in previous.items()},
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for argument in ("base", "original", "target", "pilot", "regression"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    asyncio.run(execute(args.base, args.original, args.target, args.pilot, args.regression))
