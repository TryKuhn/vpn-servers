# vpn-servers

Self-hosted VPN infrastructure based on Xray (VLESS + Reality protocol).

Production-ready setup for personal VPN servers, designed to be easy to deploy
on any Linux VPS via Docker. Comes with a Python-based management API for
zero-downtime user operations.

## Features

- **VLESS + Reality** — modern, censorship-resistant protocol that masks traffic
  as TLS to a legitimate website.
- **Zero-downtime user management** — add/remove users without dropping existing
  connections, via Xray gRPC API.
- **Dockerized** — single `make up` to spin up a node.
- **Multi-user** — manage many users on a single server with friendly CLI.
- **Anti-leak routing** — block requests to RU domains/IPs to prevent accidental
  exposure of users' real identity (coming in v0.6).
- **Ad blocking** — server-side filtering of known ad domains (coming in v0.7).
- **Smart routing** — selectively route traffic through VPN to look less
  suspicious to DPI systems (coming in v0.8).

## Status

🚧 **Active development.** See [CHANGELOG.md](./CHANGELOG.md) for the release
history and upcoming features.

## Quick start

> Docker-based deployment will be available in v0.5.0. Until then, this repo
> is a work-in-progress.

```bash
git clone https://github.com/TryKuhn/vpn-servers.git
cd vpn-servers
cp .env.example .env
# edit .env: set SERVER_IP, SNI, etc.
make init      # generate keys
make up        # start the server
make add USER=alice
```

## Architecture

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for a high-level overview.

## License

Apache 2.0 — see [LICENSE](./LICENSE).

## Disclaimer

This software is provided for educational and personal use. Operators are
responsible for compliance with local laws regarding VPN operation and use.