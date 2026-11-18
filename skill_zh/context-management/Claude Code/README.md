# Claude Code 上下文管理技能

## 来源与适用范围
来自原生 Claude Code 长轨迹的离线逐事件审阅，包括顺序与乱序执行对比；围绕原生文件工具中的记忆生成、使用、反馈和修订归纳，不依赖 CLM 上下文编辑接口。

以下 7 个技能来自行为观察，均为候选，尚未独立验证提分效果。仅使用当前运行实际提供的接口，遵守原有授权边界。

## 技能目录
- [把观察假设规则分层并保留反例](cc-evidence-hypothesis/README.md)
- [反馈必须带指标范围且不反演唯一原因](cc-feedback-scope/README.md)
- [按语义定位而非历史行号检索](cc-semantic-memory-address/README.md)
- [记忆写入必须核验成功](cc-verify-memory-write/README.md)
- [分离简短活跃记忆和证据日志](cc-active-memory-index/README.md)
- [恢复时对齐摘要与最新状态](cc-resume-state/README.md)
- [为实体与环境建立记忆作用域](cc-scope-and-version/README.md)

## 运行时与研究资料隔离
仅将选中的 SKILL.md 复制到运行时技能目录；分类与单技能 README、EVIDENCE.md、EVALUATION.md 和 references 均留在被测容器及其检索路径之外。研究资料用于理解证据与局限，不应作为读取评测答案的入口。中英文版本择一使用。
