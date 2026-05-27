#!/usr/bin/env bash
set -euo pipefail
docker compose run --rm manager python -m manager.cli render-configs
echo "→ rendered files"
find rendered -maxdepth 3 -type f -print
