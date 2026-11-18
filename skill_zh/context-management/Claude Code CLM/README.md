# Claude Code CLM 上下文管理技能

## 来源与适用范围
来自本仓库多阶段 Claude Code CLM 轨迹的离线审阅，包括模型上下文编辑与后期运行器触发的维护；适用该 harness，不把此运行视为固定配置的干净消融。

以下 6 个技能来自行为观察，均为候选，尚未独立验证提分效果。仅使用当前运行实际提供的接口，遵守原有授权边界。

## 技能目录
- [有余量且有进展的容量维护](ccclm-capacity-maintenance/README.md)
- [冲突记忆的当前规则索引](ccclm-current-policy/README.md)
- [先核验保存，再剪枝](ccclm-save-before-prune/README.md)
- [区分持久工作区与官方任务环境](ccclm-workspace-protocol/README.md)
- [不把跨题分数当策略消融](ccclm-metric-feedback/README.md)
- [完成状态只接受工具回执](ccclm-confirm-action-receipts/README.md)

## 运行时与研究资料隔离
仅将选中的 SKILL.md 复制到运行时技能目录；分类与单技能 README、EVIDENCE.md、EVALUATION.md 和 references 均留在被测容器及其检索路径之外。研究资料用于理解证据与局限，不应作为读取评测答案的入口。中英文版本择一使用。
