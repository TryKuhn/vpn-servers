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
    return {
        "mixed-port": 7890,
        "mode": "rule",
        "log-level": "warning",
        "ipv6": False,
        "allow-lan": False,
        "dns": _dns_section(),
        "proxies": [_proxy_outbound(user, settings)],
        "proxy-groups": _proxy_groups(),
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


def _proxy_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """Build the VLESS+Reality outbound — the actual VPN connection.

    Field layout follows Mihomo's clash YAML schema. Reality is
    expressed via `reality-opts`, distinct from sing-box's `tls.reality`
    and from xray's `streamSettings.realitySettings`.
    """
    return {
        "name": "TryKuhnVpn",
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


def _proxy_groups() -> list[dict[str, Any]]:
    """Single 'PROXY' group containing our VPN node + DIRECT escape."""
    return [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": ["TryKuhnVpn", "DIRECT"],
        }
    ]


def _rule_providers() -> dict[str, Any]:
    """Remote rule-set definitions.

    All sourced from MetaCubeX/meta-rules-dat (official Mihomo geo data).
    Format `mrs` is Mihomo's compact binary format.
    """
    return {
        "ads": _remote_ruleset_domain(
            url=_ruleset_url("geosite", "category-ads-all"),
        ),
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
    """Routing rules, evaluated top-to-bottom (first match wins).

    GEOIP rules use Mihomo's built-in geoip.dat rather than rule-providers
    — they're available everywhere and don't need separate downloads.

    `no-resolve` is used ONLY on the `private` rule. For `telegram` and
    `RU`, traffic typically arrives as a domain (not a raw IP), so
    skipping DNS resolution would make those rules never match for
    domain connections. The `private` case is different: RFC1918 traffic
    is always raw IP, so DNS resolution is unnecessary.
    """
    return [
        # 0. GitHub → DIRECT (whitelist before ads-rejection).
        #    MetaCubeX category-ads-all blocks `collector.github.com`,
        #    which breaks `git push` for users running our VPN client
        #    on the same machine they develop on. Whitelisting all of
        #    github.com is a reasonable trade-off: it's developer
        #    infrastructure, not a typical "ads/tracking" target.
        "DOMAIN-SUFFIX,github.com,PROXY",
        # RU-specific domains where geoip:RU misses (e.g. Ozon)
        "DOMAIN-SUFFIX,ozon.ru,DIRECT",
        "DOMAIN-SUFFIX,ozone.ru,DIRECT",
        "DOMAIN-SUFFIX,ozonusercontent.com,DIRECT",
        # 1. Ads & trackers → REJECT.
        "RULE-SET,ads,REJECT",
        # 2. Telegram → PROXY. DCs are RU-registered but blocked inside
        #    Russia, so direct routing breaks the desktop client.
        "GEOIP,telegram,PROXY",
        # 3. Private addresses → DIRECT (RFC1918 etc.). no-resolve is
        #    safe here: private addresses arrive as raw IPs, not domains.
        "GEOIP,private,DIRECT,no-resolve",
        # 4. Russian IPs → DIRECT. Catches gosuslugi/sber/banks/medicine/
        #    ecommerce by IP. Mihomo will resolve the domain to check the
        #    target IP against geoip:RU.
        "GEOIP,RU,DIRECT",
        # 5. Everything else → through VPN.
        "MATCH,PROXY",
    ]
