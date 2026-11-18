# Locate by title or entity rather than storing unstable line numbers

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When retrieving experience about a topic or entity after notes have been appended, inserted, or reordered.

## Procedure

1. Search using the current entity ID, a stable heading, or a topic index first. Old line numbers are hints only.
2. Read a short window containing the heading, identity, and relevant entries. If it is insufficient, expand the range or search again.
3. Verify that the returned topic, entity, and entries address the current question. A successful call does not mean the content is correct.
4. Distinguish retrieval for a decision from reading to obtain an edit anchor. Record the entries actually used and their sources; unused entries must not be counted as effective reuse.

## Cautions

Reading a file does not establish that a particular entry was read. Do not treat a Read performed before a post-hoc append as the cause of successful task completion.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Relevant-passage hit rate, wrong-entity reuse rate, retrieval tool/token cost, and final scores.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
