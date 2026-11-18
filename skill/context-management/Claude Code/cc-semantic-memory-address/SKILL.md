---
name: cc-semantic-memory-address
description: "Retrieve by semantic anchors, not historical line numbers, for relevant memory operations in long Claude Code trajectories."
---

# Retrieve by semantic anchors, not historical line numbers

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Long files that are continually appended to, or mixed task families and entities.

## Workflow: generate → use → feedback → revise
Generate: Build a short index: family/entity/version/topic → file and unique heading. Treat line numbers only as coordinates for the current read.
Use: Locate a task ID or unique heading with Grep, then Read the surrounding text. Confirm the entity and version before citing it, and confirm anchor uniqueness before writing. If no relevant result is found, broaden the search once; do not substitute a neighboring topic for the requested memory.
Feedback: Record whether retrieval happened before a decision or after its result. A post-result Read counts only as preparation for editing, not knowledge retrieval preceding success.
Revise: Update the index or split files when headings and entities become misaligned. Retain old evidence paths, and do not permanently cache line numbers that shift as content is appended.

## Evidence
Related event: CC-N3. See [Events and evidence](../../EVIDENCE.md).

## Validation
Correct-topic hit rate, repeated-read count, and effective retrieval rate before decisions.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
