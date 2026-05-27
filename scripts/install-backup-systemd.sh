#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_PATH=/etc/systemd/system/trykuhn-vpn-backup.service
TIMER_PATH=/etc/systemd/system/trykuhn-vpn-backup.timer

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo ./scripts/install-backup-systemd.sh" >&2
  exit 1
fi

cat > "$SERVICE_PATH" <<EOF_SERVICE
[Unit]
Description=Backup trykuhn VPN stack
Wants=docker.service
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=${ROOT_DIR}
ExecStart=${ROOT_DIR}/scripts/backup.sh
EOF_SERVICE

cat > "$TIMER_PATH" <<'EOF_TIMER'
[Unit]
Description=Run trykuhn VPN backup daily

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
EOF_TIMER

systemctl daemon-reload
systemctl enable --now trykuhn-vpn-backup.timer
systemctl list-timers trykuhn-vpn-backup.timer --no-pager
