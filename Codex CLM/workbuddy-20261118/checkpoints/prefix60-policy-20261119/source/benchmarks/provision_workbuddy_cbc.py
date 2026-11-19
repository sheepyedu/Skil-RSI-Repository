"""Install the official interactive judge dependency only after the actor has closed."""

import argparse
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path


def load(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def docker(*args, timeout=120):
    return subprocess.check_output(["docker", *args], text=True, timeout=timeout).strip()


def actor_done(directory):
    result = directory / "agent/native-result.json"
    timeline = directory / "agent/native.jsonl"
    if not result.is_file() or not timeline.is_file():
        return None
    native = load(result)
    if native.get("native_exit") != 0 or not native.get("turn"):
        return None
    completed = None
    for line in timeline.open():
        event = json.loads(line).get("data") or {}
        if event.get("method") == "turn/completed":
            completed = (event.get("params") or {}).get("turn") or {}
    if not completed or completed.get("id") != native["turn"] or completed.get("status") != "completed":
        return None
    return {"thread": native["thread"], "turn": native["turn"], "native_result_sha256": sha(result),
            "native_timeline_sha256": sha(timeline)}


def identify(info, base):
    mounts = {m["Destination"]: m["Source"] for m in info["Mounts"]}
    raw = mounts.get("/serial-home", "")
    if raw.startswith("/mainroot" + str(base) + "/"):
        mounts = {key: value.removeprefix("/mainroot") for key, value in mounts.items()}
    home = Path(mounts.get("/serial-home", "/"))
    if not home.is_relative_to(base) or home.name != "home" or home.parent.name not in ("native", "clm"):
        return None
    arm, run = home.parent.name, home.parent.parent
    if not re.fullmatch(r"formal-\d+", run.name) or run.parent != base:
        return None
    agent = Path(mounts.get("/logs/agent", "/"))
    trial = agent.parent
    if agent.name != "agent" or trial.parent != run / arm / "trials":
        return None
    label = info["Config"].get("Labels", {}).get("com.docker.compose.project")
    if label != trial.name + "__env":
        return None
    match = re.search(r"-(native|clm)-(\d{3})(?:-r\d+)?$", trial.name)
    if not match or match[1] != arm:
        return None
    plan = load(run / "plan.json")
    row = next(r for r in plan["tasks"] if r["position"] == int(match[2]))
    return {"arm": arm, "run": run, "home": home, "trial": trial, "row": row, "plan": plan}


def home_digest(home):
    records = []
    for path in sorted(home.rglob("*")):
        if path.is_symlink():
            records.append((str(path.relative_to(home)), "symlink", str(path.readlink())))
        elif path.is_file():
            records.append((str(path.relative_to(home)), "file", sha(path)))
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def scan(base, output):
    qualified = load(base / "cbc-cache/QUALIFIED.json")
    bundle = base / "cbc-cache/install.tar.gz"
    if (qualified["version"] != "2.109.3" or qualified["model_api_calls"] != 0
            or qualified["bundle_sha256"] != sha(bundle)):
        raise ValueError("CBC bundle has not passed the offline qualification")
    output.mkdir(parents=True, exist_ok=True)
    installed = []
    identifiers = docker("ps", "-q", "--filter", "name=wbc-", "--filter", "label=com.docker.compose.service=main").splitlines()
    for identifier in identifiers:
        info = json.loads(docker("inspect", identifier))[0]
        context = identify(info, base)
        if not context or context["row"]["domain"] != "web":
            continue
        proof = actor_done(context["trial"])
        if not proof:
            continue
        target = output / (context["trial"].name + ".json")
        if target.exists():
            continue
        row = context["row"]
        task = Path(context["plan"]["reference"]) / "datasets/wb-bench-web-v1.0/tasks" / row["task"]
        cases = list((task / "tests/web/verify-context/cases").glob("*.json"))
        if len(cases) != 1:
            raise ValueError("Cannot identify the official Web scoring context")
        recipe = load(cases[0])["evaluation_spec"]["scoring_recipe"]
        if not any(item.get("judge_type") == "agent" for item in recipe.get("checklist_items", recipe.get("dimension_items", []))):
            continue
        before = home_digest(context["home"])
        docker("cp", str(bundle), identifier + ":/tmp/workbuddy-cbc-install.tar.gz")
        result = subprocess.run(["docker", "exec", "--user", "root", identifier, "/bin/bash", "-c",
            "set -eu; echo '" + qualified["bundle_sha256"] + "  /tmp/workbuddy-cbc-install.tar.gz' | sha256sum -c -; "
            "test ! -e /opt/codebuddy-code; tar -xzf /tmp/workbuddy-cbc-install.tar.gz -C /opt; "
            "ln -s /opt/codebuddy-code/bin/codebuddy /usr/local/bin/cbc; cbc --version"],
            capture_output=True, text=True, timeout=120)
        after = home_digest(context["home"])
        record = {"container": identifier, "run": str(context["run"]), "arm": context["arm"],
                  "row": row, "actor_complete": proof, "bundle_sha256": qualified["bundle_sha256"],
                  "exit": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                  "home_before_sha256": before, "home_after_sha256": after,
                  "actor_home_content_unchanged": before == after, "provisioned_at_ns": time.time_ns(),
                  "model_api_calls_for_provisioning": 0,
                  "scope": "Official CBC judge dependency installed after actor termination; task inputs, actor runtime, shared image and other projects unchanged."}
        with target.open("x") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
        if result.returncode or before != after or "2.109.3" not in result.stdout:
            raise RuntimeError(f"CBC provisioning did not preserve the completed actor: {target}")
        installed.append(str(target))
    return installed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--watch", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            for path in scan(args.base, args.output):
                print(path, flush=True)
        except (subprocess.SubprocessError, OSError) as error:
            # A container can close between inspection and copying; retain the incident.
            with (args.output / "incidents.jsonl").open("a") as stream:
                stream.write(json.dumps({"time_ns": time.time_ns(), "error": str(error)}) + "\n")
        if not args.watch or (args.output / "STOP").exists() or (args.base / "formal-65/accepted.json").exists():
            break
        time.sleep(3)
