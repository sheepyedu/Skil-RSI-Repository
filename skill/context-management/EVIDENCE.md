# Evidence, scope, and strength of conclusions

## Units and coverage
Source repository snapshot: `13a6306eb7ec47f44fd6cd88c08b0d25017c2f88`. The original generation stage added skills and review artifacts without changing trajectories or earlier skills. This bilingual reorganization moves those documents, not the underlying trajectories.

Five long sequences contain 500 officially scored executions of the same 100 tasks, not 500 independent problems. The restored directories contain 502 cases including retries; do not confuse them with scored executions. Native Claude grouped/shuffled each contain 100; Claude CLM, native Codex, and Codex CLM each contain 100. Archive byte/hash checks covered all restored files.

- Native Claude: per-task notes diffs, all 335 file calls/results, and state segments around all 19 automatic compactions; replayed notes writes matched snapshots for 200/200 tasks. Not every thinking token or repeated large output was read verbatim.
- Claude CLM: 101 case results, 66 file diffs, raw/projected differences and surrounding responses for all 40 accepted edits, with focused rereading of anomalous chains. Maintenance failures were reviewed at request level. Not all 680 repeated histories or every thinking token were read verbatim.
- Native Codex: actions and completion feedback for 100 tasks, 64 memory commandExecution records, all spectroscopy updates/SQL, and both compactions; repeated SSE bytes were not reread.
- Codex CLM: semantic evidence for the first 50 tasks and all 19 edits; visible actions, tool results, memory, and four edits in the latter 50 tasks. Sales-generation logic was read, but each task's 75 output rows were not audited number by number. Three paired cases use result turn IDs, not native turn ordinal alignment.

This was model-assisted semantic review plus programmatic indexing, not a human audit or a new causal experiment.

## Reproduction
Original archives retain their repository locations: grouped/shuffled in the root split ZIP; `Claude code CLM/archive/CLAUDE_CODE_CLM_ROLLOUTS.tar.zst`; `Codex CLM/trajectories/{NATIVE_CODEX_ROLLOUTS,CODEX_CLM_ROLLOUTS}.tar.zst`. After extraction, use source paths in the references indexes. Claude case-level line numbers refer to that case's `native/native-cli.jsonl`; Codex line numbers refer to archive-root `native.jsonl`. Locators below do not include evaluation answers.

## Claude Code
|Event|Source locator|Supported finding|Not established|
|---|---|---|---|
|CC-N1|grouped051 L10941/10947; shuffled094 L573|Summary TODOs may lag the retained tail; recovery needs both|Compaction made the answer wrong|
|CC-N2|grouped040 L13916/14066/14094; shuffled087 L9307/9321/9327/17263/17320/17322|Unread-state/anchor errors can recover through Read then correct Edit|Disk files disappeared|
|CC-N3|shuffled045 L1166; 047 L273; 056 L191/193/195|Fixed line numbers are unreliable; semantic lookup chains can work|A later mistaken read caused an earlier failure|
|CC-N4|grouped001–030; 013 L2270|Failures occurred in the first 30 tasks without compact; hypotheses hardened prematurely|Compaction was the main failure cause|
|CC-N5|shuffled039 L1036 and 045 L1168; grouped046/050/051/052|Entity attribution, schema, and units require scope|Every contamination necessarily lowers scores|
|CC-N6|shuffled036,057; grouped099/100|Feedback led to revisions, but metric definitions and causality must be distinguished|Cross-task scores are ablations|
|CC-N7|Complete end-of-task notes for both sequences|Final character counts 115603/132002; zero net decreases in total end-of-task size|Every internal Edit was append-only|

## Claude Code CLM
|Event|Source locator|Supported finding|Not established|
|---|---|---|---|
|CCLM-E1|memory-mcp/chain/upstream/0014 response,0015 edit/raw/clm,0018/0019 response; case043|Pruning before note writing changed an already queried fact into an allegedly unqueried one, persisting false provenance|Score harm on this task: submission had already occurred; no later same-family test|
|CCLM-E2|case075,086,096|Completion was narrated prematurely even after a verification reminder; q86 recurred without prune|Every occurrence was caused by pruning|
|CCLM-E3|case097–100 notes and result|Immediate Composite and official actual_performance differ in definition; final strong rules lack subsequent validation|Flat generally outperforms growth|
|CCLM-E4|case039/041/043,048/054,067/072,079/081|Old claims remain alongside counterexamples; explicit supersedes is needed|All old evidence should be deleted|
|CCLM-E5|case051/054/056,055; coding031–037|Successful version rechecks exist; coding tasks show future-git/test shortcut risks|These scores measure general context capability|
|CCLM-E6|40 accepted edits; late phase 57 catalog/39 prune/37 accepted; q93/q97 rejections|Catalog lacks semantic preview; IDs and arguments must be checked|Accepted means semantically lossless|

Configuration boundary: the original 200k window blocked execution; rescue used 262144 and later 393216. The last 58 tasks used input>=120k to trigger memory-only maintenance; thinking settings also changed. These stages are not a fixed-configuration, purely autonomous policy. The first 3 accepted edits used an early Bash path and the latter 37 used MCP. This package makes only the established late MCP protocol executable; check the interface before use in early runs.

## Native Codex
|Event|Source locator|Supported finding|
|---|---|---|
|CX-N1|q97–100; q98 native L9563; q1–30|Official /app resets between tasks; persistence must be tested|
|CX-N2|Archived rollout compacted L1102(q38),L2541(q75)|Summaries retain active state; valid resumption does not imply scoring success|
|CX-N3|q64 L6383,q73,q78,q88|Conversation evidence is called by entity; no disk write does not imply no learning|
|CX-N4|q8 L656,q18 L1474,q24–30|Observations and association hypotheses need layers; progressive reads are observable but benefits are not isolated|
|CX-N5|q49 L5056/5165,q53 L5437/5443|Aggregation/denominator errors cannot directly be attributed to forgetting|
|CX-N6|q46,q51,q53–55,q98–100|New versions and observations can revise priors|

## Codex CLM
|Event|Source locator|Supported finding|
|---|---|---|
|CX-C1|q39 L4318/4323/4333; q43 L5315/5320/5336/5419/5426|Exact evidence was reread after accepted edits, closing the loop|
|CX-C2|q10 L869,q16 L1427,q21 L1840; q23–30|String replacement, regex number extraction, and positional array updates motivate structured state|
|CX-C3|q8,q17,q18,q26|Conflicts were retained but insufficiently rechecked; borderline score differences do not establish compression harm|
|CX-C4|q44–50; q53 exec-e1fc37ad-5eaf-43ad-a8b3-1396866147ad|An obsolete table name was corrected after misuse; the native counterpart erred on aggregation grain, not proof of better CLM schema memory|
|CX-C5|q52 exec-19bc89d9-1aa6-47af-9bc4-e614d14dcb40; q74 exec-20acdfcc-3f96-4938-b6a2-8e29f57530c7; q93 exec-632628f5-c321-4ff1-979a-bc6ba4f5b490; q99 exec-0848339b-036e-40af-b332-287491061835|Four latter-half edits were accepted and notes existed; q52/q99 reread files, and summary evidence was used after q74|
|CX-C6|q97→98→99; q99 note|A false temporary-environment persistence claim was corrected but retained; stale Current93 state remained|
|CX-C7|q62→73/75,q64/78/87,q100|Feedback preceded strategy revisions, entity isolation, and observations replacing guesses; this does not prove causal benefits|

Implementation constraints checked against `Codex CLM/source/clm/{context.py,edit.py,container_entry.py}` and related files: note is a full replacement limited to 8192 UTF-8 bytes; omission preserves it; drop must be nonempty and strictly shrink the projection; queued edits apply to the next request. show excludes reasoning; the latest complete tool group and user/developer messages are protected; anchor changes reset the session note. Raw archives, disk files, and actual projections are separate layers. Paper SCR is not implemented.

## Interpreting aggregate results
Native Claude grouped 43,shuffled 41; Claude CLM 38; Codex 54,Codex CLM 53 (each out of 100). Claude and Codex differ in models and run configurations, so this is not a causal framework comparison. Same-order Codex: 51 both pass,44 both fail,3 native-only,2 CLM-only. Total input decreased approximately 28.6%, while uncached input increased approximately 31.7%; total input does not establish lower cost. The new skills have not run; these are discovery-set results.

## Per-skill evidence mapping

- `cc-resume-state`: CC-N1
- `cc-verify-memory-write`: CC-N2
- `cc-semantic-memory-address`: CC-N3
- `cc-evidence-hypothesis`: CC-N4
- `cc-scope-and-version`: CC-N5
- `cc-feedback-scope`: CC-N6
- `cc-active-memory-index`: CC-N7
- `cxclm-transactional-edit`: CX-C1,CX-C5
- `cxclm-structured-state`: CX-C2
- `cxclm-conflict-recheck`: CX-C3,CX-C7
- `cxclm-scoped-retrieval`: CX-C4,CX-C6,CX-C7
- `cxclm-note-lifecycle`: CX-C5,CX-C6
- `cxclm-measure-edit-effect`: CX-C3,CX-C5,CX-C7
- `ccclm-save-before-prune`: CCLM-E1,E6; q43,q93,q97.
- `ccclm-confirm-action-receipts`: CCLM-E2; q75,q86,q96.
- `ccclm-current-policy`: CCLM-E4,E5; q39/41/43,q48/54,q67/72,q79/81.
- `ccclm-metric-feedback`: CCLM-E3; q97–100.
- `ccclm-workspace-protocol`: CCLM-E5; q43,q55,q98–100.
- `ccclm-capacity-maintenance`: CCLM-E6; 40 accepted edits; multistage configuration above.
- `cx-verify-persistence`: CX-N1;q97–100,q1–30.
- `cx-resume-checkpoint`: CX-N2;q38,q75.
- `cx-evidence-state`: CX-N4;q8,q18,q24–30.
- `cx-scoped-retrieval`: CX-N3,N6;q64,q73,q78,q88,q46/51/53–55.
- `cx-feedback-change`: CX-N5,N6;q49,q53,q98–100.
- `cx-progressive-memory-read`: CX-N4;q24–30; native Claude semantic-retrieval counterexamples can inform cross-platform hypotheses.

## Additional interface verification
Codex `source/clm/edit.py` defines `--drop` as argparse `nargs="+"`; separate multiple IDs with spaces. Late Claude MCP source was not included in this snapshot. Direct comparison of memory-mcp/chain/upstream/0082→0083,0140→0141,0172→0173 found the first CLM memory in the next request equal character-for-character to a fixed prefix plus the current prune input note, rather than an append to the old note. All three pairs agree, supporting full replacement when a value is supplied. Preservation on omission is separately confirmed by the tool description. This is actual projection verification, not a claim of source-code verification.
