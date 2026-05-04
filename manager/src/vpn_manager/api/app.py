"""FastAPI application factory.

The HTTP API serves subscription URLs to VPN clients. Clients import
their personal subscription URL once; the client app polls it
periodically for config updates.
"""

from __future__ import annotations

import base64
import logging

from fastapi import FastAPI, HTTPException

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.storage.users_store import UsersStore
from vpn_manager.utils.vless_link import build_vless_link

log = logging.getLogger(__name__)


def create_app(settings: Settings, store: UsersStore) -> FastAPI:
    """Build the FastAPI application with dependencies wired in.

    We pass settings and store explicitly rather than using FastAPI's
    Depends() machinery — this is a tiny app and explicit is clearer.
    """
    app = FastAPI(
        title="vpn-manager subscription API",
        # Hide docs in production. Subscription endpoints are not
        # something we want to expose publicly via /docs.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe. Used by nginx upstream check."""
        return {"status": "ok"}

    @app.get("/sub/{token}")
    def subscription(token: str) -> str:
        """Return the user's subscription as a base64-encoded VLESS link.

        Format note: most VLESS clients (V2RayTun, Hiddify, v2rayN)
        support two subscription content types:

          1. Plain or base64-encoded list of vless:// URIs (one per line).
          2. Full xray-core JSON config.

        For Step A we return the simplest form: a single base64 vless://
        URI. Step C (smart routing) will switch to JSON to include
        routing rules.
        """
        user = _resolve_user(token, store)
        link = build_vless_link(user, settings)

        # Subscription content per V2Ray/Xray convention is base64-encoded.
        # Multiple links would be newline-separated. We have one for now.
        encoded = base64.b64encode(link.encode("utf-8")).decode("ascii")
        return encoded

    return app


def _resolve_user(token: str, store: UsersStore) -> User:
    """Look up the user owning this subscription token.

    Raises:
        HTTPException 404 if no user has this token.
    """
    # Linear scan is fine for our scale (<1000 users). If we ever grow
    # past that, build an index when loading users.json.
    for user in store.list_all():
        if user.subscription_token == token:
            return user

    # Slow-equal length comparison was already done by string equality
    # above with full content; we don't need timing-attack mitigation
    # because tokens are 256-bit random and equally improbable to guess
    # regardless of timing leaks.
    log.info("Unknown subscription token requested")
    raise HTTPException(status_code=404, detail="Not found")
