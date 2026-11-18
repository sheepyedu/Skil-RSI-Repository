---
name: ccclm-metric-feedback
description: "When generating or revising skills from Claude Code CLM feedback."
---

# Do not treat score differences across tasks as strategy ablations

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
When generating or revising skills from Claude Code CLM feedback.

## Generate and use
1. Record task/data/seed, budget, metric definition, time of visibility, and evaluation interval. Distinguish immediately visible scores from final official metrics.
2. Record score differences between tasks only as observations; do not conclude that a strategy is necessarily better.
3. Retain competing explanations for failures, such as lost information, incorrect old assumptions, environmental changes, or differences in metric definitions.
4. Mark a new strategy candidate. Plan paired or held-out validation with a frozen configuration rather than writing a permanent rule.

## Feedback and revision
Link each revision to its triggering evidence and falsification conditions. Rules without subsequent validation remain candidates. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
Raw discovery-set values may remain in isolated research evidence, but must not become answer-bearing skills read during testing. New paid experiments require an explicit budget. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E3; q97–100. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
