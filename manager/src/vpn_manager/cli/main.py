"""CLI entry point.

Usage:
    vpn-user add ALICE
    vpn-user remove ALICE
    vpn-user list
    vpn-user show ALICE
    vpn-user sync
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable

from vpn_manager.cli.commands import add, list_users, remove, show, sync
from vpn_manager.config import Settings
from vpn_manager.services.user_service import UserService
from vpn_manager.storage.users_store import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UsersStore,
)
from vpn_manager.xray.client import XrayApiError, XrayClient


def _build_parser() -> argparse.ArgumentParser:
    """Build the top-level argparse parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="vpn-user",
        description="Manage VPN users on this server.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
    )

    # Each command module registers itself.
    for module in (add, remove, list_users, show, sync):
        module.register(subparsers)

    return parser


def _build_service(settings: Settings) -> UserService:
    """Wire dependencies and build the service."""
    store = UsersStore(settings.users_db_path)
    xray = XrayClient(settings=settings)
    return UserService(store=store, xray=xray)


def run() -> int:
    """Entry point. Returns shell exit code."""
    parser = _build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    try:
        settings = Settings.from_env()
    except RuntimeError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 2

    service = _build_service(settings)

    command_func: Callable[
        [argparse.Namespace, UserService, Settings], int
    ] = args.func

    try:
        return command_func(args, service, settings)
    except UserAlreadyExistsError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except UserNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except XrayApiError as e:
        print(f"Xray error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(run())
