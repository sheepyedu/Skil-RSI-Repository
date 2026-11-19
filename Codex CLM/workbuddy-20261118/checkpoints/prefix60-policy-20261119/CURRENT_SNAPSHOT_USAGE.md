# 当前快照用量（目标未完成）

来源：`CURRENT_SNAPSHOT_LEDGER_01/all-provider-usage.json`。所有原始HTTP尝试按原始时刻、请求及响应摘要去重；包含正式失败恢复、补评、试跑与容量探针。第61题拒绝计入正式原生作答尝试，其用量未知。

| 范围 | 臂 | 用途 | 尝试数 | 用量已知 | 用量未知 | 已知输入token | 已知输出token |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| auxiliary_or_unclassified | unassigned | actor_and_context | 2 | 2 | 0 | 95533 | 446 |
| formal | clm | actor_and_context | 472 | 467 | 5 | 44625286 | 270662 |
| formal | clm | judge | 258 | 250 | 8 | 4726831 | 31339 |
| formal | native | actor_and_context | 449 | 430 | 19 | 54660347 | 183931 |
| formal | native | judge | 276 | 264 | 12 | 5364302 | 32328 |
| pilot | clm | actor_and_context | 35 | 34 | 1 | 1623958 | 13820 |
| pilot | clm | judge | 8 | 8 | 0 | 156628 | 541 |
| pilot | native | actor_and_context | 37 | 37 | 0 | 1315237 | 12997 |
| pilot | native | judge | 51 | 37 | 14 | 768854 | 2491 |

合计1588次；已知1529、未知59；已报告输入113,336,976、输出548,555 token。未知不填零，缓存token按服务商输入口径保留，未提供实际货币账单。

仅比较正式作答/上下文用途（含失败恢复，不含judge）：原生449次、CLM472次；CLM已知输入较原生减少18.36%，已知输出增加47.15%。原生19次、CLM5次用量未知，因此这不是完整费用比较，也不能单独归因于CLM编辑。

65题目标尚未完成；本文件为前60对完成且第61题策略拒绝后的快照统计。完整物理请求索引和原始usage随完整轨迹保留。
