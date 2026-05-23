"""Generation of Mihomo (Clash Meta) client configurations.

Mihomo is the proxy core used by Clash Verge Rev (Windows/macOS/Linux),
Clash Meta For Android (CMFA), and other modern Clash-family clients.
Unlike sing-box config in V2RayTun/Hiddify (which strip our routing
rules), Mihomo *applies* routing from the subscription as part of its
core design.

Routing strategy (rules are evaluated top-to-bottom, first match wins):
  1. Ads & trackers           → REJECT
  2. Telegram IPs             → PROXY (RU-registered but blocked in RU)
  3. Private addresses        → DIRECT
  4. Russian IPs              → DIRECT (banks, gov, ecommerce — most are
                                here by IP if not by domain)
  5. Everything else (MATCH)  → PROXY

Rule-sets are downloaded from MetaCubeX/meta-rules-dat — the official
repository for Mihomo. They auto-update every 24 hours per `interval`.

The output is YAML, served as text/yaml. Mihomo clients import this URL
as a "subscription" and refresh it periodically.
"""

from __future__ import annotations

from typing import Any

import yaml

from vpn_manager.config import Settings
from vpn_manager.models.user import User

# Base URL for MetaCubeX rule-sets in MRS (binary) format.
# Confirmed available as of 2026-05-06: category-ads-all, ru, telegram,
# private. All return 200 OK on raw.githubusercontent.com.
_RULESET_BASE = (
    "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo"
)


def _ruleset_url(kind: str, tag: str) -> str:
    """Build a MetaCubeX rule-set URL.

    Args:
        kind: Either 'geosite' or 'geoip'.
        tag: Category name without the kind prefix, e.g. 'category-ads-all'.
    """
    return f"{_RULESET_BASE}/{kind}/{tag}.mrs"


def build_client_config(user: User, settings: Settings) -> dict[str, Any]:
    """Build a complete Mihomo client config for the given user."""
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
    """Render the config as a YAML string ready to serve over HTTP."""
    config = build_client_config(user, settings)
    # Use safe_dump with sort_keys=False to preserve our intentional
    # ordering (top-level fields like proxies before rules feels natural).
    rendered: str = yaml.safe_dump(
        config,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return rendered


def _dns_section() -> dict[str, Any]:
    """DNS configuration.

    We use redir-host mode (not fake-ip) so that GEOIP rules can match
    the real destination IP of each domain. With fake-ip mode, all
    domains resolve to 198.18.0.x and GEOIP,RU never matches — sites
    like ozon.ru that aren't on a RU CDN get sent through PROXY by
    fallthrough to MATCH.

    redir-host is slower (real DNS round-trip per domain), but correct.
    """
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
    """VLESS+WebSocket outbound — via Cloudflare Tunnel or CDN proxy."""
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
    """VLESS+Reality outbound — direct connection, no CDN."""
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
    """Single 'PROXY' group containing all VPN nodes + DIRECT escape."""
    return [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": proxy_names + ["DIRECT"],
        }
    ]


def _rule_providers() -> dict[str, Any]:
    """Remote MRS rule-sets fetched and cached by Mihomo.

    - ads: trackers and ad domains, REJECTed before any routing.
    - ru-direct: RU-only domains where geoip:RU misses
      (Ozon's CDN, Госуслуги subdomains, Яндекс CDN, etc.).
      Replaces the manual DOMAIN-SUFFIX whitelist from v0.85.
    """
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


def _remote_ruleset_domain(url: str) -> dict[str, Any]:
    """Build a single remote rule-set definition (domain behavior)."""
    return {
        "type": "http",
        "behavior": "domain",
        "format": "mrs",
        "url": url,
        "interval": 86400,
        "path": "./rule-providers/ads.mrs",
    }


def _rules() -> list[str]:
    """Routing rules in priority order.

    Order matters: manual overrides → ads-rejection →
    domain-based RU whitelist (geoip-miss fix) → geoip routing.
    """
    return [
        # Manual override: GitHub via PROXY (RU ISPs throttle direct).
        # "DOMAIN-SUFFIX,github.com,PROXY",
        # Manual override: MangaLib via DIRECT
        # "DOMAIN-SUFFIX,mangalib.me,DIRECT",
        # Ads & trackers.
        # "RULE-SET,ads,REJECT",
        # RU-domains where geoip:RU misses (e.g., Ozon CDN).
        # "RULE-SET,ru-direct,DIRECT",
        # Telegram via PROXY.
        # "GEOIP,telegram,PROXY",
        # Private networks (RFC1918) — no DNS resolve.
        # "GEOIP,private,DIRECT,no-resolve",
        # Other RU IPs → DIRECT.
        # "GEOIP,RU,DIRECT",
        # Everything else → PROXY.
        "MATCH,PROXY",
    ]
