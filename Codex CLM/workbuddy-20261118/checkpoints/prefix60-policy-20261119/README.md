# WorkBuddy Codex：前60对及策略拒绝的全轨迹检查点

冻结目标为65题、两臂130条。当前完成60对、120条评分；第61题原生首个API请求被服务端 `cyber_policy` 拒绝，未评分、未执行工具，另9槽位未启动。**65题目标仍未完成。** 两臂保持原thread、原冻结题序；没有改写请求或换通道绕过策略限制。

[阶段报告](PREFIX60_REPORT.md) · [逐题成绩](prefix60-audit/paired.csv) · [请求用量](CURRENT_SNAPSHOT_USAGE.md) · [冻结130槽位状态](FROZEN65_EXECUTION_STATUS_01.json) · [拒绝原证据索引](POLICY_REFUSAL_061_01.json) · [运行源码](source/README.md) · [橙色修改区与提示词](framework-docs-v6/FRAMEWORK.md)

原生平均reward 0.753175，CLM 0.718195；CLM胜15、平26、原生胜19。这是单条连续会话链上的描述统计，不能单独证明记忆机制的因果效果。评分修复、动态分母局限和原始失败在报告与归档中逐项保留。

## 全部当前轨迹

全目录快照形成于2026-11-19 09:14（北京时间），包含55292条目、19505029011B逻辑内容；ZIP 3292817014B，SHA256 `40667201f924a9306bd86053a70a1ad0b117d5e6e988b9d3500bd59fdcc502fe`。没有目录排除，目录符号链接仅保存元数据。服务器和Mac均已核验全部压缩块CRC/SHA及所有原文件还原配方；回执见 [verification/](verification/)。私有GPT key扫描匹配0。

为便于GitHub存储，原ZIP按8MiB分卷；分卷重组字节必须与上述ZIP完全相同。下载此检查点整个目录（包括全部archive/parts），在该目录运行：

```sh
python3 restore_workbuddy.py join .
python3 restore_workbuddy.py verify WORKBUDDY_PREFIX60_WITH_POLICY_FAILURE.zip
python3 restore_workbuddy.py extract WORKBUDDY_PREFIX60_WITH_POLICY_FAILURE.zip /新的空目录
```

分卷索引见 [archive/MANIFEST.json](archive/MANIFEST.json)。这是去重分块ZIP，使用配套还原程序才能重建原目录。还原程序只还原文件，不运行归档代码。原uid/gid保存在元数据中，实际属主为执行还原的当前用户。

归档内 `workbuddy-codex-20261118/` 包括所有正式与试跑的API原始输入/输出、原生会话、工具、上下文编辑、任务产物、官方评分、评分更正层、检查点、各版本源码与管理失败。`CURRENT_SNAPSHOT_LEDGER_01/all-provider-attempts.json` 和 `all-task-attempts.json` 在ZIP内保存完整逐请求/逐trial索引；这里的可浏览文件仅是索引和说明，不替代原始轨迹。

全部物理HTTP去重1588次，1529次用量已知、59次未知；145个实际trial目录和505个CLM投影核验通过。第61题拒绝计1次，用量未知、reward=null；未启动槽位不记为模型失败。

本次发布是可续接的阶段检查点。完整65题的生产报告、最终轨迹归档与固定子任务完成审核仍待完成，最终生产验收门槛未修改。
