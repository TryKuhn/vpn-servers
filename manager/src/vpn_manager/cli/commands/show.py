"""`vpn-user show NAME` — show a user's connection link and QR."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService
from vpn_manager.utils.qr import render_qr_to_terminal
from vpn_manager.utils.vless_link import build_vless_link


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "show",
        help="Show a user's link and QR code",
        description="Display the VLESS link and QR code for an existing user. "
        "Useful for re-sending the link to a user who lost it.",
    )
    parser.add_argument("name", help="User name")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    user = service.get(args.name)
    link = build_vless_link(user, settings)
    sub_url = f"{settings.subscription_url}/sub/{user.subscription_token}"

    print(f"User: {user.name}")
    print()
    print("Subscription URL:")
    print(f"  {sub_url}")
    print()
    print("VLESS link (legacy):")
    print(f"  {link}")
    print()
    print("QR code (subscription URL):")
    print(render_qr_to_terminal(sub_url))
    return 0
