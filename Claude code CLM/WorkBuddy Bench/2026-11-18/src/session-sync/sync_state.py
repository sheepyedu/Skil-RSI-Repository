"""Transactional CLM edit admission for the host-side native Messages relay."""

import copy
import json
import os
import time
from pathlib import Path

from clm.context import blocks, editable_exchanges, write_json
from native_session import canonical_history, file_json


def prompt_markers(messages):
    # Compare the complete benchmark prompt blocks, not just their marker IDs.
    return [
        block["text"]
        for message in messages if message["role"] == "user"
        for block in blocks(message)
        if block["type"] == "text" and block["text"].startswith("[WB_SERIAL_TASK_")
    ]


def present_tools(messages):
    return {
        item.get("id") if item["type"] == "tool_use" else item.get("tool_use_id")
        for m in messages for item in blocks(m) if item["type"] in {"tool_use", "tool_result"}
    }


class SessionSync:
    def __init__(self, context, directory, task_marker, session_id):
        self.context = context
        self.control = Path(directory)
        self.task_marker = task_marker
        self.session_id = session_id
        self.sequence = 0
        self.pending = None

    def on_messages(self, messages, accept_edit):
        markers = prompt_markers(messages)
        if not any(self.task_marker in prompt for prompt in markers):
            return {"side_session": True}, None

        if self.pending:
            active = self.pending
            if not (active["directory"] / "native" / "committed.json").is_file():
                raise ValueError("Native session synchronization is in progress")
            if present_tools(messages) & active["tool_ids"]:
                raise ValueError("Reloaded native context contains a deleted exchange")
            base = canonical_history(messages, active["context"].note)
            if prompt_markers(base) != active["markers"]:
                raise ValueError("Reloaded native context changed the original task prompts")
            staged = active["context"]
            self.context.revision = staged.revision
            self.context.anchor = staged.anchor
            self.context.visible = set(staged.visible)
            self.context.dropped.clear()
            self.context.note = staged.note
            try:
                _, evidence = self.context.apply(base, accept_edit=False)
                # Use the ordinary mode once to publish the new catalog. This
                # request has no new tool action between commit and reload.
                _, catalog = self.context.apply(base)
            except (OSError, ValueError):
                raise RuntimeError("Could not publish the synced native context")
            file_json(active["directory"] / "resumed.json", {
                "session_id": self.session_id,
                "continued": True,
                "preserved_original_prompts": len(active["markers"]),
                "deleted_tool_ids": sorted(active["tool_ids"]),
                "catalog_revision": catalog["revision"],
            })
            self.pending = None
            return {**evidence, "edit": "accepted", "synchronized_native": True,
                    "dropped_ids": active["event"]["dropped_ids"]}, None

        base = canonical_history(messages, self.context.note)
        incoming = self.context.directory / "edit.json"
        if not accept_edit or not (incoming.exists() or incoming.is_symlink()):
            _, evidence = self.context.apply(base, accept_edit=accept_edit)
            return evidence, None

        self.sequence += 1
        target = self.control / f"edit-{self.sequence:04d}"
        target.mkdir()
        state = target / "staged-context"
        state.mkdir()
        # The original CLM parser validates the edit against the last exposed
        # revision, its allowed exchange IDs, and a positive size reduction.
        os.replace(incoming, state / "edit.json")
        staged = copy.copy(self.context)
        staged.directory = state
        staged.dropped = set(self.context.dropped)
        staged.visible = set(self.context.visible)
        pairs = editable_exchanges(base)
        _, event = staged.apply(base)
        if event["edit"] != "accepted":
            self.context.revision = staged.revision
            self.context.visible = staged.visible
            write_json(
                self.context.directory / "LIVE_CTX_MAIN.json",
                json.loads((state / "LIVE_CTX_MAIN.json").read_text()),
            )
            file_json(target / "rejected.json", event)
            return event, None

        selected = {
            part["id"] for identity in event["dropped_ids"]
            for part in blocks(pairs[identity][1][0]) if part["type"] == "tool_use"
        }
        self.pending = {
            "directory": target, "tool_ids": selected,
            "event": event, "markers": prompt_markers(base), "context": staged,
        }
        file_json(target / "request.json", {
            "session_id": self.session_id, "tool_ids": sorted(selected),
            "old_note": self.context.note, "new_note": staged.note,
            "protected_prompt_count": len(self.pending["markers"]),
        })
        return {**event, "edit": "awaiting_native_commit"}, target

    @staticmethod
    def wait_for_native(path, timeout=35):
        until = time.monotonic() + timeout
        while time.monotonic() < until:
            if (path / "native" / "committed.json").is_file():
                return True
            if (path / "failed.json").is_file():
                return False
            time.sleep(0.05)
        return False
