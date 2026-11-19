"""Preserve every logical file in a deduplicated ZIP, then make Git-sized verified parts."""

import argparse
import hashlib
import json
import os
from pathlib import PurePosixPath
import stat
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

FORMAT = "workbuddy-content-chunks-v1"
CHUNK_SIZE = 4 * 1024 * 1024


def chunk_lengths(path, size, maximum):
    """Align raw tar chunks at member boundaries without extracting or rewriting it.

    Docker commits often shift identical large layers by a small header offset.
    Variable chunk lengths already belong to v1; every raw byte, including tar
    headers, padding and trailer, still participates in the original file recipe.
    Malformed/oversized metadata falls back to ordinary fixed-size chunking.
    """
    boundaries = {0, size}
    if path.suffix == ".tar" and size > maximum:
        try:
            with tarfile.open(path, "r:") as archive:
                for count, member in enumerate(archive, 1):
                    offsets = (member.offset, member.offset_data, member.offset_data + member.size)
                    if count > 50_000 or not all(type(v) is int and 0 <= v <= size for v in offsets):
                        raise ValueError("Tar metadata exceeds bounded chunk planning")
                    boundaries.update(offsets)
        except (tarfile.TarError, OSError, ValueError, OverflowError):
            boundaries = {0, size}
    previous = 0
    for boundary in sorted(boundaries):
        remaining = boundary - previous
        while remaining:
            length = min(maximum, remaining)
            yield length
            remaining -= length
        previous = boundary


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(path.read_text())


def enumerate_tree(base):
    for current, directories, files in os.walk(base, followlinks=False):
        directories.sort()
        files.sort()
        parent = Path(current)
        yield parent
        for name in list(directories):
            path = parent / name
            if path.is_symlink():
                yield path
                directories.remove(name)
        yield from (parent / name for name in files)


def make_archive(base, destination, secrets=(), expected=None, chunk_size=CHUNK_SIZE):
    """Chunking removes duplicate copied prefixes while retaining all original path metadata."""
    base, destination = base.resolve(), destination.resolve()
    if type(chunk_size) is not int or chunk_size <= 0:
        raise ValueError("Content chunk size must be positive")
    if destination.is_relative_to(base):
        raise ValueError("Archive output must be outside its source tree")
    expected = expected or {}
    entries, chunks, unique_bytes, logical_bytes = [], {}, 0, 0
    with destination.open("xb") as raw_output, zipfile.ZipFile(
            raw_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
        for path in enumerate_tree(base):
            relative = path.relative_to(base.parent).as_posix()
            before = path.lstat()
            entry = {"path": relative, "mode": before.st_mode, "mtime_ns": before.st_mtime_ns,
                     "uid": before.st_uid, "gid": before.st_gid}
            if stat.S_ISLNK(before.st_mode):
                target = os.readlink(path)
                if any(secret in target.encode() for secret in secrets):
                    raise ValueError(f"Publication credential match in link: {relative}")
                entry.update(kind="symlink", target=target)
                if relative in expected and expected[relative].get("symlink_target") != target:
                    raise ValueError(f"Audited link changed: {relative}")
            elif stat.S_ISDIR(before.st_mode):
                entry["kind"] = "directory"
            elif stat.S_ISREG(before.st_mode):
                digest, identifiers, length, tail = hashlib.sha256(), [], 0, b""
                with path.open("rb") as source:
                    for planned in chunk_lengths(path, before.st_size, chunk_size):
                        data = source.read(planned)
                        if len(data) != planned:
                            raise ValueError(f"Source truncated while packaging: {relative}")
                        scan = tail + data
                        if any(secret in scan for secret in secrets):
                            raise ValueError(f"Publication credential match in file: {relative}")
                        maximum = max((len(secret) for secret in secrets), default=1)
                        tail = scan[-(maximum-1):] if maximum > 1 else b""
                        digest.update(data)
                        length += len(data)
                        identifier = hashlib.sha256(data).hexdigest()
                        identifiers.append(identifier)
                        if identifier not in chunks:
                            archive.writestr("chunks/" + identifier, data)
                            chunks[identifier] = len(data)
                            unique_bytes += len(data)
                after = path.lstat()
                if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_mode) != (
                        after.st_ino, after.st_size, after.st_mtime_ns, after.st_mode):
                    raise ValueError(f"Source changed while packaging: {relative}")
                if length != before.st_size:
                    raise ValueError(f"Source length changed while packaging: {relative}")
                entry.update(kind="file", bytes=length, sha256=digest.hexdigest(), chunks=identifiers)
                if relative in expected:
                    record = expected[relative]
                    if record.get("size") != length or record.get("sha256") != entry["sha256"]:
                        raise ValueError(f"Audited file changed: {relative}")
                logical_bytes += length
            else:
                # A socket cannot be serialized as file contents; keep its exact type in the inventory.
                entry.update(kind="special", device=before.st_rdev)
            entries.append(entry)
        paths = {entry["path"] for entry in entries}
        if not set(expected) <= paths:
            raise ValueError("Some audited paths are missing from the archive scope")
        header = {"format": FORMAT, "root": base.name, "chunk_size": chunk_size,
                  "chunk_strategy": "bounded raw tar member alignment; fixed-size fallback",
                  "created_at": datetime.now(timezone.utc).isoformat(), "entries": len(entries),
                  "logical_bytes": logical_bytes, "unique_chunk_bytes": unique_bytes,
                  "unique_chunks": len(chunks), "special_entries": sum(e["kind"] == "special" for e in entries),
                  "scope": "All files and link metadata in the isolated experiment root; no directory symlinks followed."}
        archive.writestr("FORMAT.json", json.dumps(header, ensure_ascii=False, indent=2))
        archive.writestr("FILES.jsonl", "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries))
    return header


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        header = json.loads(archive.read("FORMAT.json"))
        if header["format"] != FORMAT:
            raise ValueError("Unknown archive format")
        entries = [json.loads(line) for line in archive.read("FILES.jsonl").splitlines()]
        paths = [e["path"] for e in entries]
        if len(paths) != len(set(paths)):
            raise ValueError("Archive has duplicate logical paths")
        for value in paths:
            pure = PurePosixPath(value)
            if pure.is_absolute() or ".." in pure.parts or not pure.parts or pure.parts[0] != header["root"]:
                raise ValueError("Invalid logical archive path")
        expected_chunks = {identifier for e in entries if e["kind"] == "file" for identifier in e["chunks"]}
        names = archive.namelist()
        if len(names) != len(set(names)) or set(names) != {"FORMAT.json", "FILES.jsonl", *{"chunks/"+x for x in expected_chunks}}:
            raise ValueError("Archive has extra, duplicate, or missing entries")
        chunk_bytes = 0
        for identifier in expected_chunks:
            if not 0 < archive.getinfo("chunks/" + identifier).file_size <= header["chunk_size"]:
                raise ValueError("Invalid content chunk size")
            data = archive.read("chunks/" + identifier)  # zipfile also validates its CRC.
            if hashlib.sha256(data).hexdigest() != identifier:
                raise ValueError(f"Corrupt archive chunk: {identifier}")
            chunk_bytes += len(data)
        recipes = set()
        for entry in entries:
            if entry["kind"] != "file":
                continue
            recipe = (entry["sha256"], entry["bytes"], tuple(entry["chunks"]))
            if recipe in recipes:
                continue
            digest, size = hashlib.sha256(), 0
            for identifier in entry["chunks"]:
                data = archive.read("chunks/" + identifier)
                digest.update(data)
                size += len(data)
            if size != entry["bytes"] or digest.hexdigest() != entry["sha256"]:
                raise ValueError(f"File recipe does not reconstruct its original bytes: {entry['path']}")
            recipes.add(recipe)
        if len(entries) != header["entries"]:
            raise ValueError("Archive inventory count differs")
        if (len(expected_chunks) != header["unique_chunks"] or chunk_bytes != header["unique_chunk_bytes"]
                or sum(e["bytes"] for e in entries if e["kind"] == "file") != header["logical_bytes"]):
            raise ValueError("Archive byte accounting differs")
    return {**header, "all_chunk_crc_sha_passed": True, "all_file_recipes_sha_passed": True,
            "archive_bytes": path.stat().st_size, "archive_sha256": sha(path)}


def split_archive(path, output, part_size=45 * 1024 * 1024):
    folder = output / "archive"
    parts = folder / "parts"
    parts.mkdir(parents=True)
    records, whole, size = [], hashlib.sha256(), 0
    with path.open("rb") as source:
        number = 1
        while data := source.read(part_size):
            name = f"workbuddy.part-{number:04d}"
            with (parts / name).open("xb") as target:
                target.write(data)
            whole.update(data)
            size += len(data)
            records.append({"path": "parts/" + name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            number += 1
    if size != path.stat().st_size or whole.hexdigest() != sha(path):
        raise ValueError("Multipart export differs from the original archive")
    manifest = {"archive_name": path.name, "archive_bytes": size, "archive_sha256": whole.hexdigest(), "parts": records}
    (folder / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (folder / ".gitattributes").write_text("parts/* -text -diff\n")
    return manifest


def production(base, audit, output, scan_gpt):
    summary = load(audit / "summary.json")
    if summary["groups"]["all"]["pairs"] != 65:
        raise ValueError("Publication requires all 65 audited pairs")
    run = Path(summary["run"])
    accepted = load(run / "accepted.json")
    if (run.resolve().parent != base.resolve() or not base.name.startswith("workbuddy-codex-")
            or output.resolve().is_relative_to(base.resolve()) or accepted["pairs"] != 65
            or accepted["plan_sha256"] != sha(run / "plan.json") or not (audit / "REPORT.md").is_file()):
        raise ValueError("Complete audited experiment and report are required")
    binding_path = audit / "native-task-binding.json"
    if not binding_path.is_file():
        raise ValueError("Final native and API task binding proof is required before publication")
    binding = load(binding_path)
    plan_rows = load(run / "plan.json")["tasks"]
    entries = binding.get("trials", [])
    expected_keys = [(r["position"], arm) for r in plan_rows for arm in ("native", "clm")]
    if (binding.get("selected_trials_verified") != 130 or len(entries) != 130
            or not binding.get("all_native_completions_and_task_bindings_verified")
            or binding.get("threads") != accepted["threads"] or Path(binding.get("run", "/")).resolve() != run.resolve()
            or [(r["position"], r["arm"]) for r in entries] != expected_keys
            or binding.get("source_sha256") != sha(Path(__file__).with_name("check_workbuddy_binding.py"))
            or binding.get("native_helper_sha256") != sha(Path(__file__).with_name("provision_workbuddy_cbc.py"))):
        raise ValueError("Final task binding proof is incomplete or from another run/source")
    by_position = {r["position"]: r for r in plan_rows}
    for entry in entries:
        if (entry["instruction_sha256"] != by_position[entry["position"]]["instruction_sha256"]
                or entry["native_completion"]["thread"] != accepted["threads"][entry["arm"]]):
            raise ValueError("Final task binding proof disagrees with the frozen task or original thread")
    expected = {}
    for line in (audit / "sha256.jsonl").open():
        record = json.loads(line)
        relative = base.name + "/" + record["path"]
        if relative in expected and expected[relative] != record:
            raise ValueError("Audit inventory contains conflicting duplicate paths")
        expected[relative] = record
    secret_values = []
    if scan_gpt:
        value = subprocess.check_output(["/mount-data/Tools/skill-api", "_credential", "--service", "gpt"]).strip()
        if len(value) < 16:
            raise ValueError("Invalid private credential scan input")
        secret_values.append(value)
    os.umask(0o077)
    output.mkdir(mode=0o700, parents=True)
    archive = output / "WORKBUDDY_CODEX_65_FULL.zip"
    partial = archive.with_suffix(".zip.partial")
    make_archive(base, partial, secrets=secret_values, expected=expected)
    result = verify_archive(partial)
    partial.rename(archive)
    result["private_gpt_key_match_count"] = 0 if scan_gpt else None
    (output / "VERIFIED.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = split_archive(archive, output)
    print(json.dumps({"archive_bytes": result["archive_bytes"], "logical_bytes": result["logical_bytes"],
                      "entries": result["entries"], "parts": len(manifest["parts"]), "sha256": result["archive_sha256"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scan-private-gpt-key", action="store_true")
    args = parser.parse_args()
    production(args.base, args.audit, args.output, args.scan_private_gpt_key)
