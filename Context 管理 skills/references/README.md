# 可复查索引

CASE_LOCATORS.json含502个执行目录（含重试），不是502个独立任务。CONTEXT_EVENT_LOCATORS.json含机器收集的722条定位记录，覆盖不同事件类型及原始/请求级记录，**不是722次独立编辑**；accepted次数必须按运行分组去重核验。索引保留source、事件位置/类型，不复制任务答案和完整请求。

将原仓库对应归档解包到任意位置，以group前缀映射：claude_native为根grouped/shuffled归档；claude_clm为Claude CLM归档；codex_native与codex_clm分别是Codex两tar。索引source相对于恢复根；部分source附case/context-events或runs/wire。用原始事件与前后响应复查EVIDENCE中的推断。

本索引只证明可定位，不能替代逐条语义审阅。严格覆盖边界见上级EVIDENCE。技能运行时不需要加载这些研究索引。
