"""Preserve the exact selected task files and dataset verifier dependencies, without execution."""

import argparse
import collections
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_text())


def snapshot(base, output):
    groups = [("formal-prefix", base / "formal-14/plan.json"),
              ("pilot", base / "pilot-07/plan.json"),
              ("security-supplement", base / "security-extra/plan.json")]
    selected = {name: load(plan)["tasks"] for name, plan in groups}
    formal = selected["formal-prefix"] + selected["security-supplement"]
    assert collections.Counter(r["domain"] for r in formal) == {"code": 20, "office": 12, "sec": 15, "web": 18}
    formal_keys = {(r["domain"], r["task"]) for r in formal}
    assert len(formal_keys) == 65
    assert collections.Counter(r["domain"] for r in selected["pilot"]) == {"code": 1, "office": 1, "sec": 1, "web": 1}
    assert not formal_keys & {(r["domain"], r["task"]) for r in selected["pilot"]}
    assert [r["position"] for r in formal] == list(range(1, 66))
    output.mkdir(mode=0o700, parents=True)
    manifest, tasks, plans = [], [], []

    def capture(source, destination):
        paths = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
        if source.is_symlink() or any(p.is_symlink() for p in source.rglob("*")):
            raise ValueError(f"Input snapshot requires an explicit mapping for symlinks: {source}")
        before = {p: (p.stat().st_size, p.stat().st_mtime_ns, sha(p)) for p in paths}
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.copy2(source, destination)
        else:
            shutil.copytree(source, destination, symlinks=True)
        for path, (size, modified, expected) in before.items():
            target = destination if source.is_file() else destination / path.relative_to(source)
            if (path.stat().st_size != size or path.stat().st_mtime_ns != modified
                    or sha(path) != expected or sha(target) != expected):
                raise ValueError(f"Source changed or copy differs: {path}")
            manifest.append({"path": str(target.relative_to(output)), "source": str(path),
                             "bytes": size, "sha256": expected})

    for group, plan_path in groups:
        plan = load(plan_path)
        reference = Path(plan.get("reference", plan_path.parent))
        capture(plan_path, output / group / "original-plan.json")
        plans.append({"group": group, "original_plan": str(plan_path), "plan_sha256": sha(plan_path)})
        datasets = set()
        for row in plan["tasks"]:
            dataset = reference / "datasets" / f"wb-bench-{row['domain']}-v1.0"
            task = dataset / "tasks" / row["task"]
            if sha(task / "instruction.md") != row["instruction_sha256"]:
                raise ValueError(f"Selected official instruction no longer matches the plan: {task}")
            if row.get("staged_task_config_sha256") and sha(task / "task.toml") != row["staged_task_config_sha256"]:
                raise ValueError(f"Selected runtime task configuration changed: {task}")
            target = output / group / "datasets" / dataset.name / "tasks" / task.name
            capture(task, target)
            tasks.append({"group": group, "position": row["position"], "domain": row["domain"],
                          "task": row["task"], "snapshot": str(target.relative_to(output)),
                          "instruction_sha256": row["instruction_sha256"],
                          "runtime_dockerfile_sha256": sha(task / "environment/Dockerfile"),
                          "original_dockerfile_sha256_from_plan": row["dockerfile_sha256"],
                          "task_config_sha256": sha(task / "task.toml"),
                          "image": row.get("image"), "image_id": row.get("image_id")})
            datasets.add(dataset)
        for dataset in sorted(datasets):
            destination = output / group / "datasets" / dataset.name
            capture(dataset / "dataset.toml", destination / "dataset.toml")
            if (dataset / "shared").exists():
                capture(dataset / "shared", destination / "shared")
    inventory = output / "FILES.jsonl"
    inventory.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in manifest))
    (output / "TASKS.json").write_text(json.dumps(tasks, ensure_ascii=False, indent=2) + "\n")
    result = {"snapshot_at": datetime.now(timezone.utc).isoformat(), "formal_tasks": 65, "pilot_tasks": 4,
              "source_plans": plans, "input_files": len(manifest),
              "bytes": sum(r["bytes"] for r in manifest), "inventory_sha256": sha(inventory),
              "all_source_and_copy_sha256_matched": True, "model_api_calls": 0,
              "scope": "Selected formal65 and disjoint pilot4 task files, dataset.toml and shared verifier dependencies; original staged runtime files and plans, without modifying execution inputs."}
    (output / "VERIFIED.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (output / "README.md").write_text(
        "# Selected WorkBuddy inputs\n\n"
        "65 formal tasks (reference60 + Security5) and four disjoint pilot tasks. "
        "Each snapshot includes its original plan, selected task directories, dataset.toml "
        "and shared verifier dependencies. FILES.jsonl binds the actual consumed source paths "
        "to copied bytes with SHA256; TASKS.json preserves the instruction, configuration "
        "and original-versus-runtime Dockerfile hashes. Staged mirror/cache adaptations "
        "are retained as used, with the original Dockerfile hash separately identified. "
        "No input was changed and no model API was called.\n\n"
        "Original plans contain absolute server paths; use TASKS.json to locate their "
        "relocated input directories. Images and runtime must be restored/configured before "
        "execution. This input snapshot is separate from trajectory acceptance and final audit.\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    snapshot(args.base, args.output)
