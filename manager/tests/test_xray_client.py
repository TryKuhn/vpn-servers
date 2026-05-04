"""Tests for vpn_manager.xray.client.

We mock subprocess.run rather than running a real xray process. This keeps
tests fast and deterministic, at the cost of not catching protocol-level
issues with the real xray API. Those are caught by integration tests
(coming in a later step).
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

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


def _success_result() -> MagicMock:
    """A subprocess.run result simulating a successful call."""
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = 0
    r.stdout = ""
    r.stderr = ""
    return r


def _failure_result(stderr: str, returncode: int = 1) -> MagicMock:
    """A subprocess.run result simulating a failed call."""
    r = MagicMock(spec=subprocess.CompletedProcess)
    r.returncode = returncode
    r.stdout = ""
    r.stderr = stderr
    return r


# ----------------------------------------------------------------------------
# add_user — happy path
# ----------------------------------------------------------------------------


def test_add_user_invokes_xray_api_with_correct_payload(
    client: XrayClient, alice: User
) -> None:
    with patch("subprocess.run", return_value=_success_result()) as mock_run:
        client.add_user(alice)

    mock_run.assert_called_once()
    args = mock_run.call_args.args[0]

    # Verify command structure: xray api adu --server=... -- {json}
    assert args[0] == "xray"
    assert args[1] == "api"
    assert args[2] == "adu"
    assert args[3] == f"--server={client.settings.xray_api_addr}"
    assert args[4] == "--"

    payload = json.loads(args[5])
    assert payload["tag"] == client.settings.xray_inbound_tag
    assert len(payload["users"]) == 1

    user_payload = payload["users"][0]
    assert user_payload["email"] == alice.email
    assert user_payload["account"]["id"] == alice.uuid
    assert user_payload["account"]["type"] == "vless"
    assert user_payload["account"]["flow"] == "xtls-rprx-vision"


# ----------------------------------------------------------------------------
# add_user — error mapping
# ----------------------------------------------------------------------------


def test_add_user_translates_already_exists_error(
    client: XrayClient, alice: User
) -> None:
    failure = _failure_result("user with email already exists")

    with patch("subprocess.run", return_value=failure), pytest.raises(XrayUserAlreadyExistsError):
        client.add_user(alice)


def test_add_user_raises_unavailable_on_connection_refused(
    client: XrayClient, alice: User
) -> None:
    failure = _failure_result(
        "rpc error: connection refused on 127.0.0.1:10085"
    )

    with patch("subprocess.run", return_value=failure), pytest.raises(XrayApiUnavailableError):
        client.add_user(alice)


def test_add_user_raises_unavailable_on_timeout(
    client: XrayClient, alice: User
) -> None:
    timeout_error = subprocess.TimeoutExpired(cmd="xray api", timeout=5.0)

    with patch("subprocess.run", side_effect=timeout_error), pytest.raises(XrayApiUnavailableError):
        client.add_user(alice)


def test_add_user_raises_generic_on_unknown_failure(
    client: XrayClient, alice: User
) -> None:
    failure = _failure_result("something weird happened")

    with patch("subprocess.run", return_value=failure), pytest.raises(XrayApiError) as exc_info:
        client.add_user(alice)

    # Make sure it's the base, not a more specific subclass.
    assert type(exc_info.value) is XrayApiError


# ----------------------------------------------------------------------------
# remove_user
# ----------------------------------------------------------------------------


def test_remove_user_invokes_xray_api_with_correct_payload(
    client: XrayClient,
) -> None:
    with patch("subprocess.run", return_value=_success_result()) as mock_run:
        client.remove_user("alice@vpn")

    args = mock_run.call_args.args[0]
    assert args[2] == "rmu"

    payload = json.loads(args[5])
    assert payload == {
        "tag": client.settings.xray_inbound_tag,
        "email": "alice@vpn",
    }


def test_remove_user_translates_not_found_error(client: XrayClient) -> None:
    failure = _failure_result("user not found")

    with patch("subprocess.run", return_value=failure), pytest.raises(XrayUserNotFoundError):
        client.remove_user("ghost@vpn")


def test_remove_user_translates_no_such_error(client: XrayClient) -> None:
    """Some xray versions phrase the error differently."""
    failure = _failure_result("no such user")

    with patch("subprocess.run", return_value=failure), pytest.raises(XrayUserNotFoundError):
        client.remove_user("ghost@vpn")


# ----------------------------------------------------------------------------
# Edge cases
# ----------------------------------------------------------------------------


def test_xray_binary_missing_raises_xray_api_error(
    client: XrayClient, alice: User
) -> None:
    """If `xray` isn't on PATH, surface a clear error."""
    with patch(
        "subprocess.run",
        side_effect=FileNotFoundError("[Errno 2] No such file or directory: 'xray'"),
    ), pytest.raises(XrayApiError, match="xray binary not found"):
        client.add_user(alice)


def test_client_is_frozen(client: XrayClient) -> None:
    with pytest.raises(AttributeError):
        client.timeout_seconds = 1.0  # type: ignore[misc]
