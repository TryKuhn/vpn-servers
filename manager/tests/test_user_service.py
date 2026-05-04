"""Tests for vpn_manager.services.user_service.

We mock the XrayClient (we already test it separately). UsersStore is real
because it has no external dependencies and exercising the real code here
gives us better integration coverage.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from vpn_manager.models.user import User
from vpn_manager.services.user_service import UserService
from vpn_manager.storage.users_store import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UsersStore,
)
from vpn_manager.xray.client import (
    XrayApiError,
    XrayClient,
    XrayUserAlreadyExistsError,
    XrayUserNotFoundError,
)

# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path: Path) -> UsersStore:
    return UsersStore(tmp_path / "users.json")


@pytest.fixture
def xray_mock() -> MagicMock:
    return MagicMock(spec=XrayClient)


@pytest.fixture
def service(store: UsersStore, xray_mock: MagicMock) -> UserService:
    return UserService(store=store, xray=xray_mock)


# ----------------------------------------------------------------------------
# add — happy path
# ----------------------------------------------------------------------------


def test_add_creates_user_in_xray_and_storage(
        service: UserService, xray_mock: MagicMock, store: UsersStore
) -> None:
    user = service.add("alice")

    assert user.name == "alice"
    assert user.email == "alice@vpn"
    assert len(user.uuid) == 36  # standard UUID length

    xray_mock.add_user.assert_called_once_with(user)
    assert store.list_all() == [user]


def test_add_assigns_unique_uuids(service: UserService) -> None:
    a = service.add("alice")
    b = service.add("bob")
    assert a.uuid != b.uuid


# ----------------------------------------------------------------------------
# add — duplicate detection
# ----------------------------------------------------------------------------


def test_add_rejects_duplicate_name(service: UserService) -> None:
    service.add("alice")
    with pytest.raises(UserAlreadyExistsError):
        service.add("alice")


def test_add_rejects_duplicate_without_calling_xray(
        service: UserService, xray_mock: MagicMock
) -> None:
    """Pre-flight check: don't bother xray if name is taken."""
    service.add("alice")
    xray_mock.add_user.reset_mock()

    with pytest.raises(UserAlreadyExistsError):
        service.add("alice")

    xray_mock.add_user.assert_not_called()


# ----------------------------------------------------------------------------
# add — failure modes & compensation
# ----------------------------------------------------------------------------


def test_add_does_not_persist_if_xray_rejects(
        service: UserService, xray_mock: MagicMock, store: UsersStore
) -> None:
    """If xray fails, storage must not be touched."""
    xray_mock.add_user.side_effect = XrayApiError("xray is down")

    with pytest.raises(XrayApiError):
        service.add("alice")

    assert store.list_all() == []


def test_add_handles_xray_already_exists(
        service: UserService, xray_mock: MagicMock
) -> None:
    """Storage and xray are out of sync — surface a clear error."""
    xray_mock.add_user.side_effect = XrayUserAlreadyExistsError("dup in xray")

    with pytest.raises(XrayApiError, match="sync"):
        service.add("alice")


# ----------------------------------------------------------------------------
# remove
# ----------------------------------------------------------------------------


def test_remove_calls_xray_and_storage(
        service: UserService, xray_mock: MagicMock, store: UsersStore
) -> None:
    service.add("alice")
    xray_mock.reset_mock()

    removed = service.remove("alice")

    assert removed.name == "alice"
    xray_mock.remove_user.assert_called_once_with("alice@vpn")
    assert store.list_all() == []


def test_remove_nonexistent_raises(service: UserService) -> None:
    with pytest.raises(UserNotFoundError):
        service.remove("ghost")


def test_remove_tolerates_user_missing_from_xray(
        service: UserService, xray_mock: MagicMock, store: UsersStore
) -> None:
    """If xray says 'not found', we still proceed with storage removal."""
    service.add("alice")
    xray_mock.remove_user.side_effect = XrayUserNotFoundError("gone")

    service.remove("alice")  # must NOT raise

    assert store.list_all() == []


# ----------------------------------------------------------------------------
# list / get
# ----------------------------------------------------------------------------


def test_list_returns_oldest_first(service: UserService) -> None:
    a = service.add("alice")
    b = service.add("bob")
    assert service.list_all() == [a, b]


def test_get_returns_user(service: UserService) -> None:
    a = service.add("alice")
    assert service.get("alice") == a


def test_get_missing_raises(service: UserService) -> None:
    with pytest.raises(UserNotFoundError):
        service.get("ghost")


# ----------------------------------------------------------------------------
# sync
# ----------------------------------------------------------------------------


def test_sync_re_adds_all_users_to_xray(
        service: UserService, xray_mock: MagicMock
) -> None:
    a = service.add("alice")
    b = service.add("bob")
    xray_mock.reset_mock()

    count = service.sync()

    assert count == 2
    assert xray_mock.add_user.call_args_list == [call(a), call(b)]


def test_sync_skips_users_already_in_xray(
        service: UserService, xray_mock: MagicMock
) -> None:
    """If xray already has a user, sync should not count it as 're-added'."""
    service.add("alice")
    service.add("bob")
    xray_mock.reset_mock()

    # Simulate alice already in xray, bob fresh
    def add_side_effect(user: object) -> None:
        if getattr(user, "name", None) == "alice":
            raise XrayUserAlreadyExistsError("already there")

    xray_mock.add_user.side_effect = add_side_effect

    count = service.sync()
    assert count == 1


def test_sync_continues_on_individual_errors(
        service: UserService, xray_mock: MagicMock
) -> None:
    """One bad user shouldn't stop the rest."""
    service.add("alice")
    service.add("bob")
    service.add("charlie")
    xray_mock.reset_mock()

    def add_side_effect(user: object) -> None:
        if getattr(user, "name", None) == "bob":
            raise XrayApiError("transient error")

    xray_mock.add_user.side_effect = add_side_effect

    count = service.sync()
    assert count == 2  # alice + charlie, bob failed


def test_sync_on_empty_store(service: UserService) -> None:
    assert service.sync() == 0


# ----------------------------------------------------------------------------
# add_many
# ----------------------------------------------------------------------------


def test_add_many_creates_all_users(
        service: UserService, xray_mock: MagicMock
) -> None:
    users = service.add_many(["alice", "bob", "charlie"])

    assert len(users) == 3
    assert [u.name for u in users] == ["alice", "bob", "charlie"]
    assert xray_mock.add_user.call_count == 3


def test_add_many_pre_validates_existing_names(
        service: UserService, xray_mock: MagicMock
) -> None:
    """If any name already exists, NO users should be added."""
    service.add("alice")
    xray_mock.reset_mock()

    with pytest.raises(UserAlreadyExistsError, match="alice"):
        service.add_many(["bob", "alice", "charlie"])

    # Crucially: bob and charlie were NOT added either, because
    # pre-validation runs BEFORE any mutations.
    assert xray_mock.add_user.call_count == 0
    assert {u.name for u in service.list_all()} == {"alice"}


def test_add_many_pre_validates_duplicate_names_in_batch(
        service: UserService, xray_mock: MagicMock
) -> None:
    """Duplicates within the input list must be rejected upfront."""
    with pytest.raises(UserAlreadyExistsError, match="Duplicate"):
        service.add_many(["alice", "bob", "alice"])

    assert xray_mock.add_user.call_count == 0
    assert service.list_all() == []


def test_add_many_empty_list(service: UserService, xray_mock: MagicMock) -> None:
    """add_many([]) is a no-op."""
    result = service.add_many([])
    assert result == []
    assert xray_mock.add_user.call_count == 0


def test_add_many_partial_failure_keeps_earlier_users(
        service: UserService, xray_mock: MagicMock
) -> None:
    """If xray fails midway, earlier-added users stay added.

    Each user is its own unit of work; we don't roll back the batch.
    """
    # Make xray fail on the second user
    call_count = {"n": 0}

    def add_side_effect(user: User) -> None:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise XrayApiError("simulated failure")

    xray_mock.add_user.side_effect = add_side_effect

    with pytest.raises(XrayApiError, match="simulated failure"):
        service.add_many(["alice", "bob", "charlie"])

    # alice was added successfully before the failure
    names = {u.name for u in service.list_all()}
    assert names == {"alice"}
