---
name: cxclm-note-lifecycle
description: Manage the active index lifecycle for memory operations in long Codex CLM trajectories.
---

# Manage the active index lifecycle

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

Switching tasks, compressing in batches, or adding a new phase's state to the note.

## Procedure

1. Divide the note into a durable index, current active state, and unresolved items. Allow only one `task_id/version` in the current state.
2. On a new task, first close the preceding task's state as completed, aborted, or awaiting verification, retaining necessary receipt pointers. Do not simply append another “Current task” entry.
3. Put full details of old domains on disk and retain retrievable paths in the index. Do not continually fill the active note with recoverable numbers unrelated to the current goal.
4. Before submission, check for contradictory `pending`, `no actions yet`, and `completed` markers, unnecessary accumulation, and violation of the byte limit.
5. At a new session or anchor change, check whether CLM has reset and recover from genuinely persistent files. Do not assume the gateway note persists across launches.

## Stop conditions and safeguards

The current interface does not support note-only edits. If there is no suitable drop candidate, update the disk index first and replace the note at the next valid edit opportunity. Do not delete important exchanges merely to change wording.

## Evidence

Events: CX-C5, CX-C6. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Two current tasks; stale state misleading subsequent actions; indefinitely growing summaries of old domains; assuming the note survives a restart.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
