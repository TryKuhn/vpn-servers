"""`vpn-user sync` — re-apply users.json to running xray."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "sync",
        help="Re-apply users.json to running xray",
        description="Re-register all users with the running xray instance. "
        "Run this after xray restarts (its runtime state is wiped on start).",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    print("Syncing users.json → xray...")
    added = service.sync()
    total = len(service.list_all())
    print(f"✓ {added}/{total} users (re-)applied to xray.")
    return 0
