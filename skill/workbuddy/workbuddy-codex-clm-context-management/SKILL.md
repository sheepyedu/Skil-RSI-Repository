---
name: workbuddy-codex-clm-context-management
description: Safely edit active context in Codex CLM when large completed spans crowd out active work or repeated context carries measurable cost. Use only when a runtime exposes CLM editing tools and their contract; for ordinary Codex or short tasks, use a recoverable checkpoint instead of rewriting context.
---
# Codex CLM: make small, verifiable edits

Treat the projected model context, a durable checkpoint, and the execution record as distinct. An edit receipt is not proof of what the next request contained. An automatic native compaction is not a model-authored CLM edit. Never edit the underlying execution record as a substitute for editing active context.

## Decide whether to edit

- Name the pressure and the next decision. Edit only when a specific inactive span competes with current work, the runtime signals pressure, or repeated old content is measurably costly. Before treating an old note as global, ask whether a later task outside that domain would need it; prefer a scoped locator when the answer is no. Don't edit for its own sake; leave the active tail intact during an open tool call, unresolved action, or uncertain recovery.
- Inspect the live tool contract and current context revision. Read the status fields for revision, last accepted edit, candidate IDs/sizes, and protected records; don't truncate the first N characters. Confirm the size unit/limit and whether a note replaces or appends. If the capability is absent or the tool state is ambiguous, use a small durable checkpoint and let the native runtime handle compaction. Do not guess at endpoints or operations.
- Classify each candidate: **keep** exact constraints, unresolved state, recent tool receipts and unrecoverable evidence; **index** recoverable bulky evidence with scope, version and a stable locator; **omit** duplicates and completed, reproducible output. Keep a stale item out of the active note once replacement is verified; unresolved contradictions stay labelled with the cheapest recheck.

## Save, edit, verify

1. Save the minimal checkpoint before any lossy edit: `scope/version | objective + exact constraints | verified decisions and pointers | unanswered question/pending action | next verification`. Read it back and verify the most important pointer from the scope that will resume. If evidence cannot be recovered, keep it active. If saving is unauthorized or fails, do not drop it.
2. Edit one coherent region using fresh IDs. For a whole-note replacement, build from the current note; retain still-valid entries and explicitly retire those made stale. Cut duplicated output before unique evidence. Avoid broad pruning or touching protected/active records.
3. Treat a queued submission as pending. Check the receipt or status of the next request that can apply it, then the next visible context revision or projection, if available. Verify that the critical facts are still usable and that the intended span is gone or shorter. If projection is unobservable, record that limit and do not claim validation. A rejected edit can be retried only after identifying why and refreshing the view, not resubmitted blindly.
4. If an edit loses state, stop editing. Recover via the verified checkpoint or source, mark the broken pointer or note stale, and resume only after the next decision is grounded. Do not invent a rollback, reconstruct exact data from a vague note, or assume an archived span is retrievable.

## Use the memory and revise the rule

At the next consequential action, distinguish evidence located, evidence actually read, and action verified. Retrieve by current scope and exact entity first, not by narrative similarity alone. Newer text does not win a conflict unless it is valid for the same scope; mark stale versions or carry a recheck condition. Record whether the edit was offered, accepted, visible, and useful, and whether native compaction also occurred. Compare input/cache, latency, and recovery cost only where measured. Note whether counts are per edit or cumulative, and record bytes separately from tokens. An accepted edit or a better final score alone does not establish benefit.

Example: a long diagnostics dump is recoverable from a revision-pinned artifact. Preserve the exact failing check and its pointer; drop duplicate output only after the pointer is verified. If the next request no longer contains a pending action or a hard constraint, recover it first instead of removing more context.
