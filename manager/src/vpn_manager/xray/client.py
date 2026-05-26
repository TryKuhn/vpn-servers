"""Client for Xray's gRPC HandlerService.

Talks directly to xray's gRPC API on `xray_api_addr` to add/remove users
without restarting xray.

Versioning: bindings are generated at build time from xray-core
.proto files at the version pinned in the Dockerfile (XRAY_VERSION).
The generated modules live under vpn_manager.xray._generated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import grpc
from google.protobuf import message as protobuf_message

# Trigger sys.path setup for generated modules' absolute imports.
import vpn_manager.xray._generated  # noqa: F401  (side-effect import)
from vpn_manager.config import Settings
from vpn_manager.models.user import User

# These imports must come AFTER the side-effect import above, or proto's
# transitive imports (e.g. `from common.protocol import user_pb2`) will fail.
# fmt: off
from vpn_manager.xray._generated.app.proxyman.command import (
    command_pb2,
    command_pb2_grpc,
)
from vpn_manager.xray._generated.common.protocol import user_pb2
from vpn_manager.xray._generated.common.serial import (
    typed_message_pb2,
)
from vpn_manager.xray._generated.proxy.vless import account_pb2 as vless_pb2

# fmt: on

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
# Helpers
# ----------------------------------------------------------------------------

# Fully-qualified protobuf type name for VLess account. xray's TypedMessage
# uses these strings to identify which proto type is packed inside.
_VLESS_ACCOUNT_TYPE = "xray.proxy.vless.Account"


def _build_vless_account(uuid: str, flow: str) -> typed_message_pb2.TypedMessage:
    """Build a TypedMessage wrapping a VLess account proto."""
    account = vless_pb2.Account(id=uuid, flow=flow, encryption="none")
    return typed_message_pb2.TypedMessage(
        type=_VLESS_ACCOUNT_TYPE,
        value=account.SerializeToString(),
    )


def _build_user_proto(user: User, flow: str) -> user_pb2.User:
    """Convert our domain User into the xray protobuf User."""
    return user_pb2.User(
        level=0,
        email=user.email,
        account=_build_vless_account(user.uuid, flow=flow),
    )


# ----------------------------------------------------------------------------
# Client
# ----------------------------------------------------------------------------


@dataclass
class XrayClient:
    """gRPC client for xray's HandlerService.

    A single channel is opened lazily on first use and reused across calls.
    For our scale (low QPS, single thread) this is fine; the channel is
    thread-safe per gRPC docs.
    """

    settings: Settings
    timeout_seconds: float = 5.0

    # Lazily initialized state. Marked as field with init=False so it's
    # not part of __init__.
    _channel: grpc.Channel | None = field(default=None, init=False, repr=False)
    _stub: command_pb2_grpc.HandlerServiceStub | None = field(
        default=None, init=False, repr=False
    )

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
        self._add_to_inbound(user, self.settings.xray_inbound_tag, flow="xtls-rprx-vision")

    def sync_user(self, user: User) -> int:
        """Add user to the inbound, tolerating already-exists.

        Returns 1 if user was newly added, 0 if already present.
        """
        try:
            self._add_to_inbound(user, self.settings.xray_inbound_tag, "xtls-rprx-vision")
            return 1
        except XrayUserAlreadyExistsError:
            log.debug("User %s already in %s; skipping", user.email, self.settings.xray_inbound_tag)
            return 0

    def remove_user(self, email: str) -> None:
        """Remove a user from the running xray inbound.

        Raises:
            XrayUserNotFoundError: if `email` isn't currently in xray.
            XrayApiUnavailableError: if xray is not responding.
            XrayApiError: for any other failure.
        """
        self._remove_from_inbound(email, self.settings.xray_inbound_tag)

    def _add_to_inbound(self, user: User, tag: str, flow: str) -> None:
        op = command_pb2.AddUserOperation(user=_build_user_proto(user, flow=flow))
        request = command_pb2.AlterInboundRequest(tag=tag, operation=_pack_operation(op))
        self._call(
            f"AlterInbound (AddUser/{tag})",
            lambda: self._get_stub().AlterInbound(request, timeout=self.timeout_seconds),
            email=user.email,
        )

    def _remove_from_inbound(self, email: str, tag: str) -> None:
        op = command_pb2.RemoveUserOperation(email=email)
        request = command_pb2.AlterInboundRequest(tag=tag, operation=_pack_operation(op))
        self._call(
            f"AlterInbound (RemoveUser/{tag})",
            lambda: self._get_stub().AlterInbound(request, timeout=self.timeout_seconds),
            email=email,
        )

    def close(self) -> None:
        """Close the gRPC channel. Idempotent."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None

    # ------------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------------

    def _get_stub(self) -> command_pb2_grpc.HandlerServiceStub:
        """Lazily create the gRPC stub. Reuses the channel across calls."""
        if self._stub is None:
            # Insecure channel: xray's API listens only on 127.0.0.1 inside
            # the container, no TLS needed (and xray's API doesn't support
            # it natively anyway).
            self._channel = grpc.insecure_channel(self.settings.xray_api_addr)
            self._stub = command_pb2_grpc.HandlerServiceStub(self._channel)
        return self._stub

    def _call(
        self,
        op_name: str,
        rpc: object,  # callable returning the response; typed loosely to keep mypy happy
        *,
        email: str,
    ) -> None:
        """Execute an RPC and translate gRPC errors into our domain errors.

        Centralizes the boilerplate of error mapping so add/remove stay short.
        """
        try:
            rpc()  # type: ignore[operator]
        except grpc.RpcError as e:
            self._raise_from_grpc(e, op_name=op_name, email=email)

    def _raise_from_grpc(
        self,
        err: grpc.RpcError,
        *,
        op_name: str,
        email: str,
    ) -> None:
        """Translate a grpc.RpcError into the appropriate domain exception."""
        # grpc.RpcError instances are also Call objects with code() and details()
        code: grpc.StatusCode = err.code()  # type: ignore[attr-defined]
        details: str = err.details() or ""  # type: ignore[attr-defined]
        details_lower = details.lower()

        log.debug("gRPC %s failed: code=%s details=%s", op_name, code, details)

        # Connection errors -> XrayApiUnavailableError.
        if code in (
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
        ):
            raise XrayApiUnavailableError(
                f"Cannot reach xray at {self.settings.xray_api_addr}: {details}"
            ) from err

        # Already-exists / not-found are signalled by xray as INTERNAL or
        # UNKNOWN with descriptive details. We match by string.
        if "already exists" in details_lower:
            raise XrayUserAlreadyExistsError(
                f"User {email!r} already exists in xray"
            ) from err
        if "not found" in details_lower or "no such" in details_lower:
            raise XrayUserNotFoundError(
                f"User {email!r} not found in xray"
            ) from err

        # Fallback: generic error with the gRPC details preserved.
        raise XrayApiError(
            f"{op_name} failed: code={code.name}, details={details}"
        ) from err


# ----------------------------------------------------------------------------
# Module-level helpers
# ----------------------------------------------------------------------------


def _pack_operation(op: protobuf_message.Message) -> typed_message_pb2.TypedMessage:
    """Wrap an Add/Remove operation in TypedMessage for AlterInboundRequest.

    xray's AlterInboundRequest.operation is a TypedMessage so the same
    request can carry any operation type. We need to fully-qualify the
    type name so xray knows what to deserialize.
    """
    type_name = op.DESCRIPTOR.full_name
    return typed_message_pb2.TypedMessage(
        type=type_name,
        value=op.SerializeToString(),
    )
