#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# UND — All In One · one-shot installer for Debian / Ubuntu VPS (incl. Oracle
# Cloud Always Free ARM). Installs the bot as a systemd service that restarts
# itself forever.
#
#   sudo bash deploy/install.sh
#
# Override defaults with env vars:
#   APP_DIR=/opt/und  SERVICE_USER=und  REPO_DIR=$(pwd)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/und}"
SERVICE_NAME="${SERVICE_NAME:-und-bot}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "✖ run me with sudo: sudo bash deploy/install.sh" >&2
  exit 1
fi

echo "◈ Installing system packages (python 3, venv, ffmpeg for music)…"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ffmpeg rsync curl

echo "◈ Creating service user…"
if ! id -u und >/dev/null 2>&1; then
  useradd --system --create-home --shell /usr/sbin/nologin und
fi

echo "◈ Copying project to ${APP_DIR} …"
mkdir -p "${APP_DIR}"
rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude 'node_modules' \
  --exclude '.next' \
  "${REPO_DIR}/bot/" "${APP_DIR}/bot/"

if [[ ! -f "${APP_DIR}/bot/.env" ]]; then
  cp "${APP_DIR}/bot/.env.example" "${APP_DIR}/bot/.env"
  echo "⚠  ${APP_DIR}/bot/.env was created from .env.example — fill in TOKEN and OWNER_IDS."
fi

echo "◈ Creating virtualenv and installing requirements…"
python3 -m venv "${APP_DIR}/bot/.venv"
"${APP_DIR}/bot/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/bot/.venv/bin/pip" install -r "${APP_DIR}/bot/requirements.txt"

chown -R und:und "${APP_DIR}"
chmod 600 "${APP_DIR}/bot/.env"

echo "◈ Installing systemd service…"
install -m 644 "${REPO_DIR}/deploy/und-bot.service" "/etc/systemd/system/${SERVICE_NAME}.service"
sed -i "s|/opt/und|${APP_DIR}|g" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"

if grep -q '^TOKEN=$' "${APP_DIR}/bot/.env" || ! grep -q '^TOKEN=..*' "${APP_DIR}/bot/.env"; then
  echo "✖ ${APP_DIR}/bot/.env has no TOKEN yet — add it, then start the bot:"
  echo "     sudo nano ${APP_DIR}/bot/.env"
  echo "     sudo systemctl start ${SERVICE_NAME}"
  exit 0
fi

systemctl restart "${SERVICE_NAME}"
echo "✔ Done. Follow the logs with:  journalctl -u ${SERVICE_NAME} -f"
