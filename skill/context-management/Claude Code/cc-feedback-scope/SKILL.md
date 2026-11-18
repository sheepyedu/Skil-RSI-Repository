---
name: cc-feedback-scope
description: "Attach metric scope to feedback; do not infer a unique cause, for relevant memory operations in long Claude Code trajectories."
---

# Attach metric scope to feedback; do not infer a unique cause

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Turning scores, test results, or execution feedback into a long-term skill.

## Workflow: generate → use → feedback → revise
Generate: Record the definition of feedback, sample/year scope, whether it is the final official score, comparison baseline, and visible conditions. Explicitly mark unknown fields unknown.
Use: Compare only metrics with matching definitions and scope. When an aggregate score may depend on several factors, list competing explanations. Do not infer a unique growth rate, city coefficient, or true value of a missing product from a single score.
Feedback: Distinguish successful submission, passing visible tests, and final correctness. Score differences across tasks with different data are not within-task ablations.
Revise: When a clearer scoring definition or new evidence becomes available, correct the old inference and mark dependent rules for revalidation. Preserve the original observation.

## Evidence
Related event: CC-N6. See [Events and evidence](../../EVIDENCE.md).

## Validation
Frequency of mismatched metric definitions, non-identifiable reverse inferences, and gains after repeated evaluation under matching conditions.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
