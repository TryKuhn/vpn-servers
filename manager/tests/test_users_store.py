"""Tests for vpn_manager.storage.users_store."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpn_manager.models.user import User
from vpn_manager.storage.users_store import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UsersStore,
)


@pytest.fixture
def store(tmp_path: Path) -> UsersStore:
    """A UsersStore backed by a fresh tmp file."""
    return UsersStore(tmp_path / "users.json")


# ----------------------------------------------------------------------------
# Empty store
# ----------------------------------------------------------------------------


def test_empty_store_lists_nothing(store: UsersStore) -> None:
    assert store.list_all() == []


def test_empty_store_get_raises(store: UsersStore) -> None:
    with pytest.raises(UserNotFoundError):
        store.get("alice")


def test_empty_store_exists_returns_false(store: UsersStore) -> None:
    assert store.exists("alice") is False


# ----------------------------------------------------------------------------
# Add
# ----------------------------------------------------------------------------


def test_add_persists_user(store: UsersStore, alice: User) -> None:
    store.add(alice)
    assert store.list_all() == [alice]


def test_add_duplicate_raises(store: UsersStore, alice: User) -> None:
    store.add(alice)
    with pytest.raises(UserAlreadyExistsError):
        store.add(alice)


def test_add_persists_across_instances(
    tmp_path: Path, alice: User
) -> None:
    """Verify that data survives recreating the store object."""
    path = tmp_path / "users.json"

    UsersStore(path).add(alice)
    assert UsersStore(path).list_all() == [alice]


# ----------------------------------------------------------------------------
# Remove
# ----------------------------------------------------------------------------


def test_remove_returns_user(store: UsersStore, alice: User) -> None:
    store.add(alice)
    removed = store.remove("alice")
    assert removed == alice
    assert store.list_all() == []


def test_remove_nonexistent_raises(store: UsersStore) -> None:
    with pytest.raises(UserNotFoundError):
        store.remove("ghost")


# ----------------------------------------------------------------------------
# List ordering
# ----------------------------------------------------------------------------


def test_list_all_sorts_by_creation_time(
    store: UsersStore, alice: User, bob: User
) -> None:
    # Add in reverse creation order
    store.add(bob)
    store.add(alice)

    # But list_all returns oldest first
    assert store.list_all() == [alice, bob]


# ----------------------------------------------------------------------------
# Get / exists
# ----------------------------------------------------------------------------


def test_get_returns_correct_user(
    store: UsersStore, alice: User, bob: User
) -> None:
    store.add(alice)
    store.add(bob)

    assert store.get("alice") == alice
    assert store.get("bob") == bob


def test_exists_returns_true_for_present(store: UsersStore, alice: User) -> None:
    store.add(alice)
    assert store.exists("alice") is True


# ----------------------------------------------------------------------------
# Atomicity / file behavior
# ----------------------------------------------------------------------------


def test_save_creates_parent_dirs(tmp_path: Path, alice: User) -> None:
    """Store creates parent directories if they don't exist."""
    deep_path = tmp_path / "deeply" / "nested" / "users.json"
    store = UsersStore(deep_path)
    store.add(alice)

    assert deep_path.exists()


def test_no_temp_files_left_after_save(
    store: UsersStore, alice: User
) -> None:
    """After a successful save, no .tmp files should remain."""
    store.add(alice)

    leftovers = list(store.path.parent.glob(".*.tmp"))
    assert leftovers == []
