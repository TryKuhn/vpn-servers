from __future__ import annotations

from typing import Any

from vpn_manager.config import Settings
from vpn_manager.models.user import User

_RULESET_BASE = (
    "https://raw.githubusercontent.com/runetfreedom/"
    "russia-v2ray-rules-dat/release/sing-box"
)
_TEST_URL = "http://www.gstatic.com/generate_204"


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a remote rule-set URL for the given geo kind and tag."""
    return f"{_RULESET_BASE}/rule-set-{kind}/{kind}-{tag}.srs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete sing-box client config for the given user."""
    return {
        "log": {"level": "warn"},
        "outbounds": _build_outbounds(user, settings),
        "route": _route_section(),
        "experimental": {
            "cache_file": {"enabled": True}
        },
    }


def _build_outbounds(user: User, settings: Settings) -> list[dict[str, Any]]:
    outbounds: list[dict[str, Any]] = [
        _reality_outbound(user, settings),
        {
            "type": "urltest",
            "tag": "auto",
            "outbounds": ["reality-proxy"],
            "url": _TEST_URL,
            "interval": "5m",
            "tolerance": 50,
        },
        {
            "type": "selector",
            "tag": "proxy",
            "outbounds": ["auto", "reality-proxy", "direct"],
            "default": "auto",
        },
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"},
    ]
    return outbounds


def _reality_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server."""
    return {
        "type": "vless",
        "tag": "reality-proxy",
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
    """Route section: all traffic through VPN except ads (blocked) and private IPs."""
    return {
        "final": "proxy",
        "rules": [
            {
                "rule_set": ["geosite-category-ads-all"],
                "outbound": "block",
            },
            {
                "ip_is_private": True,
                "outbound": "direct",
            },
        ],
        "rule_set": [
            _remote_ruleset("geosite", "category-ads-all"),
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
