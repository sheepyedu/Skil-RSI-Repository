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

## 两组运行轨迹

两组各串行完成同一顺序的 100 道 CL-Bench 题。原生 Codex 达标 54 题，Codex CLM 达标 53 题。[配对报告](results/native-vs-clm/REPORT.md) · [逐题配对结果](results/native-vs-clm/PAIRED_COMPARISON.json)

| 运行 | 轨迹包 | 请求 |
|---|---|---|
| 原生 Codex | [NATIVE_CODEX_ROLLOUTS.tar.zst](trajectories/NATIVE_CODEX_ROLLOUTS.tar.zst) | 511 次请求，505 条完整响应，6 条失败或截断 |
| Codex CLM | [CODEX_CLM_ROLLOUTS.tar.zst](trajectories/CODEX_CLM_ROLLOUTS.tar.zst) | 591 次请求，591 条完整响应 |

每个包包含原生会话、逐请求输入与响应、工具调用和评分。原生 Codex 包也包含中断及恢复记录。解包后可用内置的 `ARCHIVE_FILE_MANIFEST.json` 校验每个成员。归档整体校验值见 [SHA256SUMS](trajectories/SHA256SUMS)。

```sh
cd 'Codex CLM/trajectories'
shasum -a 256 -c SHA256SUMS
mkdir -p native-codex codex-clm
zstd -dc NATIVE_CODEX_ROLLOUTS.tar.zst | tar -xf - -C native-codex
zstd -dc CODEX_CLM_ROLLOUTS.tar.zst | tar -xf - -C codex-clm
```

## WorkBuddy Bench（独立实验，目标尚未完成）

[原生Codex与Codex CLM串行评测](workbuddy-20261118/README.md)：冻结65题/130条；当前前60对、120条完成并评分，第61题遭服务端策略拒绝、未评分，另9槽位未启动。[完整阶段轨迹检查点](workbuddy-20261118/checkpoints/prefix60-policy-20261119/README.md)保留全部输入输出、原生会话、工具、失败恢复及评分；3.29GB分卷已双端完整校验。原有CL-Bench 100题结果与轨迹保持。
