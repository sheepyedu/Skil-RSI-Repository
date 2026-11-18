"""Supervise one native task turn and reload its session after synchronized edits."""

import argparse
import grp
import json
import os
import pwd
import signal
import socketserver
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from native_session import file_json, message_parts, project_native, publish_projection

sys.path.insert(0, "/opt/clm/clm")
from container_entry import Relay


def write_control(child, value):
    child.stdin.write(json.dumps(value).encode() + b"\n")
    child.stdin.flush()


class Child:
    def __init__(self, arguments, env, output, error):
        identity = pwd.getpwnam("dev")
        group = grp.getgrgid(identity.pw_gid)
        self.result = threading.Event()
        with error.open("ab", buffering=0) as stderr:
            self.process = subprocess.Popen(
                ["/opt/claude", *arguments], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=stderr, env=env, user=identity.pw_uid, group=group.gr_gid, extra_groups=[],
                start_new_session=True,
            )
        self.reader = threading.Thread(target=self.collect, args=(output,), daemon=True)
        self.reader.start()

    def collect(self, output):
        with output.open("ab", buffering=0) as stream:
            for line in self.process.stdout:
                stream.write(line)
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") == "result":
                    self.result.set()

    def abort_for_reload(self):
        if self.process.poll() is not None:
            raise RuntimeError("Native child ended before the synchronization barrier")
        os.killpg(self.process.pid, signal.SIGTERM)
        self.process.wait(timeout=10)
        self.reader.join(timeout=5)
        if self.reader.is_alive():
            raise RuntimeError("Native journal reader failed to close")

    def finish(self):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        code = self.process.wait(timeout=15)
        self.reader.join(timeout=5)
        return code

    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                return self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                return self.process.wait()
        return self.process.returncode


def locate_anchor(path, identifier):
    for line in path.read_bytes().splitlines():
        event = json.loads(line)
        if event.get("type") != "user" or event.get("sessionId") != identifier or event.get("isSidechain"):
            continue
        content = event.get("message", {}).get("content")
        if content and any(
            part.get("text", "").startswith("[WB_SERIAL_TASK_")
            for part in message_parts(event["message"]) if part["type"] == "text"
        ):
            return event["uuid"]
    raise ValueError("Native benchmark anchor not found")


def run_turn(args, relay_port):
    env = {
        **os.environ, "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{relay_port}",
        "ANTHROPIC_API_KEY": "clm-session-local", "CLAUDE_CODE_ENTRYPOINT": "sdk-ts",
    }
    output = Path("/logs/agent/cc-output.txt")
    error = Path("/logs/agent/cc-stderr.txt")
    history = Path(env["CLAUDE_CONFIG_DIR"]) / "projects" / "-workspace" / f"{args.session}.jsonl"
    segment = 0
    edit_index = 1
    child = None
    until = time.monotonic() + args.timeout
    try:
        while True:
            env["CLAUDE_CODE_RESUME_INTERRUPTED_TURN"] = "1" if segment else "0"
            launch_flags = [
                *args.claude, "--input-format", "stream-json", "--replay-user-messages",
                "--resume" if segment or args.resume else "--session-id", args.session,
            ]
            child = Child(launch_flags, env, output, error)
            write_control(child.process, {
                "type": "control_request", "request_id": str(uuid.uuid4()),
                "request": {"subtype": "initialize", "hooks": {}, "sdkMcpServers": []},
            })
            if segment == 0:
                write_control(child.process, {
                    "type": "user", "message": {"role": "user", "content": args.instruction.read_text()},
                    "session_id": "", "parent_tool_use_id": None,
                })
            while time.monotonic() < until:
                pending = args.control / f"edit-{edit_index:04d}"
                request = pending / "request.json"
                if request.is_file():
                    try:
                        change = json.loads(request.read_text())
                        if change["session_id"] != args.session:
                            raise ValueError("Unexpected native synchronization target")
                        child.abort_for_reload()
                        if history.is_symlink() or history.parent.is_symlink():
                            raise ValueError("Unexpected native replay symlink")
                        before = history.read_bytes()
                        after, count = project_native(
                            before, set(change["tool_ids"]), locate_anchor(history, args.session),
                            change["old_note"], change["new_note"], args.session,
                        )
                        publish_projection(history, before, after, pending / "native", {
                            "session_id": args.session, "native_writer_exit": child.process.returncode,
                            "deleted_events": count, "generation": segment + 1,
                        })
                    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                        file_json(pending / "failed.json", {"error": str(error)})
                        raise
                    segment += 1
                    edit_index += 1
                    break
                if (pending / "rejected.json").is_file():
                    # Rejections do not interrupt the current native CLI reader.
                    edit_index += 1
                    continue
                if child.result.is_set():
                    return child.finish()
                if child.process.poll() is not None:
                    child.reader.join(timeout=3)
                    return child.process.returncode
                time.sleep(0.04)
            else:
                raise RuntimeError("Native turn did not reach a terminal or synchronization boundary")
    finally:
        if child is not None:
            child.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--instruction", type=Path, required=True)
    parser.add_argument("--control", type=Path, default=Path("/sync-control"))
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument("claude", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    args.claude = args.claude[1:] if args.claude[:1] == ["--"] else args.claude
    with socketserver.ThreadingTCPServer(("127.0.0.1", 0), Relay) as bridge:
        bridge.daemon_threads = True
        server = threading.Thread(target=bridge.serve_forever, daemon=True)
        server.start()
        try:
            return run_turn(args, bridge.server_address[1])
        finally:
            bridge.shutdown()
            server.join(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
