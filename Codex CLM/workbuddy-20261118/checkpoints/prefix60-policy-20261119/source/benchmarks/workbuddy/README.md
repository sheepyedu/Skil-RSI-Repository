# WorkBuddy Bench 串行 Codex 对照

两臂均使用 Codex CLI 0.169.0、GPT‑6.1‑sol 和 low 推理强度。两臂按照同一题单依次运行。每题在新的官方 WorkBuddy 工作区中启动原生 app-server，首题创建线程，后续以原 thread ID 调用 thread/resume。两臂各自使用独立 CODEX_HOME、笔记、服务套接字和容器名。CLM 臂提供 clm-context 工具及其说明。

## 数据与阶段

使用 Tencent WorkBuddy Bench v1.0，官方评测框架固定在 625b2233093ae4f23e76be28c1f341d41cc70373，数据修订为 3e8ad839685c589d83a1dd60fe2d15eabb75f27a。取自同服务器的 Claude Code WorkBuddy 参考实验，保留该实验封存的官方源、已验镜像和评分契约。本实验重验指令、原 Dockerfile、评分环境和 CLI 运行时文件的摘要。

- 试跑各 1 道 Code、Office、Security、Web，两臂共 8 次。收到官方评分、真实 GPT 终态、实际工具回执和相同 thread 续接证据才通过。Web 还核对官方外部评分模型的实际回执。
- 正式组和试跑组没有重叠。正式总计 65 题，Code 20/80、Office 12/50、Security 15/60、Web 18/70。前60题沿用参考实验的冻结顺序，最后追加五道官方容器内安全评测题，两臂继续使用原 thread。追加通过 prepare_workbuddy_security_extra.py 和 append_workbuddy_security.py 冻结、构建并执行。
- 首次正式派发与四类试跑采用相同源码、模型和二进制。正式运行中的恢复升级保留原试跑资格，另记录源码差异和针对实际故障的回归证据；原模型及CLI二进制保持固定。
- 使用官方 Code、Office、Web CompositeVerifier 和 Security 程序评分。阶段验收允许模型取得任意有效分数，包括零分。工程、传输或评分失败保留全部证据。

## 上下文与容量

原生臂的 Responses 请求逐字节转发，沿用 Codex 自身的压缩。CLM 臂由模型选择需要移除的成对工具交换、写短记忆，网关验收后应用到模型请求。两臂保留实际完整请求及返回，并使用同一个有效模型窗口。

CLM 检查上一题最终请求的原始输入大小和模型实际输入 token。达到 3 MiB 或 165,000 token 任一阈值时，在下一题送入之前调用原生 thread/compact/start，保持原 thread ID。保护性压缩及其费用单独标注。原生压缩改变首条用户消息时，清理失效的工具交换引用并保留已经写入的短记忆。网关对整份原始 HTTP 请求的传输上限是 64 MiB。常规 CLM 编辑作用于 API 请求，原生保护性压缩会改变 CLI 的活跃历史。

## 运行与轨迹

在 H20 独立源码目录依次运行以下命令。Harbor、Docker Compose、题库和镜像来自已核对的共享参考环境。题面通过文件传输，API 凭据只在宿主网关进程。

    ./h20.sh prepare pilot PILOT_DIR
    ./h20.sh prepare formal FORMAL_DIR
    ./h20.sh run PILOT_DIR
    ./h20.sh run FORMAL_DIR --pilot-gate PILOT_DIR

这四步运行冻结的60题前缀。完整65题还需要运行 prepare_workbuddy_security_extra.py 和 build_workbuddy_security_extra.py，待镜像就绪，再运行 append_workbuddy_security.py，将五题追加至两条原生线程。H20 的 launch-combined-65.sh 自动等待前缀和镜像就绪，完整结果写入 formal-65。最终审计使用 delivery65。

框架中的生成式 verifier.py 上传存在文件模式问题。本项目的 patch_workbuddy_verifier_permissions.py 将官方框架复制到独立 framework 目录，设置临时脚本为0644。h20.sh 优先加载该目录。check_workbuddy_verifier_mode.py 验证上传权限，regrade_workbuddy_code.py 可以用原始补丁重新运行受影响的官方评分。更正成绩与原错误评分分别保留，模型轨迹沿用原件。

每个任务的 evidence 目录包括原始和实际发送的 JSON、原始响应流、用量、状态、各层摘要和原生会话 JSONL。CLM 同时保留编辑前后状态，另存每臂共享笔记快照。Harbor trials 目录保存原生 app-server 事件、stderr、产物及官方评分。工程失败留在各自尝试目录。对照由 benchmarks/audit_workbuddy.py 从实际回执独立汇总。

网关在交付 SSE 前核查终态，针对短期传输错误、限流或服务端错误，以同一请求体最多尝试三次。每次原始回执都单独保存。Codex 只消费一次最终返回，已执行的工具不会因一次网关重试而重新执行。

## 断流与任务恢复

`check_workbuddy_recovery.py` 使用第6题真实失败流，验证临时 `upstream_error` 重试、相同请求体、只交付完整成功响应、三次失败后返回502，以及永久错误分类。它同时从宿主保护的请求记录重建CLM投影，并在真实Docker任务容器验证根文件系统与挂载产物检查点；全部为零模型调用的工程回归。

`continue_workbuddy_transport.py` 核对已完成前缀、原生会话中的全部已执行调用及其摘要，然后续接原thread。第6题首次恢复仅重放已经核对的原始三文件补丁，使用原版Codex补丁引擎，恢复后比对最后一次工具观察与文件摘要，原失败不删除。

后续未完成任务在AGENT_END边界暂停容器，保存工作区镜像、镜像归档和挂载产物，随即解除暂停。临时传输失败可在同thread中恢复工作区和产物；每个控制器对当前题最多四次尝试，修复并通过资格核验的新版本可在原检查点继续，因此跨版本总次数单独记录。每次失败的请求、会话、检查点和恢复意图保存在failed-attempts目录。重复发送原题面构成新的续接turn，所有额外请求与费用需单列；新环境或评分故障仍需诊断，不据此重做已完成题目。

追加DNS题的官方CMD负责启动named，Harbor的默认sleep命令会覆盖它。适配器在该题首次初始化时调用官方restart-named.sh，并查询容器内127.0.0.1:5353。检查点记录服务存活与健康状态；健康服务恢复时保留活动区文件，停止状态保持停止。存活但不健康的进程内存无法从文件快照还原，自动恢复会在此状态停止。check_workbuddy_dns.py分别以健康和停止状态做真实Harbor容器恢复验证，模型API调用0。

补充题还需要五镜像工具预检和serial-environment-check.json。追加入口核对官方题面、镜像ID、工具预检SHA、DNS检查及该版本传输回归，再沿原thread执行61–65。前60题的接受版本及追加版本升级分别记录。
