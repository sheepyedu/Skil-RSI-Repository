# Initial context-management skills

These 10 initial candidate skills were distilled from analysis of the repository's long-running trajectories. Each is saved separately in Markdown so it can be read for the relevant situation or copied into your skill-loading workflow.

## Contents

1. [Write a task-state card before compaction](01-task-state-card/SKILL.md)
2. [Store observations, hypotheses, and rules separately](02-evidence-hypothesis-layers/SKILL.md)
3. [Check feedback definitions before revising experience](03-feedback-definition-check/SKILL.md)
4. [Reuse methods, not instance-specific answers](04-method-instance-separation/SKILL.md)
5. [Reconstruct file state after a failed edit](05-file-edit-recovery/SKILL.md)
6. [Retain verifiable values and directions in summaries](06-numeric-direction-consistency/SKILL.md)
7. [Distinguish model-editing loss from transport corruption](07-transport-integrity-diagnosis/SKILL.md)
8. [Confirm the storage lifecycle first](08-storage-lifecycle/SKILL.md)
9. [Bind every observation to an entity, not just a section in a shared file](09-entity-binding/SKILL.md)
10. [Locate by title or entity rather than storing unstable line numbers](10-semantic-retrieval/SKILL.md)

## Usage

1. Select a small number of relevant files by their triggers; do not inject the entire set into context every round.
2. Treat the procedures as candidate strategies. Actual tools, paths, and permissions remain determined by the runtime environment.
3. When compacting, retrieving, or writing back, record which skill was used, its extra cost, and the outcome to enable comparison.
4. Freeze this version first, compare it with the native baseline on unseen instances, and then decide whether to retain, revise, or withdraw it. Performance again on the original discovery set is not direct evidence of generalization benefits.

## Boundaries

- The original experiment used two orders of the same 100 tasks: 200 task-runs, not 200 independent tasks.
- The 19 compactions were triggered by native Claude Code thresholds; the model wrote summaries and autonomously read and wrote notes. This is not a full reproduction of CLM autonomously choosing when to edit context.
- These are v0.1 candidates with no verified success-rate or performance-improvement guarantees. They contain no answers to specific test tasks.
- Skill 7 is an engineering diagnostic procedure for situations with log visibility. The other skills likewise grant no additional permissions. This directory contains Markdown content; it does not mean the skills are automatically installed as native Claude Code skills.
- Suggested validation: fix the model, budget, and task conditions; use multiple seeds; separately measure task success, raw API tokens, latency, retrieval hits, tool retries, and incorrect knowledge reuse. Keep discovery, development, and final test sets separate.

## Bilingual organization and migration

This directory was migrated from the former `初始 skill/` directory. Each skill now resides in its own subdirectory as `SKILL.md`, accompanied by a README explaining its derivation stage and applicability. The v0.1 content and usage boundaries are retained; this reorganization does not represent new experimental validation. This is the English edition; the [Chinese edition](../../skill_zh/initial-skills/README.md) has a matching structure. Original trajectories and archive locations are unchanged. Research evidence and evaluation materials must not be copied into the evaluated runtime environment.
