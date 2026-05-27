#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
DEST="backups/$TS"
mkdir -p "$DEST"
echo "→ backing up files to $DEST"
cp -a .env "$DEST/.env" 2>/dev/null || true
cp -a certs "$DEST/certs" 2>/dev/null || true
cp -a rendered "$DEST/rendered" 2>/dev/null || true
cp -a docker-compose.yml Dockerfile Makefile alembic.ini "$DEST/" 2>/dev/null || true
cp -a manager migrations scripts "$DEST/" 2>/dev/null || true
git rev-parse HEAD > "$DEST/git-commit.txt" 2>/dev/null || true
docker compose ps > "$DEST/docker-ps.txt" 2>/dev/null || true
docker inspect vpn-manager vpn-xray vpn-haproxy vpn-hysteria vpn-naive vpn-postgres > "$DEST/docker-inspect.json" 2>/dev/null || true
echo "→ backing up postgres"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-vpn}" "${POSTGRES_DB:-vpn}" > "$DEST/postgres.sql" 2>/dev/null || echo "WARN: pg_dump failed"
ARCHIVE="backups/trykuhn-vpn-backup-$TS.tar.gz"
tar -czf "$ARCHIVE" -C backups "$TS"
rm -rf "$DEST"
echo "✓ backup created: $ARCHIVE"
