# Codex CLM：可验证的任务间上下文维护

这份候选适用于有真实请求投影编辑器的长会话。它不是 WorkBuddy 插件，不会修改调度器，也不取代原生 Codex 的上下文管理。只安装一个语言版本。不必把本 README、测试用例或历史轨迹载入每一道题。

**来源。** 来自四组 WorkBuddy 离线审计：原生 Codex、Codex CLM、带 skill 路径提示的 Codex CLM，以及带控制器独立整理回合的 Codex CLM。审计分开记录了投影修改是否生效，以及后续决策是否用到修改后的信息。实验排名不是对 skill 或插件净效应的受控估计。

**可迁移部分。** 边界是安全机会，不是凑编辑次数的指标。只写可能服务于下一次决策的最小笔记，核验实际传入和取用。把策略与调度、跑分专用提示分开。原实验每两题整理一次，不代表其他工作也应这么做。

**如何采用。** 先用[测试用例](references/validation.md)核验。分别量化信息保留、后续使用与开销；如果出现任务被阻断、旧记忆被误用或不可恢复的证据被删除，就回滚。

设计参考：[Agent Skills 规范](https://agentskills.io/specification#progressive-disclosure)、[Anthropic 工程文章：Agent Skills](https://www.anthropic.com/research/equipping-agents-for-the-real-world-with-agent-skills)、[Anthropic 工程文章：Agent 评测](https://www.anthropic.com/research/demystifying-evals-for-ai-agents)、[SkillsBench](https://arxiv.org/abs/2602.12670)、[SkillRL](https://arxiv.org/abs/2602.08234)。
