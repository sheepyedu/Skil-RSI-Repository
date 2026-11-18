# Claude Code CLM context-management skills

## Origin and scope
Derived during offline review of the repository’s multi-phase Claude Code CLM trajectory, including model context edits and later runner-triggered maintenance. It is specific to that harness; the run is not a fixed-configuration clean ablation.

The 6 skills below are candidates derived from observed behavior, not independently validated score improvements. Use only the interfaces actually available in the current run. Preserve applicable authorization boundaries.

## Skills
- [Maintain capacity with headroom and measurable progress](ccclm-capacity-maintenance/README.md)
- [Maintain a current-rule index for conflicting memories](ccclm-current-policy/README.md)
- [Verify saved state before pruning](ccclm-save-before-prune/README.md)
- [Distinguish the persistent workspace from the official task environment](ccclm-workspace-protocol/README.md)
- [Do not treat score differences across tasks as strategy ablations](ccclm-metric-feedback/README.md)
- [Accept only tool receipts as evidence of completion](ccclm-confirm-action-receipts/README.md)

## Runtime and research separation
Copy only selected SKILL.md files into runtime skill directories. Keep category and individual READMEs, EVIDENCE.md, EVALUATION.md, and references outside the tested container and its retrieval paths. The documents describe evidence and limitations rather than granting access to benchmark answers. Select either the English or Chinese version, not both.
