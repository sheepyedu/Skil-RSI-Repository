---
name: ccclm-current-policy
description: "Maintain currently valid Claude Code CLM memories when entities change, versions change, or a rule encounters a counterexample."
---

# Maintain a current-rule index for conflicting memories

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
Maintain currently valid Claude Code CLM memories when entities change, versions change, or a rule encounters a counterexample.

## Generate and use
1. Separate evidence logs from current-policy: logs retain observations; the index retains current rules, scope, sources, and status.
2. Locate memories by task family, entity, environment version, and observation time. Read the index first, then necessary evidence.
3. When new evidence conflicts, mark the affected scope of the old rule superseded and retain the original evidence. Do not merely append two contradictory conclusions.
4. Recheck high-risk units, fields, and denominators cheaply against current data. One outcome against the same opponent is insufficient to infer NEVER/ALWAYS.
5. Preserve counterexamples, unresolved items, and source pointers during compression. Do not compress a hypothesis into a fact.

## Feedback and revision
Record incorrect transfer, conflict detection, old-rule retirement, and retrieval costs. Expand scope only when new comparable evidence supports it. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
The current-rule index is not a hidden answer table. Stable methods may transfer; instance values must be checked against the environment. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E4, E5; q39/41/43, q48/54, q67/72, q79/81. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
