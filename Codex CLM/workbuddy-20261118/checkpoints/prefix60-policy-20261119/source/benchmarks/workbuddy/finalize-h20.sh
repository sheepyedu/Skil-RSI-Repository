#!/bin/bash
set -euo pipefail
umask 077

if (( $# != 4 )); then
  echo "Usage: finalize-h20.sh SOURCE PILOT FORMAL DELIVERY" >&2
  exit 2
fi
source_root="$1"
pilot="$2"
formal="$3"
delivery="$4"
base="$(dirname -- "$formal")"
audit="$base/audit_workbuddy.py"
runner="$source_root/benchmarks/workbuddy/h20.sh"

test -s "$pilot/accepted.json"
test -s "$base/pilot-audit/summary.json"
test -s "$base/capacity-probe/result.json"
python3 - "$base/capacity-probe/result.json" <<'PY'
import json, sys
with open(sys.argv[1]) as source:
    if not json.load(source)["accepted"]:
        raise SystemExit("Capacity probe did not pass")
PY

printf '%s\n' "$(date -Is)" >"$formal/controller.started"
if "$runner" run "$formal" --pilot-gate "$pilot"; then
  printf '0\n' >"$formal/controller.exit"
else
  rc=$?
  printf '%s\n' "$rc" >"$formal/controller.exit"
  exit "$rc"
fi

if python3 "$audit" "$formal" "$delivery" --all-attempts "$base"/pilot-[0-9][0-9] "$base/capacity-probe"; then
  printf '0\n' >"$formal/audit.exit"
else
  rc=$?
  printf '%s\n' "$rc" >"$formal/audit.exit"
  exit "$rc"
fi
printf '%s\n' "$(date -Is)" >"$formal/controller.finished"
