"""Make a private copy of the official framework and fix uploaded verifier file permissions."""

import hashlib
import json
import shutil
from pathlib import Path

BASE=Path("/mount-data/Codex-CLM/experiments/workbuddy-codex-20261118")
SOURCE=Path("/mount-data/Claude-code-CLM/experiments/workbuddy-20261118/upstream/src/workbuddy_bench")
BEFORE='''        try:
            await self.environment.upload_file(tmp_path, f"{self.tests_dir}/verifier.py")'''
AFTER='''        try:
            tmp_path.chmod(0o644)
            await self.environment.upload_file(tmp_path, f"{self.tests_dir}/verifier.py")'''


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    framework=BASE/"framework"
    framework.mkdir(exist_ok=False)
    package=framework/"workbuddy_bench"
    shutil.copytree(SOURCE,package,ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
    original=SOURCE/"judge/runtime/harbor.py"
    target=package/"judge/runtime/harbor.py"
    source=original.read_text()
    if source.count(BEFORE)!=1:
        raise ValueError("Unexpected official verifier upload implementation")
    target.write_text(source.replace(BEFORE,AFTER))
    (BASE/"VERIFIER_PERMISSION_FIX.json").write_text(json.dumps({
        "upstream_source":str(SOURCE),"private_framework":str(framework),
        "file":"workbuddy_bench/judge/runtime/harbor.py",
        "before_sha256":sha(original),"after_sha256":sha(target),
        "change":"Mark generated verifier.py readable by the non-root verifier before upload",
        "test_logic_changed":False,
    },indent=2)+"\n")


if __name__=="__main__":
    main()
