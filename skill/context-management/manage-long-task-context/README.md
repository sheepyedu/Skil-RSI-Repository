# Long-task context continuity

Install only one language edition. The entrypoint is SKILL.md. No framework changes or additional tools are required; a context editor and next-request visibility are optional capabilities. Keep checkpoints in an existing authorized task location; a skill never grants write or external-action permission.

The checks in [cases and evals](references/cases-and-evals.md) are a candidate evaluation plan, not measured performance. The design takes cues from [OpenAI's skill evals](https://developers.openai.com/blog/eval-skills), [Anthropic's Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md), and [CTXAgent](https://arxiv.org/abs/2610.34425). The skill does not rely on benchmark artifacts during use.

Design references outside the runtime skill: [Anthropic's long-running harness guidance](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents) for durable progress and state verification; [CliffCompaction](https://arxiv.org/abs/2609.26779) for preserving retrievable evidence; [Supersede](https://arxiv.org/abs/2606.27472) for testing stale or conflicting facts. These references guide design, not claims that the new skill improves scores.
