# WorkBuddy Bench 正式对照结果

北京时间 2026 年 11 月 19 日 22:52 完成 **60/60 道配对、120 条有效线次**。原生 Claude Code 平均有效分 **0.6467**，CLM **0.6344**，CLM 低 **1.23 个百分点**。CLM 得分较高 12 题，原生较高 16 题，平分 32 题。两组均使用 Claude Code 2.1.160、DeepSeek V4.1 Flash 和冻结题单，各自沿用原会话。 [逐题分数](analysis/final-scores.csv) · [机器可读汇总](analysis/final-comparison.json) · [原会话和时序核验](evidence/final-serial-order.json)

## 按子集比较

| 子集 | 配对题数 | 原生均分 | CLM 均分 | CLM − 原生（百分点） |
|---|---:|---:|---:|---:|
| Code | 20 | 0.5206 | 0.5504 | +2.98 |
| Office | 12 | 0.7539 | 0.7549 | +0.10 |
| Security（防御） | 10 | 0.8343 | 0.8398 | +0.56 |
| Web | 18 | 0.6111 | 0.5333 | −7.78 |
| 共计 | 60 | 0.6467 | 0.6344 | −1.23 |

每道配对等权。按题求差后取均值，第 5 题采用有效补评分。题号 51–53 和 60 的 CLM 各返回一次完整响应，响应中没有工具调用，官方零分保留。 [原始分与有效分](analysis/final-scores.json) · [第 51–53 题核验](evidence/tasks-051-053-clm-single-response-review.json) · [第 60 题核验](evidence/task-060-clm-single-response.json)

## 请求和上下文维护

正式运行及失败尝试共发送 4,337 次请求，另有 5 次补评。正式请求包括 3,906 次作答、391 次 Web 评分及 40 次 CLM 维护。诊断探针另行记录。复核 36 条 Web 评分线次后，待补评异常为 0。第 5 题 CLM 使用相同冻结产物、官方规则及评分模型补评，分数由 0.5 修正为 0.8。 [最终请求计数](evidence/hourly/2026-11-19-2252-request-counts.json) · [Web 评分审计](evidence/hourly/2026-11-19-2252-web-judge-health.json) · [补评记录](REGRADING.md)

从最终采用的试验回执统计，原生组发出 2,483 次作答请求，闭合 2,482 次，供应商回报累计 222,551,636 个输入 token。CLM 发出并闭合 1,303 次作答请求，累计 94,319,160 个输入 token。CLM 的计数比原生少 57.6% 输入 token。该差值同时包含每次上下文大小和作答步数的区别。原生记录 28 次自带压缩，CLM 在题间实际写回原会话 39 次，题内记录中获接受的编辑为 0。39 次题间写回均核对了修改前后 JSONL 的哈希，37 次回执逐条核对可见助手文本。 [轨迹和维护审计](evidence/final-trajectory-audit.json)

## 恢复与解释范围

第 1–14 题两组输出上限均为 8,192 token，CLM 平均高 9.02 个百分点。第 15–60 题两组上限均为 16,384 token，CLM 平均低 4.35 个百分点。第 34 题保留 CLM 的必要历史，第 48 题提前触发 CLM 题间维护，第 56 题提前触发原生压缩。第 56 题沿用早先有效的 CLM 成绩，之后重跑原生。120 条采用的线次按实际时间核对，无时间重叠，各组与冻结题序一致。 [运行版本与异常标记](analysis/run-qualification-annotations.json) · [修复记录](INCIDENTS.md) · [时序审计](evidence/final-serial-order.json)

剔除 9 道标记了后台清理、容量重跑或末次响应未闭合的配对后，51 道配对的 CLM 均分相差 −1.48 个百分点。两个输出上限阶段使用不同的题目位置，结果描述本次连续会话、题序和版本，分阶段差值也包含题目和先前历史的影响。 [敏感性结果与分阶段均分](analysis/final-comparison.json)

## 轨迹留存

最终 H20 批次 `formal-02-resume-09` 的轨迹清单含 76,178 个文件及逐文件 SHA-256，共 12,414,835,219 字节。120 条有效线次的原生会话日志、CLI 输出、ATIF、时序与评分回执全部覆盖。控制器退出码为 0，已退出。此前批次继续保留失败试验及其原始输入、响应、会话和评分。GitHub 保存可公开结果、代码、故障和修复记录，以及可供核验的索引。 [最终轨迹审计](evidence/final-trajectory-audit.json) · [历次轨迹索引](evidence/retained-trajectory-inventories.json) · [分阶段监督](CHECKPOINTS.md)
