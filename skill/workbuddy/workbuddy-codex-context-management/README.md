# WorkBuddy Codex: recoverable context

The current `SKILL.md` is candidate v2. It follows an offline review of 50 Codex CLM trajectories and focuses on verifying state, making non-urgent memory edits at task boundaries, and checking that an edit reached the actual request. The run showed the skill path hint, but no observed read of the target skill body, so it does not establish a score or usage gain from the skill. The original review background is preserved below.

**Use for:** native Codex doing multi-stage work, recovering after interruption or compaction, or resuming against changed workspace state. No custom context editor is needed. This skill is not a requirement to write a note on every turn.

**How it was derived:** compare both arms in the same WorkBuddy task order, then inspect accepted source timelines for the information-to-action chain. Native position 31 compacted during work; position 32 still retrieved current evidence. At position 28 the native arm reproduced the same fixture errors on a clean baseline, preventing a local test result from becoming a false global status. Positions 38–39 illustrate why a prior environment failure should prompt a fresh capability check, not a permanent rule. See [the offline paired audit](../EVIDENCE.md).

**Transferable mechanism:** a checkpoint earns its place by answering a real next-decision question and pointing to recoverable evidence. Outside coding, this applies to a report handoff, staged release, or multi-step document task. It is not permission to persist data beyond the current scope.

**Install:** copy only this folder's `SKILL.md` into a matching skill directory. Install one language, not both. Keep this README, the audit, and all benchmark artifacts outside runtime retrieval. The candidate has not been tested on/off.
