#!/usr/bin/env bash
set -euo pipefail
if [ ! -f .env ]; then cp .env.example .env; echo "→ Created .env from .env.example"; fi
XRAY_IMAGE="ghcr.io/xtls/xray-core:${XRAY_VERSION:-latest}"
echo "→ Generating Reality x25519 keys using $XRAY_IMAGE"
KEYS=$(docker run --rm "$XRAY_IMAGE" x25519)
PRIVATE_KEY=$(echo "$KEYS" | awk -F': ' '/Private key/ {print $2}')
PUBLIC_KEY=$(echo "$KEYS" | awk -F': ' '/Public key/ {print $2}')
SHORT_ID=$(openssl rand -hex 8)
FALLBACK_PASSWORD=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '=')
export PRIVATE_KEY PUBLIC_KEY SHORT_ID FALLBACK_PASSWORD POSTGRES_PASSWORD
python3 - <<'PY_SCRIPT'
from pathlib import Path
import os
p = Path('.env')
s = p.read_text()
private = os.environ['PRIVATE_KEY']
public = os.environ['PUBLIC_KEY']
short_id = os.environ['SHORT_ID']
fallback = os.environ['FALLBACK_PASSWORD']
pg = os.environ['POSTGRES_PASSWORD']
repls = {
    'REALITY_PRIVATE_KEY=': private,
    'REALITY_PUBLIC_KEY=': public,
    'REALITY_SHORT_ID=': short_id,
    'FALLBACK_AUTH_PASSWORD=': fallback,
    'POSTGRES_PASSWORD=': pg,
}
lines = []
for line in s.splitlines():
    done = False
    for key, value in repls.items():
        if line.startswith(key):
            lines.append(key + value)
            done = True
            break
    if not done and line.startswith('DATABASE_URL='):
        lines.append(f'DATABASE_URL=postgresql+asyncpg://vpn:{pg}@postgres:5432/vpn')
        done = True
    if not done:
        lines.append(line)
p.write_text('\n'.join(lines) + '\n')
PY_SCRIPT
echo "✓ .env updated with Reality keys, shortId and random fallback/db passwords"
echo "  Public key: $PUBLIC_KEY"
echo "  Short ID:   $SHORT_ID"
