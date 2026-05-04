"""VLESS link generation for Reality + Vision flow."""

from __future__ import annotations

from urllib.parse import quote

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_vless_link(user: User, settings: Settings) -> str:
    """Build a vless:// URI suitable for V2RayTun, Hiddify, etc.

    The label after `#` is URL-encoded so emoji and other Unicode
    characters survive copy-paste through messaging apps that may
    sanitize URLs.

    Format::

        vless://{uuid}@{ip}:{port}?...&sid={short_id}#{flag} {tag}@{name}

    """
    label = f"{settings.country_flag} {settings.server_tag}@{user.name}"
    encoded_label = quote(label)

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
        f"?{params}#{encoded_label}"
    )
