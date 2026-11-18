"""Restore only the failed trial after proven response-free upstream timeouts."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from resume_formal import label, read, restored_context
from retry_pair_budget import ARMS, clone_prefix
from run_pair import run_matched, sha
from wire import write_json


def failed_prefix(source, position, maintenance_log):
    plan = read(source / "plan.json")
    launch = read(source / "sessions.json")
    terminal = read(source / "progress.json")
    if (
        plan["stage"] != "formal" or len(plan["tasks"]) != 60
        or read(source / "qualification.json")["formal_plan_sha256"] != sha(source / "plan.json")
        or (source / "exit-status.txt").read_text().strip() != "1"
        or terminal["completed_pairs"] not in (position - 1, position) or (source / "accepted.json").exists()
    ):
        raise ValueError("Source has no matching terminal failure at a frozen pair")
    ready = {}
    history = []
    failed = None
    maintenance_timeout = None
    for row in plan["tasks"][:position]:
        for arm in ARMS:
            evidence = source / arm / "evidence" / label(row)
            receipt_path = evidence / "receipt.json"
            if row["position"] == position and arm == "clm" and not receipt_path.is_file():
                maintenance = source / arm / "maintenance" / label(row)
                prior = source / arm / "evidence" / label(plan["tasks"][position - 2])
                logfile = maintenance_log.read_bytes()[-32000:]
                if (
                    terminal["completed_pairs"] != position - 1
                    or (evidence / "timeline.jsonl").exists()
                    or (maintenance / "maintenance-response.raw").exists()
                    or b"TimeoutError: timed out" not in logfile or b"choose_edits" not in logfile
                    or sha(maintenance / "native-session.before.jsonl") != sha(prior / "native-session.jsonl")
                ):
                    raise ValueError("Current CLM task did not stop on response-free maintenance")
                maintenance_timeout = {"request_sha256": sha(maintenance / "maintenance-request.json")}
                continue
            receipt = read(receipt_path)
            if receipt["session"] != launch["sessions"][arm] or row != receipt["row"]:
                raise ValueError("Receipt belongs to a different session or task")
            history.append(receipt)
            key = row["position"], arm
            if receipt["accepted"]:
                ready[key] = receipt
            elif key == (position, "native"):
                failed = evidence
            else:
                raise ValueError("Unresolved additional trial failure")
    expected_history = history[:-1] if maintenance_timeout else history
    if expected_history != terminal["receipts"] or failed is None:
        raise ValueError("Original trial and controller records disagree")
    old_score = read(failed / "receipt.json")["reward"]
    if old_score is not None:
        raise ValueError("The failed original trial already has an official score")
    failed_responses = []
    for path in (failed / "chat-gateway").glob("*/receipt.json"):
        status = read(path)
        data = path.with_name("response.raw")
        if (
            status.get("forwarded") and not status.get("complete") and status.get("http_status") is None
            and (not data.is_file() or data.stat().st_size == 0)
            and (status.get("failure") or {}).get("kind") == "TimeoutError"
        ):
            failed_responses.append({"attempt": path.parent.name, "receipt_sha256": sha(path)})
    if len(failed_responses) < 2 or not (failed / "residual-tool-cleanup.json").is_file():
        raise ValueError("The archived native failure lacks two upstream timeouts or successful-terminal evidence")
    return plan, launch, ready, failed, failed_responses, maintenance_timeout


async def resume(source, target, position, inspector, maintenance_log, start_gate):
    plan, launch, ready, failed, response_failures, maintenance_timeout = failed_prefix(
        source, position, maintenance_log,
    )
    checkpoint = clone_prefix(source, target, plan, launch, ready)
    latest_clm = source / "clm" / "evidence" / label(plan["tasks"][checkpoint["clm"]["position"] - 1])
    context = restored_context(target / "clm" / "context", latest_clm, ready, source)
    write_json(target / "recovery.json", {
        "source": source.name, "position": position,
        "retried_arms": ["native", "clm"] if maintenance_timeout else ["native"],
        "plan_sha256": sha(target / "plan.json"), "accepted_trials_retained": len(ready),
        "original_native_receipt": sha(failed / "receipt.json"),
        "last_accepted_clm_receipt": sha(latest_clm / "receipt.json"),
        "original_clm_maintenance_timeout": maintenance_timeout,
        "response_free_timeouts": response_failures, "lane_checkpoints": checkpoint,
        "configuration_changed": False,
    })
    if start_gate is not None:
        print("Frozen trail is staged; waiting for a successful same-model health response.", flush=True)
        while not start_gate.is_file():
            await asyncio.sleep(5)
        health = read(start_gate)
        if (
            health["exit_code"] != 0 or not health["verified_ok"]
            or health["requested_model"] != launch["model"] or health["actual_model"] != launch["model"]
        ):
            raise ValueError("The generation health receipt does not match the frozen model")
        write_json(target / "start-gate.json", {
            "verified_model": launch["model"],
            "health_receipt_sha256": sha(start_gate),
            "health_response_sha256": health["response_sha256"],
            "health_observed_at": health["finished_at"],
        })

    def verify_pair(run):
        raw = subprocess.check_output([sys.executable, str(inspector), str(run), "--count", str(position)])
        audit = json.loads(raw)
        if audit["verified_pairs"] != list(range(1, position + 1)):
            raise ValueError("The recovered pair did not pass independent verification")
        (run / f"recovery-prefix-{position:03d}-audit.json").write_bytes(raw)
        print(json.dumps({"recovered_pair": position}), flush=True)

    await run_matched(target, launch["model"], launch["judge_model"], launch["judge_service"], {
        "sessions": launch["sessions"], "ready": ready, "context": context,
        "reuse_edits": {}, "verify_position": position, "verify_prefix": verify_pair,
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--position", type=int, required=True)
    parser.add_argument("--inspector", type=Path, required=True)
    parser.add_argument("--maintenance-log", type=Path, required=True)
    parser.add_argument("--start-gate", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    asyncio.run(resume(args.source, args.target, args.position, args.inspector, args.maintenance_log, args.start_gate))
