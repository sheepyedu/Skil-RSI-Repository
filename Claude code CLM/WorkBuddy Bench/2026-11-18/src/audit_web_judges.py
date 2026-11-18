"""Audit Web judge closure and flag grade-affecting upstream failures."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from inspect_run import response_closed


def read(path):
    return json.loads(path.read_bytes())


def calls_for_trial(evidence):
    groups = defaultdict(list)
    for metadata in sorted((evidence / "wire").glob("*/metadata.json")):
        event = read(metadata)
        if event.get("actor") != "judge":
            continue
        request = metadata.with_name("request.upstream.json").read_bytes()
        response = metadata.with_name("response.raw")
        closed = bool(
            event.get("http_status") == 200 and event.get("transport") == "eof"
            and response.is_file() and response_closed(response)
        )
        groups[hashlib.sha256(request).hexdigest()].append(
            {"attempt": metadata.parent.name, "http_status": event.get("http_status"), "closed": closed},
        )
    return groups


def formal_web_scores(run, correction_ledger):
    resolved = {(c["position"], c["arm"], c["criterion"]) for c in correction_ledger.get("corrections", [])}
    plan = read(run / "plan.json")
    rows = []
    for case in plan["tasks"]:
        if case["domain"] != "web":
            continue
        position = case["position"]
        label = f"{position:03d}-web-{case['task']}"
        for arm in ("native", "clm"):
            evidence = run / arm / "evidence" / label
            if not (evidence / "receipt.json").is_file():
                continue
            verifier = run / arm / "trials" / label / "verifier"
            summary_path = verifier / "evidence" / "eval-report.json"
            results_path = verifier / "evidence" / "submitted-results.json"
            if not summary_path.is_file() or not results_path.is_file():
                rows.append({"position": position, "arm": arm, "state": "missing_official_judge_artifacts"})
                continue
            report = read(summary_path)
            calls = calls_for_trial(evidence)
            unclosed = {key: group for key, group in calls.items() if not any(c["closed"] for c in group)}
            adverse = []
            for criterion, item in read(results_path).items():
                meta = item.get("judge_meta") or {}
                if item.get("status") != "fail" or not (
                    item.get("actual") == "LLM returned empty response" or meta.get("fallback_mode") == "llm_api_error"
                ):
                    continue
                adverse.append({"criterion": criterion, "regraded": (position, arm, criterion) in resolved})
            rows.append({
                "position": position, "task": case["task"], "arm": arm, "raw_reward": report.get("case_score"),
                "expected_llm_criteria": (report.get("judge_pipeline") or {}).get("llm_item_count"),
                "judge_attempts": sum(len(group) for group in calls.values()),
                "closed_attempts": sum(attempt["closed"] for group in calls.values() for attempt in group),
                "recovered_request_groups": sum(
                    len(group) > 1 and any(a["closed"] for a in group) and any(not a["closed"] for a in group)
                    for group in calls.values()
                ),
                "unclosed_request_groups": unclosed, "grade_affecting_judge_failures": adverse,
            })
    return {"run": run.name, "rows": rows}


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("run", type=Path)
    options.add_argument("--corrections", type=Path)
    args = options.parse_args()
    corrections = read(args.corrections) if args.corrections else {}
    print(json.dumps(formal_web_scores(args.run, corrections), ensure_ascii=False, indent=2))
