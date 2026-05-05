"""Generation of full xray client configurations for VPN clients.

Subscription endpoints serve these as JSON. Clients (V2RayTun, Hiddify,
v2rayN) import the URL once, then poll periodically for updates. The
config replaces the client's previous settings entirely — including
routing rules.
"""

from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a full xray client config for the given user.

    Routing strategy ('smart routing'):
        - Ads & trackers     → block (saves bandwidth, faster pages)
        - RU IPs & gov sites → direct (banks/gosuslugi see real IP)
        - Private networks   → direct (don't tunnel local LAN)
        - Everything else    → proxy through VPN

    See docs/ARCHITECTURE.md for the rationale on this routing.
    """
    return {
        "log": {"loglevel": "warning"},
        "outbounds": [
            _proxy_outbound(user, settings),
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
        ],
        "routing": {
            "domainStrategy": "IPIfNonMatch",
            "rules": [
                # Ads first — even if hosted on RU IPs, we block them.
                {
                    "type": "field",
                    "outboundTag": "block",
                    "domain": ["geosite:category-ads-all"],
                },
                # Russian gov domains — direct, even if their CDN is foreign.
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "domain": ["geosite:category-gov-ru"],
                },
                # RU IPs — direct (catches services hosted in Russia
                # regardless of domain).
                {
                    "type": "field",
                    "outboundTag": "direct",
                    "ip": ["geoip:ru", "geoip:private"],
                },
                # Everything else — through the VPN.
                {
                    "type": "field",
                    "outboundTag": "proxy",
                    "network": "tcp,udp",
                },
            ],
        },
    }


def _proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """Build the VLESS+Reality outbound — the actual VPN connection."""
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
