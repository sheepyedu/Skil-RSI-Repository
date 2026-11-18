---
name: cxclm-scoped-retrieval
description: Use semantic retrieval and scoped memory for memory operations in long Codex CLM trajectories.
---

# Use semantic retrieval and scoped memory

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

Reusing database rules, research estimates, tool methods, or knowledge across instances.

## Procedure

1. Attach scope keys to memory: task family, data version/entity, units, conditions, aggregation level, and observation/inference label.
2. Check these keys against the current task before selectively reading relevant memory. Sharing a task family does not make all conditions transferable.
3. Validate high-risk fields such as units, denominators, null values, and encodings against current tool output. Distinguish verified correct execution from a proposed causal explanation.
4. Store reusable methods separately from instance-specific answers. Keep method indexes in the short note; do not turn a specific answer into a universal rule.
5. Label paths with their workspace, lifecycle, and last verification time. Read back files in the official temporary environment in the next task before relying on persistence. Do not treat archives under `/app` as durable memory. Delete a unique context source only after saving lasting facts in an actually persistent workspace and successfully reading them back.
6. When conditions change, append new evidence and explicitly invalidate the corresponding scope of the old rule, retaining portions that still apply.

## Stop conditions and safeguards

Respect tool budgets. Stable, low-risk fields do not require exhaustive rechecking every time.

## Evidence

Events: CX-C4, CX-C6, CX-C7. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Incorrect reuse caused by omitted conditions; substituting the most recent answer for a calculation; treating a formal `complete` as proof of correctness.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
