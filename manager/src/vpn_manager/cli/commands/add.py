"""`vpn-user add NAME` — add a new user."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService
from vpn_manager.utils.qr import render_qr_to_terminal
from vpn_manager.utils.vless_link import build_vless_link


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the `add` subcommand."""
    parser = subparsers.add_parser(
        "add",
        help="Add a new user",
        description="Add a new VPN user. Generates a UUID, registers with "
        "xray, and prints the connection link with a QR code.",
    )
    parser.add_argument("name", help="User name (e.g. alice, phone, work)")
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    """Execute the command. Returns shell exit code."""
    user = service.add(args.name)

    link = build_vless_link(user, settings)

    print(f"✓ User {user.name!r} created.")
    print()
    print("VLESS link:")
    print(link)
    print()
    print("QR code (scan with V2RayTun, Hiddify, etc.):")
    print(render_qr_to_terminal(link))
    return 0
