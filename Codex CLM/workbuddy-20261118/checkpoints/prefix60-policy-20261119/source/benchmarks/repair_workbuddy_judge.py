"""Retry one empty official judge response without redoing the actor or valid verdicts."""

import argparse
import copy
import importlib
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlsplit

from audit_workbuddy import judge_quality, load, sha, trial_key
from relay import Handler, stream_outcome
from run import provider


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def content(raw):
    parts = []
    for line in raw.splitlines():
        if not line.startswith(b"data:") or line[5:].strip() == b"[DONE]":
            continue
        try:
            event = json.loads(line[5:])
        except ValueError:
            continue
        for choice in event.get("choices", []):
            text = (choice.get("delta") or choice.get("message") or {}).get("content")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts).strip()


def prepare(base, run, position, arm, output):
    plan = load(run / "plan.json")
    row = plan["tasks"][position - 1]
    if row["position"] != position or row["domain"] != "web":
        raise ValueError("Repair supports one identified official Web judge failure")
    evidence = run / arm / "evidence" / trial_key(row)
    receipt = load(evidence / "receipt.json")
    if not receipt["accepted"]:
        raise ValueError("Actor must already be complete; this operation never reruns it")
    trial = run / arm / "trials" / receipt["trial_name"]
    old_report = load(trial / "verifier/evidence/eval-report.json")
    store = load(trial / "verifier/evidence/submitted-results.json")
    failed = [v for v in store.values() if (v.get("judge_meta") or {}).get("raw_response_chars") == 0
              and (v.get("judge_meta") or {}).get("judge_path") == "llm"]
    if len(failed) != 1 or failed[0].get("actual") != "LLM returned empty response":
        raise ValueError("Expected precisely one empty judge result, with no semantic verdict")
    item = failed[0]
    sources = []
    for path in sorted((evidence / "wire").glob("*/receipt.json")):
        wire = load(path)
        if wire.get("path") != "/v1/chat/completions":
            continue
        payload = load(path.parent / "request.raw.json")
        if item["id"] in json.dumps(payload.get("messages", [])):
            if content((path.parent / "response.raw").read_bytes()):
                raise ValueError("The selected item already has a nonempty response; manual review required")
            if sha(path.parent / "request.raw.json") != wire["raw_sha256"]:
                raise ValueError("Original failed judge request changed")
            sources.append(path)
    if len(sources) != item["judge_meta"]["empty_response_attempts"] or len({load(p)["raw_sha256"] for p in sources}) != 1:
        raise ValueError("Original empty retries are not bound to one identical request")
    original = sources[0].parent / "request.raw.json"
    payload = load(original)
    if payload.get("model") != "gpt-6.1-sol" or payload.get("stream") is not True:
        raise ValueError("Unexpected official judge model or protocol")
    dataset = Path(plan["reference"]) / "datasets/wb-bench-web-v1.0"
    task = dataset / "tasks" / row["task"]
    shared = dataset / "shared/verifier"
    container = shared / "container/web_verifier"
    submit = module(container / "reporting/submit_result.py", "repair_official_submit")
    verdict = module(container / "llm_judge/verdict.py", "repair_official_verdict")
    finalizer = module(container / "reporting/finalize_eval.py", "repair_official_finalize")
    # Import the official fixed-judge adapter as an isolated package for relative imports.
    spec = importlib.util.spec_from_file_location("repair_official_shared", shared / "__init__.py",
                                                  submodule_search_locations=[str(shared)])
    package = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = package
    spec.loader.exec_module(package)
    profile = importlib.import_module("repair_official_shared.profile")
    scoring = importlib.import_module("repair_official_shared.scoring")
    plan_spec = profile.detect_plan_spec(task)
    runtime_case = load(plan_spec.case_path)
    output.mkdir(mode=0o700, parents=True)
    (output / "verifier/evidence").mkdir(parents=True)
    # Reuse original completion evidence; archived actor artifacts remain unchanged.
    submit.load_runtime_case = lambda: runtime_case
    submit.load_store = lambda: copy.deepcopy(store)
    submit.completion_check = lambda _: copy.deepcopy(old_report["completion_condition"])
    submit._load_judge_pipeline_meta = lambda: old_report.get("judge_pipeline")
    submit.OUTPUT_FILE = output / "verifier/evidence/eval-report.json"
    submit.REWARD_FILE = output / "verifier/reward.txt"
    # Before any API call, prove the unmodified official functions reproduce the old score.
    dimensions, _ = submit.build_dimension_payload(runtime_case, store)
    if dimensions != old_report["dimensions"]:
        raise ValueError("Official reaggregation does not reproduce original item payloads")
    old_score = load(trial / "verifier/score.json")
    old_reward = load(trial / "verifier/raw_reward.json")
    before = scoring.score_from_payloads(task_id=row["task"], spec=plan_spec, raw_reward=old_reward,
             eval_report=old_report, stage_results=old_score["diagnostics"]["stages"],
             raw_reward_path=trial / "verifier/raw_reward.json",
             wall_time_sec=receipt["reward"].get("wall_time_sec"))
    if before.reward_payload() != receipt["reward"]:
        raise ValueError("Official score adapter does not reproduce the original numeric reward")
    tracked = [evidence / "receipt.json", original, trial / "verifier/agent.patch",
               trial / "verifier/agent.workspace.tar.gz", trial / "verifier/score.json",
               trial / "verifier/evidence/submitted-results.json", trial / "verifier/evidence/eval-report.json",
               plan_spec.case_path, container / "reporting/submit_result.py",
               container / "reporting/finalize_eval.py", container / "llm_judge/verdict.py",
               shared / "scoring.py", shared / "profile.py"]
    proof = {"position": position, "arm": arm, "row": row, "thread": receipt["thread"],
             "item_id": item["id"], "original_reward": receipt["reward"],
             "original_empty_attempts": len(sources), "original_request_sha256": sha(original),
             "source_evidence": str(evidence), "source_trial": str(trial),
             "source_files_sha256": {str(p): sha(p) for p in tracked},
             "official_reaggregation_reproduced_original": True, "actor_model_calls": 0}
    write(output / "PREPARED.json", proof)
    shutil.copyfile(original, output / "original-request.json")
    return locals()


def execute(state):
    output, original, item = state["output"], state["original"], state["item"]
    key, base_url = provider()
    handler = object.__new__(Handler)
    handler.path = "/v1/chat/completions"
    handler.server = SimpleNamespace(endpoint=urlsplit(base_url))
    headers = {"Authorization": "Bearer " + key, "Content-Type": "application/json", "Accept-Encoding": "identity"}
    body = original.read_bytes()
    endpoint = handler.server.endpoint.path.rstrip("/")
    target = (endpoint if endpoint.endswith("/v1") else endpoint + "/v1") + "/chat/completions"
    parsed = None
    for number in range(1, 4):
        folder = output / "wire" / f"{number:05d}"
        (folder / "attempts").mkdir(parents=True)
        (folder / "request.raw.json").write_bytes(body)
        (folder / "request.sent.json").write_bytes(body)
        started = time.time_ns()
        attempt = handler.take_attempt(target, headers, body, folder / "attempts/1", True, 1)
        raw = folder / "attempts/1/response.raw"
        if raw.exists():
            shutil.copyfile(raw, folder / "response.raw")
        event = {"path": handler.path, "started_ns": started, "ended_ns": time.time_ns(),
                 "raw_sha256": sha(original), "sent_sha256": sha(original), "attempts": [attempt],
                 **{k: v for k, v in attempt.items() if k in ("status", "eof", "response_sha256", "transport_error", "terminal_sse")}}
        # Keep the outer original clock distinct from the nested HTTP attempt clock.
        event["started_ns"] = started
        event["delivered"] = False
        text = content(raw.read_bytes()) if raw.exists() else ""
        decision, reason = state["verdict"].json_verdict_from_response(text)
        complete = attempt.get("status") == 200 and attempt.get("eof") and stream_outcome(raw, chat=True)[0] == "chat.done"
        if complete and decision in ("pass", "fail"):
            event["delivered"] = True
            parsed = decision, reason, text, folder
        write(folder / "receipt.json", event)
        if parsed:
            break
        if number < 3:
            time.sleep(2 ** number)
    if not parsed:
        raise RuntimeError("Bounded identical-request judge repair still lacks a valid final verdict")
    decision, reason, text, folder = parsed
    store = copy.deepcopy(state["store"])
    meta = {**item["judge_meta"], "raw_response_excerpt": text[:500], "raw_response_chars": len(text),
            "verdict_parse_strategy": "json", "llm_retry_error": "", "fallback_mode": "none",
            "repair_evidence": str(folder), "repair_original_empty_attempts": state["proof"]["original_empty_attempts"]}
    store[item["id"]] = {**item, "status": decision, "source": "llm", "actual": reason, "judge_meta": meta}
    if any(store[k] != state["store"][k] for k in store if k != item["id"]):
        raise ValueError("A valid original verdict changed during repair")
    state["submit"].load_store = lambda: copy.deepcopy(store)
    state["submit"].cmd_generate(SimpleNamespace(app_name=state["old_report"].get("app_name")))
    report = load(output / "verifier/evidence/eval-report.json")
    old = state["old_reward"]["verifier"]
    reward = state["finalizer"].build_reward_payload(report, wall_time=state["old_reward"]["wall_time_sec"],
        **{k: old[k] for k in ("rule_judge_evidence_exit", "rule_judge_exit", "llm_judge_exit", "agent_judge_exit")})
    score = state["scoring"].score_from_payloads(task_id=state["row"]["task"], spec=state["plan_spec"],
        raw_reward=reward, eval_report=report, stage_results=state["old_score"]["diagnostics"]["stages"],
        raw_reward_path=output / "verifier/raw_reward.json", wall_time_sec=state["receipt"]["reward"].get("wall_time_sec"))
    write(output / "verifier/evidence/submitted-results.json", store)
    write(output / "verifier/raw_reward.json", reward)
    write(output / "verifier/score.json", score.to_dict())
    result = {"verifier_result": {"rewards": score.reward_payload()}, "exception_info": None}
    write(output / "result.json", result)
    quality = judge_quality(output, result)
    if quality["requires_review"]:
        raise ValueError("Repaired official judge still has technical findings")
    applied = {**state["proof"], "reward": score.reward_payload(), "verdict": decision,
               "source_actor_artifact_sha256_unchanged": all(sha(Path(p)) == value
                   for p, value in state["proof"]["source_files_sha256"].items()),
               "unchanged_other_verdicts": True, "judge_quality": quality,
               "repair_files_sha256": {str(p.relative_to(output)): sha(p) for p in output.rglob("*") if p.is_file()}}
    if not applied["source_actor_artifact_sha256_unchanged"]:
        raise ValueError("Source artifacts changed during judge repair")
    write(output / "APPLIED.json", applied)
    print(json.dumps({"position": applied["position"], "arm": applied["arm"], "verdict": decision,
                      "original_reward": applied["original_reward"], "reward": applied["reward"], "actor_model_calls": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("position", type=int)
    parser.add_argument("arm", choices=("native", "clm"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    state = prepare(args.base, args.run, args.position, args.arm, args.output)
    if args.execute:
        execute(state)
    else:
        print(json.dumps(state["proof"], ensure_ascii=False))
