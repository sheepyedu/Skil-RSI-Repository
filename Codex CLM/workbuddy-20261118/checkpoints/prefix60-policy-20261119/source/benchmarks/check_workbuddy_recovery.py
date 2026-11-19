"""Regression checks using the captured task-006 failure and real Docker checkpoints."""

import argparse
import asyncio
import io
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

from harbor.agents.base import BaseAgent
from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig
from harbor.trial.hooks import TrialEvent
from harbor.trial.trial import Trial
from workbuddy_bench.agents._agent_user import ensure_agent_user

from checkpoint import capture_failed_task, docker, restore_context
from clm.context import write_json
from relay import Handler, temporary_provider_failure
import run
from continue_workbuddy_transport import eligible_checkpoint


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def getheaders(self):
        return [("Content-Type", "text/event-stream")]

    def read1(self, _):
        payload, self.payload = self.payload, b""
        return payload


def transport_check(failure, success, retries_succeed):
    sent = []
    responses = [failure, success] if retries_succeed else [failure, failure, failure]

    class Connection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, method, target, body, headers):
            sent.append(body)

        def getresponse(self):
            return Response(responses.pop(0))

        def close(self):
            pass

    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        handler = object.__new__(Handler)
        handler.path = "/v1/responses"
        handler.server = SimpleNamespace(endpoint=urlsplit("https://fixture.invalid/v1"))
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        event = {}
        with patch("relay.http.client.HTTPSConnection", Connection), patch("relay.time.sleep"):
            handler.transfer("/v1/responses", {}, b"exact original request", folder, event, True)
        assert all(value == b"exact original request" for value in sent)
        assert (folder / "attempts/1/response.raw").read_bytes() == failure
        if retries_succeed:
            assert len(sent) == 2 and statuses == [200]
            assert handler.wfile.getvalue() == success and event["delivered"]
        else:
            assert len(sent) == 3 and statuses == [502] and not event["delivered"]
            assert b"response.failed" not in handler.wfile.getvalue()
        return {"attempts": len(sent), "statuses": statuses, "delivered": event["delivered"]}


class ProbeAgent(BaseAgent):
    @staticmethod
    def name():
        return "checkpoint-engineering-fixture"

    def version(self):
        return "1.0"

    async def setup(self, environment):
        self.exec_as_root = lambda environment, command: environment.exec(command=command, user="root")
        await ensure_agent_user(self, environment)
        result = await environment.exec(
            command="mkdir -p /logs/agent /logs/artifacts; chmod a+x /logs; "
                    "chown dev /logs/agent /logs/artifacts", user="root",
        )
        assert result.return_code == 0

    async def run(self, instruction, environment, context):
        result = await environment.exec(
            command="printf 'root filesystem checkpoint\n' > /workspace/checkpoint-probe.txt; "
                    "printf 'mounted task artifact\n' > /logs/artifacts/checkpoint-probe.txt"
        )
        assert result.return_code == 0
        (self.logs_dir / "native-result.json").write_text(json.dumps({
            "thread": "00000000-0000-0000-0000-000000000001", "fixture": True,
        }))
        raise RuntimeError("Intentional engineering fixture failure, zero model API calls")


async def checkpoint_check(base, plan, output):
    row = plan["tasks"][5]
    home = output / "home"
    home.mkdir()
    evidence = output / "evidence"
    evidence.mkdir()
    name = "wbc-checkpoint-engineering-fixture"
    trial_dir = output / "trials" / name
    trial = await Trial.create(TrialConfig(
        task=TaskConfig(path=run.task_dir(Path(plan["reference"]), row)),
        trial_name=name, trials_dir=output / "trials",
        agent=AgentConfig(import_path="check_workbuddy_recovery:ProbeAgent"),
        environment=EnvironmentConfig(
            import_path="checkpoint:CheckpointEnvironment",
            mounts=[run.bind(home, "/serial-home", False)],
            extra_docker_compose=[base / "formal-12/offline.yaml"],
        ),
    ))

    async def save(event):
        await asyncio.to_thread(capture_failed_task, name, trial_dir, home, evidence, row)

    trial.add_hook(TrialEvent.AGENT_END, save)
    result = (await trial.run()).model_dump(mode="json")
    assert result["exception_info"]["exception_message"].startswith("Intentional engineering fixture")
    saved = run.read(evidence / "checkpoint/receipt.json")
    archive = evidence / "checkpoint/image.tar"
    assert run.sha(archive) == saved["archive_sha256"]
    docker("load", "--input", str(archive), timeout=600)
    content = docker("run", "--rm", "--network=none", "--entrypoint", "cat",
                     saved["image_id"], "/workspace/checkpoint-probe.txt")
    assert content == "root filesystem checkpoint"
    assert (Path(saved["artifacts"]) / "checkpoint-probe.txt").read_text() == "mounted task artifact\n"
    return {"image_id": saved["image_id"], "root_file_restored": True, "artifact_restored": True, "api_calls": 0}


async def main(base, output):
    output.mkdir(mode=0o700, exist_ok=False)
    old = base / "formal-12"
    failed_dir = next((old / "native/evidence").glob("006*/wire"))
    failure = (sorted(failed_dir.glob("*/response.raw"))[-1]).read_bytes()
    success = (sorted(failed_dir.glob("*/response.raw"))[0]).read_bytes()
    results = {}
    results["retry_then_deliver_once"] = transport_check(failure, success, True)
    results["failed_stream_suppressed"] = transport_check(failure, success, False)
    newer = list((base / "formal-13/native/failed-attempts").glob("008*/attempt-01/wire/*/response.raw"))
    newer = [path for path in newer if b'upstream_stream_read_error' in path.read_bytes()]
    if newer:
        results["actual_stream_read_error"] = transport_check(newer[-1].read_bytes(), success, True)
    status_errors = list((base / "formal-13/native/evidence").glob("009*/wire/*/response.raw"))
    status_errors = [path for path in status_errors if b'bad_response_status_code' in path.read_bytes()]
    if status_errors:
        results["actual_bad_status_temporary"] = transport_check(status_errors[-1].read_bytes(), success, True)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        context = restore_context(root, old / "clm")
        source = run.read(root / "RESTORED_FROM_WIRE.json")["source"]
        wire = Path(source).parent
        raw = run.read(wire / "request.raw.json")["input"]
        sent = run.read(wire / "request.sent.json")["input"]
        restored, _ = context.apply(raw)
        assert restored == sent
        results["clm_projection_restored"] = {"matches": True, "revision": context.revision - 1}
    permanent = output / "permanent-error.raw"
    permanent.write_text('data: {"type":"response.failed","response":{"error":{"code":"invalid_request_error","message":"invalid schema"}}}\n\n')
    assert not temporary_provider_failure(permanent)
    auth = output / "permanent-auth.raw"
    auth.write_text('data: {"type":"response.failed","response":{"error":{"code":"bad_response_status_code","message":"authentication failed"}}}\n\n')
    assert not temporary_provider_failure(auth)
    results["permanent_failure_rejected"] = True
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "checkpoint").mkdir()
        saved = {"row": {"position": 0}, "thread": "engineering-fixture"}
        write_json(root / "checkpoint/receipt.json", saved)
        record = {**saved, "reward": None}
        wire = root / "wire/00001"
        for number, raw in ((1, failure), (2, permanent.read_bytes())):
            folder = wire / "attempts" / str(number)
            folder.mkdir(parents=True)
            (folder / "response.raw").write_bytes(raw)
            write_json(folder / "receipt.json", {"status": 200, "temporary_provider_failure": number == 1})
        write_json(wire / "receipt.json", {"delivered": False})
        assert eligible_checkpoint(root, record) is None
        if newer:
            (wire / "attempts/2/response.raw").write_bytes(newer[-1].read_bytes())
            assert eligible_checkpoint(root, record) == saved
        results["last_attempt_controls_task_recovery"] = True
    results["checkpoint"] = await checkpoint_check(base, run.read(old / "plan.json"), output)
    dns_path = base / "dns-service-check-01/RESULT.json"
    if dns_path.exists():
        dns = run.read(dns_path)
        if dns.get("code_sha256") == run.code_sha():
            assert dns["api_calls"] == 0 and dns["initial_dns_healthy"] and dns["restored_dns_healthy"]
            assert dns["active_zone_preserved"]
            results["dns_service"] = {"result": str(dns_path), "sha256": run.sha(dns_path)}
    results["code_sha256"] = run.code_sha()
    write_json(output / "RESULT.json", results)
    print(json.dumps(results), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    asyncio.run(main(args.base, args.output))
