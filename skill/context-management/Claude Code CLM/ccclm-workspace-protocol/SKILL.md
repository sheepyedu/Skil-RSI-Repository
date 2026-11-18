---
name: ccclm-workspace-protocol
description: "When switching tasks, recovering after maintenance, or encountering path/action-parameter errors."
---

# Distinguish the persistent workspace from the official task environment

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
When switching tasks, recovering after maintenance, or encountering path/action-parameter errors.

## Generate and use
1. Identify the current namespace first: local Read/Edit/Write/Bash operate on persistent notes; benchmark.act enters the official task environment.
2. Record cwd, data version, and the actual action schema in the recovery card. Do not treat the official /app as long-term storage.
3. If a path is missing, check the environment before searching. For protocol-validation failures, correct only the fields; do not redo tasks that already succeeded.
4. Record tool errors separately from domain conclusions. Revalidate temporary environment paths for the next task.

## Feedback and revision
Track namespace misuse, parameter retries, and missing notes. Record environment-version changes in the current index. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
Do not change isolation settings, reset the official environment, or migrate secret credentials without authorization. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E5; q43, q55, q98–100. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
