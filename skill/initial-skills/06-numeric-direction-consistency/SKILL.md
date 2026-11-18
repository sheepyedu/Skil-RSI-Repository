# Retain verifiable values and directions in summaries

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When compacting statistical results into conclusions such as harmful/protective, increasing/decreasing, or better/worse.

## Procedure

1. Retain key values, units, denominators/reference groups, metric meanings, direction conventions, and evidence sources.
2. Check each verbal conclusion against those values. Re-derive the direction when changing the reference group, unit, or metric definition.
3. When values conflict with an old conclusion, flag the conflict and revisit the source. If it cannot be resolved, preserve uncertainty rather than retaining stronger wording.
4. After correction, identify the superseded conclusion and its scope so later retrieval knows which version is no longer valid.

## Cautions

Do not keep only “harmful” or “effective” while losing the definition. Preserving an incorrect number does not make it correct either; a traceable source is required.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Error-inheritance rate, proactive correction rate, and summary cost in direction-reversal and reference-group-swap tests.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
