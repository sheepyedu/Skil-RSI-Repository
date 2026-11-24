# Continuity validation

## Record only what makes the run reproducible

- Before acting, record the worktree and resolved release/base ref, the runner or session identifier when observable, current requirement/phase, allowed and forbidden artifacts, and the prior verified state. Inventory staged, unstaged, and relevant untracked paths. For Git, `git status --short --untracked-files=all` alongside staged and unstaged diffs is a useful start. Explicitly inspect expected artifacts under ignored paths if they are in scope. Do not stage, delete, or revert pre-existing work to make an inventory look clean.
- For each accepted or rejected submission, record the source snapshot, result, elapsed time, and evidence. Keep local representative tests, official evaluator F2P/P2P (when defined), and missing or unscored results distinct. Check regressions in already verified dependencies and unauthorized state changes; an earlier successful score does not certify the current tree. Use a disposable snapshot for evaluator operations that mutate state.
- At a boundary, save a minimal recovery record: active requirement; immutable constraints and permitted paths; last verified outcome with source/ref; unfinished changes/checks; one next action. Do not duplicate full logs, keep sensitive information in the record, or treat the record as evidence.
- On resumption, compare worktree/branch and checkpoint identity, verify that an in-flight operation did not run twice, and cross-check the relevant files and tests. Distinguish useful revalidation after changes from redundant repeats. If continuation identity or previous effects are unknown, do not replay destructive or externally visible actions.

## Candidate verification cases (not reported results)

| Fixture | Expected observable behavior |
| --- | --- |
| Existing untracked report beside newly changed tracked code | Detect both; preserve the report and identify the changed paths without resetting or staging them. |
| New dependent phase opens just after context maintenance | Read the current requirement and relevant existing dependency, run the smallest verifying check, and work on the new phase in the same job. |
| Summary says complete; local smoke check passed; unrelated regression or official result still missing | Preserve the distinction; do not report acceptance. Record F2P/P2P outcome or missing evaluator separately. |
| Runtime resumes the same session, then a separate fixture simulates rotation or uncertain state | Resume using verified state in the former. In the latter, fence unsafe retries and separate fresh-session provenance. |

## Attribution

Record timestamps, runtime/version, session IDs and worktree checkpoints, actual skill-body version and exposure when observable, and first meaningful next action. Reporting one run is observational: a worktree snapshot, milestone transition, or different session can explain the same outcome. To isolate the effect of a particular replacement, compare authorized continuations from a cloned, identical task state, runtime, model and remaining budget, changing only the replacement; do not let evaluator details reach the actor. Label such diagnostics separately from official scores.

Sources: [SWE-Milestone scoring](https://arxiv.org/html/2603.13428v4#S5.SS1), [Compact-Bench controlled replay](https://arxiv.org/html/2610.31710#S3.SS4), [CompAct-Bench matched continuation](https://arxiv.org/html/2611.25673v1#S2.SS2), [Compaction and process-constraint loss](https://arxiv.org/html/2610.31778#S4.SS2).

## CLM-specific verification

Use small fixtures for no edit, unchanged, rejected, and actually applied edits. Evidence for an applied edit links revisions to the next effective input; if unavailable, mark unconfirmed. Count native fallback, output eviction, external notes, and rotations separately. A recovery handle must resolve to the same source and return the original or signal truncation; a sentence in a note is not a reliable backup. Add a negative case: do not remove a dependency while its result is pending or its source is inaccessible. Report live input, cumulative provider input, and cache usage separately where available; shorter prompts do not establish cache reuse or lower charges. [CLM §4](https://arxiv.org/html/2609.37725v1#S4); [Folio recovery contract](https://arxiv.org/html/2611.16627v1#S2).

## Revise from outcomes, not from edit counts

Run this skill on a held-out work family before changing the default. Log whether the specific instructions were visible before a decision, whether they were followed, and the effect on verified progress and avoidable rework. Record the first failed or repeated check and its plausible mechanism. Revise one rule at a time; rerun the original case and a different held-out case with the same budget. Keep improvements only if they preserve task outcomes and do not increase unauthorized side effects. A stale source, a newer but non-authoritative claim, and a safe no-op are required negative controls.
