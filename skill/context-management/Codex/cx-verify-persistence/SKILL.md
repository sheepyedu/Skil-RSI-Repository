---
name: cx-verify-persistence
description: Use when writing or reading long-term memory across tasks.
---

# Verify the memory lifecycle

Applies to Codex. Status: a trajectory-derived candidate skill without independent intervention validation; no score improvement is promised. Use only information allowed for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger

Use when writing or reading long-term memory across tasks.

## Generation and use

1. Distinguish the local persistent workspace from the official temporary environment accessed through `benchmark.act`. Record memory location, lifecycle, and source.
2. Immediately read back fields or a content summary after writing. Confirm again in the next task or after recovery before marking `persistent_verified`.
3. If a file is missing, recover from accessible original evidence and mark it `reconstructed`. A previous path appearing in the conversation does not prove the file still exists.

## Feedback and revision

Measure cross-task read-back success rates and reconstruction overhead. Keep only persistent files with a real use. Retain the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, first narrow or suspend the rule, then validate the new version. Do not treat success on one task as proof that the skill works.

## Boundaries and rollback

Do not reset a production environment to test persistence. Native Codex does not have this repository's CLM exact-deletion interface. If a memory write fails, retain the old version; do not treat a plan as a completed action. Recover only from readable evidence, not recollection. The skill does not expand tool permissions or authorization for external actions.

## Evidence

CX-N1; q97–100, q1–30. See [Events and evidence](../../EVIDENCE.md) and [Evaluation plan](../../EVALUATION.md).
