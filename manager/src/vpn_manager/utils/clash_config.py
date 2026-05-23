from __future__ import annotations

from typing import Any

import yaml

from vpn_manager.config import Settings
from vpn_manager.models.user import User

_RULESET_BASE = (
    "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo"
)


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a MetaCubeX rule-set URL for the given geo kind and tag."""
    return f"{_RULESET_BASE}/{kind}/{tag}.mrs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete Mihomo (Clash Meta) client config for the given user."""
    proxies = (
        [_ws_proxy_outbound(user, settings), _reality_proxy_outbound(user, settings)]
        if settings.ws_domain and settings.ws_path
        else [_reality_proxy_outbound(user, settings)]
    )
    return {
        "mixed-port": 7890,
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "allow-lan": False,
        "dns": _dns_section(),
        "proxies": proxies,
        "proxy-groups": _proxy_groups([p["name"] for p in proxies]),
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


def _ws_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket outbound via Cloudflare Tunnel."""
    return {
        "name": "TryKuhnVpn",
        "type": "vless",
        "server": settings.ws_domain,
        "port": settings.ws_port,
        "uuid": user.uuid,
        "network": "ws",
        "tls": True,
        "udp": True,
        "servername": settings.ws_domain,
        "client-fingerprint": "chrome",
        "ws-opts": {
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.ws_domain},
        },
    }


def _reality_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server, no CDN."""
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
    """Single PROXY group containing all VPN nodes plus a DIRECT escape hatch."""
    return [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": proxy_names + ["DIRECT"],
        }
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
        "ru-direct": {
            "type": "http",
            "behavior": "domain",
            "format": "mrs",
            "url": "https://github.com/itdoginfo/allow-domains/releases/latest/download/russia_outside_domain.mrs",
            "interval": 86400,
            "path": "./rule-providers/ru-direct.mrs",
        },
    }


def _rules() -> list[str]:
    """Routing rules evaluated top-to-bottom, first match wins."""
    return [
        "RULE-SET,ads,REJECT",
        "RULE-SET,ru-direct,DIRECT",
        "GEOIP,telegram,PROXY",
        "GEOIP,private,DIRECT,no-resolve",
        "GEOIP,RU,DIRECT",
        "MATCH,PROXY",
    ]
