#!/bin/sh
set -eu

RUNTIME_HOME="${SFLOWRT_HOME:-/var/lib/nsddos/sflowrt}"
STORE_DIR="${RUNTIME_HOME}/store"

mkdir -p "${STORE_DIR}"

if [ -z "$(ls -A "${STORE_DIR}" 2>/dev/null)" ]; then
  cp -R /opt/nsddos-seed/store/. "${STORE_DIR}/"
fi

rm -rf /opt/nsddos/store
ln -s "${STORE_DIR}" /opt/nsddos/store

exec sh /opt/nsddos/start.sh
