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

### Coming soon

- Zero-downtime user management via Xray gRPC API (v0.5.0)
- Anti-leak routing for RU domains/IPs (v0.6.0)
- Server-side ad blocking (v0.7.0)
- Subscription URL server (v0.75.0)
- Smart routing in client configs (v0.8.0)
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

## Architecture

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for the high-level overview.

## License

Apache 2.0 — see [LICENSE](./LICENSE).

## Disclaimer

This software is provided for educational and personal use. Operators are
responsible for compliance with local laws regarding VPN operation and use.