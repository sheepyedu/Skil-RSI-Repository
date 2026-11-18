---
name: cc-resume-state
description: "Reconcile summaries with the latest state when resuming, for relevant memory operations in long Claude Code trajectories."
---

# Reconcile summaries with the latest state when resuming

Applicability: Native Claude Code long conversations, using its existing Read/Grep/Write/Edit tools and persistent notes; no CIM dependency.
Status: Candidate skill derived from offline trajectory review; score improvement has not been validated.

## Trigger
After native automatic compaction, or when resuming the current task from a long conversation.

## Workflow: generate → use → feedback → revise
Generate: Save the task ID, current phase, completed actions and evidence, pending work, remaining budget, output protocol, and key numerical values in persistent notes. Update only when the phase changes.
Use: On resumption, compare the summary against the latest retained messages and current tool state, favoring newer verified results. Before submitting, check whether submission already occurred; do not repeat completed actions merely because the summary says to do them.
Feedback: Record specific repeated queries, repeated submissions, missed phases, or stale-summary incidents. Distinguish completion status from answer quality.
Revise: Add frequently omitted fields to the state card and remove narrative that does not help recovery. If no state interface exists, retain uncertainty rather than repeating side-effectful actions without authorization.

## Evidence
Related event: CC-N1. See [Events and evidence](../../EVIDENCE.md).

## Validation
Post-resumption repeated-action rate, missed-pending-item rate, and recovery tool-call count. The native mechanism retaining the conversation tail is not controlled by this skill.
Use on/off comparisons with the same task order, multiple random seeds, and held-out tasks not used to derive the skill. Do not treat the original trajectories as new generalization validation.

## Rollback and authorization
Preserve the pre-change memory version and evidence index. If a new rule conflicts with current tool facts, suspend it first and restore from sourced records. Do not restore task state confirmed to be obsolete. Mark information unknown when no recovery evidence exists; do not fabricate it. This skill does not expand authorization for external actions.
