# Four categories of context-management skills (candidate v0.1)

Model-assisted semantic review of the repository's raw long trajectories produced executable candidates. No new on/off ablations were run; these skills are not established score improvements. Earlier candidates are now in [initial-skills](../initial-skills/README.md).

## Direct use
Each child SKILL.md is an independent Markdown skill. Copy only selected skill directories into the target framework's supported skill location, or read them when their triggers apply. Keep README, EVIDENCE, EVALUATION, references, and other research documents outside the tested container and runtime search paths. Do not inject the entire research report; prefer a small task-relevant selection. Research links are for repository review, not required runtime dependencies. Both CLM categories apply only to this repository's custom interfaces, not official native features.

## Claude Code

- [Separate a short active-memory index from evidence logs](Claude%20Code/cc-active-memory-index/SKILL.md)
- [Separate observations, hypotheses, and rules while preserving counterexamples](Claude%20Code/cc-evidence-hypothesis/SKILL.md)
- [Attach metric scope to feedback; do not infer a unique cause](Claude%20Code/cc-feedback-scope/SKILL.md)
- [Reconcile summaries with the latest state when resuming](Claude%20Code/cc-resume-state/SKILL.md)
- [Scope memories by entity and environment](Claude%20Code/cc-scope-and-version/SKILL.md)
- [Retrieve by semantic anchors, not historical line numbers](Claude%20Code/cc-semantic-memory-address/SKILL.md)
- [Verify that memory writes succeed](Claude%20Code/cc-verify-memory-write/SKILL.md)

## Claude Code CLM

- [Maintain capacity with headroom and measurable progress](Claude%20Code%20CLM/ccclm-capacity-maintenance/SKILL.md)
- [Accept only tool receipts as evidence of completion](Claude%20Code%20CLM/ccclm-confirm-action-receipts/SKILL.md)
- [Maintain a current-rule index for conflicting memories](Claude%20Code%20CLM/ccclm-current-policy/SKILL.md)
- [Do not treat score differences across tasks as strategy ablations](Claude%20Code%20CLM/ccclm-metric-feedback/SKILL.md)
- [Verify saved state before pruning](Claude%20Code%20CLM/ccclm-save-before-prune/SKILL.md)
- [Distinguish the persistent workspace from the official task environment](Claude%20Code%20CLM/ccclm-workspace-protocol/SKILL.md)

## Codex

- [Separate raw evidence from aggregate state](Codex/cx-evidence-state/SKILL.md)
- [Maintain feedback-driven rule change records](Codex/cx-feedback-change/SKILL.md)
- [Read progressively for the current decision](Codex/cx-progressive-memory-read/SKILL.md)
- [Define a native-compaction recovery contract](Codex/cx-resume-checkpoint/SKILL.md)
- [Constrain retrieval by entity and version](Codex/cx-scoped-retrieval/SKILL.md)
- [Verify the memory lifecycle](Codex/cx-verify-persistence/SKILL.md)

## Codex CLM

- [Preserve conflicts and recheck conditionally](Codex%20CLM/cxclm-conflict-recheck/SKILL.md)
- [Validate compression effects separately from task outcomes](Codex%20CLM/cxclm-measure-edit-effect/SKILL.md)
- [Manage the active index lifecycle](Codex%20CLM/cxclm-note-lifecycle/SKILL.md)
- [Use semantic retrieval and scoped memory](Codex%20CLM/cxclm-scoped-retrieval/SKILL.md)
- [Structure state and separate evidence layers](Codex%20CLM/cxclm-structured-state/SKILL.md)
- [Compress transactionally and verify by reading back](Codex%20CLM/cxclm-transactional-edit/SKILL.md)

## Findings from this review
- The largest risks include not just forgetting but preserving false explanations, mixing entities, treating temporary paths as persistent, and failing to retire obsolete rules.
- Claude CLM q43 directly shows incorrect reconstruction of queried facts after deletion. This occurred after submission, so it does not establish score harm on that task.
- Native Claude disk notes grew in both sequences; conversation compaction is not note deduplication.
- Codex CLM includes cases of rereading and using notes after accepted edits. Having an archive and retrieving effectively remain different things.
- “Verify first” reminders can be violated; completion needs tool receipts. Runner gates are proposed changes, not implemented features of this package.
- Same-sequence native Codex scored 54/100 and CLM 53/100. A single-run difference does not establish superiority; lower input does not imply lower uncached cost.

See [evidence and coverage](EVIDENCE.md), [evaluation protocol](EVALUATION.md), and [reviewable indexes](references/README.md). Research indexes must not be injected as runtime memory.
