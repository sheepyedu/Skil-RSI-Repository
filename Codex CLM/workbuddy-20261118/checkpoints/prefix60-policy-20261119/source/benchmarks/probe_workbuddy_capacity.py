"""Exercise native compaction and continuation on an isolated copy of the CLM pilot."""

import argparse
import json
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from clm.context import digest, is_message
from relay import SeriesContext, Wire
from run import HERE, RUNTIME, provider, read, sha, response_record


DRIVER = """
set -eu
export HOME=/serial-home CODEX_HOME=/serial-home/codex CLM_CONTEXT_DIR=/context
python3 /opt/workbuddy/loopback.py >/logs/agent/relay.out 2>&1 &
relay=$!
trap 'kill "$relay" 2>/dev/null || true' EXIT
for i in {1..50}; do test -f /tmp/workbuddy-relay-ready && break; sleep 0.1; done
test -f /tmp/workbuddy-relay-ready
python3 /opt/workbuddy/native_turn.py /probe/options.json /probe/prompt.txt
"""


def main():
    args = argparse.ArgumentParser()
    args.add_argument("pilot", type=Path)
    args.add_argument("output", type=Path)
    args.add_argument("--verified-prefix", action="store_true")
    opt = args.parse_args()
    plan = read(opt.pilot / "plan.json")
    if opt.verified_prefix:
        prefix = read(opt.pilot / "progress.json")
        completed = [r for r in prefix if r["arm"] == "clm" and r["accepted"]]
        if len(completed) < 3 or len({r["thread"] for r in completed}) != 1:
            raise ValueError("Capacity probe requires three verified CLM turns")
        thread = completed[-1]["thread"]
    else:
        accepted = read(opt.pilot / "accepted.json")
        if accepted["stage"] != "pilot" or accepted["pairs"] != 4:
            raise ValueError("Capacity probe requires a completed four-category pilot")
        thread = accepted["threads"]["clm"]
    source_home = opt.pilot / "clm" / "home"
    pilot_sessions = list((source_home / "codex" / "sessions").rglob(f"*{thread}.jsonl"))
    if len(pilot_sessions) != 1:
        raise ValueError("Cannot identify uniquely the completed CLM thread")
    original_sha = sha(pilot_sessions[0])
    target = opt.output.resolve()
    target.mkdir(mode=0o700, parents=True)
    home = target / "home"
    shutil.copytree(source_home, home, symlinks=True)
    state = target / "context"
    state.mkdir()
    context = SeriesContext(state)
    memory = "workbuddy-compaction-receipt-" + thread[-8:]
    context.note = f"The capacity probe verification phrase is {memory}."
    # Preserve the test note when the first real user message becomes the anchor.
    raw_inputs = sorted((opt.pilot / "clm" / "evidence").glob("*/wire/*/request.raw.json"), reverse=True)
    for source in raw_inputs:
        user = next((item for item in read(source).get("input", []) if is_message(item, "user")), None)
        if user is not None:
            context.anchor = digest(user)
            break
    if context.anchor is None:
        raise ValueError("Pilot has no visible Responses user message")
    (target / "options.json").write_text(json.dumps({"arm": "clm", "thread": thread,
                                                     "marker": "WB_CODEX_CAPACITY_PROBE", "compact": True}))
    (target / "prompt.txt").write_text("This is an engineering control, not a scored WorkBuddy task. "
                                      "Return only the capacity probe verification phrase from your CLM memory.")
    (target / "driver.sh").write_text(DRIVER)
    (target / "logs").mkdir()
    (target / "wire").mkdir()
    key, base = provider()
    with tempfile.TemporaryDirectory(prefix="wb-capacity-") as temp:
        socket = Path(temp) / "responses.sock"
        with Wire(socket, target / "wire", base, key, context) as gateway:
            bridge = threading.Thread(target=gateway.serve_forever, daemon=True)
            bridge.start()
            mounts = {
                RUNTIME: "/opt/codex",
                HERE / "native_turn.py": "/opt/workbuddy/native_turn.py",
                HERE / "loopback.py": "/opt/workbuddy/loopback.py",
                HERE.parent.parent / "clm" / "container_entry.py": "/opt/codex-clm/clm/container_entry.py",
                HERE.parent.parent / "clm" / "edit.py": "/opt/codex-clm/clm/edit.py",
                HERE.parent.parent / "clm" / "context.py": "/opt/codex-clm/clm/context.py",
                HERE / "tools" / "clm-context": "/usr/local/bin/clm-context",
                socket: "/gateway/responses.sock",
                home: "/serial-home",
                state: "/context",
                target / "logs": "/logs/agent",
                target / "options.json": "/probe/options.json",
                target / "prompt.txt": "/probe/prompt.txt",
                target / "driver.sh": "/probe/driver.sh",
            }
            options = []
            for source, path in mounts.items():
                rw = source in {home, state, target / "logs"}
                options += ["--mount", f"type=bind,src={source},dst={path}" + ("" if rw else ",readonly")]
            try:
                with (target / "docker.log").open("wb") as log:
                    result = subprocess.run([
                        "docker", "run", "--name", f"wbc-capacity-{thread[-8:]}", "--rm", "--network=none",
                        "--user", "0:0", "--workdir", "/workspace", *options, "--entrypoint", "/bin/bash",
                        plan["tasks"][0]["image"], "/probe/driver.sh",
                    ], stdout=log, stderr=subprocess.STDOUT, timeout=1800)
            finally:
                gateway.shutdown()
                bridge.join()
    native = target / "logs" / "native-result.json"
    events = target / "logs" / "native.jsonl"
    output = []
    if events.exists():
        for line in events.open():
            event = json.loads(line)["data"]
            if event.get("method") == "item/completed":
                item = event["params"]["item"]
                if item["type"] == "agentMessage":
                    output.append(item.get("text", ""))
    native_result = read(native) if native.exists() else {}
    calls = [response_record(path) for path in sorted((target / "wire").iterdir())]
    proof = {
        "pilot_thread": thread, "docker_exit": result.returncode, "native": native_result,
        "original_thread_unchanged": sha(pilot_sessions[0]) == original_sha,
        "verified_note_recalled": any(memory in item for item in output),
        "requests": calls,
    }
    proof["accepted"] = bool(
        not result.returncode and native_result.get("protective_compaction") and native_result.get("turn")
        and native_result.get("thread") == thread and proof["original_thread_unchanged"]
        and proof["verified_note_recalled"] and sum(bool(call.get("complete")) for call in calls) >= 2
    )
    (target / "result.json").write_text(json.dumps(proof, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in proof.items() if k != "requests"}, ensure_ascii=False), flush=True)
    raise SystemExit(0 if proof["accepted"] else 1)


if __name__ == "__main__":
    main()
