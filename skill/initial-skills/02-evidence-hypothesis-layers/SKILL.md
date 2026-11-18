# Store observations, hypotheses, and rules separately

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When deriving lessons from a single score, local success or failure, or when compacting existing notes.

## Procedure

1. Separate raw observations from explanations: observations record the task, source, original feedback or a locatable reference; hypotheses record inferences and alternative explanations.
2. For each candidate rule, state its applicability conditions, number of supporting cases, counterexamples, uncertainty, and withdrawal conditions. Do not promote one matching case into a universal rule.
3. During compaction, prioritize hypothesis labels, contradictions, and the scope of evidence. Do not turn “possible” into “confirmed” or “never fails.”
4. On encountering a counterexample, mark the rule as withdrawn or identify its replacement version. Preserve the source for recovery; do not allow two contradictory versions to remain simultaneously active.

## Cautions

Total reward usually does not uniquely identify the cause of an error. Rules without subsequent use or independent validation remain candidates.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Incorrect-rule adoption rate, withdrawal rate after counterexamples, cross-instance generalization, and memory length.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
