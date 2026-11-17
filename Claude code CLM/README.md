# Claude code CLM

使用 DeepSeek V4.1 Flash API 和隔离的 Claude Code 运行 CL-Bench 单会话串行评测。官方固定版本 `5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26` 含 301 题，按六类比例抽取 100 题，沿用既有分类基线的同一题序。

- 100 道题获得官方评分，38 道达标。同题同序的既有原生压缩基线为 43 道达标。
- 680 次 DeepSeek 请求全部获得完整 HTTP 200 响应，40 次 CLM 编辑生效，原生自动压缩 0 次。
- 102 个执行记录包含原生 CLI 轨迹，涵盖两次上下文阻断、恢复与第 43 题的 Bash 维护尝试。该次尝试在生成逐题结果前中断，并保留原始日志。
- [实验报告](results/REPORT.md) · [固定题单](results/PLAN.json) · [逐题分数](results/tasks.csv) · [有效编辑](results/edits.json) · [会话接续证据](results/SESSION_LINEAGE.json)

## 原始轨迹

压缩归档包含 Claude Code 原始 Messages 请求、CLM 投影后的 Messages、实际 DeepSeek Chat 请求、原始回复 SSE 与接口返回的思考字段、转回 Claude Code 的响应、逐请求回执、官方动作与观察、逐题笔记和原生会话 JSONL。归档也保存各阶段的故障与退出记录。运行配置、整个用户 HOME 和符号链接不随包发布。

1. 下载 [CLAUDE_CODE_CLM_ROLLOUTS.tar.zst](archive/CLAUDE_CODE_CLM_ROLLOUTS.tar.zst)。
2. 在归档目录运行 `shasum -a 256 -c SHA256SUMS`，核对压缩包的 SHA-256。
3. 执行 `zstd -dc CLAUDE_CODE_CLM_ROLLOUTS.tar.zst | tar -xf -` 解包。逐文件校验和位于包内的 `ARCHIVE_FILE_MANIFEST.json`。

压缩包清单见 [MANIFEST.json](archive/MANIFEST.json)，逐阶段轨迹库存见 [TRACE_INVENTORY.json](archive/TRACE_INVENTORY.json)。框架实现见 [Claude-code-CLM 源仓库](https://github.com/sheepyedu/Claude-code-CLM)。
