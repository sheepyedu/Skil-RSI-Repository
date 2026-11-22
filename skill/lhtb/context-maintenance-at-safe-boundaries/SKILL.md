---
name: context-maintenance-at-safe-boundaries
description: Keep long-running agent work recoverable during context pressure, compaction, or handoff. Use when deciding whether to remove tool history, writing or recovering a checkpoint, or resolving a remembered fact against a changed artifact. Skip routine short tasks.
---

# Maintain context at safe boundaries

**Default: keep working.** A reminder is an invitation to assess, never an instruction to edit. Do not turn every tool result into maintenance. Avoid editing while a command, investigation, or external write has an unresolved outcome.

## Decide: keep, checkpoint, or edit

1. **Check need.** Use actual runtime pressure, a task boundary, or a known recovery need. Cumulative billed input is not available context. If pressure is low and nothing will be lost, continue without editing.
2. **Identify one replaceable span.** Choose a complete, verified exchange with no open tool call or unresolved decision depending on its raw details. Keep hard constraints, current artifact identity, unconfirmed work, near-term dependencies, and evidence not safely available elsewhere. If there is no safe span, do not edit it.
3. **Prove recovery first.** Record the exact decision-critical fact, or reopen its source from the environment that will resume the work. Confirm entity/scope, revision or digest, and that the locator will still be readable when needed. If a location will expire or its lifetime is unknown, retain the raw exchange or an approved durable copy. A basename match is not evidence.
4. **Write the smallest usable checkpoint.** Include the objective and hard constraints; last validated state and test; specific unresolved issue or next action; plus only the scoped facts and exact references needed to resume. Read back a newly written checkpoint before dropping source text. Store no secrets, hidden evaluator material, or unsupported claims as facts.
5. **Apply only through a supported interface.** If a live editor is available, use a fresh revision, remove only complete eligible exchanges, and verify the applied receipt. When possible verify the effective next model input. If the editor is absent or rejects the edit, preserve evidence and use the runtime's normal continuation and compaction. Do not infer a successful edit from assistant text or a Bash invocation.

## Resume and revise

- First reconcile the checkpoint with the current artifact or live state. Inspect uncertain prior writes with a read-only check before retrying. A receipt or memory entry isn't proof of the current effect.
- Reopen the smallest necessary source, then make one substantive, verifiable next action. If a new authoritative revision conflicts, update only its effective scope and preserve distinct historical or unrelated facts. If authority or version is unresolved, mark uncertainty and avoid destructive updates.
- One short pressure cue may be useful when there is a new eligible opportunity. Let no-op count as a good decision. Rearm after meaningful progress, a phase change, or a reset in pressure. Do not stack reminders to maximize edit count. Native fallback remains separate.
- Review actual verification and any recovery rework. Keep a revision only if a held-out case shows it preserves the right evidence without creating avoidable work. See [validation](references/validation.md) for the smallest offline checks.
