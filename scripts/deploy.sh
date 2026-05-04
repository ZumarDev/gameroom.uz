#!/usr/bin/env bash

set -euo pipefail

BRANCH="${1:-main}"
SERVICE_NAME="${2:-gameroom.service}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${APP_DIR}/.venv"

echo "[deploy] app dir: ${APP_DIR}"
echo "[deploy] branch: ${BRANCH}"

cd "${APP_DIR}"

if [ ! -d "${VENV_DIR}" ]; then
  python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"
python -m pip install --upgrade pip
pip install -r requirements.txt

python -m compileall .

SYSTEMCTL_BIN=""
if command -v sudo >/dev/null 2>&1; then
  SYSTEMCTL_BIN="sudo systemctl"
elif [ "$(id -u)" -eq 0 ]; then
  SYSTEMCTL_BIN="systemctl"
fi

if [ -n "${SYSTEMCTL_BIN}" ] && ${SYSTEMCTL_BIN} cat "${SERVICE_NAME}" >/dev/null 2>&1; then
  ${SYSTEMCTL_BIN} restart "${SERVICE_NAME}"
  ${SYSTEMCTL_BIN} status "${SERVICE_NAME}" --no-pager
else
  echo "[deploy] warning: unable to restart ${SERVICE_NAME}; install sudo for the deploy user or run as root"
fi
