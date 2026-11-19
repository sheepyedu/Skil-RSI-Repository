"""Read back every published binary part from one immutable GitHub commit.

This manager utility performs public read-only downloads, not model/API calls.
It never updates GitHub or executes archived files. Completed valid parts can be
resumed; failed partial transfers and their receipts remain available.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(commit, expected_manifest, output, helpers):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("An immutable full Git commit SHA is required")
    manifest_bytes = expected_manifest.read_bytes()
    manifest = json.loads(manifest_bytes)
    parts = manifest["parts"]
    if (manifest["archive_name"] != "WORKBUDDY_PREFIX60_WITH_POLICY_FAILURE.zip" or not parts
            or len({p["path"] for p in parts}) != len(parts)
            or sum(p["bytes"] for p in parts) != manifest["archive_bytes"]):
        raise ValueError("Invalid expected incomplete-checkpoint manifest")
    for part in parts:
        if (not re.fullmatch(r"parts/workbuddy\.part-[0-9]{4}", part["path"])
                or not 0 < part["bytes"] <= 8 * 1024 * 1024
                or not re.fullmatch(r"[0-9a-f]{64}", part["sha256"])):
            raise ValueError("Expected qualified 8 MiB parts with SHA256")
    root_url = ("https://raw.githubusercontent.com/sheepyedu/Skil-RSI-Repository/"
                + commit + "/Codex%20CLM/workbuddy-20261118/checkpoints/prefix60-policy-20261119/archive/")
    identity = {"commit": commit, "expected_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                "archive_sha256": manifest["archive_sha256"], "source": root_url}
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    session = output / "DOWNLOAD_SESSION.json"
    if session.exists():
        if json.loads(session.read_text()) != identity:
            raise ValueError("Existing download directory belongs to another artifact")
    else:
        session.write_text(json.dumps(identity, indent=2) + "\n")
    attempt_log = output / "transport-attempts.jsonl"
    log_lock = threading.Lock()

    def download(relative, length, expected):
        path = output / "archive" / Path(*PurePosixPath(relative).parts)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if path.exists():
            if path.is_symlink() or path.stat().st_size != length or sha(path) != expected:
                raise ValueError("Existing downloaded content differs: " + relative)
            return
        last_error = None
        for number in range(1, 4):
            temporary = path.with_name(path.name + f".partial-{time.time_ns()}")
            record = {"path": relative, "attempt": number, "started_at": datetime.now(timezone.utc).isoformat()}
            try:
                request = urllib.request.Request(root_url + urllib.parse.quote(relative, safe="/"), headers={
                    "User-Agent": "WorkBuddyArchiveVerifier/1.0", "Accept-Encoding": "identity", "Cache-Control": "no-cache"})
                count, digest = 0, hashlib.sha256()
                with urllib.request.urlopen(request, timeout=120) as response, temporary.open("xb") as target:
                    record["status"] = response.status
                    while data := response.read(1024 * 1024):
                        count += len(data)
                        if count > length:
                            raise ValueError("Remote content exceeds expected byte count")
                        target.write(data)
                        digest.update(data)
                record.update(bytes=count, sha256=digest.hexdigest())
                if count != length or digest.hexdigest() != expected:
                    raise ValueError("Remote content differs from expected SHA256")
                temporary.rename(path)
                record["verified"] = True
            except Exception as error:
                last_error = error
                record.update(verified=False, error=str(error), partial_path=str(temporary))
            finally:
                record["finished_at"] = datetime.now(timezone.utc).isoformat()
                with log_lock:
                    with attempt_log.open("a") as stream:
                        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            if record["verified"]:
                return
            if number < 3:
                time.sleep(2 ** number)
        raise RuntimeError("Bounded public download failed: " + relative) from last_error

    download("MANIFEST.json", len(manifest_bytes), identity["expected_manifest_sha256"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(download, p["path"], p["bytes"], p["sha256"]): p for p in parts}
        try:
            for index, future in enumerate(as_completed(pending), 1):
                future.result()
                if index % 12 == 0 or index == len(parts):
                    print(json.dumps({"parts_verified": index, "total_parts": len(parts)}), flush=True)
        except BaseException:
            for future in pending:
                future.cancel()
            raise
    sys.path.insert(0, str(helpers.resolve()))
    from restore_workbuddy import join_parts
    from package_workbuddy import verify_archive
    joined = join_parts(output)
    result = verify_archive(joined)
    if result["archive_sha256"] != identity["archive_sha256"]:
        raise ValueError("Full remote archive changed during reconstruction")
    receipt = {**identity, **result, "parts_downloaded_and_sha256_verified": len(parts),
        "finished_at": datetime.now(timezone.utc).isoformat(), "model_api_calls": 0,
        "scope": "Actual remote binary readback of the incomplete prefix60 checkpoint, full ZIP rejoin, all chunk CRC/SHA and all logical file recipes; no archive execution",
        "planned_trials": 130, "completed_and_graded": 120, "provider_policy_rejected_ungraded": 1,
        "not_started": 9, "final65_complete": False}
    (output / "REMOTE_DOWNLOAD_VERIFIED.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("commit")
    for name in ("expected_manifest", "output", "helpers"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    verify(args.commit, args.expected_manifest, args.output, args.helpers)
