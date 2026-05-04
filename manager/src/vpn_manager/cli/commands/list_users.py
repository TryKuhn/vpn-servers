"""`vpn-user list` — list all users."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "list",
        help="List all users",
        description="List all VPN users with their creation time.",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    users = service.list_all()

    if not users:
        print("No users yet. Add one with: vpn-user add <name>")
        return 0

    # Compute column widths for tidy alignment.
    name_w = max(len(u.name) for u in users)
    name_w = max(name_w, len("NAME"))

    print(f"{'NAME':<{name_w}}  CREATED                   UUID")
    print(f"{'-' * name_w}  -----------------------   ----")
    for user in users:
        created = user.created_at.strftime("%Y-%m-%d %H:%M:%S %Z")
        print(f"{user.name:<{name_w}}  {created:<23}   {user.uuid}")
    return 0
