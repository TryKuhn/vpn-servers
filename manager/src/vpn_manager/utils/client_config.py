from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a full xray client config for the given user."""
    return {
        "log": {"loglevel": "warning"},
        "outbounds": [
            _reality_proxy_outbound(user, settings),
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
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
                    "ip": ["geoip:private"],
                },
                {
                    "type": "field",
                    "outboundTag": "proxy",
                    "network": "tcp,udp",
                },
            ],
        },
    }


def _reality_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server."""
    return {
        "tag": "proxy",
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
