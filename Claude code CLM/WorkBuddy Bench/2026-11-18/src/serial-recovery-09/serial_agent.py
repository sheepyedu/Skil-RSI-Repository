"""WorkBuddy CLI harness with a persistent native session per experimental arm."""

import json
import shlex

from pydantic import ValidationError

from workbuddy_bench.agents._agent_user import ensure_agent_user
from workbuddy_bench.agents.cc_agent import CcAgent

from clm.run import system_prompt


NATIVE_AUTO_COMPACT_PERCENT = 75


class SerialCcAgent(CcAgent):
    def __init__(self, *args, arm, position, session_id, marker, web, **kwargs):
        super().__init__(*args, **kwargs)
        self.arm = arm
        self.position = position
        self.claude_session_uuid = session_id
        self.marker = marker
        self.web = web

    def get_version_command(self):
        return "/opt/claude --version"

    async def install(self, environment):
        await ensure_agent_user(self, environment)
        # Harbor captures the original image WORKDIR before the agent switches to the
        # stable session directory. The private bridge and scripts are read-only.
        outcome = await self.exec_as_root(
            environment,
            command=(
                'set -eu; mkdir -p /logs/agent /logs/artifacts; '
                'chmod a+x /logs; chown dev /logs/agent /logs/artifacts; '
                'case "$PWD" in /app|/workdir|/workspace) chown dev "$PWD";; esac; '
                'chown -hR dev /serial-home; if [ -d /context ]; then chown -hR dev /context; fi; '
                'test -x /opt/claude; command -v python3 >/dev/null'
            ),
        )
        if outcome.return_code:
            raise RuntimeError("Task container did not satisfy the native CLI preflight")
        if self.web:
            relay = await self.exec_as_root(
                environment, command=(
                    "nohup python3 /opt/serial/judge_relay.py </dev/null >/logs/agent/judge-relay.txt 2>&1 &"
                ),
            )
            if relay.return_code:
                raise RuntimeError("Verifier relay failed to start")

    def populate_context_post_run(self, context):
        try:
            super().populate_context_post_run(context)
        except ValidationError as error:
            if any(item["loc"] != ("steps",) or item["type"] != "too_short" for item in error.errors()):
                raise
            (self.logs_dir / "atif-conversion-error.txt").write_text(str(error) + "\n")

    async def run(self, instruction, environment, context):
        prompt = self.render_instruction(instruction)
        workdir = await environment.exec(command="pwd")
        if workdir.return_code:
            raise RuntimeError("Cannot discover official task WORKDIR")
        prompt = (
            f"[{self.marker}] This turn contains a new benchmark task. "
            f"Use the current task files in {workdir.stdout.strip()} and follow "
            "the task's requested output paths. The current container has fresh task files. "
            "The prior conversation and /serial-home/notes are available for reusable knowledge.\n\n"
            + prompt
        )
        flags = [
            "python3", "/opt/clm/clm/container_entry.py", "--bare", "--print", "--verbose",
            "--output-format", "stream-json", "--include-partial-messages",
            "--model", self.model_name, "--permission-mode", "bypassPermissions",
            "--setting-sources", "", "--no-chrome", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--settings", "/opt/serial/settings.json",
            "--max-turns", str(self._max_turns),
            "--session-id" if self.position == 1 else "--resume", self.claude_session_uuid,
        ]
        if self.arm == "clm":
            extra = system_prompt("WORKBUDDY_CLM_SESSION_" + self.claude_session_uuid)
            extra = extra.replace("/workspace", "/serial-home/notes")
            extra += " During a series of tasks, decide when completed tool results can be discarded and which knowledge should carry forward."
            flags += ["--append-system-prompt", extra]
        command = (
            "set -eu; cd /workspace; printf '%s' "
            + shlex.quote(prompt)
            + " > /tmp/workbuddy-prompt.txt; "
            + shlex.join(flags)
            + " < /tmp/workbuddy-prompt.txt > /logs/agent/cc-output.txt "
            + "2> /logs/agent/cc-stderr.txt"
        )
        env = {
            "HOME": "/serial-home",
            "CLAUDE_CONFIG_DIR": "/serial-home/config",
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
            "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "200000",
            "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "16384",
            "PATH": "/opt/clm/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "CLM_CONTEXT_DIR": "/context",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": self.model_name,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": self.model_name,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": self.model_name,
            "CLAUDE_CODE_SUBAGENT_MODEL": self.model_name,
        }
        if self.arm == "clm":
            env["DISABLE_AUTO_COMPACT"] = "1"
            # Leave room for the raw replay history while CLM manages the
            # projected input and independently prunes between tasks.
            env["CLAUDE_CODE_AUTO_COMPACT_WINDOW"] = "393216"
        else:
            env["CLAUDE_AUTOCOMPACT_PCT_OVERRIDE"] = str(NATIVE_AUTO_COMPACT_PERCENT)
        result = await environment.exec(command=command, env=env)
        if result.return_code:
            (self.logs_dir / "exec-error.txt").write_text(
                f"exit={result.return_code}\n{result.stdout}\n{result.stderr}\n"
            )
            raise RuntimeError(f"Claude Code exited {result.return_code}. See raw stream and stderr.")
