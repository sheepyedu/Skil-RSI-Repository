---
name: workbuddy-claude-code-clm-context-management
description: Manage active context in a custom Claude Code CLM runner when long work may exceed capacity or needs a verified handoff. Diagnose failures before trimming, preserve recoverable state, and verify the next request and action. Use only when the runner exposes the relevant controls; not a native Claude Code feature.
---
# Claude Code CLM: trim for the next action, verify delivery

Separate the raw execution record, the active session view and the actual model request. Treat a model edit, native compaction, controller maintenance, and manual intervention as four different event sources. Never edit the raw transcript directly or bypass a runtime limit.

## Prefer task boundaries for elective memory editing

- Schedule non-urgent persistent-memory rewrites and context pruning after the previous task is delivered and all tool calls have settled, or before the next task starts reading new material or making its first task-execution call. This is a timing preference, not a requirement to edit at every boundary or a proven score improvement.
- Normal tool use, evidence capture, short task-local notes and necessary checkpoints may continue during a task. Edit memory mid-task only when a context limit is approaching, critical state is at imminent risk of loss, or progress cannot continue; use the smallest reversible intervention, then resume the task.
- Before editing, retain unfinished obligations, exact constraints, evidence locators and a recoverable prior version or rollback pointer. Apply the save/readback checks below, and verify the next task's effective context before substantive work. Defer elective editing if safe application and verification cannot fit at the boundary.

For Claude Code CLM, inspect the actually applied note and any controller-added pruning, not just the model proposal; keep those event sources distinct.

## Diagnose before removing anything

| Signal | Response |
|---|---|
| Input pressure or a growing tool result | Narrow the next read or compact a verified inactive span; reserve headroom for the next tool result and required response. Check within long work, not just at task boundaries. |
| Output cap | Preserve partial artifacts and the uncompleted step; resume or revise the output budget only if authorized. Trimming history does not raise that cap. |
| Unclosed stream, timeout, or refusal | Inspect the actual provider/CLI status. Preserve the attempt and check partial effects before retrying an eligible transient error; do not retry policy refusals or treat missing data as success. |
| Complete response that just states a plan | No delivery yet. Check tool receipts and the requested artifact; if work continues, name the next authorized action and its acceptance check. |

## Preserve, edit, and prove recovery

1. Before a lossy edit, preserve the goal, exact constraints, current target/version, pending side effects, last confirmed state, and the next action with its check. Keep adjacent tool calls and their results linked. Retain unique evidence if its locator can't be reread from the resuming environment.
2. Inspect the actual editor contract and protected range. Check allowed IDs and the byte/token budget before applying. If a note is over budget, rewrite it from the required fields; do not truncate from one end. Prefer retiring one irrelevant closed span or replacing a duplicate with a scoped locator. Keep the active tail. If editing is unavailable, use a verified checkpoint and the runner's supported recovery; never invent an operation or use a broad rewrite by default.
3. Check acceptance and the next visible request or resumed view, where observable. Verify one exact critical fact and one unresolved state, then confirm the intended action or artifact happened. For a rule with precedence or exceptions, test a case where changing the order would change the decision. A smaller request, a changed file hash, or a successful stop signal does not prove retained facts were used. A verifier startup error is a separate state from a completed check that failed. If the view is unavailable, report that limit; if a critical anchor is missing, stop trimming and recover it from the verified source.
4. Retrieve by task, artifact and version. If an old entry conflicts with current evidence, preserve the unresolved uncertainty or retire the old entry after confirming scope. Update only the failing rule after feedback, with an invalidation condition and a recheck; keep task trivia out of durable memory. Record whether the note was actually used. Keep recovery attempts and budget changes visible; do not report controller maintenance as learned model behavior.

Example: after a large report run stops, the last intact reply promised an export. Verify whether the output exists, matches the target version, and opens before claiming delivery. If it is absent, recover the pending export step; compact only if input pressure actually blocks it.
