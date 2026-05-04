# vpn-manager

User management service for [vpn-servers](../README.md).

Manages VPN users on the Xray VLESS+Reality server: add, remove, list, generate
client links and QR codes. Communicates with the Xray gRPC API for
zero-downtime user operations.

## Status

🚧 Active development. See [CHANGELOG.md](../CHANGELOG.md).

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    vpn-manager (Python)                  │
│                                                          │
│   ┌──────────────────────────────────────────────────┐   │
│   │ Interfaces                                       │   │
│   │   • CLI (vpn-user)                ← v0.5         │   │
│   │   • HTTP API (subscription URLs)  ← v0.75        │   │
│   │   • Telegram bot                  ← v1.0         │   │
│   └───────────────────────────┬──────────────────────┘   │
│                               │                          │
│   ┌───────────────────────────▼──────────────────────┐   │
│   │ Services (business logic, interface-agnostic)    │   │
│   └───────┬─────────────┬──────────────┬─────────────┘   │
│           │             │              │                 │
│   ┌───────▼─────┐ ┌─────▼──────┐ ┌─────▼─────────┐       │
│   │ UsersStore  │ │ XrayClient │ │   Models      │       │
│   │ (JSON)      │ │  (gRPC)    │ │  (dataclass)  │       │
│   └─────────────┘ └────────────┘ └───────────────┘       │
└──────────────────────────────────────────────────────────┘
```

## Development

```bash
cd manager
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest
```

## CLI Usage

```bash
vpn-user add alice
vpn-user add alice bob charlie    # multiple at once
vpn-user list
vpn-user show alice               # print link + QR
vpn-user remove alice
vpn-user sync                     # re-apply users.json to running xray
```

