"""Regrade task21's original CSV exporters with a BOM-aware official CSV reader.

The original UTF-8-sig CSV bytes and exporters remain unchanged. Only the official
reader's codec changes, allowing its original thirteen semantic checks to run.
"""

import argparse
import asyncio
import hashlib
import json
import re
import shlex
import shutil
from pathlib import Path

from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig, VerifierConfig
from harbor.trial.trial import Trial

from audit_workbuddy import judge_quality, load, sha, trial_key
from regrade_workbuddy_code import PatchAgent, basic_setup
from repair_workbuddy_judge import write
import run


ORIGINAL_READER = "rows=list(csv.DictReader((ROOT/'export.csv').open(newline='',encoding='utf-8')))"
FIXED_READER = ORIGINAL_READER.replace("encoding='utf-8'", "encoding='utf-8-sig'")


def csv_from_patch(patch):
    sections = patch.split(b"diff --git ")
    selected = [s for s in sections if s.startswith(b"a/export.csv b/export.csv\n")]
    if len(selected) != 1 or b"--- /dev/null\n" not in selected[0]:
        raise ValueError("Expected one fully archived new CSV file in the original patch")
    section = selected[0]
    headers = re.findall(rb"^@@ -0,0 \+1,(\d+) @@\r?$", section, flags=re.M)
    if len(headers) != 1:
        raise ValueError("Expected a single complete CSV addition hunk")
    lines = [line[1:] for line in section.splitlines(keepends=True)
             if line.startswith(b"+") and not line.startswith(b"+++ ")]
    if len(lines) != int(headers[0]):
        raise ValueError("Original CSV hunk is incomplete")
    data = b"".join(lines)
    if not data.startswith(b"\xef\xbb\xbfaccount_id,"):
        raise ValueError("The identified leading UTF-8 BOM is absent")
    return data


class BOMPatchAgent(PatchAgent):
    async def run(self, instruction, environment, context):
        await super().run(instruction, environment, context)
        await environment.upload_file(Path(self.options["original_verifier"]), "/tmp/original-verifier.py")
        result = await self.exec_as_root(environment, "chmod 644 /tmp/original-verifier.py")
        if result.return_code:
            raise RuntimeError("Original verifier transfer failed")
        probe = '''import os,pathlib,hashlib,subprocess,json
p=pathlib.Path('/workspace/export.csv')
digest=lambda:hashlib.sha256(p.read_bytes()).hexdigest()
before=digest()
r=subprocess.run(['python','/tmp/original-verifier.py'],env={**os.environ,'LOG_DIR':'/tmp/original-grader-probe'},capture_output=True,text=True,timeout=30)
print(json.dumps({'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'before_csv_sha256':before,'after_csv_sha256':digest(),'header_hex':p.read_bytes().splitlines()[0].hex()}))'''
        result = await environment.exec(command="python3 -c " + shlex.quote(probe))
        (self.logs_dir / "original-probe.json").write_text(result.stdout or "")
        (self.logs_dir / "original-probe.stderr").write_text(result.stderr or "")
        if result.return_code:
            raise RuntimeError("Original CSV verification probe did not finish")


async def repair(base, original, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    script = output / "EXECUTED_SCRIPT.py"
    shutil.copyfile(Path(__file__), script)
    row = load(original / "plan.json")["tasks"][20]
    if (row["position"], row["domain"], row["task"]) != (21, "code", "data_reporting-medium-customer_health_export"):
        raise ValueError("Only the identified Code21 CSV reader defect is supported")
    if run.image_id(row["image"]) != row["image_id"]:
        raise ValueError("The original task image identity changed")
    plan = load(original / "plan.json")
    task = run.task_dir(Path(plan["reference"]), row)
    verifier = task / "tests/verifier.py"
    text = verifier.read_text()
    if text.count(ORIGINAL_READER) != 1:
        raise ValueError("The official verifier differs from the diagnosed source")
    dataset = output / "dataset"
    dataset.mkdir()
    shutil.copyfile(task.parent.parent / "dataset.toml", dataset / "dataset.toml")
    shutil.copytree(task.parent.parent / "shared", dataset / "shared", symlinks=True)
    copied = dataset / "tasks" / row["task"]
    shutil.copytree(task, copied, symlinks=True)
    corrected = copied / "tests/verifier.py"
    corrected.write_text(text.replace(ORIGINAL_READER, FIXED_READER))
    repairs = []
    for arm in run.ARMS:
        receipt_path = original / arm / "evidence" / trial_key(row) / "receipt.json"
        receipt = load(receipt_path)
        if not receipt["accepted"] or receipt["row"] != row:
            raise ValueError("Original actor is not complete")
        source = original / arm / "trials" / receipt["trial_name"]
        patch = source / "verifier/agent.patch"
        if "KeyError: 'account_id'" not in (source / "verifier/test_output.txt").read_text():
            raise ValueError("Original grade lacks the identified BOM failure")
        csv_bytes = csv_from_patch(patch.read_bytes())
        expected_csv_sha = hashlib.sha256(csv_bytes).hexdigest()
        name = f"wbc-csv-bom-regrade-{arm}"
        trial = await Trial.create(TrialConfig(
            task=TaskConfig(path=copied), trial_name=name, trials_dir=output / "trials",
            agent=AgentConfig(import_path="repair_workbuddy_csv_bom:BOMPatchAgent", model_name=run.MODEL,
                kwargs={"options": {"arm": "native", "patch": str(patch), "original_verifier": str(verifier)}}),
            environment=EnvironmentConfig(
                import_path="workbuddy_bench.runner.docker_environment:WorkBuddyDockerEnvironment",
                mounts=[run.bind(run.RUNTIME, "/opt/codex")], extra_docker_compose=[original / "offline.yaml"]),
            verifier=VerifierConfig(import_path="workbuddy_bench.judge:CompositeVerifier")))
        trial.agent.setup = basic_setup.__get__(trial.agent, type(trial.agent))
        result = (await trial.run()).model_dump(mode="json")
        graded = output / "trials" / name
        if result.get("exception_info") or not result.get("verifier_result"):
            raise RuntimeError("CPU-only official CSV regrade failed")
        if sha(graded / "verifier/agent.patch") != sha(patch):
            raise ValueError("Regrading changed the original actor patch")
        probe = load(graded / "agent/original-probe.json")
        if (probe["exit"] != 1 or "KeyError: 'account_id'" not in probe["stderr"]
                or probe["before_csv_sha256"] != expected_csv_sha or probe["after_csv_sha256"] != expected_csv_sha):
            raise ValueError("The original crash and exact CSV bytes were not reproduced")
        score = load(graded / "verifier/score.json")
        reward = result["verifier_result"]["rewards"]
        if reward["tests_total"] != 13 or score["judges"][0]["status"] in ("build_error", "judge_error"):
            raise ValueError("The original thirteen-check rubric did not finish")
        quality = judge_quality(graded, result)
        if quality["requires_review"]:
            raise ValueError("Corrected grade still contains technical errors")
        target = base / "judge-repairs" / f"021-{arm}-csv-bom-01"
        target.mkdir(mode=0o700, parents=True, exist_ok=False)
        for directory in ("agent", "verifier"):
            shutil.copytree(graded / directory, target / directory)
        shutil.copyfile(graded / "result.json", target / "result.json")
        sources = [receipt_path, patch, source / "verifier/score.json", verifier, corrected,
                   task / "instruction.md", task / "task.toml", script]
        proof = {"repair_kind": "csv_utf8_bom_reader", "item_id": "CSV reader UTF-8 BOM decoding; original thirteen checks",
            "position": 21, "arm": arm, "row": row, "thread": receipt["thread"],
            "source_trial": str(source), "original_reward": receipt["reward"], "reward": reward,
            "actor_artifacts": ["agent.patch"], "original_patch_exact": True,
            "original_evaluation_reproduced": True, "original_csv_sha256": expected_csv_sha,
            "actor_model_calls": 0, "grading_model_calls": 0, "frozen_image_id": row["image_id"],
            "change": "Only official CSV input codec utf-8 to utf-8-sig; CSV/exporter bytes and thirteen predicates unchanged",
            "source_files_sha256": {str(p): sha(p) for p in sources},
            "repair_files_sha256": {str(p.relative_to(target)): sha(p) for p in target.rglob("*") if p.is_file()}}
        write(target / "APPLIED.json", proof)
        repairs.append(proof)
        print(json.dumps({"arm": arm, "reward": reward, "model_calls": 0}), flush=True)
    write(output / "COMPLETE.json", {"repairs": repairs, "actor_model_calls": 0, "grading_model_calls": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("base", "run", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    asyncio.run(repair(args.base, args.run, args.output))
