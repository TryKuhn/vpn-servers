# vpn-servers

Self-hosted VPN infrastructure based on Xray (VLESS + Reality protocol).

Production-ready setup for personal VPN servers, deployable on any Linux VPS
via Docker. Comes with a Python-based management API (coming in v0.5.0) for
zero-downtime user operations.

## Features

- **VLESS + Reality** — modern, censorship-resistant protocol that masks traffic
  as TLS to a legitimate website.
- **Dockerized** — single `make up` to spin up a node.
- **Idempotent setup** — `make install` on a fresh VPS handles dependencies,
  firewall, and Docker.
- **Subscription server** with smart routing — `?format=clash` for
  Mihomo-family clients (Clash Verge Rev, CMFA, Stash) routes RU traffic
  DIRECT and international traffic through the VPN automatically. See
  [docs/CLIENTS.md](./docs/CLIENTS.md) for client setup.

### Coming soon

- Telegram-bot billing with recurring payments (v1.0.0)

See [CHANGELOG.md](./CHANGELOG.md) for the full roadmap.

## Quick start

On a fresh Ubuntu 22.04 / 24.04 VPS:

```bash
# 1. Clone the repo
git clone https://github.com/TryKuhn/vpn-servers.git
cd vpn-servers

# 2. Bootstrap the server (Docker, UFW, tools)
sudo make install

# 3. Configure (creates .env from template)
make init      # this will create .env if missing, then prompt to edit it
nano .env      # set SERVER_IP, choose SNI, etc.
make init      # generate Reality keys (rerun after editing .env)

# 4. Start the server
make up
make status    # check it's running
make logs      # see xray output
```

## Connecting clients

User-side setup is documented separately — see
[docs/CLIENTS.md](./docs/CLIENTS.md). Quick recap:

- **Default subscription URL** — base64 VLESS link, works in any
  Xray-family client (V2RayTun, v2rayN, Hiddify, etc.) as a full-tunnel
  VPN.
- **`?format=clash`** — Mihomo YAML with smart routing. Use with Clash
  Verge Rev (Windows/macOS/Linux), CMFA (Android), or Stash (iOS) for
  automatic split: RU sites direct, international through VPN, ads
  blocked.

## Architecture

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the high-level overview.

## License

Apache 2.0 — see [LICENSE](./LICENSE).

## Disclaimer

This software is provided for educational and personal use. Operators are
responsible for compliance with local laws regarding VPN operation and use. 
