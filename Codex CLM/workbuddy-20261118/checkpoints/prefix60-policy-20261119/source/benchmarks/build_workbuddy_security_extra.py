"""Build the supplement in its own dataset copy, retaining official recipe hashes."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import toml

ROOT = Path("/mount-data/Codex-CLM/experiments/workbuddy-codex-20261118/security-extra")


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def main():
    plan=json.loads((ROOT/"plan.json").read_text())
    evidence=ROOT/"image-builds"
    evidence.mkdir(exist_ok=True)
    receipts=[]
    progress=ROOT/"build-progress.json"
    previous=json.loads(progress.read_text()) if progress.exists() else []
    cached=ROOT/"cache/ghidra_12.0_PUBLIC_20251205.zip"
    verified=json.loads((ROOT/"cache/VERIFIED.json").read_text())
    if (not verified["official_digest_match"] or not verified["crc_all_passed"]
            or sha(cached)!=verified["sha256"]):
        raise ValueError("Ghidra cache does not match the official release digest")
    for row in plan["tasks"]:
        task=ROOT/"datasets/wb-bench-sec-v1.0/tasks"/row["task"]
        source=task/"environment"
        original=source/"Dockerfile"
        if sha(original)!=row["dockerfile_sha256"]:
            raise ValueError("Official Dockerfile changed")
        cached_copy=source/"codex-cache-ghidra.zip"
        if not cached_copy.exists():
            os.link(cached,cached_copy)
        if sha(cached_copy)!=verified["sha256"]:
            raise ValueError("Build context Ghidra cache changed")
        folder=evidence/f"{row['position']:03d}-{row['task']}"
        folder.mkdir(exist_ok=True)
        lines=[]
        for line in original.read_text().splitlines(keepends=True):
            lines.append(line)
            if line.upper().startswith("FROM "):
                lines.append("ARG JOBS=4\n")
                lines.append("COPY --from=python:3.11.11-slim-bookworm /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt\n")
                lines.append("RUN sed -i 's@http://deb.debian.org@https://mirrors.aliyun.com@g;s@http://archive.ubuntu.com@https://mirrors.aliyun.com@g;s@http://security.ubuntu.com@https://mirrors.aliyun.com@g' /etc/apt/sources.list.d/*.sources /etc/apt/sources.list 2>/dev/null || true\n")
                lines.append("ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple\n")
        recipe=folder/"Dockerfile"
        combined="".join(lines)
        download="RUN wget -q https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.0_build/ghidra_12.0_PUBLIC_20251205.zip \\\n"
        if combined.count(download)!=1:
            raise ValueError("Official Ghidra download recipe differs from the reviewed fixed URL")
        combined=combined.replace(download,
            "COPY codex-cache-ghidra.zip /opt/ghidra_12.0_PUBLIC_20251205.zip\n"
            "RUN printf '%s  %s\\n' '"+verified["sha256"]+"' ghidra_12.0_PUBLIC_20251205.zip | sha256sum -c - \\\n")
        jdk_sha=None
        jdk_context=None
        if "https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jdk/hotspot/normal/eclipse?project=jdk" in combined:
            jdk=json.loads((ROOT/"cache/JDK21_VERIFIED.json").read_text())
            jdk_cache=ROOT/"cache/jdk21.tar.gz"
            if not jdk["official_digest_match"] or sha(jdk_cache)!=jdk["sha256"]:
                raise ValueError("JDK cache does not match the official resolved release")
            jdk_sha=jdk["sha256"]
            jdk_context=source/"codex-cache-jdk21.tar.gz"
            if not jdk_context.exists(): os.link(jdk_cache,jdk_context)
            if sha(jdk_context)!=jdk_sha: raise ValueError("JDK build context changed")
            install="RUN apt-get update && apt-get install -y --no-install-recommends \\\n    curl \\\n    wget \\\n    unzip \\\n"
            fetch='    && curl -fsSL "'+jdk["original_url"]+'" \\\n        -o /tmp/jdk21.tar.gz \\\n'
            if combined.count(install)!=1 or combined.count(fetch)!=1:
                raise ValueError("Official JDK recipe differs from the reviewed download")
            combined=combined.replace(install,"COPY codex-cache-jdk21.tar.gz /tmp/jdk21.tar.gz\n"+install)
            combined=combined.replace(fetch,"    && printf '%s  %s\\n' '"+jdk_sha+"' /tmp/jdk21.tar.gz | sha256sum -c - \\\n")
        recipe.write_text(combined)
        image=f"wb-codex-quarter-{row['position']:03d}:"+sha(recipe)[:16]
        prior=next((r for r in previous if r.get("image")==image and r.get("exit")==0
                    and r.get("image_id") and r.get("build_recipe_sha256")==sha(recipe)),None)
        if prior:
            observed=subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",image],text=True).strip()
            if observed!=prior["image_id"]: raise ValueError("Previously completed image changed")
            if toml.loads((task/"task.toml").read_text())["environment"]["docker_image"]!=image:
                raise ValueError("Previously completed task image configuration changed")
            (folder/"receipt.json").write_text(json.dumps({**prior,"reuse_verified":True},indent=2)+"\n")
            receipts.append(prior)
            progress.write_text(json.dumps(receipts,indent=2)+"\n")
            cached_copy.unlink()
            if jdk_context: jdk_context.unlink()
            print(row["task"],"reused",observed,flush=True)
            continue
        started=time.time()
        with (folder/"build.log").open("wb") as out:
            try:
                code=subprocess.run(
                    ["docker","build","--memory","8g","--cpu-quota","400000",
                     "--label","workbuddy.codex.supplement=true","--file",str(recipe),
                     "--tag",image,str(source)],stdout=out,stderr=subprocess.STDOUT,timeout=1800).returncode
            except subprocess.TimeoutExpired:
                code=124
        cached_copy.unlink()
        if jdk_context: jdk_context.unlink()
        ident=None
        if not code:
            ident=subprocess.check_output(["docker","image","inspect","--format","{{.Id}}",image],text=True).strip()
            cfg=toml.loads((task/"task.toml").read_text())
            cfg["environment"]["docker_image"]=image
            (task/"task.toml").write_text(toml.dumps(cfg))
        receipt={"row":row,"image":image,"image_id":ident,"exit":code,
                 "official_dockerfile_sha256":sha(original),"build_recipe_sha256":sha(recipe),
                 "ghidra_release_sha256":verified["sha256"],
                 "jdk21_release_sha256":jdk_sha,
                 "seconds":time.time()-started}
        (folder/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
        receipts.append(receipt)
        (ROOT/"build-progress.json").write_text(json.dumps(receipts,indent=2)+"\n")
        print(row["task"],code,ident,flush=True)
    raise SystemExit(0 if all(x["image_id"] for x in receipts) else 1)


if __name__=="__main__":
    main()
