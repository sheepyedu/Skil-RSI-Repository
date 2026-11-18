---
name: ccclm-save-before-prune
description: "Before pruning or capacity maintenance in this repository’s Claude Code CLM."
---

# Verify saved state before pruning

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
Before pruning or capacity maintenance in this repository’s Claude Code CLM.

## Generate and use
1. Confirm the current run phase and actual tools. Later phases use mcp__clm__catalog / mcp__clm__prune; native Claude Code does not provide these interfaces. Do not substitute Codex's clm-context.
2. Build a recovery capsule from still-visible tool results: task_id, environment version, phase, confirmed actions, unresolved items, unique new facts, and their sources. Save it with Write/Edit in the persistent workspace, then verify it with Read.
3. Call the current catalog. It returns only ID, bytes, and tools, without content previews. Delete only exchanges that can be explicitly mapped to saved facts or retrievable content; do not delete blindly by size. Retain exchanges when the mapping is unclear.
4. Submit drop according to the actual schema, with at most 40 IDs. The optional note is limited to 4000 characters and completely replaces the old note when supplied. First merge still-valid old note content and indexes for other domains; only omitting note preserves the existing note. Submission does not establish application.
5. Check accepted status in the next catalog or available audit records, and inspect the actual next-request projection. If the ordinary model cannot see the projection, record that verification gap. Recover at least one key fact from a deleted exchange before relying on it.

## Feedback and revision
Record save success rate, consistency of recovered facts, extra retrieval cost, and rejection reasons. When repeated maintenance makes no capacity progress, stop repeated calls, preserve state, and switch to safe recovery. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
Refresh catalog when IDs expire or parameters fail. If an erroneous deletion has taken effect, the current tool does not promise prune reversal. Recover semantics by rereading persistent evidence; if necessary, let the runner restore a snapshot. Do not claim the original context was restored. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E1, E6; q43, q93, q97. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
