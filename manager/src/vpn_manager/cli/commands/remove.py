"""`vpn-user remove NAME` — remove a user."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "remove",
        help="Remove a user",
        description="Remove a VPN user from xray and storage. The user's "
        "existing client links will stop working immediately.",
    )
    parser.add_argument("name", help="User name to remove")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    user = service.remove(args.name)
    print(f"✓ User {user.name!r} removed.")
    return 0
