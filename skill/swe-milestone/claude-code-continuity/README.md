# Native Claude Code continuity

Uses Claude Code's native context behaviors; it does not change compaction thresholds or enable CLM.

## Fit and installation

Use when a single repository continues through dependent requirements. Choose exactly one language and one runtime variant; do not load both variants into a measured trial. To install, copy this skill directory unchanged into an authorized Claude Code skill location (for example, `.claude/skills/` within the relevant project). Use `/claude-code-continuity` if the client supports explicit invocation. Check that the intended body was actually loaded, including in headless or restricted configurations. Do not copy this note into the model prompt or broaden permissions. This package includes no scripts, hooks, endpoints, or credentials.

- [Agent Skills format](https://agentskills.io/specification)
- [Claude Code skill lifecycle and evaluation](https://code.claude.com/docs/en/skills#skill-content-lifecycle)
- [SWE-Milestone: continuous tasks and isolated snapshots](https://arxiv.org/html/2603.13428v4#S4.SS1)
- [Validation and audit procedure](references/validation.md)
