# Codex CLM · CL-Bench 100 题终局自查

2026-11-17 北京时间 14:42:33 至 16:55:03。原生线程 `01a1e83e-3c61-7cf0-ae3c-3ab926adc239`，100 个不重叠原生 turn，官方评分 **100/100**，达标 **53/100**。原生退出码 0。

## 题目来源与结果

固定官方数据版本 `5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26` 的 default 数据共 301 题。Codex 与 Claude Code CLM 的 PLAN.json 在服务器重新计算 SHA-256 一致，冻结的 100 题顺序未改。模型为 `gpt-6.1-sol`（low）。

| 冻结顺序 | 原始题数 | 本轮已评分 | 官方达标 |
|---|---:|---:|---:|
| 频谱监测 | 90 | 30 | 3 |
| 代码库适配 | 19 | 7 | 7 |
| 队列研究 | 20 | 6 | 5 |
| 数据库探索 | 40 | 13 | 13 |
| 扑克 | 120 | 40 | 21 |
| 销售预测 | 12 | 4 | 4 |
| 合计 | 301 | 100 | 53 |

## 连续上下文和记忆编辑

- 100 个任务首请求全部包含此前应有的用户任务标记。全程原生自动压缩 0 次。
- 591 条真实 Responses SSE 均 HTTP 200 并收到唯一完成事件。网关 19 次接受模型提交的历史编辑，逐请求检查原始及出站 input 哈希、消息对及任务标记。
- 首次有效编辑在第 2 题的第 6 个请求，保留第 1、2 题用户标记，匹配并删除旧 custom_tool_call 与 output，另移除该组的相邻条目。该轮从 72,676 降至 67,546 字节。
- 原生 shell 记录显示模型跨题复用 `spectrum_memory/scan_history.json`、`database_memory/products.txt`、`poker_memory/opponents.txt`。这是单条固定序列的行为观测，计分效果的因果估计需要配对对照。
- 峰值输入 141,266 token。原生请求回执累计输入 48,890,579 token，其中缓存输入 43,420,509；输出 83,794。

## 原始证据

- 本机 `evidence/FINAL_AUDIT.json`、`evidence/FINAL_OBSERVATION.json`、`evidence/CLEANUP.txt` 和冻结 `PLAN.json`。
- H20 `/mount-data/Codex-CLM/experiments/clbench100-20261117` 下的 `cases/*/result.json`、`native.jsonl` 和正式会话 `runs/codex-clm-87a302cc479846d59f7b8a5889ee512f/wire/`。
- 实验由同一 Codex app-server 进程执行。公网 SSH 观察短时断开后使用既有跳板检查运行状态。实验进程没有因此重启。
