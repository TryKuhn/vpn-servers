from __future__ import annotations

from typing import Any

import yaml

from vpn_manager.config import Settings
from vpn_manager.models.user import User

_RULESET_BASE = (
    "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo"
)
_TEST_URL = "http://www.gstatic.com/generate_204"


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a MetaCubeX rule-set URL for the given geo kind and tag."""
    return f"{_RULESET_BASE}/{kind}/{tag}.mrs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete Mihomo (Clash Meta) client config for the given user."""
    proxies = _build_proxies(user, settings)
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


def _build_proxies(user: User, settings: Settings) -> list[dict[str, Any]]:
    proxies: list[dict[str, Any]] = []

    # Primary WS: nginx direct — full bandwidth, no CDN throttling
    if settings.server_domain and settings.ws_path:
        proxies.append(_ws_nginx_proxy_outbound(user, settings))

    # Fallback WS: Cloudflare Tunnel — bypasses ISP blocks on server IP
    if settings.cloudflare_ws_domain and settings.ws_path:
        proxies.append(_ws_cf_proxy_outbound(user, settings))

    proxies.append(_reality_proxy_outbound(user, settings))
    return proxies


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


def _ws_nginx_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket via nginx — direct to server, full bandwidth."""
    return {
        "name": "TryKuhnVpn",
        "type": "vless",
        "server": settings.server_domain,
        "port": settings.ws_port,
        "uuid": user.uuid,
        "network": "ws",
        "tls": True,
        "udp": True,
        "servername": settings.server_domain,
        "client-fingerprint": "chrome",
        "ws-opts": {
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.server_domain},
        },
    }


def _ws_cf_proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket via Cloudflare Tunnel — fallback when server IP is ISP-blocked."""
    return {
        "name": "TryKuhnVpn-CF",
        "type": "vless",
        "server": settings.cloudflare_ws_domain,
        "port": settings.ws_port,
        "uuid": user.uuid,
        "network": "ws",
        "tls": True,
        "udp": True,
        "servername": settings.cloudflare_ws_domain,
        "client-fingerprint": "chrome",
        "ws-opts": {
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.cloudflare_ws_domain},
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
    """Auto uses Reality only; PROXY Selector exposes WS/CF for manual use.

    WS and CF are excluded from Auto: ISP DPI identifies WebSocket traffic
    as a VPN and throttles large transfers (YouTube, etc.) while allowing
    Telegram (which ISPs whitelist). Reality evades DPI by impersonating
    Apple iCloud TLS, so it works for all traffic. WS/CF stay in PROXY
    for manual selection when the server IP is directly blocked by ISP.
    """
    reality_proxies = [n for n in proxy_names if n == "TryKuhnVpn-Reality"]
    auto_proxies = reality_proxies if reality_proxies else proxy_names
    return [
        {
            "name": "Auto",
            "type": "url-test",
            "proxies": auto_proxies,
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
    """Routing rules: everything through VPN except explicitly listed Russian services."""
    return [
        "RULE-SET,ads,REJECT",
        # Russian services that must work without VPN (gov portals, marketplaces).
        # Add new entries here when users report issues with a specific site.
        "DOMAIN-SUFFIX,gosuslugi.ru,DIRECT",
        "DOMAIN-SUFFIX,nalog.gov.ru,DIRECT",
        "DOMAIN-SUFFIX,nalog.ru,DIRECT",
        "DOMAIN-SUFFIX,wildberries.ru,DIRECT",
        "DOMAIN-SUFFIX,wb.ru,DIRECT",
        "DOMAIN-SUFFIX,wbstatic.net,DIRECT",
        "DOMAIN-SUFFIX,ozon.ru,DIRECT",
        "GEOSITE,yandex,DIRECT",
        "GEOIP,private,DIRECT,no-resolve",
        "MATCH,PROXY",
    ]
