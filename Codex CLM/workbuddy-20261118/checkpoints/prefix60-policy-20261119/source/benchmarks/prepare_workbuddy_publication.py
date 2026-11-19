"""Stage the verified full65 delivery for GitHub, without publishing anything.

Only the exact complete archive and archive-bound reports/source/docs are accepted.
The ZIP remains unchanged; 8 MiB parts fit the qualified GitHub binary channel.
"""

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

from package_workbuddy import load, sha, split_archive, verify_archive


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def stage(export, audit, source, framework, output, upload_plan):
    if output.exists() or upload_plan.exists():
        raise FileExistsError("Publication output and upload plan must be new")
    receipt = load(export / "VERIFIED.json")
    if (receipt.get("private_gpt_key_match_count") != 0
            or not receipt.get("all_chunk_crc_sha_passed")
            or not receipt.get("all_file_recipes_sha_passed")):
        raise ValueError("Complete archive verification and private GPT credential scan are required")
    manifest = load(export / "archive/MANIFEST.json")
    archive_path = export / manifest["archive_name"]
    if (Path(manifest["archive_name"]).name != manifest["archive_name"]
            or archive_path.is_symlink() or not archive_path.is_file()):
        raise ValueError("Expected one complete regular ZIP in the verified export")
    verified = verify_archive(archive_path)
    for key in ("archive_sha256", "archive_bytes", "entries", "logical_bytes", "unique_chunk_bytes"):
        if verified[key] != receipt.get(key):
            raise ValueError(f"Archive verification receipt differs: {key}")
    if (manifest["archive_sha256"] != verified["archive_sha256"]
            or manifest["archive_bytes"] != verified["archive_bytes"]):
        raise ValueError("Original multipart manifest belongs to a different archive")
    with zipfile.ZipFile(archive_path) as archive:
        entries = {entry["path"]: entry for entry in
                   (json.loads(line) for line in archive.read("FILES.jsonl").splitlines())}
        root = verified["root"]

        def bound(path, relative):
            entry = entries.get(root + "/" + relative)
            if (not entry or entry["kind"] != "file" or path.is_symlink()
                    or not path.is_file() or sha(path) != entry["sha256"]):
                raise ValueError(f"Publication file differs from its full-archive evidence: {relative}")
            return entry

        summary = load(audit / "summary.json")
        binding = load(audit / "native-task-binding.json")
        bound(audit / "summary.json", "delivery65/summary.json")
        bound(audit / "native-task-binding.json", "delivery65/native-task-binding.json")
        expected_counts = {"code": 20, "office": 12, "sec": 15, "web": 18}
        expected_order = [(position, arm) for position in range(1, 66) for arm in ("native", "clm")]
        if (summary["groups"]["all"]["pairs"] != 65
                or {k: summary["groups"][k]["pairs"] for k in expected_counts} != expected_counts
                or binding.get("selected_trials_verified") != 130
                or len(binding.get("trials", [])) != 130
                or [(e["position"], e["arm"]) for e in binding["trials"]] != expected_order
                or binding.get("threads") != summary["threads"]
                or len(set(summary["threads"].values())) != 2
                or binding.get("source_sha256") != sha(source / "benchmarks/check_workbuddy_binding.py")
                or binding.get("native_helper_sha256") != sha(source / "benchmarks/provision_workbuddy_cbc.py")
                or not binding.get("all_native_completions_and_task_bindings_verified")):
            raise ValueError("A full65/130 audit on the original two threads is required")
        quality = load(audit / "official-judge-quality.json")
        bound(audit / "official-judge-quality.json", "delivery65/official-judge-quality.json")
        if ([(e["position"], e["arm"]) for e in quality] != expected_order
                or any(item["requires_review"] for item in quality)):
            raise ValueError("Unresolved technical judge errors block publication")
        selected = []
        for folder, destination, archived_prefix in (
                (audit, "results", "delivery65"),
                (source, "source", source.name),
                (framework, "framework", framework.name)):
            for path in sorted(folder.rglob("*")):
                if path.is_symlink():
                    raise ValueError("Visible publication folders must contain regular files")
                if not path.is_file():
                    continue
                relative = path.relative_to(folder).as_posix()
                bound(path, archived_prefix + "/" + relative)
                selected.append((path, destination + "/" + relative))
        for filename in ("restore_workbuddy.py", "package_workbuddy.py"):
            path = source / "benchmarks" / filename
            bound(path, source.name + "/benchmarks/" + filename)
            selected.append((path, filename))
        if not any(destination == "results/REPORT.md" for _, destination in selected):
            raise ValueError("A finished paired report is required")
    output.mkdir(mode=0o700, parents=True)
    for source_path, destination in selected:
        target = output / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        if sha(target) != sha(source_path):
            raise ValueError("Publication copy differs from its verified source")
    # Repartition the same verified ZIP; do not recompress, filter or omit its contents.
    parts = split_archive(archive_path, output, part_size=8 * 1024 * 1024)
    if parts["archive_sha256"] != verified["archive_sha256"]:
        raise ValueError("8 MiB export changed the complete archive")
    shutil.copy2(export / "VERIFIED.json", output / "VERIFIED.json")
    write(output / "DELIVERY.json", {
        "model": "gpt-6.1-sol", "cli": "0.169.0", "reasoning_effort": "low",
        "tasks": 65, "trials": 130, "category_counts": expected_counts,
        "threads": summary["threads"], "archive_sha256": verified["archive_sha256"],
        "archive_bytes": verified["archive_bytes"], "logical_bytes": verified["logical_bytes"],
        "entries": verified["entries"], "parts": len(parts["parts"]),
        "all_original_failures_and_checkpoints_included": True,
        "source_snapshot": source.name, "framework_snapshot": framework.name,
        "archive_verified_again_during_publication_staging": True})
    overall = summary["groups"]["all"]
    readme = f"""# WorkBuddy Bench: native Codex and Codex CLM

65 paired tasks / 130 selected trials, GPT-6.1-sol, Codex CLI 0.169.0, reasoning low.
Each arm uses its original continuous thread. Order: native_i, clm_i, then i+1.
Code20 / Office12 / Security15 / Web18; the original60 prefix is preserved and
five Security tasks are appended in the same order on both original threads.

Native mean reward: {overall['native']['mean_reward']:.4f};
CLM mean reward: {overall['clm']['mean_reward']:.4f}.
These are descriptive results from one continuous chain per arm.

- [Paired report and disclosed limitations](results/REPORT.md)
- [Per-task results](results/paired.csv)
- [Original native turns and actual API input binding](results/native-task-binding.json)
- [Official judge technical audit](results/official-judge-quality.json)
- [Framework, orange modifications and exact injected prompts](framework/FRAMEWORK.md)
- [Implementation and restoration details](source/benchmarks/workbuddy/DELIVERY.md)
- [Full archive multipart manifest](archive/MANIFEST.json)
- [Archive integrity verification](VERIFIED.json)
- [Visible file integrity index](INTEGRITY.json)

The full archive retains all logical paths in the isolated experiment root,
including native/CLM model IO, native sessions, tools, context edits, task outputs,
original and repaired grades, failed attempts, recovery checkpoints, source versions
and public dependency caches. No directory is excluded. Tar layer deduplication
preserves exact original file bytes, headers and padding. Special filesystem objects
are recorded as metadata rather than recreated. See the report for recovery and
scoring corrections; original failures are retained.

Archive SHA-256: `{verified['archive_sha256']}`.
Archive bytes: {verified['archive_bytes']}; original logical bytes: {verified['logical_bytes']}.
The unchanged complete ZIP is distributed as {len(parts['parts'])} parts of at most8MiB.

Download this directory and run:

```bash
python3 restore_workbuddy.py join .
python3 restore_workbuddy.py verify WORKBUDDY_CODEX_65_FULL.zip
python3 restore_workbuddy.py extract WORKBUDDY_CODEX_65_FULL.zip NEW_RESTORE_DIRECTORY
```

Restoration verifies all parts, chunks and reconstructed file bytes. It does not
execute the archived benchmark or binaries. It restores basic modes, timestamps
and links; original uid/gid remain in the inventory, while restored files belong
to the user running restoration.
"""
    (output / "README.md").write_text(readme)
    records = []
    for path in sorted(output.rglob("*")):
        if not path.is_file():
            continue
        content = path.read_bytes()
        records.append({"path": path.relative_to(output).as_posix(), "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "git_blob": hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(),
            "mode": "100755" if path.stat().st_mode & 0o111 else "100644"})
    write(output / "INTEGRITY.json", {"scope": "All visible files except this integrity index",
        "archive_sha256": verified["archive_sha256"], "files": records})
    integrity = output / "INTEGRITY.json"
    content = integrity.read_bytes()
    records.append({"path": "INTEGRITY.json", "bytes": len(content), "sha256": sha(integrity),
        "git_blob": hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest(), "mode": "100644"})
    write(upload_plan, {"repository": "sheepyedu/Skil-RSI-Repository",
        "destination": "Codex CLM/workbuddy-20261118", "local_directory": str(output.resolve()),
        "archive_sha256": verified["archive_sha256"], "files": records,
        "scope": "Staging only; no remote upload or branch update has been performed"})
    print(json.dumps({"visible_files": len(records), "parts": len(parts["parts"]),
        "archive_sha256": verified["archive_sha256"], "output": str(output)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for name in ("export", "audit", "source", "framework", "output", "upload_plan"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    stage(args.export, args.audit, args.source, args.framework, args.output, args.upload_plan)
