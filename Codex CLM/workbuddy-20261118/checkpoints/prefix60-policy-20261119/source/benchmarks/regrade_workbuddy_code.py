"""Regrade the original Code patches after correcting the framework's upload permissions."""

import argparse
import asyncio
import json
import shutil
from pathlib import Path

from harbor.models.trial.config import AgentConfig, EnvironmentConfig, TaskConfig, TrialConfig, VerifierConfig
from harbor.trial.trial import Trial

from agent import SerialCodex
from clm.context import write_json
import run


class PatchAgent(SerialCodex):
    async def run(self,instruction,environment,context):
        patch=Path(self.options["patch"])
        await environment.upload_file(patch,"/tmp/original-agent.patch")
        result=await self.exec_as_root(environment,
            "chown dev /tmp/original-agent.patch; chmod 600 /tmp/original-agent.patch")
        if result.return_code:
            raise RuntimeError("Patch transfer permissions failed")
        result=await environment.exec(
            command="git apply --check /tmp/original-agent.patch && git apply /tmp/original-agent.patch")
        (self.logs_dir/"patch-restore.txt").write_text(f"{result.stdout}\n{result.stderr}\n")
        if result.return_code:
            raise RuntimeError("Cannot restore the original model patch onto the official image")


async def main(original,output):
    output.mkdir(mode=0o700,parents=True,exist_ok=False)
    plan=run.read(original/"plan.json")
    row=plan["tasks"][3]
    if row["domain"]!="code":
        raise ValueError("Expected the fourth Code task")
    task=run.task_dir(Path(plan["reference"]),row)
    results={}
    for arm in run.ARMS:
        rec=run.read(original/arm/"evidence"/run.instance_key(row)/"receipt.json") if hasattr(run,"instance_key") else run.read(
            original/arm/"evidence"/f"{row['position']:03d}-{row['domain']}-{row['task']}"/"receipt.json")
        trial_dir=original/arm/"trials"/rec["trial_name"]
        patch=trial_dir/"verifier/agent.patch"
        stderr=(trial_dir/"verifier/test_output.txt").read_text()
        if "can't open file '/tests/verifier.py': [Errno 13] Permission denied" not in stderr:
            raise ValueError("Source score was not the identified verifier permissions failure")
        name=f"wbc-code-permission-regrade-{arm}"
        trial=await Trial.create(TrialConfig(
            task=TaskConfig(path=task),trial_name=name,trials_dir=output/"trials",
            agent=AgentConfig(import_path="regrade_workbuddy_code:PatchAgent",model_name=run.MODEL,
                              kwargs={"options":{"arm":arm,"patch":str(patch)}}),
            environment=EnvironmentConfig(
                import_path="workbuddy_bench.runner.docker_environment:WorkBuddyDockerEnvironment",
                mounts=[run.bind(run.RUNTIME,"/opt/codex")],
                extra_docker_compose=[original/"offline.yaml"],
            ),
            verifier=VerifierConfig(import_path="workbuddy_bench.judge:CompositeVerifier"),
        ))
        # This CPU operation restores patches only. No API bridge or CLM tools are mounted.
        trial.agent.options["arm"]="native"
        trial.agent.setup=basic_setup.__get__(trial.agent,type(trial.agent))
        result=(await trial.run()).model_dump(mode="json")
        graded=output/"trials"/name
        errors=list((graded/"verifier").glob("*output*"))
        if result.get("exception_info") or not result.get("verifier_result"):
            raise RuntimeError(f"Official CPU regrade failed for {arm}: {result.get('exception_info')}")
        if any("can't open file '/tests/verifier.py': [Errno 13]" in p.read_text(errors="replace") for p in errors):
            raise RuntimeError("The original permissions error persists")
        reconstructed=graded/"verifier/agent.patch"
        if not reconstructed.exists() or run.sha(patch)!=run.sha(reconstructed):
            raise ValueError("Regrading changed the original model patch")
        results[arm]={"row":row,"source_trial":str(trial_dir),"rescore_trial":str(graded),
                      "patch_sha256":run.sha(patch),"original_reward":rec["reward"],
                      "reward":result["verifier_result"]["rewards"]}
        write_json(output/"results.json",results)
        print(json.dumps(results[arm],ensure_ascii=False),flush=True)


async def basic_setup(self,environment):
    from workbuddy_bench.agents._agent_user import ensure_agent_user
    await ensure_agent_user(self,environment)
    result=await self.exec_as_root(environment,
        "mkdir -p /logs/agent /logs/artifacts; chmod a+x /logs; chown dev /logs/agent /logs/artifacts")
    if result.return_code:
        raise RuntimeError("CPU regrade user setup failed")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("original",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    asyncio.run(main(args.original,args.output))
