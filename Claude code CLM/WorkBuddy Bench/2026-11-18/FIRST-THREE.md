# 正式前三题输入输出监督

北京时间 2026-11-18 21:48:46，运行器完成独立验收。两组共 6 条试验，模型作答共 183 次，Web 评分模型调用共 62 次。全部调用有完整响应闭合，6 条 CLI 记录有匹配的原生会话 UUID、正常终态、保存的会话及正式评分。

| 顺序和任务 | 原生得分 | CLM 得分 | DeepSeek 完整调用（原生／CLM） | Web 评分调用（原生／CLM） |
|---|---:|---:|---:|---:|
| 1 · Security · linux-ld-preload-investigation | 0.7613 | 0.8283 | 20／27 | — |
| 2 · Web · dense-saas-visual-refactor-L3-046 | 0.2 | 0.0 | 43／37 | 15／15 |
| 3 · Web · security-privacy-permission-review-L4-020 | 0.7 | 1.0 | 29／27 | 16／16 |

每条试验都在实际发往 DeepSeek 的请求里核对官方原题和当前任务标记。四条续题试验的首个请求均含上一题标记。原生组第 3 题在题内发生一次自动压缩，后续调用和评分完整。CLM 组第 3 题恢复后首次真实请求为 34,497 输入 token，作答和评分均完成。第 2 题 CLM 得分 0.0 来自官方评分。以上只覆盖前三题。

`formal-02` 的五条有效试验原样带入 `formal-02-resume-01`。CLM 第 3 题最初停在题间维护，保留维护请求、响应、原始会话和退出码。恢复后仅补第 3 题 CLM 组，控制器写入前三题验收回执后才放行第 4 题。此处调用计数以每条有效试验的实际作答与评分请求为准，独立维护请求另有记录。

[逐请求输入和输出哈希、用量与会话回执](evidence/formal-first-three.json) · [正式原始尝试索引](evidence/attempts/formal-02.jsonl) · [恢复前缀索引](evidence/attempts/formal-02-resume-01-prefix.jsonl) · [故障及修复](INCIDENTS.md)
