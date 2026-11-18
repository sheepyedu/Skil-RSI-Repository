# Claude Code context-management skills

## Origin and scope
Derived during offline, event-by-event review of native Claude Code long trajectories, including grouped and shuffled task orders. It addresses memory generation, use, feedback, and revision with native file tools, not CLM context-editing interfaces.

The 7 skills below are candidates derived from observed behavior, not independently validated score improvements. Use only the interfaces actually available in the current run. Preserve applicable authorization boundaries.

## Skills
- [Separate observations, hypotheses, and rules while preserving counterexamples](cc-evidence-hypothesis/README.md)
- [Attach metric scope to feedback; do not infer a unique cause](cc-feedback-scope/README.md)
- [Retrieve by semantic anchors, not historical line numbers](cc-semantic-memory-address/README.md)
- [Verify that memory writes succeed](cc-verify-memory-write/README.md)
- [Separate a short active-memory index from evidence logs](cc-active-memory-index/README.md)
- [Reconcile summaries with the latest state when resuming](cc-resume-state/README.md)
- [Scope memories by entity and environment](cc-scope-and-version/README.md)

## Runtime and research separation
Copy only selected SKILL.md files into runtime skill directories. Keep category and individual READMEs, EVIDENCE.md, EVALUATION.md, and references outside the tested container and its retrieval paths. The documents describe evidence and limitations rather than granting access to benchmark answers. Select either the English or Chinese version, not both.
