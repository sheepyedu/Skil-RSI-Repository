"""Apply verified score corrections to a WorkBuddy read-only checkpoint."""

import argparse
import hashlib
import json
from pathlib import Path


def compose(snapshot, ledger):
    if snapshot["plan_sha256"] != ledger["plan_sha256"]:
        raise ValueError("The scoring ledger does not match the frozen task plan")
    corrections = {}
    for correction in ledger["corrections"]:
        key = correction["position"], correction["arm"]
        if key in corrections:
            raise ValueError(f"Duplicate score correction for {key}")
        corrections[key] = correction
    rows = []
    for task in snapshot["closed_trials"]:
        position = task["position"]
        if any(arm["state"] != "accepted" for arm in task["arms"].values()):
            continue
        scores = {}
        for name, trial in task["arms"].items():
            raw = trial["reward"]
            effective = raw
            correction = corrections.pop((position, name), None)
            if correction is not None:
                if (
                    correction["task"] != task["task"]
                    or correction["original_trial_receipt_sha256"] != trial["receipt_sha256"]
                    or correction["original_reward"] != raw
                ):
                    raise ValueError(f"Frozen score origin changed for task {position} {name}")
                effective = correction["corrected_reward"]
            scores[name] = {"raw": raw, "effective": effective, "correction_used": correction is not None}
        rows.append({
            "position": position, "domain": task["domain"], "task": task["task"],
            "scores": scores,
            "effective_paired_difference": round(scores["clm"]["effective"] - scores["native"]["effective"], 6),
        })
    if corrections:
        raise ValueError(f"No accepted receipt for a score correction: {sorted(corrections)}")
    return {
        "observed_at": snapshot["observed_at"], "run": snapshot["run"],
        "plan_sha256": snapshot["plan_sha256"], "completed_pairs": len(rows),
        "total_pairs": snapshot["total_pairs"], "rows": rows,
    }


def load_ledger(path):
    ledger = json.loads(path.read_bytes())
    for correction in ledger["corrections"]:
        receipt_bytes = (path.parent / correction["regrade_receipt"]).read_bytes()
        if hashlib.sha256(receipt_bytes).hexdigest() != correction["regrade_receipt_sha256"]:
            raise ValueError("The correction receipt digest does not match")
        receipt = json.loads(receipt_bytes)
        if not receipt["official_baseline_reproduced"] or any(
            receipt[key] != correction[key] for key in (
                "position", "task", "arm", "criterion", "original_reward", "corrected_reward",
            )
        ):
            raise ValueError("The correction differs from the regrade receipt")
    return ledger


if __name__ == "__main__":
    options = argparse.ArgumentParser()
    options.add_argument("checkpoint", type=Path)
    options.add_argument("corrections", type=Path)
    args = options.parse_args()
    print(json.dumps(compose(
        json.loads(args.checkpoint.read_bytes()), load_ledger(args.corrections),
    ), ensure_ascii=False, indent=2))
