---
name: cx-evidence-state
description: Use when repeatedly accumulating observations, matching entities, or using historical statistics.
---

# Separate raw evidence from aggregate state

Applies to Codex. Status: a trajectory-derived candidate skill without independent intervention validation; no score improvement is promised. Use only information allowed for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger

Use when repeatedly accumulating observations, matching entities, or using historical statistics.

## Generation and use

1. Save raw observations with time, source, and candidate entities. Use stable `entity_id`, counts, statistics, and hypothesis status for aggregate state.
2. When conflicts arise, preserve alternative associations and define recheck conditions. Do not merely write `uncertain` and continue merging unconditionally.
3. Recheck, split, or undo when comparable new evidence becomes available. Temporary absence does not mean a long-lived entity has expired.
4. Read the aggregate index first; read raw evidence when a conflict needs explanation.

## Feedback and revision

Check whether statistics can be recomputed from evidence, the rate at which incorrect merges are undone, and reading costs. Retain the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, first narrow or suspend the rule, then validate the new version. Do not treat success on one task as proof that the skill works.

## Boundaries and rollback

Do not require every domain to retain its entire history forever. Retain only permitted evidence that could affect decisions. If a memory write fails, retain the old version; do not treat a plan as a completed action. Recover only from readable evidence, not recollection. The skill does not expand tool permissions or authorization for external actions.

## Evidence

CX-N4; q8, q18, q24–30. See [Events and evidence](../../EVIDENCE.md) and [Evaluation plan](../../EVALUATION.md).
