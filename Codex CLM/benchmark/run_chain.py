"""Drive one native Codex app-server thread over the frozen CL-Bench sequence."""
import collections
import hashlib
import json
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from skillrl.clbench import CLBenchTask, capture_workspace, docker
from skillrl.interactive import TaskBroker
from skillrl.storage import atomic

ROOT = Path(__file__).resolve().parent
REPOSITORY = Path("/mount-data/Datasets/continual-learning-bench/repository")
SHA = "2cfc987dacf1a2810e34a8e72a006cbe06b978d2099f53908833aa7a3e9a471e"
TOOLS = [
    {"type": "function", "name": "benchmark_status", "description": "Read current official task query and action schema.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"type": "function", "name": "benchmark_act", "description": "Apply one action in the current official task. Supply its action object in the shape from benchmark_status.",
     "inputSchema": {"type": "object", "properties": {"action": {"type": "object", "additionalProperties": True}},
                     "required": ["action"], "additionalProperties": False}},
]


class Native:
    def __init__(self):
        self.next_id = 0
        self.pending = queue.Queue()
        self.stderr = (ROOT / "native.stderr").open("wb")
        self.last_usage = None
        self.log = (ROOT / "native.jsonl").open("a", buffering=1)
        self.process = subprocess.Popen(
            [str(ROOT / "bin/codex-clm"), "--", "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr, text=True,
        )
        self.reader = threading.Thread(target=self.receive, daemon=True)
        self.reader.start()

    def receive(self):
        try:
            for line in self.process.stdout:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    item = {"transport_error": line.rstrip()}
                self.pending.put(item)
        finally:
            self.pending.put(None)

    def record(self, direction, item):
        self.log.write(json.dumps({"time": time.time(), "direction": direction, "data": item}, ensure_ascii=False) + "\n")

    def send(self, item):
        self.record("to_codex", item)
        self.process.stdin.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.process.stdin.flush()

    def read(self, deadline):
        remaining = deadline - time.monotonic()
        try:
            item = self.pending.get(timeout=max(0, remaining))
        except queue.Empty as exc:
            raise TimeoutError("Codex app-server message deadline") from exc
        if item is None:
            raise EOFError(f"Codex app-server exited ({self.process.poll()})")
        self.record("from_codex", item)
        if "transport_error" in item:
            raise RuntimeError("Non-JSON Codex app-server reply")
        if item.get("method") == "thread/tokenUsage/updated":
            self.last_usage = item["params"]["tokenUsage"]["last"]
        return item

    def request(self, method, params, deadline):
        self.next_id += 1
        identifier = self.next_id
        self.send({"id": identifier, "method": method, "params": params})
        while True:
            item = self.read(deadline)
            if item.get("id") == identifier and "method" not in item:
                if "error" in item:
                    raise RuntimeError(f'{method}: {item["error"]}')
                return item["result"]
            if "id" in item and "method" in item:
                raise RuntimeError(f'Unexpected server request before {method} ack: {item["method"]}')

    def start(self):
        deadline = time.monotonic() + 90
        self.request("initialize", {"clientInfo": {"name": "codex_clm_clbench", "version": "1.0"},
                                    "capabilities": {"experimentalApi": True}}, deadline)
        self.send({"method": "initialized"})
        return self.request("thread/start", {"cwd": "/workspace", "dynamicTools": TOOLS}, deadline)["thread"]["id"]

    def run_turn(self, thread_id, prompt, broker, deadline):
        result = self.request("turn/start", {"threadId": thread_id, "input": [{"type": "text", "text": prompt}]}, deadline)
        turn_id = result["turn"]["id"]
        while True:
            item = self.read(deadline)
            method = item.get("method")
            if method == "item/tool/call" and "id" in item:
                params = item["params"]
                if (params["threadId"], params["turnId"]) != (thread_id, turn_id):
                    raise RuntimeError("Dynamic tool request escaped its active task turn")
                tools = {"benchmark_status": "status", "benchmark_act": "act"}
                operation = hashlib.sha256(params["callId"].encode()).hexdigest()
                answer = broker.call(operation, tools[params["tool"]], params["arguments"])
                self.send({"id": item["id"], "result": {
                    "success": not answer["isError"],
                    "contentItems": [{"type": "inputText", "text": part["text"]} for part in answer["content"]],
                }})
            elif method == "turn/completed":
                params = item["params"]
                if (params["threadId"], params["turn"]["id"]) != (thread_id, turn_id):
                    raise RuntimeError("Unexpected completed turn")
                return params["turn"]
            elif "id" in item and method is not None:
                self.send({"id": item["id"], "error": {"code": -32601, "message": "Unsupported server request"}})

    def close(self):
        try:
            self.process.stdin.close()
            try:
                return self.process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                return self.process.wait(timeout=45)
        finally:
            self.reader.join(5)
            self.stderr.close()
            self.log.close()


def initial_prompt(descriptor, index, total, query, usage):
    pressure = ""
    previous = (usage or {}).get("inputTokens", 0)
    if previous >= 120000:
        pressure = (f"\nThe previous native Responses request used {previous} input tokens. "
                    "Before additional benchmark actions, use clm-context status and proactively offload and drop large stale completed tool exchanges.\n")
    return (
        f"CODEX_CLBENCH_TASK_{index:03d}\n"
        f"Continue the same long-term learning session. Task {index}/{total}: {descriptor['id']}. "
        "This task has its own official environment. Use benchmark_status and benchmark_act for all "
        "official actions and submission. Your local /workspace is only persistent working memory. "
        "Keep reusable notes from earlier tasks and retrieve them when useful. Before finishing the task, "
        "consider batching shrinking CLM edits for stale large observations, while retaining useful details. "
        "Use clm-context status to verify any accepted edit. Finish only after the official task is done. "
        "The next task arrives as another user turn in this same thread.\n"
        f"{pressure}\n{query}"
    )


def execute(tasks, native, thread_id):
    counts = collections.Counter()
    for index, descriptor in enumerate(tasks, 1):
        case = ROOT / "cases" / f'{index:03d}-{descriptor["id"]}'
        case.mkdir(parents=True, exist_ok=False)
        atomic(case / "intent.json", {"thread_id": thread_id, "index": index, "task": descriptor, "time": time.time()})
        task = CLBenchTask(REPOSITORY, descriptor["family"], descriptor["canonical_index"], "none")
        started = time.monotonic()
        turns = []
        try:
            first = task.status()
            atomic(case / "initial-task.json", first)
            atomic(case / "container-adaptations.json", task.container_adaptations)
            broker = TaskBroker(task, case / "tools")
            prompt = initial_prompt(descriptor, index, len(tasks), first["query"], native.last_usage)
            while not task.done:
                current = native.run_turn(thread_id, prompt, broker, started + 28800)
                turns.append(current)
                atomic(case / "turns.json", turns)
                if broker.failed:
                    raise RuntimeError(f'Official task action failed: {broker.failed}')
                if current["status"] != "completed":
                    raise RuntimeError(f'Native turn ended with {current["status"]}: {current.get("error")}')
                if not task.done:
                    prompt = (
                        f"CODEX_CLBENCH_TASK_{index:03d} The same official task is still active. "
                        "Continue from current benchmark_status, and finish the official task before replying."
                    )
            if task.container:
                capture_workspace(task.container, task.cwd, case)
            outcome = task.outcome()
            instance, = outcome["instance_outcomes"]
            result = {"thread_id": thread_id, "index": index, "task": descriptor, "turns": [turn["id"] for turn in turns],
                      "actions": task.actions, "initialization_terminal": first["done"], "objective": outcome,
                      "seconds": time.monotonic() - started}
            atomic(case / "result.json", result)
            counts["passed"] += bool(instance["success"])
            print(f'{index:03d}/{len(tasks)} {descriptor["id"]} passed={instance["success"]}', flush=True)
        finally:
            try:
                task.close()
            finally:
                if task.container:
                    removed = docker(["rm", "-f", task.container], check=False)
                    atomic(case / "container-cleanup.json", {
                        "container": task.container, "exit": removed.returncode,
                        "stderr": removed.stderr.decode(errors="replace"),
                    })
        atomic(ROOT / "PROGRESS.json", {"time": time.time(), "scored": index, "planned": len(tasks),
                                       "passed": counts["passed"], "last": descriptor["id"], "thread_id": thread_id})
    return {"scored": len(tasks), "passed": counts["passed"], "thread_id": thread_id}


def main():
    data = (ROOT / "PLAN.json").read_bytes()
    assert hashlib.sha256(data).hexdigest() == SHA, "frozen Claude Code order has changed"
    plan = json.loads(data)
    by_id = {task["id"]: task for task in plan["selected_tasks"]}
    tasks = [by_id[key] for key in plan["grouped_order"]]
    assert len(tasks) == len(by_id) == len(set(plan["grouped_order"])) == 100
    assert collections.Counter(row["family"] for row in tasks) == plan["quotas"]
    os.chdir(REPOSITORY)
    if "--probe" not in sys.argv:
        with (ROOT / "LAUNCH.json").open("x") as stream:
            json.dump({"pid": os.getpid(), "time": time.time(), "plan_sha256": SHA, "parallelism": 1}, stream)
    native = Native()
    try:
        thread_id = native.start()
        if "--probe" in sys.argv:
            print(json.dumps({"schema_probed": True, "thread_id": thread_id, "upstream_requests": 0}), flush=True)
            return
        atomic(ROOT / "THREAD.json", {"thread_id": thread_id, "launcher_pid": native.process.pid})
        atomic(ROOT / "RESULT.json", execute(tasks, native, thread_id))
    except Exception as exc:
        if "--probe" not in sys.argv:
            atomic(ROOT / "FAILURE.json", {"time": time.time(), "type": type(exc).__name__, "message": str(exc)})
        raise
    finally:
        status = native.close()
        atomic(ROOT / ("PROBE_EXIT.json" if "--probe" in sys.argv else "NATIVE_EXIT.json"), {"status": status, "time": time.time()})


if __name__ == "__main__":
    main()
