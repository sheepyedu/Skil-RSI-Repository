# 复现与核验

## 数据和运行条件

以 [SOURCES.json](data/SOURCES.json) 中的提交、数据修订、镜像 ID 和 SHA-256 为准。官方数据卡列出四个数据包、目录布局和许可证。依据仓库与数据包条款获取公开原件，验证其 SHA-256，再对照冻结题单核验任务指令和 Dockerfile。工作区内部保留官方测试、测试产物和原始任务文件。Security 仅启用冻结的防御性任务。 [官方数据卡](https://huggingface.co/datasets/tencent/workbuddy-bench/tree/3e8ad839685c589d83a1dd60fe2d15eabb75f27a)

正式运行依赖 Harbor 0.18.0 和 WorkBuddy 官方评测器。Claude Code 固定为 2.1.160，实验层通过只读挂载从隔离工作区启动。仓库中的部署入口记录原 H20 目录约定，复现者按实际环境配置 Docker、凭据入口与依赖。模型请求在宿主适配器由 Claude Messages 转为 DeepSeek Chat Completions。正式版真实题面已按原文传入，记录中同时归档上下文投影前后的请求。 [本次 CLM 核心代码与适配器](src/clm-core/) · [Claude Code CLM 的 CL-Bench 归档](../../archive/)

| 条件 | 原生组 | CLM 组 |
|---|---|---|
| 本地 CLI 配置窗口 | 200,000 token | 393,216 token |
| 会话维护 | 原生自动压缩 | 模型选工具交换裁剪和记忆更新，关闭原生自动压缩 |
| 题间预处理 | 原生续接 | 达到 285,000 消息字节时调用维护，投影目标 165,000 字节 |
| 作答模型 | DeepSeek V4.1 Flash | 同模型 |
| Web 外部评分 | GPT-6.1-sol | 同评分器 |
| 工作区与会话 | 每题隔离工作区、本组 UUID 连续 | 同机制，另一组独立 UUID |

两组的本地窗口随运行策略不同。结果反映这次冻结的两套配置，对其中任一参数的独立效果需要相同窗口的额外对照。逐题报告配对差值，保留失败及恢复阶段；单题差值不外推到整轮。

## 首三题监督

用 [只读脚本](src/inspect_run.py) 指向有权读取的运行目录。它读取命令执行结束后的回执，对在途请求给出状态和开始时刻，不干预进程。

- 输入验证。真实 DeepSeek 请求含官方题面与当前标记，续题核对上一题标记或原生压缩事件。
- 输出验证。逐请求核对完整标记、HTTP 状态、实际模型、原始响应闭合及原字节哈希。
- 会话与评分。核对实际 CLI init UUID、最终 result、存档 transcript、正式评分和 Web 评分器回执。
- 阶段边界。读取正式的冻结资格和实际进度文件，单独记录预处理、重试与终态。低分仍计入已有效评分的题目。

## 第 3 题恢复

`formal-02-resume-01` 使用同一冻结题单。将 `src/serial` 复制到独立目录，再覆盖 `src/serial-recovery-01` 的四个文件并放入 `src/inspect_run.py`。执行前核对 `formal-02` 终态、五条有效试验、预留会话快照和维护响应。该运行器首次只补发第 3 题 CLM 组，首三题通过逐请求验收才继续第 4 题。试跑和第 1、2 题采用原始的已冻结运行器，第 3 题 CLM 起才启用容量降级路径。汇总时以恢复目录的有效记录为准，同一条已通过的旧试验只计一次，保留原始失败维护尝试。 [恢复运行器](src/serial-recovery-01/)

第 4 题 CLM 恢复需要覆盖 [第二次恢复运行器](src/serial-recovery-02/)。入口读取先前的退出状态、七条成功试验和原始维护响应，沿用两条会话，修复后核验完整的四题前缀。实时状态及各题已结束回执可用 [只读进度脚本](src/checkpoint_run.py) 读取。

第 6 题 CLM 恢复覆盖 [第三次恢复运行器](src/serial-recovery-03/)。工具裁剪达到极限时，归档没有保留调用相依关系的旧推理块。离线探针逐字核对历史 benchmark 用户题面与全部可见助手文本。复核先看 CLI 与真实 DeepSeek 出入，然后检查 GPT 评分 SSE 终态。控制器接收的原始比分和评分服务异常一并保留。 [小时复核](CHECKPOINTS.md)

正式请求量从作答调用、外部评分和维护的原始记录核对，另计补评请求。重复带入恢复目录的原始试验按线次和启动时间去重。评分审计通过原请求 SHA-256 将同请求的失败和重试关联，同时查验官方评分项是否判为 API 异常。 [请求计数脚本](src/count_model_requests.py) · [评分状态脚本](src/audit_web_judges.py)

前 14 题两组的输出上限均为每请求 8,192 token。自第 15 题重跑起，同一上限提高到 16,384 token。第五次恢复从两组上一道已验收的会话和笔记重新启动，使用相同的冻结任务输入和评分规则。原第 15 题与重跑均保留，汇总按选定的同预算配对使用结果。 [配对重跑代码](src/serial-recovery-05/) · [输出上限原始回执](evidence/task-015-original-output-cap.json)

第 27 题的第六次恢复从第 26 对验收边界接续。已启动且正在等待的控制器读取 `operator-supervision/allow-formal-06.json`。用原 DeepSeek 服务完成一次新的最小探针后，运行 `python3 release_health_gate.py EXPERIMENT_DIR PROBE_DIR`，其中 `PROBE_DIR` 指向该实验下的 `operator-supervision/service-health-*`。工具核对冻结模型、成功回复及原始请求和响应的 SHA-256，并以一次原子操作创建放行文件；已有文件时退出。随后核对运行目录的 `start-gate.json` 和两组第 27 题首个实际请求。 [健康探针](src/probe_deepseek_health.py) · [放行工具](src/serial-recovery-06/release_health_gate.py) · [H20 文件系统验证](evidence/formal-02-recovery-06-gate-validation.json)

第 34 题起，CLM 仍先以 165,000 字节为回放目标。在用尽既有安全裁剪后，可将必须保留的内容保存在原 285,000 字节维护阈值以内。第 34 题离线回放复用原维护响应，原生会话与对外投影分别核对。33 条已完成题面和全部可见助手文本逐条相同，修改前后的原生会话各自留档。第七次恢复从原生组第 34 题和 CLM 第 33 题的已验收检查点续接。 [运行代码](src/serial-recovery-07/) · [离线回放回执](evidence/formal-02-recovery-07-offline-proof.json)

最终对照以冻结题单逐题配对，原始分和生效分同时保留。汇总代码要求完整的 60 对，计算全样本、子集、共享输出上限各阶段的计数与配对差，并单列剔除人工清理或末次响应不完整的配对后的结果。连续会话中的题目之间可能相互影响，汇总使用描述统计。 [最终汇总代码](src/summarize_paired_scores.py) · [版本与异常标记](analysis/run-qualification-annotations.json)

## 证据路径

有权限的协作者可在 H20 CPFS 查找 `/mount-data/Claude-code-CLM/experiments/workbuddy-20261118`。运行根的 `formal-02` 按 `native` 和 `clm` 分组：

- `evidence/<题序-子集-任务>/wire` 保存 Claude Messages 原文和投影、Web 评分模型调用及传输回执。
- `evidence/<题序-子集-任务>/chat-gateway` 保存真实 DeepSeek 输入、原始 SSE 或 JSON 输出、终态与用量。
- `trials/<题序-子集-任务>/agent` 和 `verifier` 保存 CLI、ATIF 和官方评分。题目产物在对应 `artifacts` 下。
- `clm/maintenance` 保存题间维护请求、模型选取、修改前后会话副本和校验值。
- `pilot-01` 至 `pilot-08`、`formal-01`、`formal-02`、`formal-02-resume-01`、`plumbing-*` 和 `sync-probes` 保存正式执行、诊断和恢复。GitHub 上的 [尝试数据](evidence/attempts/) 保留各批次有效轨迹和失败的可公开元数据。
