"""Bind official task text to a completed native turn and an actual model request."""

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from provision_workbuddy_cbc import actor_done


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def user_texts(payload):
    for item in payload.get("input", []):
        if item.get("role") != "user":
            continue
        content = item.get("content", [])
        yield content if isinstance(content, str) else "".join(
            x.get("text", "") for x in content if isinstance(x, dict))


def completed_response(path):
    terminal = None
    for line in path.open("rb"):
        if not line.startswith(b"data:"):
            continue
        try:
            event = json.loads(line[5:])
        except (ValueError, UnicodeError):
            continue
        if isinstance(event, dict) and event.get("type") in {
                "response.completed", "response.failed", "response.incomplete", "error"}:
            terminal = event["type"]
    return terminal == "response.completed"


def native_prompt(trial, receipt):
    sent, matched = {}, []
    for line in (trial / "agent/native.jsonl").open():
        event = json.loads(line)
        data = event.get("data") or {}
        if event.get("direction") == "to_codex" and "id" in data:
            sent[data["id"]] = data
        elif event.get("direction") == "from_codex":
            result = data.get("result") or {}
            if (isinstance(result, dict) and isinstance(result.get("turn"), dict)
                    and result["turn"].get("id") == receipt["native"]["turn"]):
                request = sent.get(data.get("id"), {})
                params = request.get("params") or {}
                if request.get("method") != "turn/start" or params.get("threadId") != receipt["thread"]:
                    raise ValueError("Native task turn is not bound to its original start request")
                matched.append("".join(x.get("text", "") for x in params["input"] if x.get("type") == "text"))
    if len(matched) != 1:
        raise ValueError("Expected one native turn/start response for the selected completed turn")
    return matched[0]


def check(run, output, require_full, expected_threads):
    if output.exists():
        raise FileExistsError(output)
    plan = load(run / "plan.json")
    progress = load(run / "progress.json")
    if (not progress or [r["position"] for r in plan["tasks"]] != list(range(1, len(plan["tasks"]) + 1))
            or len({(r["domain"], r["task"]) for r in plan["tasks"]}) != len(plan["tasks"])):
        raise ValueError("Expected a nonempty prefix of unique sequential official questions")
    expected = [(row["position"], arm) for row in plan["tasks"] for arm in ("native", "clm")]
    sequence = [(r["row"]["position"], r["arm"]) for r in progress]
    if sequence != expected[:len(sequence)] or any(not r.get("accepted") for r in progress):
        raise ValueError("Accepted tasks are not the frozen serial prefix")
    if require_full:
        counts = Counter(row["domain"] for row in plan["tasks"])
        if (len(progress) != 130 or len(plan["tasks"]) != 65
                or counts != {"code": 20, "office": 12, "sec": 15, "web": 18}
                or not all(expected_threads.values())):
            raise ValueError("Final verification requires the full65/130 contract and original thread IDs")
        accepted = load(run / "accepted.json")
        if accepted["pairs"] != 65 or accepted["plan_sha256"] != sha(run / "plan.json"):
            raise ValueError("Final acceptance does not match the frozen full65 plan")
    threads, results = {}, []
    by_position = {row["position"]: row for row in plan["tasks"]}
    for progress_receipt in progress:
        arm, row = progress_receipt["arm"], progress_receipt["row"]
        evidence = run / arm / "evidence" / f"{row['position']:03d}-{row['domain']}-{row['task']}"
        receipt = load(evidence / "receipt.json")
        if any(receipt.get(k) != progress_receipt.get(k) for k in (
                "row", "arm", "thread", "native", "trial_name", "accepted", "reward", "session_sha256")):
            raise ValueError("Full evidence receipt differs from the accepted progress record")
        if row != by_position[row["position"]]:
            raise ValueError("Accepted row changed from the frozen question")
        if bool(threads.get(arm)) != receipt["native"]["resumed"]:
            raise ValueError("Unexpected native start/resume transition")
        if (threads.get(arm, receipt["thread"]) != receipt["thread"]
                or expected_threads.get(arm) not in (None, receipt["thread"])):
            raise ValueError("Actor left its original thread")
        threads[arm] = receipt["thread"]
        trial = run / arm / "trials" / receipt["trial_name"]
        actual = actor_done(trial)
        if not actual or actual["thread"] != receipt["thread"] or actual["turn"] != receipt["native"]["turn"]:
            raise ValueError("Actual native completion does not match the selected turn")
        instruction_file = trial / "agent/instruction-source.md"
        instruction = instruction_file.read_bytes().decode("utf-8")
        prefix = "[" + row["marker"] + "]"
        if not instruction.strip() or (require_full and row["marker"] != f"WB_CODEX_FORMAL_{row['position']:03d}"):
            raise ValueError("An official instruction or formal marker is missing")
        prompt_file = trial / "agent/prompt-model.txt"
        prompt = native_prompt(trial, receipt)
        if (sha(instruction_file) != row["instruction_sha256"] or not prompt.startswith(prefix)
                or not prompt.endswith(instruction) or prompt_file.read_bytes().decode("utf-8") != prompt):
            raise ValueError("Completed native turn did not receive the complete official instruction")
        bound = None
        for number, record in enumerate(receipt["wire"]["records"], 1):
            if record.get("path") != "/v1/responses" or not record.get("complete"):
                continue
            directory = evidence / "wire" / f"{number:05d}"
            raw, sent = directory / "request.raw.json", directory / "request.sent.json"
            if sha(raw) != record["raw_sha256"] or sha(sent) != record["sent_sha256"]:
                raise ValueError("Captured model request bytes changed")
            before, after = load(raw), load(sent)
            exact = instruction.rstrip("\n")
            if not all(p.get("model") == "gpt-6.1-sol" for p in (before, after)):
                raise ValueError("Unexpected actor model")
            if not all(any(t.startswith(prefix) and exact in t for t in user_texts(p)) for p in (before, after)):
                continue
            response = directory / "response.raw"
            if sha(response) != record["response_sha256"] or not completed_response(response):
                raise ValueError("Selected task request has no complete successful model response")
            bound = {"wire": str(directory), "started_ns": record["started_ns"],
                     "request_raw_sha256": sha(raw), "request_sent_sha256": sha(sent),
                     "response_sha256": sha(response)}
            break
        if not bound:
            raise ValueError("No actual successful raw/sent model request contains the full current question")
        results.append({"position": row["position"], "domain": row["domain"], "task": row["task"],
            "arm": arm, "marker": row["marker"], "instruction_sha256": sha(instruction_file),
            "native_prompt_sha256": sha(prompt_file), "native_completion": actual, "model_binding": bound})
    if require_full and (len(set(threads.values())) != 2 or threads != accepted["threads"]):
        raise ValueError("Final original two-thread contract does not match acceptance")
    summary = {"scope": "Final65/130 native and model input binding" if require_full else "Stage prefix diagnostic",
        "observed_at": datetime.now().astimezone().isoformat(), "model_api_calls": 0,
        "run": str(run), "selected_trials_verified": len(results), "threads": threads,
        "all_native_completions_and_task_bindings_verified": True,
        "source_sha256": sha(Path(__file__)), "native_helper_sha256": sha(Path(__file__).with_name("provision_workbuddy_cbc.py")),
        "normalization": "Native RPC prompt preserves full UTF-8 instruction; API comparison ignores trailing LF only.",
        "trials": results}
    with output.open("x") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "trials"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--require-full", action="store_true")
    parser.add_argument("--native-thread")
    parser.add_argument("--clm-thread")
    args = parser.parse_args()
    check(args.run, args.output, args.require_full, {"native": args.native_thread, "clm": args.clm_thread})
