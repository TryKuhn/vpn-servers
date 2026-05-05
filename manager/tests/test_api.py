"""Tests for vpn_manager.api.app."""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from vpn_manager.api.app import create_app
from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.storage.users_store import UsersStore


@pytest.fixture
def client(settings: Settings, alice: User, bob: User) -> TestClient:
    """A FastAPI test client with two users in storage."""
    store = UsersStore(settings.users_db_path)
    store.add(alice)
    store.add(bob)
    app = create_app(settings, store)
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_subscription_unknown_token_returns_404(client: TestClient) -> None:
    response = client.get("/sub/this_token_does_not_exist")
    assert response.status_code == 404


def test_subscription_default_format_is_base64_vless(
        client: TestClient, alice: User
) -> None:
    """No query param = base64-encoded VLESS link (universal format)."""
    response = client.get(f"/sub/{alice.subscription_token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    # Decodes back to a vless:// link with the user's UUID
    decoded = base64.b64decode(response.text).decode("utf-8")
    assert decoded.startswith("vless://")
    assert alice.uuid in decoded


def test_subscription_explicit_format_link(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}?format=link")
    assert response.status_code == 200
    decoded = base64.b64decode(response.text).decode("utf-8")
    assert decoded.startswith("vless://")


# ----------------------------------------------------------------------------
# Format negotiation: ?format=sing-box
# ----------------------------------------------------------------------------


def test_subscription_explicit_format_xray(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}?format=xray")
    assert response.status_code == 200

    config = response.json()
    assert "routing" in config


def test_subscription_format_sing_box(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}?format=sing-box")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    config = response.json()
    # sing-box has these top-level keys
    assert "route" in config
    assert "outbounds" in config
    assert "experimental" in config
    # And NOT the xray ones
    assert "routing" not in config


def test_subscription_sing_box_contains_user_uuid(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}?format=sing-box")
    config = response.json()

    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")
    # In sing-box, uuid lives directly on the outbound (not in vnext.users)
    assert proxy["uuid"] == alice.uuid


def test_subscription_invalid_format_returns_422(
        client: TestClient, alice: User
) -> None:
    """FastAPI Enum validation rejects unknown formats."""
    response = client.get(f"/sub/{alice.subscription_token}?format=clash")
    assert response.status_code == 422


def test_subscription_format_is_case_sensitive(
        client: TestClient, alice: User
) -> None:
    """Enum values are exact-match — protects us from future renames."""
    response = client.get(f"/sub/{alice.subscription_token}?format=Sing-Box")
    assert response.status_code == 422


def test_subscription_returns_correct_user(
        client: TestClient, alice: User, bob: User
) -> None:
    """Each token resolves to its respective user's link."""
    alice_resp = client.get(f"/sub/{alice.subscription_token}")
    bob_resp = client.get(f"/sub/{bob.subscription_token}")

    alice_link = base64.b64decode(alice_resp.text).decode("utf-8")
    bob_link = base64.b64decode(bob_resp.text).decode("utf-8")

    assert alice.uuid in alice_link
    assert bob.uuid in bob_link
    assert alice.uuid not in bob_link
