"""Release an isolated stale grep pipeline after an observed successful CLI result."""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


CONTAINER_CHECK = r"""
import os, signal
from pathlib import Path

processes = {}
for folder in Path('/proc').glob('[0-9]*'):
    try:
        status = (folder / 'stat').read_text().rsplit(')', 1)[-1].split()
        name = (folder / 'comm').read_text().strip()
        args = (folder / 'cmdline').read_bytes().split(b'\0')
        processes[int(folder.name)] = (name, int(status[1]), args)
    except (OSError, ValueError, IndexError):
        continue

candidates = []
for pid, (name, parent, args) in processes.items():
    if name != 'grep' or b'-R' not in args or b'/' not in args:
        continue
    bash, claude, _ = processes.get(parent, (None, None, ()))
    agent, _, _ = processes.get(claude, (None, None, ()))
    siblings = [cid for cid, (kind, parent_id, _) in processes.items() if parent_id == parent and kind == 'head']
    if bash != 'bash' or agent != 'claude' or len(siblings) != 1:
        continue
    fd = Path(f'/proc/{parent}/fd/1')
    try:
        log = os.readlink(fd)
        owned = Path(f'/proc/{pid}').stat().st_uid == os.getuid()
    except OSError:
        continue
    if owned and log.startswith('/tmp/claude-') and '/tasks/' in log and log.endswith('.output'):
        candidates.append(pid)

if len(candidates) != 1:
    raise SystemExit('No uniquely verified stale recursive grep')
os.kill(candidates[0], signal.SIGTERM)
"""


def read(path):
    return json.loads(path.read_bytes())


def release(run, position, arm):
    row = read(run / "plan.json")["tasks"][position - 1]
    tag = f"{position:03d}-{row['domain']}-{row['task']}"
    evidence = run / arm / "evidence" / tag
    output = run / arm / "trials" / tag / "agent" / "cc-output.txt"
    audit = evidence / "residual-tool-cleanup.json"
    if (run / "exit-status.txt").is_file() or (evidence / "receipt.json").is_file() or audit.exists():
        raise ValueError("The task is no longer eligible for in-place process cleanup")
    if time.time() - output.stat().st_mtime < 120:
        raise ValueError("Wait for a confirmed stale interval after the CLI terminal event")
    raw = output.read_bytes()
    expected_session = read(run / "sessions.json")["sessions"][arm]
    results = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "result":
            results.append((event.get("subtype"), event.get("is_error"), event.get("session_id")))
    if results != [("success", False, expected_session)]:
        raise ValueError("Expected one successful saved terminal event for this session")
    attempts = sorted((evidence / "chat-gateway").glob("*/intent.json"))
    if not attempts or any(not read(p.with_name("receipt.json"))["complete"] for p in attempts):
        raise ValueError("All upstream requests must have closed successfully")
    label = tag + "__env"
    ids = subprocess.check_output(
        ["docker", "ps", "--filter", f"label=com.docker.compose.project={label}", "--format", "{{.ID}}"],
        text=True,
    ).splitlines()
    if len(ids) != 1:
        raise ValueError("The expected benchmark environment is not unique")
    if output.read_bytes() != raw:
        raise ValueError("The CLI resumed work while checking the container")
    subprocess.run(
        ["docker", "exec", "-u", "dev", ids[0], "python3", "-c", CONTAINER_CHECK],
        check=True, timeout=10,
    )
    record = {
        "observed_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds"),
        "run": run.name, "position": position, "arm": arm, "project": label,
        "complete_model_requests_before_intervention": len(attempts),
        "cli_stream_sha256_at_intervention": hashlib.sha256(raw).hexdigest(),
        "ready_result_type": "success", "process_signal": "SIGTERM",
        "process_target": "one confirmed recursive grep under the trial Claude Code process",
    }
    text = json.dumps(record, indent=2) + "\n"
    audit.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("position", type=int)
    parser.add_argument("arm", choices=("native", "clm"))
    args = parser.parse_args()
    release(args.run, args.position, args.arm)
