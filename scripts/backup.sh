#!/usr/bin/env bash
# Создаёт unencrypted локальный бекап критичных файлов.
# Шифрование делается на стороне клиента (pull-backup.cmd).
#
# Запускается из cron под root. Output: /var/backups/vpn/vpn-state-YYYYMMDD-HHMMSS.tar.gz
# Хранит последние 14 архивов, старые удаляет.

set -euo pipefail

BACKUP_DIR="/var/backups/vpn"
RETENTION_COUNT=14
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
ARCHIVE="${BACKUP_DIR}/vpn-state-${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

cd /opt/vpn-servers

# Tar critical files. Failure on any missing file is fatal.
tar czf "$ARCHIVE" \
    .env \
    data/users.json \
    data/xray/config.json

chmod 440 "$ARCHIVE"
chgrp backup-readers "$ARCHIVE"

# Rotate old backups (keep N most recent).
ls -1t "$BACKUP_DIR"/vpn-state-*.tar.gz \
    | tail -n +$((RETENTION_COUNT + 1)) \
    | xargs -r rm -f

echo "Backup created: $ARCHIVE"
