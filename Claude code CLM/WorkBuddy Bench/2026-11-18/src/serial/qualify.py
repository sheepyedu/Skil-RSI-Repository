"""Verify the complete matched pilot and freeze the image identity of every formal task."""

import argparse
import json
import subprocess
import tomllib
from pathlib import Path

from audit_run import audit
from run_pair import CLI_MODEL, JUDGE_MODEL, DOMAINS, contains_instruction, sha
from wire import write_json


def image_identity(image):
    response = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        text=True, capture_output=True, check=False,
    )
    return response.stdout.strip() if response.returncode == 0 else None


def main(pilot, formal, output):
    qualification = audit(pilot)
    plan_path = pilot / "plan.json"
    pilot_done = json.loads((pilot / "accepted.json").read_text())
    plan = json.loads(plan_path.read_text())
    if (
        qualification["accepted_pairs"] != len(DOMAINS) or pilot_done["pairs"] != len(DOMAINS)
        or pilot_done["plan_sha256"] != sha(plan_path)
        or [row["domain"] for row in plan["tasks"]] != list(DOMAINS)
        or qualification["sessions"]["model"] != CLI_MODEL
        or qualification["sessions"]["judge_model"] != JUDGE_MODEL
    ):
        raise ValueError("Four-domain paired pilot is incomplete or incompatible")
    for row in plan["tasks"]:
        label = f"{row['position']:03d}-{row['domain']}-{row['task']}"
        instruction_path = pilot / "datasets" / f"wb-bench-{row['domain']}-v1.0" / "tasks" / row["task"] / "instruction.md"
        instruction = instruction_path.read_text()
        for arm in ("native", "clm"):
            evidence = pilot / arm / "evidence" / label / "chat-gateway"
            complete = (
                path.parent for path in sorted(evidence.glob("*/receipt.json"))
                if json.loads(path.read_text())["complete"]
            )
            found = False
            for path in complete:
                provider_input = json.loads((path / "request.raw").read_bytes())
                if contains_instruction(provider_input["messages"], row["marker"], instruction):
                    found = True
                    break
            if not found:
                raise ValueError(f"Exact provider input missing for {arm} {label}")
    formal_plan_path = formal / "plan.json"
    formal_plan = json.loads(formal_plan_path.read_text())
    pilot_tasks = {row["task"] for row in plan["tasks"]}
    formal_tasks = {row["task"] for row in formal_plan["tasks"]}
    if (
        len(formal_tasks) != 60 or len(formal_plan["tasks"]) != 60
        or pilot_tasks & formal_tasks or formal_plan["chosen_totals"] != formal_plan["declared_formal_quota"]
    ):
        raise ValueError("Formal sample and pilot are not disjoint and complete")
    images = []
    missing = []
    for row in formal_plan["tasks"]:
        task = formal / "datasets" / f"wb-bench-{row['domain']}-v1.0" / "tasks" / row["task"]
        if sha(task / "instruction.md") != row["instruction_sha256"]:
            raise ValueError(f"Instruction changed: {row['task']}")
        data = tomllib.loads((task / "task.toml").read_text())
        tag = data["environment"].get("docker_image")
        ident = image_identity(tag) if tag else None
        if ident:
            images.append({"position": row["position"], "image": tag, "id": ident})
        else:
            missing.append(row["position"])
    if missing:
        print(json.dumps({"image_count": len(images), "missing_positions": missing}))
        return 2
    code = Path(__file__).resolve().parent
    framework = Path("/mount-data/Claude-code-CLM")
    pinned = [
        *(code / name for name in ("run_pair.py", "serial_agent.py", "wire.py", "resume_projection.py", "settings.json")),
        framework / "runtime" / "claude",
        framework / "clm" / "context.py",
        framework / "experiments/clbench100-20261117/framework/skillrl/chat_gateway.py",
    ]
    write_json(output, {
        "pilot_plan_sha256": sha(plan_path), "formal_plan_sha256": sha(formal_plan_path),
        "pilot_audit": qualification, "images": images,
        "runtime_sha256": {str(path): sha(path) for path in pinned},
    })
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pilot", type=Path)
    parser.add_argument("formal", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(main(args.pilot, args.formal, args.output))
