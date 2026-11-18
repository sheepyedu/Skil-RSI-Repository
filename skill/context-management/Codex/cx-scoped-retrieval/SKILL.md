---
name: cx-scoped-retrieval
description: Use before reusing opponent profiles, schemas, units, or cross-task rules.
---

# Constrain retrieval by entity and version

Applies to Codex. Status: a trajectory-derived candidate skill without independent intervention validation; no score improvement is promised. Use only information allowed for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger

Use before reusing opponent profiles, schemas, units, or cross-task rules.

## Generation and use

1. Locate memory by entity, task family, environment version, and time range; preserve observation/inference labels.
2. Transfer methods to a new entity, not another entity's profile. Confirm current units, fields, and null semantics using low-cost checks.
3. When changes occur, invalidate the affected scope of old rules while preserving still-valid portions and counterexamples.

## Feedback and revision

Record cross-entity misuse, version misuse, and irrelevant retrieval. File-read counts are not evidence of effective learning. Retain the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, first narrow or suspend the rule, then validate the new version. Do not treat success on one task as proof that the skill works.

## Boundaries and rollback

Absence of a disk file does not mean absence of memory; current conversation evidence remains usable. Current facts take precedence over old generalizations. If a memory write fails, retain the old version; do not treat a plan as a completed action. Recover only from readable evidence, not recollection. The skill does not expand tool permissions or authorization for external actions.

## Evidence

CX-N3, N6; q64, q73, q78, q88, q46/51/53–55. See [Events and evidence](../../EVIDENCE.md) and [Evaluation plan](../../EVALUATION.md).
