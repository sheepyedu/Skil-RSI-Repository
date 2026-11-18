---
name: cx-progressive-memory-read
description: Select evidence relevant to the current decision in native Codex when long memory files repeatedly consume context.
---

# Read progressively for the current decision

Applies to native Codex. Status: a trajectory-derived candidate without independent validation of score improvements.

## Trigger

Long memory files repeatedly occupy context, while the current decision needs only part of them.

## Generation and use

1. Generate a short index with entities, versions, validity, and evidence locations.
2. Read the index first and retrieve only fields relevant to the current decision. Expand into raw evidence when conflicts or missing evidence require it, rather than running `cat` on the whole history every time.
3. Record which action the retrieved content supported, which prior it overturned, or why it did not apply.
4. Write new valid rules into the current index and store complete evidence separately. Do not substitute fixed historical line numbers for semantic addresses. After locating content, verify its entity and heading.

## Feedback and revision

Measure retrieval cost, missed retrievals, actual references, and stale matches. Adjust the index based on counterexamples instead of continually enlarging default reads. Validate on independent tasks; success in the original trajectory does not establish benefit.

## Boundaries and rollback

Reduce redundant reads without deleting unique original sources. Save the previous index. If the new index cannot recover key facts, restore the last valid version and add evidence locations. Do not use evaluation answers or future information, or expand permissions for external actions.

## Evidence

CX-N4 (q24–30). CC-N3 is a cross-platform clue that may be useful, not a native Codex intervention experiment. See [Events and evidence](../../EVIDENCE.md).
