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
    XrayApiUnavailableError,
    XrayClient,
    XrayUserNotFoundError,
    XrayUserAlreadyExistsError,
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
                newly = self.xray.sync_user(user)
                if newly > 0:
                    added += 1
            except XrayApiUnavailableError:
                raise  # xray is completely down — let the caller decide
            except XrayApiError as e:
                log.error("Failed to sync user %s: %s", user.email, e)

        log.info("Sync complete: %d/%d users (re-)added", added, len(users))
        return added

    def add_many(self, names: list[str]) -> list[User]:
        """Add multiple users in a batch with pre-validation.

        Pre-flight: check all names against storage. If any name is
        already taken, raise UserAlreadyExistsError WITHOUT touching
        anything. This guarantees an "all or nothing" experience for
        the user — they don't end up with a partial set of new accounts.

        Once pre-validation passes, users are added one at a time. If a
        single add fails (xray rejection, network blip, etc.), already
        added users stay added — we don't try to roll them back, since
        each one is a complete unit of work.

        Returns:
            List of created users, in the same order as input names.

        Raises:
            UserAlreadyExistsError: if any input name is already taken.
                In this case, NO users are added.
            XrayApiError: if xray rejects an add midway. Earlier successful
                adds are kept.
        """
        # --- Pre-validation: all-or-nothing semantics ---
        existing = [name for name in names if self.store.exists(name)]
        if existing:
            raise UserAlreadyExistsError(
                f"User(s) already exist: {', '.join(repr(n) for n in existing)}. "
                f"No users were added."
            )

        # Also catch duplicates within the input list itself, e.g.
        # `vpn-user add alice alice` would otherwise add the first one,
        # then fail on the second with a confusing 'already exists'.
        seen: set[str] = set()
        duplicates = [n for n in names if n in seen or seen.add(n)]  # type: ignore[func-returns-value]
        if duplicates:
            raise UserAlreadyExistsError(
                f"Duplicate name(s) in batch: {', '.join(repr(n) for n in duplicates)}"
            )

        # --- Add one at a time ---
        created: list[User] = []
        for name in names:
            user = self.add(name)  # reuses single-user logic, including
            # compensate-on-error
            created.append(user)
        return created

    def rotate_subscription_token(self, name: str) -> User:
        """Generate a new subscription token for an existing user.

        The user's UUID and xray runtime entry are NOT changed — only
        the subscription URL becomes invalid. After rotation:
          - The old `/sub/<old_token>` URL returns 404.
          - The user's existing client connection (already imported)
            keeps working until the client tries to re-fetch.
          - The new `/sub/<new_token>` URL must be re-shared with the user.

        Use case: subscription token leaked, user lost device, etc.

        Raises:
            UserNotFoundError: if no user with this name exists.
        """
        user = self.store.get(name)

        # Build a new user with a freshly-generated token. dataclass.replace
        # would be cleaner, but User is frozen and we want explicit control.
        from vpn_manager.models.user import _generate_subscription_token

        rotated = User(
            name=user.name,
            uuid=user.uuid,
            email=user.email,
            subscription_token=_generate_subscription_token(),
            created_at=user.created_at,
        )

        # Persist by remove + add (UsersStore doesn't have an update method).
        self.store.remove(name)
        try:
            self.store.add(rotated)
        except Exception:
            # Restore the old user if save fails. add() shouldn't really
            # fail here (we just removed the same name), but defense in
            # depth.
            self.store.add(user)
            raise

        return rotated
