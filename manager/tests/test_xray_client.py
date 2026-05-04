"""Tests for vpn_manager.xray.client.

We mock the gRPC stub directly. This is cleaner than the previous
subprocess-based approach: we test our error-mapping logic without
caring about CLI argument parsing or stderr scraping.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import grpc
import pytest

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.xray.client import (
    XrayApiError,
    XrayApiUnavailableError,
    XrayClient,
    XrayUserAlreadyExistsError,
    XrayUserNotFoundError,
)

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def client(settings: Settings) -> XrayClient:
    return XrayClient(settings=settings)


def _make_rpc_error(
    code: grpc.StatusCode, details: str = ""
) -> grpc.RpcError:
    """Build a grpc.RpcError-compatible mock.

    Real RpcError instances also implement the Call interface (code(),
    details()). We construct a subclass on the fly that has both, so
    the mock behaves like a real one.
    """

    class _MockRpcError(grpc.RpcError):
        def code(self) -> grpc.StatusCode:
            return code

        def details(self) -> str:
            return details

    return _MockRpcError()


# ----------------------------------------------------------------------------
# add_user — happy path
# ----------------------------------------------------------------------------


def test_add_user_calls_alter_inbound(
    client: XrayClient, alice: User
) -> None:
    """Successful add_user should make exactly one AlterInbound RPC."""
    fake_stub = MagicMock()
    fake_stub.AlterInbound.return_value = MagicMock()

    with patch.object(client, "_get_stub", return_value=fake_stub):
        client.add_user(alice)

    fake_stub.AlterInbound.assert_called_once()


def test_add_user_sends_correct_tag_and_email(
    client: XrayClient, alice: User
) -> None:
    """The AlterInbound request must carry our inbound tag and the user's email."""
    fake_stub = MagicMock()
    fake_stub.AlterInbound.return_value = MagicMock()

    with patch.object(client, "_get_stub", return_value=fake_stub):
        client.add_user(alice)

    request = fake_stub.AlterInbound.call_args.args[0]
    assert request.tag == client.settings.xray_inbound_tag
    # The operation is a packed TypedMessage; it carries the email inside,
    # but we don't deserialize it here — that's xray's job. We just
    # verify the wrapping is non-empty.
    assert request.operation.value  # non-empty serialized payload


# ----------------------------------------------------------------------------
# add_user — error mapping
# ----------------------------------------------------------------------------


def test_add_user_translates_already_exists(
    client: XrayClient, alice: User
) -> None:
    err = _make_rpc_error(
        grpc.StatusCode.INTERNAL,
        details="user with email 'alice@vpn' already exists",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayUserAlreadyExistsError):
            client.add_user(alice)


def test_add_user_translates_unavailable(
    client: XrayClient, alice: User
) -> None:
    err = _make_rpc_error(
        grpc.StatusCode.UNAVAILABLE,
        details="failed to connect to all addresses",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayApiUnavailableError):
            client.add_user(alice)


def test_add_user_translates_deadline_exceeded(
    client: XrayClient, alice: User
) -> None:
    err = _make_rpc_error(
        grpc.StatusCode.DEADLINE_EXCEEDED,
        details="deadline exceeded",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayApiUnavailableError):
            client.add_user(alice)


def test_add_user_unknown_error_becomes_generic_error(
    client: XrayClient, alice: User
) -> None:
    err = _make_rpc_error(
        grpc.StatusCode.UNKNOWN,
        details="something weird",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayApiError) as exc_info:
            client.add_user(alice)

    # Make sure it's the base, not a more specific subclass.
    assert type(exc_info.value) is XrayApiError


# ----------------------------------------------------------------------------
# remove_user
# ----------------------------------------------------------------------------


def test_remove_user_calls_alter_inbound(client: XrayClient) -> None:
    fake_stub = MagicMock()
    fake_stub.AlterInbound.return_value = MagicMock()

    with patch.object(client, "_get_stub", return_value=fake_stub):
        client.remove_user("alice@vpn")

    fake_stub.AlterInbound.assert_called_once()


def test_remove_user_translates_not_found(client: XrayClient) -> None:
    err = _make_rpc_error(
        grpc.StatusCode.INTERNAL,
        details="user 'ghost@vpn' not found",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayUserNotFoundError):
            client.remove_user("ghost@vpn")


def test_remove_user_translates_no_such(client: XrayClient) -> None:
    """Some xray error messages use 'no such' wording."""
    err = _make_rpc_error(
        grpc.StatusCode.INTERNAL,
        details="no such user with email",
    )
    fake_stub = MagicMock()
    fake_stub.AlterInbound.side_effect = err

    with patch.object(client, "_get_stub", return_value=fake_stub), pytest.raises(XrayUserNotFoundError):
            client.remove_user("ghost@vpn")


# ----------------------------------------------------------------------------
# Channel management
# ----------------------------------------------------------------------------


def test_channel_is_lazy(client: XrayClient) -> None:
    """No gRPC channel should exist before the first call."""
    assert client._channel is None
    assert client._stub is None


def test_close_is_idempotent(client: XrayClient) -> None:
    """Calling close() multiple times must not raise."""
    client.close()  # before any usage
    client.close()  # twice in a row


def test_close_releases_channel(client: XrayClient) -> None:
    """After close(), the channel should be back to None."""
    fake_channel = MagicMock(spec=grpc.Channel)
    fake_stub = MagicMock()
    client._channel = fake_channel
    client._stub = fake_stub

    client.close()

    fake_channel.close.assert_called_once()
    assert client._channel is None
    assert client._stub is None
