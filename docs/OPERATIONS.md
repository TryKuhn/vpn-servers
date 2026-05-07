# Operations Runbook

This document covers maintenance and recovery procedures for the VPN
server. It is intended for the operator (currently @TryKuhn). Most
commands assume SSH access as the `vpn` user.

## Architecture overview

- **Server**: Aeza HEL-1 Helsinki, IP `193.29.224.82`, Ubuntu 24.04
- **Domain**: `trykuhnvpn.duckdns.org`
- **Production path**: `/opt/vpn-servers` (owned by `deploy` user)
- **Services** (docker compose):
  - `xray` — VLESS Reality on port 443 (host network)
  - `manager` — FastAPI on `0.0.0.0:8080` (firewalled, internal only)
  - `nginx` — HTTPS reverse proxy on port 8443 (subscription endpoint)
- **Network**: ufw active, default deny incoming. Allowed: 22/tcp,
  80/tcp (ACME), 443/tcp (xray), 8443/tcp (nginx subscription).

## Backup

### How it works

A cron job runs `/opt/vpn-servers/scripts/backup.sh` daily at 03:00
UTC. It creates an unencrypted tarball of:
- `.env` (Reality keys, secrets)
- `data/users.json` (user list, UUIDs, subscription tokens)
- `data/xray/config.json` (xray runtime config)

Output: `/var/backups/vpn/vpn-state-YYYYMMDD-HHMMSS.tar.gz`.
Retention: 14 most recent archives. Mode `0400`, owned by root.

The archive is **not encrypted on the server**. Encryption is applied
when pulled to the operator's Windows machine via `pull-backup.cmd`.

### Manual backup (run now)

```bash
sudo /opt/vpn-servers/scripts/backup.sh
ls -la /var/backups/vpn/
```

### Pull backup to local machine

On Windows:

```cmd
set BACKUP_PASSPHRASE=<from password manager>
scripts\pull-backup.cmd
```

The encrypted file lands in `%USERPROFILE%\vpn-backups\`.

### Verify cron is working

```bash
sudo cat /var/log/vpn-backup.log
# Should show entries like "Backup created: /var/backups/vpn/vpn-state-..."
ls -la /var/backups/vpn/
# Should have 1-14 files dated within the last 14 days.
```

## Restore

### Scenario A: Same server, recover from local archive

Used when `.env` or `users.json` got corrupted but server is otherwise
healthy.

```bash
# 1. Stop services
cd /opt/vpn-servers
docker compose down

# 2. Restore from latest server-local backup
LATEST=$(ls -t /var/backups/vpn/vpn-state-*.tar.gz | head -1)
sudo tar xzf "$LATEST" -C /opt/vpn-servers

# 3. Start services
docker compose up -d

# 4. Verify
docker compose ps
docker compose logs --tail=20 xray manager nginx
```

### Scenario B: New server (disaster recovery)

The original VPS is gone. You need to rebuild on a fresh Ubuntu host.

```bash
# 1. Provision new VPS, get root SSH access. Create vpn user, lock root.
adduser vpn
usermod -aG sudo vpn
mkdir -p /home/vpn/.ssh
# Copy authorized_keys from password manager / backup
chown -R vpn:vpn /home/vpn/.ssh && chmod 700 /home/vpn/.ssh && chmod 600 /home/vpn/.ssh/authorized_keys
sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh

# 2. Install dependencies
apt update && apt install -y docker.io docker-compose-plugin git ufw fail2ban gnupg

# 3. Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8443/tcp
ufw enable

# 4. Clone repo
mkdir -p /opt && cd /opt
git clone https://github.com/TryKuhn/vpn-servers
chown -R deploy:deploy /opt/vpn-servers  # adjust if deploy user not yet created

# 5. Restore .env, users.json, xray config from your encrypted backup
# Copy your encrypted backup to the server first:
#   scp ~/vpn-backups/vpn-state-*.tar.gz.gpg vpn@<new-ip>:/tmp/

BACKUP_PASSPHRASE='<from password manager>' \
    /opt/vpn-servers/scripts/restore.sh /tmp/vpn-state-*.tar.gz.gpg

# 6. Start services
cd /opt/vpn-servers
docker compose pull
docker compose up -d

# 7. Update DNS (DuckDNS) to point to new IP
# Manually via DuckDNS web UI, or update via API call

# 8. Verify
docker compose ps
curl -k https://localhost:8443/health
ss -tulpn | grep -E "(443|8443|22)"

# 9. Notify users — subscription URL stays the same (token unchanged),
# but they may need to refresh subscription in their client.
```

### Scenario C: Lost SSH key but server is up

Use Aeza's web console (VNC) to log in as root with provider-issued
password, then add a new SSH key:

```bash
# Via VNC console:
mkdir -p /home/vpn/.ssh
echo "ssh-ed25519 AAAA... new-key" >> /home/vpn/.ssh/authorized_keys
chown vpn:vpn /home/vpn/.ssh/authorized_keys
chmod 600 /home/vpn/.ssh/authorized_keys
```

## User management

### Add user

```bash
# TODO: document actual API call once stabilized
# curl -X POST http://localhost:8080/users -d '{"name": "alice"}'
```

### Remove user

```bash
# TODO
```

### Rotate user UUID (suspected leak)

```bash
# TODO
```

## Key rotation

### Reality keys

**When**: suspected private key compromise. **Impact**: ALL clients
will need updated subscriptions.

```bash
# 1. Generate new Reality key pair
docker compose exec xray xray x25519
# Outputs Private/Public key pair

# 2. Update .env with new keys
# 3. Update data/xray/config.json with new private key + short_id
# 4. docker compose restart xray
# 5. All users must refresh subscription in their clients
```

### Subscription token (single user)

```bash
# TODO once API documented
```

## Monitoring & health

### Quick health check

```bash
# Services running?
docker compose ps

# Listening on expected ports?
sudo ss -tulpn | grep LISTEN

# TLS cert expiry?
echo | openssl s_client -servername trykuhnvpn.duckdns.org \
    -connect trykuhnvpn.duckdns.org:8443 2>/dev/null \
    | openssl x509 -noout -dates

# Recent xray logs (look for errors, not 'rejected')
docker compose logs --tail=100 xray | grep -iE "(error|fatal)"
```

### Resource usage

```bash
docker stats --no-stream
df -h /
free -h
```

## Common issues

### Subscription endpoint returns 404

Cause: nginx config drift, or 8443 firewalled.

```bash
sudo ufw status | grep 8443
docker compose logs --tail=50 nginx
docker compose restart nginx
```

### xray container won't start

Cause: usually invalid `data/xray/config.json` after manual edit.

```bash
docker compose logs xray
# Look for "config check failed" or JSON parse errors
# Restore config from backup:
sudo tar xzf /var/backups/vpn/vpn-state-*.tar.gz -C /opt/vpn-servers data/xray/config.json
docker compose restart xray
```

### TLS certificate expired

`jonasal/nginx-certbot` auto-renews. If failed:

```bash
docker compose logs --tail=200 nginx | grep -i certbot
docker compose exec nginx certbot renew --dry-run
```

### "Connection refused" from clients

```bash
# 1. xray running?
docker compose ps xray

# 2. Port 443 open?
sudo ss -tulpn | grep :443

# 3. ufw not blocking?
sudo ufw status | grep 443

# 4. Check xray logs for connection attempts
docker compose logs --tail=100 xray
```

## Emergency contacts

- **Hosting**: Aeza, support@aeza.net, https://aeza.net
- **Domain**: DuckDNS (free, no support); fallback domain procedure TBD
- **Operator**: @TryKuhn (Telegram)