"""Recompute a frozen Web score with exactly one replayed judge verdict."""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tarfile
from argparse import Namespace
from pathlib import Path, PurePosixPath
from unittest.mock import patch


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def checked_completion(case, report, archive, work, official):
    """Run the original artifact checks against the frozen workspace archive."""
    relocated = copy.deepcopy(case)
    mounts = official.mounted_required_outputs(case)
    paths = {}
    hashes = {}
    with tarfile.open(archive, "r:gz") as tar:
        members = {member.name: member for member in tar if member.isfile()}
        for item in report["completion_condition"]["checks"]:
            key = item["path"]
            full_path = item["mounted_path"]
            if item["kind"] != "artifact_exists" or not full_path.startswith("/app/"):
                raise ValueError("Unsupported completion check in the original report")
            if (mounts.get(key) or official.normalize_container_path(key)) != full_path:
                raise ValueError("The completion check no longer points to the original artifact")
            candidate = PurePosixPath(full_path).relative_to("/app")
            if ".." in candidate.parts:
                raise ValueError("Unexpected path in the original artifact contract")
            target = work.joinpath(*candidate.parts)
            paths[key] = str(target)
            if candidate.as_posix() in members:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(tar.extractfile(members[candidate.as_posix()]).read())
                hashes[key] = sha(target)
    relocated.setdefault("verification_resources", {})["mounted_required_outputs"] = paths
    completed = official.completion_check(relocated)
    for item, old in zip(completed["checks"], report["completion_condition"]["checks"], strict=True):
        item["mounted_path"] = old["mounted_path"]
    if completed != report["completion_condition"]:
        raise ValueError("The frozen workspace no longer reproduces the original completion checks")
    return completed, hashes


def recompute(source, replay, modules, criterion):
    sys.path.insert(0, str(modules.resolve()))
    from web_verifier.llm_judge.verdict import json_verdict_from_response
    from web_verifier.reporting import finalize_eval, submit_result

    anchor = read(replay / "source.json")
    if anchor["run"] != source.name:
        raise ValueError("Replay binding and source run differ")
    transport = read(replay / "transport-summary.json")
    if transport["status"] != "closed" or transport["request_sha256"] != anchor["request_sha256"]:
        raise ValueError("Missing complete replay transport")
    position = anchor["position"]
    task = anchor["task"]
    arm = anchor["arm"]
    label = f"{position:03d}-web-{task}"
    if sha(source / "plan.json") != anchor["plan_sha256"]:
        raise ValueError("Frozen plan has changed")
    if sha(source / arm / "evidence" / label / "receipt.json") != anchor["trial_receipt_sha256"]:
        raise ValueError("Frozen attempt receipt has changed")
    verifier = source / arm / "trials" / label / "verifier"
    old_report_path = verifier / "evidence" / "eval-report.json"
    old_store_path = verifier / "evidence" / "submitted-results.json"
    original_report = read(old_report_path)
    initial = read(old_store_path)
    old_item = initial[criterion]
    if old_item["status"] != "fail" or old_item["actual"] != "LLM returned empty response":
        raise ValueError("The selected criterion did not fail for an empty judge response")
    task_root = source / "datasets" / "wb-bench-web-v1.0" / "tasks" / task
    testcases = task_root / "tests" / "web" / "testcases.json"
    cases = [c for c in read(testcases) if c["id"] == original_report["case_id"]]
    if len(cases) != 1:
        raise ValueError("Cannot resolve the archived case uniquely")
    case, = cases
    if case["evaluation_spec"]["identity"] != original_report["evaluation_spec_identity"]:
        raise ValueError("Archived case uses a different evaluation specification")
    if case["dataset_metadata"] != original_report["dataset_metadata"]:
        raise ValueError("Archived case metadata does not match the official report")
    definitions = [item for item in submit_result.scoring_items(case) if item["id"] == criterion]
    if len(definitions) != 1 or definitions[0]["judge_type"] not in {"llm", "vlm"}:
        raise ValueError("Criterion is outside the original LLM/VLM scoring recipe")

    response = (replay / "replayed-response.txt").read_text().strip()
    verdict, reason = json_verdict_from_response(response)
    strategy = "json"
    if verdict is None:
        prefix = re.match(r"^(PASS|FAIL)\b", response, re.IGNORECASE)
        if not prefix:
            raise ValueError("Replayed response contains no explicit official verdict")
        verdict = prefix[1].lower()
        reason = response[prefix.end():].strip(": ")[:200]
        strategy = "prefix_pass_fail"
    if verdict not in {"pass", "fail"}:
        raise ValueError("Unexpected Web judge verdict")

    workspace = replay / "recomputed"
    workspace.mkdir()
    archives = verifier / "agent.workspace.tar.gz"
    completion, asset_hashes = checked_completion(case, original_report, archives, workspace / "workspace", submit_result)

    def rerender(name, store):
        outputs = workspace / name
        outputs.mkdir()
        store_path = outputs / "submitted-results.json"
        report_path = outputs / "eval-report.json"
        write(store_path, store)
        with (
            patch.object(submit_result, "load_runtime_case", return_value=case),
            patch.object(submit_result, "completion_check", return_value=completion),
            patch.object(submit_result, "_load_judge_pipeline_meta", return_value=original_report["judge_pipeline"]),
            patch.object(submit_result, "STORE_FILE", store_path),
            patch.object(submit_result, "OUTPUT_FILE", report_path),
            patch.object(submit_result, "REWARD_FILE", outputs / "reward.txt"),
        ):
            submit_result.cmd_generate(Namespace(app_name=original_report["app_name"]))
        return read(report_path)

    baseline = rerender("original-reconstruction", initial)
    compared = ("case_score", "raw_case_score", "pass_gate", "completion_condition", "dimensions")
    if any(baseline[key] != original_report[key] for key in compared):
        raise ValueError("Original scoring data does not reproduce the published baseline")
    corrected = copy.deepcopy(initial)
    corrected[criterion] = {
        **old_item, "status": verdict, "actual": reason or response[:200],
        "judge_meta": {
            **old_item["judge_meta"], "verdict_parse_strategy": strategy,
            "regrade_request_sha256": anchor["request_sha256"],
            "regrade_response_sha256": transport["attempts"][-1]["response_sha256"],
            "raw_response_chars": len(response),
            "raw_response_excerpt": response[:500],
        },
    }
    corrected_report = rerender("corrected", corrected)
    raw_original = read(verifier / "raw_reward.json")
    original_reward = read(verifier / "reward.json")
    raw_corrected = finalize_eval.build_reward_payload(
        corrected_report, wall_time=raw_original["wall_time_sec"],
        **{key: raw_original["verifier"][key] for key in (
            "rule_judge_evidence_exit", "rule_judge_exit", "llm_judge_exit", "agent_judge_exit",
        )},
    )
    revised = finalize_eval.numeric_reward_payload(raw_corrected)
    counts = corrected_report["dimensions"]["_penalty"]
    revised.update(tests_passed=counts["passed_count"], tests_total=counts["total_count"])
    write(workspace / "corrected" / "raw_reward.json", raw_corrected)
    write(workspace / "corrected" / "reward.json", revised)
    summary = {
        **{k: anchor[k] for k in ("run", "position", "task", "arm", "model", "request_sha256")},
        "criterion": criterion,
        "old_status": old_item["status"],
        "corrected_status": verdict,
        "original_reward": original_reward["reward"],
        "corrected_reward": revised["reward"],
        "tests_passed": revised["tests_passed"], "tests_total": revised["tests_total"],
        "transport_attempts": len(transport["attempts"]),
        "stream": transport["stream"],
        "transport_request_sha256": transport["transport_request_sha256"],
        "response_sha256": transport["attempts"][-1]["response_sha256"],
        "original_report_sha256": sha(old_report_path),
        "original_verifier_reward_sha256": sha(verifier / "reward.json"),
        "original_submission_archive_sha256": sha(archives),
        "frozen_testcases_sha256": sha(testcases),
        "frozen_completion_artifact_sha256": asset_hashes,
        "official_baseline_reproduced": True,
        "criterion_ids_changed": [criterion],
        "corrected_report_sha256": sha(workspace / "corrected" / "eval-report.json"),
        "corrected_reward_sha256": sha(workspace / "corrected" / "reward.json"),
        "official_code_sha256": {
            "submit_result.py": sha(Path(submit_result.__file__)),
            "finalize_eval.py": sha(Path(finalize_eval.__file__)),
        },
    }
    write(replay / "regrade-receipt.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("source", type=Path)
    options.add_argument("replay", type=Path)
    options.add_argument("verifier_modules", type=Path)
    options.add_argument("criterion")
    args = options.parse_args()
    os.umask(0o077)
    recompute(args.source, args.replay, args.verifier_modules, args.criterion)
