#!/usr/bin/env bash
# Восстанавливает .env, users.json, xray config из шифрованного бекапа.
#
# Usage: BACKUP_PASSPHRASE=xxx ./restore.sh /path/to/vpn-state-*.tar.gz.gpg

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: BACKUP_PASSPHRASE=xxx $0 /path/to/vpn-state-*.tar.gz.gpg" >&2
    exit 1
fi

ENCRYPTED="$1"
TARGET_DIR="${TARGET_DIR:-/opt/vpn-servers}"

if [[ -z "${BACKUP_PASSPHRASE:-}" ]]; then
    echo "ERROR: BACKUP_PASSPHRASE env var not set" >&2
    exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
    echo "ERROR: $TARGET_DIR does not exist. Clone repo first:" >&2
    echo "  git clone https://github.com/TryKuhn/vpn-servers $TARGET_DIR" >&2
    exit 1
fi

DECRYPTED=$(mktemp /tmp/vpn-restore-XXXXXX.tar.gz)
trap "rm -f $DECRYPTED" EXIT

echo "Decrypting $ENCRYPTED..."
echo "$BACKUP_PASSPHRASE" | gpg --batch --yes --passphrase-fd 0 \
    --decrypt --output "$DECRYPTED" "$ENCRYPTED"

echo "Extracting to $TARGET_DIR..."
tar xzf "$DECRYPTED" -C "$TARGET_DIR"

echo "Done. Verify with:"
echo "  ls -la $TARGET_DIR/.env $TARGET_DIR/data/users.json"
echo "Then restart services:"
echo "  cd $TARGET_DIR && docker compose down && docker compose up -d"
