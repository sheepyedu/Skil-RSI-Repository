"""Prebuild the frozen WorkBuddy task images and retain recipe and image provenance."""

import argparse
import concurrent.futures
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import toml

from wire import write_json


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def image_id(image):
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def dockerfile_text(original, web_runtime):
    text = original.read_text()
    if web_runtime and "COPY workspace.tar.gz " in text:
        return f"FROM {web_runtime}\n" + text[text.index("COPY workspace.tar.gz "):]
    lines = text.splitlines(keepends=True)
    index = next((i for i, line in enumerate(lines) if line.lstrip().upper().startswith("FROM ")), None)
    if index is None:
        raise ValueError(f"Missing FROM in {original}")
    if "python:3." in lines[index]:
        # APT's signed package metadata and HTTPS are unchanged apart from the
        # mirror host. Keep the project base image and benchmark build steps.
        lines[index + 1:index + 1] = [
            "RUN sed -i s@http://deb.debian.org@https://mirrors.aliyun.com@g /etc/apt/sources.list.d/debian.sources\n",
            "ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple\n",
        ]
    if "radare/radare2:" in lines[index]:
        pip_index = next(i for i, line in enumerate(lines) if line.startswith("RUN pip3 install "))
        lines.insert(pip_index, "ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple\n")
    return "".join(lines)


def build(run, row, archive, web_runtime):
    domain, task = row["domain"], row["task"]
    task_dir = run / "datasets" / f"wb-bench-{domain}-v1.0" / "tasks" / task
    source = task_dir / "environment"
    original = source / "Dockerfile"
    source_hash = digest(original)
    if source_hash != row["dockerfile_sha256"]:
        raise ValueError(f"Source hash mismatch for {task}")
    prefix = f"{row['position']:03d}-{domain}-{task}"
    evidence = archive / prefix
    evidence.mkdir(exist_ok=True)
    recipe = evidence / "Dockerfile"
    recipe.write_text(dockerfile_text(original, web_runtime if domain == "web" else None))
    recipe_hash = digest(recipe)
    image = "wb-clm-formal-" + f"{row['position']:03d}-{domain}:" + recipe_hash[:16]
    ident = image_id(image)
    started = time.time()
    if not ident:
        with (evidence / "docker-build.log").open("wb") as log:
            try:
                status = subprocess.run(
                    ["docker", "build", "--label", f"workbuddy.serial.recipe={recipe_hash}",
                     "--file", str(recipe), "--tag", image, str(source)],
                    stdout=log, stderr=subprocess.STDOUT, check=False, timeout=1200,
                ).returncode
            except subprocess.TimeoutExpired:
                status = 124
        ident = image_id(image) if status == 0 else None
    else:
        status = 0
    receipt = {
        "row": row, "image": image, "image_id": ident, "status": status,
        "dockerfile_original_sha256": source_hash, "dockerfile_build_sha256": recipe_hash,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    write_json(evidence / "build.json", receipt)
    if ident:
        spec = task_dir / "task.toml"
        task_config = toml.loads(spec.read_text())
        task_config["environment"]["docker_image"] = image
        temporary = spec.with_suffix(".tmp")
        temporary.write_text(toml.dumps(task_config))
        temporary.replace(spec)
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--domains", nargs="+", default=["code", "office", "sec", "web"])
    ap.add_argument("--tasks", nargs="+")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--web-runtime")
    ap.add_argument("--attempt", required=True)
    args = ap.parse_args()
    os.umask(0o077)
    if (args.run / "sessions.json").exists():
        raise ValueError("Formal session already started")
    plan_path = args.run / "plan.json"
    plan = json.loads(plan_path.read_text())
    archive = args.run / "image-builds" / args.attempt
    archive.mkdir(parents=True)
    picks = [
        row for row in plan["tasks"]
        if row["domain"] in args.domains and (not args.tasks or row["task"] in args.tasks)
    ]
    with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
        futures = [pool.submit(build, args.run, row, archive, args.web_runtime) for row in picks]
        receipts = []
        for future in concurrent.futures.as_completed(futures):
            try:
                receipt = future.result()
            except (OSError, ValueError) as error:
                print(type(error).__name__, str(error), flush=True)
                continue
            print(receipt["row"]["task"], receipt["status"], receipt["image_id"], flush=True)
            receipts.append(receipt)
    write_json(archive / "summary.json", {
        "plan_sha256": digest(plan_path), "expected": len(picks), "results": receipts,
        "ready": sum(record["image_id"] is not None for record in receipts),
    })


if __name__ == "__main__":
    main()
