# Bind every observation to an entity, not just a section in a shared file

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When recording individual profiles, opponent behavior, or instance characteristics, or when retrieving and writing back across entities.

## Procedure

1. Explicitly bind each observation to entity_id, instance_id, environment_version, and its source. Mark unknown fields as unknown.
2. After retrieval, verify that the returned content's identity matches the current task. Do not infer identity from pronouns such as “he” or “it,” or from the file's location.
3. Transfer only general methods across entities. Transferring individual facts requires new direct evidence; do not merge profiles merely because behavior is similar.
4. Before writing back, recheck the subject, source, and scope. If entities have been mixed up, correct the target entity and mark the erroneous version as withdrawn.

## Cautions

A single win or loss cannot prove that entity confusion is harmless or caused failure. Do not guess that an unidentified fragment refers to the current subject.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Wrong-entity reuse rate, missing-identity rate, retrieval hit rate after entity switches, and task scores.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
