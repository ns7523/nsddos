#!/usr/bin/env bash
set -euo pipefail

service openvswitch-switch start >/dev/null 2>&1 || true

tail -f /dev/null
