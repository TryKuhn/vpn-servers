from __future__ import annotations

import re
import secrets
import uuid


def new_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def new_password(nbytes: int = 24) -> str:
    return secrets.token_urlsafe(nbytes)


def new_uuid() -> str:
    return str(uuid.uuid4())


def slugify(value: str, *, max_len: int = 64) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9_-]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_")
    return (value or "user")[:max_len]
