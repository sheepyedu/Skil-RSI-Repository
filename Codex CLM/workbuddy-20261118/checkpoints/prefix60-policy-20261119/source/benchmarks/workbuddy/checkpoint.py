"""Capture a failed task's container state and rebuild CLM state from protected wire logs."""

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from clm.context import CALLS, candidates, digest, is_message, write_json
from relay import SeriesContext
from workbuddy_bench.runner.docker_environment import WorkBuddyDockerEnvironment


class CheckpointEnvironment(WorkBuddyDockerEnvironment):
    def __init__(self, *args, task_env_config, checkpoint_image=None, **kwargs):
        if checkpoint_image:
            task_env_config = task_env_config.model_copy(update={"docker_image": checkpoint_image})
        super().__init__(*args, task_env_config=task_env_config, **kwargs)


def docker(*arguments, timeout=120):
    return subprocess.check_output(["docker", *arguments], text=True, timeout=timeout).strip()


def capture_failed_task(trial_name, trial_dir, home, evidence, row):
    result_file = trial_dir / "agent/native-result.json"
    if not result_file.exists():
        return
    native = json.loads(result_file.read_text())
    if native.get("turn") or not native.get("thread"):
        return
    identifiers = docker(
        "ps", "-q", "--filter", f"name={trial_name}",
        "--filter", "label=com.docker.compose.service=main",
    ).splitlines()
    if len(identifiers) != 1:
        raise ValueError("Cannot uniquely identify this failed task's live container")
    identifier = identifiers[0]
    info = json.loads(docker("inspect", identifier))[0]
    mounts = {item["Destination"]: item["Source"] for item in info["Mounts"]}
    write_json(evidence / "checkpoint-mounts.json", {"expected_home": str(home), "mounts": mounts})
    # The PAI Docker proxy exposes host binds below its explicit /mainroot prefix.
    if mounts.get("/serial-home") == "/mainroot" + str(home):
        mounts = {target: source.removeprefix("/mainroot") for target, source in mounts.items()}
    if mounts.get("/serial-home") != str(home):
        raise ValueError("Checkpoint container does not belong to this arm's home")
    artifact_source = Path(mounts["/logs/artifacts"])
    if not artifact_source.resolve().is_relative_to(trial_dir.resolve()):
        raise ValueError("Task artifacts are outside this trial")
    directory = evidence / "checkpoint"
    directory.mkdir()
    image = f"wb-codex-checkpoint-{hashlib.sha256(str(evidence).encode()).hexdigest()[:16]}:{time.time_ns()}"
    services = {}
    if row.get("task") == "bb-bin-dns-parse-010":
        probe = '''import pathlib,subprocess,json
running=False
for p in pathlib.Path("/proc").glob("[0-9]*/comm"):
 try: running|=p.read_text().strip()=="named"
 except OSError: pass
try:
 result=subprocess.run(["dig","@127.0.0.1","-p","5353","www.corp.example","A","+short","+time=1","+tries=1"],capture_output=True,text=True,timeout=3)
 healthy=result.returncode==0 and bool(result.stdout.strip())
except subprocess.TimeoutExpired:
 healthy=False
print(json.dumps({"running":running,"healthy":healthy}))'''
        services["named"] = json.loads(docker("exec", identifier, "python3", "-c", probe))
    docker("pause", identifier)
    try:
        shutil.copytree(artifact_source, directory / "artifacts", symlinks=True)
        image_id = docker("commit", "--no-pause", "--change",
                          "LABEL com.docker.compose.project=workbuddy-codex-checkpoint",
                          "--change", "LABEL com.docker.compose.service=checkpoint", identifier, image)
    finally:
        docker("unpause", identifier)
    observed_id = docker("image", "inspect", "--format", "{{.Id}}", image)
    write_json(directory / "image-operation.json", {"image": image, "commit_output": image_id, "inspect_output": observed_id})
    if observed_id != image_id:
        raise ValueError("Checkpoint image ID verification failed")
    docker("save", "--output", str(directory / "image.tar"), image, timeout=600)
    with (directory / "image.tar").open("rb") as stream:
        archive_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    write_json(directory / "receipt.json", {
        "row": row, "thread": native["thread"], "image": image, "image_id": image_id,
        "artifacts": str(directory / "artifacts"), "container": identifier,
        "native_result": str(result_file), "captured_ns": time.time_ns(),
        "archive_sha256": archive_sha,
        "services": services,
    })


def restore_context(directory, arm_root):
    records = []
    for path in arm_root.rglob("wire/*/receipt.json"):
        event = json.loads(path.read_text())
        if event.get("clm"):
            records.append((event["clm"]["revision"], path, event))
    if not records:
        raise ValueError("No protected CLM request ledger to resume")
    revision, receipt_path, event = max(records, key=lambda value: value[0])
    raw = json.loads((receipt_path.parent / "request.raw.json").read_text())["input"]
    sent = json.loads((receipt_path.parent / "request.sent.json").read_text())["input"]
    if digest(raw) != event["clm"]["raw_input_sha256"] or digest(sent) != event["clm"]["upstream_input_sha256"]:
        raise ValueError("CLM request fingerprints differ from the protected ledger")
    anchor_index = next(i for i, item in enumerate(raw) if is_message(item, "user"))
    groups = candidates(raw, anchor_index)
    retained = {(item["type"], item["call_id"]) for item in sent if item.get("type") in CALLS}
    dropped = set()
    for key, (start, end) in groups.items():
        calls = [(item["type"], item["call_id"]) for item in raw[start:end] if item.get("type") in CALLS]
        present = [call in retained for call in calls]
        if not any(present):
            dropped.add(key)
        elif not all(present):
            raise ValueError("Projected history has only part of a tool-call batch")
    first_sent = next(item for item in sent if is_message(item, "user"))
    first_raw = raw[anchor_index]
    note = ""
    if first_sent != first_raw:
        old_content = first_raw["content"]
        if isinstance(old_content, str):
            old_content = [{"type": "input_text", "text": old_content}]
        content = first_sent["content"]
        if len(content) != len(old_content) + 1 or content[:-1] != old_content:
            raise ValueError("CLM changed protected first-user content")
        prefix = "CLM memory written by the assistant:\n"
        if content[-1].get("type") != "input_text" or not content[-1].get("text", "").startswith(prefix):
            raise ValueError("Unrecognized CLM note encoding")
        note = content[-1]["text"][len(prefix):]
    context = SeriesContext(directory)
    context.revision = revision
    context.anchor = digest(first_raw)
    context.note = note
    context.dropped = dropped
    context.visible = set(groups) - dropped
    write_json(directory / "RESTORED_FROM_WIRE.json", {
        "revision": revision, "source": str(receipt_path), "dropped": sorted(dropped),
        "note_sha256": hashlib.sha256(note.encode()).hexdigest(),
    })
    return context
