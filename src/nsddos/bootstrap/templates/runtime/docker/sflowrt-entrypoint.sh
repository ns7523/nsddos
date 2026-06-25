#!/usr/bin/env bash
set -euo pipefail

if [ ! -d /var/lib/nsddos/sflowrt/store ]; then
  mkdir -p /var/lib/nsddos/sflowrt
  cp -R /opt/nsddos-seed/store /var/lib/nsddos/sflowrt/store
fi

cd /opt/nsddos
exec /opt/nsddos/start.sh
