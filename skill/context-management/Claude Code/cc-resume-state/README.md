# Reconcile summaries with the latest state when resuming

## Derivation and applicability
Derived during offline, event-by-event review of native Claude Code long trajectories, including grouped and shuffled task orders. It addresses memory generation, use, feedback, and revision with native file tools, not CLM context-editing interfaces.

Use when: After native automatic compaction, or when resuming the current task from a long conversation.

Related evidence: CC-N1 See [Events and evidence](../../EVIDENCE.md).

## Use and validation status
Read [SKILL.md](SKILL.md) for the procedure, checks, revision loop, and rollback boundaries. This is an unvalidated candidate, not an experimentally proven improvement. It does not grant new tool capabilities or authorization.

For runtime installation, copy only the selected SKILL.md into the corresponding skill directory. Keep this research-oriented README, evidence documents, event locators, and evaluation materials outside the tested agent’s container and retrieval paths to avoid evaluation contamination. Do not load both language versions as separate skills.
