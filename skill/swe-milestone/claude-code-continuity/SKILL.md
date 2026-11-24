---
name: claude-code-continuity
description: Preserve verified engineering state across dependent milestones, native Claude Code compaction, and same-session resume. Use for sustained work on a persistent repository, not unrelated tasks.
---

# Engineering continuity in native Claude Code

1. Freeze the scope before changing anything. Identify the repository/worktree, branch and HEAD, active requirement, allowed and prohibited paths, and existing staged, unstaged and relevant untracked artifacts. Preserve pre-existing changes. A clean Git diff does not prove the scope is clean.
2. Treat milestones as phases of the same job. Confirm what the current phase is and which dependencies were actually verified. Carry forward the active requirement, unresolved test or assumption, and one concrete next step. Do not start a fresh session or mark a phase done just to tidy the context.
3. If the runtime compacts or a same-session resume is needed, recover from the scoped workspace and existing evidence, not from the summary alone. Confirm the session and worktree identity when available. Compare tracked and untracked state with the previous checkpoint, then run the smallest relevant check or inspect the existing result under the same state. Read a prior raw excerpt only when needed. Correct stale notes.
4. Before reporting completion, distinguish tests for the new behavior (fail-to-pass, or F2P), regression tests for previous behavior (pass-to-pass, or P2P), and actual evaluator results. Report representative local checks as such. Check the full scope, including untracked artifacts. Do not treat a successful test command, submission, or compacted summary as evaluator acceptance by itself.
5. Fence recovery. If the environment or session identity changed unexpectedly, a process has an uncertain side effect, or there is repeated no progress, preserve the state and identify the blocker before retrying. Do not use a new session, reset the worktree, broaden scope, or re-submit unless the authorized protocol permits it. If rotation is allowed, label it as a fresh session.

**When evidence conflicts:** current source authority and scope beat recency. Amend only the affected fact and retain prior valid scopes. Do not write the host session store, permission configuration, or grader to repair context; use an authorized runtime path.

This skill provides guidance, not access to editable live context or a reason to invoke manual compaction. Follow host defaults and explicit operator decisions. Read [validation](references/validation.md) when investigating failed recovery, regressions, or attribution.
