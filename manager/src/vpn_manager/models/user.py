"""User domain model."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class User:
    """A VPN user.

    Identified primarily by `name` (human-readable, e.g. "alice").
    The `uuid` is the actual VLESS credential — anyone with it can
    connect to the server as this user.

    The `email` field is used by xray as an internal identifier in its
    API; we generate it from the name as `{name}@vpn`. It is not a real
    email address.
    """

    name: str
    uuid: str
    email: str
    created_at: datetime

    # ------------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------------

    @classmethod
    def new(cls, name: str, uuid: str) -> User:
        """Create a new user with `created_at` set to now (UTC)."""
        return cls(
            name=name,
            uuid=uuid,
            email=f"{name}@vpn",
            created_at=datetime.now(tz=UTC),
        )

    # ------------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-friendly dict."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Reconstruct a User from its dict representation.

        Raises:
            KeyError: if required fields are missing.
            ValueError: if `created_at` is not a valid ISO-8601 timestamp.
        """
        return cls(
            name=data["name"],
            uuid=data["uuid"],
            email=data["email"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )
