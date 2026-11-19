"""Exercise publication integrity gates with real wire bytes and explicit CPU fixtures.

Synthetic 65/130 metadata below is test data, never a completed experiment claim.
No model/API calls, uploads or branch changes occur.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from package_workbuddy import make_archive, sha, split_archive, verify_archive
from prepare_workbuddy_publication import stage, write
from restore_workbuddy import join_parts


def check(sample):
    checks = []
    with tempfile.TemporaryDirectory(prefix="wb-publication-cpu-") as tmp:
        root = Path(tmp)
        base = root / "workbuddy-codex-CPU_FIXTURE_ONLY"
        audit, source, framework = base / "delivery65", base / "source-fixture", base / "framework-fixture"
        for path in (audit, source / "benchmarks", framework):
            path.mkdir(parents=True)
        here = Path(__file__).parent
        for name in ("check_workbuddy_binding.py", "provision_workbuddy_cbc.py", "package_workbuddy.py", "restore_workbuddy.py"):
            shutil.copy2(here / name, source / "benchmarks" / name)
        (framework / "FRAMEWORK.md").write_text("CPU fixture only\n")
        (audit / "REPORT.md").write_text("CPU fixture; not scientific results\n")
        shutil.copyfile(sample / "response.raw", audit / "captured-wire-bytes.raw")
        counts = {"code": 20, "office": 12, "sec": 15, "web": 18}
        threads = {"native": "CPU-native-fixture", "clm": "CPU-clm-fixture"}
        summary = {"threads": threads, "groups": {k: {"pairs": v} for k, v in counts.items()}}
        summary["groups"]["all"] = {"pairs": 65, "native": {"mean_reward": 0.5}, "clm": {"mean_reward": 0.5}}
        order = [{"position": i, "arm": arm} for i in range(1, 66) for arm in ("native", "clm")]
        binding = {"CPU_FIXTURE_ONLY": True, "selected_trials_verified": 130,
            "all_native_completions_and_task_bindings_verified": True, "threads": threads, "trials": order,
            "source_sha256": sha(source / "benchmarks/check_workbuddy_binding.py"),
            "native_helper_sha256": sha(source / "benchmarks/provision_workbuddy_cbc.py")}
        write(audit / "summary.json", summary)
        write(audit / "native-task-binding.json", binding)
        write(audit / "official-judge-quality.json", [{**e, "requires_review": False} for e in order])

        def export(number):
            folder = root / f"export-{number}"
            folder.mkdir()
            archive = folder / "WORKBUDDY_CODEX_65_FULL.zip"
            make_archive(base, archive, secrets=[b"CPU-fixture-private-canary-0123456789"])
            result = verify_archive(archive)
            write(folder / "VERIFIED.json", {**result, "private_gpt_key_match_count": 0, "CPU_FIXTURE_ONLY": True})
            split_archive(archive, folder, part_size=8192)
            return folder

        initial = export(1)
        output, plan = root / "staged", root / "UPLOAD_PLAN.json"
        stage(initial, audit, source, framework, output, plan)
        assert sha(join_parts(output)) == sha(initial / "WORKBUDDY_CODEX_65_FULL.zip")
        assert sha(output / "results/captured-wire-bytes.raw") == sha(sample / "response.raw")
        for entry in json.loads(plan.read_text())["files"]:
            assert sha(output / entry["path"]) == entry["sha256"]
        checks.append("unchanged complete ZIP, 8 MiB export and all visible-file checksums roundtrip")
        (audit / "REPORT.md").write_text("changed after full-archive verification\n")

        def rejected(folder, number):
            target = root / f"refused-{number}"
            try:
                stage(folder, audit, source, framework, target, root / f"refused-{number}.json")
            except ValueError:
                assert not target.exists()
            else:
                raise AssertionError("Incomplete or changed delivery was accepted")

        rejected(initial, 2)
        checks.append("refuse a report changed after the complete archive was verified")
        binding["trials"] = [order[0]] * 130
        write(audit / "native-task-binding.json", binding)
        rejected(export(3), 3)
        checks.append("refuse numeric130 metadata with duplicated native/API task bindings")
        binding["trials"] = order
        write(audit / "native-task-binding.json", binding)
        quality = [{**e, "requires_review": False} for e in order]
        quality[-1]["requires_review"] = True
        write(audit / "official-judge-quality.json", quality)
        rejected(export(4), 4)
        checks.append("refuse complete-count metadata with an unresolved technical judge failure")
    return {"passed": True, "checks": checks, "count": len(checks), "model_api_calls": 0,
        "scope": "CPU fixtures with copied real wire bytes; not a full65 experiment or publication",
        "sample_response_sha256": sha(sample / "response.raw")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("sample", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = check(args.sample)
    write(args.output, result)
    print(json.dumps(result, ensure_ascii=False))
