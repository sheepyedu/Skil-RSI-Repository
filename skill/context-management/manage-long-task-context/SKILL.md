---
name: manage-long-task-context
description: Preserve and retrieve trustworthy working state during long, tool-heavy tasks and dependent milestones. Use when a task must survive a context limit, compaction, a handoff, repeated investigation, or a change that may invalidate earlier notes.
---

# Manage context across a long task

Before a transition, preserve enough evidence to recover the active task, continue the next action, and verify the result. Treat context, the current workspace, and durable notes as different sources with different update times.

## Recover the active state

- Re-read the current user requirement or authoritative task brief. Establish the workspace, document revision, data version, Git commit, or other identity that scopes the work.
- Recover recent actions and pending side effects from actual outputs. Check in-flight requests, staged and unstaged changes, partial writes, and unfinished verification when applicable.
- Fetch the smallest evidence that resolves the next decision. Start with an index or saved pointer, then open a path, section, test log or source record. Use a whole transcript when reconstructing a disputed sequence requires it.

## Create and use scoped memory

Write to an approved durable location when information is hard to recover, spans a boundary, or would be expensive to reconstruct. Record:

- **Scope** including task or milestone, source revision, and any relevant time or environment.
- **State** including what was verified, what changed, and the evidence location.
- **Open items** including uncertainties, failures, pending actions and the smallest useful next check.
- **Exact data** only where the next action depends on a non-reproducible error, a requirement, a test invocation, a decision, or another physical identifier. Prefer a recoverable pointer for bulky output.

Read back important writes. Retrieve notes for a purpose, then use the source or a narrow check to decide whether each note still applies. Promote a discovered routine only after the procedure and its preconditions have worked, with evidence that another case can meet them.

## Choose one maintenance action

| Situation | Action |
|---|---|
| Context is sufficient and the next decision depends on recent evidence | Continue the task. Record only state that needs to persist. |
| Old reproducible observations dominate the window and the runtime supports selective editing | At a quiet boundary, retain needed constraints, unresolved feedback and stable pointers. Remove redundant completed exchanges using the supported interface. Preserve tool call/result integrity. |
| The conversation needs a substantial reset or the runtime lacks a selective editor | Save and check the continuation state. Use supported native compaction or the authorized handoff mechanism. |
| A pending side effect or ambiguous change may already have happened | Read the receipt or authoritative state before resuming, repeating or pruning. |

Use context pressure, dependency on exact evidence and recovery cost together. A token threshold is a cue to assess pressure. Native compaction and custom editing have different effects on retained history and cache reuse. Keep the user's session and tool constraints in force.

## Handle feedback and conflict

1. Compare a conflicting note with the current authoritative source or a reproducible check. Distinguish changed scope, changed reality, a stale note and an unresolved ambiguity.
2. Update the affected claim with its source and revision. Mark the old claim superseded within that scope and put the new pointer where retrieval will find it first. Keep the correction history when later actions may have used it.
3. Check downstream effects on work and verification. Recheck the smallest affected action, plus a representative regression when earlier behavior must survive.
4. Confirm continuation. For a memory write, verify it can be read back and retrieved. For a runtime edit, verify acceptance and the next effective input if the runtime exposes it. For a compaction or handoff, verify the current objective, unresolved checks and workspace state are still recoverable.

Compare initiative, task quality and cost with observable outcomes. Useful measures include retained checks, repeated lookups, requests, input size and cache misses. Judge less traffic together with target coverage and regressions.

For examples of durable records, stale-state recovery and accept/reject checks, read [examples](references/examples.md).
