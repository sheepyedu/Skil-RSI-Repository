---
name: cc-active-memory-index
description: "Separate a short active-memory index from evidence logs, for relevant memory operations in long Claude Code trajectories."
---

# Separate a short active-memory index from evidence logs

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Notes growing steadily, duplicate conclusions across logs/profiles, or conflicting rules.

## Workflow: generate → use → feedback → revise
Generate: Maintain a short active index and detailed evidence logs using available native file tools. Each active rule includes its scope, evidence references, confidence, and invalidation conditions. Do not assume CLM CIM tools exist.
Use: Retrieve active rules for the current entity/task by default, expanding evidence when necessary. During compression, remove duplicate narrative first; preserve current task state, unresolved items, key counterexamples, and reconstruction paths.
Feedback: Check before and after compression: What is the next step in the current task? What are the key constraints? Where did each rule come from? When must it not be used? If these questions cannot be answered, retain the original text or restore the evidence.
Revise: Append evidence for new facts, make targeted updates to active rules, and invalidate old versions. Periodically merge synonymous file headings without deleting unique facts. Record automatic conversation compaction separately from on-disk note organization.

## Evidence
Related event: CC-N7. See [Events and evidence](../../EVIDENCE.md).

## Validation
Active-memory length, unique-fact coverage, counterexample retention, and retrieval cost; shorter alone does not mean success.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
