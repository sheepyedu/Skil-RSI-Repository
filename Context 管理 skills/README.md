# 四类 Context 管理技能（候选 v0.1）

基于仓库的原始长期轨迹开展模型辅助语义审阅，生成可执行候选；没有运行新的开关消融，不能宣称技能已经提分。原 `初始 skill/` 保留不动。

## 直接取用
每个子目录的 `SKILL.md` 是一个独立 Markdown 技能，可复制单个技能目录到目标框架支持的技能目录，或按触发条件读取。只复制所选技能目录；README、EVIDENCE、EVALUATION、references 等研究资料保留在被测容器之外，不随技能安装，也不配置运行时搜索可达。不要把整份研究报告注入 agent；优先使用与当前任务匹配的少数技能。技能内研究证据链接仅供仓库浏览复核，运行时不要求读取这些隔离文件。CLM 两类仅针对本仓库自定义接口，不能当成官方原生能力。

## Claude Code

- [恢复时对齐摘要与最新状态](Claude%20Code/cc-resume-state/SKILL.md)
- [记忆写入必须核验成功](Claude%20Code/cc-verify-memory-write/SKILL.md)
- [按语义定位而非历史行号检索](Claude%20Code/cc-semantic-memory-address/SKILL.md)
- [把观察假设规则分层并保留反例](Claude%20Code/cc-evidence-hypothesis/SKILL.md)
- [为实体与环境建立记忆作用域](Claude%20Code/cc-scope-and-version/SKILL.md)
- [反馈必须带指标范围且不反演唯一原因](Claude%20Code/cc-feedback-scope/SKILL.md)
- [分离简短活跃记忆和证据日志](Claude%20Code/cc-active-memory-index/SKILL.md)

## Claude Code CLM

- [先核验保存，再剪枝](Claude%20Code%20CLM/ccclm-save-before-prune/SKILL.md)
- [完成状态只接受工具回执](Claude%20Code%20CLM/ccclm-confirm-action-receipts/SKILL.md)
- [冲突记忆的当前规则索引](Claude%20Code%20CLM/ccclm-current-policy/SKILL.md)
- [不把跨题分数当策略消融](Claude%20Code%20CLM/ccclm-metric-feedback/SKILL.md)
- [区分持久工作区与官方任务环境](Claude%20Code%20CLM/ccclm-workspace-protocol/SKILL.md)
- [有余量且有进展的容量维护](Claude%20Code%20CLM/ccclm-capacity-maintenance/SKILL.md)

## Codex

- [验证记忆生命周期](Codex/cx-verify-persistence/SKILL.md)
- [原生压缩恢复契约](Codex/cx-resume-checkpoint/SKILL.md)
- [原始证据与聚合状态分离](Codex/cx-evidence-state/SKILL.md)
- [实体和版本约束检索](Codex/cx-scoped-retrieval/SKILL.md)
- [反馈驱动的规则变更单](Codex/cx-feedback-change/SKILL.md)
- [面向决策的渐进读取](Codex/cx-progressive-memory-read/SKILL.md)

## Codex CLM

- [事务式压缩与回读](Codex%20CLM/cxclm-transactional-edit/SKILL.md)
- [结构化状态与证据分层](Codex%20CLM/cxclm-structured-state/SKILL.md)
- [冲突保留与条件化复查](Codex%20CLM/cxclm-conflict-recheck/SKILL.md)
- [语义检索与记忆作用域](Codex%20CLM/cxclm-scoped-retrieval/SKILL.md)
- [活动索引生命周期](Codex%20CLM/cxclm-note-lifecycle/SKILL.md)
- [压缩效果与任务结果分开验证](Codex%20CLM/cxclm-measure-edit-effect/SKILL.md)

## 本轮发现
- 最大风险不仅是忘记，也包括把错误解释完整保存、实体串线、临时路径被误认为持久存储、旧规则未废止。
- Claude CLM q43 有“删除之后错误重构已查询事实”的直接证据，但发生在提交之后，不能说它导致本题掉分。
- 原生 Claude 两条序列的磁盘笔记持续增长，conversation compact 不等于笔记去冗余。
- Codex CLM 接受编辑后确有重新读取并使用笔记的案例；“有归档”与“检索有效”仍是两回事。
- 提示“先验证”会被违反，完成状态需要工具回执；运行器门控是建议改造，不是本技能包已经实现的功能。
- 同序列原生 Codex 54/100、CLM 53/100，不能凭单次差值判优劣；输入下降也不等于未缓存费用下降。

详见 [证据与覆盖边界](EVIDENCE.md)、[验证方案](EVALUATION.md)、[可复查索引说明](references/README.md)。研究索引不应作为运行时记忆注入。
