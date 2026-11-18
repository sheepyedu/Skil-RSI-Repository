---
name: cx-resume-checkpoint
description: Use when a long native Codex conversation is interrupted, automatically compacted, or handed over between phases.
---

# Define a native-compaction recovery contract

Applies to Codex. Status: a trajectory-derived candidate skill without independent intervention validation; no score improvement is promised. Use only information allowed for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger

Use when a long native Codex conversation is interrupted, automatically compacted, or handed over between phases.

## Generation and use

1. Save five sections: `active-state`, `executed-receipts`, `next-step`, `reusable-evidence`, and `unresolved`, with the current task, remaining budget, and protocol.
2. After resuming, verify the summary against retained tail messages and current status. First check whether submission has already occurred.
3. Continue only unfinished obligations. Separate proposed actions from executed actions. Keep old-domain details behind a file index rather than continually adding them to the summary.

## Feedback and revision

Record duplicate side effects, omitted obligations, and recovery call counts. Report successful continuation separately from final scores. Retain the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, first narrow or suspend the rule, then validate the new version. Do not treat success on one task as proof that the skill works.

## Boundaries and rollback

The skill cannot control the exact timing of native compaction or guarantee summary completeness. In a conflict, prefer more recent trustworthy receipts. If a memory write fails, retain the old version; do not treat a plan as a completed action. Recover only from readable evidence, not recollection. The skill does not expand tool permissions or authorization for external actions.

## Evidence

CX-N2; q38, q75. See [Events and evidence](../../EVIDENCE.md) and [Evaluation plan](../../EVALUATION.md).
