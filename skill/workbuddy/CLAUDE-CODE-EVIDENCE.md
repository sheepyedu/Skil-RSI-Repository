# WorkBuddy Claude Code: offline paired rollout audit

Keep this file and the benchmark records out of evaluated runtime retrieval. Only the selected `SKILL.md` is needed at runtime.

## Scope

Read the final `formal-02-resume-09` record: 60 accepted pairs and 120 selected trajectories. Align each arm by frozen task and accepted receipt; inspect the completed trajectory steps and relevant raw tool, maintenance, and recovery events. Inspect safety-sensitive tasks only at the level of context and execution metadata. This is not a word-by-word review of every streaming delta or a replay of all artifacts. No benchmark tools were executed for this review. The position/arm locators below are relative to the accepted evidence directories in the final archive. For historical attempts, use the linked incident record rather than the final score alone.

Retain five distinct checks: **generated** a note → **visible/read** in a later request → **used** to change a decision or action → **verified** what happened → **revised** based on feedback. A changed transcript, a retained note, a successful provider response and a completed benchmark result are different events. Task-local revisions do not establish cross-task learning.

## Evidence that shaped the skills

- **Separate action sources.** The [fixed result and audit](https://github.com/sheepyedu/Skil-RSI-Repository/blob/4e9a0351fc2b036eced4774e82e2b9625e031dec/Claude%20code%20CLM/WorkBuddy%20Bench/2026-11-18/RESULTS.md) record 28 native auto-compactions, 39 CLM between-task session writebacks and zero accepted in-task CLM edits. All 39 accepted maintenance receipts used a budget fallback: the maintenance model proposed removals, and the runner could also select additional pairs or archive material; this is not 39 episodes of autonomous in-task editing. The reported score difference is −1.23 points in this single fixed sequence. Accepted actor input totals mix context size and number of calls (222.55M vs 94.32M tokens; 2,482 vs 1,303 closed requests), not an isolated editing effect.
- **A smaller projection and a resumable session are different.** Before task 3, model selections left a projected 536,627 bytes; the controller stopped before opening the next task. Recovery used whole completed tool exchanges and archived old result payloads; the later projection was 109,384 bytes. Before task 4 there were candidate IDs outside the permitted set, and before task 7 the note exceeded the byte budget. The recovery path had explicit checks and preserved the originals. Do not use arbitrary tail truncation or reissue an invalid edit blindly.
- **Keep the cause of a stop explicit.** Task 15's original native attempt hit the output cap (`finish_reason=length`) and was ungraded. Both arms were rerun from their task-14 checkpoints with a higher shared cap. In contrast, task 48 CLM crossed local input capacity mid-task despite its previous history being below the between-task byte trigger; task 56 native also hit local input capacity and later tied the retained CLM score after recovery. These are not measurements of an optimal threshold. Preserve failed attempts and any asymmetry in recovery. [Incident and recovery log](https://github.com/sheepyedu/Skil-RSI-Repository/blob/4e9a0351fc2b036eced4774e82e2b9625e031dec/Claude%20code%20CLM/WorkBuddy%20Bench/2026-11-18/INCIDENTS.md)
- **Completion needs an action or artifact.** In the selected positions 43, 51–53 and 60, the CLM arm returned a complete plan-only reply with zero tool invocations. Position 43 adds a trace-level case to the four listed in the report. At position 43, `agent/cc-output.txt` lines 14 and 18 show the plan and a CLI success result; `chat-gateway/0000/response.raw` records `finish_reason=stop`. Positions 52–53 had no new between-task maintenance. This supports checking action and artifact, not attributing the stop to history length or maintenance.
- **A verifier startup error is not a failed behavioral assertion.** Scanning the 64 available `test_output.txt` logs found 14 execution records (seven paired positions: 4, 11, 17, 23, 34, 36 and 59) with `Permission denied` starting the verifier, all recorded as zero. No correction for those selected results was found in the reviewed archive. Keep the frozen scores and flag the failures separately; they are not 14 confirmed implementation failures. Compare artifacts or run a separately authorized, frozen grader audit before inferring actor quality.

- **Generation, reading, and revision did not form a loop.** In positions 1–20 the native notes directory was empty. The CLM note directory reached 17 task artifacts at position 2 and stayed byte-identical through position 20; there was evidence of search at positions 10 and 17, not feedback-driven revision. Before positions 9 and 12 the proposed notes were truncated and lost later task sections. A persisted file or proposed note is not a usable memory contract.

- **A shorter rule can be wrong even when it sounds plausible.** Position 27 CLM ATIF steps 7, 16 and 21 apply source priority before deciding whether a conflict remains. The proposal in position 29's `maintenance/.../model-edit.json` put conflict rejection first. The proposed summary is not equivalent; there is no evidence that it was applied by a later task. Check a decision boundary where reversing precedence changes the outcome before promoting a summary.

## What we borrowed from outside the benchmark

- [Claude Code skills](https://code.claude.com/docs/en/skills), [memory](https://code.claude.com/docs/en/memory), and [commands](https://code.claude.com/docs/en/commands): clear activation cues; native diagnostics and focused compaction only where observable; project memory is separate from an active session.
- [Anthropic: The components of agent memory](https://www.anthropic.com/research/components-of-agent-memory) and [Harness design for long-running application development](https://www.anthropic.com/research/harness-design-long-running-apps): separate source evidence from a small handoff, then verify the actual result after recovery.
- [Benchmarks Are Surprisingly Compaction-Friendly](https://arxiv.org/abs/2610.31778) and [CompactionBench](https://www.microsoft.com/en-us/research/wp-content/uploads/2026/10/CompactionBench_preprint.pdf): evaluate retention on dependent tasks and account for cache and recomputation; static token savings are not an operational result.
- [The Resolution Hypothesis](https://arxiv.org/html/2611.23068v1) and [OpenAI skill evals](https://developers.openai.com/blog/eval-skills): separate candidate generation from validation; test behavior and artifacts on unseen cases and repeat the comparison. None of the sources validates these two skills.

## Proposed tests, not executed on an agent

Freeze model, harness, environment, native compaction policy and budgets inside each comparison. Use held-out unrelated tasks and dependent long sessions. Compare skill on/off; for CLM mechanism studies separately identify model proposal, applied edit, runner fallback, and operator intervention. Include an in-task oversized result, an output-cap stop, an interrupted stream, a valid plan-only response, stale version/path, a verifier that never starts, and a resumed action with an existing receipt. For each case score: exact critical fact retained; locator works; stale item not used as rule; required action actually occurs; artifact meets the same criterion; and retries, input/output, cache and recovery cost reported at the right layer. Tabletop review only checks that the instructions lead to distinct decisions.

## Pair-by-pair observations

Each row covers both selected arms unless scoped otherwise. Observations are abstractions, not benchmark instructions or solutions.

| Pair | Observation |
|---:|---|
| 1 | CLM persisted task artifacts; native had no note files. Artifacts are not reusable rules. |
| 2 | CLM saved and reread working artifacts; the persistent folder grew to 17 files. |
| 3 | Native compacted; CLM model selections alone did not meet the runner's budget. |
| 4 | Both self-checked; the recorded zeros came with verifier startup errors. |
| 5 | Current artifact was revised from checks; no durable memory revision observed. |
| 6 | Native compacted; CLM runner intervened before task start; effects not isolated. |
| 7 | Over-limit generated note and shorter applied note were not equivalent. |
| 8 | Both used current source rules rather than treating earlier task artifacts as authority. |
| 9 | The later note segments were lost mechanically; both selected results still passed. |
| 10 | CLM searched persistent files and explicitly bounded unsupported claims. |
| 11 | Native compacted; local checks cannot resolve a verifier startup failure. |
| 12 | Later sections of the proposed note did not appear in the applied note. |
| 13 | Both verified this task; no lower-scope result was promoted to a checked reusable rule. |
| 14 | A shorter note fitted the actual budget without truncation. |
| 15 | Original output-cap stop and same-budget replay are separate attempts. |
| 16 | Controller archived older material before the task; no accepted in-task edit. |
| 17 | Both searched old notes without useful authority; verifier did not start. |
| 18 | Current evidence drove the task; no persistent feedback update was observed. |
| 19 | Several task-local repair-and-test cycles did not change durable notes. |
| 20 | Native compacted; CLM runner fallback edited old history before launch. |
| 21 | CLM corrected a faulty local assertion against the source. |
| 22 | Readback exposed an invented rule boundary; CLM restored the source semantics. |
| 23 | Both produced and checked artifacts; selected graders failed to start. |
| 24 | CLM maintenance removed additional completed tool exchanges. |
| 25 | Runtime feedback led to revised expectations and repeated checks. |
| 26 | A fallback maintenance event and score difference co-occurred; no content attribution. |
| 27 | The task applied source precedence first; a later proposed summary reversed it. |
| 28 | Native compaction did not preclude matched scores; CLM preserved separate paths. |
| 29 | Both missed some acceptance conditions; CLM maintenance also pruned completed pairs. |
| 30 | Both passed some checks despite a zero aggregate; replay did not cover full acceptance. |
| 31 | CLM kept distinct categories of missing and stale states and reread the artifact. |
| 32 | Both agreed on major result categories, but local checks did not establish full correctness. |
| 33 | Only native compacted in this task; request and score differences are descriptive. |
| 34 | Both honored the protected implementation boundary; neither verifier started. |
| 35 | CLM checked real viewports rather than inferring all behavior from source. |
| 36 | Artifacts were self-checked; both recorded zeros were verifier startup failures. |
| 37 | Both passed despite different native compaction and maintenance events. |
| 38 | CLM reported a test environment limit; some combined states went unchecked. |
| 39 | CLM revised the artifact after real browser feedback and checked it again. |
| 40 | Both passed despite substantial between-task CLM maintenance. |
| 41 | Both reread the artifact and left truncated source material unresolved. |
| 42 | Both revised from present-state evidence, with different acceptance outcomes. |
| 43 | Complete CLM plan-only reply; no tool invocation or actual delivery. |
| 44 | Both distinguished drafts, scope and effective dates; checks remained partial. |
| 45 | Passing local tests did not establish full contract coverage in either arm. |
| 46 | CLM maintenance included runner-added removals; score attribution is not established. |
| 47 | CLM corrected an assertion after a current-task check; both passed. |
| 48 | CLM capacity recovery was an intervention, not a model-authored in-task edit. |
| 49 | Editing a stale skill was the current deliverable, not evidence of cross-task learning. |
| 50 | Both rechecked the interface and passed; not the same outcome as Codex. |
| 51 | CLM ended with a plan and zero tool calls; native produced and checked the artifact. |
| 52 | The CLM plan-only outcome recurred without new maintenance. |
| 53 | No new maintenance or CLM execution; native performed behavioral checks. |
| 54 | Both revised the artifact; unequal verifier denominators limit direct interpretation. |
| 55 | Later instructions replaced selected parts, not the entire earlier record. |
| 56 | Native recovered from capacity failure; both selected attempts passed. |
| 57 | Both revalidated the current contract in a separate process. |
| 58 | A saved screenshot is evidence, not a durable reusable rule. |
| 59 | More historical lookup or local self-tests did not substitute for a running verifier. |
| 60 | CLM returned only a plan; native produced and reread the requested report. |
