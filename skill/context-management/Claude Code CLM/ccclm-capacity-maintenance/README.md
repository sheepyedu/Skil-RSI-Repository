# Maintain capacity with headroom and measurable progress

## Derivation and applicability
Derived during offline review of the repository’s multi-phase Claude Code CLM trajectory, including model context edits and later runner-triggered maintenance. It is specific to that harness; the run is not a fixed-configuration clean ablation.

Use when: Before tool calls likely to return large results, or when the runner triggers capacity maintenance.

Related evidence: CCLM-E6; 40 accepted edits; see EVIDENCE for the multi-phase configuration. See [Events and evidence](../../EVIDENCE.md).

## Use and validation status
Read [SKILL.md](SKILL.md) for the procedure, checks, revision loop, and rollback boundaries. This is an unvalidated candidate, not an experimentally proven improvement. It does not grant new tool capabilities or authorization.

For runtime installation, copy only the selected SKILL.md into the corresponding skill directory. Keep this research-oriented README, evidence documents, event locators, and evaluation materials outside the tested agent’s container and retrieval paths to avoid evaluation contamination. Do not load both language versions as separate skills.
