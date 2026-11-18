---
name: cxclm-measure-edit-effect
description: Validate compression effects separately from task outcomes for memory operations in long Codex CLM trajectories.
---

# Validate compression effects separately from task outcomes

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

Selecting or revising a compression strategy, or claiming cost or success-rate improvements.

## Procedure

1. Record each edit revision, dropped groups, current task, acceptance status, original request size, and projected size. State whether each measurement is cumulative or marginal to this edit.
2. Define recovery checks: key facts remain retrievable, current obligations are retained, entities and versions are not confused, and downstream steps actually reference the information.
3. Record `observed_feedback` visible to the model at the time separately from post-hoc `audit_reward`, including metric definition, scope, and time. Do not conflate Composite with the final official result.
4. Report total input, cached input, uncached input, output, tool calls, and latency separately. Reduced input alone does not establish lower cost or faster execution.
5. For failures, check whether an incorrect assumption predated the edit, whether feedback was visible, and whether information was actually lost before discussing compression causality.
6. Evaluate candidate skills using frozen versions, held-out tasks, and same-order/multiple-seed controls. Explicitly record when a no-edit counterfactual is missing.

## Stop conditions and safeguards

New paid tests must stay within the user's explicit budget and account permissions. Do not add expensive experiments without authorization.

## Evidence

Events: CX-C3, CX-C5, CX-C7. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Drawing conclusions solely from success counts of 53 versus 54; treating 100 dependent tasks as independent repetitions; treating original size minus cumulative projected size as the benefit of a single edit.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
