"""Create an unscored infrastructure check for the session and retention wiring."""

import hashlib
import sys
from pathlib import Path

from wire import write_json


def main(run):
    run.mkdir(parents=True)
    (run / "offline.yaml").write_text("services:\n  main:\n    network_mode: none\n")
    rows = []
    instructions = (
        "Remember the exact codeword LIME-ASTER-7241 for the next task. Use Bash to print "
        "a numbered sequence from 1 to 100, use Bash again to print a second short line, "
        "and then write OK to /logs/artifacts/probe.txt. If your system instructions "
        "expose the CLM tool, call clm-context status, drop an eligible sequence-printing "
        "exchange, and add the codeword to your own memory note. Read the artifact "
        "back with Bash or Read before finishing.",
        "Recall the exact codeword from the prior task. Write the codeword to "
        "/logs/artifacts/probe.txt. Use Bash and verify it is there before finishing.",
    )
    for position, prompt in enumerate(instructions, start=1):
        name = f"plumbing-{position}"
        marker = f"WB_SERIAL_TASK_SYNTHETIC_{position}"
        task = run / "datasets" / "wb-bench-code-v1.0" / "tasks" / name
        (task / "tests").mkdir(parents=True)
        (task / "environment").mkdir()
        (task / "environment" / "Dockerfile").write_text("FROM python:3.12-slim\n")
        (task / "instruction.md").write_text(prompt + "\n")
        (task / "task.toml").write_text(
            'schema_version = "1.3"\n[agent]\nuser = "dev"\ntimeout_sec = 300\n'
            '[verifier]\nuser = "root"\ntimeout_sec = 120\n'
            '[environment]\ndocker_image = "python:3.12-slim"\ncpus = 2\nmemory_mb = 2048\n'
        )
        expected = "OK" if position == 1 else "LIME-ASTER-7241"
        (task / "tests" / "test.sh").write_text(
            "#!/bin/sh\nmkdir -p /logs/verifier\n"
            f'test "$(cat /logs/artifacts/probe.txt)" = "{expected}" && result=1 || result=0\n'
            'printf "%s\\n" "$result" > /logs/verifier/reward.txt\n'
        )
        rows.append({
            "position": position, "domain": "code", "task": name,
            "instruction_sha256": hashlib.sha256((task / "instruction.md").read_bytes()).hexdigest(),
            "marker": marker,
        })
    write_json(run / "plan.json", {"stage": "plumbing", "tasks": rows})


if __name__ == "__main__":
    main(Path(sys.argv[1]))
