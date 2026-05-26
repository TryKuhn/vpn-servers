from __future__ import annotations

from typing import Any

import yaml

from vpn_manager.config import Settings
from vpn_manager.models.user import User

_TEST_URL = "http://www.gstatic.com/generate_204"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete Mihomo (Clash Meta) client config for the given user."""
    proxies = [_reality_proxy_outbound(user, settings)]
    proxy_names = [p["name"] for p in proxies]
    return {
        "mixed-port": 7890,
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "allow-lan": False,
        "dns": _dns_section(),
        "proxies": proxies,
        "proxy-groups": _proxy_groups(proxy_names),
        "rule-providers": _rule_providers(),
        "rules": _rules(),
    }


def render_yaml(user: User, settings: Settings) -> str:
    """Render the Mihomo config as a YAML string ready to serve over HTTP."""
    config = build_client_config(user, settings)
    rendered: str = yaml.safe_dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return rendered


def _dns_section() -> dict[str, Any]:
    """DNS configuration using redir-host mode so GEOIP rules match real destination IPs."""
    return {
        "enable": True,
        "ipv6": False,
        "enhanced-mode": "redir-host",
        "default-nameserver": ["8.8.8.8", "1.1.1.1"],
        "nameserver": [
            "https://1.1.1.1/dns-query",
            "https://8.8.8.8/dns-query",
        ],
    }


def _reality_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server."""
    return {
        "name": "TryKuhnVpn-Reality",
        "type": "vless",
        "server": settings.server_ip,
        "port": settings.server_port,
        "uuid": user.uuid,
        "network": "tcp",
        "tls": True,
        "udp": True,
        "flow": "xtls-rprx-vision",
        "servername": settings.sni,
        "client-fingerprint": "chrome",
        "reality-opts": {
            "public-key": settings.public_key,
            "short-id": settings.short_id,
        },
    }


def _proxy_groups(proxy_names: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "name": "Auto",
            "type": "url-test",
            "proxies": proxy_names,
            "url": _TEST_URL,
            "interval": 300,
            "tolerance": 50,
        },
        {
            "name": "PROXY",
            "type": "select",
            "proxies": ["Auto"] + proxy_names + ["DIRECT"],
        },
    ]


def _rule_providers() -> dict[str, Any]:
    """Remote MRS rule-sets fetched and cached by Mihomo on first start."""
    return {
        "ads": {
            "type": "http",
            "behavior": "domain",
            "format": "mrs",
            "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ads-all.mrs",
            "interval": 86400,
            "path": "./rule-providers/ads.mrs",
        },
    }


def _rules() -> list[str]:
    return [
        "RULE-SET,ads,REJECT",
        "GEOIP,private,DIRECT,no-resolve",
        "MATCH,PROXY",
    ]
