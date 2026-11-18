---
name: ccclm-capacity-maintenance
description: "Before tool calls likely to return large results, or when the runner triggers capacity maintenance."
---

# Maintain capacity with headroom and measurable progress

Applicability: Claude Code CLM. Status: Candidate skill derived from trajectory review, not independently validated through intervention; score gains cannot be promised. Use only information permitted for the current task. Do not put evaluation answers or future submissions into the skill.

## Trigger
Before tool calls likely to return large results, or when the runner triggers capacity maintenance.

## Generate and use
1. Read the current phase's context window, output budget, and maintenance threshold. These are runner settings; do not treat the historical 120k threshold as a universal constant.
2. Reserve room for the next tool result and reply. Save current state before selecting reclaimable exchanges.
3. After small prune batches, check capacity changes, accepted status, and fact recoverability. Do not loop indefinitely over catalog calls or repeated maintenance echoes.
4. Distinguish raw requests from projected requests, and cumulative removals from the current edit's marginal removals. Report the cost of maintenance itself.
5. If undeletable headers or user history dominate usage, stop ineffective pruning, report the capacity lower bound, and use an authorized safe recovery plan.

## Feedback and revision
Record maintenance rounds, no-progress exits, uncached input, output, and recovery quality together; do not optimize only bytes. Preserve the pre-change version, evidence sources, and applicability conditions. When a counterexample appears, narrow or suspend the rule before validating a new version. Do not treat one successful task as proof that the skill works.

## Boundaries and rollback
Later memory-only rounds are triggered by runner thresholds, not fully autonomous. JSON pruning is not SCR or KV-cache reuse. If a memory write fails, retain the previous version and do not treat a plan as success. Recover only from readable evidence, not recollection. This skill does not expand tool permissions or authorization for external actions.

## Evidence
CCLM-E6; 40 accepted edits; see EVIDENCE for the multi-phase configuration. See [Events and evidence](../../EVIDENCE.md) and [Validation plan](../../EVALUATION.md).
