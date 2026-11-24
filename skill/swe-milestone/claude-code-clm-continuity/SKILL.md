---
name: claude-code-clm-continuity
description: Preserve verified engineering work across dependent milestones and runtime-supported live-context edits in Claude Code with a CLM-compatible extension. Use only when that extension is available.
---

# Engineering continuity with editable context

1. Freeze the scope: identify the repository/worktree, branch and HEAD, current requirement, allowed and prohibited paths, and any staged, unstaged, or relevant untracked artifacts. Preserve existing changes and working state. Treat milestones as phases of one continuing job.
2. Inspect only runtime-supported context controls. With measured context pressure, prefer a safe boundary: relevant state is verified or recoverable, and no pending tool result or uncertain side effect depends on the text to be changed. A milestone alone is not a trigger. Leave context unchanged when there is no useful and safe edit. Let a hard runtime limit follow its supported fallback instead of trying to override it.
3. Keep the active goal and constraints, current requirement, last verified state and source, open assumptions/failures, and one executable next action. Reduce redundant material first. Retain exact detail if a live dependency needs it or when its original cannot be recovered; otherwise keep stable source references and record any truncation. Do not modify authoritative instructions or break tool-call/result pairs.
4. Call an edit applied only when runtime evidence shows it entered the next effective model input. Track accepted, rejected, pending and no-op outcomes separately; an external note, ordinary output trimming, native compaction, and session rotation are distinct. Do not invent an editing command or label the code work as complete because context changed.
5. After resuming, reconcile the session and worktree identity, tracked/untracked changes, the latest requirement and the smallest relevant verification. Distinguish new-behavior tests (F2P), regressions (P2P), local representative tests, and evaluator results. Fence retries and rotation: preserve state on ambiguity and use a fresh session only when the authorized protocol permits it; report it distinctly.

**When evidence conflicts:** current source authority and scope beat recency. Amend only the affected fact and retain prior valid scopes. Do not write the host session store, permission configuration, or grader to repair context; use an authorized runtime path.

Read [validation](references/validation.md) if provenance is unclear or if comparing edit behavior. This skill does not implement context editing or change runtime permissions.
