# Check feedback definitions before revising experience

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When inferring strategies from rewards or changing growth rates, thresholds, directions, or evaluation rules.

## Procedure

1. Record the feedback source, metric name, unit, direction, statistical year/sample scope, aggregation method, and task stage.
2. Label model-visible feedback and final evaluation separately. If they differ, first consult definitions, receipts, or scoring explanations that you are authorized to read.
3. If the scope is unclear, retain “definition/scope unknown.” Do not treat a single-year, local, or proxy metric as the final full-period score.
4. Check whether the observation distinguishes competing strategies. If it does not identify a unique answer, retain multiple possibilities and choose a permitted validation step that can distinguish them.

## Cautions

Do not read hidden test answers to tune parameters. Reward units and meanings can differ across tasks; do not directly average them across tasks.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Feedback-definition identification accuracy, incorrect reverse-inference count, and the proportion of non-identifiable cases where multiple possibilities are retained.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
