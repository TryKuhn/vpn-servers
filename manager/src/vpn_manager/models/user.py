"""User domain model."""

from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


def _generate_subscription_token() -> str:
    """Generate a cryptographically secure URL-safe token.

    32 bytes → 256 bits of entropy → impossible to brute-force.
    URL-safe base64 → fits in URLs without escaping.
    """
    return secrets.token_urlsafe(32)


@dataclass(frozen=True, slots=True)
class User:
    """A VPN user."""

    name: str
    uuid: str
    email: str
    subscription_token: str
    created_at: datetime

    @classmethod
    def new(cls, name: str, uuid: str) -> User:
        """Create a new user with `created_at` set to now (UTC)."""
        return cls(
            name=name,
            uuid=uuid,
            email=f"{name}@vpn",
            subscription_token=_generate_subscription_token(),
            created_at=datetime.now(tz=UTC),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-friendly dict."""
        d = asdict(self)
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Reconstruct a User from its dict representation.

        Backwards-compatible with users created before subscription tokens
        existed: missing fields get freshly generated tokens.
        """
        return cls(
            name=data["name"],
            uuid=data["uuid"],
            email=data["email"],
            # Backwards compat: legacy users without tokens get one generated.
            # On the next save, the token will be persisted.
            subscription_token=data.get("subscription_token") or _generate_subscription_token(),
            created_at=datetime.fromisoformat(data["created_at"]),
        )
