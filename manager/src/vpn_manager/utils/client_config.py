from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a full xray client config for the given user.

    When ws_domain and ws_path are configured, includes a WebSocket outbound
    as the primary proxy and Reality as a named fallback. Otherwise Reality
    is the sole proxy tagged simply as 'proxy'.
    """
    outbounds: list[dict[str, Any]] = []

    if settings.ws_domain and settings.ws_path:
        outbounds.append(_ws_proxy_outbound(user, settings))
        outbounds.append(_reality_proxy_outbound(user, settings, tag="reality-proxy"))
    else:
        outbounds.append(_reality_proxy_outbound(user, settings, tag="proxy"))

    outbounds += [
        {"tag": "direct", "protocol": "freedom"},
        {"tag": "block", "protocol": "blackhole"},
    ]

    return {
        "log": {"loglevel": "warning"},
        "outbounds": outbounds,
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                {
                    "type": "field",
                    "outboundTag": "block",
                    "domain": ["geosite:category-ads-all"],
                },
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "domain": ["geosite:category-gov-ru"],
                },
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "ip": ["geoip:ru", "geoip:private"],
                },
                {
                    "type": "field",
                    "outboundTag": "proxy",
                    "network": "tcp,udp",
                },
            ],
        },
    }


def _ws_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket outbound via Cloudflare Tunnel or CDN proxy."""
    return {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": settings.ws_domain,
                    "port": settings.ws_port,
                    "users": [{"id": user.uuid, "encryption": "none", "flow": ""}],
                }
            ]
        },
        "streamSettings": {
            "network": "ws",
            "security": "tls",
            "tlsSettings": {
                "serverName": settings.ws_domain,
                "fingerprint": "chrome",
            },
            "wsSettings": {
                "path": f"/{settings.ws_path}",
            },
        },
    }


def _reality_proxy_outbound(user: User, settings: Settings, tag: str) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server, no CDN."""
    return {
        "tag": tag,
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": settings.server_ip,
                    "port": settings.server_port,
                    "users": [
                        {
                            "id": user.uuid,
                            "encryption": "none",
                            "flow": "xtls-rprx-vision",
                        }
                    ],
                }
            ]
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "serverName": settings.sni,
                "fingerprint": "chrome",
                "publicKey": settings.public_key,
                "shortId": settings.short_id,
            },
        },
    }
