# Skill RSI · 持续上下文轨迹

Claude Code + DeepSeek 4.1 Flash API 的两条长会话。每条连续完成同一套100道 Continual Learning Bench 题目，共200题次，分别按类别排序和随机打乱。

| 指标 | 分类顺序 | 打乱顺序 |
| --- | ---: | ---: |
| 完成题数 | 100 | 100 |
| 官方达标 | 43 | 41 |
| 模型响应 | 656 | 777 |
| 原生自动上下文压缩 | 9 | 10 |
| 本地文件工具尝试 | 155 | 180 |

每条链保持同一原生会话、HOME及笔记，官方任务沙箱逐题切换。上下文窗口为200k，初始技能为空，关闭技能精炼。Claude Code触发压缩，DeepSeek生成摘要，主模型自主读写笔记。每种顺序各执行一次。

## 内容

- [完整报告](results/REPORT.md)
- [200题次结果](results/tasks.csv)、[逐请求token与token/s](results/requests.csv)、[19次压缩记录](results/compactions.csv)
- [题单与两种顺序](results/PLAN.json)、[独立审计](results/AUDIT.json)
- [完整轨迹分卷](archive/parts)，包含所有原始请求、SSE响应、API返回的thinking、原生会话、工具调用及返回、笔记版本、压缩前后快照、运行源码和环境证据。

## 获取完整轨迹

```bash
git clone https://github.com/sheepyedu/Skil-RSI-Repository.git
cd Skil-RSI-Repository
python3 restore_archive.py
unzip ROLLOUTS_200.zip -d trajectories
```

脚本逐分卷核验并合并，得到原始ZIP，共905,688,718字节、50,720个载荷文件，解压约4.07 GB。[分卷清单](archive/MANIFEST.json)包含每卷SHA256及完整包SHA256。分卷为48 MiB，适配[GitHub单文件限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)。

完整ZIP的SHA256为

```text
560fe301ba065ecb6a1e1cc63f3ecf911a51b86db0596cc66ba1f73145bf2509
```

解压后，`grouped/`与`shuffled/`保存两条链，`source-v1/`保存冻结运行源码，根目录包含结果表、题单和审计证据。

## 保留问题

一份摘要在原生CLI重组时出现两字符变化，两次响应达到32k thinking输出上限后在原会话继续。原始输出、实际后续输入、辅助计数404及管理回执缺口均已保留并在报告说明。压缩事件与文件操作分别统计，数据训练采纳需另行筛选。

采集日期为北京时间2026年11月16日至17日，模型配置及回执标识为`deepseek-v4-1-flash-261017`，Claude Code版本2.1.160。官方数据版本为`5f8c50eb1e84b2eda2ef4faff757dfc812a0ea26`，运行源码提交为`2f02798`。
