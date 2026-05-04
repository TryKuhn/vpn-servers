"""Tests for vpn_manager.models.user."""

from __future__ import annotations

from datetime import UTC, datetime

from vpn_manager.models.user import User


def test_new_creates_user_with_current_time() -> None:
    before = datetime.now(tz=UTC)
    u = User.new(name="alice", uuid="abc")
    after = datetime.now(tz=UTC)

    assert u.name == "alice"
    assert u.uuid == "abc"
    assert u.email == "alice@vpn"
    assert before <= u.created_at <= after


def test_to_dict_serializes_datetime_as_iso() -> None:
    u = User(
        name="alice",
        uuid="abc",
        email="alice@vpn",
        subscription_token="test_token",
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
    )
    d = u.to_dict()

    assert d == {
        "name": "alice",
        "uuid": "abc",
        "email": "alice@vpn",
        "subscription_token": "test_token",
        "created_at": "2026-01-01T12:00:00+00:00",
    }


def test_from_dict_roundtrip() -> None:
    original = User.new(name="bob", uuid="xyz")
    restored = User.from_dict(original.to_dict())

    assert restored == original


def test_user_is_frozen(alice: User) -> None:
    import pytest

    with pytest.raises(AttributeError):
        alice.name = "mallory"  # type: ignore[misc]

def test_new_generates_unique_subscription_tokens() -> None:
    """Each new user gets a different subscription token."""
    a = User.new(name="a", uuid="u1")
    b = User.new(name="b", uuid="u2")
    assert a.subscription_token != b.subscription_token
    assert len(a.subscription_token) > 30  # token_urlsafe(32) gives ~43 chars


def test_from_dict_handles_legacy_users_without_token() -> None:
    """Existing users from before subscription tokens get one generated."""
    legacy_data = {
        "name": "alice",
        "uuid": "abc",
        "email": "alice@vpn",
        "created_at": "2026-01-01T12:00:00+00:00",
        # no subscription_token
    }
    user = User.from_dict(legacy_data)
    assert user.subscription_token  # not empty
    assert len(user.subscription_token) > 30
