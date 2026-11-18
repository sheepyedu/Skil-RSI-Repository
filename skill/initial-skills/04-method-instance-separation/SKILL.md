# Reuse methods, not instance-specific answers

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When reusing experience on a new task of the same type, a different dataset, or a different environment version.

## Procedure

1. First read transferable methods, field checks, units, boundary conditions, and failure traps. Separate them from the old instance's specific values and answers.
2. Check the new task's schema, environment version, and applicability conditions; obtain this task's inputs anew and recompute key values.
3. Compare the new results against the old method's expected checks. If prerequisites are not met, stop applying it and explain the differences.
4. When saving general improvements, record conditions and evidence. Save instance results separately; do not turn them into default constants.

## Cautions

Do not assume identical conditions from matching field names, similar task wording, or a single success.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Success rate on unseen instances, changed values, and changed schemas; incorrect constant-reuse rate.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
