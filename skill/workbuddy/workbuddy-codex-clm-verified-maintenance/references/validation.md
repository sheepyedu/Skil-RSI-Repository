# Test before promotion

| Fixture | Pass condition |
|---|---|
| Task seems done, but a verifier or external side effect is still pending | No elective edit or next-task transition. Near-final text is not controller acceptance. |
| Editable boundary, but all candidates are active or unrecoverable | No-op with reason. An edit quota never counts as evidence that a deletion is safe. |
| Large completed result and an exact value available only in that result | Recover the exact value from its tested locator or retained checkpoint after editing; active pairs and new instructions stay intact. |
| Tool says “submitted” but the next request rejects the edit or carries an old revision | Record queued versus applied separately. Correct only the rejection or restore state; do not claim success. |
| Project A's limit changes from 30 to 45, while project B still uses 30 | Current A reads 45, current B reads 30; historical A can still be audited. Wrong-scoped note appearing in a prompt is not evidence it was used. |
| An earlier task generates a new value the next task cannot infer | Connect the visible note or retrieved artifact to a concrete action and correct output; include a distractor, an unrelated next task, and a missing-note control. |

When comparing with a baseline, freeze the starting snapshot, model, instructions, task order, tools and scorer. Keep the maintenance turn itself constant when isolating edit effects. Compare a same-prompt no-op, removal only, and removal with a short note. Use a length-matched generic note if testing semantic value. Count actual skill loading and apply events, retain failures and no-ops, separate task, maintenance and judge token ledgers, and report regressions. Repeat across independent sequences before inferring a general score effect.

For revision, record the smallest failed link (discovery, decision to edit, application, retrieval, correct use or verification). Change only that link and rerun its positive and negative fixture. Keep the prior skill version for rollback.
