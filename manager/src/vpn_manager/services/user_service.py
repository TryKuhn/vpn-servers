"""User management service: orchestrates storage + xray API.

This is the only place where business operations live. CLI commands,
the future HTTP API, and the future Telegram bot will all call into
this service rather than touching storage and xray directly.
"""

from __future__ import annotations

import logging
import uuid as uuid_lib
from dataclasses import dataclass

from vpn_manager.models.user import User
from vpn_manager.storage.users_store import (
    UserAlreadyExistsError,
    UsersStore,
)
from vpn_manager.xray.client import (
    XrayApiError,
    XrayClient,
    XrayUserAlreadyExistsError,
    XrayUserNotFoundError,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserService:
    """Business operations on users.

    The service ensures that the running xray instance and the on-disk
    users.json stay in sync: any user in xray is in the file, and vice
    versa.

    On failures, we follow a "compensate-on-error" pattern: if a write
    to xray succeeds but storage fails, we roll back xray to keep them
    consistent.
    """

    store: UsersStore
    xray: XrayClient

    # ------------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------------

    def list_all(self) -> list[User]:
        """Return all users, oldest first."""
        return self.store.list_all()

    def get(self, name: str) -> User:
        """Look up a user by name.

        Raises:
            UserNotFoundError: if no such user.
        """
        return self.store.get(name)

    # ------------------------------------------------------------------------
    # Mutating operations
    # ------------------------------------------------------------------------

    def add(self, name: str) -> User:
        """Create a new user, persist, and register with xray.

        Generates a fresh UUID. The user becomes immediately usable —
        no xray restart required.

        Raises:
            UserAlreadyExistsError: if a user with this name already
                exists in storage.
            XrayApiError: if xray rejects the operation (e.g. it's down,
                or the user already exists in xray's runtime state).
        """
        # Pre-flight: fail fast if the name is taken in storage.
        if self.store.exists(name):
            raise UserAlreadyExistsError(f"User {name!r} already exists")

        user = User.new(name=name, uuid=str(uuid_lib.uuid4()))

        # 1) Add to live xray. If this fails, nothing has been persisted yet.
        try:
            self.xray.add_user(user)
        except XrayUserAlreadyExistsError:
            # The user is in xray's runtime but not in our storage.
            # This means the two are out of sync — likely manual edit
            # or a previous failed add. Surface a clear error.
            raise XrayApiError(
                f"User {user.email!r} exists in xray but not in storage. "
                f"Run 'vpn-user sync' to reconcile."
            ) from None

        # 2) Persist. If this fails, compensate by removing from xray.
        try:
            self.store.add(user)
        except Exception as e:
            log.error(
                "Failed to persist user %s after xray.add succeeded; "
                "rolling back xray. Original error: %s",
                user.name, e,
            )
            try:
                self.xray.remove_user(user.email)
            except XrayApiError as rollback_error:
                # Worst case: xray has the user, storage doesn't.
                # Logged loudly so it can be reconciled with `sync`.
                log.critical(
                    "Compensation failed: user %s is now in xray "
                    "but not in storage. Manual sync required. "
                    "Rollback error: %s",
                    user.email, rollback_error,
                )
            raise

        log.info("Added user %s (uuid=%s)", user.name, user.uuid)
        return user

    def remove(self, name: str) -> User:
        """Remove a user from xray and storage.

        Returns the removed user (useful for confirmation messages).

        Raises:
            UserNotFoundError: if no such user in storage.
            XrayApiError: if xray rejects the operation.
        """
        user = self.store.get(name)  # raises UserNotFoundError if missing

        # 1) Remove from live xray. We tolerate "not found" because the
        # user being absent from xray runtime means the desired state
        # (gone) is already achieved for that side.
        try:
            self.xray.remove_user(user.email)
        except XrayUserNotFoundError:
            log.warning(
                "User %s was in storage but not in xray runtime. "
                "Removing from storage only.",
                user.email,
            )

        # 2) Remove from storage. If this fails, we have a problem
        # (xray-removed but storage-kept), but storage failures are
        # extremely rare and we don't have a way to "undo" the xray
        # removal without re-inviting concurrency issues.
        self.store.remove(name)

        log.info("Removed user %s", user.name)
        return user

    def sync(self) -> int:
        """Re-apply all stored users to the running xray instance.

        Useful after xray restarts (its runtime state is empty until
        we re-register everyone). Returns the number of users
        successfully (re-)added.

        Users already present in xray are silently skipped — this
        operation is idempotent.
        """
        users = self.store.list_all()
        added = 0

        for user in users:
            try:
                self.xray.add_user(user)
                added += 1
            except XrayUserAlreadyExistsError:
                # Already in xray, that's the goal anyway.
                log.debug("User %s already in xray; skipping", user.email)
            except XrayApiError as e:
                log.error("Failed to sync user %s: %s", user.email, e)

        log.info("Sync complete: %d/%d users (re-)added", added, len(users))
        return added
