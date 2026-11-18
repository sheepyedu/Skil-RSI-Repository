---
name: cx-feedback-change
description: Use when failure feedback arrives or new evidence overturns a prior.
---

# Maintain feedback-driven rule change records

Applies to Codex. Status: a trajectory-derived candidate skill without independent intervention validation; no score improvement is promised. Use only information allowed for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger

Use when failure feedback arrives or new evidence overturns a prior.

## Generation and use

1. Record the erroneous action, visible feedback, mechanism explanation, and verification status. Do not put an answer supplied by feedback into a general-purpose skill.
2. Distinguish candidate mechanisms such as denominators, aggregation levels, missing values, and `distinct`; validate them on subsequently permitted data.
3. Update the current rule and explicitly invalidate the superseded scope, preserving versions and counterexamples.

## Feedback and revision

Compare independent cases after revision rather than inferring improvement directly from scores across different tasks. Record whether the revision was actually used. Retain the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, first narrow or suspend the rule, then validate the new version. Do not treat success on one task as proof that the skill works.

## Boundaries and rollback

A cause not verified by a rerun must remain a hypothesis. Do not infer a unique mechanism backward from the outcome. If a memory write fails, retain the old version; do not treat a plan as a completed action. Recover only from readable evidence, not recollection. The skill does not expand tool permissions or authorization for external actions.

## Evidence

CX-N5, N6; q49, q53, q98–100. See [Events and evidence](../../EVIDENCE.md) and [Evaluation plan](../../EVALUATION.md).
