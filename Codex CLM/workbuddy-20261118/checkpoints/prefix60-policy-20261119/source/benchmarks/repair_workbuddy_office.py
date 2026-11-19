"""Regrade task 49's exact original patches after a strict artifact_refs type guard.

No actor or judge model is invoked. Missing dataset fixtures remain missing and fail.
The copied official evaluator changes only the unchecked dict.values access and its
existing atomic predicate: a non-dict artifact_refs always fails that predicate.
"""

import argparse
import asyncio
import json
import shutil
import shlex
from pathlib import Path

from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig, VerifierConfig
from harbor.trial.trial import Trial

from agent import SerialCodex
from audit_workbuddy import judge_quality, load, sha, trial_key
from regrade_workbuddy_code import basic_setup
from repair_workbuddy_judge import write
import run


ACCESS = '    artifact_refs = set(str(value) for value in _get(evidence_log, ["artifact_refs"], {}).values() if isinstance(value, str))'
GUARD = '''    artifact_refs_raw = _get(evidence_log, ["artifact_refs"], {})
    artifact_refs_is_mapping = isinstance(artifact_refs_raw, dict)
    artifact_refs = set(str(value) for value in (artifact_refs_raw.values() if artifact_refs_is_mapping else []) if isinstance(value, str))'''
PREDICATE = '"artifact_refs_consistent", not missing_artifact_refs and not unresolved_artifact_refs,'
STRICT = '"artifact_refs_consistent", artifact_refs_is_mapping and not missing_artifact_refs and not unresolved_artifact_refs,'


def guarded(text):
    if text.count(ACCESS) != 1 or text.count(PREDICATE) != 1:
        raise ValueError("The frozen official evaluator does not match the identified defect")
    return text.replace(ACCESS, GUARD).replace(PREDICATE, STRICT)


def comparable_failures(checks):
    result = []
    for check in checks:
        if check.get("passed") is True:
            continue
        item = {k: check[k] for k in ("name", "group", "detail")}
        # The official check renders a Python set as a list. Its display order
        # varies between interpreter processes; preserve every value and verdict.
        if item["name"] == "runtime_selected_profiles_inspected":
            if not isinstance(item["detail"], list) or not all(isinstance(v, str) for v in item["detail"]):
                raise ValueError("Unexpected runtime profile diagnostic shape")
            item["detail"] = sorted(item["detail"])
        result.append(item)
    return result


class OfficePatchAgent(SerialCodex):
    async def run(self, instruction, environment, context):
        for source, target in [(self.options["patch"], "/tmp/original-agent.patch"),
                               (self.options["original_eval"], "/tmp/original-eval.py"),
                               (self.options["gold"], "/tmp/original-gold.json")]:
            await environment.upload_file(Path(source), target)
            result = await self.exec_as_root(environment, "chmod 644 " + shlex.quote(target))
            if result.return_code:
                raise RuntimeError("CPU grading input transfer failed")
        result = await environment.exec(command="git apply --check /tmp/original-agent.patch && git apply /tmp/original-agent.patch")
        (self.logs_dir / "patch-restore.txt").write_text(f"{result.stdout}\n{result.stderr}\n")
        if result.return_code:
            raise RuntimeError("Original actor patch does not apply to the frozen image")
        probe = '''import importlib.util,json,traceback
s=importlib.util.spec_from_file_location('original_eval','/tmp/original-eval.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
try:
 r={'result':m.evaluate('/workspace','/tmp/original-gold.json')}
except Exception as e:
 r={'exception':repr(e),'traceback':traceback.format_exc()}
print(json.dumps(r,ensure_ascii=False))'''
        result = await environment.exec(command="python3 -c " + shlex.quote(probe))
        (self.logs_dir / "original-evaluation.stdout").write_text(result.stdout or "")
        (self.logs_dir / "original-evaluation.stderr").write_text(result.stderr or "")
        if result.return_code:
            raise RuntimeError("Original deterministic evaluator probe did not finish")
        capture = '''import hashlib,json,pathlib
r=pathlib.Path('/workspace')
print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(r.rglob('*')) if p.is_file() and '.git' not in p.relative_to(r).parts},sort_keys=True))'''
        result = await environment.exec(command="python3 -c " + shlex.quote(capture))
        if result.return_code:
            raise RuntimeError("Restored workspace fingerprint failed")
        (self.logs_dir / "original-workspace-sha256.json").write_text(result.stdout)


async def repair(base, original, output, reuse=False):
    if not reuse:
        output.mkdir(mode=0o700, parents=True, exist_ok=False)
    plan = load(original / "plan.json")
    row = plan["tasks"][48]
    if (row["position"], row["domain"], row["task"]) != (49, "office", "recruiting-search-skill-mock-mcp-hardened"):
        raise ValueError("Only the identified task49 failure is supported")
    task = run.task_dir(Path(plan["reference"]), row)
    original_eval = task / "tests/grading/eval_core.py"
    gold = task / "tests/gold/gold_answer.json"
    dataset = output / "dataset"
    copied = dataset / "tasks" / row["task"]
    if not reuse:
        dataset.mkdir()
        shutil.copy2(task.parent.parent / "dataset.toml", dataset / "dataset.toml")
        shutil.copytree(task.parent.parent / "shared", dataset / "shared", symlinks=True)
        shutil.copytree(task, copied, symlinks=True)
        (copied / "tests/grading/eval_core.py").write_text(guarded(original_eval.read_text()))
        write(output / "CHANGE.json", {"original_evaluator": str(original_eval),
        "original_sha256": sha(original_eval), "corrected_sha256": sha(copied / "tests/grading/eval_core.py"),
        "changes": ["guard dict.values access", "wrong JSON type fails existing artifact_refs_consistent check"],
        "rubric_checks_added_or_removed": 0, "model_outputs_changed": False,
            "fixtures_injected": [], "actor_model_calls": 0, "grading_model_calls": 0})
    elif (copied / "tests/grading/eval_core.py").read_text() != guarded(original_eval.read_text()):
        raise ValueError("Previously corrected evaluator changed")
    repairs = []
    for arm in run.ARMS:
        receipt_path = original / arm / "evidence" / trial_key(row) / "receipt.json"
        receipt = load(receipt_path)
        if not receipt["accepted"] or receipt["row"] != row:
            raise ValueError("The original actor must be complete")
        source = original / arm / "trials" / receipt["trial_name"]
        patch = source / "verifier/agent.patch"
        name = f"wbc-office-type-guard-{arm}"
        target = base / "judge-repairs" / f"049-{arm}-type-guard-01"
        if reuse and (target / "APPLIED.json").exists():
            existing = load(target / "APPLIED.json")
            for filename, expected in existing["source_files_sha256"].items():
                if sha(Path(filename)) != expected:
                    raise ValueError("Previously applied repair source changed")
            for filename, expected in existing["repair_files_sha256"].items():
                if sha(target / filename) != expected:
                    raise ValueError("Previously applied repair evidence changed")
            repairs.append(existing)
            continue
        graded = output / "trials" / name
        if reuse:
            result = load(graded / "result.json")
        else:
            trial = await Trial.create(TrialConfig(
            task=TaskConfig(path=copied), trial_name=name, trials_dir=output / "trials",
            agent=AgentConfig(import_path="repair_workbuddy_office:OfficePatchAgent", model_name=run.MODEL,
                kwargs={"options": {"arm": "native", "patch": str(patch),
                    "original_eval": str(original_eval), "gold": str(gold)}}),
            environment=EnvironmentConfig(
                import_path="workbuddy_bench.runner.docker_environment:WorkBuddyDockerEnvironment",
                mounts=[run.bind(run.RUNTIME, "/opt/codex")], extra_docker_compose=[original / "offline.yaml"]),
            verifier=VerifierConfig(import_path="workbuddy_bench.judge:CompositeVerifier")))
            trial.agent.setup = basic_setup.__get__(trial.agent, type(trial.agent))
            result = (await trial.run()).model_dump(mode="json")
        if result.get("exception_info") or not result.get("verifier_result"):
            raise RuntimeError(f"CPU-only official regrade failed: {arm}")
        if sha(graded / "verifier/agent.patch") != sha(patch):
            raise ValueError("Reconstructed patch differs from the original actor patch")
        before = load(graded / "agent/original-evaluation.stdout")
        quality = judge_quality(graded, result)
        if quality["requires_review"]:
            raise ValueError("Corrected deterministic evaluator retains a technical failure")
        score = load(graded / "verifier/score.json")
        raw = score["judges"][0]["metadata"]["raw"]
        failed = {c["name"] for c in raw["failed_checks"]}
        if raw["total_count"] != 134:
            raise ValueError("The frozen 134-check rubric changed")
        if arm == "native":
            if (before.get("exception") != 'AttributeError("\'list\' object has no attribute \'values\'")'
                    or "line 556" not in before.get("traceback", "")
                    or "artifact_refs_consistent" not in failed):
                raise ValueError("Original crash or strict malformed-shape failure was not reproduced")
        else:
            old = load(source / "verifier/score.json")["judges"][0]["metadata"]["raw"]
            if (before["result"]["passed_count"] != old["passed_count"]
                    or before["result"]["total_count"] != old["total_count"]
                    or comparable_failures(before["result"]["checks"]) != comparable_failures(old["failed_checks"])):
                raise ValueError("Restored CLM artifacts do not reproduce the original official score")
            if (comparable_failures(raw["failed_checks"]) != comparable_failures(old["failed_checks"])
                    or result["verifier_result"]["rewards"] != receipt["reward"]):
                raise ValueError("Type guard changed a previously valid CLM verdict")
        missing = {"parse_case_yaml", "protected_hash_case_yaml", "protected_hash_instruction_md",
                   "case_yaml_case_id", "case_yaml_skill_mcp_text_only_wb_judge_metadata"}
        if not missing.issubset(failed):
            raise ValueError("Missing dataset fixture failures were incorrectly removed")
        target.mkdir(mode=0o700, parents=True, exist_ok=False)
        shutil.copytree(graded / "verifier", target / "verifier")
        shutil.copytree(graded / "agent", target / "agent")
        shutil.copyfile(graded / "result.json", target / "result.json")
        sources = [receipt_path, patch, source / "verifier/score.json", original_eval, gold,
                   task / "environment/workspace.tar.gz", copied / "tests/grading/eval_core.py",
                   Path(__file__).resolve(), output / "CHANGE.json"]
        proof = {"repair_kind": "office_artifact_refs_type_guard", "position": 49, "arm": arm,
            "row": row, "thread": receipt["thread"], "source_trial": str(source),
            "original_reward": receipt["reward"], "reward": result["verifier_result"]["rewards"],
            "actor_artifacts": ["agent.patch"], "original_patch_exact": True,
            "original_evaluation_reproduced": True, "actor_model_calls": 0, "grading_model_calls": 0,
            "diagnostic_display_order": "Only runtime_selected_profiles_inspected's set-derived detail list is sorted for comparison; all values and verdicts preserved",
            "missing_fixture_failures_preserved": sorted(missing), "rubric_checks": 134,
            "source_files_sha256": {str(p): sha(p) for p in sources},
            "repair_files_sha256": {str(p.relative_to(target)): sha(p) for p in target.rglob("*") if p.is_file()}}
        write(target / "APPLIED.json", proof)
        repairs.append(proof)
        print(json.dumps({"arm": arm, "reward": proof["reward"], "model_calls": 0}), flush=True)
    write(output / "COMPLETE.json", {"repairs": repairs, "actor_model_calls": 0, "grading_model_calls": 0})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--finalize-existing", action="store_true",
                        help="Validate completed CPU trials without repeating grading or actor work")
    args = parser.parse_args()
    asyncio.run(repair(args.base, args.run, args.output, args.finalize_existing))
