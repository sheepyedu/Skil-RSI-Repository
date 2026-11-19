"""Render the completed paired audit into a report and standalone research figures."""

import argparse
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def render(directory):
    summary = load(directory / "summary.json")
    paired = load(directory / "paired.json")
    usage = load(directory / "all-provider-usage.json")
    if len(paired) != 65 or summary["groups"]["all"]["pairs"] != 65:
        raise ValueError("A final report requires all 65 audited pairs")
    if [p["position"] for p in paired] != list(range(1, 66)):
        raise ValueError("Audited task order is not the frozen sequence")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"native": "#2463a3", "clm": "#eb841e"}
    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True, constrained_layout=True)
    for arm in ("native", "clm"):
        x = [p["position"] for p in paired]
        axes[0].plot(x, [p[arm]["provider_input_peak"] or None for p in paired],
                     label=arm, color=colors[arm])
        axes[1].plot(x, [p[arm]["raw_input_bytes_peak"] / 2**20 for p in paired],
                     label=f"{arm}: CLI raw", color=colors[arm], linestyle="--")
        axes[1].plot(x, [p[arm]["sent_input_bytes_peak"] / 2**20 for p in paired],
                     label=f"{arm}: sent", color=colors[arm])
        axes[2].scatter([p["position"] for p in paired if p[arm]["native_compacted"]
                         or p[arm]["protective_compaction"]],
                        [1 if arm == "native" else 2 for p in paired
                         if p[arm]["native_compacted"] or p[arm]["protective_compaction"]],
                        label=f"{arm}: native compaction", color=colors[arm], marker="s")
    axes[2].scatter([p["position"] for p in paired if p["clm"]["accepted_clm_edits"]],
                    [3 for p in paired if p["clm"]["accepted_clm_edits"]],
                    label="clm: accepted edit", color=colors["clm"], marker="o")
    axes[0].set_ylabel("Peak provider input tokens")
    axes[1].set_ylabel("Peak input JSON (MiB)")
    axes[2].set_yticks([1, 2, 3], ["Native compact", "CLM compact", "CLM edit"])
    axes[2].set_xlabel("Frozen serial task position")
    for axis in axes:
        axis.grid(alpha=.2)
        axis.legend(fontsize=8, loc="upper left")
    for suffix in ("png", "pdf"):
        fig.savefig(directory / f"context-history.{suffix}", dpi=180)
    plt.close(fig)
    groups = summary["groups"]
    lines = ["# WorkBuddy Bench：原生 Codex 与 Codex CLM", "",
             "已核验65题、两臂130条正式结果。两臂按相同题序串行，每臂保持原生单一thread。", "",
             "模型请求ID为gpt-6.1-sol，Codex CLI0.169.0，low推理强度。固定官方框架625b2233093ae4f23e76be28c1f341d41cc70373，数据修订3e8ad839685c589d83a1dd60fe2d15eabb75f27a。", "",
             "| 类别 | 配对题数 | 原生平均reward | CLM平均reward | CLM减原生 | CLM胜/平/原生胜 |",
             "| --- | ---: | ---: | ---: | ---: | --- |"]
    for name in ("code", "office", "sec", "web", "all"):
        row = groups[name]
        lines.append(f"| {name} | {row['pairs']} | {row['native']['mean_reward']:.4f} | "
                     f"{row['clm']['mean_reward']:.4f} | {row['reward_delta_mean']:+.4f} | "
                     f"{row['clm_wins']}/{row['ties']}/{row['native_wins']} |")
    lines += ["", "Code20/80、Office12/50、Security15/60、Web18/70。前60题保持参考实验题序，五道补充安全题在两条原thread的末尾依同序追加。样本沿用既有题池且有容器内题型限制；结果描述此固定样本。", "",
              "官方部分Office评分的检查数量会随提交产物变化。第54题原生214/293、reward0.7304，CLM1363/1888、reward0.7219；同一评分器对缺失表、缺失行或不完整列会跳过相应值检查。因此通过检查的绝对数量和单题pass率不能直接等同于覆盖完整程度。这里保留官方reward，不改分母或补造检查；分类均值按每题等权计算，不把两臂不同数量的原子检查混合汇总。", "",
              "## 上下文与记忆", "", "![逐题请求输入与上下文事件](context-history.png)", "",
              "图中token为每题最大实际API输入用量，JSON字节为原始CLI请求输入及实际发送输入。两者度量不同。压缩事件按题是否出现计数，一题内多次压缩不在此图中重复计数。", "",
              "| 机制 | 原生 | CLM |", "| --- | ---: | ---: |"]
    overall = groups["all"]
    for name, label in (("accepted_clm_edits", "选用尝试中已接受CLM编辑"),
                        ("native_compacted", "观察到原生压缩的题数"),
                        ("protective_compaction", "保护性原生压缩的题数"),
                        ("provider_input_peak", "最大API输入token"),
                        ("raw_input_bytes_peak", "最大原始CLI输入字节"),
                        ("sent_input_bytes_peak", "最大发送输入字节")):
        lines.append(f"| {label} | {overall['native'][name]} | {overall['clm'][name]} |")
    compactions = load(directory / "formal-native-compactions.json")
    for protective, label in ((False, "全部正式尝试中的自动压缩事件"), (True, "全部正式尝试中的保护性压缩事件")):
        counts = {arm: sum(event["arm"] == arm and event["protective"] == protective for event in compactions)
                  for arm in ("native", "clm")}
        lines.append(f"| {label} | {counts['native']} | {counts['clm']} |")
    edits = load(directory / "formal-clm-edit-events.json")
    lines.append(f"| 全部正式尝试中已接受CLM编辑 | 0 | {sum(e['edit'] == 'accepted' for e in edits)} |")
    lines.append(f"| 全部正式尝试中被拒绝CLM编辑 | 0 | {sum(e['edit'] != 'accepted' for e in edits)} |")
    lines += ["", "CLM常规编辑改变API请求的投影，包括完整旧工具交换的删除与短记忆注入。它本身不删除CLI原生历史。CLM上一题原始输入达到3MiB或实际输入达到165000token时，下题前调用原生thread/compact/start，实际改变CLI活跃历史并保留thread；原生臂沿用Codex自身自动压缩。短记忆、持久笔记与原生压缩分别留证。", "",
              "## 传输、评分及恢复", "",
              "四类配对试跑先通过8/8，之后正式派发。正式运行的恢复版本升级保留原pilot资格，源码差异与零模型API的定向回归单列。所有HTTP尝试、失败流、原生会话、工具回执、工作区恢复和评分保留。", "",
              "当前作答与上下文Responses网关（transport-v2及以后）最多三次相同请求，仅交付完整成功流。评分Chat Completions保留原始流，技术失败由独立评分审计拦截并定向补评。早期source-07曾把包含response.failed的HTTP200流交给CLI，原失败完整保留；不能把当前终态保护追溯为早期也已具备。第5题CLM的该失败只有用户/assistant消息通知，没有工具执行；新版本随后沿原thread继续。任务退出后，已执行状态由检查点恢复；每个控制器对当前题最多四次尝试。控制器终止后，经修复和资格核验的新版本可以从原检查点继续，因此四次并非跨版本总次数上限，所有物理尝试另按trial目录及原始ID去重统计。原失败不删除。第6题首次故障发生于检查点机制加入前，核对十个完整调用后仅用原版Codex引擎恢复唯一三文件补丁，并核对最后工具观察；续接使用原thread。额外续接turn和请求属于工程恢复，不能当作纯首次成功轨迹。", "",
              "官方生成verifier.py的0600权限曾使第四题两臂错误判零分。独立框架副本仅修复上传文件权限；沿原模型补丁重评，两臂11/15、0.7333，未再次作答。原错误结果和重评分证据分别保留。", "",
              "第21题两臂原始CSV均含UTF-8 BOM，原验证器按普通UTF-8读取后把首列误认作带BOM的account_id，KeyError使13项检查中断并由外层记为build_error/零分。仅将验证器CSV读取编码改为utf-8-sig；原导出程序、CSV字节及13条断言不变，隔离CPU复评两臂均13/13、1.0。原异常和逐字节CSV已复现，无actor或评分模型调用。评分审计现会拦截标准化build_error/judge_error或ok=false，要求核验其来源；正常语义fail仍保留为模型结果。", "",
              "第49题Office的官方评分器对原生输出的list类型artifact_refs直接调用.values()，异常被外层退出0掩盖为0/1。独立副本仅增加类型守卫，并要求错误类型在原artifact_refs_consistent检查中失败，保留134项分母；用两臂原补丁零模型调用复评。原生原异常可复现，CLM原79/134与逐项失败必须原样复现并保持不变。原工作区包缺少case.yaml与instruction.md，相关五项检查仍失败；没有补造文件或更改模型输出，因此这五项包含数据包局限。", "",
              "官方评审在耗尽重试后可能把空响应直接记作失败。审计逐项检查最终响应、技术错误和回退；已识别的空响应修复仅重试该项的相同请求，并用原官方解析器及汇总函数重新计算。交互评审还依赖CBC2.109.3，离线npm安装失败曾使第30题两臂agent阶段退出127；补评仅在冻结镜像上还原原作答、核对补丁及归档文件，运行缺失agent项。后续仅在actor结束后配置已验官方离线依赖。每项交互判定均核对实际提交和日志，外层退出0不能代替有效判定。其他有效判分、原作答文件、两条会话和原始结果保持留档。逐项修复及原分数见下表；累计费用包含这些额外评审请求。", "",
              "| 题序 | 臂 | 修复前reward | 修复后reward | 修复项目 |", "| --- | --- | ---: | ---: | --- |",
              *[f"| {p['position']} | {arm} | {p[arm]['judge_repair']['original_reward']:.4f} | {p[arm]['reward']:.4f} | {p[arm]['judge_repair']['item_id']} |"
                for p in paired for arm in ("native", "clm") if p[arm].get("judge_repair")], "",
              "Harbor默认用sleep覆盖镜像CMD。追加DNS题显式调用官方启动脚本，保证模型开始前容器内服务可查询；检查点记录服务存活和查询状态。健康服务恢复时保留活动区文件，已停止服务保持停止。文件系统快照不包含进程内存，存活但不健康的DNS状态不会被自动重置后冒充原状态。初始化、健康恢复和停止状态恢复均以真实容器、零模型API验证。", "",
              "## 请求量与用量", "",
              f"全部已索引物理HTTP尝试共{usage['attempts']}次，已知用量{usage['usage_known']}次，未知{usage['usage_unknown']}次。已知输入{usage['known_input_tokens']}token、输出{usage['known_output_tokens']}token。该口径包括试跑、失败及容量辅助请求，按原始时间和响应摘要去重，复制旧目录不会重复计费。未知用量不补零；未提供可核实的实际货币账单。", "",
              "下表按正式/试跑/辅助、两臂及作答与上下文请求/评审请求分列物理尝试；正式行包含失败恢复和评分补评。辅助或无法归属的请求保留独立行，不强行归入正式两臂。token列均为已报告用量的合计，未知用量可能造成低估。", "",
              "| 范围 | 臂 | 用途 | HTTP尝试 | 用量已知/未知 | 已知输入token | 已知输出token |",
              "| --- | --- | --- | ---: | ---: | ---: | ---: |",
              *[f"| {r['scope']} | {r['arm']} | {r['purpose']} | {r['attempts']} | {r['usage_known']}/{r['usage_unknown']} | {r['known_input_tokens']} | {r['known_output_tokens']} |"
                for r in usage["by_scope_arm_purpose"]], "",
              "正式有效任务的请求计数、已知token、缓存用量及墙钟见summary.json；每次物理尝试的证据路径、原始响应SHA和usage见all-provider-attempts.json。工程失败成本不混入正式reward分母。", "",
              "逐题墙钟沿用选用原trial的起止时刻，独立补评和其他失败尝试的额外时间留在各物理请求/恢复时序中；它们不会被悄悄加回原trial时间。", "",
              "all-task-attempts.json保留实际Harbor试验目录、原始结果SHA、原生turn、异常及各复制目录的别名，formal-task-attempt-counts.json逐题逐臂统计跨版本物理尝试和无结果目录。Harbor之外、模型启动之前的管理资格门错误另保留在完整归档，不冒充模型作答尝试。", "",
              "## 解释范围与证据", "",
              "本轮每臂只有一条持续学习链、每题一份选用结果，早期误差会影响后续历史。评分模型、环境和恢复也会引入差异。平均reward和配对差是本轮描述统计，不能据此单独归因为CLM机制或推广为模型整体优劣。API报告的模型ID未独立验证后端权重。", "",
              "paired.csv提供逐题reward，paired.json提供逐题上下文、工具及时间统计，summary.json提供分类汇总，sha256.jsonl索引全轨迹与旧失败。all-clm-edit-events.json按原始请求时间和SHA去重，包含失败尝试中已生效的编辑及被拒绝编辑；全部CLM请求均从原始input、完整工具批次和短记忆独立重建实际投影，保护文本与投影SHA逐字验证。完整归档及分卷SHA另见交付目录。", "",
              "原生thread：`"+summary["threads"]["native"]+"`；CLM thread：`"+summary["threads"]["clm"]+"`。", ""]
    output = directory / "REPORT.md"
    with output.open("x") as stream:
        stream.write("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("audit_directory", type=Path)
    args = parser.parse_args()
    render(args.audit_directory)
