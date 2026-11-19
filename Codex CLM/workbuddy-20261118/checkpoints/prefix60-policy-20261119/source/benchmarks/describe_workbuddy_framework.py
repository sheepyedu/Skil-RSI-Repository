"""Generate code-backed framework diagrams, exact prompt templates and evidence examples."""

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def template(node):
    parts = []
    for value in node.values:
        if isinstance(value, ast.Constant):
            parts.append(value.value)
        elif isinstance(value, ast.FormattedValue):
            name = ast.unparse(value.value)
            parts.append({"opts['marker']": "{marker}", "cwd": "{cwd}"}[name])
        else:
            raise ValueError("Unexpected prompt template expression")
    return "".join(parts)


def prompts(source):
    native = source / "benchmarks/workbuddy/native_turn.py"
    tree = ast.parse(native.read_text())
    developer = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == "instructions" for t in node.targets))
    task = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "prompt" for t in node.targets))
    assert isinstance(task.value, ast.BinOp) and isinstance(task.value.left, ast.JoinedStr)
    memory_source = source / "clm/context.py"
    memory = next(node for node in ast.walk(ast.parse(memory_source.read_text()))
                  if isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and node.value.startswith("CLM memory written by the assistant:"))
    return {
        "P1": {"arms": ["native", "clm"], "role": "user", "source": str(native),
               "line": task.lineno, "source_sha256": sha(native),
               "text": template(task.value.left) + "{official_instruction}"},
        "P2": {"arms": ["clm"], "role": "developer_instructions", "source": str(native),
               "line": developer.lineno, "source_sha256": sha(native), "text": ast.literal_eval(developer.value)},
        "P3": {"arms": ["clm"], "role": "first_user_additional_input_text", "source": str(memory_source),
               "line": memory.lineno, "source_sha256": sha(memory_source), "text": memory.value + "{assistant_note}"},
    }


def event_usage(path):
    for line in path.read_text().splitlines():
        if line.startswith("data:"):
            try:
                event = json.loads(line[5:])
            except ValueError:
                continue
            if event.get("type") == "response.completed":
                return event["response"].get("usage") or {}
    return {}


def examples(run_root):
    accepted = []
    for path in sorted((run_root / "clm/evidence").glob("*/wire/*/receipt.json")):
        event = read(path)
        if (event.get("clm") or {}).get("edit") != "accepted":
            continue
        sent = read(path.parent / "request.sent.json")
        notes = [part["text"] for item in sent["input"] if item.get("role") == "user"
                 and isinstance(item.get("content"), list) for part in item["content"]
                 if part.get("text", "").startswith("CLM memory written by the assistant:\n")]
        accepted.append({"receipt": str(path), "receipt_sha256": sha(path), "event": event["clm"],
                         "injected_memory": notes, "request_raw_sha256": sha(path.parent / "request.raw.json"),
                         "request_sent_sha256": sha(path.parent / "request.sent.json")})
        break
    assert accepted, "No actual CLM edit evidence"
    case = next((run_root / "native/evidence").glob("008*"))
    record = read(case / "receipt.json")
    trials = run_root / "native/trials" / record["trial_name"]
    native = [json.loads(line) for line in (trials / "agent/native.jsonl").open()]
    compact_events = [entry for entry in native if entry.get("data", {}).get("method") == "item/completed"
                      and entry["data"].get("params", {}).get("item", {}).get("type") == "contextCompaction"]
    assert len(compact_events) == 1
    wires = sorted((case / "wire").glob("*/receipt.json"))
    index = next(i for i, p in enumerate(wires) if "CONTEXT CHECKPOINT COMPACTION" in
                 (p.parent / "request.raw.json").read_text())
    boundary = []
    for label, path in zip(("ordinary_before", "compaction_request", "ordinary_after"), wires[index-1:index+2]):
        event = read(path)
        assert event["delivered"] and event["raw_sha256"] == event["sent_sha256"]
        usage = event_usage(path.parent / "response.raw")
        boundary.append({"label": label, "receipt": str(path), "path": event["path"],
                         "raw_input_array_bytes": event["raw_input_bytes"],
                         "reported_input_tokens": usage.get("input_tokens"),
                         "request_raw_sha256": sha(path.parent / "request.raw.json"),
                         "response_sha256": sha(path.parent / "response.raw")})
    return {"clm_edit": accepted[0], "native_compaction": {
        "thread": record["thread"], "trial": record["trial_name"],
        "native_event": compact_events[0], "boundary": boundary,
        "scope": "One completed task-008 native trial, adjacent ordinary requests around the compaction request",
    }}


MERMAID = '''flowchart TB
  subgraph B[官方 WorkBuddy 数据与评分]
    D[官方260题与原始instruction SHA\nCode80 / Office50 / Security60 / Web70]
    J[原有CompositeVerifier与Security脚本\nWeb官方多模态评分]
  end
  subgraph H[共同串行适配：两臂相同，禁止链内并发]
    S[冻结65：Code20 / Office12 / Security15 / Web18\n参考60题序 + 末尾追加5题\n任务i：native → clm，再进入i+1\n每题新官方环境；每臂独立HOME与同一thread]
    P1[P1：共同user任务包装 + 官方题面原文]
    R[宿主保护记录器\nraw/sent JSON、每个响应attempt、会话、产物、SHA]
    E[每题工作区与任务产物\n原有官方输出路径]
  end
  subgraph C[原生 Codex CLI 0.169.0：官方二进制与工具宿主]
    CLI[app-server\nthread/start或thread/resume；turn/start]
    ACTIVE[CLI活跃上下文 H_t]
    STORE[原生会话JSONL / CODEX_HOME\n保留旧历史证据；每题沿原thread]
    TOOLS[原生Code Mode / exec_command / apply_patch]
    COMPACT[原生context compaction\n自动触发或thread/compact/start]
  end
  subgraph M[CLM新增：模型通过原生Bash调用外部命令]
    P2[P2：CLM专用developer说明]
    CT[clm-context status / show / edit]
    LIVE[LIVE_CTX_MAIN.json\nrevision、可编辑完整批次、note]
    EDIT[edit.json\nrevision + drop IDs + note]
    PROJ[API输入投影 P_t\n删除旧完整工具批次；P3追加短记忆]
    P3[P3：CLM memory written by the assistant + 动态note]
    G[CLM题间容量保护\n上一题raw ≥ 3 MiB 或实际input ≥ 165000 tokens]
  end
  W[容器127.0.0.1:19731 → Unix socket → 宿主网关\nBase原字节透传；CLM采用P_t\n最多3次同请求，仅交付完整成功响应]
  GPT[GPT-6.1-sol Responses API\n模型报告ID；后端权重未独立验证]
  N[每臂独立/serial-home/notes\n两臂均可通过原生工具读写；不自动全文注入]
  CP[终态临时传输故障\nAGENT_END暂停、工作区镜像及挂载产物、TAR/SHA]
  RES[从当前题快照恢复；同thread续接\n保留原失败与费用；不重做已完成题]
  DNS[追加DNS题初始化\n启动官方named；恢复健康或停止状态；保留区文件]
  JR[共同评分技术适配与独立复评\n权限 / UTF-8 BOM / 类型守卫 / CBC\n冻结原补丁及产物；不重跑actor\n保留原成绩与失败，附独立评分覆盖层]
  D --> S --> P1 --> CLI
  CLI <--> ACTIVE
  CLI <--> STORE
  CLI <--> TOOLS
  TOOLS --> E --> J --> R
  CLI <--> W <--> GPT
  P2 --> CLI
  TOOLS -->|仅CLM可用该命令| CT
  CT <-->|工具输出P4| LIVE
  CT --> EDIT --> PROJ
  PROJ --> LIVE
  P3 --> PROJ
  ACTIVE -->|原始input| PROJ -->|CLM分支| W
  TOOLS <--> N
  W -.前题用量.-> G --> COMPACT -->|实际替换活跃历史| ACTIVE
  ACTIVE -.原生自动策略.-> COMPACT
  W --> R
  S --> CP --> RES --> CLI
  RES --> E
  S --> DNS --> E
  J -.技术缺口.-> JR --> R
  classDef original fill:#edf4ff,stroke:#2867a6,color:#122d4a;
  classDef official fill:#edf8f1,stroke:#238159,color:#123b26;
  classDef added fill:#fff0e3,stroke:#e5781a,color:#5c2d08;
  classDef external fill:#f3effb,stroke:#7d60aa,color:#332451;
  class D,J,E official;
  class CLI,ACTIVE,STORE,TOOLS,COMPACT original;
  class S,P1,R,P2,CT,LIVE,EDIT,PROJ,P3,G,W,N,CP,RES,DNS,JR added;
  class GPT external;
'''


def draw(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
    font = FontProperties(fname="/usr/share/fonts/truetype/wqy/wqy-microhei.ttc")
    plt.rcParams["svg.fonttype"] = "path"
    fig, ax = plt.subplots(figsize=(19, 12.6))
    ax.set(xlim=(-.3, 18.4), ylim=(-2.8, 11.1))
    ax.axis("off")
    palette = {"native": ("#edf4ff", "#2867a6"), "added": ("#fff0e3", "#e5781a"),
               "official": ("#edf8f1", "#238159"), "api": ("#f3effb", "#7d60aa")}
    ax.text(9, 10.75, "Codex CLM × WorkBuddy：同题同序、每臂单一原生会话", ha="center", fontproperties=font, fontsize=21)
    ax.text(9, 10.18, "蓝色：原生 Codex　　绿色：官方评测　　橙色：新增/适配（包括共同接线）", ha="center", fontproperties=font, fontsize=12)
    nodes = {
        "data": (1.6, 8.5, "官方WorkBuddy题库260题\n80 Code / 50 Office\n60 Security / 70 Web", "official"),
        "schedule": (5.3, 8.5, "冻结65题（20/12/15/18）\n参考60题序 + 末尾5题\nnative_i → clm_i → i+1\n新工作区、每臂同thread", "added"),
        "cli": (9.1, 8.5, "原生 Codex CLI 0.169.0\napp-server / 活跃上下文 H_t\nP1共同任务；P2仅CLM", "native"),
        "wire": (12.9, 8.5, "记录、投影与传输网关\nBase：原始input字节不变\nCLM：采用投影 P_t", "added"),
        "gpt": (16.5, 8.5, "GPT-6.1-sol\nResponses API\n完整成功响应才交付", "api"),
        "tools": (9.1, 5.9, "原生工具与Code Mode宿主\nexec_command / apply_patch\n工作区文件与普通Bash", "native"),
        "editor": (12.9, 5.9, "CLM命令（仅CLM可用）\nstatus / show / edit\n模型提交drop与短记忆", "added"),
        "projection": (16.5, 5.9, "revision与输入投影\n旧完整工具批次可删除\nP3记忆；P4状态/工具输出", "added"),
        "session": (5.3, 3.3, "原生会话JSONL / HOME\n两臂各自独立\n旧证据继续留档", "native"),
        "compact": (9.1, 3.3, "原生context compaction\n自动策略 / 原生RPC\n真正改变CLI活跃历史", "native"),
        "guard": (12.9, 3.3, "CLM题间容量保护\n前题raw ≥ 3 MiB\n或实际input ≥ 165000 token", "added"),
        "notes": (16.5, 3.3, "每臂独立notes目录\n两臂均可用原生工具读写\n不自动注入笔记全文", "added"),
        "judge": (1.6, 1.0, "官方评分契约\nCompositeVerifier / Security\nWeb官方多模态评分", "official"),
        "output": (5.3, 1.0, "官方指定输出路径\n任务工作区 / artifacts\n两臂采用相同题面", "official"),
        "evidence": (9.1, 1.0, "完整证据与差异报告\n模型IO、工具、编辑与压缩\n失败、评分、SHA与已知用量", "added"),
        "recovery": (12.9, 1.0, "临时故障检查点恢复\n工作区镜像、产物、TAR/SHA\n同thread续接，旧失败保留", "added"),
        "prompt": (16.5, 1.0, "所有新增提示词见全文\nP1共同user / P2 CLM developer\nP3动态记忆 / P4工具观察", "added"),
        "judge_repair": (1.6, -1.5, "评分技术适配与独立复评\n权限 / BOM / 类型守卫 / CBC\n原补丁；无actor重跑\n旧成绩和失败留档", "added"),
    }
    width, height = 3.15, 1.52
    for key, (x, y, text, color) in nodes.items():
        face, edge = palette[color]
        ax.add_patch(FancyBboxPatch((x-width/2, y-height/2), width, height,
                                   boxstyle="round,pad=0.025,rounding_size=0.12", linewidth=1.4,
                                   facecolor=face, edgecolor=edge, zorder=3))
        ax.text(x, y, text, ha="center", va="center", fontsize=10.2, fontproperties=font, linespacing=1.7, zorder=4)
    def arrow(a, b, label=None, both=False, dashed=False, offset=(0, 0)):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="<|-|>" if both else "-|>",
                                    mutation_scale=13, linewidth=1.3, color="#51616f",
                                    linestyle="--" if dashed else "-", zorder=2))
        if label:
            ax.text((a[0]+b[0])/2+offset[0], (a[1]+b[1])/2+offset[1], label,
                    ha="center", va="center", fontsize=8.2, fontproperties=font, color="#394653", zorder=5,
                    bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    arrow((3.2,8.5),(3.7,8.5))
    arrow((6.9,8.5),(7.5,8.5))
    arrow((10.7,8.5),(11.3,8.5),both=True)
    arrow((14.5,8.5),(14.9,8.5),both=True)
    arrow((9.1,7.7),(9.1,6.7),both=True)
    arrow((10.7,5.9),(11.3,5.9))
    arrow((14.5,5.9),(14.9,5.9))
    arrow((15.0,6.7),(14.3,7.7),"CLM输入",offset=(.4,0))
    arrow((11.3,3.3),(10.7,3.3))
    arrow((7.5,3.3),(6.9,3.3))
    arrow((5.3,4.1),(5.3,7.7),"同一thread续接",dashed=True)
    ax.plot([10.65,10.95,10.95], [3.3,4.1,7.4], color="#51616f", linewidth=1.3, zorder=2)
    arrow((10.95,7.4),(10.55,7.75))
    ax.text(10.95,6.0,"原生状态更新",rotation=90,ha="center",va="center",fontsize=8.2,fontproperties=font,
            bbox={"facecolor":"white","edgecolor":"none","pad":1},zorder=5)
    arrow((14.6,7.7),(14.6,4.1),"前题用量",dashed=True,offset=(.12,0))
    arrow((14.6,4.1),(14.4,3.7),dashed=True)
    ax.plot([7.55,7.15,7.15], [5.35,4.65,1.85], color="#51616f",linewidth=1.3,zorder=2)
    arrow((7.15,1.85),(6.85,1.1))
    ax.text(7.15,2.3,"产物",ha="center",fontsize=8.2,fontproperties=font,zorder=5,
            bbox={"facecolor":"white","edgecolor":"none","pad":1})
    arrow((3.7,1.0),(3.2,1.0))
    arrow((11.3,1.0),(10.7,1.0))
    ax.plot([1.6,1.6,9.1], [.24,-.03,-.03],color="#51616f",linewidth=1.3,zorder=2)
    arrow((9.1,-.03),(9.1,.24))
    ax.text(5.3,-.03,"官方结果",ha="center",va="center",fontsize=8,fontproperties=font,zorder=5,
            bbox={"facecolor":"white","edgecolor":"none","pad":1})
    arrow((1.6,.24),(1.6,-.72),dashed=True)
    ax.plot([3.2,9.1,9.1],[-1.5,-1.5,.08],color="#e5781a",linewidth=1.3,zorder=2)
    arrow((9.1,.08),(9.1,.24))
    ax.text(6.0,-1.35,"保留原成绩，附独立覆盖层",ha="center",va="center",fontsize=9,fontproperties=font,
            color="#c35f12",bbox={"facecolor":"white","edgecolor":"none","pad":1},zorder=5)
    ax.text(1.6, 6.6, "① 所有题目串行\n② Base与CLM环境独立\n③ 两臂共用P1与传输记录\n④ CLM额外P2、P3及编辑命令",
            ha="center", va="top", fontsize=11, linespacing=1.9, fontproperties=font, color="#354251")
    ax.text(1.6, 3.35, "常规CLM编辑作用于API投影\n不会就地删除CLI历史\n原生compaction才更新活跃上下文",
            ha="center", va="center", fontsize=10.5, linespacing=1.8, fontproperties=font, color="#c35f12")
    ax.text(9, -2.6, "概览图；完整连接、全部新增提示词、保护规则与实际请求证据见 FRAMEWORK.md / framework.mmd / PROMPTS.json", ha="center", fontproperties=font, fontsize=10)
    fig.subplots_adjust(left=.02,right=.99,bottom=.03,top=.98)
    for suffix in ("png", "svg", "pdf"):
        fig.savefig(output / f"framework-overview.{suffix}", dpi=180)
    plt.close(fig)


def main(source, run_root, output):
    output.mkdir(mode=0o700, parents=True)
    instructions = prompts(source)
    evidence = examples(run_root)
    (output / "PROMPTS.json").write_text(json.dumps(instructions, ensure_ascii=False, indent=2) + "\n")
    (output / "EVIDENCE_EXAMPLES.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
    mermaid = re.sub(r'([A-Za-z0-9_]+)\[([^\]]*)\]',
                     lambda m: m.group(1) + '["' + m.group(2).replace('\n', '<br/>').replace('"', '&quot;') + '"]', MERMAID)
    (output / "framework.mmd").write_text(mermaid)
    draw(output)
    edit = evidence["clm_edit"]["event"]
    boundary = evidence["native_compaction"]["boundary"]
    lines = ["# Codex CLM × WorkBuddy：框架与提示词", "",
             "本文件描述当前独立实现。蓝色为原生Codex CLI与工具，绿色为官方WorkBuddy部分，橙色为本项目新增或适配。橙色共同接线适用于两臂，CLM专属部分另外注明。", "",
             "![框架概览](framework-overview.png)", "", "## 详细框架图", "", "```mermaid", mermaid.rstrip(), "```", "",
             "## 两种上下文必须分开", "",
             "CLI活跃上下文H_t由官方Codex维护；常规CLM操作在宿主网关构造API投影P_t。删除投影中的旧工具交换并不等于删除CLI自己的活跃历史。原生自动压缩或thread/compact/start完成后，CLI才会采用新的活跃历史；完整会话JSONL仍保留旧内容供审计。", "",
             "CLM上一题raw输入数组达到3MiB或实际API输入达到165000token时，下题前调用原生压缩。阈值使用逐请求input数组字节及报告用量，不使用会话JSONL文件大小。原生臂保持CLI自身压缩策略。两臂使用相同官方二进制、模型ID和low推理强度。", "",
             "本轮这个provider的实际原生自动压缩通过/v1/responses发送原生摘要任务。网关兼容/v1/responses/compact不代表该路由已经被实际采用。", "",
             "## 所有新增提示词", "",
             "原生Codex本身的系统提示、原生工具定义及原生压缩摘要模板由原版CLI产生。新增文本如下；源码位置和SHA保存在PROMPTS.json。", ""]
    labels = {"P1": "P1：共同的user任务包装（两臂相同）", "P2": "P2：CLM专用developer说明", "P3": "P3：CLM动态短记忆格式"}
    for key in ("P1", "P2", "P3"):
        lines += ["### " + labels[key], "", "```text", instructions[key]["text"], "```", ""]
    lines += ["P1中的official_instruction直接来自冻结instruction.md，逐题核SHA。P2通过该臂独立CODEX_HOME/config.toml的developer_instructions配置。P3追加到首条受保护user消息的额外input_text；assistant_note由模型自己提交，限制8192字节。", "",
              "### P4：工具观察与反馈", "",
              "P4不是额外system/developer指令。模型通过原生Bash运行clm-context，status返回revision、last_edit、note及可编辑ID/字节/工具名；show返回选定旧工具交换；edit写revision、drop、note，并提示下一轮确认acceptance。完整动态观察来自实际工具轨迹与上下文快照，不另拼一段隐藏系统提示。", "",
              "## 可编辑范围与保护", "",
              "仅接受已完成且配对完整的旧工具批次，包含相应assistant/reasoning前缀。最新完整批次保留；未配对、重复call_id及未知格式不进入可编辑范围。原始system、developer与user正文保留。编辑必须匹配当前revision、引用合法ID，并使投影严格缩小。原始请求、实际发送请求及被移除内容均继续保存。", "",
              "每臂都有独立/serial-home/notes，两臂均可用原生文件工具保存通用经验。文件内容只有模型读取时才进入上下文；框架不会自动拼入笔记全文。", "",
              "## 实际运行证据", "",
              f"CLM首个已接受编辑：revision={edit['revision']}，删除ID={','.join(edit['dropped_ids'])}，input数组{edit['before_input_bytes']:,}→{edit['after_input_bytes']:,}字节，减少{edit['removed_items']}个API item。这是API投影变化。", "",
              "该次模型写入的真实短记忆：", "", "```text", "\n".join(evidence["clm_edit"]["injected_memory"]), "```", "",
              "原生第8题，同一次成功恢复内的压缩边界：", "",
              "| 请求 | 路由 | input数组字节 | API报告input token |", "| --- | --- | ---: | ---: |"]
    for row in boundary:
        lines.append(f"| {row['label']} | {row['path']} | {row['raw_input_array_bytes']:,} | {row['reported_input_tokens']:,} |")
    lines += ["", "普通任务请求前后严格配对为647082→89429字节、247200→29274输入token。摘要请求本身的用量单列。旧阶段约570KB→115KB混用了不同恢复尝试及input数组/HTTP正文口径，不作为最终压缩边界。原生contextCompaction完成事件、同一thread及各请求/响应SHA都在EVIDENCE_EXAMPLES.json。", "",
              "## 执行与恢复", "",
              "每题使用新官方工作区；传输失败时最多三次相同请求，仅完整成功响应交给CLI。任务退出后在AGENT_END保存当前工作区镜像、挂载产物与TAR/SHA，再沿同一thread继续。每个控制器对当前题最多四次有界尝试；修复和资格核验后的新版本可继续原检查点，跨版本物理尝试单独统计。旧失败、额外turn和费用都保留；永久配置/格式/评分错误不自动当作网络故障。", "",
              "追加DNS题显式执行被Harbor默认sleep覆盖的官方服务初始化。健康DNS恢复保留活动区文件，停止状态保持停止；文件快照无法恢复活着但不健康的进程内存，框架在该状态保守停止。两种恢复均已用真实Harbor容器验证，未调用模型API。", "",
              "图示完整终态保护对应transport-v2及以后的实现。早期source-07曾将包含response.failed的HTTP200流转交CLI；该历史失败及后续恢复单独保留，不把后来的修复追溯为此前已生效。", "",
              "## 评分适配也是橙色修改", "",
              "官方评分契约保留绿色；新增技术适配和独立复评用橙色旁路表示。包括第4题验证脚本读取权限、第21题CSV的UTF-8 BOM解码、第49题artifact_refs类型守卫，以及第30/53题CBC官方评审依赖。独立复评恢复冻结原补丁和原产物，不重新调用actor，不覆盖原始失败；技术修复后的评分通过独立覆盖层进入报告。第21题两臂原CSV字节不变、原KeyError复现，读取编码修正后原13项断言完整运行。第49题保留134项及缺失原文件的失败检查。", "",
              "标准化build_error/judge_error/ok=false、空评审响应、未提交交互判定和失败CLI终态均需要技术核验；正常语义fail不因低分重跑。CBC沿用官方评审提示词，此处没有新增actor提示词；P1至P4仍是上文逐字列出的完整新增actor指令与工具反馈边界。", "",
              "## 验证边界", "",
              "源版本和题目终态以各plan、逐题receipt及最终65题审计为准。本文件中的两个例子证明已观察到的具体编辑和原生压缩，不替代完整65题长期评测。它不是对原始CLM论文全部操作空间或训练过程的逐项复现声明。", ""]
    (output / "FRAMEWORK.md").write_text("\n".join(lines))
    metadata = {"source": str(source), "run": str(run_root), "plan_sha256": sha(run_root / "plan.json"),
                "runtime_sha256": read(run_root / "plan.json")["runtime_sha256"],
                "files": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}}
    (output / "MANIFEST.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"output": str(output), "files": len(metadata["files"]), "prompts": list(instructions)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.source, args.run, args.output)
