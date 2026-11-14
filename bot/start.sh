#!/usr/bin/env bash
# Start script for bot panels (Pterodactyl / ACLClouds / Waifly / cogithost).
# Upload the `bot/` folder as the server root and use this as the start command:
#     bash start.sh
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

# A local venv keeps pip working on hosts with PEP 668 ("externally managed").
if [ ! -x .venv/bin/python ]; then
  echo "◈ Creating virtualenv…"
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

exec .venv/bin/python UND.py
