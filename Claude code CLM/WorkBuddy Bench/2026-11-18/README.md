# WorkBuddy Bench · Claude Code 与 CLM 串行对照

**2026-11-18 北京时间开始。运行批次 `formal-02`，续接批次为 `formal-02-resume-01` 至 `formal-02-resume-05`。** 两条 Claude Code 2.1.160 线路使用同一份 60 题清单和同一题序。每组使用独立且连续的原生会话 UUID，每道题使用隔离的官方工作区，组内延续会话和笔记。执行顺序为同题原生组、CLM 组，随后进入下一题。作答模型均为 DeepSeek V4.1 Flash `deepseek-v4-1-flash-261017`。Web 外部评分使用 GPT-6.1-sol，其余按对应的官方评分方式。

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
- [冻结运行器](src/serial/)、[正式恢复运行器](src/serial-recovery-01/)、[CLM 核心代码](src/clm-core/)、[会话同步验证版本](src/serial-sync/)、[同步事务实现](src/session-sync/)、[只读审计工具](src/inspect_run.py)

`formal-02` 已完成两道配对题和第 3 题原生组。第 3 题 CLM 组开题前的维护发现旧编辑操作无法满足预算，控制器保留证据并停止。恢复版沿用五条验收记录与两个原会话 UUID，补齐第 3 题 CLM 组。北京时间 21:48，前三题的两组均通过输入、输出、会话和评分的独立核验，控制器已放行第 4 题。[前三题监督报告](FIRST-THREE.md) · [中断时观测](evidence/observation-2133-formal-02-stop.json) · [离线复验](evidence/formal-02-recovery-probe.json)

第 4 题 CLM 开题前的维护响应含两个未列入候选的 ID。第二次恢复沿用七条验收记录，过滤未列出项并保持原会话与题序。第 4 题 CLM 在人工清理残留后台搜索后完成，四题共 8 条线次均已验收，第 5 题已放行。 [第 4 题停机观测](evidence/observation-2201-formal-02-resume-01-stop.json) · [第二次恢复验证](evidence/formal-02-recovery-02-probe.json) · [四题验收](evidence/formal-first-four.json)

原始会话等文件可按 [已终止批次的原轨迹校验清单索引](evidence/retained-trajectory-inventories.json) 在 H20 上核对。

22:49 首次小时复核记录 5 道已收配对。第 5 题 CLM 有一项评分遭遇上游错误，第 6 题在维护修复后继续。 [小时复核](CHECKPOINTS.md) · [第三次恢复运行器](src/serial-recovery-03/)

第 5 题补评重用相同的冻结产物和模型，按 WorkBuddy 官方规则把 CLM 分数从 0.5 修正为 0.8。对照汇总已经按原始回执哈希应用修正。 [补评记录](REGRADING.md) · [评分修正账本](analysis/score-corrections.json)

第 15 题发生输出预算终止。两组从第 14 题的独立检查点续接，在同一 16,384 token 上限下完成重跑，得分为原生 0.809、CLM 0.8876。原先 8,192 token 的两条第 15 题试验均留档。 [输出预算故障与恢复](INCIDENTS.md) · [第 15 题原始尝试](evidence/task-015-original-output-cap.json) · [恢复后配对验收](evidence/task-015-recovered-pair.json)

2026-11-19 11:41，原 DeepSeek V4.1 Flash 入口恢复并通过真实生成核验。截至 11:57，已完成 27/60 道配对，原生与 CLM 已沿用各自原会话完成第 27 题，控制器已启动第 28 题。阶段正式请求 1,569 次，另有 5 次补评。 [恢复记录](INCIDENTS.md) · [第 27 题配对验收](evidence/task-027-recovered-pair.json) · [请求计数](evidence/hourly/2026-11-19-1157-request-counts.json)

此阶段归档不代表 60 题全部结束。GitHub 保存题单、源版本、校验值、执行代码和可公开观测。完整原始会话、逐请求正文、响应流、CLI 输出、题目产物、失败尝试、敏感配置与原始依赖包留在访问受控的 H20 CPFS。原始第三方数据由上游分发，公开索引可核对实际使用版本及全部归档校验值。混合 Security 压缩包含超出本次防御范围的任务。可公开逐请求文件记录完整性、哈希、用量和状态。

官方数据及条款。[WorkBuddy Bench v1.0 固定数据版本](https://huggingface.co/datasets/tencent/workbuddy-bench/tree/3e8ad839685c589d83a1dd60fe2d15eabb75f27a) · [固定框架版本](https://github.com/Tencent/workbuddy-bench/tree/625b2233093ae4f23e76be28c1f341d41cc70373) · [Tencent 条款](data/TENCENT-LICENSE.txt)
