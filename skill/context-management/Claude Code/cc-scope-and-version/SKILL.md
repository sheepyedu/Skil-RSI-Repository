---
name: cc-scope-and-version
description: "Scope memories by entity and environment, for relevant memory operations in long Claude Code trajectories."
---

# Scope memories by entity and environment

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Switching opponents, repositories, database instances, or task families, or encountering different meanings for identically named fields.

## Workflow: generate → use → feedback → revise
Generate: Bind each memory to its family, entity, schema/version, observation time, and evidence path. Separate methods from instance-specific answers.
Use: At the start of a new task, check the current entity, schema, units, budget, and tool protocol. Transfer methods; transfer numbers or field interpretations only after matching scope and rechecking. Do not assume that an identical column name guarantees an identical unit.
Feedback: When evidence contradicts a rule, first check whether the object or version changed. Do not put observations about A into B's profile.
Revise: Specify expiration conditions, retain evidence for old versions, and remove old rules from the active set. Do not present retrospective conjecture about a task as a rerun-validated result.

## Evidence
Related event: CC-N5. See [Events and evidence](../../EVIDENCE.md).

## Validation
Cross-entity contamination count, obsolete-schema reference count, and revalidation costs and benefits.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
