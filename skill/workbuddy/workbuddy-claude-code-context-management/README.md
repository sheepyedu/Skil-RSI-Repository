# WorkBuddy native Claude Code: recoverable state

**Use for:** native Claude Code tasks likely to cross a compaction, interruption or handoff. It changes how the agent bounds tool results, records partial progress and verifies that the right artifact exists after resumption. It does not need a custom context editor.

**Derivation:** compare the paired native and CLM execution traces, then inspect native compactions, verification and recovery. The native arm recovered from a local capacity stop at position 56. Positions 21–25 and 39 show how recency, source constraints and real readback matter more than simply remembering a success claim. The audit also identifies verifier startup failures that a local test cannot resolve. See [the paired audit](../CLAUDE-CODE-EVIDENCE.md).

**Use outside this benchmark:** repository migrations, long incident investigations, and document/build pipelines with resumable artifacts. Skip for short tasks with no state worth preserving.

**Install:** copy only `SKILL.md` into a same-named Claude Code skill directory (e.g. project `.claude/skills/` if appropriate). Install one language. Keep this README, benchmark data and audit outside runtime search. No live skill-on/off evaluation was run.
