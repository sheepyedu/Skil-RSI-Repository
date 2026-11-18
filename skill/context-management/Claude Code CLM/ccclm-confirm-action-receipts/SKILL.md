---
name: ccclm-confirm-action-receipts
description: "When summarizing tasks, writing completion facts into memory, or responding to stop/status reminders."
---

# Accept only tool receipts as evidence of completion

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
When summarizing tasks, writing completion facts into memory, or responding to stop/status reminders.

## Generate and use
1. Distinguish planned, submitted, and confirmed for key actions, binding them to task_id and action ID.
2. Upgrade to confirmed only on the basis of an actual tool result matching the current task. A narrative claim that an action was executed cannot substitute for benchmark.act.
3. Before writing a task result, check status/the latest receipt. Record Write/Edit success separately from task-action success.
4. If status shows incomplete work, perform the remaining actions according to the current protocol without repeating confirmed side effects.
5. If the same error recurs after a reminder, propose a runner-level completion gate. Until that gate exists, do not claim the prompt has solved the problem.

## Feedback and revision
Track premature completion claims, omitted actions, and falsely recorded successes. Do not judge receipt gating by whether a task wins or loses. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
If the tool has no status query, retain unknown and first read available receipts. Do not resend a non-idempotent action merely to verify it. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E2; q75, q86, q96. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
