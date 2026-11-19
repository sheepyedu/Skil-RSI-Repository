"""Drive a native Codex app server for one task, resuming the arm's existing thread."""

import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path("/logs/agent")
CODEX = "/opt/codex/bin/codex"
LOCAL_TOKEN = "workbuddy-codex-local"


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


class Native:
    def __init__(self):
        self.seq = 0
        self.events = queue.Queue()
        self.trace = (ROOT / "native.jsonl").open("a", buffering=1)
        self.stderr = (ROOT / "native.stderr").open("ab")
        self.process = subprocess.Popen(
            [CODEX, "--no-daemon", "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True,
        )
        self.reader = threading.Thread(target=self.receive, daemon=True)
        self.reader.start()
        self.deadline = time.monotonic() + 3500

    def record(self, direction, data):
        self.trace.write(json.dumps({"direction": direction, "data": data, "time_ns": time.time_ns()},
                                    ensure_ascii=False) + "\n")

    def receive(self):
        try:
            for line in self.process.stdout:
                try:
                    self.events.put(json.loads(line))
                except json.JSONDecodeError:
                    self.events.put({"invalid_app_server_message": line})
        finally:
            self.events.put(None)

    def send(self, data):
        self.record("to_codex", data)
        self.process.stdin.write(json.dumps(data, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def event(self):
        try:
            data = self.events.get(timeout=max(0, self.deadline - time.monotonic()))
        except queue.Empty as exc:
            raise TimeoutError("Native app-server exceeded task deadline") from exc
        if data is None:
            raise EOFError(f"Native app-server exited {self.process.poll()}")
        self.record("from_codex", data)
        if "invalid_app_server_message" in data:
            raise ValueError("Native app-server emitted invalid JSON")
        if "id" in data and "method" in data:
            self.send({"id": data["id"], "error": {"code": -32601, "message": "Unsupported server request"}})
        return data

    def request(self, method, params):
        self.seq += 1
        self.send({"id": self.seq, "method": method, "params": params})
        while True:
            data = self.event()
            if data.get("id") == self.seq and "method" not in data:
                if "error" in data:
                    raise RuntimeError(f"{method}: {data['error']}")
                return data["result"]

    def complete(self, thread_id, turn_id=None, compacting=False):
        saw_compaction = False
        while True:
            data = self.event()
            params = data.get("params") or {}
            if params.get("threadId") != thread_id:
                continue
            if data.get("method") == "item/completed" and params["item"]["type"] == "contextCompaction":
                saw_compaction = True
            if data.get("method") == "thread/compacted":
                saw_compaction = True
            if data.get("method") == "turn/completed":
                turn = params["turn"]
                if turn_id is not None and turn["id"] != turn_id:
                    raise ValueError("Unexpected Codex turn completion")
                if turn["status"] != "completed":
                    raise RuntimeError(f"Native turn {turn['status']}: {turn.get('error')}")
                if compacting and not saw_compaction:
                    raise RuntimeError("Native compaction produced no compaction receipt")
                return {"turn": turn["id"], "saw_compaction": saw_compaction}

    def close(self):
        self.process.stdin.close()
        try:
            code = self.process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            code = self.process.wait(timeout=10)
        self.reader.join(2)
        # Save late lifecycle notifications as well.
        while not self.events.empty():
            data = self.events.get_nowait()
            if data is not None:
                self.record("from_codex", data)
        self.trace.close()
        self.stderr.close()
        return code


def configure(opts):
    target = Path(os.environ["CODEX_HOME"])
    target.mkdir(exist_ok=True)
    text = '''
model = "gpt-6.1-sol"
model_provider = "workbuddy"
model_reasoning_effort = "low"
approval_policy = "never"
sandbox_mode = "danger-full-access"
check_for_update_on_startup = false
'''
    if opts["arm"] == "clm":
        instructions = (
            "You are in a continuing benchmark session. Use the clm-context tool to manage context. "
            "Run clm-context status to view editable completed tool exchanges and "
            "clm-context show ID to inspect one. Submit clm-context edit --drop ID [ID ...] "
            "--note 'short reusable memory' when old tool exchanges are no longer needed. "
            "Use clm-context status after applying an edit to check acceptance. "
            "Keep only reusable knowledge in /serial-home/notes and use exact source files as needed. "
            "The active task and its instructions remain authoritative."
        )
        text += "developer_instructions = " + json.dumps(instructions) + "\n"
    text += '''
[features]
multi_agent_v2 = false
web_search = false

[agents]
enabled = false

[model_providers.workbuddy]
name = "WorkBuddy GPT"
base_url = "http://127.0.0.1:19731/v1"
env_key = "CODEX_WORKBUDDY_TOKEN"
wire_api = "responses"
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
stream_idle_timeout_ms = 930000
'''
    (target / "config.toml").write_text(text)


def run(opts, instruction):
    configure(opts)
    native = Native()
    records = {}
    try:
        native.request("initialize", {"clientInfo": {"name": "workbuddy_codex", "version": "1.0"},
                                      "capabilities": {"experimentalApi": True}})
        native.send({"method": "initialized"})
        cwd = os.getcwd()
        params = {"cwd": cwd, "persistExtendedHistory": True}
        thread_id = opts["thread"]
        if thread_id:
            result = native.request("thread/resume", {**params, "threadId": thread_id, "excludeTurns": True})
        else:
            result = native.request("thread/start", params)
        thread = result["thread"]
        if thread_id and thread_id != thread["id"]:
            raise RuntimeError("Codex resumed a different thread")
        thread_id = thread["id"]
        if not re.fullmatch(r"[0-9a-f-]{36}", thread_id):
            raise ValueError("Invalid native thread ID")
        records.update(thread=thread_id, resumed=bool(opts["thread"]), workdir=cwd, rollout_path=thread.get("path"))
        write(ROOT / "native-start.json", records)
        if opts["compact"]:
            native.request("thread/compact/start", {"threadId": thread_id})
            records["protective_compaction"] = native.complete(thread_id, compacting=True)
        prompt = (
            f"[{opts['marker']}] This turn is a new WorkBuddy Benchmark task. "
            f"Use the fresh official task files in {cwd}, follow the task's output paths, "
            "and use earlier conversation and /serial-home/notes for applicable reusable knowledge.\n\n"
            + instruction
        )
        (ROOT / "prompt-model.txt").write_text(prompt)
        started = native.request("turn/start", {"threadId": thread_id,
                                                 "input": [{"type": "text", "text": prompt}]})
        records.update(native.complete(thread_id, started["turn"]["id"]))
    finally:
        records["native_exit"] = native.close()
        write(ROOT / "native-result.json", records)
    if records["native_exit"]:
        raise RuntimeError(f"Native app-server exit {records['native_exit']}")


if __name__ == "__main__":
    os.environ["CODEX_WORKBUDDY_TOKEN"] = LOCAL_TOKEN
    with open(sys.argv[1], encoding="utf-8") as options:
        opts = json.load(options)
    run(opts, Path(sys.argv[2]).read_bytes().decode("utf-8"))
