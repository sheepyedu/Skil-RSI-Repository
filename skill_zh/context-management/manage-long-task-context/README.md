# 长任务上下文管理

中英版择一安装，入口是 SKILL.md。技能不要求改造框架或增加工具；是否能编辑上下文、是否能观察实际请求，按运行环境区分。检查点使用已有且获准写入的任务位置，技能不会授予额外写入或操作权限。

[案例与评测](references/cases-and-evals.md)是候选验证方案，不是已测收益。设计参考 [OpenAI 技能评测](https://developers.openai.com/blog/eval-skills)、[Anthropic Skill Creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) 和 [CTXAgent](https://arxiv.org/abs/2610.34425)。执行时不读取评测数据或验收器。

不随技能正文加载的设计参考：[Anthropic 长任务 Harness](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)的持久进度与状态复核；[CliffCompaction](https://arxiv.org/abs/2609.26779)对可回读证据的保留；[Supersede](https://arxiv.org/abs/2606.27472)的过期与冲突事实测试。这些仅供设计参考，不代表新版技能已提高分数。
