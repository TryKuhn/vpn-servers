"""FastAPI application factory.

The HTTP API serves subscription URLs to VPN clients. Clients import
their personal subscription URL once; the client app polls it
periodically for config updates.
"""

from __future__ import annotations

import base64
import json
import logging
from enum import StrEnum

from fastapi import FastAPI, HTTPException, Response

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.storage.users_store import UsersStore
from vpn_manager.utils.clash_config import render_yaml as render_clash_config
from vpn_manager.utils.client_config import build_client_config as build_xray_config
from vpn_manager.utils.singbox_config import build_client_config as build_singbox_config
from vpn_manager.utils.vless_link import build_vless_link

log = logging.getLogger(__name__)


class SubscriptionFormat(StrEnum):
    """Format of the client config served by the subscription endpoint.

    Values are exposed as query-param strings, so they're stable
    public API and shouldn't be renamed lightly.
    """

    LINK = "link"
    XRAY = "xray"
    SING_BOX = "sing-box"
    CLASH = "clash"


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
    def subscription(
            token: str,
            format: SubscriptionFormat = SubscriptionFormat.LINK,
    ) -> Response:
        """Serve the user's subscription in the requested format.

        Default (no `?format=`) is the classic base64 VLESS-link format
        that's universally supported. xray, sing-box and clash JSON/YAML
        formats are opt-in for clients that benefit from them.

        Returns 404 if the token doesn't match any user.
        Returns 422 (FastAPI default) if `format` is not a known value.
        """
        user = _resolve_user(token, store)

        if format is SubscriptionFormat.CLASH:
            body = render_clash_config(user, settings)
            # text/yaml is the de-facto Content-Type for Clash subscriptions.
            # Mihomo clients accept text/plain too, but text/yaml is more
            # honest about what we're returning.
            return Response(content=body, media_type="text/yaml")

        if format is SubscriptionFormat.SING_BOX:
            config = build_singbox_config(user, settings)
            body = json.dumps(config, indent=2, ensure_ascii=False)
            return Response(content=body, media_type="application/json")

        if format is SubscriptionFormat.XRAY:
            config = build_xray_config(user, settings)
            body = json.dumps(config, indent=2, ensure_ascii=False)
            return Response(content=body, media_type="application/json")

        # Default: base64-encoded VLESS share link.
        link = build_vless_link(user, settings)
        encoded = base64.b64encode(link.encode("utf-8")).decode("ascii")
        return Response(content=encoded, media_type="text/plain")

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
