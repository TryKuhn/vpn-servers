"""`vpn-user add NAME [NAME ...]` — add one or more users."""

from __future__ import annotations

import argparse

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.services.user_service import UserService
from vpn_manager.utils.qr import render_qr_to_terminal
from vpn_manager.utils.vless_link import build_vless_link


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Register the `add` subcommand."""
    parser = subparsers.add_parser(
        "add",
        help="Add one or more users",
        description=(
            "Add one or more VPN users. For a single user, prints the "
            "VLESS link and QR code. For multiple users, prints links only "
            "(use `vpn-user show NAME` to get a QR for any user later)."
        ),
    )
    parser.add_argument(
        "names",
        nargs="+",  # one or more
        metavar="NAME",
        help="User name(s) (e.g. alice, phone, work)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace, service: UserService, settings: Settings) -> int:
    """Execute the command. Returns shell exit code."""
    names: list[str] = args.names
    users = service.add_many(names)

    if len(users) == 1:
        _print_single_user(users[0], settings)
    else:
        _print_multiple_users(users, settings)

    return 0


def _print_single_user(user: User, settings: Settings) -> None:
    """Print full output for a single user: link + QR."""
    link = build_vless_link(user, settings)
    print(f"✓ User {user.name!r} created.")
    print()
    print("VLESS link:")
    print(link)
    print()
    print("QR code (scan with V2RayTun, Hiddify, etc.):")
    print(render_qr_to_terminal(link))


def _print_multiple_users(users: list[User], settings: Settings) -> None:
    """Print compact output for multiple users: links only.

    QR codes are not rendered to keep output readable when adding many
    users at once. Use `vpn-user show NAME` to get a QR for any user.
    """
    print(f"✓ Created {len(users)} user(s).")
    print()
    print("VLESS links:")
    print()

    # Compute name column width for alignment.
    name_w = max(len(u.name) for u in users)

    for user in users:
        link = build_vless_link(user, settings)
        print(f"  {user.name:<{name_w}}  {link}")

    print()
    print("To get a QR code for any user: vpn-user show NAME")
