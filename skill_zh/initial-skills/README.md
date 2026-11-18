# 初始 Context 管理 skills

这里是从本仓库长期轨迹分析提炼的 10 项初始候选 skill，每项单独保存为 Markdown，可按场景直接读取或复制进你的 skill 加载流程。

## 目录

1. [压缩前写任务状态卡](01-task-state-card/SKILL.md)
2. [把观察、假设和规则分层保存](02-evidence-hypothesis-layers/SKILL.md)
3. [先核反馈口径再修订经验](03-feedback-definition-check/SKILL.md)
4. [复用方法，不照搬实例答案](04-method-instance-separation/SKILL.md)
5. [编辑失败后重建文件状态](05-file-edit-recovery/SKILL.md)
6. [摘要保留可核验数值及方向](06-numeric-direction-consistency/SKILL.md)
7. [区分模型编辑损失与传输损坏](07-transport-integrity-diagnosis/SKILL.md)
8. [先确认存储生命周期](08-storage-lifecycle/SKILL.md)
9. [每条观察绑定实体，而非只依赖同文件分节](09-entity-binding/SKILL.md)
10. [按标题或实体定位，不保存易漂移的固定行号](10-semantic-retrieval/SKILL.md)

## 使用方式

1. 按触发条件选择少量相关文件，不要每轮全量塞入上下文。
2. 将文件中的执行步骤作为候选策略使用；实际工具、路径和权限仍以运行环境为准。
3. 压缩、检索、写回时记录采用了哪项 skill、额外成本和结果，便于比较。
4. 先冻结这一版，在未见实例上与原生基线对照，再决定保留、修订或撤销；本次发现集上的再次表现不能直接当作泛化收益。

## 边界

- 原实验是同一组 100 题的两种顺序，共 200 题次，而非 200 道独立题。
- 19 次压缩由 Claude Code 原生阈值触发，模型写摘要并自主读写笔记；这不是 CLM 自主决定 Context 编辑时机的完整复现。
- 这些是 v0.1 候选，没有已验证的成功率或性能提升承诺；不含具体测试题答案。
- Skill 7 属于具备日志可见性时的工程诊断，其余也不授予额外权限。本目录只是 Markdown 内容，不代表已自动安装为 Claude Code 原生技能。
- 验证建议：固定模型、预算和任务条件，多 seed，分别衡量达标率、原始 API token、延迟、检索命中、工具重试和错误知识复用。发现集、开发集和最终测试集分开。

## 双语整理与迁移

本目录由旧 `初始 skill/` 迁入；每个技能现在位于独立子目录中的 `SKILL.md`，并附 README 说明归纳环节和适用范围。保留原 v0.1 内容和使用边界，本次目录整理不代表新增实验验证。英文版位于 [`skill/initial-skills`](../../skill/initial-skills/README.md)，中文版位于当前目录。原始轨迹及其归档位置不变。研究证据和评测材料不应复制进被测运行环境。
