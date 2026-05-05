# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- **v0.85** — sing-box subscription format for clients that fully apply
  routing config (V2RayTun, Hiddify, NekoBox). Will enable automatic
  client-side split tunneling.
- **v1.0.0** — Subscription billing with Telegram bot, recurring payments.

## [0.75.0] — 2026-05-05

Subscription server. Clients can now import a single URL that auto-updates
when server config changes.

### Added

- **HTTP API in manager** (FastAPI + uvicorn) on `:8080`, host network.
  - `GET /health` — liveness probe.
  - `GET /sub/{token}` — returns the user's xray client config as JSON.
- **HTTPS termination via nginx** on `:8443` with auto-renewing
  Let's Encrypt certificates (jonasal/nginx-certbot).
- **Subscription tokens**: every user gets a 256-bit URL-safe token at
  creation, used as the secret in their personal subscription URL.
  Backwards-compat: legacy users (created before v0.75) get tokens
  generated on first read.
- **`vpn-user rotate-token NAME` CLI** — issue a fresh subscription URL
  for an existing user. UUID and active VPN session are unaffected;
  only the subscription URL changes.
- **Updated CLI output**: `vpn-user add` and `vpn-user show` now print
  the subscription URL (recommended) alongside the legacy VLESS link.
  QR codes encode the subscription URL.
- **DuckDNS support**: Reality keys, server cert, and subscription URL
  use a DuckDNS subdomain (no domain registration needed).
- **`config-init` for nginx**: docker-compose runs nginx + certbot in
  `network_mode: host` so it can reach manager directly via 127.0.0.1.

### Operational notes

- The xray-config JSON returned by `/sub/{token}` includes `outbounds`
  for VPN/direct/block plus routing rules for smart split tunneling
  (RU sites direct, ads blocked, rest through VPN).
- **However**: most popular clients today (V2RayTun, Hiddify) extract
  only the VLESS connection details from this JSON and ignore the
  routing rules — they apply their own routing instead. This means
  the "smart routing in subscription" goal is **not yet** delivered to
  end users. Server-side anti-leak (v0.7.1) still protects from RU
  domain leakage even when client-side routing isn't applied.
- Full client-side smart routing requires a sing-box-formatted
  subscription, planned for v0.85.

### Configuration

New environment variables required (see `.env.example`):

- `NGINX_DOMAIN` — DuckDNS subdomain pointing to your VPS.
- `CERTBOT_EMAIL` — email for Let's Encrypt renewal warnings.
- `ACME_STAGING` — `1` for staging certs, `0` for production.
- `SUBSCRIPTION_BASE_URL` — base URL for subscription endpoints
  (e.g., `https://your-domain.duckdns.org:8443`).

### Infrastructure

Production docker-compose now runs four services:

- `xray` — VPN itself (port 443).
- `manager` — FastAPI subscription server + CLI (port 8080).
- `nginx` — TLS termination + Let's Encrypt (ports 80, 8443).
- `config-init`, `data-init` — one-shot init for permissions and config.

## [0.7.1] — 2026-05-05

Restore anti-leak and ad-blocking after upstream xray image incompatibility,
and harden the deployment pipeline with safety nets that would have prevented
the morning outage.

### Fixed

- **Restored anti-leak and ad-blocking routing**, broken since the morning's
  outage when teddysun's xray image bumped its bundled geosite database and
  silently dropped the `geosite:ru` category. Replaced with `geoip:ru`
  (catches more — works at the IP layer regardless of DNS), kept
  `geosite:category-gov-ru` and `geosite:category-ads-all`.
- **Pinned `teddysun/xray` to 25.12.8** in docker-compose. The `:latest`
  tag was the root cause of the morning's outage: an upstream image
  refresh broke our routing rules without warning. Image upgrades are
  now explicit, deliberate decisions.

### Added

- **Pre-deploy xray config validation** in GitHub Actions. The deploy
  workflow now renders the xray config from template + `.env` and runs
  `xray run -test` against it BEFORE touching production containers. If
  validation fails, the deploy aborts with the running stack untouched.
  This is the safety net that would have prevented the morning's outage.
- **Smarter CI healthcheck**:
  - Manager's `/health` HTTP endpoint is probed (proves uvicorn is
    serving, not just that the process started).
  - Manager's `RestartCount` is tracked: if the container restarts
    more than twice during the deploy window, deployment is failed
    fast.
  - Failure log shows final state (`xray=...`, `manager=...`,
    `/health=...`, restarts) for faster diagnosis.

### Operational notes

- The `geosite:ru` category was removed from teddysun's bundled
  geosite.dat at some point in early May 2026. We don't depend on it
  anymore. If a future image upgrade restores it, we may revisit the
  trade-off between domain-based and IP-based blocking.
- For users without client-side split tunneling, RU sites continue
  to be blocked through the VPN. The recommended client config in
  `docs/DEPLOYMENT.md` still applies.

## [0.7.0] — 2026-05-04

Server-side ad blocking via geosite categories.

### Added

- **Ad/tracker blocking** in xray routing rules:
  `geosite:category-ads-all` covers ~20,000 known ad and tracking domains
  including Google Ads, YouTube Ads, Meta tracking, Yandex Metrica, and
  others. Effect: fewer ads in browser, YouTube, social feeds.
- **Documentation** for tuning ad-blocking aggressiveness or adding
  domain-specific exceptions.

### Notes

- This is server-side filtering — no client configuration needed.
- Some ads (especially those served from the same domain as content,
  like YouTube's pre-roll injected into the video stream) cannot be
  blocked at this layer. Client-side ad blockers complement this.

## [0.6.0] — 2026-05-04

Server-side anti-leak: protect users from accidentally exposing their real
identity through the VPN when accessing Russian services.

### Added

- **Routing rules** in xray config that block:
  - `geosite:ru` — known Russian domains (mail.ru, yandex, vk, sberbank,
    gosuslugi, etc.).
  - `geosite:category-gov-ru` — government domains specifically.
  - `geoip:ru` — IPs registered to Russian providers.
  - `geoip:private` — private/local IP ranges (security: prevents
    tunneling into the VPS's internal network).
- **`domainStrategy: IPIfNonMatch`** for two-pass routing: domains first,
  then resolve to IP and re-check. Catches domains not in geosite but
  hosted on Russian IPs.
- **Documentation** for client-side split tunneling, since blocking RU
  on the server requires complementary client-side direct routing.

### Behavior changes

- **Existing client configs without split tunneling will lose access to
  RU sites through the VPN.** Users must either configure direct routing
  in their client (recommended) or disconnect VPN when accessing RU
  services.

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