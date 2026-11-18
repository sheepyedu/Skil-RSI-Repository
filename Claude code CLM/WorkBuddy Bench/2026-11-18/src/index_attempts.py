"""Export execution outcomes from archived attempts without emitting payloads or credentials."""

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_bytes())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=Path)
    parser.add_argument("category", choices=("pre-formal", "formal"))
    scope = parser.parse_args()
    for run in sorted(scope.experiment.iterdir()):
        is_formal = run.name.startswith("formal-")
        if not (run.is_dir() and (is_formal or run.name.startswith(("pilot-", "plumbing-", "sync-probes")))):
            continue
        if (scope.category == "formal") != is_formal:
            continue
        stages = sorted(run.glob("*/evidence/*/receipt.json"))
        if not stages:
            print(json.dumps({"run": run.name, "terminal_trial_receipts": 0}, separators=(",", ":")))
            continue
        for f in stages:
            trial = load(f)
            requests = []
            for request in sorted((f.parent / "chat-gateway").glob("*/receipt.json")):
                info = load(request)
                usage = info.get("usage") or {}
                requests.append({
                    "attempt": request.parent.name, "status": info.get("http_status"),
                    "disposition": info.get("disposition"), "complete": info.get("complete"),
                    "forwarded": info.get("forwarded"), "finish": info.get("finish_reason"),
                    "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
                    "seconds": info.get("seconds"), "error_kind": (info.get("failure") or {}).get("kind"),
                })
            context = trial["wire"].get("context_events", [])
            event_count = sum(1 for x in context if x.get("edit") == "accepted")
            row = {
                "run": run.name, "position": trial["row"]["position"], "domain": trial["row"]["domain"],
                "task": trial["row"]["task"], "arm": trial["arm"], "accepted": trial["accepted"],
                "exceptions": (trial.get("exception") or {}).get("exception_type"),
                "native_terminal": trial.get("native", {}).get("terminal"),
                "reward": trial.get("reward"), "accepted_context_edits": event_count,
                "actual_prompt_exact": trial["wire"].get("official_instruction_exact"),
                "attempts": requests,
            }
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
