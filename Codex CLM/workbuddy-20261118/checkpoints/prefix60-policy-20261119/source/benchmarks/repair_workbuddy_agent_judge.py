"""Regrade missing official interactive items using original actor artifacts only."""

import argparse
import copy
import importlib
import importlib.util
import json
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

from audit_workbuddy import agent_cli_complete, judge_quality, load, sha, trial_key
from repair_workbuddy_judge import module, write
from relay import Wire, MODEL
from run import provider
from provision_workbuddy_cbc import actor_done


def docker(*args, timeout=120):
    return subprocess.check_output(["docker", *map(str, args)], text=True, timeout=timeout).strip()


def prepare(base, run, position, arm, output, seed=None):
    plan = load(run / "plan.json")
    row = next(r for r in plan["tasks"] if r["position"] == position)
    if row["domain"] != "web":
        raise ValueError("Only official Web interactive judge failures are supported")
    evidence = run / arm / "evidence" / trial_key(row)
    receipt = load(evidence / "receipt.json")
    if not receipt["accepted"] or receipt["native"]["native_exit"] != 0:
        raise ValueError("The original actor must already be complete")
    trial = run / arm / "trials" / receipt["trial_name"]
    actor = actor_done(trial)
    if not actor or actor["thread"] != receipt["thread"] or actor["turn"] != receipt["native"]["turn"]:
        raise ValueError("Native actor completion event does not match the accepted receipt")
    old_report = load(trial / "verifier/evidence/eval-report.json")
    old_score = load(trial / "verifier/score.json")
    old_reward = load(trial / "verifier/raw_reward.json")
    store = load(trial / "verifier/evidence/submitted-results.json")
    if old_reward["verifier"]["agent_judge_exit"] != 127:
        raise ValueError("This recovery requires the recorded missing CBC dependency")
    if "cbc CLI not on PATH and auto-install failed" not in (trial / "verifier/agent_judge.log").read_text():
        raise ValueError("The original stage failure is not the missing offline CBC dependency")
    dataset = Path(plan["reference"]) / "datasets/wb-bench-web-v1.0"
    task = dataset / "tasks" / row["task"]
    shared = dataset / "shared/verifier"
    container = shared / "container/web_verifier"
    spec = importlib.util.spec_from_file_location("agent_repair_shared", shared / "__init__.py",
        submodule_search_locations=[str(shared)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    profile = importlib.import_module("agent_repair_shared.profile")
    scoring = importlib.import_module("agent_repair_shared.scoring")
    runtime = importlib.import_module("agent_repair_shared.runtime")
    plan_spec = profile.detect_plan_spec(task)
    runtime_case = load(plan_spec.case_path)
    recipe = runtime_case["evaluation_spec"]["scoring_recipe"]
    items = [x for x in recipe.get("checklist_items", recipe.get("dimension_items", []))
             if x.get("judge_type") == "agent"]
    if not items or any((store.get(x["id"], {}).get("judge_meta") or {}).get("judge") == "agent_judge" for x in items):
        raise ValueError("The selected items must have no previously submitted agent verdicts")
    submit = module(container / "reporting/submit_result.py", "agent_repair_submit")
    finalizer = module(container / "reporting/finalize_eval.py", "agent_repair_finalize")
    dimensions, _ = submit.build_dimension_payload(runtime_case, store)
    if dimensions != old_report["dimensions"]:
        raise ValueError("Unmodified official functions do not reproduce original dimensions")
    before = scoring.score_from_payloads(task_id=row["task"], spec=plan_spec, raw_reward=old_reward,
        eval_report=old_report, stage_results=old_score["diagnostics"]["stages"],
        raw_reward_path=trial / "verifier/raw_reward.json", wall_time_sec=receipt["reward"].get("wall_time_sec"))
    if before.reward_payload() != receipt["reward"]:
        raise ValueError("Official scoring adapter does not reproduce the original reward")
    bundle = base / "cbc-cache/install.tar.gz"
    qualified = load(base / "cbc-cache/QUALIFIED.json")
    if qualified["version"] != "2.109.3" or sha(bundle) != qualified["bundle_sha256"]:
        raise ValueError("Official CBC offline bundle qualification mismatch")
    tracked = [evidence / "receipt.json", trial / "verifier/agent.patch", trial / "verifier/agent.workspace.tar.gz",
        trial / "verifier/evidence/submitted-results.json", trial / "verifier/evidence/eval-report.json",
        trial / "verifier/raw_reward.json", trial / "verifier/score.json", trial / "verifier/agent_judge.log",
        trial / "agent/native-result.json", trial / "agent/native.jsonl", plan_spec.case_path,
        container / "reporting/submit_result.py", container / "reporting/finalize_eval.py",
        shared / "profile.py", shared / "runtime.py", shared / "scoring.py", bundle]
    tracked += sorted((container / "agent_judge").rglob("*.py"))
    seed_store = copy.deepcopy(store)
    reused, reused_files = [], {}
    if seed:
        prior = load(seed / "PREPARED.json")
        if prior["row"] != row or prior["thread"] != receipt["thread"] or prior["source_trial"] != str(trial):
            raise ValueError("Previous partial judge recovery belongs to another actor")
        if load(seed / "workspace-content.json") != load(seed / "workspace-content-after.json"):
            raise ValueError("Prior interactive recovery changed the actor workspace")
        if sha(seed / "verifier/agent.patch") != sha(trial / "verifier/agent.patch"):
            raise ValueError("Prior recovery did not use the original actor patch")
        for filename, expected in prior["source_files_sha256"].items():
            if sha(Path(filename)) != expected:
                raise ValueError("An input to the previous recovery changed")
        previous_store = load(seed / "verifier/evidence/submitted-results.json")
        if any(previous_store.get(k) != v for k, v in store.items()):
            raise ValueError("Prior recovery changed an original valid verdict")
        ids = {i["id"] for i in items}
        if set(previous_store) - set(store) - ids:
            raise ValueError("Prior recovery added an unrelated rubric item")
        for item in items:
            identifier = item["id"]
            value = previous_store.get(identifier, {})
            meta = value.get("judge_meta") or {}
            path = seed / "verifier/agent-judge" / (identifier + ".json")
            verdict = load(path) if path.is_file() else {}
            if (meta.get("judge") == "agent_judge" and meta.get("agent_returncode") == 0
                    and verdict.get("agent_returncode") == 0
                    and verdict.get("verdict") == value.get("status") in ("pass", "fail")
                    and meta.get("model") == verdict.get("model") == MODEL
                    and agent_cli_complete(path.with_suffix(".stream.log"))):
                reused.append(identifier)
                seed_store[identifier] = value
                files = [path, path.with_suffix(".stream.log")]
                for name in verdict.get("evidence_paths", []):
                    local = Path(name)
                    if not local.is_relative_to("/logs/verifier"):
                        raise ValueError("A reused judgment references unpreserved evidence")
                    files.append(seed / "verifier" / local.relative_to("/logs/verifier"))
                for file in files:
                    reused_files[str(file.relative_to(seed))] = sha(file)
        if not reused or len(reused) == len(items):
            raise ValueError("Subset recovery requires both valid prior items and unfinished items")
        tracked += [p for p in seed.rglob("*") if p.is_file()]
    proof = {"position": position, "arm": arm, "row": row, "thread": receipt["thread"],
        "item_id": [x["id"] for x in items], "source_evidence": str(evidence), "source_trial": str(trial),
        "original_reward": receipt["reward"], "actor_model_calls": 0,
        "native_actor_completion": actor,
        "reused_interactive_items": reused, "reused_files_sha256": reused_files,
        "pending_interactive_items": [x["id"] for x in items if x["id"] not in reused],
        "partial_recovery_source": str(seed) if seed else None,
        "official_reaggregation_reproduced_original": True,
        "source_files_sha256": {str(p): sha(p) for p in tracked},
        "scope": "Only missing agent rubric items; all original valid judgments and actor artifacts retained"}
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    shutil.copyfile(Path(__file__), output / "IMPLEMENTATION.py")
    (output / "verifier/evidence").mkdir(parents=True)
    (output / "wire").mkdir()
    if seed:
        shutil.copytree(seed / "verifier/agent-judge", output / "verifier/agent-judge")
    write(output / "initial-store.json", seed_store)
    write(output / "PREPARED.json", proof)
    return locals()


def execute(state):
    base, output, trial = state["base"], state["output"], state["trial"]
    source = base / "source-transport-v4"
    name = "wb-agent-repair-" + output.name
    before_workspace = output / "workspace-content.json"
    after_workspace = output / "workspace-content-after.json"
    fingerprint = ("import hashlib,json,pathlib; root=pathlib.Path('/workspace'); "
        "print(json.dumps({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() "
        "for p in sorted(root.rglob('*')) if p.is_file() and '.git' not in p.relative_to(root).parts "
        "and not str(p.relative_to(root)).startswith(('verify-context/','verify-assets/'))},sort_keys=True))")
    def checked(command, **kwargs):
        return docker("exec", "--workdir", "/workspace", name, "bash", "-c", command, **kwargs)
    key, base_url = provider()
    with tempfile.TemporaryDirectory(prefix="wb-agent-repair-") as tmp:
        socket = Path(tmp) / "responses.sock"
        with Wire(socket, output / "wire", base_url, key, None) as gateway:
            gateway.judge_enabled = True
            worker = threading.Thread(target=gateway.serve_forever, daemon=True)
            worker.start()
            mounts = [(socket, "/gateway/responses.sock", "ro"),
                (source / "benchmarks/workbuddy/loopback.py", "/opt/workbuddy/loopback.py", "ro"),
                (source / "clm/container_entry.py", "/opt/codex-clm/clm/container_entry.py", "ro"),
                (state["task"] / "tests", "/official-tests", "ro"),
                (state["container"], "/official-web-verifier", "ro"),
                (trial / "verifier", "/original-verifier", "ro"),
                (output / "verifier", "/logs/verifier", "rw"),
                (output / "initial-store.json", "/initial-store.json", "ro"),
                (state["bundle"], "/cbc-install.tar.gz", "ro")]
            command = ["create", "--name", name, "--network", "none", "--cpus", "2", "--memory", "4g"]
            for host, target, mode in mounts:
                command += ["--mount", f"type=bind,source={host},target={target},readonly={'true' if mode == 'ro' else 'false'}"]
            env = {"PYTHONPATH": "/tests/web", "PYTHONDONTWRITEBYTECODE": "1",
                "WEB_BENCH_CASE_ID": state["plan_spec"].case_id,
                "WEB_BENCH_JUDGE_MODE": state["plan_spec"].judge_mode,
                "WEB_BENCH_RUNTIME_CASE_PATH": f"/workspace/verify-context/cases/{state['plan_spec'].case_id}.json",
                "WEB_BENCH_VERIFY_CONTEXT_ROOT": "/workspace/verify-context",
                "WEB_BENCH_VERIFY_ASSETS_ROOT": "/workspace/verify-assets",
                "WEB_BENCH_VERIFIER_CONFIG": "/tests/web/verifier.toml",
                "WEB_BENCH_LLM_JUDGE_MODE": "full", "WEB_BENCH_LLM_TIMEOUT_SEC": "1200",
                "WORKBUDDY_VERIFIER_LLM_BASE_URL": "http://127.0.0.1:19731/v1",
                "WORKBUDDY_VERIFIER_LLM_API_KEY": gateway.judge_token,
                "WORKBUDDY_VERIFIER_LLM_MODEL": MODEL}
            for key_name, value in env.items():
                command += ["--env", key_name + "=" + str(value)]
            # Image ID, original task, original artifacts, no actor home and no CLI actor mounts.
            command += [state["row"]["image_id"], "sleep", "infinity"]
            created = False
            try:
                identifier = docker(*command)
                created = True
                docker("start", name)
                checked("cp -a /official-tests /tests; cp -a /official-web-verifier /tests/web/web_verifier")
                patch = "/original-verifier/agent.patch"
                checked(f"git -c safe.directory=/workspace apply --check {patch} && git -c safe.directory=/workspace apply {patch}")
                # Compare every archived changed file to the reconstructed workspace before API use.
                with tarfile.open(trial / "verifier/agent.workspace.tar.gz") as archive:
                    expected = {member.name: __import__('hashlib').sha256(archive.extractfile(member).read()).hexdigest()
                                for member in archive.getmembers() if member.isfile()}
                before_workspace.write_text(checked("python3 -c " + shlex.quote(fingerprint)) + "\n")
                actual = load(before_workspace)
                if any(actual.get(k.removeprefix("./")) != v for k, v in expected.items()):
                    raise ValueError("Restored workspace differs from the original actor archive")
                setup = state["runtime"].setup_command(tests_dir="/tests", verifier_dir="/logs/verifier",
                    case_id=state["plan_spec"].case_id)
                checked(setup)
                if sha(output / "verifier/agent.patch") != sha(trial / "verifier/agent.patch"):
                    raise ValueError("Reconstructed actor patch is not byte identical")
                checked("cp /initial-store.json /app/.eval-results.json; "
                    "tar -xzf /cbc-install.tar.gz -C /opt; ln -s /opt/codebuddy-code/bin/codebuddy /usr/local/bin/cbc; cbc --version")
                write(output / "RESTORED.json", {"container": identifier, "original_patch_exact": True,
                    "all_archived_files_exact": True, "actor_model_calls": 0, "network": "none"})
                checked("python3 /opt/workbuddy/loopback.py > /logs/verifier/loopback.log 2>&1 &")
                for _ in range(50):
                    if checked("if test -f /tmp/workbuddy-relay-ready; then echo ready; fi") == "ready":
                        break
                    time.sleep(0.1)
                else:
                    raise RuntimeError("Judge-only loopback did not become ready")
                started = time.time()
                selection = state["proof"]["pending_interactive_items"]
                wrapper = ("from web_verifier.agent_judge import base; "
                    "from web_verifier.agent_judge.__main__ import main; original=base.scoped_items; "
                    f"base.scoped_items=lambda case:[i for i in original(case) if i['id'] in {selection!r}]; "
                    "raise SystemExit(main())")
                (output / "selected-items-wrapper.py").write_text(wrapper + "\n")
                result = subprocess.run(["docker", "exec", "--workdir", "/workspace", name, "python3", "-c", wrapper],
                    capture_output=True, text=True, timeout=3600)
                (output / "verifier/agent_judge.log").write_text(result.stdout + result.stderr)
                write(output / "AGENT_STAGE.json", {"exit_code": result.returncode, "elapsed_sec": time.time() - started})
                if result.returncode:
                    raise RuntimeError("Official interactive judge failed; logs retained")
                checked("cp /app/.eval-results.json /logs/verifier/evidence/submitted-results.json")
                after_workspace.write_text(checked("python3 -c " + shlex.quote(fingerprint)) + "\n")
                if load(before_workspace) != load(after_workspace):
                    raise ValueError("Interactive judge changed original model files")
                store = load(output / "verifier/evidence/submitted-results.json")
                ids = set(state["proof"]["item_id"])
                if (set(store) - ids != set(state["store"]) - ids
                        or any(store.get(k) != v for k, v in state["store"].items() if k not in ids)):
                    raise ValueError("A previously valid original verdict changed")
                for filename, expected in state["reused_files"].items():
                    if sha(output / filename) != expected:
                        raise ValueError("Previously valid interactive evidence changed")
                for item_id in ids:
                    verdict = load(output / "verifier/agent-judge" / (item_id + ".json"))
                    submitted = store.get(item_id, {})
                    if (verdict["verdict"] not in ("pass", "fail") or verdict["agent_returncode"] != 0
                            or submitted.get("status") != verdict["verdict"]
                            or (submitted.get("judge_meta") or {}).get("judge") != "agent_judge"
                            or verdict["model"] != MODEL
                            or not agent_cli_complete(output / "verifier/agent-judge" / (item_id + ".stream.log"))):
                        raise ValueError("Interactive item did not produce a valid submitted final verdict")
                finalize(state, store)
            finally:
                if created:
                    # Preserve the complete CBC session, configs and tool traces for every outcome.
                    temporary = subprocess.run(["docker", "exec", name, "tar", "-czf",
                        "/logs/verifier/judge-temp-files.tar.gz", "--exclude=tmp/agent-judge-home", "-C", "/", "tmp"],
                        capture_output=True, text=True, timeout=120)
                    (output / "judge-temp-copy.log").write_text(temporary.stdout + temporary.stderr)
                    saved = subprocess.run(["docker", "cp", name + ":/tmp/agent-judge-home", str(output / "judge-home")],
                        capture_output=True, text=True, timeout=120)
                    (output / "judge-home-copy.log").write_text(saved.stdout + saved.stderr)
                    docker("rm", "--force", name)
                gateway.shutdown()
                worker.join(timeout=5)
    # Finalize hashes only after all logs and judge session files are closed.
    applied = load(output / "CANDIDATE.json")
    applied["source_actor_artifact_sha256_unchanged"] = all(sha(Path(p)) == value
        for p, value in state["proof"]["source_files_sha256"].items())
    if not applied["source_actor_artifact_sha256_unchanged"]:
        raise ValueError("An original tracked input changed")
    applied["repair_files_sha256"] = {str(p.relative_to(output)): sha(p) for p in output.rglob("*") if p.is_file()}
    write(output / "APPLIED.json", applied)
    print(json.dumps({"position": applied["position"], "arm": applied["arm"], "reward": applied["reward"],
        "actor_model_calls": 0}), flush=True)


def finalize(state, store):
    output, submit = state["output"], state["submit"]
    submit.load_runtime_case = lambda: state["runtime_case"]
    submit.load_store = lambda: copy.deepcopy(store)
    submit.completion_check = lambda _: copy.deepcopy(state["old_report"]["completion_condition"])
    submit._load_judge_pipeline_meta = lambda: state["old_report"].get("judge_pipeline")
    submit.OUTPUT_FILE = output / "verifier/evidence/eval-report.json"
    submit.REWARD_FILE = output / "verifier/reward.txt"
    submit.cmd_generate(SimpleNamespace(app_name=state["old_report"].get("app_name")))
    report = load(submit.OUTPUT_FILE)
    old = state["old_reward"]["verifier"]
    exits = {k: old[k] for k in ("rule_judge_evidence_exit", "rule_judge_exit", "llm_judge_exit", "agent_judge_exit")}
    exits["agent_judge_exit"] = 0
    reward = state["finalizer"].build_reward_payload(report, wall_time=state["old_reward"]["wall_time_sec"], **exits)
    stages = copy.deepcopy(state["old_score"]["diagnostics"]["stages"])
    replaced = 0
    for stage in stages:
        if stage.get("name") == "agent_judge":
            stage.update(exit_code=0, repair_evidence=str(output / "AGENT_STAGE.json"), original_exit_code=127)
            replaced += 1
    if replaced != 1:
        raise ValueError("Cannot bind exactly one original failed agent stage")
    score = state["scoring"].score_from_payloads(task_id=state["row"]["task"], spec=state["plan_spec"],
        raw_reward=reward, eval_report=report, stage_results=stages,
        raw_reward_path=output / "verifier/raw_reward.json", wall_time_sec=state["receipt"]["reward"].get("wall_time_sec"))
    write(output / "verifier/raw_reward.json", reward)
    write(output / "verifier/score.json", score.to_dict())
    result = {"verifier_result": {"rewards": score.reward_payload()}, "exception_info": None}
    write(output / "result.json", result)
    quality = judge_quality(output, result)
    if quality["requires_review"]:
        raise ValueError("Repaired scoring retains a technical error")
    write(output / "CANDIDATE.json", {**state["proof"], "reward": score.reward_payload(),
        "unchanged_other_verdicts": True, "judge_quality": quality,
        "verdict": {i: store[i]["status"] for i in state["proof"]["item_id"]}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("position", type=int)
    parser.add_argument("arm", choices=("native", "clm"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--seed", type=Path)
    args = parser.parse_args()
    state = prepare(args.base, args.run, args.position, args.arm, args.output, args.seed)
    if args.execute:
        execute(state)
    else:
        print(json.dumps(state["proof"], ensure_ascii=False))
