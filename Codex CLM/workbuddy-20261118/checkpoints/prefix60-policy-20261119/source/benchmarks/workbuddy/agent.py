"""Harbor adapter for both native and CLM Codex runs."""

import json
from pathlib import Path

from harbor.agents.base import BaseAgent
from workbuddy_bench.agents._agent_user import ensure_agent_user


async def initialize_named(environment, output, restored=None):
    """Honor the official DNS image's startup contract without resetting a restored zone."""
    if restored is not None:
        if restored.get("running") != restored.get("healthy"):
            raise RuntimeError("Cannot reproduce a live but unhealthy DNS process from a filesystem checkpoint")
        if not restored.get("running"):
            cleared = await environment.exec(command="rm -f /var/cache/bind/named.pid", user="root")
            if cleared.return_code:
                raise RuntimeError("Cannot clear the stopped service's stale process identifier")
            output.write_text(json.dumps({"restored_down_service": True}) + "\n")
            return
        command = "rm -f /var/cache/bind/named.pid; /usr/local/sbin/named -c /etc/bind/named.conf -u bind"
    else:
        command = "/usr/local/bin/restart-named.sh"
    result = await environment.exec(
        command="set -eu; " + command + "; "
                "for i in {1..30}; do if answer=$(dig @127.0.0.1 -p 5353 www.corp.example A +short +time=1 +tries=1 2>/dev/null); then "
                "if [ -n \"$answer\" ]; then printf '%s\\n' \"$answer\"; exit 0; fi; fi; sleep 0.1; done; exit 1",
        user="root", timeout_sec=45,
    )
    output.write_text(json.dumps({"restored": restored, "exit": result.return_code,
                                  "stdout": result.stdout, "stderr": result.stderr}, indent=2) + "\n")
    if result.return_code:
        raise RuntimeError("The official container-local DNS service did not become ready")


class SerialCodex(BaseAgent):
    def __init__(self, *args, options, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = options

    @staticmethod
    def name():
        return "workbuddy-codex-serial"

    def version(self):
        return "0.169.0"

    async def exec_as_root(self, environment, command):
        return await environment.exec(command=command, user="root")

    async def setup(self, environment):
        await ensure_agent_user(self, environment)
        result = await self.exec_as_root(
            environment,
            "set -eu; mkdir -p /logs/agent /logs/artifacts /serial-home/notes; "
            "chmod a+x /logs; chown dev /logs/agent /logs/artifacts; "
            "case \"$PWD\" in /app|/workdir|/workspace) chown dev \"$PWD\";; esac; "
            "chown -hR dev /serial-home; if [ -d /context ]; then chown -hR dev /context; fi; "
            "command -v python3; test -x /opt/codex/bin/codex-code-mode-host; "
            "test -x /opt/codex/codex-path/rg; /opt/codex/bin/codex --version",
        )
        (self.logs_dir / "preflight.txt").write_text(f"{result.stdout}\n{result.stderr}\n")
        if result.return_code:
            raise RuntimeError("Codex preflight failed in the official task environment")
        if self.options.get("restore_patch"):
            restored = await self.exec_as_root(
                environment,
                "python3 /opt/workbuddy/restore_state.py /recovery /logs/agent/restored-state.json "
                "> /logs/agent/restored-state.stdout 2>/logs/agent/restored-state.stderr",
            )
            if restored.return_code:
                raise RuntimeError("The reviewed native patch could not be restored")
            access = await self.exec_as_root(environment, "chown -hR dev /workspace")
            if access.return_code:
                raise RuntimeError("Restored workspace ownership is invalid")
        if self.options.get("restore_artifacts"):
            restored = await self.exec_as_root(
                environment,
                "cp -a /recovery-artifacts/. /logs/artifacts/ && chown -hR dev /logs/artifacts",
            )
            if restored.return_code:
                raise RuntimeError("Failed task artifacts could not be restored")
        if self.options.get("init_named"):
            await initialize_named(environment, self.logs_dir / "named-service.json",
                                   self.options.get("named_restored"))
        if self.options["arm"] == "clm":
            tool = await environment.exec(command="command -v clm-context")
            if tool.return_code:
                raise RuntimeError("CLM tool missing from the task user's standard PATH")

    async def run(self, instruction, environment, context):
        # Use Harbor's file transfer, not shell interpolation of benchmark text.
        path = self.logs_dir / "instruction-source.md"
        path.write_bytes(Path(self.options["instruction"]).read_bytes())
        opts = self.logs_dir / "run-options.json"
        opts.write_text(json.dumps({k: v for k, v in self.options.items() if k != "instruction"}))
        await environment.upload_file(path, "/tmp/workbuddy-instruction.md")
        await environment.upload_file(opts, "/tmp/workbuddy-options.json")
        access = await self.exec_as_root(
            environment,
            "chown dev /tmp/workbuddy-instruction.md /tmp/workbuddy-options.json; "
            "chmod 600 /tmp/workbuddy-instruction.md /tmp/workbuddy-options.json",
        )
        if access.return_code:
            raise RuntimeError("Cannot hand the transferred task input to the container's agent user")
        cleared = await environment.exec(command="rm -f /tmp/workbuddy-relay-ready")
        if cleared.return_code:
            raise RuntimeError("Cannot clear the previous loopback readiness marker")
        relay = await environment.exec(
            command="nohup python3 /opt/workbuddy/loopback.py </dev/null "
                    ">/logs/agent/loopback.stderr 2>&1 & "
                    "for i in {1..50}; do test -f /tmp/workbuddy-relay-ready && exit 0; sleep 0.1; done; exit 1"
        )
        if relay.return_code:
            raise RuntimeError("The trial's offline provider bridge failed to start")
        path = "/opt/codex/codex-path:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin"
        env = {"HOME": "/serial-home", "CODEX_HOME": "/serial-home/codex", "PYTHONUTF8": "1", "PATH": path}
        if self.options["arm"] == "clm":
            env["CLM_CONTEXT_DIR"] = "/context"
        result = await environment.exec(
            command="python3 /opt/workbuddy/native_turn.py /tmp/workbuddy-options.json "
                    "/tmp/workbuddy-instruction.md > /logs/agent/driver.stdout 2>/logs/agent/driver.stderr",
            env=env,
        )
        if result.return_code:
            raise RuntimeError(f"Codex task process exited with {result.return_code}")
