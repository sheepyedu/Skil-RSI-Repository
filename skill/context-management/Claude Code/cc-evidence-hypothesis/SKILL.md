---
name: cc-evidence-hypothesis
description: "Separate observations, hypotheses, and rules while preserving counterexamples, for relevant memory operations in long Claude Code trajectories."
---

# Separate observations, hypotheses, and rules while preserving counterexamples

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
Deriving rules from limited feedback, compressing memory, or encountering new observations that conflict with old rules.

## Workflow: generate → use → feedback → revise
Generate: Store tool observations, model hypotheses, and actionable rules separately. Attach supporting and opposing evidence, sample size, scope, and falsification conditions to hypotheses.
Use: Retrieve the latest counterexamples alongside a rule. Perform a minimal check of key values or directions affecting the current action. An unverified explanation must not become FINAL or immutable.
Feedback: When an answer fails, check whether an incorrect rule was faithfully reused before attributing failure to forgetting. A single win or loss does not establish a strategy's effectiveness.
Revise: When evidence conflicts, mark the old rule superseded, retain the reason, and update the active rule. Preserve counterexamples and uncertainty during compression rather than keeping only conclusions.

## Evidence
Related event: CC-N4. See [Events and evidence](../../EVIDENCE.md).

## Validation
Conflict detection rate, number of incorrect hypotheses treated as facts, and performance after rule revision on independent tasks under the same conditions.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
