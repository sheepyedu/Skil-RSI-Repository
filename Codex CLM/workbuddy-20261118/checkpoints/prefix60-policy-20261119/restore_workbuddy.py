"""Rejoin verified parts or reconstruct all logical paths from the WorkBuddy archive.

The part manifest follows the repository's existing restore_archive.py format.
No benchmark commands or archived executables are run during reconstruction.
"""

import argparse
import hashlib
import json
import os
import uuid
import zipfile
from pathlib import Path, PurePosixPath

from package_workbuddy import sha, verify_archive


def join_parts(root):
    folder = root / "archive"
    manifest = json.loads((folder / "MANIFEST.json").read_text())
    name = manifest["archive_name"]
    if Path(name).name != name:
        raise ValueError("Invalid archive filename")
    destination = root / name
    if destination.exists():
        if destination.is_symlink() or sha(destination) != manifest["archive_sha256"]:
            raise ValueError("Existing archive differs; refusing to replace it")
        return destination
    temporary = destination.with_name(name + ".partial-" + uuid.uuid4().hex)
    whole, size = hashlib.sha256(), 0
    with temporary.open("xb") as target:
        for part in manifest["parts"]:
            pure = PurePosixPath(part["path"])
            source = folder.joinpath(*pure.parts)
            if (pure.is_absolute() or ".." in pure.parts or source.is_symlink()
                    or not source.resolve().is_relative_to(folder.resolve())):
                raise ValueError("Invalid archive part path")
            digest, length = hashlib.sha256(), 0
            with source.open("rb") as stream:
                while data := stream.read(8 * 1024 * 1024):
                    target.write(data)
                    digest.update(data)
                    whole.update(data)
                    length += len(data)
            if length != part["bytes"] or digest.hexdigest() != part["sha256"]:
                raise ValueError(f"Archive part changed: {part['path']}")
            size += length
    if size != manifest["archive_bytes"] or whole.hexdigest() != manifest["archive_sha256"]:
        raise ValueError("Reconstructed archive differs")
    temporary.rename(destination)
    return destination


def extract(path, destination):
    verification = verify_archive(path)
    destination.mkdir(mode=0o700, parents=True)
    with zipfile.ZipFile(path) as archive:
        entries = [json.loads(line) for line in archive.read("FILES.jsonl").splitlines()]
        deferred, directories, specials = [], [], []
        for entry in entries:
            target = destination.joinpath(*PurePosixPath(entry["path"]).parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError("Reconstruction path escapes its destination")
            if entry["kind"] == "directory":
                target.mkdir(mode=0o700, parents=True, exist_ok=True)
                directories.append((target, entry))
            elif entry["kind"] == "file":
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                digest = hashlib.sha256()
                with target.open("xb") as stream:
                    for identifier in entry["chunks"]:
                        data = archive.read("chunks/" + identifier)
                        stream.write(data)
                        digest.update(data)
                if digest.hexdigest() != entry["sha256"]:
                    raise ValueError(f"Restored file differs: {entry['path']}")
                os.chmod(target, entry["mode"] & 0o777)
                os.utime(target, ns=(entry["mtime_ns"], entry["mtime_ns"]))
            elif entry["kind"] == "symlink":
                deferred.append((target, entry))
            else:
                specials.append(entry)
        # Links are created after regular files, so no payload is written through an archived link.
        for target, entry in deferred:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.symlink_to(entry["target"])
        for target, entry in sorted(directories, key=lambda value: len(value[0].parts), reverse=True):
            os.chmod(target, entry["mode"] & 0o777)
            os.utime(target, ns=(entry["mtime_ns"], entry["mtime_ns"]))
    result = {**verification, "restored_files": sum(e["kind"] == "file" for e in entries),
              "restored_symlinks": len(deferred), "special_entries_not_recreated": specials,
              "ownership": "Original uid/gid retained in FILES.jsonl; restored files belong to the current user."}
    (destination / "RESTORE_VERIFIED.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("join").add_argument("directory", type=Path)
    sub.add_parser("verify").add_argument("archive", type=Path)
    command = sub.add_parser("extract")
    command.add_argument("archive", type=Path)
    command.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "join":
        print(join_parts(args.directory))
    elif args.command == "verify":
        print(json.dumps(verify_archive(args.archive), indent=2))
    else:
        print(json.dumps(extract(args.archive, args.destination), indent=2))
