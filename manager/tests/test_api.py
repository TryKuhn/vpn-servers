"""Tests for vpn_manager.api.app."""

from __future__ import annotations

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


def test_subscription_returns_json_xray_config(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    config = response.json()

    # Top-level shape
    assert "outbounds" in config
    assert "routing" in config

    # Has VPN outbound + direct + block
    outbound_tags = {o["tag"] for o in config["outbounds"]}
    assert outbound_tags == {"proxy", "direct", "block"}

    # Proxy outbound has the user's UUID
    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")
    proxy_uuid = proxy["settings"]["vnext"][0]["users"][0]["id"]
    assert proxy_uuid == alice.uuid


# ----------------------------------------------------------------------------
# Format negotiation: ?format=sing-box
# ----------------------------------------------------------------------------


def test_subscription_default_format_is_xray(
        client: TestClient, alice: User
) -> None:
    """No query param = legacy xray-config (backwards compat)."""
    response = client.get(f"/sub/{alice.subscription_token}")
    assert response.status_code == 200

    config = response.json()
    # xray uses `routing`, sing-box uses `route` — quick discriminator
    assert "routing" in config
    assert "route" not in config


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


def test_subscription_routing_rules_present(
        client: TestClient, alice: User
) -> None:
    response = client.get(f"/sub/{alice.subscription_token}")
    config = response.json()
    rules = config["routing"]["rules"]

    # Should have at least: ads-block, gov-ru-direct, ru-ip-direct, default-proxy
    rule_tags = [r["outboundTag"] for r in rules]
    assert "block" in rule_tags
    assert "direct" in rule_tags
    assert "proxy" in rule_tags


def test_subscription_returns_correct_user(
        client: TestClient, alice: User, bob: User
) -> None:
    """Each token resolves to its respective user's UUID."""
    alice_resp = client.get(f"/sub/{alice.subscription_token}")
    bob_resp = client.get(f"/sub/{bob.subscription_token}")

    alice_uuid = alice_resp.json()["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"]
    bob_uuid = bob_resp.json()["outbounds"][0]["settings"]["vnext"][0]["users"][0]["id"]

    assert alice_uuid == alice.uuid
    assert bob_uuid == bob.uuid
