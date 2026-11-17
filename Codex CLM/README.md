# Codex CLM

本目录归档 H20 上的 Codex CLM 实现及同一会话的 CL-Bench 100 题串行评测。

- 模型为 `gpt-6.1-sol`，reasoning effort 为 low。单个 Codex app-server 线程顺序评分 100 题，53 题达标，原生进程退出码 0。
- 591 次 Responses 请求均返回 HTTP 200 及唯一的完成事件，19 次 CLM 历史编辑生效。
- 固定 100 题及顺序与 Claude Code CLM 实验一致。单条实验记录提供描述性结果。

[源码和运行方式](source/README.md) · [原源码仓库](https://github.com/sheepyedu/Codex-CLM) · [评测报告](results/REPORT.md) · [逐题成绩](results/tasks.csv)

## 原始轨迹

[下载 CODEX_CLM_ROLLOUTS.tar.zst](archive/CODEX_CLM_ROLLOUTS.tar.zst)。归档包括网关收到的原始 Responses input、CLM 投影后实际发出的 Responses 请求、接口原始 SSE、逐请求编辑回执、Codex 原生会话及 app-server 轨迹、逐题动作与评分，以及隔离工作区的笔记。运行 HOME 中的认证与配置保留在服务器。

1. 在归档目录运行 `shasum -a 256 -c SHA256SUMS` 检查下载。
2. 执行 `zstd -dc CODEX_CLM_ROLLOUTS.tar.zst | tar -xf -` 解包。
3. 包内 `ARCHIVE_FILE_MANIFEST.json` 提供逐文件 SHA-256。归档范围与请求计数见 [校验清单](archive/MANIFEST.json)。
