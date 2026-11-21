# Long-task context recovery for Claude Code

This is a candidate for interrupted, capacity-bound or multi-stage tasks. It supports native Claude Code and editable CLM, but neither enables a plugin nor changes host configuration. Install one language version and do not bring the research notes into every prompt.

The skill comes from a paired five-task LHTB 2.0 audit of an optional editor and the native fallback. The formal event ledger reports zero accepted CLM edits; both arms used native compaction. Runner failures and environmental state loss were not counted as model memory failures. The comparison supports making editor uptake and external recovery observable, not a claim that selective editing improved the scores. The candidate is not evaluated in a new run.

Design references: [Anthropic long-running harness](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents), [Anthropic memory components](https://www.anthropic.com/research/components-of-agent-memory), [CompAct-Bench](https://arxiv.org/html/2611.25673v1#S2.SS2), [VISTA](https://arxiv.org/html/2606.30005v5#S3.SS7) and [OpenAI skill evaluation](https://developers.openai.com/blog/eval-skills).
