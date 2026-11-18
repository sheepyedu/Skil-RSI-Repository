# 证据、范围与结论等级

## 数据单位与覆盖
源仓库快照：`13a6306eb7ec47f44fd6cd88c08b0d25017c2f88`。原始生成阶段只新增技能和审阅产物，不改轨迹或旧技能。本次双语整理迁移文档，不修改原始轨迹。

五条长序列合计500个正式评分执行，覆盖相同100个任务；不是500个独立题。恢复目录有502个case（含重试），不得与正式执行数混淆。原生Claude grouped/shuffled各100；Claude CLM100；原生Codex100；Codex CLM100。归档字节/哈希校验覆盖所有恢复文件。

- Claude原生：逐题notes差分、全部335个文件调用/返回和19次自动压缩的状态段；200/200 notes写入重放与快照一致。并非逐字审阅全部thinking或重复大输出。
- Claude CLM：101个case结果、66个文件差分、全部40次accepted edit的原始/投影差异、前后响应，重点回读异常链。维护失败另按request审阅。未逐字审阅680次重复历史或每个thinking token。
- Codex原生：100题行动、完成反馈，64个记忆commandExecution，所有谱图更新/SQL和2次compaction；不重复阅读所有SSE字节。
- Codex CLM：前50题语义证据及全部19次编辑；后50题逐题可见行动、工具结果、记忆与4次编辑，销售生成逻辑已读，未逐数字审计每题75行输出。三例配对按result的turn ID，不能按native turn序号直接对齐。

本轮是模型辅助语义审阅加程序索引，并非人工审计或新的因果实验。

## 复查方法
原始档案位于仓库原路径：根目录split ZIP的grouped/shuffled；`Claude code CLM/archive/CLAUDE_CODE_CLM_ROLLOUTS.tar.zst`；`Codex CLM/trajectories/{NATIVE_CODEX_ROLLOUTS,CODEX_CLM_ROLLOUTS}.tar.zst`。解包后按 references 下索引的source路径定位。case级Claude行号是该case `native/native-cli.jsonl`；Codex是归档根 `native.jsonl`。下述定位不携带评测答案。

## Claude Code
|事件|来源定位|可支持的发现|不能推出|
|---|---|---|---|
|CC-N1|grouped051 L10941/10947；shuffled094 L573|摘要待办可能落后于保留尾段，恢复需联合核对|压缩使答案错误|
|CC-N2|grouped040 L13916/14066/14094；shuffled087 L9307/9321/9327/17263/17320/17322|未读状态/锚点错误可由Read后正确Edit恢复|磁盘文件消失|
|CC-N3|shuffled045 L1166；047 L273；056 L191/193/195|固定行号定位不可靠；语义定位链可用|事后错误读取导致此前失败|
|CC-N4|grouped001–030；013 L2270|首30题无compact仍失败，假设被过早固化|失败主要来自压缩|
|CC-N5|shuffled039 L1036与045 L1168；grouped046/050/051/052|实体归属及schema/单位需要作用域|每次污染必然掉分|
|CC-N6|shuffled036、057；grouped099/100|反馈确有修订，但口径与因果需区分|跨题分数等于消融|
|CC-N7|两序列任务末notes全量|最终字符数115603/132002；0次任务末总量净缩短|内部每次Edit都仅追加|

## Claude Code CLM
|事件|来源定位|可支持的发现|不能推出|
|---|---|---|---|
|CCLM-E1|memory-mcp/chain/upstream/0014 response、0015 edit/raw/clm、0018/0019 response；case043|先prune后笔记导致“已查询”被误记为“未查询”，错误数据来源持久化|本题分数损害：提交已发生；无后续同族测试|
|CCLM-E2|case075、086、096|写验证提示后仍提前叙述完成；q86无prune仍复发|每次是剪枝引起|
|CCLM-E3|case097–100 notes及result|即时Composite与官方actual_performance口径不同，末尾强规则无后验验证|flat优于growth的一般规律|
|CCLM-E4|case039/041/043、048/054、067/072、079/081|旧说法留存、反例出现，需显式supersedes|所有旧证据都应删除|
|CCLM-E5|case051/054/056、055；代码031–037|版本复查有成功例；代码阶段存在future git/test捷径风险|这些得分代表一般context能力|
|CCLM-E6|40次accepted edit，后期57 catalog/39 prune/37 accepted；q93/q97拒绝|catalog无语义预览；ID与参数必须校验|accepted就代表语义无损|

配置边界：原始窗口200k遇阻，rescue改262144，后期393216；后58题有输入>=120k触发memory-only维护，thinking设置亦变化。不能将这些阶段合并当成固定配置的纯自主策略。前3次accepted为早期Bash路径，后37次为MCP；此包仅把已明确的后期MCP协议写为可执行技能，早期运行先核对接口。

## Codex 原生
|事件|来源定位|可支持的发现|
|---|---|---|
|CX-N1|q97–100；q98 native L9563；q1–30|官方/app跨题重置，持久性需实际验证|
|CX-N2|归档rollout compacted L1102(q38)、L2541(q75)|摘要保留活动状态，合法续跑不等于评分成功|
|CX-N3|q64 L6383、q73、q78、q88|按实体调用会话证据，没写磁盘不等于没学习|
|CX-N4|q8 L656、q18 L1474、q24–30|观测与关联假设需分层；渐进读取可观察，收益未隔离|
|CX-N5|q49 L5056/5165、q53 L5437/5443|聚合与分母错误不能直接归因遗忘|
|CX-N6|q46、q51、q53–55、q98–100|新版本与新观察可修订先验|

## Codex CLM
|事件|来源定位|可支持的发现|
|---|---|---|
|CX-C1|q39 L4318/4323/4333；q43 L5315/5320/5336/5419/5426|接受编辑后读回精确证据形成闭环|
|CX-C2|q10 L869、q16 L1427、q21 L1840；q23–30|字符串替换/正则提数/数组位置更新提示结构化需求|
|CX-C3|q8、q17、q18、q26|冲突保留但未充分复查；临界分数差不可称压缩损害|
|CX-C4|q44–50；q53 exec-e1fc37ad-5eaf-43ad-a8b3-1396866147ad|旧表名误用后纠正；原生同题错在聚合粒度，不是CLM记schema更好|
|CX-C5|q52 exec-19bc89d9-1aa6-47af-9bc4-e614d14dcb40；q74 exec-20acdfcc-3f96-4938-b6a2-8e29f57530c7；q93 exec-632628f5-c321-4ff1-979a-bc6ba4f5b490；q99 exec-0848339b-036e-40af-b332-287491061835|四次后半编辑accepted，note实际存在；q52/q99有文件回读，q74后有摘要证据使用|
|CX-C6|q97→98→99；q99 note|临时环境持久性错误获纠正，但旧错仍留；Current93陈旧状态未清理|
|CX-C7|q62→73/75、q64/78/87、q100|反馈后策略修订、实体隔离和新观察替代猜测；不证明因果收益|

实现约束由 `Codex CLM/source/clm/{context.py,edit.py,container_entry.py}` 等核对：note完整替换且限8192 UTF-8 bytes；省略才保留；drop非空且投影严格缩小；编辑排队在下一请求应用。show不包含reasoning；最近完整工具组、user/developer受保护；anchor变化重置会话note。raw存档、磁盘文件、实际投影是三层，不能混同。没有实现论文SCR。

## 全局结果的正确读法
原生Claude grouped43、shuffled41；Claude CLM38；Codex54、Codex CLM53（每组100题）。Claude与Codex模型和运行配置不同，不能作框架因果对照。Codex同序：51共同通过、44共同失败、3原生独有、2CLM独有。输入总量约下降28.6%，未缓存输入约增加31.7%，因此不能据总输入宣称费用下降。新技能尚未运行，以上都是发现集结果。

## 逐技能证据映射

- `cc-resume-state`：CC-N1
- `cc-verify-memory-write`：CC-N2
- `cc-semantic-memory-address`：CC-N3
- `cc-evidence-hypothesis`：CC-N4
- `cc-scope-and-version`：CC-N5
- `cc-feedback-scope`：CC-N6
- `cc-active-memory-index`：CC-N7
- `cxclm-transactional-edit`：CX-C1、CX-C5
- `cxclm-structured-state`：CX-C2
- `cxclm-conflict-recheck`：CX-C3、CX-C7
- `cxclm-scoped-retrieval`：CX-C4、CX-C6、CX-C7
- `cxclm-note-lifecycle`：CX-C5、CX-C6
- `cxclm-measure-edit-effect`：CX-C3、CX-C5、CX-C7
- `ccclm-save-before-prune`：CCLM-E1、E6；q43，q93、q97。
- `ccclm-confirm-action-receipts`：CCLM-E2；q75、q86、q96。
- `ccclm-current-policy`：CCLM-E4、E5；q39/41/43、q48/54、q67/72、q79/81。
- `ccclm-metric-feedback`：CCLM-E3；q97–100。
- `ccclm-workspace-protocol`：CCLM-E5；q43、q55、q98–100。
- `ccclm-capacity-maintenance`：CCLM-E6；40次accepted；多阶段配置见 EVIDENCE。
- `cx-verify-persistence`：CX-N1；q97–100，q1–30。
- `cx-resume-checkpoint`：CX-N2；q38、q75。
- `cx-evidence-state`：CX-N4；q8、q18、q24–30。
- `cx-scoped-retrieval`：CX-N3、N6；q64、q73、q78、q88，q46/51/53–55。
- `cx-feedback-change`：CX-N5、N6；q49、q53、q98–100。
- `cx-progressive-memory-read`：CX-N4；q24–30，原生Claude语义检索反例可作跨平台假设。

## 接口补充核验
Codex `source/clm/edit.py` 的 `--drop` 为 argparse `nargs="+"`，多ID用空格分隔。Claude后期MCP的源码未在本快照提供；直接比较 memory-mcp/chain/upstream/0082→0083、0140→0141、0172→0173：下一请求首条CLM memory逐字符等于固定前缀加本次prune输入note，而非附加旧note。三组均一致，支持传值完整替换；省略保留旧note另由工具描述确认。此处是实际投影核验，不冒称源码核验。
