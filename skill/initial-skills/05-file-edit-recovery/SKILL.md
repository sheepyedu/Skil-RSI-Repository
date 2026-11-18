# Reconstruct file state after a failed edit

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When Edit reports an unread file, unmatched old text, or an inconsistent path, or when modifying notes after compaction.

## Procedure

1. Identify the error type and verify the target path, current environment, and whether the file exists. A failed call does not count as a successful disk write.
2. Read the target's actual content, obtaining the smallest sufficient window containing its identity/title and the text to change.
3. Make a local Edit using a real, unique, sufficiently short anchor. If it matches multiple places, narrow the scope or add context first.
4. Check the tool's success receipt. Read back important changes and preserve unrelated content. On failure, locate the target again rather than retrying the same call indefinitely.

## Cautions

Do not overwrite existing knowledge with a whole-file Write merely to eliminate an error. An unread-file error occurring alongside compaction does not establish its internal cause.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Edit success rate, retry count, accidentally deleted entries, and recovery tool-call and token costs.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
