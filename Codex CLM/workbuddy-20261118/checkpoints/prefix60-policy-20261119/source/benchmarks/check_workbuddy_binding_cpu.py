"""Use real first-pair bytes to test binding checks without making model calls."""

import argparse
import contextlib
import copy
import io
import json
import shutil
import tempfile
from pathlib import Path

from check_workbuddy_binding import check, load, sha


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def fixture(source, target):
    rows = load(source / "progress.json")[:2]
    if [(r["row"]["position"], r["arm"]) for r in rows] != [(1, "native"), (1, "clm")]:
        raise ValueError("The real first completed pair is required")
    write(target / "plan.json", {"tasks": [rows[0]["row"]]})
    write(target / "progress.json", rows)
    for progress in rows:
        arm, row = progress["arm"], progress["row"]
        key = f"001-{row['domain']}-{row['task']}"
        origin = source / arm / "evidence" / key
        receipt = load(origin / "receipt.json")
        index, wire = next((i, w) for i, w in enumerate(receipt["wire"]["records"], 1)
                           if w.get("path") == "/v1/responses" and w.get("complete"))
        receipt = copy.deepcopy(receipt)
        receipt["wire"]["records"] = [wire]
        dest = target / arm / "evidence" / key
        write(dest / "receipt.json", receipt)
        folder = dest / "wire/00001"
        folder.mkdir(parents=True)
        for name in ("request.raw.json", "request.sent.json", "response.raw"):
            shutil.copyfile(origin / "wire" / f"{index:05d}" / name, folder / name)
        agent = target / arm / "trials" / receipt["trial_name"] / "agent"
        agent.mkdir(parents=True)
        for name in ("native-result.json", "native.jsonl", "instruction-source.md", "prompt-model.txt"):
            shutil.copyfile(source / arm / "trials" / receipt["trial_name"] / "agent" / name, agent / name)
    return {r["arm"]: r["thread"] for r in rows}


def rejected(action, expected):
    try:
        action()
    except ValueError as error:
        if expected not in str(error):
            raise AssertionError(f"Unexpected rejection: {error}") from error
    else:
        raise AssertionError("Invalid binding was accepted")


def main(source, output):
    tests = []
    with tempfile.TemporaryDirectory(prefix="wb-binding-cpu-") as temporary:
        root = Path(temporary)
        valid = root / "valid"
        expected = fixture(source, valid)
        with contextlib.redirect_stdout(io.StringIO()):
            check(valid, valid / "proof.json", False, expected)
        assert load(valid / "proof.json")["selected_trials_verified"] == 2
        tests.append("real first-pair RPC, native completion and raw/sent Responses bytes agree")

        wrong = root / "wrong-instruction"
        fixture(source, wrong)
        rows = load(wrong / "progress.json")
        for row in rows:
            agent = wrong / row["arm"] / "trials" / row["trial_name"] / "agent"
            path = agent / "instruction-source.md"
            path.write_bytes(path.read_bytes() + b"\nBINDING_FIXTURE_SENTINEL\n")
            row["row"]["instruction_sha256"] = sha(path)
            evidence = wrong / row["arm"] / "evidence" / f"001-{row['row']['domain']}-{row['row']['task']}"
            receipt = load(evidence / "receipt.json")
            receipt["row"] = row["row"]
            write(evidence / "receipt.json", receipt)
        write(wrong / "progress.json", rows)
        write(wrong / "plan.json", {"tasks": [rows[0]["row"]]})
        rejected(lambda: check(wrong, wrong / "proof.json", False, expected), "Completed native turn")
        tests.append("reject altered instruction despite matching recomputed plan and receipt hashes")

        wrong = root / "wrong-api"
        fixture(source, wrong)
        row = load(wrong / "progress.json")[0]
        evidence = wrong / "native/evidence" / f"001-{row['row']['domain']}-{row['row']['task']}"
        path = evidence / "wire/00001/request.sent.json"
        payload = load(path)
        for item in payload["input"]:
            if item.get("role") == "user":
                item["content"] = "[WB_CODEX_FORMAL_001] BINDING_FIXTURE_WRONG_QUESTION"
        write(path, payload)
        receipt = load(evidence / "receipt.json")
        receipt["wire"]["records"][0]["sent_sha256"] = sha(path)
        write(evidence / "receipt.json", receipt)
        rejected(lambda: check(wrong, wrong / "proof.json", False, expected), "No actual successful raw/sent")
        tests.append("reject different API question even with recomputed transport hash")

        rejected(lambda: check(valid, valid / "full.json", True, expected), "full65/130 contract")
        tests.append("reject a two-trial fixture as a final65/130 result")
    result = {"scope": "CPU qualification using copied real first-pair evidence and explicit tamper fixtures",
              "model_api_calls": 0, "checks": tests, "passed": len(tests),
              "checker_sha256": sha(Path(__file__).with_name("check_workbuddy_binding.py")),
              "qualification_source_sha256": sha(Path(__file__))}
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.source, args.output)
