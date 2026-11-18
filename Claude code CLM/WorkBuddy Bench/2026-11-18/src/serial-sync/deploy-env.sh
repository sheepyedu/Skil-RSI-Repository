#!/bin/bash
set -eu
experiment=/mount-data/Claude-code-CLM/experiments/workbuddy-20261118
export DOCKER_HOST=unix:///var/docker/proxy/docker-proxy.sock
export DOCKER_CONFIG="$experiment/docker-config"
export DOCKER_BUILDKIT=0
export PATH="/mount-data/yangyang-h20-2gpu-train-20261107/env/skill100-20261110/runtime/usr/bin:$PATH"
export PYTHONPATH="/mount-data/Claude-code-CLM:$experiment/serial-sync:$experiment/session-sync:/mount-data/Claude-code-CLM/experiments/clbench100-20261117/framework"
cd "$experiment"
exec "$experiment/.venv/bin/python" "$@"
