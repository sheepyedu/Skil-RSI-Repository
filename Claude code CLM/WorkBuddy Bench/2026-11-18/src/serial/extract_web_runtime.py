"""Extract the exact browser-runtime layer prefix preceding the first task COPY."""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

SOURCE_TAG = "wb-clm-pilot-web:20261118"
BASE_TAG = "wb-clm-web-runtime:20261118"
EXPECTED_SOURCE_ID = "24aed792c07e739d0df126734b0133833760a6bfb67e1e5341f8e41ac94a424f"


def bytes_json(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


def add_bytes(archive, name, payload):
    member = tarfile.TarInfo(name)
    member.size = len(payload)
    archive.addfile(member, io.BytesIO(payload))


def main(source, output):
    with tarfile.open(source, "r:gz") as original:
        manifest = json.load(original.extractfile("manifest.json"))
        web = next(image for image in manifest if SOURCE_TAG in image["RepoTags"])
        config_raw = original.extractfile(web["Config"]).read()
        if hashlib.sha256(config_raw).hexdigest() != EXPECTED_SOURCE_ID:
            raise ValueError("Browser source image SHA mismatch")
        config = json.loads(config_raw)
        history = config["history"]
        boundary = next(i for i, entry in enumerate(history) if entry["created_by"].startswith("COPY workspace.tar.gz "))
        after = history[boundary:]
        if len(after) != 4 or not any("playwright install" in e["created_by"] for e in history[:boundary]):
            raise ValueError("Unexpected task layer boundary")
        if any("COPY " in e["created_by"] for e in history[:boundary]):
            raise ValueError("Unexpected COPY in browser runtime")
        layer_count = sum(not e.get("empty_layer", False) for e in history[:boundary])
        rootfs = config["rootfs"]["diff_ids"]
        if len(rootfs) != len(web["Layers"]):
            raise ValueError("OCI history and layer archive disagree")
        config["history"] = history[:boundary]
        config["rootfs"]["diff_ids"] = rootfs[:layer_count]
        config_raw = bytes_json(config)
        config_id = hashlib.sha256(config_raw).hexdigest()
        layers = web["Layers"][:layer_count]
        config_name = f"{config_id}.json"
        flat = {"Config": config_name, "RepoTags": [BASE_TAG], "Layers": layers}
        with tarfile.open(output, "w") as out:
            add_bytes(out, "manifest.json", bytes_json([flat]))
            add_bytes(out, config_name, config_raw)
            for name in layers:
                member = original.getmember(name)
                if not member.isfile():
                    raise ValueError("Browser layer entry is not a regular file")
                with original.extractfile(member) as content:
                    out.addfile(member, content)
    print(json.dumps({
        "source": SOURCE_TAG, "source_image_id": f"sha256:{EXPECTED_SOURCE_ID}",
        "runtime": BASE_TAG, "runtime_image_id": f"sha256:{config_id}",
        "rootfs": rootfs[:layer_count], "task_layers_excluded": len(web["Layers"]) - layer_count,
    }, indent=2))


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument("source", type=Path)
    args.add_argument("output", type=Path)
    values = args.parse_args()
    main(values.source, values.output)
