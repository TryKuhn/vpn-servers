"""FastAPI application factory.

The HTTP API serves subscription URLs to VPN clients. Clients import
their personal subscription URL once; the client app polls it
periodically for config updates.
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, Response

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.storage.users_store import UsersStore
from vpn_manager.utils.client_config import build_client_config

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
    def subscription(token: str) -> Response:
        """Return the user's full xray client config as JSON.

        The client (V2RayTun, Hiddify, v2rayN) imports this URL and uses the
        JSON as its complete xray configuration — including routing rules
        that handle split tunneling automatically.
        """
        user = _resolve_user(token, store)
        config = build_client_config(user, settings)
        body = json.dumps(config, indent=2, ensure_ascii=False)
        return Response(content=body, media_type="application/json")
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
