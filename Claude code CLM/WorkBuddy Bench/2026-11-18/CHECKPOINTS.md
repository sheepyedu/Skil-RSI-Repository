# 正式运行复核

首次稳定验收完成于北京时间 2026-11-18 21:48:46。以下是验收后的人工复核记录。

## 2026-11-18 22:49

控制器接收了 5 道配对，第 6 题原生组也完成评分。第 5 题两组作答 29／47 次调用全部闭合，官方记录得分 0.8／0.5。CLM 的 8 个 LLM/VLM 评分项中有 1 项，`risk_level_derivation`，同请求连续 5 次返回流内上游错误。官方评分器把这项按空结果判负，保留其原始 0.5 并标为受评分服务异常影响。第 4 题 CLM 已单列人工干预。

第 6 题原生组 35 次作答全部闭合，得分 0.25。原运行停止在第 6 题 CLM 的开题前维护。第三次恢复保留全部旧会话、模型响应和评分，沿用 11 条已完成试验，验证历史推理归档后从第 6 题 CLM 继续。

[小时复核快照](evidence/hourly/2026-11-18-2249.json) · [第 5、6 题已观测的输入输出](evidence/hourly/2026-11-18-2249-input-output.json) · [评分异常](evidence/task-005-judge-degradation.json) · [第三次恢复复验](evidence/formal-02-recovery-03-probe.json)

## 2026-11-18 23:14 补评复核

第 5 题缺失的评分项已收到完整回复并通过。对照按同模型的补评将 CLM 得分从 0.5 修正为 0.8。第 6 题已完成配对，第 7 题在修复题间笔记长度后继续。 [补评记录](REGRADING.md) · [修正后配对快照](analysis/post-regrade-checkpoint.json)

## 2026-11-18 23:49

控制器仍在运行，已完成 9/60 对和 19/120 条单组试验。第 10 题原生组得分 1.0，13 次作答及 14 次外部评分响应均闭合。CLM 组 17 次作答完成，当时正在评分。复核时第 10 题 CLM 有 12 次完整评分响应和 4 次评分流错误，最终评分仍待闭合。

23:45 的请求核对记录 555 次作答、108 次外部评分和 5 次独立维护请求，正式运行合计 668 次。第 5 题补评另发 5 次，计入后为 673 次。按已观察吞吐粗估剩余 9–13 小时，后续评分时延和恢复会影响时间。

[小时复核快照](evidence/hourly/2026-11-18-2349.json) · [第 6 至 10 题已观测输入输出](evidence/hourly/2026-11-18-2349-input-output.json) · [应用第 5 题修正的已完成配对](analysis/hourly-2026-11-18-2349-scores.json)

23:51 已完成第 10 道配对。CLM 组的 4 次评分流中断涉及 3 个原请求，官方同请求重试后 14 个评分项均闭合，两组得分均为 1.0。第 11 题已开始。 [重试回执](evidence/task-010-judge-retries.json) · [前十题有效比分](analysis/through-010-scores.json)

## 2026-11-19 00:19

持续目标启用后开始每半小时复核。此次检查确认控制器正常，12/60 道配对已完成，第 13 题原生组运行中。正式请求 752 次，其中作答 608 次、评分 138 次、题间维护 6 次。计入补评 5 次后为 757 次。

第 12 题原生组的 3 个评分请求和 CLM 组的 1 个评分请求出现中断，均由官方重试闭合，两组各 10 个评分项均有有效结果。已完成任务中，影响评分的上游异常只有第 5 题，已补评并应用修正。 [进度](evidence/hourly/2026-11-19-0019.json) · [请求计数](evidence/hourly/2026-11-19-0019-request-counts.json) · [评分健康](evidence/hourly/2026-11-19-0019-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0019-input-output.json) · [应用修正后的比分](analysis/hourly-2026-11-19-0019-scores.json)

## 2026-11-19 00:49

完成 14/60 道配对，第 15 题启动。正式请求 817 次，补评 5 次，合计 822 次。正式作答请求 672 次，其中 670 次已闭合、1 次仍在途、1 次为第 13 题原生组已知读超时。该组原始轨迹保留 205,995 字节响应前缀，CLI 终态正常，提交产物通过 4/4 项官方测试，得分 1.0。评分审计未发现新增待补评项目。 [复核快照](evidence/hourly/2026-11-19-0049.json) · [逐请求核验](evidence/hourly/2026-11-19-0049-input-output.json) · [计数](evidence/hourly/2026-11-19-0049-request-counts.json) · [评分](evidence/hourly/2026-11-19-0049-web-judge-health.json) · [第 13 题传输记录](evidence/task-013-native-transport.json) · [修正汇总](analysis/hourly-2026-11-19-0049-scores.json)

第 15 题原生组因 8,192 token 单次输出预算退出，CLM 原试验完成评分。两组均从第 14 题各自检查点续接，使用同一 16,384 token 上限重跑第 15 题，原尝试保留。原生组恢复首个实际模型请求已闭合，确认 16,384 token 和上一题标记。 [原尝试](evidence/task-015-original-output-cap.json) · [恢复启动](evidence/formal-02-recovery-05-launch.json) · [恢复首请求](evidence/task-015-first-recovery-request.json)

## 2026-11-19 01:19

控制器在新恢复目录正常运行。已完成 14/60 道配对，第 15 题原生重跑的 16 次作答均闭合，得分 0.809，CLM 重跑在途。两组真实作答首请求均使用 16,384 token 输出上限，含前一题标记，响应正常。历史额外分段保留原第 15 题评分和失败尝试。

正式请求 875 次，含原第 15 题两组尝试。另有补评 5 次，两项合计 880 次。预算参数探针额外发送 1 次。已完成的 Web 评分无待补评项。 [运行快照](evidence/hourly/2026-11-19-0119.json) · [逐请求核验](evidence/hourly/2026-11-19-0119-input-output.json) · [计数](evidence/hourly/2026-11-19-0119-request-counts.json) · [评分](evidence/hourly/2026-11-19-0119-web-judge-health.json) · [实际配对预算](evidence/task-015-matched-budget.json) · [修正汇总](analysis/hourly-2026-11-19-0119-scores.json)

01:22 第 15 题恢复后配对验收，两组各自沿用原会话，实际作答上限均为 16,384，16/20 次请求全部闭合。官方得分 0.809/0.8876。01:25 已完成 16 道配对，第 17 题启动。 [第 15 题恢复验收](evidence/task-015-recovered-pair.json) · [前 16 题比分](analysis/through-016-scores.json)

## 2026-11-19 01:49

完成 17/60 道配对。第 18 题原生组得分 1.0，21 次作答均闭合，CLM 组在途。正式请求 978 次，另有 5 次补评，合计 983 次。最新评分审计中，仍无待补评的已完成任务。第 17 题原生组介入已标记，官方评分保留。 [进度](evidence/hourly/2026-11-19-0149.json) · [请求计数](evidence/hourly/2026-11-19-0149-request-counts.json) · [评分健康](evidence/hourly/2026-11-19-0149-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0149-input-output.json) · [比分](analysis/hourly-2026-11-19-0149-scores.json)

## 2026-11-19 02:19

完成 19/60 道配对。第 20 题原生组得分 0.8269，47 次作答全部闭合，CLM 组题间维护已验收并正在运行。正式请求 1,119 次，补评 5 次，合计 1,124 次。已完成题目无新增待补评项。第 18 题 CLM 后台搜索处理已保留原轨迹和官方得分 1.0。 [进度](evidence/hourly/2026-11-19-0219.json) · [计数](evidence/hourly/2026-11-19-0219-request-counts.json) · [评分](evidence/hourly/2026-11-19-0219-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0219-input-output.json) · [比分](analysis/hourly-2026-11-19-0219-scores.json)

## 2026-11-19 02:49

完成 24/60 道配对，过去半小时新增 5 道，第 25 题正在运行。正式请求 1,289 次，其中作答 1,140 次、评分 138 次、题间维护 11 次，另有补评 5 次。有 1 次作答请求在途，已知作答读取超时仍为第 13 题的一次。已完成 Web 评分无新增缺口。 [进度](evidence/hourly/2026-11-19-0249.json) · [计数](evidence/hourly/2026-11-19-0249-request-counts.json) · [评分](evidence/hourly/2026-11-19-0249-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0249-input-output.json) · [比分](analysis/hourly-2026-11-19-0249-scores.json)

## 2026-11-19 03:19

完成 26/60 道配对，第 27 题启动。正式请求 1,481 次，补评 5 次，合计 1,486 次。第 25 题两组各 7 个 Web 评分项均闭合，未出现新增评分缺口。第 26 题两组已完成官方评分，会话与冻结题序连续。 [进度](evidence/hourly/2026-11-19-0319.json) · [计数](evidence/hourly/2026-11-19-0319-request-counts.json) · [评分](evidence/hourly/2026-11-19-0319-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0319-input-output.json) · [比分](analysis/hourly-2026-11-19-0319-scores.json)

## 2026-11-19 03:49

完成 26/60 道配对。第 27 题原生组在初始成功终态后清理后台搜索，随后 2 次实际发往 DeepSeek 的请求在响应前超时，CLI 最终退出，原工作区快照已保存。CLM 组维护请求也在响应前超时，控制器停止发题。单独发出的最小同模型检查同样在响应前超时。评分审计对已完成题目无新增待补评项。

实际向模型发送的正式请求为 1,500 次，另有补评 5 次。第 27 题还有 9 个本地重试意图被请求网关拦住，留档备查。 [进度](evidence/hourly/2026-11-19-0349.json) · [计数](evidence/hourly/2026-11-19-0349-request-counts.json) · [评分](evidence/hourly/2026-11-19-0349-web-judge-health.json) · [逐请求核验](evidence/hourly/2026-11-19-0349-input-output.json) · [故障诊断](evidence/task-027-transport-stop.json) · [产物校验](evidence/task-027-native-staged-output.json)

## 2026-11-19 04:19

恢复批次已核对 52 条逐字节一致的验收记录、两组第 26 题会话与同一冻结题单。第 27 题等待原模型恢复，第四次最小请求到 04:15 仍以零响应字节超时。26/60 道配对，实际正式及补评仍合计 1,505 次，四次诊断请求另计。已完成任务无待补评项。 [准备验收](evidence/formal-02-recovery-06-staged.json) · [第四次服务探针](evidence/provider-health-0414.json) · [进度](evidence/hourly/2026-11-19-0419.json) · [计数](evidence/hourly/2026-11-19-0419-request-counts.json) · [评分](evidence/hourly/2026-11-19-0419-web-judge-health.json)

## 2026-11-19 04:49

26/60 道配对。第 27 题两组仍等待同模型健康回执。04:37 探针超时，04:48 探针返回客户端网络异常 `URLError`，两次均无响应字节。正式加补评仍为 1,505 次。已完成任务的评分没有新增缺口。 [进度](evidence/hourly/2026-11-19-0449.json) · [计数](evidence/hourly/2026-11-19-0449-request-counts.json) · [评分](evidence/hourly/2026-11-19-0449-web-judge-health.json) · [04:37 探针](evidence/provider-health-0437.json) · [04:48 探针](evidence/provider-health-0448.json)

## 2026-11-19 05:19

26/60 道配对。恢复目录仍保有原题单、52 条验收回执和两组会话检查点。原入口 05:18 探针在 45 秒后返回 `URLError` 与零响应字节，配置仍沿用原部署。独立 SSH 回环和绑定 Wi-Fi 诊断均未取得应用响应，临时转发已关闭。正式加补评仍为 1,505 次。 [进度](evidence/hourly/2026-11-19-0519.json) · [计数](evidence/hourly/2026-11-19-0519-request-counts.json) · [评分](evidence/hourly/2026-11-19-0519-web-judge-health.json) · [最新健康探针](evidence/provider-health-0518.json) · [路径诊断](INCIDENTS.md)

## 2026-11-19 05:49

26/60 道配对，第 27 题待发。05:48 的同模型请求仍以 `URLError` 结束，零响应字节。已验收 Web 评分无待补评项，正式加补评保持 1,505 次。 [进度](evidence/hourly/2026-11-19-0549.json) · [计数](evidence/hourly/2026-11-19-0549-request-counts.json) · [评分](evidence/hourly/2026-11-19-0549-web-judge-health.json) · [健康探针](evidence/provider-health-0548.json)

## 2026-11-19 06:19

26/60 道配对，第 27 题恢复待发。06:18 原入口请求结果为 `URLError`、零响应字节。06:20 从另一已核实的服务器只读测试同一原服务端口，TCP 也超时。正式加补评保持 1,505 次。 [进度](evidence/hourly/2026-11-19-0619.json) · [计数](evidence/hourly/2026-11-19-0619-request-counts.json) · [评分](evidence/hourly/2026-11-19-0619-web-judge-health.json) · [健康探针](evidence/provider-health-0618.json) · [额外网络路径](evidence/provider-transport-node01-0620.json)

## 2026-11-19 06:49

26/60 道配对。第 27 题仍待已验证的模型服务响应。06:48 原入口客户端 `URLError`，零响应字节。正式及补评请求保持 1,505 次，已结束 Web 评分无待补评。 [进度](evidence/hourly/2026-11-19-0649.json) · [计数](evidence/hourly/2026-11-19-0649-request-counts.json) · [评分](evidence/hourly/2026-11-19-0649-web-judge-health.json) · [健康探针](evidence/provider-health-0648.json)

## 2026-11-19 07:19

26/60 道配对，1,505 次正式及补评请求。07:18 原入口仍为 `URLError`、零响应字节。第 27 题恢复目录继续待命。 [进度](evidence/hourly/2026-11-19-0719.json) · [计数](evidence/hourly/2026-11-19-0719-request-counts.json) · [评分](evidence/hourly/2026-11-19-0719-web-judge-health.json) · [健康探针](evidence/provider-health-0718.json)

## 2026-11-19 07:49

07:50 核对仍为 26/60 道配对，正式及补评 1,505 次。原入口最近的请求未收到响应字节，临界位置为第 27 题。 [进度](evidence/hourly/2026-11-19-0749.json) · [计数](evidence/hourly/2026-11-19-0749-request-counts.json) · [评分](evidence/hourly/2026-11-19-0749-web-judge-health.json) · [健康探针](evidence/provider-health-0748.json)

## 2026-11-19 08:19

08:20 核对完成 26/60 道配对，余 34 道。正式 1,500 次，加补评 1,505 次。08:18 原入口最小生成请求在 45 秒后出现 `URLError`，响应为零字节。第 27 题恢复入口仍绑定原模型，52 条已验收记录已完成复制与验收。已完成 Web 评分无待补评。 [进度](evidence/hourly/2026-11-19-0819.json) · [计数](evidence/hourly/2026-11-19-0819-request-counts.json) · [评分](evidence/hourly/2026-11-19-0819-web-judge-health.json) · [健康探针](evidence/provider-health-0818.json)

## 2026-11-19 11:57 北京时间 · 恢复后第 27 题通过

- 已验收 27/60 道配对。第 27 题两组沿用冻结模型、原会话和 16,384 token 共同输出预算，原生得 0.8462，CLM 得 0.7692。各核对原题面、上一题标记、模型响应和正式评分。第 28 题原生组已启动。 [配对验收](evidence/task-027-recovered-pair.json) · [控制器快照](evidence/hourly/2026-11-19-1157.json)
- 累计正式上游请求 1,569 次，另有补评 5 次。12 条已完成的 Web 评分线次没有待补评的上游错误。 [请求计数](evidence/hourly/2026-11-19-1157-request-counts.json) · [评分审计](evidence/hourly/2026-11-19-1157-web-judge-health.json)

## 2026-11-19 12:12 北京时间 · 定时复核

- 已验收 28/60 道配对。第 28 题双组均为 0.6，真实输入、上一题标记和原会话校验通过，原生 53 次与 CLM 24 次模型回复闭合。第 29 题原生组已启动，核验到已闭合的真实请求与响应。 [快照](evidence/hourly/2026-11-19-1212.json) · [输入输出验收](evidence/hourly/2026-11-19-1212-input-output.json)
- 正式请求 1,653 次，补评 5 次，现有 Web 评分没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1212-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1212-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1212-scores.json)

## 2026-11-19 12:42 北京时间 · 定时复核

- 已验收 29/60 道配对。第 29 题两组均为 0.2727，原生 60 次、CLM 46 次模型回复闭合，上一题标记、官方输入和原会话匹配。第 30 题原生组已取得真实回复。 [快照](evidence/hourly/2026-11-19-1242.json) · [输入输出验收](evidence/hourly/2026-11-19-1242-input-output.json)
- 正式请求 1,782 次，补评 5 次。12 条已完成的 Web 评分线次无待补评异常。 [请求计数](evidence/hourly/2026-11-19-1242-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1242-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1242-scores.json)

## 2026-11-19 13:12 北京时间 · 定时复核

- 已验收 32/60 道配对。第 30–32 题的两组官方输入、上一题标记、原会话和输出已核验，第 33 题原生组已取得真实回复。 [快照](evidence/hourly/2026-11-19-1312.json) · [输入输出验收](evidence/hourly/2026-11-19-1312-input-output.json)
- 正式请求 1,935 次，补评 5 次。第 30 题双组得分均为 0.0，两组各 10 次 Web 评分请求全部闭合。14 条已完成的 Web 评分线次无待补评异常。 [请求计数](evidence/hourly/2026-11-19-1312-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1312-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1312-scores.json)

## 2026-11-19 13:42 北京时间 · 定时复核

- 已验收 34/60 道配对。第 34 题的 CLM 组以原会话续跑，真实输入含原题面和上一题标记，首个回复已闭合。两组该题的官方得分均为 0.0。第 35 题已启动。 [快照](evidence/hourly/2026-11-19-1342.json) · [输入输出验收](evidence/hourly/2026-11-19-1342-input-output.json) · [第 34 题续跑](evidence/task-034-resumed-clm-input.json)
- 正式请求 2,013 次，补评 5 次。14 条已完成的 Web 评分线次无待补评异常。 [请求计数](evidence/hourly/2026-11-19-1342-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1342-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1342-scores.json)

## 2026-11-19 14:12 北京时间 · 定时复核

- 已验收 35/60 道配对。第 35 题双组均为 0.8，原生和 CLM 分别有 20、22 次完整作答回复，同题 32 次 Web 评分全部闭合。第 36 题原生已验收，CLM 已收到真实模型回复。 [快照](evidence/hourly/2026-11-19-1412.json) · [输入输出验收](evidence/hourly/2026-11-19-1412-input-output.json)
- 正式请求 2,203 次，补评 5 次。16 条已完成的 Web 评分线次没有待补评异常。 [请求计数](evidence/hourly/2026-11-19-1412-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1412-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1412-scores.json)

## 2026-11-19 14:42 北京时间 · 定时复核

- 已验收 37/60 道配对。第 36、37 题两组均通过题面、上题标记、原会话与模型回复核查，得分分别为双组 0.0、双组 1.0。第 38 题原生已验收，CLM 正在执行。 [快照](evidence/hourly/2026-11-19-1442.json) · [输入输出验收](evidence/hourly/2026-11-19-1442-input-output.json)
- 正式请求 2,372 次，补评 5 次。17 条已完成的 Web 评分线次没有待补评异常。 [请求计数](evidence/hourly/2026-11-19-1442-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1442-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1442-scores.json)

## 2026-11-19 15:12 北京时间 · 定时复核

- 已验收 38/60 道配对。第 38 题原生得 0.5、CLM 得 0.2，两组真实输入、原会话和回复均通过验收。第 39 题原生已验收，CLM 正在执行。 [快照](evidence/hourly/2026-11-19-1512.json) · [输入输出验收](evidence/hourly/2026-11-19-1512-input-output.json)
- 正式请求 2,460 次，补评 5 次。19 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1512-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1512-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1512-scores.json)

## 2026-11-19 16:12 北京时间 · 定时复核

- 已验收 41/60 道配对。第 39–41 题两组均通过题面、上题标记、原会话和输出核查。第 42 题原生的首个真实输入与回复通过核验，CLM 随后串行执行。 [快照](evidence/hourly/2026-11-19-1612.json) · [输入输出验收](evidence/hourly/2026-11-19-1612-input-output.json)
- 正式请求 2,716 次，补评 5 次。22 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1612-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1612-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1612-scores.json)

## 2026-11-19 16:42 北京时间 · 定时复核

- 已验收 43/60 道配对。第 42、43 题两组均通过题面、原会话及响应核查。第 44 题原生组已取得真实回复。 [快照](evidence/hourly/2026-11-19-1642.json) · [输入输出验收](evidence/hourly/2026-11-19-1642-input-output.json)
- 正式请求 2,834 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1642-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1642-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1642-scores.json)

## 2026-11-19 17:12 北京时间 · 定时复核

- 已验收 44/60 道配对。第 44 题原生得 0.2275、CLM 得 0.3588，两组原会话与真实输入输出通过验收。第 45 题原生组已验收，CLM 正在执行。 [快照](evidence/hourly/2026-11-19-1712.json) · [输入输出验收](evidence/hourly/2026-11-19-1712-input-output.json)
- 正式请求 3,001 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1712-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1712-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1712-scores.json)

## 2026-11-19 17:42 北京时间 · 定时复核

- 已验收 45/60 道配对。第 45 题原生得 0.6923、CLM 得 0.6154，两组真实输入和原会话通过验收。第 46 题仍在原生组运行。 [快照](evidence/hourly/2026-11-19-1742.json) · [输入输出验收](evidence/hourly/2026-11-19-1742-input-output.json)
- 正式请求 3,125 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1742-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1742-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1742-scores.json)

## 2026-11-19 18:12 北京时间 · 定时复核

- 已验收 47/60 道配对。第 46 题原生得 0.6175、CLM 得 0.8725。第 47 题双组均为 1.0。两题均通过真实输入、上题标记、原会话及响应核查，第 48 题原生组已取得实际模型回复。 [快照](evidence/hourly/2026-11-19-1812.json) · [输入输出验收](evidence/hourly/2026-11-19-1812-input-output.json)
- 正式请求 3,278 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1812-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1812-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1812-scores.json)

## 2026-11-19 18:42 北京时间 · 定时复核

- 已验收 47/60 道配对。第 48 题原生沿用已验收的 0.8532。CLM 原试验因 CLI 容量停止，新维护在 47 道历史题面完整的原会话上完成，CLM 已重跑并取得真实回复。 [快照](evidence/hourly/2026-11-19-1842.json) · [输入输出验收](evidence/hourly/2026-11-19-1842-input-output.json)
- 正式请求 3,355 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1842-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1842-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1842-scores.json)

## 2026-11-19 19:12 北京时间 · 定时复核

- 已验收 49/60 道配对。第 49 题原生为 0.0、CLM 为 0.8582，两组原会话、真实输入和闭合响应通过验收。第 50 题原生已取得响应，正在继续。 [快照](evidence/hourly/2026-11-19-1912.json) · [输入输出验收](evidence/hourly/2026-11-19-1912-input-output.json)
- 正式请求 3,585 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1912-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1912-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1912-scores.json)

## 2026-11-19 19:42 北京时间 · 定时复核

- 已验收 50/60 道配对。第 50 题双组各得 1.0。清理残留搜索后的追加作答全部闭合，两组原会话及官方评分通过校验。第 51 题原生已继续取得真实回复。 [快照](evidence/hourly/2026-11-19-1942.json) · [输入输出验收](evidence/hourly/2026-11-19-1942-input-output.json)
- 正式请求 3,778 次，补评 5 次。26 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-1942-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-1942-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-1942-scores.json)

## 2026-11-19 20:12 北京时间 · 定时复核

- 已验收 53/60 道配对。第 51–53 题两组均通过题面、会话与响应核查。CLM 三题各仅有一次完整回复且工具调用数为零，保留官方原分。第 54 题已取得真实回复。 [快照](evidence/hourly/2026-11-19-2012.json) · [输入输出验收](evidence/hourly/2026-11-19-2012-input-output.json)
- 正式请求 3,922 次，补评 5 次。32 条已有正式回执的 Web 线次没有待补评的上游异常。 [请求计数](evidence/hourly/2026-11-19-2012-request-counts.json) · [Web 评分](evidence/hourly/2026-11-19-2012-web-judge-health.json) · [有效评分快照](analysis/hourly-2026-11-19-2012-scores.json)
