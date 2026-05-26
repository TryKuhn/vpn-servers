from __future__ import annotations

from urllib.parse import quote

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_vless_links(user: User, settings: Settings) -> str:
    """Return all configured proxy links joined by newlines (v2ray subscription format)."""
    links: list[str] = []

    if settings.server_domain and settings.ws_path:
        links.append(_build_ws_link(
            user=user,
            server=settings.server_domain,
            port=settings.ws_port,
            ws_path=settings.ws_path,
            label=f"{settings.country_flag} {settings.server_tag} WS@{user.name}",
        ))

    if settings.cloudflare_ws_domain and settings.ws_path:
        links.append(_build_ws_link(
            user=user,
            server=settings.cloudflare_ws_domain,
            port=settings.ws_port,
            ws_path=settings.ws_path,
            label=f"{settings.country_flag} {settings.server_tag} CF@{user.name}",
        ))

    links.append(_build_reality_link(user, settings))

    return "\n".join(links)


def build_vless_link(user: User, settings: Settings) -> str:
    """Build a vless:// URI for VLESS+Reality (single link, legacy use)."""
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


def _build_ws_link(
    user: User,
    server: str,
    port: int,
    ws_path: str,
    label: str,
) -> str:
    params = (
        f"type=ws"
        f"&security=tls"
        f"&sni={server}"
        f"&fp=chrome"
        f"&path={quote('/' + ws_path)}"
        f"&host={server}"
    )
    return (
        f"vless://{user.uuid}@{server}:{port}"
        f"?{params}#{quote(label)}"
    )
