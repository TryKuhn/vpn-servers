# TryKuhn VPN v0.1 async

Core stack:

- HAProxy SNI-router on `443/tcp`
- Xray VLESS + REALITY + XHTTP
- Hysteria2 on `443/udp`
- NaiveProxy via custom Caddy `forwardproxy@naive`
- FastAPI manager
- PostgreSQL 16
- SQLAlchemy 2.0 async + asyncpg
- Alembic migrations
- Makefile operator commands

## First run

```bash
sudo make install
cp .env.example .env
make init
nano .env
make certs
make deploy-from-scratch
```

## Users

```bash
make add-user NAME=MrNykterstein-PC
make show-user NAME=MrNykterstein-PC
make list-users
```

## Legacy import

```bash
cp docs/legacy_users.example.csv legacy_users.csv
nano legacy_users.csv
make import-legacy FILE=legacy_users.csv
```

Preserve old `subscription_token` to keep old subscription URLs stable.

## Migrations

```bash
make migrate
make migrate.upgrade
make migrate.downgrade
make migrate.revision MSG="add devices field"
```
