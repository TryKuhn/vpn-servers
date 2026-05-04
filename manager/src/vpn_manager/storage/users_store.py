"""Users JSON store: atomic CRUD over `users.json`.

The store is the source of truth for user data. It must be:
- Atomic on writes (either fully old or fully new file, never partial).
- Resilient to missing/empty files (treats them as empty store).
- Thread-safe within a single process (we use a lock).
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from contextlib import suppress
from pathlib import Path

from vpn_manager.models.user import User


class UserAlreadyExistsError(Exception):
    """Raised when adding a user with a name that already exists."""


class UserNotFoundError(Exception):
    """Raised when looking up a user by a name that doesn't exist."""


class UsersStore:
    """Persistent store of users, backed by a JSON file.

    The file format is:

        {
            "users": [
                {
                    "name": "alice",
                    "uuid": "...",
                    "email": "alice@vpn",
                    "created_at": "2026-05-04T12:00:00+00:00"
                },
                ...
            ]
        }

    On every mutating operation (`add`, `remove`), the entire file is
    rewritten atomically.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.RLock()

    @property
    def path(self) -> Path:
        """The filesystem path of this store."""
        return self._path

    # ------------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------------

    def list_all(self) -> list[User]:
        """Return all users, sorted by creation time (oldest first)."""
        with self._lock:
            users = self._load()
            return sorted(users, key=lambda u: u.created_at)

    def get(self, name: str) -> User:
        """Look up a user by name.

        Raises:
            UserNotFoundError: if no user with this name exists.
        """
        with self._lock:
            for user in self._load():
                if user.name == name:
                    return user
            raise UserNotFoundError(f"User {name!r} not found")

    def exists(self, name: str) -> bool:
        """Return True if a user with this name exists."""
        with self._lock:
            try:
                self.get(name)
                return True
            except UserNotFoundError:
                return False

    # ------------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------------

    def add(self, user: User) -> None:
        """Add a new user.

        Raises:
            UserAlreadyExistsError: if a user with this name already exists.
        """
        with self._lock:
            users = self._load()
            if any(u.name == user.name for u in users):
                raise UserAlreadyExistsError(
                    f"User {user.name!r} already exists"
                )
            users.append(user)
            self._save(users)

    def remove(self, name: str) -> User:
        """Remove a user by name.

        Returns the removed user (useful for confirmation messages).

        Raises:
            UserNotFoundError: if no such user exists.
        """
        with self._lock:
            users = self._load()
            for i, user in enumerate(users):
                if user.name == name:
                    users.pop(i)
                    self._save(users)
                    return user
            raise UserNotFoundError(f"User {name!r} not found")

    # ------------------------------------------------------------------------
    # Internal: file I/O
    # ------------------------------------------------------------------------

    def _load(self) -> list[User]:
        """Read the file and return all users.

        Returns an empty list if the file doesn't exist or is empty.
        """
        if not self._path.exists() or self._path.stat().st_size == 0:
            return []

        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)

        return [User.from_dict(d) for d in data.get("users", [])]

    def _save(self, users: list[User]) -> None:
        """Write all users to the file atomically.

        Uses the standard write-temp-then-rename pattern: writes to a
        temporary file in the same directory, then atomically renames it
        over the target. This guarantees that readers never see a
        partial file, even if the process crashes mid-write.
        """
        self._path.parent.mkdir(parents=True, exist_ok=True)

        data = {"users": [u.to_dict() for u in users]}

        # Write to a temp file in the same directory (so rename is atomic;
        # cross-filesystem renames aren't atomic on Linux).
        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent,
            prefix=f".{self._path.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")  # POSIX-friendly newline at EOF
                f.flush()
                os.fsync(f.fileno())  # force write to disk before rename

            os.replace(tmp_path, self._path)
        except Exception:
            # Clean up temp file on any error.
            with suppress(OSError):
                os.unlink(tmp_path)
            raise
