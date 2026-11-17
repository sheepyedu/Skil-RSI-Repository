# CL-Bench 单会话评测

本目录保存实际使用的 Codex app-server 驱动、记录型网关和终局审计。冻结题序见 [PLAN.json](../results/PLAN.json)，数据与评价口径见 [评测说明](../results/RESULT_FORMAT.md)。

在 H20 的独立实验目录中，复制 `source/` 的源码并按 [运行说明](../source/README.md) 准备固定 Codex 二进制。把本目录的四个脚本复制到该实验目录顶层，用这里的 `clm/gateway.py` 覆盖实验副本的同名文件，再放入 `results/PLAN.json`。原运行复用 H20 上 Claude Code CLM 实验的 `framework/`（包含 `skillrl.clbench` 和 `skillrl.interactive`），从 `/mount-data/Claude-code-CLM/experiments/clbench100-20261117/framework` 复制到实验目录。官方数据路径为 `/mount-data/Datasets/continual-learning-bench/repository`。

```sh
./run-h20 --probe
./run-h20
python3 observe.py
python3 audit_final.py
```

`--probe` 只启动原生 app-server 并验证协议接线。正式运行逐题评分，保留同一线程的历史和工作区，并拒绝在已有 `LAUNCH.json` 的目录重复启动。
