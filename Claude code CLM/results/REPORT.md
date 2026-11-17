# DeepSeek Claude Code CLM 单会话串行评测

同一个原生会话执行并评分 100 题，达标 38/100。原生完整终态 99/100。模型提交的 CLM 编辑实际生效 40 次，原生自动压缩 0 次。

| 类别 | 题数 | CLM 达标 | 既有自动压缩基线达标 | CLM 编辑接受 |
| --- | ---: | ---: | ---: | ---: |
| blind_spectrum_monitoring | 30 | 0 | 0 | 0 |
| codebase_adaptation | 7 | 7 | 7 | 0 |
| cohort_studies | 6 | 2 | 4 | 5 |
| database_exploration | 13 | 12 | 11 | 8 |
| exploitable_poker | 40 | 14 | 17 | 11 |
| sales_prediction | 4 | 3 | 4 | 14 |

实际 Messages 生成请求 680 次，其中 HTTP 200 且完整 680 次。累计已知输入 73,691,637 token，输出 375,725 token。单次最大已知输入 239,734 token。

共有 66 道题的笔记内容发生变化。模型发出的显式记忆工具调用 {"notes_write": 7, "notes_edit": 65, "clm_context_status": 4, "clm_context_edit": 1, "notes_read": 4, "clm__catalog": 57, "clm__prune": 39, "notes_grep": 2}。接受和拒绝的编辑分别保留。

## 单会话恢复

原始阶段 38 题完成，200,000 token 本地窗口在第 39 题触发 blocking_limit。第一恢复段 4 题有官方成绩，沿用原生 session ID、原历史及笔记。第 39 题的三条既有环境动作在恢复环境核对，官方观察逐条匹配。第 42 题官方评分已形成，原生总结再次因 blocking_limit 中断。第一恢复段使用 262,144 本地窗口、16,384 最大输出设定及 130,000 token 容量提醒。

随后试用原生 Bash 专用回合，模型多次选择无关的 shell 命令。试验停止前第 43 题没有执行官方动作。最终同一会话通过 CLM catalog/prune MCP 完成其余 58 题。该段本地窗口为 393,216，实际上一轮用量达到 120,000 token 时网关先安排维护回合，维护回合限定可用的记忆工具并关闭 thinking。模型在 catalog 中自行选 ID；正式任务回合继续使用原工具及 thinking high。这些接线调整仅适用于此实验分支。

第 39 题恢复段首次接受模型提交的编辑，删除 12 组旧工具交换。该请求历史消息从 673,258 降至 464,596 字节，上游实际输入 123,830 token。

固定 CL-Bench 题库和分类题序与既有基线一致。使用 DeepSeek 专用 Chat Completions 及 Claude Code 2.1.160 原生工具。逐题继续同一会话和笔记工作区，官方任务环境逐题切换。

这一实验记录单条序列。对照来自既有自动压缩实验，运行期、提示词、Bash 编辑工具及 压缩策略不同。结果可以逐题描述差异，无法单独识别 CLM 的因果增益。
