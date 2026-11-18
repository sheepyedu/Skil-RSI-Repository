---
name: cxclm-conflict-recheck
description: Preserve conflicts and recheck conditionally for memory operations in long Codex CLM trajectories.
---

# Preserve conflicts and recheck conditionally

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

New and old observations about the same entity clearly conflict, two entities may have been incorrectly merged, or associations run in opposite directions across groups.

## Procedure

1. Record fact A and fact B separately, each with its source and time; do not overwrite them with an unconditional average.
2. Explicitly label explanations such as same-entity noise, different entities, and environment drift as candidates. Preserve the next piece of evidence that could distinguish them.
3. Put recheck triggers in the active note, such as recurrence of broad/narrow bimodality, repeated cross-region reversals, or sensitivity of the current answer to the merge decision.
4. Once triggered, read the original evidence before comparing candidate models. Preserve uncertainty when the evidence is insufficient; do not promote a suspected conclusion to a fact.
5. Preserve both the conflict and the recheck path during context edits. Determine expiry by entity and environment, not merely because something has not appeared recently.

## Stop conditions and safeguards

Do not retain every stale instance. Keep conflicts that could change later decisions. Do not search indefinitely for resolved, inconsequential conflicts.

## Evidence

Events: CX-C3, CX-C7. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Writing only `uncertain` without ever rechecking; always merging nearest neighbors; generalizing one group's correlation into a universal rule.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
