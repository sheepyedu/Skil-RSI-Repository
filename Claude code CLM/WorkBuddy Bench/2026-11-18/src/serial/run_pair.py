"""Prepare and run matched WorkBuddy tasks, one turn at a time per Claude session."""

import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import tomllib
import uuid
from pathlib import Path

import toml
import yaml
from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig, VerifierConfig
from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial
from workbuddy_bench.runner.prepare_tasks import ensure_composite_verifier_contract, ensure_task_user

from clm.context import Context
from skillrl.chat_gateway import ChatMessagesGateway

from resume_projection import maintain
from wire import Wire, write_json

CODE = Path(__file__).resolve().parent
H20 = Path("/mount-data/Claude-code-CLM")
BASE = "https://cn.affordablerouter.com"
DOMAINS = ("code", "office", "sec", "web")
CLI_MODEL = "deepseek-v4-1-flash-261017"
JUDGE_MODEL = "gpt-6.1-sol"
PILOT = {
    "code": "bug_fix-easy-a_crash_in_local",
    "office": "calendar-dida-sync-state",
    "sec": "linux-ld-preload-rule-gen",
    "web": "chart-generation-L2-025",
}
SEED = "workbuddy-clm-v1.0-20261118"


def source_dataset(experiment, domain):
    return experiment / "upstream" / "datasets" / f"wb-bench-{domain}-v1.0"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory(experiment):
    result = {}
    for domain in DOMAINS:
        dataset = source_dataset(experiment, domain)
        tasks = sorted(p.parent.name for p in (dataset / "tasks").glob("*/task.toml"))
        expected = tomllib.loads((dataset / "dataset.toml").read_text())["dataset"]["task_count"]
        if len(tasks) != expected:
            raise ValueError(f"{domain} source expected {expected} tasks; found {len(tasks)}")
        result[domain] = tasks
    return result


def rank(*parts):
    return hashlib.sha256(":".join((SEED, *parts)).encode()).hexdigest()


def make_plan(experiment, stage, allowlist_path):
    catalog = inventory(experiment)
    expected = dict(zip(DOMAINS, (20, 12, 10, 18)))
    if stage == "pilot":
        picks = [(domain, PILOT[domain]) for domain in DOMAINS]
    else:
        if allowlist_path is None:
            raise ValueError("Formal run requires the reviewed task allowlist")
        verified = json.loads(allowlist_path.read_text())
        picks = []
        for domain in DOMAINS:
            names = verified[domain]
            if len(names) != len(set(names)) or not set(names) <= set(catalog[domain]):
                raise ValueError(f"Invalid approved task inventory for {domain}")
            available = sorted(
                set(names) - {PILOT[domain]}, key=lambda name: rank("sample", domain, name)
            )
            picks.extend((domain, name) for name in available[:expected[domain]])
        picks.sort(key=lambda row: rank("order", *row))
    rows = []
    for position, (domain, task) in enumerate(picks, start=1):
        source = source_dataset(experiment, domain) / "tasks" / task
        rows.append({
            "position": position, "domain": domain, "task": task,
            "instruction_sha256": sha(source / "instruction.md"),
            "dockerfile_sha256": sha(source / "environment" / "Dockerfile"),
            "marker": "WB_SERIAL_TASK_" + rank(stage, domain, task)[:20].upper(),
        })
    return {
        "stage": stage,
        "seed": SEED,
        "declared_formal_quota": expected,
        "formal_scope": "60 matched tasks, including 10 approved defensive Security tasks; separate 4-task pilot",
        "source_totals": {domain: len(tasks) for domain, tasks in catalog.items()},
        "chosen_totals": {domain: sum(row["domain"] == domain for row in rows) for domain in DOMAINS},
        "tasks": rows,
    }


def stage_task(experiment, run, row, image):
    domain, task = row["domain"], row["task"]
    origin = source_dataset(experiment, domain)
    dataset = run / "datasets" / origin.name
    staged = dataset / "tasks" / task
    staged.parent.mkdir(parents=True, exist_ok=True)
    if not (dataset / "dataset.toml").exists():
        shutil.copy2(origin / "dataset.toml", dataset / "dataset.toml")
        if (origin / "shared").is_dir():
            shutil.copytree(origin / "shared", dataset / "shared")
    shutil.copytree(origin / "tasks" / task, staged)
    ensure_composite_verifier_contract(staged)
    ensure_task_user(staged, agent_user="dev", verifier_user="root" if domain != "code" else "dev")
    task_toml = staged / "task.toml"
    data = toml.loads(task_toml.read_text())
    # Docker network=none provides the same isolation to both arms. The socket
    # is deliberately the only transport, including for the official VLM judge.
    for section in ("agent", "environment", "verifier"):
        if section in data:
            config = data[section]
            config.pop("network_mode", None)
            config.pop("allowed_hosts", None)
    if data.get("steps"):
        raise ValueError("An explicit per-step network configuration is required for this task")
    if image:
        data["environment"]["docker_image"] = image
    task_toml.write_text(toml.dumps(data))
    compose = staged / "environment" / "docker-compose.yaml"
    if compose.exists():
        existing = yaml.safe_load(compose.read_text())
        if existing == {"services": {"main": {"extra_hosts": ["host.docker.internal:host-gateway"]}}}:
            compose.unlink()
        else:
            raise ValueError("Task requires a custom Compose review before offline execution")
    run_compose = run / "offline.yaml"
    if not run_compose.exists():
        run_compose.write_text("services:\n  main:\n    network_mode: none\n")
    return staged


def binding(source, target, read_only=True):
    bind = {"type": "bind", "source": str(source), "target": target, "bind": {"create_host_path": False}}
    if read_only:
        bind["read_only"] = True
    return bind


def native_receipt(log, session):
    if not log.exists():
        return {"events": 0, "session_match": False, "terminal": False, "terminal_error": None,
                "native_compactions": 0}
    rows = []
    for line in log.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    ids = sorted({row["session_id"] for row in rows if row.get("type") == "system" and row.get("subtype") == "init"})
    terminal = [row for row in rows if row.get("type") == "result"]
    return {
        "events": len(rows), "session_match": ids == [session], "session_ids": ids,
        "terminal": bool(terminal),
        "terminal_error": terminal[-1].get("is_error") if terminal else None,
        "native_compactions": sum(row.get("subtype") == "compact_boundary" for row in rows),
    }


def contains_instruction(messages, marker, instruction):
    for message in messages:
        if message["role"] != "user":
            continue
        value = message["content"]
        parts = [value] if isinstance(value, str) else [
            item.get("text", "") for item in value if item.get("type") == "text"
        ]
        if any(marker in part and instruction.strip() in part for part in parts):
            return True
    return False


def wire_receipt(path, backend, row, previous, arm, instruction):
    requests = 0
    valid_responses = 0
    judge_responses = 0
    history = False
    exact_instruction = False
    edits = []
    records = []
    by_projection = {}
    for item in sorted(backend.iterdir()):
        intent = item / "intent.json"
        receipt = item / "receipt.json"
        if intent.exists() and receipt.exists():
            digest = json.loads(intent.read_text())["incoming_sha256"]
            entry = json.loads(receipt.read_text())
            by_projection.setdefault(digest, []).append((entry, item))
    for directory in sorted(path.iterdir()):
        record_path = directory / "metadata.json"
        if not record_path.exists():
            continue
        meta = json.loads(record_path.read_text())
        records.append(meta)
        if meta.get("actor") == "judge" and meta.get("http_status") == 200:
            judge_responses += 1
        if meta.get("actor") != "agent" or not meta["route"].startswith("/v1/messages") or "count_tokens" in meta["route"]:
            continue
        requests += 1
        upstream = directory / "request.upstream.json"
        if not upstream.exists():
            continue
        body = json.loads(upstream.read_text())
        messages = json.dumps(body["messages"], ensure_ascii=False)
        digest = sha(upstream)
        matching = [(entry, path) for entry, path in by_projection.get(digest, ()) if entry["complete"]]
        backend_complete = bool(matching)
        if backend_complete and meta.get("http_status") == 200 and row["marker"] in messages and meta.get("transport") == "eof":
            if not valid_responses:
                history = bool(previous and previous["marker"] in messages)
                exact_instruction = contains_instruction(body["messages"], row["marker"], instruction) and any(
                    contains_instruction(json.loads((p / "request.raw").read_bytes())["messages"], row["marker"], instruction)
                    for _, p in matching
                )
            valid_responses += 1
        if "context" in meta:
            edits.append(meta["context"])
        if arm == "native" and (directory / "request.raw.json").read_bytes() != upstream.read_bytes():
            raise RuntimeError("Native request bytes were modified in transit")
    return {
        "requests": requests, "valid_current_task_responses": valid_responses,
        "previous_marker_in_first_success": history, "successful_judge_responses": judge_responses,
        "official_instruction_exact": exact_instruction,
        "context_events": edits, "recorded_http_requests": len(records),
        "backend_requests": sum(len(entries) for entries in by_projection.values()),
        "backend_complete": sum(entry["complete"] for entries in by_projection.values() for entry, _ in entries),
        "provider_usage": [
            entry["usage"] for entries in by_projection.values() for entry, _ in entries
            if entry["complete"] and entry["usage"]
        ],
    }


async def one_trial(run, row, previous, arm, session, service, key, model, judge_model, context, judge_key):
    stage_path = run / "datasets" / f"wb-bench-{row['domain']}-v1.0" / "tasks" / row["task"]
    trial_name = f"{row['position']:03d}-{row['domain']}-{row['task']}"
    arm_dir = run / arm
    trial_root = arm_dir / "trials"
    private = arm_dir / "evidence" / trial_name
    private.mkdir(parents=True, mode=0o700)
    home = arm_dir / "home"
    state = arm_dir / "context" if arm == "clm" else None
    for directory in (home, home / "notes", home / "config", state):
        if directory:
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state:
        # Keep a copy beside wire evidence at each task boundary.
        shutil.copytree(state, private / "context-before", symlinks=True)
    backend = ChatMessagesGateway(service, key, model, private / "chat-gateway", timeout=360)
    (private / "chat-gateway").mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix="wb-serial-", dir="/tmp") as tmp:
        socket_path = Path(tmp) / "messages.sock"
        with Wire(socket_path, private / "wire", BASE, backend, model, judge_model, context, judge_key) as gateway:
            gateway.timeout_sec = 380
            mounts = [
                binding(H20 / "runtime" / "claude", "/opt/claude"),
                binding(H20 / "clm", "/opt/clm/clm"),
                binding(CODE, "/opt/serial"),
                binding(socket_path, "/gateway/messages.sock"),
                binding(home, "/serial-home", False),
            ]
            if state:
                mounts.extend((binding(state, "/context", False), binding(H20 / "bin", "/opt/clm/bin")))
            else:
                # Prevent the control agent from seeing an unused CLM interface.
                mounts[1] = binding(H20 / "clm" / "container_entry.py", "/opt/clm/clm/container_entry.py")
            web = row["domain"] == "web"
            verifier_env = {
                "WEB_BENCH_LLM_JUDGE_MODE": "full",
                "WEB_BENCH_LLM_TIMEOUT_SEC": "1200",
                "WORKBUDDY_VERIFIER_LLM_BASE_URL": "http://127.0.0.1:19731/v1",
                "WORKBUDDY_VERIFIER_LLM_API_KEY": gateway.judge_token,
                "WORKBUDDY_VERIFIER_LLM_MODEL": judge_model,
            } if web else {}
            trial = await Trial.create(TrialConfig(
                task=TaskConfig(path=stage_path),
                trial_name=trial_name,
                trials_dir=trial_root,
                agent=AgentConfig(
                    import_path="serial_agent:SerialCcAgent", model_name=model,
                    kwargs={
                        "arm": arm, "position": row["position"], "session_id": session,
                        "marker": row["marker"], "web": web, "CLAUDE_CODE_VERSION": "2.1.160",
                        "settings_preset": json.loads((CODE / "settings.json").read_text()),
                        "CLAUDE_CODE_MAX_TURNS": 256,
                    },
                ),
                environment=EnvironmentConfig(
                    import_path="workbuddy_bench.runner.docker_environment:WorkBuddyDockerEnvironment",
                    mounts=mounts, extra_docker_compose=[run / "offline.yaml"],
                ),
                verifier=VerifierConfig(
                    import_path=(
                        "workbuddy_bench.judge:CompositeVerifier"
                        if row["domain"] != "sec" and not row["task"].startswith("plumbing-")
                        else None
                    ),
                    env=verifier_env,
                ),
                artifacts={
                    "office": [{"source": "/workspace/output", "destination": "office-output"}],
                    "web": [{"source": "/workspace/submission", "destination": "web-submission"}],
                }.get(row["domain"], []),
            ))
            async def hook(event):
                with (private / "timeline.jsonl").open("a") as trace:
                    trace.write(json.dumps({"event": event.event.value, "timestamp": event.timestamp.isoformat()}) + "\n")
                if web and event.event == TrialEvent.VERIFICATION_START:
                    gateway.judge_enabled = True
                if event.event in (TrialEvent.CANCEL, TrialEvent.END):
                    gateway.judge_enabled = False

            for event_type in TrialEvent:
                trial.add_hook(event_type, hook)
            thread = threading.Thread(target=gateway.serve_forever, daemon=True)
            backend.start()
            thread.start()
            try:
                result = await trial.run()
            finally:
                gateway.shutdown()
                thread.join()
                # A disconnected Claude CLI can leave a finite upstream response in flight.
                until = time.monotonic() + gateway.timeout_sec + 5
                while gateway.active and time.monotonic() < until:
                    await asyncio.sleep(1)
                backend.close()
            if gateway.active:
                raise RuntimeError("Relay evidence failed to close")

    trial_dir = trial_root / trial_name
    session_file = home / "config" / "projects" / "-workspace" / f"{session}.jsonl"
    session_saved = session_file.is_file() and not session_file.is_symlink()
    if session_saved:
        shutil.copy2(session_file, private / "native-session.jsonl")
    attachments = session_file.with_suffix("")
    if attachments.is_dir() and not attachments.is_symlink():
        shutil.copytree(attachments, private / "native-session-attachments", symlinks=True)
    shutil.copytree(home / "notes", private / "memory-notes", symlinks=True)
    if state:
        shutil.copytree(state, private / "context-after", symlinks=True)
    result_dict = result.model_dump(mode="json")
    native = native_receipt(trial_dir / "agent" / "cc-output.txt", session)
    wire = wire_receipt(
        private / "wire", private / "chat-gateway", row, previous, arm,
        (stage_path / "instruction.md").read_text(),
    )
    receipt = {
        "arm": arm, "session": session, "row": row, "native": native, "wire": wire,
        "reward": (result_dict.get("verifier_result") or {}).get("rewards"),
        "exception": result_dict.get("exception_info"), "session_saved": session_saved,
    }
    receipt["accepted"] = bool(
        native["session_match"] and native["terminal"] and not native["terminal_error"]
        and wire["valid_current_task_responses"] and wire["official_instruction_exact"] and receipt["session_saved"]
        and receipt["reward"] and receipt["exception"] is None
        and (previous is None or wire["previous_marker_in_first_success"] or native["native_compactions"])
        and (not web or wire["successful_judge_responses"] > 0)
    )
    write_json(private / "receipt.json", receipt)
    print(json.dumps({**receipt, "wire": {k: v for k, v in wire.items() if k not in {"context_events", "provider_usage"}}}, ensure_ascii=False), flush=True)
    return receipt


async def run_matched(run, model, judge_model, judge_service, carry=None):
    plan = json.loads((run / "plan.json").read_text())
    sessions = carry["sessions"] if carry else {arm: str(uuid.uuid4()) for arm in ("native", "clm")}
    write_json(run / "sessions.json", {"sessions": sessions, "model": model, "judge_model": judge_model, "judge_service": judge_service})
    config = json.loads(Path("/mount-data/Tools/services.json").read_text())
    service = config["services"]["deepseek"]["base_url"]
    key = subprocess.check_output(
        ["/mount-data/Tools/skill-api", "_credential", "--service", "deepseek"], text=True
    ).strip()
    judge_key = subprocess.check_output(
        ["/mount-data/Tools/skill-api", "_credential", "--service", judge_service], text=True
    ).strip()
    context = carry["context"] if carry else Context(run / "clm" / "context")
    ready = carry["ready"] if carry else {}
    previous = None
    receipts = []
    for row in plan["tasks"]:
        pair = []
        for arm, session in sessions.items():
            if (row["position"], arm) in ready:
                pair.append(ready[row["position"], arm])
                continue
            if arm == "clm" and previous:
                old = f"{previous['position']:03d}-{previous['domain']}-{previous['task']}"
                current = f"{row['position']:03d}-{row['domain']}-{row['task']}"
                native = run / "clm" / "home" / "config" / "projects" / "-workspace" / f"{session}.jsonl"
                maintain(
                    context, run / "clm" / "evidence" / old, native,
                    run / "clm" / "maintenance" / current, service, key, model,
                )
            pair.append(await one_trial(
                run, row, previous, arm, session, service, key, model, judge_model,
                context if arm == "clm" else None, judge_key,
            ))
        receipts.extend(pair)
        write_json(run / "progress.json", {"completed_pairs": row["position"], "receipts": receipts})
        if not all(rec["accepted"] for rec in pair):
            raise RuntimeError(f"Pair {row['position']} failed acceptance; all evidence preserved")
        previous = row
    write_json(run / "accepted.json", {
        "stage": plan["stage"], "pairs": len(plan["tasks"]),
        "plan_sha256": sha(run / "plan.json"), "sessions": sessions,
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("prepare", "execute"))
    ap.add_argument("--experiment", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--stage", choices=("plumbing", "pilot", "formal"), required=True)
    ap.add_argument("--allowlist", type=Path)
    ap.add_argument("--pilot-ok", type=Path)
    ap.add_argument("--pilot-prebuilt", action="store_true")
    ap.add_argument("--model", default=CLI_MODEL)
    ap.add_argument("--judge-model", default=JUDGE_MODEL)
    ap.add_argument("--judge-service", choices=("claude", "gpt"), default="gpt")
    args = ap.parse_args()
    os.umask(0o077)
    if args.action == "prepare":
        args.run.mkdir(parents=True)
        plan = make_plan(args.experiment, args.stage, args.allowlist)
        write_json(args.run / "plan.json", plan)
        for row in plan["tasks"]:
            image = f"wb-clm-pilot-{row['domain']}:20261118" if args.pilot_prebuilt else None
            stage_task(args.experiment, args.run, row, image)
    else:
        plan = json.loads((args.run / "plan.json").read_text())
        if args.stage != plan["stage"]:
            raise ValueError("CLI stage and frozen plan differ")
        if (args.run / "sessions.json").exists():
            raise FileExistsError("Attempt exists. Its traces must be preserved.")
        if args.stage == "formal":
            if not args.pilot_ok:
                raise ValueError("An accepted four-category paired pilot is required")
            pilot = json.loads(args.pilot_ok.read_text())
            pilot_plan = args.pilot_ok.parent / "plan.json"
            pilot_run = json.loads((args.pilot_ok.parent / "sessions.json").read_text())
            if (
                pilot["stage"] != "pilot" or pilot["pairs"] != 4 or pilot["plan_sha256"] != sha(pilot_plan)
                or pilot_run["model"] != args.model or pilot_run["judge_model"] != args.judge_model
                or pilot_run["judge_service"] != args.judge_service
            ):
                raise ValueError("Pilot receipt does not match the formal configuration")
            if plan["chosen_totals"] != plan["declared_formal_quota"]:
                raise ValueError("Quarter-per-category formal scope is unresolved")
        asyncio.run(run_matched(args.run, args.model, args.judge_model, args.judge_service))


if __name__ == "__main__":
    main()
