"""Verify the two serial WorkBuddy trajectories and recompute paired results."""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from clm.context import CALLS, NOTE_LIMIT, candidates, digest, encode, is_message, projection


def load(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def trial_key(row):
    return f"{row['position']:03d}-{row['domain']}-{row['task']}"


def valid_score(receipt):
    score = (receipt.get("reward") or {}).get("reward")
    if type(score) not in {int, float} or not math.isfinite(score):
        raise ValueError("Missing numeric official reward")
    return score


def response_usage(path):
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    objects = []
    if text.lstrip().startswith("{"):
        try:
            objects.append(json.loads(text))
        except ValueError:
            pass
    else:
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    objects.append(json.loads(line[5:]))
                except ValueError:
                    pass
    found = None
    for obj in objects:
        if not isinstance(obj, dict):
            continue
        usage = (obj.get("response") or obj).get("usage")
        if not isinstance(usage, dict):
            continue
        values = {"input_tokens": usage.get("input_tokens", usage.get("prompt_tokens")),
                  "output_tokens": usage.get("output_tokens", usage.get("completion_tokens"))}
        if all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values.values()):
            found = {**values, "reported": usage}
    return found


def all_attempt_ledger(roots):
    """Deduplicate copied HTTP attempts by their original clock and response digest."""
    entries, contexts = {}, {}
    for root in roots:
        for path in sorted(root.rglob("wire/*/receipt.json")):
            wire = load(path)
            case = path.parent.parent.parent
            if case not in contexts:
                metadata = {}
                for name in ("receipt.json", "PREPARED.json", "intent.json"):
                    if (case / name).is_file():
                        metadata = load(case / name)
                        break
                arm = metadata.get("arm") or next((a for a in ("native", "clm") if a in path.parts), None)
                marker = metadata.get("marker") or (metadata.get("row") or {}).get("marker") or ""
                scope = ("formal" if marker.startswith("WB_CODEX_FORMAL_") else
                         "pilot" if marker.startswith("WB_CODEX_PILOT_") else "auxiliary_or_unclassified")
                contexts[case] = {"arm": arm or "unassigned", "scope": scope, "marker": marker}
            attempts = wire.get("attempts") or [wire]
            for record in attempts:
                raw = path.parent / "response.raw"
                if record.get("number"):
                    raw = path.parent / "attempts" / str(record["number"]) / "response.raw"
                if record.get("response_sha256") and sha(raw) != record["response_sha256"]:
                    raise ValueError(f"Attempt bytes changed: {raw}")
                identity = (record.get("started_ns", wire.get("started_ns")), wire.get("raw_sha256"),
                            record.get("response_sha256"), wire.get("path"))
                if identity[0] is None:
                    raise ValueError(f"Attempt lacks original timing identity: {path}")
                if identity in entries:
                    continue
                entries[identity] = {"evidence": str(raw), "started_ns": identity[0],
                                     **contexts[case],
                                     "purpose": "judge" if wire.get("path") == "/v1/chat/completions" else "actor_and_context",
                                     "route": wire.get("path"), "status": record.get("status"),
                                     "response_sha256": record.get("response_sha256"),
                                     "usage": response_usage(raw),
                                     "terminal_sse": record.get("terminal_sse"),
                                     "transport_error": record.get("transport_error")}
    result = sorted(entries.values(), key=lambda x: x["started_ns"])
    known = [entry["usage"] for entry in result if entry["usage"] is not None]
    grouped = defaultdict(list)
    for entry in result:
        grouped[(entry["scope"], entry["arm"], entry["purpose"])].append(entry)
    groups = []
    for (scope, arm, purpose), attempts in sorted(grouped.items()):
        measured = [r["usage"] for r in attempts if r["usage"] is not None]
        groups.append({"scope": scope, "arm": arm, "purpose": purpose, "attempts": len(attempts),
                       "usage_known": len(measured), "usage_unknown": len(attempts) - len(measured),
                       "known_input_tokens": sum(u["input_tokens"] for u in measured),
                       "known_output_tokens": sum(u["output_tokens"] for u in measured)})
    return result, {"attempts": len(result), "usage_known": len(known),
                    "usage_unknown": len(result) - len(known),
                    "known_input_tokens": sum(x["input_tokens"] for x in known),
                    "known_output_tokens": sum(x["output_tokens"] for x in known),
                    "by_scope_arm_purpose": groups,
                    "scope": "Accepted, failed, pilot, capacity and judge-repair attempts; copied attempts counted once. Unknown usage is not zero cost."}


def compaction_ledger(roots):
    events = {}
    for root in roots:
        for path in sorted(root.rglob("native.jsonl")):
            options_path = path.parent / "run-options.json"
            options = load(options_path) if options_path.exists() else {}
            explicit_seen = False
            for line in path.open():
                entry = json.loads(line)
                value = entry.get("data") or {}
                params = value.get("params") or {}
                item = params.get("item") or {}
                if value.get("method") != "item/completed" or item.get("type") != "contextCompaction":
                    continue
                key = (params.get("threadId"), item["id"])
                protective = bool(options.get("compact") and not explicit_seen)
                explicit_seen = True
                if key in events:
                    continue
                events[key] = {"thread": key[0], "item_id": key[1],
                               "time_ns": entry.get("time_ns"), "evidence": str(path),
                               "marker": options.get("marker"),
                               "arm": options.get("arm") or next((a for a in ("native", "clm") if a in path.parts), None),
                               "protective": protective}
    return sorted(events.values(), key=lambda x: x.get("time_ns") or 0)


def task_attempt_ledger(roots):
    """Count actual Harbor trial directories once, retaining incomplete startups and aliases."""
    entries = {}
    for root in roots:
        plan = load(root / "plan.json") if (root / "plan.json").exists() else {}
        rows = {r["position"]: r for r in plan.get("tasks", [])}
        for arm in ("native", "clm"):
            for trial in sorted((root / arm / "trials").glob("*")):
                if not trial.is_dir():
                    continue
                result_path = trial / "result.json"
                result = load(result_path) if result_path.is_file() else {}
                identity = (trial.name, result.get("id") or result.get("started_at"))
                if identity in entries:
                    existing = entries[identity]
                    if existing["result_sha256"] != (sha(result_path) if result_path.is_file() else None):
                        raise ValueError("Copied physical trial results disagree")
                    if str(trial) not in existing["aliases"]:
                        existing["aliases"].append(str(trial))
                    continue
                options_path = trial / "agent/run-options.json"
                options = load(options_path) if options_path.is_file() else {}
                native_path = trial / "agent/native-result.json"
                native = load(native_path) if native_path.is_file() else {}
                completed, item_starts = {}, defaultdict(int)
                timeline = trial / "agent/native.jsonl"
                if timeline.is_file():
                    for line in timeline.open():
                        event = json.loads(line).get("data") or {}
                        params = event.get("params") or {}
                        if event.get("method") == "turn/completed":
                            completed = params.get("turn") or {}
                        elif event.get("method") == "item/started":
                            item_starts[(params.get("item") or {}).get("type", "unknown")] += 1
                match = re.search(r"-(?:native|clm)-(\d{3})(?:-r\d+)?$", trial.name)
                position = int(match[1]) if match else None
                row = rows.get(position)
                marker = options.get("marker") or (row or {}).get("marker") or ""
                scope = ("formal" if marker.startswith("WB_CODEX_FORMAL_") else
                         "pilot" if marker.startswith("WB_CODEX_PILOT_") else "auxiliary_or_unclassified")
                entries[identity] = {"trial_name": trial.name, "trial_id": result.get("id"),
                    "arm": arm, "scope": scope, "position": position,
                    "task": (row or {}).get("task"), "marker": marker,
                    "started_at": result.get("started_at"), "finished_at": result.get("finished_at"),
                    "thread": native.get("thread"), "native_turn": native.get("turn") or completed.get("id"),
                    "native_turn_status": completed.get("status"),
                    "native_turn_error": completed.get("error"), "observed_item_starts": dict(item_starts),
                    "app_server_exit": native.get("native_exit"), "result_present": bool(result),
                    "trial_exception": bool(result.get("exception_info")),
                    "original_reward": (result.get("verifier_result") or {}).get("rewards"),
                    "result_sha256": sha(result_path) if result_path.is_file() else None,
                    "evidence": str(trial), "aliases": [str(trial)]}
    records = sorted(entries.values(), key=lambda r: (r["started_at"] or "", r["trial_name"]))
    groups = defaultdict(list)
    for record in records:
        if record["scope"] == "formal":
            groups[(record["position"], record["arm"], record["task"])].append(record)
    counts = [{"position": position, "arm": arm, "task": task, "physical_trial_directories": len(records),
               "with_result": sum(r["result_present"] for r in records),
               "without_result": sum(not r["result_present"] for r in records),
               "with_exception": sum(r["trial_exception"] for r in records)}
              for (position, arm, task), records in sorted(groups.items())]
    return records, counts


def projection_proof(path, event):
    """Independently reconstruct the projection, including protected text and full call batches."""
    original_path, sent_path = path.parent / "request.raw.json", path.parent / "request.sent.json"
    if sha(original_path) != event["raw_sha256"] or sha(sent_path) != event["sent_sha256"]:
        raise ValueError(f"CLM request bytes changed: {path}")
    original, forwarded = load(original_path), load(sent_path)
    raw, sent = original["input"], forwarded["input"]
    if {k: v for k, v in original.items() if k != "input"} != {
            k: v for k, v in forwarded.items() if k != "input"}:
        raise ValueError(f"CLM altered fields outside the input array: {path}")
    anchor = next(i for i, item in enumerate(raw) if is_message(item, "user"))
    groups = candidates(raw, anchor)
    retained = {(item["type"], item["call_id"]) for item in sent if item.get("type") in CALLS}
    dropped = set()
    for key, (start, end) in groups.items():
        present = [(item["type"], item["call_id"]) in retained
                   for item in raw[start:end] if item.get("type") in CALLS]
        if not any(present):
            dropped.add(key)
        elif not all(present):
            raise ValueError(f"CLM removed only part of a complete batch: {path}")
    first_raw, first_sent = raw[anchor], next(item for item in sent if is_message(item, "user"))
    note = ""
    if first_raw != first_sent:
        content = first_raw["content"]
        if isinstance(content, str):
            content = [{"type": "input_text", "text": content}]
        actual = first_sent["content"]
        prefix = "CLM memory written by the assistant:\n"
        if (not isinstance(actual, list) or len(actual) != len(content) + 1 or actual[:-1] != content
                or actual[-1].get("type") != "input_text" or not actual[-1].get("text", "").startswith(prefix)):
            raise ValueError(f"CLM altered protected first-user text: {path}")
        note = actual[-1]["text"][len(prefix):]
    detail = event["clm"]
    if (len(note.encode()) > NOTE_LIMIT or projection(raw, groups, dropped, note, anchor) != sent
            or digest(raw) != detail["raw_input_sha256"] or digest(sent) != detail["upstream_input_sha256"]
            or len(encode(raw)) != detail["before_input_bytes"]
            or len(encode(sent)) != detail["after_input_bytes"]
            or len(raw) - len(sent) != detail["removed_items"]):
        raise ValueError(f"CLM projection cannot be reconstructed exactly: {path}")
    if detail.get("edit") == "accepted" and (
            not detail["dropped_ids"] or not set(detail["dropped_ids"]) <= dropped):
        raise ValueError(f"Accepted CLM edit is not present in its projected request: {path}")
    return {"effective_dropped_ids": sorted(dropped), "note": note,
            "protected_content_and_complete_batches_verified": True}


def clm_edit_ledger(roots):
    """Count edits in failed attempts as well as selected attempts; copied prefixes count once."""
    events, requests = {}, {}
    for root in roots:
        for path in sorted(root.rglob("wire/*/receipt.json")):
            event = load(path)
            detail = event.get("clm")
            if not detail:
                continue
            identity = (event["started_ns"], event["raw_sha256"], event["sent_sha256"])
            if identity in requests:
                continue
            proof = projection_proof(path, event)
            requests[identity] = True
            if detail.get("edit") is None:
                continue
            case = path.parent.parent.parent
            receipt = load(case / "receipt.json") if (case / "receipt.json").is_file() else {}
            events[identity] = {"time_ns": event["started_ns"], "evidence": str(path),
                                "receipt_sha256": sha(path), "thread": receipt.get("thread"),
                                "marker": receipt.get("marker"), "row": receipt.get("row"),
                                "request_delivered": event.get("delivered"),
                                "trial_selected_at_source": receipt.get("accepted"),
                                **detail, **proof}
    return sorted(events.values(), key=lambda x: x["time_ns"]), len(requests)


def agent_cli_complete(path):
    """The official tee pipeline can return zero after CBC itself has failed."""
    if not path.is_file():
        return False
    terminal = None
    try:
        for line in path.open():
            event = json.loads(line)
            if isinstance(event, dict) and event.get("type") == "result":
                terminal = event
    except (ValueError, UnicodeError):
        return False
    return bool(terminal and terminal.get("subtype") == "success" and terminal.get("is_error") is False)


def judge_quality(trial, result):
    """Record official technical metadata; a numeric reward alone does not validate a judge."""
    findings, recovered, models, seen = [], [], set(), set()

    def visit(value, location):
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{location}[{index}]")
        elif isinstance(value, dict):
            if (value.get("judge_name") and value.get("judge_type")
                    and (value.get("ok") is False or value.get("status") in {"judge_error", "build_error"})):
                identity = ("normalized_judge_error", value["judge_name"], value.get("status"))
                if identity not in seen:
                    seen.add(identity)
                    findings.append({"location": location, "field": identity[0],
                        "judge": value["judge_name"], "value": value.get("status"),
                        "errors": value.get("errors", [])})
            if value.get("name") in {"score_eval_core_failed", "evaluator_runtime_error",
                                     "eval_core_import_failed", "evaluator_emitted_no_checks"}:
                identity = ("deterministic_evaluator_failure", value["name"])
                if identity not in seen:
                    seen.add(identity)
                    findings.append({"location": location, "field": identity[0],
                                     "value": value["name"], "detail": value.get("detail")})
            meta = value.get("judge_meta")
            if value.get("judge_type") == "agent" and value.get("id"):
                identity = ("missing_interactive_verdict", value["id"])
                verdict_path = trial / "verifier/agent-judge" / (value["id"] + ".json")
                verdict = load(verdict_path) if verdict_path.is_file() else {}
                valid = (isinstance(meta, dict) and meta.get("judge") == "agent_judge"
                         and meta.get("agent_returncode") == 0
                         and value.get("status") in ("pass", "fail")
                         and verdict.get("agent_returncode") == 0
                         and verdict.get("verdict") == value.get("status")
                         and verdict.get("model") == meta.get("model") == "gpt-6.1-sol"
                         and agent_cli_complete(verdict_path.with_suffix(".stream.log")))
                if not valid and identity not in seen:
                    seen.add(identity)
                    findings.append({"location": location, "item_id": value["id"],
                                     "field": "missing_interactive_verdict", "value": True})
            if isinstance(meta, dict):
                if meta.get("model"):
                    models.add(str(meta["model"]))
                for key in ("image_input_error", "llm_retry_error", "fallback_mode"):
                    content = meta.get(key)
                    if content and str(content).lower() not in ("none", "null"):
                        identity = (key, str(content), value.get("id"))
                        if identity not in seen:
                            seen.add(identity)
                            finding = {"location": location, "item_id": value.get("id"),
                                       "field": key, "value": content}
                            # The official judge retains its last retry exception even after a
                            # later successful response. Require the complete final JSON verdict.
                            excerpt = meta.get("raw_response_excerpt", "")
                            verdict = None
                            try:
                                parsed = json.loads(excerpt)
                                if isinstance(parsed, dict):
                                    verdict = parsed.get("verdict")
                            except (ValueError, TypeError):
                                pass
                            if (key == "llm_retry_error" and meta.get("fallback_mode") == "none"
                                    and meta.get("verdict_parse_strategy") == "json"
                                    and meta.get("raw_response_chars") == len(excerpt)
                                    and verdict in ("pass", "fail")
                                    and verdict == value.get("status")):
                                recovered.append({**finding, "resolution": "Complete final JSON verdict after retry"})
                            else:
                                findings.append(finding)
                if meta.get("judge_path") == "llm" and meta.get("raw_response_chars") == 0:
                    identity = ("empty_final_judge_response", value.get("id"))
                    if identity not in seen:
                        seen.add(identity)
                        findings.append({"location": location, "item_id": value.get("id"),
                                         "field": "empty_final_judge_response", "value": True})
            stages = value.get("stage_results")
            if isinstance(stages, list):
                for stage in stages:
                    if stage.get("exit_code") not in (None, 0):
                        identity = ("stage_exit", stage.get("name"), stage.get("exit_code"))
                        if identity not in seen:
                            seen.add(identity)
                            findings.append({"location": location, "stage": stage.get("name"),
                                             "field": "stage_exit_code", "value": stage["exit_code"]})
            for key, item in value.items():
                if key != "judge_meta":
                    visit(item, f"{location}.{key}")

    if result.get("exception_info"):
        findings.append({"field": "exception_info", "value": result["exception_info"]})
    files = []
    for name in ("score.json", "raw_reward.json", "evidence/eval-report.json"):
        path = trial / "verifier" / name
        if path.is_file():
            files.append({"path": str(path), "sha256": sha(path)})
            visit(load(path), name)
    return {"metadata_files": files, "reported_judge_models": sorted(models),
            "technical_findings": findings, "recovered_retry_findings": recovered,
            "requires_review": bool(findings),
            "scope": "Official technical fields only; semantic failures and low scores remain model results."}


def judge_repair(root, row, arm, receipt, trial):
    matches = []
    for path in sorted((root.parent / "judge-repairs").glob("*/APPLIED.json")):
        repair = load(path)
        if repair.get("position") != row["position"] or repair.get("arm") != arm:
            continue
        if (repair["row"] != row or repair["thread"] != receipt["thread"]
                or repair["original_reward"] != receipt["reward"]):
            raise ValueError("Official judge repair is not bound to this original trial")
        for filename, expected in repair["source_files_sha256"].items():
            if sha(Path(filename)) != expected:
                raise ValueError(f"Original source for judge repair changed: {filename}")
        for filename, expected in repair["repair_files_sha256"].items():
            if sha(path.parent / filename) != expected:
                raise ValueError(f"Judge repair evidence changed: {filename}")
        for filename in (path.parent / "wire").glob("*/receipt.json"):
            wire = load(filename)
            raw, sent = filename.parent / "request.raw.json", filename.parent / "request.sent.json"
            if (wire.get("path") != "/v1/chat/completions" or load(raw).get("model") != "gpt-6.1-sol"
                    or sha(raw) != wire.get("raw_sha256") or sha(sent) != wire.get("sent_sha256")
                    or raw.read_bytes() != sent.read_bytes()):
                raise ValueError("Judge repair changed a request or used an actor/model route")
            if wire.get("response_sha256") and sha(filename.parent / "response.raw") != wire["response_sha256"]:
                raise ValueError("Judge repair response bytes changed")
        source_trial = Path(repair["source_trial"])
        artifacts = repair.get("actor_artifacts", ["agent.patch", "agent.workspace.tar.gz"])
        if artifacts not in (["agent.patch"], ["agent.patch", "agent.workspace.tar.gz"]):
            raise ValueError("Unsupported original actor artifact contract")
        if artifacts == ["agent.patch"]:
            if (repair.get("repair_kind") not in {"office_artifact_refs_type_guard", "csv_utf8_bom_reader"}
                    or not repair.get("original_patch_exact")
                    or not repair.get("original_evaluation_reproduced")
                    or repair.get("actor_model_calls") != 0
                    or repair.get("grading_model_calls") != 0):
                raise ValueError("Patch-only repair lacks deterministic restoration evidence")
        for name in artifacts:
            if sha(trial / "verifier" / name) != repair["source_files_sha256"][str(source_trial / "verifier" / name)]:
                raise ValueError("Judge repair was produced for different actor artifacts")
        result = load(path.parent / "result.json")
        if result["verifier_result"]["rewards"] != repair["reward"]:
            raise ValueError("Repaired official score disagrees with the repair receipt")
        quality = judge_quality(path.parent, result)
        if quality["requires_review"]:
            raise ValueError("Repaired official verdict still contains technical errors")
        matches.append((path, repair, quality))
    if len(matches) > 1:
        raise ValueError("Multiple applied judge repairs for one trial need explicit reconciliation")
    return matches[0] if matches else None


def audit_trial(root, row, arm, previous):
    name = trial_key(row)
    evidence = root / arm / "evidence" / name
    receipt = load(evidence / "receipt.json")
    trial = root / arm / "trials" / receipt.get("trial_name", name)
    result = load(trial / "result.json")
    if not receipt["accepted"] or row != receipt["row"] or arm != receipt["arm"]:
        raise ValueError(f"Incomplete or mismatched receipt for {arm}/{name}")
    if (previous is not None and previous != receipt["thread"]) or bool(previous) != receipt["native"]["resumed"]:
        raise ValueError(f"Native continuity failed for {arm}/{name}")
    if sha(evidence / "native-session.jsonl") != receipt["session_sha256"]:
        raise ValueError(f"Native session checksum differs for {arm}/{name}")
    if sha(trial / "agent" / "instruction-source.md") != row["instruction_sha256"]:
        raise ValueError(f"Official instruction checksum differs for {arm}/{name}")
    score_result = result
    if receipt.get("regrade_result"):
        score_result = load(evidence / receipt["regrade_result"])
        patch = evidence / "regrade" / "verifier" / "agent.patch"
        if sha(patch) != receipt["regrade_patch_sha256"]:
            raise ValueError(f"Regraded model patch checksum differs for {arm}/{name}")
    if (score_result.get("verifier_result") or {}).get("rewards") != receipt["reward"]:
        raise ValueError(f"Official verifier disagrees for {arm}/{name}")
    quality = judge_quality(evidence / "regrade" if receipt.get("regrade_result") else trial, score_result)
    repair = judge_repair(root, row, arm, receipt, trial)
    if repair:
        quality = repair[2]
    for number, wire in enumerate(receipt["wire"]["records"], start=1):
        path = evidence / "wire" / f"{number:05d}"
        for filename, field in (
            ("request.raw.json", "raw_sha256"), ("request.sent.json", "sent_sha256"),
            ("response.raw", "response_sha256"),
        ):
            if field in wire and sha(path / filename) != wire[field]:
                raise ValueError(f"{arm}/{name}/{number} corrupted {filename}")
        for attempt in wire.get("attempts", []):
            raw = path / "attempts" / str(attempt["number"]) / "response.raw"
            if "response_sha256" in attempt and sha(raw) != attempt["response_sha256"]:
                raise ValueError(f"{arm}/{name}/{number} corrupted retry response")
        if arm == "native" and wire.get("raw_sha256") != wire.get("sent_sha256"):
            raise ValueError(f"{arm}/{name}/{number} control input was transformed")
    start = datetime.fromisoformat(result["started_at"])
    end = datetime.fromisoformat(result["finished_at"])
    return {
        "thread": receipt["thread"],
        "regraded": bool(receipt.get("regrade_result")),
        "judge_repair": {"evidence": str(repair[0]), "sha256": sha(repair[0]),
                         "item_id": repair[1].get("item_id", repair[1].get("repair_kind")),
                         "original_reward": valid_score(receipt)} if repair else None,
        "judge_quality": quality,
        "reward": valid_score({"reward": repair[1]["reward"]}) if repair else valid_score(receipt),
        "requests": receipt["wire"]["requests"],
        "provider_attempts": sum(len(r.get("attempts", [r])) for r in receipt["wire"]["records"]),
        "transient_retries": sum(max(0, len(r.get("attempts", [])) - 1) for r in receipt["wire"]["records"]),
        "responses": sum(bool(r.get("complete")) for r in receipt["wire"]["records"] if r["path"] == "/v1/responses"),
        "model_input_tokens": sum(int(r.get("input_tokens") or 0) for r in receipt["wire"]["usage"]),
        "model_output_tokens": sum(int(r.get("output_tokens") or 0) for r in receipt["wire"]["usage"]),
        "usage_unknown_responses": sum(bool(r.get("path") == "/v1/responses" and r.get("complete")
                                       and response_usage(evidence / "wire" / f"{i:05d}" / "response.raw") is None
                                       )
                                       for i, r in enumerate(receipt["wire"]["records"], 1)),
        "cached_input_tokens": sum(int((r.get("input_tokens_details") or {}).get("cached_tokens") or 0)
                                   for r in receipt["wire"]["usage"]),
        "provider_input_peak": receipt["wire"]["peak_input_tokens"],
        "raw_input_bytes_peak": receipt["wire"]["max_raw_input_bytes"],
        "sent_input_bytes_peak": receipt["wire"]["max_sent_input_bytes"],
        "successful_web_judges": receipt["wire"]["successful_judge_calls"],
        "accepted_clm_edits": receipt["wire"]["accepted_edits"],
        "native_compacted": bool(receipt["native"].get("saw_compaction")),
        "protective_compaction": bool(receipt["native"].get("protective_compaction")),
        "wall_seconds": (end - start).total_seconds(),
        "trial_started_at": result["started_at"],
        "trial_finished_at": result["finished_at"],
    }


def write_json(path, data):
    with path.open("x") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def manifest(output, roots):
    with output.open("x") as stream:
        for root in roots:
            for directory, dirs, files in os.walk(root, followlinks=False):
                dirs.sort()
                files.sort()
                base = Path(directory)
                for basename in sorted(set(files) | {name for name in dirs if (base / name).is_symlink()}):
                    path = base / basename
                    relative = str(path.relative_to(root.parent))
                    if path.is_symlink():
                        entry = {"path": relative, "symlink_target": os.readlink(path)}
                    elif path.is_file():
                        entry = {"path": relative, "size": path.stat().st_size, "sha256": sha(path)}
                    else:
                        entry = {"path": relative, "type": "special"}
                    stream.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--all-attempts", type=Path, nargs="*")
    args = parser.parse_args()
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    rows = load(args.run / "plan.json")["tasks"]
    accepted = load(args.run / "accepted.json")
    if accepted["pairs"] != len(rows) or accepted["plan_sha256"] != sha(args.run / "plan.json"):
        raise ValueError("Terminal acceptance is inconsistent with the frozen plan")
    threads = {}
    paired = []
    groups = defaultdict(list)
    previous_end = None
    for row in rows:
        pair = {}
        for arm in ("native", "clm"):
            item = audit_trial(args.run, row, arm, threads.get(arm))
            if previous_end and datetime.fromisoformat(item["trial_started_at"]) < previous_end:
                raise ValueError("Trial overlapped its predecessor")
            previous_end = datetime.fromisoformat(item["trial_finished_at"])
            pair[arm] = item
            threads[arm] = item["thread"]
        values = {"position": row["position"], "domain": row["domain"], "task": row["task"],
                  "native": pair["native"], "clm": pair["clm"],
                  "reward_delta": pair["clm"]["reward"] - pair["native"]["reward"]}
        groups[row["domain"]].append(values)
        paired.append(values)
    if len(set(threads.values())) != 2 or threads != accepted["threads"]:
        raise ValueError("Expected precisely two independent native threads")
    if len(rows) == 65:
        from check_workbuddy_binding import check as check_binding
        contract_path = args.run.parent / "MANAGER_STATE.json"
        original_threads = load(contract_path)["formal_threads"] if contract_path.is_file() else accepted["threads"]
        check_binding(args.run, args.output / "native-task-binding.json", True, original_threads)
    groups["all"] = paired
    stats = {}
    for label, group in groups.items():
        stats[label] = {"pairs": len(group),
                        "reward_delta_mean": statistics.mean(x["reward_delta"] for x in group),
                        "clm_wins": sum(x["reward_delta"] > 0 for x in group),
                        "ties": sum(x["reward_delta"] == 0 for x in group),
                        "native_wins": sum(x["reward_delta"] < 0 for x in group)}
        for arm in ("native", "clm"):
            model = [x[arm] for x in group]
            stats[label][arm] = {
                "mean_reward": statistics.mean(x["reward"] for x in model),
                **{field: sum(x[field] for x in model) for field in (
                    "requests", "provider_attempts", "transient_retries", "responses", "model_input_tokens", "model_output_tokens",
                    "usage_unknown_responses",
                    "cached_input_tokens", "native_compacted", "protective_compaction",
                    "successful_web_judges", "accepted_clm_edits", "wall_seconds",
                )},
                **{field: max(x[field] for x in model) for field in (
                    "provider_input_peak", "raw_input_bytes_peak", "sent_input_bytes_peak",
                )},
            }
    write_json(args.output / "summary.json", {"run": str(args.run), "stage": accepted["stage"],
                                               "threads": threads, "groups": stats})
    write_json(args.output / "paired.json", paired)
    quality = [{"position": pair["position"], "domain": pair["domain"], "arm": arm,
                **pair[arm]["judge_quality"]} for pair in paired for arm in ("native", "clm")]
    write_json(args.output / "official-judge-quality.json", quality)
    if any(item["requires_review"] for item in quality):
        raise ValueError("Official judge technical findings require review before final delivery; see official-judge-quality.json")
    with (args.output / "paired.csv").open("x", newline="") as stream:
        fields = ("position", "domain", "task", "native", "clm", "reward_delta")
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for pair in paired:
            writer.writerow({**pair, **{arm: pair[arm]["reward"] for arm in ("native", "clm")}})
    if args.all_attempts is not None:
        roots = [args.run, *args.all_attempts]
        repair_root = args.run.parent / "judge-repairs"
        if repair_root.is_dir() and repair_root not in roots:
            roots.append(repair_root)
        ledger, totals = all_attempt_ledger(roots)
        write_json(args.output / "all-provider-attempts.json", ledger)
        write_json(args.output / "all-provider-usage.json", totals)
        task_attempts, task_counts = task_attempt_ledger(roots)
        write_json(args.output / "all-task-attempts.json", {"trials": task_attempts,
            "scope": "Observed Harbor trial directories, including incomplete startups; copied directories counted once. Management-gate failures outside Harbor remain in the full archive and are not actor trials."})
        write_json(args.output / "formal-task-attempt-counts.json", task_counts)
        compactions = compaction_ledger(roots)
        write_json(args.output / "all-native-compactions.json", compactions)
        write_json(args.output / "formal-native-compactions.json", [
            event for event in compactions if event["thread"] in accepted["threads"].values()
            and str(event.get("marker", "")).startswith("WB_CODEX_FORMAL_")
        ])
        edits, checked = clm_edit_ledger(roots)
        write_json(args.output / "all-clm-edit-events.json", {"projection_requests_verified": checked,
                   "events": edits, "scope": "All accepted and rejected edit attempts, including failed trials; copied wire events counted once."})
        write_json(args.output / "formal-clm-edit-events.json", [
            event for event in edits if event["thread"] == accepted["threads"]["clm"]
            and str(event.get("marker", "")).startswith("WB_CODEX_FORMAL_")
        ])
        manifest(args.output / "sha256.jsonl", roots)


if __name__ == "__main__":
    main()
