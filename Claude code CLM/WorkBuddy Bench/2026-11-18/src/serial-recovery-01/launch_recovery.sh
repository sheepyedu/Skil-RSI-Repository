#!/bin/bash
# Reuse accepted trials and release task four only after the first-three audit.
set -euo pipefail
runner="$(cd "$(dirname "$0")" && pwd)"
experiment="$(dirname "$runner")"
source="$experiment/formal-02"
target="$experiment/formal-02-resume-01"
cd "$experiment"
umask 077
test ! -e "$target"
exec 9>"$experiment/formal-recovery-01.lock"
flock -n 9
test ! -e "$target"

status=0
"$runner/deploy-env.sh" "$runner/resume_formal.py" "$source" \
    --target "$target" --inspector "$runner/inspect_run.py" || status=$?
if [[ -d "$target" ]]; then
    printf '%s\n' "$status" > "$target/exit-status.txt"
    "$runner/deploy-env.sh" "$runner/audit_run.py" "$target" --save "$target/final-audit.json" \
        --inventory "$target/trajectory-sha256.json"
fi
exit "$status"
