"""Append the five frozen Security trials to both completed 60-task native threads."""

import argparse
import asyncio
import collections
import json
import shutil
from pathlib import Path

import run
from clm.context import write_json
from checkpoint import restore_context
from continue_workbuddy_transport import instance_key, resilient_trial, validate_upgrade


async def execute(prefix, extra, target, pilot):
    proof=run.read(prefix/"accepted.json")
    frozen=run.read(prefix/"plan.json")
    supplemental=run.read(extra/"plan.json")
    qualified=run.read(pilot/"accepted.json")
    if (proof["pairs"]!=60 or proof["plan_sha256"]!=run.sha(prefix/"plan.json")
            or proof["code_sha256"]!=frozen["code_sha256"] or frozen["runtime_sha256"]!=run.runtime_sha()
            or qualified["pairs"]!=4
            or qualified["code_sha256"]!=frozen.get("version_upgrade",{}).get("original_code_sha256",frozen["code_sha256"])):
        raise ValueError("Prefix, runtime, or pilot qualification changed")
    environment=run.read(extra/"serial-environment-check.json")
    if not environment["accepted"] or environment["code_sha256"]!=run.code_sha():
        raise ValueError("Serial task environment has not been qualified")
    stopped_path=Path(environment["stopped_dns_check"])
    stopped=run.read(stopped_path)
    if (run.sha(stopped_path)!=environment["stopped_dns_check_sha256"]
            or stopped["code_sha256"]!=run.code_sha() or stopped["api_calls"]!=0
            or not stopped["stopped_dns_preserved"] or not stopped["active_zone_preserved"]):
        raise ValueError("Stopped DNS service restoration qualification changed")
    upgrade=validate_upgrade(prefix.parent,prefix,pilot,Path(environment["regression"]))
    regression=run.read(Path(environment["regression"])/"RESULT.json")
    if "dns_service" not in regression:
        raise ValueError("Official DNS startup contract has not been verified")
    tools=Path(environment["tools_smoke"])
    if run.sha(tools)!=environment["tools_smoke_sha256"]:
        raise ValueError("Supplementary tools qualification changed")
    builds=run.read(extra/"build-progress.json")
    if len(builds)!=5 or not all(x["image_id"] and x["exit"]==0 for x in builds):
        raise ValueError("Supplementary official images are not ready")
    observed={x["task"]:x["image_id"] for x in run.read(tools) if x["exit"]==0}
    if observed!={x["row"]["task"]:x["image_id"] for x in builds}:
        raise ValueError("Qualified supplementary images differ from the actual image set")
    rows=list(frozen["tasks"])
    for row in supplemental["tasks"]:
        row=dict(row)
        task=run.task_dir(extra,row)
        if run.sha(task/"instruction.md")!=row["instruction_sha256"]:
            raise ValueError("Supplementary instruction changed")
        receipt=next(x for x in builds if x["row"]["task"]==row["task"])
        row.update(image=receipt["image"],image_id=receipt["image_id"],
                   staged_task_config_sha256=run.sha(task/"task.toml"))
        if run.image_id(row["image"])!=row["image_id"]:
            raise ValueError("Supplementary image ID changed")
        rows.append(row)
    if collections.Counter(x["domain"] for x in rows)!={"code":20,"office":12,"sec":15,"web":18}:
        raise ValueError("The combined plan does not satisfy the quarter distribution")
    if len({(x["domain"],x["task"]) for x in rows})!=65:
        raise ValueError("Combined sample duplicates a task")
    target.mkdir(mode=0o700,exist_ok=False)
    shutil.copy2(prefix/"offline.yaml",target/"offline.yaml")
    combined={**frozen,"tasks":rows,"reference":str(target),
              "code_sha256":run.code_sha(),"version_upgrade":upgrade,
              "serial_environment_check_sha256":run.sha(extra/"serial-environment-check.json"),
              "chosen_totals":{"code":20,"office":12,"sec":15,"web":18},
              "quarter_correction":"Original 60-task order, then five additional Security tasks",
              "prefix":str(prefix),"prefix_plan_sha256":run.sha(prefix/"plan.json")}
    write_json(target/"plan.json",combined)
    for row in rows:
        source=run.task_dir(Path(frozen["reference"]) if row["position"]<=60 else extra,row)
        destination=run.task_dir(target,row)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(source,destination,symlinks=True)
        dataset=destination.parent.parent
        old_dataset=source.parent.parent
        if not (dataset/"dataset.toml").exists():
            shutil.copy2(old_dataset/"dataset.toml",dataset/"dataset.toml")
            if (old_dataset/"shared").exists():
                shutil.copytree(old_dataset/"shared",dataset/"shared",symlinks=True)
    for arm in run.ARMS:
        shutil.copytree(prefix/arm,target/arm,symlinks=True)
    previous={}
    receipts=[]
    for row in rows[:60]:
        for arm in run.ARMS:
            record=run.read(target/arm/"evidence"/instance_key(row)/"receipt.json")
            if not record["accepted"] or record["row"]!=row:
                raise ValueError("Combined prefix contains a failed or mismatched trial")
            snapshot=target/arm/"evidence"/instance_key(row)/"native-session.jsonl"
            if run.sha(snapshot)!=record["session_sha256"]:
                raise ValueError("Prefix native snapshot checksum differs")
            previous[arm]=record
            receipts.append(record)
    context=restore_context(target/"clm/context",target/"clm")
    key,base=run.provider()
    write_json(target/"progress.json",[{k:v for k,v in r.items() if k!="wire"} for r in receipts])
    for row in rows[60:]:
        for arm in run.ARMS:
            print(f"START {row['position']} {arm} {row['task']}",flush=True)
            receipt=await resilient_trial(target,combined,row,arm,previous[arm],key,base,
                                       context if arm=="clm" else None)
            receipts.append(receipt)
            write_json(target/"progress.json",[{k:v for k,v in r.items() if k!="wire"} for r in receipts])
            if not receipt["accepted"]:
                raise RuntimeError(f"Supplement stopped at {row['position']} {arm}")
            previous[arm]=receipt
    write_json(target/"accepted.json",{
        "stage":"formal","pairs":65,"code_sha256":combined["code_sha256"],
        "runtime_sha256":combined["runtime_sha256"],"plan_sha256":run.sha(target/"plan.json"),
        "threads":{arm:record["thread"] for arm,record in previous.items()},
    })


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("prefix",type=Path)
    parser.add_argument("extra",type=Path)
    parser.add_argument("target",type=Path)
    parser.add_argument("--pilot-gate",type=Path,required=True)
    args=parser.parse_args()
    asyncio.run(execute(args.prefix,args.extra,args.target,args.pilot_gate))
