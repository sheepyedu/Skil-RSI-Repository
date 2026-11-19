"""Paired, serial WorkBuddy eval using one native Codex thread per arm."""

import argparse
import asyncio
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import tomllib
from pathlib import Path

from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig, VerifierConfig
from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial

from relay import COMPACT_BYTES, COMPACT_TOKENS, MODEL, SeriesContext, Wire, stream_outcome
from checkpoint import capture_failed_task
from clm.context import write_json

HERE = Path(__file__).resolve().parent
REF = Path("/mount-data/Claude-code-CLM/experiments/workbuddy-20261118")
RUNTIME = Path("/mount-data/Codex-CLM/runtime/codex-0.169.0/x86_64-unknown-linux-musl")
ARMS = ("native", "clm")
REFERENCE_STAGES = {"pilot": "pilot-08", "formal": "formal-02"}
SOURCE_TOTALS = {"code": 80, "office": 50, "sec": 60, "web": 70}
COUNTS = {"pilot": dict.fromkeys(SOURCE_TOTALS, 1),
          "formal": {"code": 20, "office": 12, "sec": 10, "web": 18}}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as fd:
        return hashlib.file_digest(fd, "sha256").hexdigest()


def task_dir(root, row):
    return root / "datasets" / f"wb-bench-{row['domain']}-v1.0" / "tasks" / row["task"]


def image_id(ref):
    return subprocess.check_output(["docker", "image", "inspect", "--format", "{{.Id}}", ref],
                                   text=True).strip()


def runtime_sha():
    return {name: sha(RUNTIME / name) for name in ("bin/codex", "bin/codex-code-mode-host", "codex-path/rg")}


def plan(stage, target):
    reference = REF / REFERENCE_STAGES[stage]
    original = read(reference / "plan.json")
    if original["source_totals"] != SOURCE_TOTALS:
        raise ValueError("Unexpected official dataset counts")
    observed = collections.Counter(row["domain"] for row in original["tasks"])
    if observed != COUNTS[stage]:
        raise ValueError(f"Unexpected {stage} task selection {observed}")
    pilot_keys = {(r["domain"], r["task"]) for r in read(REF / "pilot-08" / "plan.json")["tasks"]}
    seen = set()
    images_by_task = []
    for i, row in enumerate(original["tasks"], 1):
        key = row["domain"], row["task"]
        if key in seen or (stage == "formal" and key in pilot_keys) or row["position"] != i:
            raise ValueError("Plan has duplicate, out-of-order, or pilot-overlapping cases")
        seen.add(key)
        official = task_dir(REF / "upstream", row)
        staged = task_dir(reference, row)
        for directory in (official, staged):
            if sha(directory / "instruction.md") != row["instruction_sha256"]:
                raise ValueError("Official task instruction hash mismatch")
            if sha(directory / "environment" / "Dockerfile") != row["dockerfile_sha256"]:
                # The prior frozen environment may legitimately patch package mirrors.
                if directory == official:
                    raise ValueError("Official task Dockerfile hash mismatch")
        with (staged / "task.toml").open("rb") as fd:
            image = tomllib.load(fd)["environment"]["docker_image"]
        row["marker"] = f"WB_CODEX_{stage.upper()}_{i:03d}"
        row["image"] = image
        row["image_id"] = image_id(image)
        row["staged_task_config_sha256"] = sha(staged / "task.toml")
        images_by_task.append(row)
    target.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copy2(reference / "offline.yaml", target / "offline.yaml")
    write_json(target / "plan.json", {
        "stage": stage, "reference": str(reference), "reference_plan_sha256": sha(reference / "plan.json"),
        "runtime_sha256": runtime_sha(), "model": MODEL, "source_totals": SOURCE_TOTALS,
        "chosen_totals": COUNTS[stage], "tasks": images_by_task,
        "security_scope": "Previously vetted offline defensive tasks only",
        "code_sha256": code_sha(),
    })


def code_sha():
    files = sorted(HERE.glob("*.py")) + [HERE / "tools" / "clm-context", HERE.parent.parent / "clm" / "context.py"]
    return {path.name: sha(path) for path in files}


def bind(path, target, readonly=True):
    mount = {"type": "bind", "source": str(path), "target": target,
             "bind": {"create_host_path": False}}
    if readonly:
        mount["read_only"] = True
    return mount


def response_record(directory):
    result = read(directory / "receipt.json")
    body = directory / "response.raw"
    if not body.exists() or result.get("status") != 200 or not result.get("eof"):
        return result
    raw = body.read_bytes()
    usage = None
    if result["path"] == "/v1/chat/completions" and raw.lstrip().startswith((b"data:", b"event:")):
        result["complete"] = stream_outcome(body, chat=True)[0] == "chat.done"
        for line in raw.splitlines():
            if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
                continue
            try:
                event = json.loads(line[5:])
            except (ValueError, UnicodeError):
                continue
            usage = event.get("usage") or usage
    elif result["path"] != "/v1/responses":
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError):
            return result
        result["complete"] = bool(data.get("choices") or data.get("output"))
        usage = data.get("usage")
    else:
        for line in raw.splitlines():
            if not line.startswith(b"data: "):
                continue
            try:
                event = json.loads(line[6:])
            except (ValueError, UnicodeError):
                continue
            if event.get("type") == "response.completed":
                response = event.get("response") or {}
                usage = response.get("usage")
                result["complete"] = True
    if usage:
        result["usage"] = usage
    return result


def message_text(item):
    content = item.get("content", [])
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content if isinstance(part, dict))


def user_text(path):
    for item in read(path).get("input", []):
        if item.get("role") == "user":
            yield message_text(item)


def wire_report(root, row, prompt, previous_marker, control):
    records = []
    prompt_hits = 0
    previous_hits = 0
    tools = set()
    missing_tool_hosts = set()
    for directory in sorted(root.iterdir()):
        if not (directory / "receipt.json").exists():
            continue
        record = response_record(directory)
        records.append(record)
        if not record.get("complete") or record["path"] != "/v1/responses":
            continue
        raw = directory / "request.raw.json"
        sent = directory / "request.sent.json"
        if control and record["sent_sha256"] != record["raw_sha256"]:
            raise ValueError("Native request bytes changed during relay")
        raw_texts, sent_texts = list(user_text(raw)), list(user_text(sent))
        if any(x.startswith(f"[{row['marker']}]") and prompt.rstrip("\n") in x for x in raw_texts):
            if not any(x.startswith(f"[{row['marker']}]") and prompt.rstrip("\n") in x for x in sent_texts):
                raise ValueError("CLM removed or changed the current official task")
            prompt_hits += 1
            previous_hits += bool(previous_marker and any(previous_marker in x for x in sent_texts))
            items = read(raw)["input"]
            first_current_user = next(
                i for i, item in enumerate(items)
                if item.get("role") == "user" and message_text(item).startswith(f"[{row['marker']}]")
            )
            for item in items[first_current_user + 1:]:
                if item.get("type") not in ("function_call_output", "custom_tool_call_output"):
                    continue
                output = item.get("output")
                if isinstance(output, str) and "failed to spawn code-mode host" in output:
                    missing_tool_hosts.add(item.get("call_id"))
                else:
                    tools.add(item.get("call_id"))
    inputs = [r.get("usage", {}).get("input_tokens", 0) or 0 for r in records]
    return {
        "requests": len(records),
        "responses_with_exact_task": prompt_hits,
        "responses_with_previous_marker": previous_hits,
        "tool_outputs": len(tools),
        "missing_tool_host_outputs": len(missing_tool_hosts),
        "successful_judge_calls": sum(r["path"] == "/v1/chat/completions" and bool(r.get("complete")) for r in records),
        "accepted_edits": sum(r.get("clm", {}).get("edit") == "accepted" for r in records),
        "max_raw_input_bytes": max((r.get("raw_input_bytes", 0) for r in records), default=0),
        "max_sent_input_bytes": max((r.get("sent_input_bytes", 0) for r in records), default=0),
        "final_raw_input_bytes": next((r["raw_input_bytes"] for r in reversed(records)
                                      if r.get("raw_input_bytes") and r.get("complete")), 0),
        "peak_input_tokens": max(inputs, default=0),
        "last_input_tokens": next((r["usage"]["input_tokens"] for r in reversed(records)
                                  if r.get("usage", {}).get("input_tokens") is not None), 0),
        "usage": [r["usage"] for r in records if r["path"] == "/v1/responses" and "usage" in r],
        "records": records,
    }


def save_thread(home, thread, private):
    if not thread or not re.fullmatch(r"[0-9a-f-]{36}", thread):
        return None
    matches = [p for p in (home / "codex" / "sessions").rglob(f"*{thread}.jsonl")
               if p.is_file() and not p.is_symlink()]
    if len(matches) != 1:
        return None
    target = private / "native-session.jsonl"
    shutil.copy2(matches[0], target, follow_symlinks=False)
    return sha(target)


async def one_trial(root, frozen, row, arm, previous, key, base_url, context, recovery=None, attempt=1):
    ordinal = row["position"]
    task = task_dir(Path(frozen["reference"]), row)
    if (sha(task / "instruction.md") != row["instruction_sha256"]
            or sha(task / "task.toml") != row["staged_task_config_sha256"]
            or image_id(row["image"]) != row["image_id"]):
        raise ValueError("Upstream task or pinned image drift")
    name = f"{ordinal:03d}-{row['domain']}-{row['task']}"
    prefix = hashlib.sha256(str(root).encode()).hexdigest()[:10]
    trial_name = f"wbc-{prefix}-{arm}-{ordinal:03d}"
    if attempt > 1:
        trial_name += f"-r{attempt:02d}"
    arm_root = root / arm
    private = arm_root / "evidence" / name
    private.mkdir(mode=0o700, parents=True)
    (private / "wire").mkdir()
    home = arm_root / "home"
    home.mkdir(mode=0o700, exist_ok=True)
    if context:
        if context.directory.exists():
            shutil.copytree(context.directory, private / "context-before")
        context.directory.mkdir(mode=0o700, exist_ok=True)
    web = row["domain"] == "web"
    old = previous or {}
    pressure = old.get("wire", {})
    compact = bool(context and (pressure.get("final_raw_input_bytes", 0) >= COMPACT_BYTES
                                or pressure.get("last_input_tokens", 0) >= COMPACT_TOKENS))
    options = {"thread": old.get("thread"), "marker": row["marker"], "arm": arm,
               "instruction": str(task / "instruction.md"), "compact": compact}
    if row["domain"] == "sec" and row["task"] == "bb-bin-dns-parse-010":
        options["init_named"] = True
    checkpoint_image = None
    if recovery and recovery.get("checkpoint"):
        saved = recovery["checkpoint"]
        if saved["row"] != row or saved["thread"] != old.get("thread"):
            raise ValueError("Task checkpoint does not match the resumed row and thread")
        archive = Path(saved["archive"])
        if sha(archive) != saved["archive_sha256"]:
            raise ValueError("Task checkpoint archive changed")
        subprocess.run(["docker", "load", "--input", str(archive)], check=True,
                       stdout=subprocess.DEVNULL, timeout=600)
        if image_id(saved["image"]) != saved["image_id"]:
            raise ValueError("Task checkpoint image changed")
        checkpoint_image = saved["image"]
        options["restore_artifacts"] = True
        if options.get("init_named"):
            options["named_restored"] = saved["services"]["named"]
    if recovery and recovery.get("patch_directory"):
        options["restore_patch"] = True
    write_json(private / "intent.json", {"row": row, **options})
    with tempfile.TemporaryDirectory(prefix="wb-codex-") as tmp:
        socket = Path(tmp) / "responses.sock"
        with Wire(socket, private / "wire", base_url, key, context) as gateway:
            mounts = [
                bind(RUNTIME, "/opt/codex"),
                bind(HERE / "native_turn.py", "/opt/workbuddy/native_turn.py"),
                bind(HERE / "loopback.py", "/opt/workbuddy/loopback.py"),
                bind(HERE.parent.parent / "clm" / "container_entry.py", "/opt/codex-clm/clm/container_entry.py"),
                bind(socket, "/gateway/responses.sock"), bind(home, "/serial-home", False),
            ]
            if context:
                mounts.extend([
                    bind(HERE.parent.parent / "clm" / "context.py", "/opt/codex-clm/clm/context.py"),
                    bind(HERE.parent.parent / "clm" / "edit.py", "/opt/codex-clm/clm/edit.py"),
                    bind(HERE / "tools" / "clm-context", "/usr/local/bin/clm-context"),
                    bind(context.directory, "/context", False),
                ])
            if options.get("restore_patch"):
                mounts.extend([
                    bind(Path(recovery["patch_directory"]), "/recovery"),
                    bind(HERE / "restore_state.py", "/opt/workbuddy/restore_state.py"),
                ])
            if options.get("restore_artifacts"):
                mounts.append(bind(Path(recovery["checkpoint"]["artifacts"]), "/recovery-artifacts"))
            judge_env = {
                "WEB_BENCH_LLM_JUDGE_MODE": "full",
                "WEB_BENCH_LLM_TIMEOUT_SEC": "1200",
                "WORKBUDDY_VERIFIER_LLM_BASE_URL": "http://127.0.0.1:19731/v1",
                "WORKBUDDY_VERIFIER_LLM_API_KEY": gateway.judge_token,
                "WORKBUDDY_VERIFIER_LLM_MODEL": MODEL,
            } if web else {}
            trial = await Trial.create(TrialConfig(
                task=TaskConfig(path=task), trial_name=trial_name, trials_dir=arm_root / "trials",
                agent=AgentConfig(import_path="agent:SerialCodex", model_name=MODEL, kwargs={"options": options}),
                environment=EnvironmentConfig(
                    import_path="checkpoint:CheckpointEnvironment",
                    kwargs={"checkpoint_image": checkpoint_image},
                    mounts=mounts, extra_docker_compose=[root / "offline.yaml"],
                ),
                verifier=VerifierConfig(import_path=None if row["domain"] == "sec" else "workbuddy_bench.judge:CompositeVerifier",
                                        env=judge_env),
                artifacts={
                    "office": [{"source": "/workspace/output", "destination": "office-output"}],
                    "web": [{"source": "/workspace/submission", "destination": "web-submission"}],
                }.get(row["domain"], []),
            ))

            async def hook(event):
                with (private / "timeline.jsonl").open("a") as log:
                    log.write(json.dumps({"event": event.event.value, "time": event.timestamp.isoformat()}) + "\n")
                if web and event.event == TrialEvent.VERIFICATION_START:
                    gateway.judge_enabled = True
                if event.event == TrialEvent.AGENT_END:
                    try:
                        await asyncio.to_thread(
                            capture_failed_task, trial_name, trial_root_path, home, private, row,
                        )
                    except Exception as error:
                        write_json(private / "checkpoint-error.json", {
                            "type": type(error).__name__, "message": str(error),
                        })
                if event.event in (TrialEvent.CANCEL, TrialEvent.END):
                    gateway.judge_enabled = False

            trial_root_path = arm_root / "trials" / trial_name
            for event_type in TrialEvent:
                trial.add_hook(event_type, hook)
            thread = threading.Thread(target=gateway.serve_forever, daemon=True)
            thread.start()
            try:
                result = (await trial.run()).model_dump(mode="json")
            finally:
                await asyncio.to_thread(gateway.shutdown)
                thread.join()

    logs = arm_root / "trials" / trial_name / "agent"
    status_path = logs / "native-result.json"
    native = read(status_path) if status_path.exists() else {}
    if not native and (logs / "native-start.json").exists():
        native = read(logs / "native-start.json")
    session_hash = save_thread(home, native.get("thread"), private)
    if context:
        shutil.copytree(context.directory, private / "context-after")
    shutil.copytree(home / "notes", private / "notes", symlinks=True, dirs_exist_ok=True)
    wire = wire_report(private / "wire", row, (task / "instruction.md").read_text(), old.get("marker"), arm == "native")
    receipt = {"row": row, "arm": arm, "trial_name": trial_name, "thread": native.get("thread"),
               "marker": row["marker"], "native": native,
               "session_sha256": session_hash, "wire": wire, "exception": result.get("exception_info"),
               "reward": (result.get("verifier_result") or {}).get("rewards")}
    if recovery:
        receipt["recovery"] = recovery
    state_proof = logs / "restored-state.json"
    if state_proof.exists():
        receipt["restored_state"] = read(state_proof)
    receipt["accepted"] = bool(
        native.get("turn") and native.get("native_exit") == 0 and session_hash and native.get("resumed") == bool(old)
        and (not old or old["thread"] == native["thread"]) and (not compact or native.get("protective_compaction"))
        and wire["responses_with_exact_task"] and wire["tool_outputs"] and not wire["missing_tool_host_outputs"]
        and (not web or wire["successful_judge_calls"])
        and result.get("exception_info") is None and receipt["reward"]
    )
    write_json(private / "receipt.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "wire"}, ensure_ascii=False), flush=True)
    return receipt


def provider():
    tools = Path("/mount-data/Tools")
    services = read(tools / "services.json")["services"]
    key = subprocess.check_output([str(tools / "skill-api"), "_credential", "--service", "gpt"], text=True).strip()
    return key, services["gpt"]["base_url"]


async def execute(root, gate, stop_after):
    frozen = read(root / "plan.json")
    if frozen["runtime_sha256"] != runtime_sha() or frozen["code_sha256"] != code_sha():
        raise ValueError("Frozen Codex or WorkBuddy controller code changed")
    if frozen["stage"] == "formal":
        proof = read(gate / "accepted.json")
        if (proof.get("pairs") != 4 or proof.get("stage") != "pilot"
                or proof["code_sha256"] != frozen["code_sha256"]
                or proof["runtime_sha256"] != frozen["runtime_sha256"]):
            raise ValueError("The current formal configuration requires a successful four-category pilot")
    key, base = provider()
    context = SeriesContext(root / "clm" / "context")
    previous = {}
    progress = []
    for row in frozen["tasks"]:
        for arm in ARMS:
            print(f"START {row['position']:03d} {row['domain']} {arm} {row['task']}", flush=True)
            receipt = await one_trial(root, frozen, row, arm, previous.get(arm), key, base,
                                      context if arm == "clm" else None)
            progress.append({k: v for k, v in receipt.items() if k != "wire"})
            write_json(root / "progress.json", progress)
            if not receipt["accepted"]:
                raise RuntimeError(f"Stopped at {row['position']} {arm}; raw failed attempt retained")
            previous[arm] = receipt
        if stop_after and row["position"] >= stop_after:
            return
    write_json(root / "accepted.json", {
        "pairs": len(frozen["tasks"]), "stage": frozen["stage"], "code_sha256": frozen["code_sha256"],
        "runtime_sha256": frozen["runtime_sha256"], "plan_sha256": sha(root / "plan.json"),
        "threads": {name: receipt["thread"] for name, receipt in previous.items()},
    })


def main():
    parser = argparse.ArgumentParser()
    cmd = parser.add_subparsers(dest="command", required=True)
    p = cmd.add_parser("prepare")
    p.add_argument("stage", choices=REFERENCE_STAGES)
    p.add_argument("root", type=Path)
    p = cmd.add_parser("run")
    p.add_argument("root", type=Path)
    p.add_argument("--pilot-gate", type=Path)
    p.add_argument("--stop-after", type=int)
    args = parser.parse_args()
    if args.command == "prepare":
        plan(args.stage, args.root.resolve())
    else:
        if (args.root / "progress.json").exists():
            raise ValueError("An existing run must be recovered from its preserved state")
        asyncio.run(execute(args.root.resolve(), args.pilot_gate, args.stop_after))


if __name__ == "__main__":
    main()
