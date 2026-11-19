"""Restore the single reviewed patch from task 006 with the original Codex patch engine."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

FILES = (
    Path("/workspace/dynaconf/loaders/base.py"),
    Path("/workspace/dynaconf/loaders/__init__.py"),
    Path("/workspace/dynaconf/base.py"),
)
OBSERVATION_COMMAND = (
    'grep -n "loader.load(" dynaconf/loaders/{json,toml,yaml,ini}_loader.py; '
    "sed -n '55,85p' dynaconf/loaders/yaml_loader.py; "
    "sed -n '45,75p' dynaconf/loaders/ini_loader.py"
)


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(directory, output):
    data = json.loads((directory / "native-patch.json").read_text())
    patch = data["patch"]
    declared = [line.removeprefix("*** Update File: ") for line in patch.splitlines()
                if line.startswith("*** Update File: ")]
    if declared != [str(path) for path in FILES]:
        raise ValueError("The patch differs from the reviewed three-file update")
    if any(line.startswith(("*** Add File:", "*** Delete File:", "*** Move to:")) for line in patch.splitlines()):
        raise ValueError("Unsupported extra operation in the reviewed recovery patch")
    before = {str(path): fingerprint(path) for path in FILES}
    result = subprocess.run(
        ["/opt/codex/bin/codex", "--codex-run-as-apply-patch", patch],
        cwd="/workspace", capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError(f"Original Codex patch engine failed: {result.stderr}")
    observation = subprocess.run(
        ["/bin/bash", "-c", OBSERVATION_COMMAND], cwd="/workspace",
        capture_output=True, text=True, check=True,
    )
    recorded = json.loads((directory / "postpatch-observation.json").read_text())["output"]
    expected = "".join(part["text"] for part in recorded[1:] if part.get("type") == "input_text")
    if observation.stdout.rstrip("\n") != expected.rstrip("\n"):
        raise ValueError("Restored workspace differs from the last completed native observation")
    after = {str(path): fingerprint(path) for path in FILES}
    if any(before[name] == after[name] for name in before):
        raise ValueError("The reviewed patch did not change every declared file")
    diff = subprocess.run(
        ["git", "diff", "--binary"], cwd="/workspace", capture_output=True, check=True,
    ).stdout
    proof = {
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "source_call_id": "call_c381d19dbd674e0995b6e76c063b696e",
        "before": before, "after": after,
        "postpatch_observation_matched": True,
        "observation_sha256": hashlib.sha256(observation.stdout.encode()).hexdigest(),
        "restored_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "patch_engine_exit": result.returncode,
    }
    output.write_text(json.dumps(proof, indent=2) + "\n")
    output.with_suffix(".patch").write_bytes(diff)
    print(json.dumps(proof), flush=True)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
