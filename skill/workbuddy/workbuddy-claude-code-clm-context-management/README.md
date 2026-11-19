# WorkBuddy Claude Code CLM: verify trimming and delivery

**Use for:** custom Claude Code CLM runners where an authorized context view or edit operation is available. It distinguishes context pressure from an output cap, transport failure and incomplete delivery. Without an editor, use the verified handoff instead; this is not a native feature.

**Derivation:** the reviewed run used controller-triggered between-task writeback with model proposals and runner fallbacks, not accepted in-task CLM edits. The audit traces over-budget proposals, a precedence change in a proposed summary, position 48's capacity recovery, and complete responses with no action after them. These motivate verified preservation and explicit failure classes, not the claim that edits improved scores. See [the paired audit](../CLAUDE-CODE-EVIDENCE.md).

**Use outside this benchmark:** multi-step coding, analysis, or agent workflows with a replayable checkpoint. In any runner, use only controls whose scope and semantics can be checked.

**Install:** copy only `SKILL.md` into a supported same-named skill directory. Install one language. Keep this README, benchmark data and audit outside runtime search. No live skill-on/off evaluation was run.
