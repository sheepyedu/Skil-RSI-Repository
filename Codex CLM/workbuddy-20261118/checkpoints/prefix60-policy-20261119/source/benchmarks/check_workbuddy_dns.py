"""Real Harbor DNS startup and filesystem checkpoint recovery, with no model calls."""

import argparse
import asyncio
import json
from pathlib import Path

from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig
from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial

from agent import initialize_named
from checkpoint import capture_failed_task, docker
from check_workbuddy_recovery import ProbeAgent
from clm.context import write_json
import run

THREAD = "00000000-0000-0000-0000-000000000002"
ZONE = "/var/cache/bind/zones/corp.example.zone"


class DNSProbe(ProbeAgent):
    def __init__(self, *args, restored=None, expected_zone=None, stop_after_init=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.restored = restored
        self.expected_zone = expected_zone
        self.stop_after_init = stop_after_init

    async def setup(self, environment):
        await super().setup(environment)
        await initialize_named(environment, self.logs_dir / "named-service.json", self.restored)

    async def run(self, instruction, environment, context):
        if self.expected_zone is None:
            result = await environment.exec(
                command=f"printf '\\n; retained-checkpoint-fixture\\n' >> {ZONE}", user="root",
            )
            assert result.return_code == 0
        result = await environment.exec(command=f"sha256sum {ZONE}", user="root")
        assert result.return_code == 0
        actual = result.stdout.split()[0]
        if self.expected_zone is not None:
            assert actual == self.expected_zone, "Restoring the service reset its active zone"
        write_json(self.logs_dir / "fixture-zone.json", {"sha256": actual, "restored": self.restored is not None})
        if self.stop_after_init and self.restored is None:
            stopped = await environment.exec(command="pkill -TERM -x named; sleep 1", user="root")
            assert stopped.return_code == 0
        if self.restored is not None and not self.restored["running"]:
            stopped = await environment.exec(command="! pgrep -x named; test ! -f /var/cache/bind/named.pid", user="root")
            assert stopped.return_code == 0, "Restoring a stopped service started it again"
        write_json(self.logs_dir / "native-result.json", {"thread": THREAD, "engineering_fixture": True})
        raise RuntimeError("Intentional DNS engineering fixture termination, zero model API calls")


async def main(base, output, stopped=False):
    output.mkdir(mode=0o700)
    home = output / "home"
    home.mkdir(mode=0o700)
    extra = base / "security-extra"
    row = next(x for x in run.read(extra / "plan.json")["tasks"] if x["position"] == 65)
    task = run.task_dir(extra, row)
    saved = None
    expected = None
    for phase in ("initial", "restored"):
        name = "wbc-dns-fixture-" + phase
        private = output / phase
        private.mkdir()
        trial_dir = output / "trials" / name
        trial = await Trial.create(TrialConfig(
            task=TaskConfig(path=task), trial_name=name, trials_dir=output / "trials",
            agent=AgentConfig(import_path="check_workbuddy_dns:DNSProbe", kwargs={
                "restored": saved["services"]["named"] if saved else None, "expected_zone": expected,
                "stop_after_init": stopped,
            }),
            environment=EnvironmentConfig(import_path="checkpoint:CheckpointEnvironment",
                kwargs={"checkpoint_image": saved["image"] if saved else None},
                mounts=[run.bind(home, "/serial-home", False)],
                extra_docker_compose=[base / "formal-13/offline.yaml"]),
        ))
        if phase == "initial":
            async def snapshot(event):
                await asyncio.to_thread(capture_failed_task, name, trial_dir, home, private, row)
            trial.add_hook(TrialEvent.AGENT_END, snapshot)
        result = (await trial.run()).model_dump(mode="json")
        assert (result.get("exception_info") or {}).get("exception_message", "").startswith("Intentional DNS engineering fixture")
        zone = run.read(trial_dir / "agent/fixture-zone.json")
        if phase == "initial":
            expected = zone["sha256"]
            saved = run.read(private / "checkpoint/receipt.json")
            assert saved["services"]["named"] == {"running": not stopped, "healthy": not stopped}
            assert run.sha(private / "checkpoint/image.tar") == saved["archive_sha256"]
            docker("load", "--input", str(private / "checkpoint/image.tar"), timeout=600)
        else:
            assert zone["restored"] and zone["sha256"] == expected
    write_json(output / "RESULT.json", {
        "api_calls": 0, "initial_dns_healthy": True, "restored_dns_healthy": not stopped,
        "stopped_dns_preserved": stopped,
        "active_zone_preserved": True, "zone_sha256": expected, "code_sha256": run.code_sha(),
    })
    print((output / "RESULT.json").read_text())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stopped", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.base, args.output, args.stopped))
