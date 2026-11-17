# Codex CLM

在阿里云 H20 的独立 Codex CLI 容器中接入模型可编辑上下文。Codex 在同一原生会话内，使用与 Claude Code CLM 相同的冻结题目和顺序完成 CL-Bench 100 题。

- 模型为 `gpt-6.1-sol`，reasoning effort 为 low。
- 官方评分 **100/100**，达标 **53/100**。
- 591 次 Responses 返回 HTTP 200 及完整结束事件，19 次模型主动提交的 CLM 编辑通过核验。

| 目录 | 内容 |
|---|---|
| [source/](source/) | Codex CLM 运行源码、容器隔离探针和合成验收 |
| [benchmark/](benchmark/) | 本次串行评测的驱动、记录网关及审计脚本 |
| [results/](results/) | 原冻结题序、逐题成绩、终局报告和汇总证据 |

[运行方式与框架图](source/README.md) · [完整报告](results/REPORT.md) · [逐题成绩](results/tasks.csv) · [终局审计](results/FINAL_AUDIT.json)

原始请求、响应流和模型工作区的轨迹路径见报告，文件保存在 H20 实验目录。
