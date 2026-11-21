# Claude Code 长任务上下文恢复

适用于会中断、接近容量限制或需要跨阶段继续的任务。支持原生 Claude Code 和带编辑器的 CLM，不负责启用插件或改变运行配置。只安装一个语言版本，别把研究说明都塞进模型上下文。

候选来自 LHTB 2.0 五题配对审计。正式账本里没有已生效的 CLM 编辑，两组都发生了原生压缩。运行器问题和外部状态丢失不算模型遗忘。这次能支持的经验是核实编辑是否真用、恢复时先验证外部状态，而不是证明选择性编辑已提高分数。没有为这个候选另跑验证实验。

设计参考：[Anthropic 长任务工程](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)、[Anthropic 记忆分层](https://www.anthropic.com/research/components-of-agent-memory)、[CompAct-Bench](https://arxiv.org/html/2611.25673v1#S2.SS2)、[VISTA](https://arxiv.org/html/2606.30005v5#S3.SS7)、[OpenAI 技能评测](https://developers.openai.com/blog/eval-skills)。
