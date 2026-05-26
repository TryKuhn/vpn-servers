from __future__ import annotations

from urllib.parse import quote

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_vless_links(user: User, settings: Settings) -> str:
    """Return the VLESS+Reality link (v2ray subscription format)."""
    return _build_reality_link(user, settings)


def build_vless_link(user: User, settings: Settings) -> str:
    """Build a vless:// URI for VLESS+Reality."""
    return _build_reality_link(user, settings)


def _build_reality_link(user: User, settings: Settings) -> str:
    label = f"{settings.country_flag} {settings.server_tag} Reality@{user.name}"
    params = (
        f"security=reality"
        f"&encryption=none"
        f"&pbk={settings.public_key}"
        f"&fp=chrome"
        f"&type=tcp"
        f"&flow=xtls-rprx-vision"
        f"&sni={settings.sni}"
        f"&sid={settings.short_id}"
    )
    return (
        f"vless://{user.uuid}@{settings.server_ip}:{settings.server_port}"
        f"?{params}#{quote(label)}"
    )
