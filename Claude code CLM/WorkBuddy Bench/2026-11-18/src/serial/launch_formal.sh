#!/bin/bash
# This starts the formal experiment only after the four paired pilot tasks
# and each frozen task image have been verified.
set -euo pipefail
experiment=/mount-data/Claude-code-CLM/experiments/workbuddy-20261118
pilot="${1:?Expected the accepted pilot directory}"
formal="${2:?Expected the frozen formal directory}"
run="$experiment/serial/deploy-env.sh"
cd "$experiment"
umask 077
"$run" serial/qualify.py "$pilot" "$formal" "$formal/qualification.json"

status=0
"$run" serial/run_pair.py execute \
    --experiment "$experiment" --run "$formal" --stage formal \
    --pilot-ok "$pilot/accepted.json" || status=$?

printf '%s\n' "$status" > "$formal/exit-status.txt"
"$run" serial/audit_run.py "$formal" --save "$formal/final-audit.json" \
    --inventory "$formal/trajectory-sha256.json"
exit "$status"
