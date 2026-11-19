---
name: workbuddy-claude-code-context-management
description: Preserve and verify the working state of a long native Claude Code task across automatic compaction, interruption, or handoff. Use when repeated tool output is crowding out active work or a resumed task could repeat an action. Not for short self-contained work or direct edits to a session log.
---
# Native Claude Code: make the next step recoverable

Keep the smallest checkpoint from which another turn can make the next decision safely. A transcript, a task checkpoint, and durable project memory have different lifetimes. Do not write a note just because you have reached a new turn.

## Prefer task boundaries for elective memory editing

- Schedule non-urgent persistent-memory rewrites and context pruning after the previous task is delivered and all tool calls have settled, or before the next task starts reading new material or making its first task-execution call. This is a timing preference, not a requirement to edit at every boundary or a proven score improvement.
- Normal tool use, evidence capture, short task-local notes and necessary checkpoints may continue during a task. Edit memory mid-task only when a context limit is approaching, critical state is at imminent risk of loss, or progress cannot continue; use the smallest reversible intervention, then resume the task.
- Before editing, retain unfinished obligations, exact constraints, evidence locators and a recoverable prior version or rollback pointer. Apply the save/readback checks below, and verify the next task's effective context before substantive work. Defer elective editing if safe application and verification cannot fit at the boundary.

For the native CLI, updating a memory file does not rewrite already-loaded conversation text or control automatic compaction; verify the next task actually loads the intended version.

## Control what comes back from tools

- Name the decision before reading. Ask for the relevant file section, bounded log tail, result count, or failing assertion instead of dumping a directory or full result. Keep the exact clause, constraint, or error field that affects the next step. Store large recoverable evidence only in a permitted location; keep its scope, revision, and locator.
- When compaction or interruption is near, checkpoint the current goal and prohibitions, workspace/revision, latest verified state, pending actions, and one next action plus its acceptance check. Distinguish **drafted**, **attempted**, **verified**, and **blocked**. Save only to approved storage and read it back. If it won't survive the boundary, hand off the essentials explicitly.
- Use the observed runtime's context diagnostics or focused compaction where available and authorized; do not assume an interactive slash command is callable as a tool. If another large result will immediately refill the window, change how you fetch it before compacting again.

## Resume by checking state, not trusting the summary

1. Match the current task, workspace and version. Read the checkpoint, then confirm the smallest decisive fact from the live artifact or authoritative source. Before repeating an action, check for its receipt or partial effect.
2. If a remembered rule conflicts with current evidence, compare scope, version and effective date first. Prefer the applicable primary source. Mark a superseded rule inactive; keep a pointer if it explains a decision. Leave genuine conflicts unresolved with a recheck condition. Never carry task outcomes, permissions or temporary paths into a different scope by default.
3. Verify completion at the right layer. Check the actual artifact, completion receipt, and relevant test. A successful response, a plan, or a syntax check is not a changed artifact or passed behavioral check. If the verifier did not run, label the result unevaluated rather than treating it as an implementation failure. After changing the artifact, recheck the affected behavior before carrying its prior status forward.
4. Revise only the part that failed. Record whether evidence was absent, unavailable, stale, ignored, or used incorrectly. Promote a note to project memory only if it has a repeatable use case, scope, source and invalidation condition. Leave task-specific progress in the checkpoint.

Example: a handoff says a report was saved and validated, but the restored directory holds a different revision. Check the exact artifact and rerun the affected acceptance check; keep the old receipt as history rather than repeating the upload or calling the new version verified.
