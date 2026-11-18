# Confirm the storage lifecycle first

> Status: initial candidate skill (v0.1). Derived from observational analysis of 200 task-runs; benefits have not been validated through ablations or held-out tests.

## Trigger

When saving knowledge for reuse across tasks, containers, session resumptions, or task switches.

## Procedure

1. Determine whether the target file belongs to a temporary task sandbox, a session workspace, or a cross-session persistent area. Rely on actual framework configuration and verifiable behavior.
2. Save content needed across tasks in an authorized area with confirmed persistence. Record its path, entity/task scope, version, and recovery entry point.
3. After switching, first verify that the file exists and that its identity and version match. The same path name does not imply the same file.
4. If the file is missing, investigate container resets, mounts, and path changes before checking edit records. Do not immediately classify it as forgetting caused by context compaction.

## Cautions

Do not hard-code a path from one experiment as the persistent area for every framework. Persistence must not exceed user permissions or retain unnecessary secrets.

## Completion checks

- The current event has been handled using the steps above, and sources, scope, and unresolved matters remain traceable.
- Failed tool calls have not been treated as effective changes, and associations have not been presented as causal benefits.

## Validation metrics

Recovery rate after container resets, incorrect path-reuse rate, and recovery capability without the full chat history.

## Source and usage boundaries

Source: analysis of this repository’s 100 tasks executed twice in two task orders, including 19 native compactions. This file provides transferable operating strategies only, not answers to specific evaluation tasks. Read it as needed rather than injecting every skill into every round. It does not change existing tool permissions or native compaction mechanisms.
