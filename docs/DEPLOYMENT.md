# Deployment Guide

Step-by-step instructions for deploying a new VPN server from scratch.

## Prerequisites

- A Linux VPS (tested on **Ubuntu 22.04 / 24.04**, x86_64).
- Root or sudo access.
- A public IPv4 address.
- Open ports `22/tcp` (SSH) and `443/tcp` (VPN).

**Recommended specs:**
- 1 vCPU, 1 GB RAM minimum (2 GB comfortable).
- 10 GB disk.
- 1 Gbps network preferred, but anything ≥100 Mbps works fine.
- Geographic location outside your users' region (Finland, Germany, Netherlands
  for Russian users).

## Quick reference

If you've done this before, here's the abbreviated flow:

```bash
ssh root@YOUR_VPS_IP
git clone https://github.com/TryKuhn/vpn-servers.git
cd vpn-servers
sudo make install
cp .env.example .env
nano .env                  # edit SERVER_IP, SNI, etc.
make init                  # generates Reality keys
make up
make shell-manager
vpn-user add alice
```

Done. The rest of this document explains each step.

## Step-by-step

### 1. Connect to the VPS

After your provider gives you SSH credentials:

```bash
ssh root@YOUR_VPS_IP
```

If you get a `host key has changed` warning (e.g. after a fresh OS install on
the same IP), clear the old key locally:

```bash
ssh-keygen -R YOUR_VPS_IP
```

### 2. Clone the repository

```bash
git clone https://github.com/TryKuhn/vpn-servers.git
cd vpn-servers
```

### 3. Bootstrap the server

This installs Docker, UFW, and other dependencies. Idempotent — safe to run
multiple times.

```bash
sudo make install
```

What it does:
- Updates apt and installs base packages (`jq`, `qrencode`, `git`, `make`).
- Installs Docker CE and Docker Compose plugin.
- Configures UFW: opens `22/tcp` (SSH) and `443/tcp` (VPN), enables firewall.
- Adds the invoking user to the `docker` group.

If you ran with `sudo`, **disconnect and reconnect** to pick up docker group
membership:

```bash
exit
ssh root@YOUR_VPS_IP
cd vpn-servers
```

Verify Docker works without sudo:

```bash
docker ps
# Should print column headers without errors
```

### 4. Configure environment

Copy the example env file and edit it:

```bash
cp .env.example .env
nano .env
```

Required fields to set:

```bash
SERVER_IP=YOUR_VPS_IP            # e.g. 193.29.224.82
SERVER_PORT=443                  # default; change only if 443 is taken
SNI=gateway.icloud.com           # the "mask" domain (see below)
DEST=gateway.icloud.com:443      # usually ${SNI}:443
COUNTRY_FLAG=🇫🇮                  # match your VPS location
SERVER_TAG=YourBrandName         # appears in client app entries
```

Leave the keys empty — `make init` fills them in next.

#### Choosing an SNI domain

The SNI is the website your VPN traffic will pretend to be visiting. It must:

- Support **TLS 1.3** and **HTTP/2**.
- **Not be blocked** in your users' region (test before committing!).
- Have **plausible traffic patterns** (your users might realistically visit it).

Recommended for Russian users:

| Domain                  | Why |
|-------------------------|-----|
| `gateway.icloud.com`    | Apple, fast worldwide, never blocked |
| `www.yahoo.com`         | Stable, popular enough |
| `www.swift.com`         | Banking, never blocked |

To verify a domain works for Reality, run from your VPS:

```bash
curl -sI --tlsv1.3 --tls-max 1.3 --http2 https://gateway.icloud.com 2>&1 | grep -E "HTTP/|ALPN"
```

The response must include `HTTP/2` (not `HTTP/1.1`).

### 5. Generate Reality keys

```bash
make init
```

This generates:
- `PRIVATE_KEY` (kept on the server)
- `PUBLIC_KEY` (used in client links)
- `SHORT_ID` (random 8-byte identifier)

The values are written to `.env`. Do not commit `.env` — it's gitignored
already.

### 6. Start the server

```bash
make up
```

First run downloads images and builds the manager (~2-3 minutes). Subsequent
runs are <10 seconds.

Verify everything's running:

```bash
make status
```

Expected output:

```
NAME              STATUS
vpn-config-init   Exited (0)
vpn-data-init     Exited (0)
vpn-xray          Up X seconds (healthy)
vpn-manager       Up X seconds
```

Both `Exited (0)` are correct — those are one-shot init containers.

### 7. Verify xray is reachable from outside

From your local machine (not the VPS):

```bash
curl -v --tlsv1.3 --tls-max 1.3 https://YOUR_VPS_IP:443
# (will fail to handshake without proper Reality params, but should
#  reach the server and start TLS)
```

If it hangs, check your VPS provider's firewall — some providers (Aeza,
Hetzner) have an external firewall in addition to UFW.

### 8. Add the first user

```bash
make shell-manager
vpn-user add alice
```

You'll see a VLESS link and a QR code. Send either to the user; they import
it into V2RayTun (Android), Hiddify (iOS/macOS), or v2rayN (Windows).

To exit the manager shell: `exit`.

## Day-to-day operations

### Add a user

```bash
make shell-manager
vpn-user add bob
exit
```

Or in one command from outside:

```bash
docker compose exec manager vpn-user add bob
```

### Add multiple users at once

```bash
docker compose exec manager vpn-user add charlie diana
```

### List users

```bash
docker compose exec manager vpn-user list
```

### Show a user's link again

If a user lost their QR or link:

```bash
docker compose exec manager vpn-user show bob
```

### Remove a user

```bash
docker compose exec manager vpn-user remove bob
```

The user's connection is severed immediately, no xray restart needed.

### Resync after a server reboot

xray's runtime state is wiped on container restart, but `users.json` survives.
Restore the runtime state from the file:

```bash
docker compose exec manager vpn-user sync
```

This is normally **automatic** — `make up` restarts everything cleanly. Only
needed if you manually messed with xray's runtime.

## Updating the server

Pull the latest code and restart:

```bash
cd ~/vpn-servers
git pull
make up
```

If only the manager changed:

```bash
make rebuild-manager
```

If only the xray config template changed:

```bash
make down && make up
```

## Troubleshooting

### `make status` shows `vpn-xray (unhealthy)`

Check the logs:

```bash
make logs-xray
```

Common causes:
- `PRIVATE_KEY` is empty — run `make init`.
- Port 443 is already in use by another service.
- Reality validation failed against the SNI domain.

### `vpn-user add` fails with permission denied

The data directory has wrong ownership. Fix:

```bash
sudo chown -R 1000:1000 ./data
make restart
```

(This is normally fixed automatically by the `data-init` container, but a
manual fix never hurts.)

### Users can connect but no internet

Check that the SNI domain is reachable from the VPS:

```bash
curl -I https://gateway.icloud.com
```

Also check that the VPS can route traffic out:

```bash
docker compose exec xray sh -c "wget -qO- https://1.1.1.1"
```

### gRPC / manager errors

```bash
make logs-manager
```

If you see `Cannot reach xray at 127.0.0.1:10085`, xray isn't running. Check
`make status` and `make logs-xray`.

## Backing up

Critical state lives in `./data/`:

```bash
data/
├── users.json          # user database — back this up!
└── xray/
    └── config.json     # regenerated from .env, no need to back up
```

Plus `.env` — contains the Reality private key. Without it, existing user
links stop working. Back up:

```bash
tar czf vpn-backup-$(date +%F).tar.gz .env data/users.json
```

Store the backup outside the VPS (your laptop, a private cloud bucket, etc.).

## Restoring from backup

1. Provision a new VPS.
2. Follow steps 1-3 of this guide.
3. Restore the backup:
```bash
   tar xzf vpn-backup-2026-XX-XX.tar.gz
```
4. Run `make up`.
5. Run `docker compose exec manager vpn-user sync` to re-register users
   in xray's runtime.

Existing client links keep working — UUIDs don't change.

## Hardening (optional)

For production deployments, consider:

- **Disable root SSH**: edit `/etc/ssh/sshd_config`, set
  `PermitRootLogin no`, restart sshd. Make sure you have a sudo-capable
  non-root user with SSH key access first.
- **Fail2ban** for SSH:
```bash
  sudo apt install -y fail2ban
  sudo systemctl enable --now fail2ban
```
- **Automatic security updates**:
```bash
  sudo apt install -y unattended-upgrades
  sudo dpkg-reconfigure unattended-upgrades
```
- **Provider-level firewall**: Aeza, Hetzner, and others let you set firewall
  rules outside the VM. Use them as defense in depth.