# Codex CLM · CL-Bench 固定序列

原始发行包为 Continual Learning Bench `5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26`，源数据 301 题。服务器验证清单为 `/mount-data/Datasets/continual-learning-bench/VERIFIED.json`。

| 分组顺序 | 原始题数 | 本次题数 |
|---|---:|---:|
| 频谱监测 | 90 | 30 |
| 代码库适配 | 19 | 7 |
| 队列研究 | 20 | 6 |
| 数据库探索 | 40 | 13 |
| 可利用扑克策略分析 | 120 | 40 |
| 销售预测 | 12 | 4 |
| 合计 | 301 | 100 |

题目 ID、canonical index、阶段和固定顺序由 `PLAN.json` 提供，文件逐字沿用 Claude Code CLM 正式实验，SHA-256 为 `2cfc987dacf1a2810e34a8e72a006cbe06b978d2099f53908833aa7a3e9a471e`。

使用 Codex CLI 0.169.0 原生 app-server stdio，一个正式线程，一个活跃题目。官方工具经动态工具请求调用同一份 benchmark 接线，各题依照固定计划进入官方环境并在终态后调用原始 evaluate。用户任务历史、工作目录和 CLM 投影随同一个线程持续。工具定义及 SSE 沿用原生 Responses 链路。gpt-6.1-sol，reasoning effort low。任务提示在上一条请求达到 120,000 输入 token 时提醒模型管理容量。CLM 删除必须由模型主动提交。容器和 CPU 路径与其他运行隔离。

`observe.py` 从官方 case 记录、Codex 原生事件和网关 Responses 回执聚合。评分已完成、官方 success、上下文连续性证据及 accepted edits 是不同维度。请求体字节数来自实际 Responses input 的压缩 JSON。原生 token 为 Codex 事件中每请求返回的 usage，分别列出输入、缓存输入和输出。单条固定序列提供描述性结果。
