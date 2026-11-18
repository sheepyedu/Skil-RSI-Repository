"""Project validated CLM exchanges into the private native replay journal."""

import hashlib
import json
import os
from pathlib import Path


MEMORY_PREFIX = "CLM memory written by the assistant:\n"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()


def message_parts(message):
    content = message["content"]
    return [{"type": "text", "text": content}] if isinstance(content, str) else content


def canonical_history(messages, note):
    result = list(messages)
    first = dict(result[0])
    marker = {"type": "text", "text": MEMORY_PREFIX + note}
    parts = message_parts(first)
    if note and not any(part.get("text") == marker["text"] and part["type"] == "text" for part in parts):
        raise ValueError("The resumed native history lacks the committed CLM note")
    first["content"] = [
        part for part in parts
        if not (part["type"] == "text" and part.get("text") == marker["text"])
    ]
    if len(first["content"]) == 1 and set(first["content"][0]) == {"type", "text"}:
        first["content"] = first["content"][0]["text"]
    result[0] = first
    return result


def file_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as out:
        out.write(canonical(obj) + b"\n")
        out.flush()
        os.fsync(out.fileno())
    tmp.replace(path)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def project_native(raw, selected_ids, anchor_uuid, old_note, new_note, session_id):
    lines = raw.splitlines()
    records = [json.loads(line) for line in lines]
    removed = {}
    replacements = set()
    seen = {tool: [0, 0] for tool in selected_ids}
    anchor_count = 0
    for position, record in enumerate(records):
        kind = record.get("type")
        if kind not in {"user", "assistant"} or record.get("isSidechain"):
            continue
        if record.get("sessionId") != session_id:
            raise ValueError("Native session ID mismatch")
        message = record.get("message") or {}
        if "content" not in message:
            continue
        parts = message_parts(message)
        if record.get("uuid") == anchor_uuid:
            if kind != "user":
                raise ValueError("The CLM anchor is not an original user turn")
            anchor_count += 1
            if old_note:
                note = MEMORY_PREFIX + old_note
                matches = [p for p in parts if p.get("type") == "text" and p.get("text") == note]
                if len(matches) != 1:
                    raise ValueError("Unexpected previous native CLM note")
                parts = [p for p in parts if p is not matches[0]]
            if new_note:
                parts = [*parts, {"type": "text", "text": MEMORY_PREFIX + new_note}]
            message["content"] = parts
            replacements.add(position)
            continue

        kept = []
        for part in parts:
            tool_id = part.get("id") if part.get("type") == "tool_use" else None
            result_id = part.get("tool_use_id") if part.get("type") == "tool_result" else None
            if tool_id in seen:
                seen[tool_id][0] += 1
            elif result_id in seen:
                seen[result_id][1] += 1
            else:
                kept.append(part)
        if len(kept) != len(parts):
            if kept:
                message["content"] = kept
                replacements.add(position)
            else:
                removed[record["uuid"]] = record.get("parentUuid")
        if kind == "assistant" and "usage" in message:
            del message["usage"]
            replacements.add(position)

    if anchor_count != 1 or any(counts != [1, 1] for counts in seen.values()):
        raise ValueError("Selected tool calls and results must each exist exactly once in the native session")

    def surviving(value):
        visited = set()
        while value in removed:
            if value in visited:
                raise ValueError("Cyclic native transcript")
            visited.add(value)
            value = removed[value]
        return value

    output = []
    native_order = []
    for position, record in enumerate(records):
        uuid = record.get("uuid")
        if uuid in removed:
            continue
        if uuid and not record.get("isSidechain"):
            native_order.append(uuid)
        for key in ("parentUuid", "leafUuid", "sourceToolAssistantUUID"):
            if record.get(key) in removed:
                record[key] = surviving(record[key])
                replacements.add(position)
        output.append(canonical(record) if position in replacements else lines[position])
    if len(native_order) != len(set(native_order)):
        raise ValueError("Duplicate main-session UUIDs")
    return b"\n".join(output) + b"\n", len(removed)


def publish_projection(path, before, after, archive, details):
    if path.is_symlink() or path.read_bytes() != before:
        raise RuntimeError("Native transcript writer is still active")
    archive.mkdir(parents=True)
    (archive / "native.before.jsonl").write_bytes(before)
    (archive / "native.after.jsonl").write_bytes(after)
    evidence = {
        **details,
        "native_before_sha256": digest(before),
        "native_after_sha256": digest(after),
    }
    file_json(archive / "intent.json", evidence)
    temporary = path.with_suffix(".clm-sync")
    with temporary.open("xb") as stream:
        stream.write(after)
        stream.flush()
        os.fsync(stream.fileno())
    original = path.stat()
    if os.geteuid() == 0:
        os.chown(temporary, original.st_uid, original.st_gid)
    os.chmod(temporary, original.st_mode & 0o777)
    temporary.replace(path)
    file_json(archive / "committed.json", evidence)
    return evidence
