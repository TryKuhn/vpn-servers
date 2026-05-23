from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User

_RULESET_BASE = (
    "https://raw.githubusercontent.com/runetfreedom/"
    "russia-v2ray-rules-dat/release/sing-box"
)


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a remote rule-set URL for the given geo kind and tag."""
    return f"{_RULESET_BASE}/rule-set-{kind}/{kind}-{tag}.srs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete sing-box client config for the given user.

    When ws_domain and ws_path are configured, the WebSocket outbound is
    primary (tagged 'proxy') and Reality is a named fallback. Otherwise
    Reality is the sole proxy.
    """
    outbounds: list[dict[str, Any]] = []

    if settings.ws_domain and settings.ws_path:
        outbounds.append(_ws_proxy_outbound(user, settings))
        outbounds.append(_reality_proxy_outbound(user, settings, tag="reality-proxy"))
    else:
        outbounds.append(_reality_proxy_outbound(user, settings, tag="proxy"))

    outbounds += [
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"},
    ]

    return {
        "log": {"level": "warn"},
        "outbounds": outbounds,
        "route": _route_section(),
        "experimental": {
            "cache_file": {"enabled": True}
        },
    }


def _ws_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket outbound via Cloudflare Tunnel or CDN proxy."""
    return {
        "type": "vless",
        "tag": "proxy",
        "server": settings.ws_domain,
        "server_port": settings.ws_port,
        "uuid": user.uuid,
        "transport": {
            "type": "ws",
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.ws_domain},
        },
        "tls": {
            "enabled": True,
            "server_name": settings.ws_domain,
            "utls": {
                "enabled": True,
                "fingerprint": "chrome",
            },
        },
    }


def _reality_proxy_outbound(user: User, settings: Settings, tag: str) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server, no CDN."""
    return {
        "type": "vless",
        "tag": tag,
        "server": settings.server_ip,
        "server_port": settings.server_port,
        "uuid": user.uuid,
        "flow": "xtls-rprx-vision",
        "tls": {
            "enabled": True,
            "server_name": settings.sni,
            "utls": {
                "enabled": True,
                "fingerprint": "chrome",
            },
            "reality": {
                "enabled": True,
                "public_key": settings.public_key,
                "short_id": settings.short_id,
            },
        },
    }


def _route_section() -> dict[str, Any]:
    """Build the route section with all rule-sets and ordered routing rules."""
    return {
        "final": "proxy",
        "rules": [
            {
                "rule_set": ["geosite-category-ads-all"],
                "outbound": "block",
            },
            {
                "rule_set": ["geosite-ru-blocked", "geoip-ru-blocked"],
                "outbound": "proxy",
            },
            {
                "rule_set": ["geosite-telegram", "geoip-telegram"],
                "outbound": "proxy",
            },
            {
                "rule_set": [
                    "geosite-category-bank-ru",
                    "geosite-category-gov-ru",
                    "geosite-category-medicine-ru",
                    "geosite-category-ecommerce-ru",
                    "geoip-ru",
                ],
                "outbound": "direct",
            },
            {
                "ip_is_private": True,
                "outbound": "direct",
            },
        ],
        "rule_set": [
            _remote_ruleset("geosite", "category-ads-all"),
            _remote_ruleset("geosite", "ru-blocked"),
            _remote_ruleset("geoip", "ru-blocked"),
            _remote_ruleset("geosite", "category-bank-ru"),
            _remote_ruleset("geosite", "category-gov-ru"),
            _remote_ruleset("geosite", "category-medicine-ru"),
            _remote_ruleset("geosite", "category-ecommerce-ru"),
            _remote_ruleset("geoip", "ru"),
            _remote_ruleset("geosite", "telegram"),
            _remote_ruleset("geoip", "telegram"),
        ],
    }


def _remote_ruleset(kind: str, tag: str) -> dict[str, Any]:
    """Build a single remote rule-set entry downloaded through the VPN proxy."""
    return {
        "tag": f"{kind}-{tag}",
        "type": "remote",
        "format": "binary",
        "url": _ruleset_url(kind, tag),
        "download_detour": "proxy",
    }
