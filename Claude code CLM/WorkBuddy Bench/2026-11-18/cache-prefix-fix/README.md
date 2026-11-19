# WorkBuddy Bench DeepSeek 前缀缓存修复

Claude Code 每次请求都会把包含动态 `cch` 的 `x-anthropic-billing-header` 行放在系统提示开头。原 WorkBuddy 转换器将这行作为模型文本发给 DeepSeek，使连续请求很早就失去相同的 token 前缀。

H20 已部署独立运行目录 `/mount-data/Claude-code-CLM/experiments/workbuddy-20261118/serial-cache-prefix`。原生组和 CLM 组从同一个私有 DeepSeek 转换器载入修复。转换器仅处理顶层 `system` 字符串或首个文本块开头、符合本版 Claude 元数据格式的账单行。原始 Messages 请求仍按原样留存。普通提示词、用户文本、工具 schema、模型设置和 CLM 编辑流程按原路径处理。CL-Bench 共用转换器仍从原目录加载。

审计脚本同时读取 DeepSeek 的 `prompt_tokens_details.cached_tokens` 和旧的显式命中与未命中字段。在有输入 token 总数但无法确认缓存状态时，单独记录未知输入 token。以下数字来自上游使用量回执。

| 线路 | 请求 | 输入 token | 命中 | 未命中 | 输出 token |
| --- | --- | ---: | ---: | ---: | ---: |
| 原生 | 第一轮 | 4,705 | 0 | 4,705 | 14 |
| 原生 | 第二轮 | 4,705 | 4,608 | 97 | 14 |
| CLM | 第一轮 | 4,715 | 0 | 4,715 | 14 |
| CLM | 第二轮 | 4,715 | 4,608 | 107 | 12 |

真实 DeepSeek V4.1 Flash 模型 `deepseek-v4-1-flash-261017` 返回 4 次 HTTP 200 和完整流终态。每组使用自己的合成系统前缀，第二轮更换 `cch` 和末尾用户问题。探针通过 WorkBuddy 的 Unix socket、Wire 和真实 ChatMessagesGateway。CLM 组启用了 Context 投影，本用例未提交记忆编辑。第二轮命中率分别为 97.94% 和 97.73%。两次探针脚本接线错误分别发生在 Unix socket 参数类型和测试脚本缺少 Wire 超时配置，均在发送 DeepSeek 请求前终止，残留证据与成功探针一并留档。

正式 60 对试验已封存。读回每条已验收线次最多前 11 份请求，共 1,228 份，逐对象对照历史出站 Chat JSON 与新转换结果。全部请求的差异仅为移除账单行。相邻 1,108 对请求的系统文本由 0 对相同恢复为 1,100 对相同，剩余 8 对原生请求还有实际系统指令差异。离线核对记录了九条既有适配器对 `document` 块的警告，对应出站内容仍逐项相符。历史比较只在 H20 本地读取。该抽样覆盖输入一致性，命中率仍以未来实际请求的上游回执为准。

CLM 编辑或原生压缩改变较早的上下文时，DeepSeek 可复用的前缀会相应变化。此次未重新运行正式 60 题，原始轨迹、用量和评分采用原提交。探针不能估计新一轮正式任务的总体缓存率、成本或分数差异。 [原正式版本](https://github.com/sheepyedu/Skil-RSI-Repository/commit/4e9a0351fc2b036eced4774e82e2b9625e031dec) · [DeepSeek 缓存文档](https://api-docs.deepseek.com/guides/kv_cache)

## 运行与复现

后续的新 WorkBuddy 批次通过新目录的 `deploy-env.sh` 启动同目录的 `run_pair.py`，传入新批次的 `--run` 路径及已约定的试跑、题单和正式参数。`deploy-env.sh` 将本目录置于 Python 模块搜索路径首位。

```bash
work=/mount-data/Claude-code-CLM/experiments/workbuddy-20261118
runner="$work/serial-cache-prefix"
"$runner/deploy-env.sh" "$runner/run_pair.py" --help
"$runner/deploy-env.sh" "$runner/smoke_cache.py"
"$runner/deploy-env.sh" "$runner/audit_history.py" "$work/formal-02-resume-09"
# 真实探针，发送四次合成请求，需要一个未使用的目录
"$runner/deploy-env.sh" "$runner/smoke_cache.py" --live "$work/cache-prefix-smoke-recheck"
```

重建时从 `serial-recovery-09` 复制 Python 源码、JSON 配置和 `deploy-env.sh` 到新的独立目录。将 `clbench100-20261117/framework/skillrl` 复制到新目录，再从该目录应用 `patch --fuzz=0 -p1 < workbuddy-cache-prefix.patch`。补丁的上游转换器 SHA-256 为 `bd608e81d2be1adf38a16968a829e18936df959b726012995eebf6f5e7bb55e0`。部署后的转换器 SHA-256 为 `8bce6a7feeafd8d0b73c7411260245008b2db31030accbac99d095d177129b33`。

## 交付文件

- [转换器、运行入口与用量统计补丁](workbuddy-cache-prefix.patch)
- [探针与本地回归脚本](smoke_cache.py) · [真实用量回执](smoke-results.json)
- [离线历史输入核对脚本](audit_history.py) · [核对结果](historical-request-audit.json)
- 逐请求原始探针轨迹和 SHA-256 校验清单位于 `/mount-data/TeamShared/YangYang/rollouts/WorkBuddy-CLM-cache-prefix-fix-20261119`。
