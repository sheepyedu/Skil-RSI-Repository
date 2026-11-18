# Write a task-state card before compaction

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When compaction may occur mid-task, during long tool chains, or when resuming across tasks or sessions.

## Procedure

1. Use a short state card to record the task ID, environment/instance ID, current stage, completed actions, last trustworthy tool receipt, unresolved questions, next action, remaining budget, and how that budget is measured.
2. When an exact submission is required, retain the schema, key values, and their sources. Put large objects in files whose persistence has been confirmed; keep only their paths, versions, and retrieval methods on the card.
3. After resuming, check the summary against the latest retained messages and tool receipts. Correct the card using verifiable, more recent facts; do not repeat a submission merely because the summary says it is pending.
4. Take the next action only after reconciling the state. If the previous submission's outcome cannot be confirmed, query its status rather than blindly resending it.

## Cautions

Do not save lengthy reasoning as a substitute for a state card. If the model cannot control native compaction timing, maintain the card at stage checkpoints; do not claim to intercept compaction.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Duplicate-action rate, omission rate, schema error rate, recovery token cost, and final task success rate.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
