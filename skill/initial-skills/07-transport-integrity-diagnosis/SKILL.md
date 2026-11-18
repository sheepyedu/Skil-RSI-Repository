# Distinguish model-editing loss from transport corruption

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When a summary, code, regular expression, or exact string enters a subsequent request and its content changes or execution behaves abnormally.

## Procedure

1. Only when authorized and observable, obtain the original summary output and the actual subsequent input. Distinguish model generation, client assembly, and server receipt.
2. Compare exact-preservation segments byte by byte or character by character. Record known normalization; do not directly use hashes of different encodings to conclude semantic corruption.
3. If the original output is correct but the actual input was rewritten, classify the problem as transport/assembly diagnosis. Analyze the summarization strategy only if information was already missing from the original output.
4. If logs from any layer are unavailable, state that the cause cannot be determined and save minimal reproduction clues. System fixes require a separate authorization process.

## Cautions

This is an engineering diagnostic skill, not a request for the model to compensate for client defects with longer summaries. Do not copy keys or unrelated sensitive data into diagnostic logs.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Special-character fixture pass rate, exact-segment consistency, and fault-localization accuracy; report these separately from task scores.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
