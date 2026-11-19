#!/bin/bash
set -euo pipefail
umask 077
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ref=/mount-data/Claude-code-CLM/experiments/workbuddy-20261118
export PATH="/mount-data/yangyang-h20-2gpu-train-20261107/env/skill100-20261110/runtime/usr/bin:$PATH"
export DOCKER_HOST=unix:///var/docker/proxy/docker-proxy.sock
export DOCKER_CONFIG="$ref/docker-config"
export DOCKER_BUILDKIT=0
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$here/../../../framework:$here/../..:$here"
exec "$ref/.venv/bin/python" "$here/run.py" "$@"
