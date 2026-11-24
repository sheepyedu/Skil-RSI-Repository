# Cases and evaluation

## Record shape

One record per task, updated rather than appended in full. Fields: task/scope; current version or timestamp; standing constraints; last verified checkpoint; remaining work; next action plus source pointer; unresolved action keys. For changed facts add authority and the previous record ID. A missing receipt means unknown, not failed or completed.

## Examples

- Code: After switching branches, match the checked-out revision and dirty state to the checkpoint. Re-run the narrow contract test before extending the implementation; retrieve the exact failing assertion from its report, not an old summary.
- Spreadsheet: After the reporting period changes, verify the active workbook version, period, currency, and formula range against the latest approved source. Keep the prior period separately. Reconcile a control total before building the next worksheet.
- Web: After an interruption during a settings change, reopen the authorized workspace, read the live record and any receipt, and compare the desired value. Do not submit a second write merely because the previous response is missing.

## Evaluation

Use matching model, tools, task fixture, context budget, and seed; compare no skill, previous skill and candidate. Take checkpoints from trusted tool receipts and state snapshots. Evaluators and answer keys stay outside the agent's workspace.

| Case | Machine check |
|---|---|
| Short task or reminder with low pressure | No context edit or duplicate progress record |
| Safe, pressured segment with editable context | Applied operation in actual next request where instrumented; required exact fields unchanged; unrelated data untouched; checkpoint passes |
| Unrecoverable evidence or an in-flight action | No premature deletion or duplicate action; preserve exact evidence/unknown receipt until reconciled |
| Native-only compaction and interruption | Artifact is reopened and scoped validation is run before a dependent write |
| Stale record and cross-scope conflict | Use current authoritative version for same scope; do not override a separate scope; unresolved conflict is logged |
| Retrieval without full transcript | Correct keyed artifact and minimal evidence retrieved; subsequent artifact passes verifier |

Collect trigger, branch, process, output, and efficiency separately. Count edit proposals, accepted writes and observed next-request application separately; log unobservable application as unknown. Compare checkpoint pass rate, requests, input, output, and applicable cached/uncached inputs; report observable mismatches, not savings inferred from a shorter prompt. Test at least one unseen workspace per domain, vary aliases and locations, retain the same critical invariants. For each failed check label rule not exercised, not followed, or followed but ineffective. Revise one rule at a time and rerun regressions and held-out cases.
