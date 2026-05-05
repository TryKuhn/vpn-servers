"""`vpn-user rotate-token NAME` — issue a new subscription URL for a user.

The user's UUID and existing VPN session are not affected. Only the
subscription URL changes — anyone who had the old URL can no longer
fetch the user's config.
"""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "rotate-token",
        help="Issue a new subscription URL for an existing user",
        description=(
            "Generate a fresh subscription token for the named user. "
            "The old subscription URL stops working immediately. The "
            "user's UUID and active VPN connection are unaffected."
        ),
    )
    parser.add_argument(
        "name",
        metavar="NAME",
        help="Existing user's name",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    user = service.rotate_subscription_token(args.name)

    sub_url = f"{settings.subscription_url}/sub/{user.subscription_token}"

    print(f"✓ New subscription URL for {user.name!r}:")
    print()
    print(f"  {sub_url}")
    print()
    print("The previous URL is now invalid. Send the new one to the user.")
    return 0
