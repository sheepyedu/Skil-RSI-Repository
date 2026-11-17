"""Verify every part and reconstruct the original rollout archive."""

import hashlib
import json
from pathlib import Path


def restore():
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "archive" / "MANIFEST.json").read_text())
    destination = root / manifest["archive_name"]
    temporary = destination.with_suffix(destination.suffix + ".partial")
    archive_hash = hashlib.sha256()
    archive_size = 0

    with temporary.open("wb") as output:
        for part in manifest["parts"]:
            part_hash = hashlib.sha256()
            part_size = 0
            with (root / "archive" / part["path"]).open("rb") as source:
                while chunk := source.read(8 * 1024 * 1024):
                    output.write(chunk)
                    part_hash.update(chunk)
                    archive_hash.update(chunk)
                    part_size += len(chunk)
            if part_size != part["bytes"] or part_hash.hexdigest() != part["sha256"]:
                raise ValueError(f"Part verification failed: {part['path']}")
            archive_size += part_size

    if archive_size != manifest["archive_bytes"]:
        raise ValueError("Archive size verification failed")
    if archive_hash.hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Archive SHA256 verification failed")

    temporary.replace(destination)
    print(f"Verified {len(manifest['parts'])} parts. Restored {destination}")
    print(f"SHA256 {archive_hash.hexdigest()}")


if __name__ == "__main__":
    restore()
