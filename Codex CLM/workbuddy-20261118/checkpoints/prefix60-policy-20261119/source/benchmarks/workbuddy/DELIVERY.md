# WorkBuddy delivery and restoration

The running experiment is an isolated Codex CLI 0.169.0 installation using
`gpt-6.1-sol`. Each arm continues its original thread; tasks are strictly ordered
`native_i`, `clm_i`, then task `i+1`. The final plan has 65 paired tasks:
Code20, Office12, Security15, Web18. The original 60-task reference prefix is
unchanged; five official Security tasks are appended to both original threads.

Scientific controller snapshots are immutable. New transport/environment fixes
have their own source directory, hashes and regression receipts. Postprocessing
scripts do not alter the running controller or accepted actor artifacts.

## Framework and prompts

`describe_workbuddy_framework.py SOURCE RUN OUTPUT` extracts exact prompt text
from Python AST and renders a detailed Mermaid source plus a PNG/SVG/PDF overview.
Orange marks added adapters, including common wiring; blue marks original Codex;
green marks the official benchmark. `PROMPTS.json` includes source line numbers
and hashes. The detailed `FRAMEWORK.md` distinguishes the common task wrapper
from the CLM developer instruction, dynamic memory and ordinary tool observations.

Routine CLM edits change the outgoing API projection. They do not delete the
CLI's own active history. Original Codex compaction, including the CLM arm's
explicit capacity safeguard, changes that active history while preserving the
thread and historical JSONL evidence. JSON array bytes and provider input tokens
are reported separately.

## Audit and technical judge repair

The final auditor checks actor thread continuity, official instructions,
request/response hashes, unchanged control requests, original patches and official
scores. It independently reconstructs all CLM projections, preserving protected
messages and complete tool-call batches. Failed-attempt edit and compaction events
are counted separately from selected-trial events. Copied prefixes are deduplicated.

For the full65 plan, `check_workbuddy_binding.py` also binds every official
instruction to the completed native turn's actual `turn/start` request and a
captured raw/sent GPT Responses request. It checks the real successful response,
native completion event, original thread and ordered task prefix. Original thread
IDs use `MANAGER_STATE.json` when present. The final auditor writes
`native-task-binding.json`; production packaging requires its complete130 entries,
matching frozen question hashes, original threads and checker source hashes.
An accepted count or numeric score alone cannot satisfy this gate.
`check_workbuddy_binding_cpu.py` qualifies the check with copied real first-pair
bytes and tamper cases, including changed questions with recomputed hashes.

`official-judge-quality.json` examines technical judge fields. A low semantic
score remains a result. Empty final judge responses, image failures and unresolved
technical fallbacks block final delivery. A stale retry-error field accompanied
by a complete final JSON verdict is recorded as a recovered retry.
Normalized official judge `build_error`, `judge_error` and `ok=false` also require
review, even when their `errors` list is empty and the wrapper exits successfully.
They are not automatically treated as model failures or automatically retried.

`repair_workbuddy_csv_bom.py` reproduces task21's original verifier `KeyError` on
the exact archived UTF-8 BOM CSV. In a copied official verifier it changes only
the CSV reader codec from `utf-8` to `utf-8-sig`, preserving all thirteen predicates,
original exporter and output bytes. Both original patches are regraded offline;
actor/judge model calls remain zero. The separate overlay pins its own immutable
executed script, original failures, restored patch and CSV digest.

Office atomic-check counts can depend on output coverage: the official task54
evaluator skips value checks for missing sheets/rows or incomplete columns. Its
two arms therefore have different test denominators. Reports retain official
rewards and per-task equal-weight means, disclose this limitation and do not
interpret raw passed-check totals as a common coverage score.

`repair_workbuddy_judge.py` handles a narrowly identified single empty Web judge
result. It first proves that the original official functions reproduce the
original score. With `--execute`, it retries only the exact captured judge request,
at most three times, and accepts either valid pass or fail. It uses the original
official parser, report generator and scoring adapter, retaining all other
verdicts and completion evidence. Actor calls are zero. Original patch, workspace,
receipt and official source hashes must remain unchanged. The repair lives under
`judge-repairs`; the final audit applies this separately hashed overlay without
overwriting original results. Additional judge requests enter the all-attempt
usage ledger.

The official Web interactive stage also needs CodeBuddy CLI 2.109.3. Its runtime
npm installation fails in an offline task container. `provision_workbuddy_cbc.py`
uses an integrity-verified official npm bundle, qualified offline with the CLI
version and a real Linux PTY. It installs only in this experiment's own Web
container after a successful actor turn has closed, preserving actor home hashes.
It does not modify the task images or the running actor controller.

`repair_workbuddy_agent_judge.py` restores an already completed actor's exact
patch on the frozen image, verifies every archived changed file, reproduces the
original official score, and runs only the missing official agent rubric items.
It keeps all other original verdicts and requires valid per-item verdict logs,
actual submissions and CBC's successful terminal event. The official tee pipeline
can return zero after CBC fails. Its network is disabled;
GPT judge calls use the protected local bridge. Actor calls remain zero. The
original results, all judge requests, tool traces, CBC sessions and repair
implementation are retained. The auditor checks the resulting separate overlay.
If one interactive item fails technically after others have valid submitted
verdicts, `--seed PREVIOUS_PARTIAL_RECOVERY` verifies the previous original-file
hashes and unchanged workspace, reuses those valid item logs and evidence, and
selects only the unfinished official items. It does not repeat completed judge
work. Selection is a wrapper around the official scoped-item function; the case,
rubric and prompt builder remain unchanged. Actor Responses have complete-stream
delivery protection; judge Chat Completions preserve their original stream and
are checked independently for valid final judgments.

## Complete archive

`snapshot_workbuddy_inputs.py` preserves the exact 65 selected formal tasks and
four disjoint pilot tasks, including original staged task files, dataset.toml,
shared verifier dependencies and original plans. Every source and copied file is
independently hashed; task instruction and frozen runtime configuration hashes
must match their plans. The snapshot does not modify the inputs used by a running
controller. Its inventory distinguishes original Dockerfile hashes from staged
mirror/cache adaptations, and records source paths for relocation.

After the 65-pair audit and report are complete:

```bash
python3 package_workbuddy.py EXPERIMENT_ROOT AUDIT_DIRECTORY NEW_OUTPUT_DIRECTORY \
  --scan-private-gpt-key
```

The production guard refuses an incomplete plan. The output must be outside the
experiment root. All logical files and link metadata in the isolated root are
included; source directory symlinks are not followed. Four-MiB SHA256 chunks
deduplicate copied prefixes and repeated image layers, while `FILES.jsonl` retains
every path, file recipe, mode, timestamp and original uid/gid. Special filesystem
endpoints have metadata only. The archive checks every chunk CRC/SHA, every file
recipe, audited hashes and byte accounting. A privately loaded GPT-key canary
scan refuses publication if the credential occurs in file contents or link targets.

The ZIP is split into 45-MiB Git-sized files under `archive/parts`, with a full
archive SHA and per-part SHA in `archive/MANIFEST.json`. Its manifest is compatible
with the repository's existing multipart joining utility. The payload itself uses
the explicit `workbuddy-content-chunks-v1` format, so restore with both supplied
Python scripts:

```bash
python3 restore_workbuddy.py join DELIVERY_DIRECTORY
python3 restore_workbuddy.py verify DELIVERY_DIRECTORY/WORKBUDDY_CODEX_65_FULL.zip
python3 restore_workbuddy.py extract \
  DELIVERY_DIRECTORY/WORKBUDDY_CODEX_65_FULL.zip NEW_RESTORE_DIRECTORY
```

Restoration verifies parts, the archive and reconstructed file bytes. It never
executes archived binaries or benchmark commands. Original uid/gid remain in the
inventory; restored files belong to the current user. Basic permission bits and
regular-file/directory timestamps are restored. Links are created only after
regular files; special endpoints are recorded rather than recreated.

`check_workbuddy_archive.py` exercises real wire-byte roundtripping, multipart
integrity, Unicode/empty/executable/link metadata, tampering rejection,
cross-chunk canary detection and incomplete-publication rejection.
Raw `.tar` checkpoints use bounded member-aligned chunks to share identical layers
even when headers shift their offsets. Original headers, padding and trailers are
stored unchanged; full-file SHA checks and restoration remain the same v1 format.
Malformed tar metadata falls back to fixed-size storage. No checkpoint is excluded.
`check_workbuddy_postprocess.py` validates actual completed trials plus protected
text mutation, failed-judge classification and copied-prefix deduplication.
Both checks make zero model API calls. Running-stage checks are explicitly not
the final 65-pair audit.

Task49's Office evaluator repair restores both original patches in the frozen
image, reproduces the original native exception and CLM score, then changes only
the unchecked `artifact_refs.values()` access and its existing type predicate.
Wrong types fail that check; the 134-item rubric remains intact. Missing original
`case.yaml` and `instruction.md` workspace fixtures remain failed checks. One
set-derived profile diagnostic is compared after sorting its displayed values;
verdicts and values remain unchanged. `--finalize-existing` validates completed
CPU grading trials without repeating them. Original failures and all versions are
retained alongside the applied score overlays.

Publish in a new dated directory under `Codex CLM` in
`sheepyedu/Skil-RSI-Repository`, preserving earlier CL-Bench content. Verify the
actual remote parts and manifest, then record the delivery and submit the Notion
subtask review. The persistent Goal stays active until execution, audit, complete
archive, report and required delivery work have finished.

`prepare_workbuddy_publication.py EXPORT AUDIT SOURCE_SNAPSHOT FRAMEWORK_SNAPSHOT OUTPUT UPLOAD_PLAN`
stages the actual publication without uploading or changing a branch. It rechecks
all archive CRCs, chunk/file SHA values and the private GPT credential-scan receipt,
requires the complete65/130 ordered binding and zero unresolved judge findings,
and binds every visible report, source file and framework artifact to its original
file digest inside the full archive. The unchanged ZIP is split into8MiB parts;
the staged README, restore scripts and `INTEGRITY.json` provide independent access
and file verification. `UPLOAD_PLAN` records expected Git blob IDs and SHA256 values
outside the published directory for resumable uploads. The current remote parent
commit and existing parent README must still be fetched before a leased branch
update. `check_workbuddy_publication.py` uses explicit CPU fixtures and copied real
wire bytes to verify roundtripping and refusal of changed reports, duplicate task
bindings and unresolved grader failures; it does not constitute a full65 run.
