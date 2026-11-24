# Working-state examples

## A small continuation record

Use the task's existing progress file or memory store when available. A compact record can be structured like this:

| Field | Example |
|---|---|
| Scope | Export job, staging, schema revision 18, current batch ID |
| Verified and changed | The normal-size export matches the source count. See the manifest and its checksum. The large export is still in flight. |
| Evidence pointer | Manifest path, log offset and request ID. Preserve the exact failure line only if the log will expire. |
| Pending | Poll the existing large-export request. A timeout in its client leaves the server state uncertain. |
| Next check | Compare the completion receipt and row count before deciding whether a retry is needed. |

As task state grows, keep a small active index and store detail behind stable pointers. Label assertions verified, provisional or superseded. Include the revision where a new assertion took effect.

## Choose what to retrieve before you edit

Suppose a long debugging task contains ten identical build logs, one failure from a changed test configuration, and a pending asynchronous test. Preserve the test configuration, the relevant one-line failure and its log location, and the live request identity. Recover the pending test first. At a later quiet boundary, repeated build logs are suitable for trimming. Check the next effective input for the intended change and rerun the narrow behavior check when feasible.

If the only copy of an observation will expire, copy the necessary excerpt or retain it in working context. The method depends on recovery cost and current relevance, even when the same observation takes up a large share of the window.

## Repair a stale conclusion

A report used a note stating that a cohort excludes part-time staff. At handoff, the current data dictionary says the exclusion ended in revision 7. Check which revision generated each table. Keep the note valid for older revisions, mark it superseded for revision 7 and later, correct the affected table, and verify the denominator against the revised filter. Point the index at the current definition. A short correction with a source and scope is easier to use than an appended summary containing both answers.

## Check that the skill helped

Use cases with known source evidence and an observable continuation outcome. Useful variations are a recoverable bulky observation, an ambiguous in-flight operation, a governing source revision change, and a workflow with only native compaction.

Compare the original and skill-assisted workflow on the same task and starting state. Record whether the next action retrieved the correct evidence, preserved unresolved work, and completed a meaningful target and regression check. Separately track repeated lookups, requests, cache misses and bytes or tokens at a verified boundary. If an edit affects later tool activity or session cost, compare both the immediate projection and downstream behavior. Verify positive cases and cases where maintenance is unnecessary.
