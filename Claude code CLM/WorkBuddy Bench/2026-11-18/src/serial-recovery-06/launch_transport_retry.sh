#!/bin/bash
set -euo pipefail
runner="$(cd "$(dirname "$0")" && pwd)"
experiment="$(dirname "$runner")"
source="$experiment/formal-02-resume-05"
target="$experiment/formal-02-resume-06"
cd "$experiment"
umask 077
exec 9>"$experiment/formal-recovery-06.lock"
flock -n 9
test ! -e "$target"

status=0
"$runner/deploy-env.sh" "$runner/retry_transport_pair.py" "$source" \
    --position 27 --target "$target" --inspector "$runner/inspect_run.py" \
    --maintenance-log "$experiment/formal-recovery-05.controller.log" || status=$?
if [[ -d "$target" ]]; then
    printf '%s\n' "$status" > "$target/exit-status.txt"
    "$runner/deploy-env.sh" "$runner/audit_run.py" "$target" --save "$target/final-audit.json" \
        --inventory "$target/trajectory-sha256.json"
fi
exit "$status"
