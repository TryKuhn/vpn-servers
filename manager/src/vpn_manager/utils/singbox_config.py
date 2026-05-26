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
    proxy_tags: list[str] = []
    outbounds: list[dict[str, Any]] = []

    # Primary WS: nginx direct — full bandwidth, no CDN throttling
    if settings.server_domain and settings.ws_path:
        outbounds.append(_ws_nginx_outbound(user, settings))
        proxy_tags.append("proxy-ws")

    # Fallback WS: Cloudflare Tunnel — bypasses ISP blocks on server IP
    if settings.cloudflare_ws_domain and settings.ws_path:
        outbounds.append(_ws_cf_outbound(user, settings))
        proxy_tags.append("proxy-cf")

    outbounds.append(_reality_outbound(user, settings))
    proxy_tags.append("reality-proxy")

    # urltest: Reality only — WS/CF identified by ISP DPI, large traffic throttled
    reality_tags = [t for t in proxy_tags if t == "reality-proxy"]
    auto_tags = reality_tags if reality_tags else proxy_tags
    outbounds.append({
        "type": "urltest",
        "tag": "auto",
        "outbounds": auto_tags,
        "url": _TEST_URL,
        "interval": "5m",
        "tolerance": 50,
    })

    # selector: manual override, defaults to auto
    outbounds.append({
        "type": "selector",
        "tag": "proxy",
        "outbounds": ["auto"] + proxy_tags + ["direct"],
        "default": "auto",
    })

    outbounds += [
        {"type": "direct", "tag": "direct"},
        {"type": "block", "tag": "block"},
    ]

    return outbounds


def _ws_nginx_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket via nginx — direct to server, full bandwidth."""
    return {
        "type": "vless",
        "tag": "proxy-ws",
        "server": settings.server_domain,
        "server_port": settings.ws_port,
        "uuid": user.uuid,
        "transport": {
            "type": "ws",
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.server_domain},
        },
        "tls": {
            "enabled": True,
            "server_name": settings.server_domain,
            "utls": {
                "enabled": True,
                "fingerprint": "chrome",
            },
        },
    }


def _ws_cf_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+WebSocket via Cloudflare Tunnel — fallback when server IP is ISP-blocked."""
    return {
        "type": "vless",
        "tag": "proxy-cf",
        "server": settings.cloudflare_ws_domain,
        "server_port": settings.ws_port,
        "uuid": user.uuid,
        "transport": {
            "type": "ws",
            "path": f"/{settings.ws_path}",
            "headers": {"Host": settings.cloudflare_ws_domain},
        },
        "tls": {
            "enabled": True,
            "server_name": settings.cloudflare_ws_domain,
            "utls": {
                "enabled": True,
                "fingerprint": "chrome",
            },
        },
    }


def _reality_outbound(user: User, settings: Settings) -> dict[str, Any]:
    """VLESS+Reality outbound — direct connection to server, no CDN."""
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


_RU_DIRECT_DOMAINS: list[str] = [
    # Госуслуги
    "gosuslugi.ru",
    # ФНС
    "nalog.gov.ru",
    "nalog.ru",
    # Маркетплейсы
    "wildberries.ru",
    "wb.ru",
    "wbstatic.net",
    "ozon.ru",
    # Яндекс
    "yandex.ru",
    "yandex.com",
    "yandex.net",
    "yandex-team.ru",
    "ya.ru",
    "yastatic.net",
]


def _route_section() -> dict[str, Any]:
    """Route section: everything through VPN except explicitly listed Russian services."""
    return {
        "final": "proxy",
        "rules": [
            {
                "rule_set": ["geosite-category-ads-all"],
                "outbound": "block",
            },
            {
                "domain_suffix": _RU_DIRECT_DOMAINS,
                "outbound": "direct",
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
