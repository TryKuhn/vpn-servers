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


def test_subscription_returns_base64_vless_link(
    client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}")
    assert response.status_code == 200

    decoded = base64.b64decode(response.text).decode("utf-8")
    assert decoded.startswith("vless://")
    assert alice.uuid in decoded


def test_subscription_unknown_token_returns_404(client: TestClient) -> None:
    response = client.get("/sub/this_token_does_not_exist")
    assert response.status_code == 404


def test_subscription_returns_correct_user_link(
    client: TestClient, alice: User, bob: User
) -> None:
    """Each token resolves to its respective user."""
    alice_response = client.get(f"/sub/{alice.subscription_token}")
    bob_response = client.get(f"/sub/{bob.subscription_token}")

    alice_link = base64.b64decode(alice_response.text).decode("utf-8")
    bob_link = base64.b64decode(bob_response.text).decode("utf-8")

    assert alice.uuid in alice_link
    assert bob.uuid in bob_link
    assert alice.uuid not in bob_link
