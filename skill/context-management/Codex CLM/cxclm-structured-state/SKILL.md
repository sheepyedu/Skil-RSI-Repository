---
name: cxclm-structured-state
description: Structure state and separate evidence layers for memory operations in long Codex CLM trajectories.
---

# Structure state and separate evidence layers

## Applicability and evidence limits

Applies to this repository's Codex CLM `clm-context` interface, not native Codex without that gateway. This is a trajectory-derived candidate skill; improvements have not been independently validated. Read only data allowed for the current task. Do not generate memory from evaluation answers or hidden scoring state.

## Feedback and revision

Record trigger counts, execution overhead, actual subsequent reads, recovery failures, and the current task's outcome. When counterexamples appear, retain the old rule version and its sources; revise its conditions rather than overturning all history based on one result. Compare against no-skill and frozen-old-skill conditions across multiple seeds. Report final reward, memory-mechanism metrics, and costs separately.

## Trigger

Accumulating means, counts, or entity attributes across rounds, or reusing a summary as input to a calculation.

## Procedure

1. Append raw observations to an evidence log with time, candidate entities, and sources.
2. Store current state in a structured file: stable `entity_id`, sample counts, aggregates, last observations, hypothesis status, and a conflict list. Do not use positions in a sorted array as permanent IDs.
3. Read structured fields for calculations. Do not extract numbers from natural-language notes using regular expressions or modify critical values using unchecked string replacement.
4. Keep only the task goal, valid state version, entity/file index, and unresolved conflicts in the short note. Read indexed fields as needed rather than repeatedly running `cat` on the entire history.
5. After updates, check unique entity IDs, count increments, numeric ranges, and agreement between current state and recomputation from raw evidence. Drop related old exchanges only after these checks pass.

## Stop conditions and safeguards

When migrating old narrative notes, preserve the original file first and verify fields individually. Do not fill in old values without evidence.

## Evidence

Event: CX-C2. See [Events and evidence](../../EVIDENCE.md).

## Counterexamples and failure signals

Summary-format changes break parsing; array sorting causes updates to the wrong entity; repeated full-file reads consume compression savings.

## Rollback and permissions

Retain the pre-change memory version and evidence index. If a new rule conflicts with current tool evidence, suspend it first and recover from sourced records. Do not restore task state confirmed to be obsolete. If no recovery evidence exists, mark it unknown rather than inventing it. This skill does not expand authorization for external actions.
