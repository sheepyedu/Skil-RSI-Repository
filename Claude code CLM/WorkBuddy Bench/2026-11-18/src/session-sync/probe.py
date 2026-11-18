"""Exercise a live edit through Claude Code's native JSONL and same-ID continuation."""

import argparse
import json
import os
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from clm.context import Context, blocks, editable_exchanges
from native_session import canonical_history, file_json, project_native, publish_projection

TASK = "WB_NATIVE_SESSION_SYNC_TEST immutable benchmark task"
OLD = "toolu_clm_obsolete"
KEEP = "toolu_clm_keep"
EDIT = "toolu_clm_edit"
NOTE = "Keep the retained fixture result. The obsolete exchange was deliberately removed."


def tool_ids(messages):
    return {
        item.get("id") if item["type"] == "tool_use" else item.get("tool_use_id")
        for m in messages for item in blocks(m) if item["type"] in {"tool_use", "tool_result"}
    }


class Probe:
    def __init__(self, root, binary):
        self.root = root
        self.binary = binary
        self.nonce = str(uuid.uuid4())
        self.context = Context(root / "state")
        self.context.directory.mkdir()
        self.started = threading.Event()
        self.old_reader_stopped = threading.Event()
        self.reloaded = threading.Event()
        self.done = threading.Event()
        self.resume_requested = threading.Event()
        self.request_count = 0
        self.old_note = ""
        self.edit = None
        self.tool_ids = None
        for name in ("home", "workspace", "wire"):
            (root / name).mkdir()
        self.home = root / "home"
        config = self.home / ".claude"
        config.mkdir()
        file_json(config / "settings.json", {"skipDangerousModePermissionPrompt": True})

        probe = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                request = json.loads(raw)
                messages = request["messages"]
                probe.request_count += 1
                number = probe.request_count
                directory = root / "wire" / f"{number:02d}"
                directory.mkdir()
                (directory / "request.json").write_bytes(raw)
                try:
                    probe.handle(self, request, messages, directory)
                except (ValueError, KeyError, AssertionError) as error:
                    file_json(directory / "failed.json", {"detail": str(error)})
                    self.send_error(400)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def handle(self, handler, request, messages, directory):
        ids = tool_ids(messages)
        if self.reloaded.is_set():
            self.resume_requested.set()
            if OLD in ids or KEEP not in ids or EDIT not in ids:
                raise ValueError(f"Reloaded CLI context contains unexpected tool IDs {sorted(ids)}")
            base = canonical_history(messages, NOTE)
            user_turns = [m for m in base if m["role"] == "user" and any(b.get("text") == TASK for b in blocks(m))]
            if len(user_turns) != 1:
                raise ValueError("The benchmark instruction was resent or lost")
            file_json(directory / "resumed-proof.json", {
                "retained_ids": sorted(ids),
                "original_user_turn_count": len(user_turns),
                "native_memory_note": True,
            })
            self.send(handler, directory, request["model"], {"type": "text", "text": "SYNC_PROBE_DONE"})
            self.done.set()
            return
        pairs = editable_exchanges(messages)
        before_note = self.context.note
        _, event = self.context.apply(messages)
        file_json(directory / "context.json", event)
        if event["edit"] == "accepted":
            self.old_note = before_note
            self.edit = event
            self.tool_ids = {
                block["id"] for item in event["dropped_ids"]
                for block in blocks(pairs[item][1][0]) if block["type"] == "tool_use"
            }
            file_json(directory / "held.json", {"model_dispatched": False, "selected_ids": sorted(self.tool_ids)})
            self.started.set()
            self.old_reader_stopped.wait(50)
            return
        if not ids:
            block = self.bash(OLD, "printf '%s\\n' OLD_FIXTURE_OUTPUT >> evidence.txt; printf '%s' OLD_FIXTURE_OUTPUT")
        elif KEEP not in ids:
            block = self.bash(KEEP, "printf '%s\\n' KEEP_FIXTURE_OUTPUT >> evidence.txt; printf '%s' KEEP_FIXTURE_OUTPUT")
        else:
            key = next(
                k for k, (_, pair) in pairs.items()
                if OLD in tool_ids(pair)
            )
            block = self.bash(EDIT, f"clm-context edit --drop {key} --note '{NOTE}'")
        self.send(handler, directory, request["model"], block)

    @staticmethod
    def bash(identifier, command):
        return {"type": "tool_use", "name": "Bash", "id": identifier,
                "input": {"command": command, "description": "Run local session synchronization fixture"}}

    @staticmethod
    def send(handler, directory, model, block):
        payload = dict(block)
        if block["type"] == "tool_use":
            payload["input"] = {}
            delta = {"type": "input_json_delta", "partial_json": json.dumps(block["input"])}
        else:
            payload["text"] = ""
            delta = {"type": "text_delta", "text": block["text"]}
        usage = {"input_tokens": 110, "output_tokens": 32}
        result = [
            {"type": "message_start", "message": {
                "id": "msg_" + uuid.uuid4().hex, "type": "message", "role": "assistant",
                "model": model, "content": [], "stop_reason": None, "stop_sequence": None,
                "usage": {"input_tokens": 110, "output_tokens": 0},
            }},
            {"type": "content_block_start", "index": 0, "content_block": payload},
            {"type": "content_block_delta", "index": 0, "delta": delta},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "tool_use" if "input" in block else "end_turn",
                                                "stop_sequence": None}, "usage": usage},
            {"type": "message_stop"},
        ]
        wire = b"".join(f"event: {x['type']}\ndata: {json.dumps(x)}\n\n".encode() for x in result)
        (directory / "response.sse").write_bytes(wire)
        handler.send_response(200)
        handler.send_header("Content-Type", "text/event-stream")
        handler.send_header("Content-Length", str(len(wire)))
        handler.end_headers()
        handler.wfile.write(wire)

    def launch(self, phase, resume=False):
        env = {
            **os.environ,
            "HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.home / ".claude"),
            "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{self.server.server_address[1]}",
            "ANTHROPIC_API_KEY": "synthetic-loopback",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
            "DISABLE_AUTO_COMPACT": "1",
            "CLAUDE_CODE_ENTRYPOINT": "sdk-ts",
            "CLM_CONTEXT_DIR": str(self.context.directory),
            "PATH": "/opt/clm/bin:" + os.environ["PATH"],
            "CLAUDE_CODE_RESUME_INTERRUPTED_TURN": "1" if resume else "0",
        }
        command = [
            str(self.binary), "--bare", "--print", "--verbose",
            "--input-format", "stream-json", "--output-format", "stream-json",
            "--include-partial-messages", "--replay-user-messages",
            "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
            "--setting-sources", "", "--permission-mode", "bypassPermissions",
            "--model", "claude-sonnet-4-6", "--tools", "Bash",
            "--session-id" if not resume else "--resume", self.nonce,
        ]
        with (self.root / f"{phase}.stdout.jsonl").open("wb") as out, (self.root / f"{phase}.stderr").open("wb") as err:
            return subprocess.Popen(command, env=env, cwd=self.root / "workspace", stdin=subprocess.PIPE, stdout=out, stderr=err)

    @staticmethod
    def input(child, value):
        child.stdin.write(json.dumps(value).encode() + b"\n")
        child.stdin.flush()

    def run(self):
        child = self.launch("initial")
        try:
            self.input(child, {
                "type": "user", "message": {"role": "user", "content": TASK},
                "parent_tool_use_id": None, "session_id": "",
            })
            if not self.started.wait(60):
                raise RuntimeError("The initial CLI never reached a model-generated edit")
            child.terminate()
            child.wait(timeout=10)
            self.old_reader_stopped.set()
            native = next((self.home / ".claude" / "projects").glob(f"*/{self.nonce}.jsonl"))
            before = native.read_bytes()
            entries = [json.loads(x) for x in before.splitlines()]
            first = next(x for x in entries if x.get("type") == "user" and
                         any(p.get("text") == TASK for p in blocks(x["message"])))
            after, count = project_native(before, self.tool_ids, first["uuid"],
                                          self.old_note, self.context.note, self.nonce)
            metadata = publish_projection(native, before, after, self.root / "commit", {
                "session_id": self.nonce, "parent_remaps_after_deletion": count,
                "native_writer_exit": child.returncode, "selected_ids": sorted(self.tool_ids),
            })
            self.reloaded.set()
            child = self.launch("resume", resume=True)
            self.input(child, {
                "type": "control_request", "request_id": str(uuid.uuid4()),
                "request": {"subtype": "initialize", "hooks": {}, "sdkMcpServers": []},
            })
            automatic = self.resume_requested.wait(5)
            if not automatic:
                self.input(child, {
                    "type": "user", "session_id": self.nonce, "parent_tool_use_id": None,
                    "message": {"role": "user", "content": (
                        "Continue the interrupted benchmark turn from the current session. "
                        "Do not repeat completed tool calls."
                    )},
                })
            if not self.done.wait(35):
                raise RuntimeError("The interrupted turn did not resume")
            child.stdin.close()
            if child.wait(timeout=15):
                raise RuntimeError("The relaunched CLI failed")
            written = (self.root / "workspace" / "evidence.txt").read_text().splitlines()
            if written != ["OLD_FIXTURE_OUTPUT", "KEEP_FIXTURE_OUTPUT"]:
                raise ValueError("A completed tool was executed more than once")
            if not any(json.loads(l).get("type") == "result" for l in (self.root / "resume.stdout.jsonl").read_text().splitlines()):
                raise ValueError("The resumed CLI has no terminal result")
            file_json(self.root / "accepted.json", {
                **metadata, "same_session": True, "original_prompt_sent_once": True,
                "tool_side_effects": written, "requests": self.request_count,
                "automatic_continuation": automatic,
            })
        finally:
            self.old_reader_stopped.set()
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            self.server.shutdown()
            self.thread.join(timeout=5)
            self.server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--binary", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    Probe(args.output, args.binary).run()
