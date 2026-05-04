# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- **v0.6.0** — Anti-leak routing: block RU domains/IPs on the server side.
- **v0.7.0** — Server-side ad blocking via geosite categories.
- **v0.75.0** — Subscription URL server: clients import a single URL and receive
  a fully-configured client config.
- **v0.8.0** — Smart routing in subscription configs: route only foreign sites
  through the VPN, keep local traffic direct.
- **v1.0.0** — Subscription billing with Telegram bot, recurring payments.

## [0.55.0] — 2026-05-04

Automated deployment via GitHub Actions. The development loop is now:
push to `main` → CI deploys → ~1 minute later changes are live in production.

### Added

- **Auto-deploy workflow** (`.github/workflows/deploy.yml`):
  - Triggered on push to `main` and via manual "Run workflow" button.
  - Concurrency-safe: parallel deploys are queued, not run simultaneously.
  - Uses a dedicated `deploy` user on the server with narrow sudo scope.
- **Auto-rollback on healthcheck failure**: if services don't reach `healthy`
  within 3 minutes after deployment, the workflow reverts the server to the
  previous commit and re-applies it.
- **Server hardening for CI**:
  - Dedicated `deploy` Linux user with SSH key auth only (no password).
  - Production directory moved to `/opt/vpn-servers` (FHS-conformant).
  - `vpn` user added to `deploy` group for diagnostic access.

### Operational changes

- Production now lives in `/opt/vpn-servers` (was `~/vpn`).
- The legacy `~/vpn` directory was removed after the migration verified.

## [0.5.1] — 2026-05-04

Hotfix: prevent runtime user state loss after xray container restart.

### Fixed

- `make up` now automatically syncs `users.json` to xray's runtime after
  bringing up the stack. Previously, restarting the stack would wipe xray's
  in-memory user list, causing existing client links to fail with
  `invalid request user id` until `vpn-user sync` was run manually.

### Added

- `make sync` Makefile target for explicit re-application of users.json.

## [0.5.0] — 2026-05-04

First production-ready release. The full stack is now Dockerized, with a
Python management service that operates on running xray via native gRPC.

### Added

- **VLESS + Reality VPN server** running in Docker (`teddysun/xray:latest`).
- **Python management service** (`vpn-manager`) with CLI:
  - `vpn-user add NAME [NAME ...]` — add one or more users with a single
    pre-validation pass; multi-add is all-or-nothing.
  - `vpn-user remove NAME` — remove a user without xray restart.
  - `vpn-user list` — list all users with creation timestamps.
  - `vpn-user show NAME` — re-print a user's VLESS link and QR code.
  - `vpn-user sync` — re-apply `users.json` to running xray (idempotent).
- **Native gRPC client** for xray's HandlerService. Bindings are generated
  at build time from xray-core `.proto` files at the pinned `XRAY_VERSION`,
  giving us version-locked, type-safe communication.
- **Atomic JSON storage** for the user database, using the
  write-temp-then-rename pattern with `os.fsync` before rename for crash
  safety.
- **Compensate-on-error** in user operations: if xray accepts but storage
  fails, xray is rolled back to keep the two in sync.
- **One-shot init containers** in docker-compose:
  - `config-init` — renders `xray/config.json` from template via envsubst.
  - `data-init` — fixes `./data` ownership for the non-root manager user.
- **Makefile interface** with operator-friendly targets:
  - `make install` — bootstrap a fresh VPS (Docker, UFW, tools).
  - `make init` — generate Reality keys.
  - `make up` / `make down` / `make restart` — lifecycle.
  - `make logs` / `make logs-xray` / `make logs-manager` — diagnostics.
  - `make shell-manager` — interactive shell inside manager container.
  - `make rebuild-manager` — fast iteration on Python code.
- **Multi-stage Dockerfile** for the manager: ~190 MB final image with
  build dependencies stripped from runtime.
- **57+ unit tests** covering models, storage, service layer, xray client
  (with mocked gRPC), CLI output formatting, and QR rendering. All pass
  under strict `mypy` and `ruff`.
- **QR code rendering** in the terminal via the `qrcode` package (Unicode
  block characters, 2x density vs ASCII).
- **Documentation**:
  - `docs/ARCHITECTURE.md` — system overview with Mermaid diagram.
  - `docs/DEPLOYMENT.md` — step-by-step production deployment.
  - `manager/README.md` — internal architecture and dev setup.

### Security

- Manager container runs as non-root (uid 1000).
- xray gRPC API binds to `127.0.0.1` only — never exposed externally.
- `.env` is gitignored; `users.json` and runtime state in `./data/` are
  gitignored.
- Apache 2.0 license.

### Known limitations

- All traffic from the VPN client is currently routed through the server.
  Selective routing (anti-leak for RU domains, smart routing) lands in v0.6+.
- No automated backups; operators must back up `.env` and
  `data/users.json` themselves (see `docs/DEPLOYMENT.md`).
- Single-server deployment only. Multi-server orchestration (failover,
  geo-distribution) is post-v1.0 territory.