"""Client for Xray's gRPC API, accessed via the `xray api` CLI subcommand.

We use subprocess rather than native gRPC to avoid managing protobuf bindings
across xray versions. The `xray` binary is installed in the manager container
and acts as our bridge to the running xray service.

Future: when we need stats or live-monitoring (v1.0+), switch to a native
gRPC client with generated bindings pinned to a specific xray version.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Errors
# ----------------------------------------------------------------------------


class XrayApiError(Exception):
    """Base class for all Xray API failures."""


class XrayApiUnavailableError(XrayApiError):
    """The xray API endpoint is unreachable or not responding."""


class XrayUserAlreadyExistsError(XrayApiError):
    """Tried to add a user that's already in xray's runtime config."""


class XrayUserNotFoundError(XrayApiError):
    """Tried to remove a user that's not in xray's runtime config."""


# ----------------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class XrayClient:
    """Thin client around the `xray api` CLI subcommand.

    All methods are blocking. Operations are performed by spawning a short-lived
    `xray api ...` subprocess, which talks to the running xray instance over
    gRPC on `xray_api_addr`.

    A new client is cheap to construct (it holds no resources, just config).
    """

    settings: Settings

    # Timeout for any single subprocess call. xray api is normally instant
    # (<100ms); 5 seconds is a generous ceiling for a stuck/unresponsive server.
    timeout_seconds: float = 5.0

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def add_user(self, user: User) -> None:
        """Add a user to the running xray inbound, with no downtime.

        Raises:
            XrayUserAlreadyExistsError: if `user.email` is already present.
            XrayApiUnavailableError: if xray is not responding.
            XrayApiError: for any other failure.
        """
        payload = {
            "tag": self.settings.xray_inbound_tag,
            "users": [
                {
                    "level": 0,
                    "email": user.email,
                    "account": {
                        "type": "vless",
                        "id": user.uuid,
                        "flow": "xtls-rprx-vision",
                        "encryption": "none",
                    },
                }
            ],
        }

        try:
            self._run("adu", payload)
        except _SubprocessFailedError as e:
            if "already exists" in e.stderr.lower():
                raise XrayUserAlreadyExistsError(
                    f"User {user.email!r} already exists in xray"
                ) from e
            raise XrayApiError(
                f"Failed to add user {user.email!r}: {e.stderr.strip()}"
            ) from e

    def remove_user(self, email: str) -> None:
        """Remove a user from the running xray inbound.

        Raises:
            XrayUserNotFoundError: if `email` isn't currently in xray.
            XrayApiUnavailableError: if xray is not responding.
            XrayApiError: for any other failure.
        """
        payload = {
            "tag": self.settings.xray_inbound_tag,
            "email": email,
        }

        try:
            self._run("rmu", payload)
        except _SubprocessFailedError as e:
            stderr = e.stderr.lower()
            if "not found" in stderr or "no such" in stderr:
                raise XrayUserNotFoundError(
                    f"User {email!r} not found in xray"
                ) from e
            raise XrayApiError(
                f"Failed to remove user {email!r}: {e.stderr.strip()}"
            ) from e

    # ------------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------------

    def _run(self, command: str, payload: dict[str, Any]) -> str:
        """Invoke `xray api {command}` with the given JSON payload.

        Returns stdout on success. Raises _SubprocessFailed (an internal
        marker exception) for non-zero exit codes; the public methods
        translate that into domain errors.
        """
        argv = [
            "xray",
            "api",
            command,
            f"--server={self.settings.xray_api_addr}",
            "--",
            json.dumps(payload),
        ]

        log.debug("xray api: %s", argv)

        try:
            result = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            raise XrayApiUnavailableError(
                f"xray api timed out after {self.timeout_seconds}s "
                f"(is xray running on {self.settings.xray_api_addr}?)"
            ) from e
        except FileNotFoundError as e:
            # `xray` binary not on PATH. Should never happen in our container,
            # but worth catching with a clear message.
            raise XrayApiError(
                "xray binary not found on PATH. "
                "Are you running this inside the manager container?"
            ) from e

        if result.returncode != 0:
            # Detect connection failures: gRPC client errors when xray is down
            # typically include strings like "connection refused" or
            # "transport is closing".
            stderr = result.stderr or ""
            if (
                "connection refused" in stderr.lower()
                or "transport" in stderr.lower()
            ):
                raise XrayApiUnavailableError(
                    f"Cannot reach xray at {self.settings.xray_api_addr}: "
                    f"{stderr.strip()}"
                )
            raise _SubprocessFailedError(stderr=stderr, returncode=result.returncode)

        return result.stdout


# ----------------------------------------------------------------------------
# Internal marker exception
# ----------------------------------------------------------------------------


@dataclass
class _SubprocessFailedError(Exception):
    """Internal: raised by _run for non-zero exits, translated by callers."""

    stderr: str
    returncode: int

    def __str__(self) -> str:
        return f"xray api exited {self.returncode}: {self.stderr}"
