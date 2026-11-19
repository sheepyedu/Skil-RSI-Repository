# WorkBuddy paired rollout audit

Research-only. Do not add this file or the underlying tasks to model retrieval in a skill evaluation.

## Scope and method

The final Codex WorkBuddy record has 65 complete pairs (130 scored trajectories) in one fixed order. Align arms by accepted position, task identity, and the official instruction binding; use the accepted raw event timelines, not just the scores. Inspect user instructions, completed model/tool events, relevant read/write receipts, and edits/compactions. For safety-sensitive tasks, inspect context-management metadata only. This is not a word-by-word review of every streaming delta or a replay of each workspace artifact. Position and arm below refer to the final archive's `results/native-task-binding.json`; line numbers refer to that binding's `agent/native.jsonl` unless otherwise stated.

Audit stages separately: **generated** note or checkpoint → **retrieved** and visible → **used** in a decision or action → **verified** effect or failure → **revised** item. A directory listing is discovery, not retrieval; note text returned to a tool is visibility, not evidence of action; a local validation result is not the benchmark's official outcome. No complete multi-task learning loop should be inferred from a current-task fix.

## What changed the skills

- **Preserve verification scope, not a success slogan.** Position 23 CLM lines 196, 301, 365, 391: a modification invalidated an earlier passing test and required repair plus replay. Position 28 native lines 316, 330, 389: a baseline run separated a known failure from the new changes. The CLM arm's broader locally green run did not earn the higher official result. These support revision-bound checks, not an unconditional “run every test” rule.
- **Treat native compaction as a boundary, not a diagnosis.** Native position 31 line 168 contains an in-task compaction; the subsequent workload could still operate on current sources. Before CLM positions 25, 30 and 36, protective compactions preceded both higher and lower paired results. The accepted CLM arm on any position does not imply a model edit occurred there.
- **Recognizing stale state is not retiring it.** Position 36 CLM lines 80 and 125 show a historical note was visible and considered irrelevant. It is still visible at position 43 line 48. This motivates scope/expiry checks; it does not show the note caused a failed task.
- **Queued and applied are different.** Position 1 CLM's cumulative session lines 66–69 show the edit command and immediate status still lacking an accepted edit; the next wire receipt (request 00010) records acceptance. Several later status queries returned only leading characters, which can hide revision and acceptance fields. Inspect named fields.
- **Edited, visible and used are different.** At position 51 (CLM timeline lines 54, 63, 72; next wire receipt 00004) the editor dropped a previous-task batch and kept an older unrelated note. At position 54 (CLM timeline lines 60, 75, 87; next wire receipt 00005) it dropped another previous-task batch and replaced the note. The note was returned in later tools (e.g. 55 lines 72 and 110), but the semantic verification it suggested was not shown in position 55's final checks (lines 202 and 217). A note may work on its originating task without transferring.
- **Receipts describe the integration, not model performance.** At positions 1, 51 and 54 the edit receipts show projected byte changes 144,706→102,601, 288,762→283,774 and 451,936→436,774. Position 54's removed count of 5 is cumulative with position 51 in that projection; its selected batch is 2 items. These are not token, latency or billed-cost reductions. The review records three accepted edits and seven protective native compactions in the CLM arm, versus three automatic compactions in native; some recorded protection belongs to a recovery attempt, not the finally scored trial. Do not collapse these into one count.

## Design references

- [Agent Skills specification](https://agentskills.io/specification) and [OpenAI skill creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md): narrow triggers, concise executable instructions, no research payload in runtime.
- [The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) and [Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents): separate original records, recoverable notes and active context; resume from verified external evidence, not only a summary.
- [What Is This Memory Useful For?](https://arxiv.org/html/2611.03930v1) and [CompactionBench](https://www.microsoft.com/en-us/research/wp-content/uploads/2026/10/CompactionBench_preprint.pdf): test utility on a later action, and account for compaction/cache and recovery costs separately.
- [OpenAI skill evals guide](https://developers.openai.com/blog/eval-skills) and [The Resolution Hypothesis](https://arxiv.org/html/2611.23068v1): inspect execution and artifacts; use holdout cases and replication before selecting a version based on score. None of these sources tests the two skills in this repository.

## Proposed validation (not run)

1. Within each harness, freeze model, runner version, budget and evaluation rubric. Compare no skill vs the appropriate skill, on unseen scenarios and repeated sequences. Include short negative-trigger tasks, a forced interruption, stale path/version, conflicting notes, a missing receipt, and a protected span or rejected edit where CLM applies. Keep the writer blind to held-out tasks. Do not install both languages or both harness skills.
2. Score task outcomes separately from process: triggered only when needed; critical facts retained exactly; pointer resolves in the resumed environment; stale rule does not drive the action; official receipt matches target/version; CLM edit status and next projection agree. Log failures and retries even when no score is issued. Track total input, cached/uncached tokens if observable, latency, and recovery/duplicate work. Judge harmless omission differently from losing a pending action or violating a hard constraint.
3. A passing tabletop check is a format/procedure check, not evidence of uplift. Freeze a rubric and acceptance criteria before running; compare per-sequence outcomes and report variation, not only an aggregate. Version revisions with the failed behavior, changed rule, and a falsifying or counterexample case.

## Tabletop checks applied to the written procedure

| Scenario | Expected decision under the skill |
|---|---|
| Short self-contained question | Do not create a note or edit history. |
| Resume after compaction; old note says “done,” but receipt is missing | Verify the current target and receipt before retrying; retain an uncertain state if unverifiable. |
| An older verified result conflicts with a newer result from another version | Keep both scoped; use the one that matches the current version, or record a recheck. |
| A queued CLM edit is followed by immediate stale status | Do not count it as accepted; check the next applicable request. |
| An editor proposes dropping a bulky but unrecoverable unique receipt | Keep it active; no lossy drop until recovery is proven. |
| A previous note is visible but not used to perform a check | Record visibility, not adoption or uplift. |

These are manual checks of what the text instructs, not execution on a live agent.

## Position-by-position audit

These notes are abstracted observations, not task instructions or answers. No absence claim extends beyond the reviewed event surface.

| Pair | Observation |
|---:|---|
| 1 | Accepted edit at next request, not immediate status. |
| 2 | Different validation coverage; both scores stayed zero. |
| 3 | Empty note listing; native request-failure history matters. |
| 4 | CLM qualified an inadequate comparison baseline. |
| 5 | CLM checked additional cases, without writing a durable note. |
| 6 | Passing local checks did not resolve different interpretations. |
| 7 | Final verification was stated with a bounded scope. |
| 8 | Native compacted, then looked up current files again. |
| 9 | Current wire slice omits events present in cumulative session. |
| 10 | CLM explicitly bounded claims by missing evidence. |
| 11 | Both tested; no durable reuse link to a similar earlier task. |
| 12 | Current primary evidence ruled out alternatives. |
| 13 | Both searched and tested; CLM status output was truncated. |
| 14 | Discovery/status only; no accepted edit. |
| 15 | Repeated source and consistency checks; no written rule revision. |
| 16 | CLM protective compaction; old note unchanged. |
| 17 | Same interface contract, different interpretation of defaults. |
| 18 | No note or editor operations observed. |
| 19 | Search and test iterations did not become cross-task notes. |
| 20 | Directory listing and status did not write memory. |
| 21 | Separate evaluator correction from actor progress. |
| 22 | Computed classifications differed despite completeness claims. |
| 23 | CLM invalidated and reran a formerly passing check after a change. |
| 24 | No compaction or model edit in the pair. |
| 25 | CLM protective compaction; replay-check coverage differed. |
| 26 | No in-task compaction/edit; opposite score direction to preceding pair. |
| 27 | Both considered precedence and unresolved ties; local tests differed. |
| 28 | Native reproduced baseline failures; local green was not official acceptance. |
| 29 | Same outcome with different verification breadth and cost. |
| 30 | CLM protective compaction, then corrected task-local behavior. |
| 31 | Native compacted in-task; CLM retained an older note. |
| 32 | Both read current sources; no proof of carrying earlier facts forward. |
| 33 | No in-task edit; workload differences are descriptive only. |
| 34 | Both respected the task's modification boundary. |
| 35 | CLM separated confirmed findings from unmeasured risk. |
| 36 | CLM recognized its old note as irrelevant but did not retire it. |
| 37 | No edit; more calls did not change the paired result. |
| 38 | Native split conflicting semantics into distinct assertions. |
| 39 | Native found a current local verification capability. |
| 40 | CLM repaired a local update that disturbed unrelated state. |
| 41 | Both left truncated source information unresolved. |
| 42 | Runtime interaction verification differed from syntax checks. |
| 43 | Same local computation did not produce the same result; old note still visible. |
| 44 | Effective-state conditions remained uncertain despite a conclusion. |
| 45 | Protective compaction preceded CLM rereading the current interface; repeated probe failure was not captured for reuse. |
| 46 | Memory/status discovery only; no in-pair edit or compaction. |
| 47 | Assertion feedback led to task-local revision, not durable memory revision. |
| 48 | Both checked memory entry points; no accepted edit or compaction. |
| 49 | Updates to an obsolete task artifact were not cross-task memory. |
| 50 | Protective compaction, path repair and blocked tests co-occurred. |
| 51 | CLM dropped a completed earlier batch and kept the older note. |
| 52 | Native summary retained active decisions and checks; source was re-read. |
| 53 | CLM previewed an older batch without editing or demonstrated use. |
| 54 | CLM dropped an older batch and replaced the note; verified current artifact. |
| 55 | Later instructions narrowed what to replace; CLM note visible without scoped verification. |
| 56 | Both checked current data in-browser; older note visible but not applicable on evidence. |
| 57 | Current contract was checked across processes; repeated environment failure persisted. |
| 58 | CLM previewed a short older batch fragment; no edit or adoption shown. |
| 59 | Rereading the current contract kept it distinct from an earlier task. |
| 60 | Later verified state superseded earlier state within this task. |
| 61 | Protective compaction belongs to a different recovery attempt, not the selected trial. |
| 62 | No explicit in-trial memory operation or compaction. |
| 63 | Request and result differences do not establish a memory mechanism. |
| 64 | An isolated tool failure is not a task- or context-level outcome. |
| 65 | Native looked up a note path; no CLM context operation. |
