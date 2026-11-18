# WorkBuddy Bench · Claude Code 与 CLM 串行对照

**2026-11-18 北京时间。运行批次 `formal-02`，恢复批次 `formal-02-resume-01`。** 两条 Claude Code 2.1.160 线路使用同一份 60 题清单和同一题序。每组使用独立且连续的原生会话 UUID，每道题使用隔离的官方工作区，组内延续会话和笔记。执行顺序为同题原生组、CLM 组，随后进入下一题。作答模型均为 DeepSeek V4.1 Flash `deepseek-v4-1-flash-261017`。Web 的外部视觉评分使用 GPT-6.1-sol，其余按对应的官方评分方式。

| 子集 | 官方 v1.0 | 正式选题 | 独立试跑 |
|---|---:|---:|---:|
| Code | 80 | 20 | 1 |
| Office | 50 | 12 | 1 |
| Security | 60 | 10 | 1 |
| Web | 70 | 18 | 1 |
| 合计 | 260 | 60 | 4 |

Security 使用经过范围核对的离线防御性任务。冻结题单记录每道题的正文与 Dockerfile SHA-256。四类试跑题与正式题单分离。上一阶段的受控编辑版与在跑版采用不同实现，结果分别留档。

## GitHub 归档

- [数据来源与镜像版本](data/SOURCES.json)、[实际环境](data/ENVIRONMENT.json)、[正式题单](data/formal-plan.json)、[试跑题单](data/pilot-plan.json)、[选题清单](data/approved-tasks.json)
- [精确题面的八条试跑验收](evidence/pilot-exact.json)、[独立会话同步验证](evidence/session-sync-proof.json)、[各尝试索引](evidence/attempt-directories.json)
- [首次运行观测](evidence/observation-2054.json)、[问题及解决记录](INCIDENTS.md)、[复现和验收口径](REPRODUCE.md)
- [实际输入目录逐文件校验清单](data/) 包含正式 60 题和试跑 4 题，共 1,021 个分阶段文件。
- [试跑与诊断逐尝试数据](evidence/attempts/) 保存 15 个执行目录的运行、异常、API 用量和用时元数据。复用记录保留其对应阶段，汇总时按实际试验版本去重。
- [冻结运行器](src/serial/)、[正式恢复运行器](src/serial-recovery-01/)、[会话同步验证版本](src/serial-sync/)、[同步事务实现](src/session-sync/)、[只读审计工具](src/inspect_run.py)

`formal-02` 已完成两道配对题和第 3 题原生组。第 3 题 CLM 组开题前的维护发现旧编辑操作无法满足预算，控制器保留证据并停止。恢复版沿用五条验收记录与两个原会话 UUID，序列首次补跑第 3 题 CLM 组，随后独立核验首三题，再进入第 4 题。[中断时逐请求观测](evidence/observation-2133-formal-02-stop.json) · [离线复验](evidence/formal-02-recovery-probe.json)

此阶段归档不代表 60 题全部结束。GitHub 保存题单、源版本、校验值、执行代码和可公开观测。完整原始会话、逐请求正文、响应流、CLI 输出、题目产物、失败尝试、敏感配置与原始依赖包留在访问受控的 H20 CPFS。原始第三方数据由上游分发，公开索引可核对实际使用版本及全部归档校验值。混合 Security 压缩包含超出本次防御范围的任务。可公开逐请求文件记录完整性、哈希、用量和状态。

官方数据及条款。[WorkBuddy Bench v1.0 固定数据版本](https://huggingface.co/datasets/tencent/workbuddy-bench/tree/3e8ad839685c589d83a1dd60fe2d15eabb75f27a) · [固定框架版本](https://github.com/Tencent/workbuddy-bench/tree/625b2233093ae4f23e76be28c1f341d41cc70373) · [Tencent 条款](data/TENCENT-LICENSE.txt)
