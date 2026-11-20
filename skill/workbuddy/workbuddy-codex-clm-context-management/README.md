# WorkBuddy Codex CLM: verified active-context edits

The current `SKILL.md` is candidate v2. It follows an offline review of 50 Codex CLM trajectories and focuses on verifying state, making non-urgent memory edits at task boundaries, and checking that an edit reached the actual request. The run showed the skill path hint, but no observed read of the target skill body, so it does not establish a score or usage gain from the skill. The original review background is preserved below.

**Use for:** a Codex CLM integration with a visible edit contract. If the runner exposes no editor or reliable context view, fall back to a checkpoint. This does not implement CLM training or SCR.

**How it was derived:** audit accepted edits separately from inspection and automatic compactions, then check the next visible view and any later use. Three accepted edits are visible in the reviewed run, at positions 1, 51, and 54. Position 36 noticed a retained historical note was irrelevant but did not revise it. Position 54 updated the note and later tools displayed it; one likely transfer opportunity did not reproduce the documented verification action. See [the offline paired audit](../EVIDENCE.md).

**Transferable mechanism:** make the smallest reversible-in-practice edit whose necessary information can be recovered. Verify three distinct things: the editor accepted it, the later view reflects it, and work actually uses the retained state. If your integration does not expose a view or rollback, say so and pre-verify the recovery source.

**Install:** copy only this folder's `SKILL.md` into a matching skill directory. Install one language, not both. Keep this README, the audit, and all benchmark artifacts outside runtime retrieval. The observed comparison did not load this skill; it is a candidate, not measured uplift.
