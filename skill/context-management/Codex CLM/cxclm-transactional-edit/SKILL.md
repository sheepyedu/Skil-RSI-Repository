---
name: cxclm-transactional-edit
description: Compress transactionally and verify by reading back for memory operations in long Codex CLM trajectories.
---

# Compress transactionally and verify by reading back

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

Old tool exchanges have grown long, completed phases can be externalized, and current unfinished obligations already have state records.

## Procedure

1. Run `clm-context status` and read the revision, current note, and editable list. Select old exchanges semantically rather than deleting blindly by byte size.
2. For candidate exchanges, retain task/entity, source, completed actions, current state, unresolved questions, exact file paths, and recovery commands. Save exact values to disk first and verify recovery through actual reads.
3. When necessary, run `clm-context show ID` for a candidate to save the visible exchange. `show` omits reasoning, so it is not a completely lossless backup.
4. Build a complete replacement note that merges still-valid content from the old note. Only omitting `--note` preserves the existing note. Do not omit indexes for other domains that still need to be retained.
5. Submit `clm-context edit --drop ID1 ID2 --note '...'`. Separate multiple IDs with spaces; replace example IDs with current real IDs. The submission receipt only means the edit is queued. After the next model request, run status to confirm that `last_edit` is `accepted`. If rejected, reread the revision and candidates before proceeding; do not reuse stale IDs.
6. Select at least one key fact from a dropped exchange, read it back from a file, and verify it before relying on it again. Stop repeated status polling after success.

## Stop conditions and safeguards

The note limit is 8192 UTF-8 bytes. Drop must be nonempty and the projection must strictly shrink. User/developer messages and the latest complete tool group are protected; do not try to bypass these protections.

## Evidence

Events: CX-C1, CX-C5. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Acceptance without a recovery test; a path exists but cannot be parsed; replacement note omits an old domain; treating cumulative before/after byte differences as savings from this single edit.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
