"""Generation of sing-box client configurations.

Sing-box is the proxy core used by V2RayTun, Hiddify, NekoBox, and other
modern clients. Unlike the xray-config we serve elsewhere, these clients
respect the routing rules we ship — so smart split-tunneling is delivered
to the user automatically.

Routing strategy (rules are evaluated top-to-bottom, first match wins):
  1. Ads & trackers           → block
  2. RU-blocked sites/IPs     → proxy (e.g. Twitter, LinkedIn — they need VPN)
  3. RU services & private    → direct (banks, gov, medicine, ecommerce, RU IPs)
  4. Everything else (final)  → proxy

Rule-sets are downloaded from runetfreedom/russia-v2ray-rules-dat — the
gold-standard collection for Russian users. Updates every 6 hours.

The client must download rule-sets at first start. We use
download_detour=proxy so this happens THROUGH the VPN — important for
users behind whitelisting where GitHub itself may be blocked.
"""

from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User

# Base URL for runetfreedom rule-sets. Files are auto-updated every 6 hours.
_RULESET_BASE = (
    "https://raw.githubusercontent.com/runetfreedom/"
    "russia-v2ray-rules-dat/release/sing-box"
)


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a remote rule-set URL.

    Args:
        kind: Either 'geosite' or 'geoip'.
        tag: Category name without the kind prefix, e.g. 'ru-blocked'.
    """
    return f"{_RULESET_BASE}/rule-set-{kind}/{kind}-{tag}.srs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete sing-box client config for the given user."""
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
    """VLESS+WebSocket outbound — via Cloudflare Tunnel or CDN proxy."""
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
    """VLESS+Reality outbound — direct connection, no CDN."""
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
    """Build the route section — rules + rule-set definitions."""
    return {
        # `final` is the catch-all; everything not caught by an explicit
        # rule goes here. We send to proxy, so the default is "use VPN".
        "final": "proxy",
        "rules": [
            # 1. Ads & trackers → block (highest priority).
            {
                "rule_set": ["geosite-category-ads-all"],
                "outbound": "block",
            },
            # 2. RU-blocked sites & IPs → proxy.
            #    These are Twitter, LinkedIn, Instagram, etc. — content
            #    blocked in Russia. Users *want* them tunneled.
            {
                "rule_set": [
                    "geosite-ru-blocked",
                    "geoip-ru-blocked",
                ],
                "outbound": "proxy",
            },
            # 3. Telegram is special: its IPs (149.154.x, 91.108.x) are
            #    *registered* as Russian networks, so geoip-ru would
            #    catch them. But Telegram is blocked inside Russia, so
            #    sending it direct breaks the desktop client. Web-version
            #    works because it goes through the proxy domain rule
            #    (web.telegram.org doesn't match any direct rule).
            #    This rule must come before geoip-ru below.
            {
                "rule_set": [
                    "geosite-telegram",
                    "geoip-telegram",
                ],
                "outbound": "proxy",
            },
            # 4. RU services that work better/only with a Russian IP.
            #    Banks, gov, medicine, ecommerce, plus the catch-all
            #    `geoip-ru`.
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
    """Build a single remote rule-set definition.

    `download_detour: proxy` ensures the client downloads rule-sets THROUGH
    the VPN. This is critical for users behind whitelisting — GitHub may
    be unreachable directly, but the VPN tunnel still works.
    """
    return {
        "tag": f"{kind}-{tag}",
        "type": "remote",
        "format": "binary",
        "url": _ruleset_url(kind, tag),
        "download_detour": "proxy",
    }
