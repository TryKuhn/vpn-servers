"""Shared pytest fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from vpn_manager.config import Settings
from vpn_manager.models.user import User


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """A Settings instance with paths under a tmp dir.

    Each test gets its own isolated tmp_path, so tests don't interfere.
    """
    return Settings(
        server_ip="1.2.3.4",
        server_port=443,
        sni="gateway.icloud.com",
        public_key="test-public-key",
        short_id="abcd1234",
        country_flag="🇫🇮",
        server_tag="TestVPN",
        xray_api_addr="127.0.0.1:10085",
        xray_inbound_tag="vless-in",
        data_dir=tmp_path,
        subscription_base_url="https://test.example.com",
    )


@pytest.fixture
def alice() -> User:
    """A canonical test user with a fixed timestamp."""
    return User(
        name="alice",
        uuid="11111111-1111-1111-1111-111111111111",
        email="alice@vpn",
        subscription_token="alice_token_xxxxxxxxxxxxxxxxxxxx",
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def bob() -> User:
    """Another canonical test user, created later than alice."""
    return User(
        name="bob",
        uuid="22222222-2222-2222-2222-222222222222",
        email="bob@vpn",
        subscription_token="bob_token_xxxxxxxxxxxxxxxxxxxxxxxx",
        created_at=datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC),
    )
