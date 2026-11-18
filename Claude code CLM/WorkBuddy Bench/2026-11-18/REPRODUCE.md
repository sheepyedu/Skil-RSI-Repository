# 复现与核验

## 数据和运行条件

以 [SOURCES.json](data/SOURCES.json) 中的提交、数据修订、镜像 ID 和 SHA-256 为准。官方数据卡列出四个数据包、目录布局和许可证。依据仓库与数据包条款获取公开原件，验证其 SHA-256，再对照冻结题单核验任务指令和 Dockerfile。工作区内部保留官方测试、测试产物和原始任务文件。Security 仅启用冻结的防御性任务。 [官方数据卡](https://huggingface.co/datasets/tencent/workbuddy-bench/tree/3e8ad839685c589d83a1dd60fe2d15eabb75f27a)

正式运行依赖 Harbor 0.18.0 和 WorkBuddy 官方评测器。Claude Code 固定为 2.1.160，实验层通过只读挂载从隔离工作区启动。仓库中的部署入口记录原 H20 目录约定，复现者按实际环境配置 Docker、凭据入口与依赖。模型请求在宿主适配器由 Claude Messages 转为 DeepSeek Chat Completions。可以从相邻 [Claude Code CLM 的 CL-Bench 归档](../archive/) 获取上一次使用的适配器，对照固定 SHA。正式版真实题面已按原文传入，记录中同时归档上下文投影前后的请求。

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

## 证据路径

有权限的协作者可在 H20 CPFS 查找 `/mount-data/Claude-code-CLM/experiments/workbuddy-20261118`。运行根的 `formal-02` 按 `native` 和 `clm` 分组：

- `evidence/<题序-子集-任务>/wire` 保存 Claude Messages 原文和投影、Web 评分模型调用及传输回执。
- `evidence/<题序-子集-任务>/chat-gateway` 保存真实 DeepSeek 输入、原始 SSE 或 JSON 输出、终态与用量。
- `trials/<题序-子集-任务>/agent` 和 `verifier` 保存 CLI、ATIF 和官方评分。题目产物在对应 `artifacts` 下。
- `clm/maintenance` 保存题间维护请求、模型选取、修改前后会话副本和校验值。
- `pilot-01` 至 `pilot-08`、`formal-01`、`plumbing-*` 和 `sync-probes` 保存诊断及修复尝试。GitHub 上的 [尝试索引](evidence/attempt-directories.json) 描述观测时点已存在的运行目录。
