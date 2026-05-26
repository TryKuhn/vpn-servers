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
from vpn_manager.utils.vless_link import build_vless_links

log = logging.getLogger(__name__)


class SubscriptionFormat(StrEnum):
    """Subscription config format requested via the `format` query parameter."""

    LINK = "link"
    XRAY = "xray"
    SING_BOX = "sing-box"
    CLASH = "clash"


def create_app(settings: Settings, store: UsersStore) -> FastAPI:
    """Create the FastAPI application with settings and user store wired in."""
    app = FastAPI(
        title="vpn-manager subscription API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Liveness probe."""
        return {"status": "ok"}

    @app.get("/sub/{token}")
    def subscription(
            token: str,
            format: SubscriptionFormat = SubscriptionFormat.CLASH,
    ) -> Response:
        """Serve the user's VPN config in the requested format.

        Returns 404 if no user has this subscription token.
        Default format is Clash YAML (consumed by Clash Verge and CMFA).
        """
        user = _resolve_user(token, store)

        if format is SubscriptionFormat.CLASH:
            body = render_clash_config(user, settings)
            return Response(content=body, media_type="text/yaml")

        if format is SubscriptionFormat.SING_BOX:
            config = build_singbox_config(user, settings)
            body = json.dumps(config, indent=2, ensure_ascii=False)
            return Response(content=body, media_type="application/json")

        if format is SubscriptionFormat.XRAY:
            config = build_xray_config(user, settings)
            body = json.dumps(config, indent=2, ensure_ascii=False)
            return Response(content=body, media_type="application/json")

        link = build_vless_links(user, settings)
        encoded = base64.b64encode(link.encode("utf-8")).decode("ascii")
        return Response(content=encoded, media_type="text/plain")

    return app


def _resolve_user(token: str, store: UsersStore) -> User:
    """Look up the user by subscription token, raising HTTP 404 if not found."""
    for user in store.list_all():
        if user.subscription_token == token:
            return user

    log.info("Unknown subscription token requested")
    raise HTTPException(status_code=404, detail="Not found")
