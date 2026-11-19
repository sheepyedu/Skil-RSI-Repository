"""Freeze the five additional Security tasks needed for the requested quarter sample."""

import hashlib
import json
from pathlib import Path

from run_pair import stage_task

BASE = Path("/mount-data/Codex-CLM/experiments/workbuddy-codex-20261118")
REF = Path("/mount-data/Claude-code-CLM/experiments/workbuddy-20261118")
NAMES = (
    "bb-bin-int-length-005", "bb-bin-media-parse-008", "bb-bin-parse-crash-006",
    "bb-bin-pdf-parse-009", "bb-bin-dns-parse-010",
)


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    target = BASE / "security-extra"
    target.mkdir(mode=0o700, exist_ok=False)
    pilot = json.loads((BASE / "pilot-07/plan.json").read_text())
    frozen = json.loads((BASE / "formal-11/plan.json").read_text())
    used = {(r["domain"],r["task"]) for r in pilot["tasks"] + frozen["tasks"]}
    rows = []
    for i, name in enumerate(NAMES, 61):
        if ("sec", name) in used:
            raise ValueError("Supplementary sample overlaps an existing trial")
        official = REF / "upstream/datasets/wb-bench-sec-v1.0/tasks" / name
        row = {"domain":"sec","task":name,"position":i,"marker":f"WB_CODEX_FORMAL_{i:03d}",
               "instruction_sha256":sha(official/"instruction.md"),
               "dockerfile_sha256":sha(official/"environment/Dockerfile")}
        staged = stage_task(REF, target, row, None)
        if sha(staged/"instruction.md") != row["instruction_sha256"]:
            raise ValueError("Staging changed the official instruction")
        rows.append(row)
    plan = {"stage":"security-quarter-supplement","tasks":rows,
            "formal_total":65,"formal_counts":{"code":20,"office":12,"sec":15,"web":18},
            "prefix_plan_sha256":sha(BASE/"formal-11/plan.json"),
            "order":"Append the same five tasks to both existing threads after the original 60 tasks"}
    (target/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n")


if __name__ == "__main__":
    main()
