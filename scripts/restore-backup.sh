#!/usr/bin/env bash
set -euo pipefail
ARCHIVE=${1:-}
if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then echo "Usage: scripts/restore-backup.sh backups/trykuhn-vpn-backup-YYYYmmddTHHMMSSZ.tar.gz"; exit 1; fi
TMP=$(mktemp -d)
tar -xzf "$ARCHIVE" -C "$TMP"
SNAP=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -1)
cp -a "$SNAP/.env" .env 2>/dev/null || true
cp -a "$SNAP/certs" . 2>/dev/null || true
cp -a "$SNAP/rendered" . 2>/dev/null || true
if [ -f "$SNAP/postgres.sql" ]; then
  docker compose up -d postgres
  echo "→ waiting for postgres"
  sleep 5
  docker compose exec -T postgres psql -U "${POSTGRES_USER:-vpn}" -d "${POSTGRES_DB:-vpn}" < "$SNAP/postgres.sql"
fi
rm -rf "$TMP"
echo "✓ restore done"
