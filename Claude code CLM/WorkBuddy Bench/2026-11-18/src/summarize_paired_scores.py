"""Summarize the full frozen WorkBuddy paired comparison with scope annotations."""

import argparse
import json
import math
from pathlib import Path
from statistics import fmean


def summarise(rows):
    differences = [row["effective_paired_difference"] for row in rows]
    if not rows:
        return {"pairs": 0}
    return {
        "pairs": len(rows),
        "native_mean": round(fmean(row["scores"]["native"]["effective"] for row in rows), 6),
        "clm_mean": round(fmean(row["scores"]["clm"]["effective"] for row in rows), 6),
        "mean_clm_minus_native": round(fmean(differences), 6),
        "clm_higher": sum(delta > 0 for delta in differences),
        "tied": sum(delta == 0 for delta in differences),
        "native_higher": sum(delta < 0 for delta in differences),
    }


def compare(snapshot, annotations):
    rows = snapshot["rows"]
    expected = snapshot["total_pairs"]
    if snapshot["plan_sha256"] != annotations["plan_sha256"]:
        raise ValueError("Analysis annotations belong to a different task plan")
    if len(rows) != expected or [r["position"] for r in rows] != list(range(1, expected + 1)):
        raise ValueError("The final paired report requires the complete ordered sample")
    for row in rows:
        scores = row["scores"]
        if not all(math.isfinite(trial["effective"]) for trial in scores.values()):
            raise ValueError("An official pair has a non-finite score")
        difference = round(scores["clm"]["effective"] - scores["native"]["effective"], 6)
        if difference != row["effective_paired_difference"]:
            raise ValueError("The stored paired difference does not match its scores")

    domain_results = {
        domain: summarise([r for r in rows if r["domain"] == domain])
        for domain in dict.fromkeys(row["domain"] for row in rows)
    }
    flags = annotations["flags"]
    flagged = {flag["position"] for flag in flags}
    phases = annotations["shared_output_budget_phases"]
    boundaries = [phase["from_position"] for phase in phases]
    if not boundaries or boundaries[0] != 1 or boundaries != sorted(set(boundaries)):
        raise ValueError("Output budget changes must be ordered from the first task")
    cohorts = []
    for phase, stop in zip(phases, boundaries[1:] + [expected + 1], strict=True):
        first = phase["from_position"]
        cohorts.append({
            "first_position": first, "last_position": stop - 1,
            "shared_output_budget": phase["tokens"],
            **summarise([r for r in rows if first <= r["position"] < stop]),
        })
    return {
        "observed_at": snapshot["observed_at"], "run": snapshot["run"],
        "plan_sha256": snapshot["plan_sha256"],
        "all_pairs": summarise(rows),
        "by_domain": domain_results,
        "output_budget_cohorts": cohorts,
        "clm_replay_policy_changes": annotations.get("clm_replay_policy_changes", []),
        "regraded_positions": [
            r["position"] for r in rows if any(trial["correction_used"] for trial in r["scores"].values())
        ],
        "operator_or_transport_flags": flags,
        "sensitivity_excluding_flagged_pairs": summarise([r for r in rows if r["position"] not in flagged]),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("effective_scores", type=Path)
    parser.add_argument("intervention_and_transport_flags", type=Path)
    args = parser.parse_args()
    report = compare(
        json.loads(args.effective_scores.read_bytes()),
        json.loads(args.intervention_and_transport_flags.read_bytes()),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
