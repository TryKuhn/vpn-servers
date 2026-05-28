from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlencode

from manager.config import Settings
from manager.models import Device

RU_DIRECT_DOMAINS = [
    "gosuslugi.ru",
    "nalog.gov.ru",
    "mos.ru",
    "mosreg.ru",
    "zakupki.gov.ru",
    "sberbank.ru",
    "tbank.ru",
    "vtb.ru",
    "alfabank.ru",
    "yandex.ru",
    "yastatic.net",
    "vk.com",
    "vk.ru",
    "mail.ru",
    "ok.ru",
    "hse.ru",
]


def device_is_allowed(device: Device) -> bool:
    if not device.enabled or device.revoked_at is not None:
        return False

    user = device.user
    if not user.enabled:
        return False

    if user.expires_at is not None and user.expires_at <= datetime.now(timezone.utc):
        return False

    return True


def _own_domains(settings: Settings) -> list[str]:
    domains = [
        settings.public_domain,
        settings.sub_domain,
        settings.naive_domain,
        settings.hysteria_domain,
    ]
    return sorted({domain for domain in domains if domain})


def _base_dns(settings: Settings) -> dict[str, Any]:
    return {
        "servers": [
            {
                "tag": "local",
                "type": "local",
            }
        ],
        "rules": [
            {
                "domain_suffix": _own_domains(settings) + RU_DIRECT_DOMAINS,
                "server": "local",
            }
        ],
        "final": "local",
        "strategy": "prefer_ipv4",
    }


def _base_route(settings: Settings, final: str = "PROXY") -> dict[str, Any]:
    return {
        "auto_detect_interface": True,
        "rules": [
            {
                "domain_suffix": _own_domains(settings),
                "outbound": "direct",
            },
            {
                "domain_suffix": RU_DIRECT_DOMAINS,
                "outbound": "direct",
            },
            {
                "protocol": [
                    "bittorrent",
                ],
                "outbound": "block",
            },
            {
                "port": [
                    25,
                    465,
                    587,
                ],
                "network": "tcp",
                "outbound": "block",
            },
        ],
        "final": final,
    }


def build_naive_subscription(device: Device, settings: Settings) -> dict[str, Any]:
    return {
        "log": {
            "level": "warn",
            "timestamp": True,
        },
        "dns": _base_dns(settings),
        "outbounds": [
            {
                "type": "selector",
                "tag": "PROXY",
                "outbounds": [
                    "NaiveProxy",
                ],
                "default": "NaiveProxy",
            },
            {
                "type": "naive",
                "tag": "NaiveProxy",
                "server": settings.naive_domain,
                "server_port": settings.public_tcp_port,
                "username": device.naive_username,
                "password": device.naive_password,
                "tls": {
                    "enabled": True,
                    "server_name": settings.naive_domain,
                },
            },
            {
                "type": "direct",
                "tag": "direct",
            },
            {
                "type": "block",
                "tag": "block",
            },
        ],
        "route": _base_route(settings),
        "experimental": {
            "cache_file": {
                "enabled": True,
            }
        },
    }


def build_hysteria_subscription(device: Device, settings: Settings) -> dict[str, Any]:
    hysteria_password = f"{device.hysteria_username}:{device.hysteria_password}"

    return {
        "log": {
            "level": "warn",
            "timestamp": True,
        },
        "dns": _base_dns(settings),
        "outbounds": [
            {
                "type": "selector",
                "tag": "PROXY",
                "outbounds": [
                    "Hysteria2",
                ],
                "default": "Hysteria2",
            },
            {
                "type": "hysteria2",
                "tag": "Hysteria2",
                "server": settings.hysteria_domain,
                "server_port": settings.public_udp_port,
                # Hiddify/sing-box не принимает отдельное поле username.
                # Поэтому для server-side auth.type=userpass оставляем username:password.
                "password": hysteria_password,
                "tls": {
                    "enabled": True,
                    "server_name": settings.hysteria_domain,
                },
            },
            {
                "type": "direct",
                "tag": "direct",
            },
            {
                "type": "block",
                "tag": "block",
            },
        ],
        "route": _base_route(settings),
        "experimental": {
            "cache_file": {
                "enabled": True,
            }
        },
    }


def build_xray_xhttp_subscription(device: Device, settings: Settings) -> dict[str, Any]:
    return {
        "log": {
            "loglevel": "warning",
        },
        "inbounds": [
            {
                "tag": "socks-in",
                "listen": "127.0.0.1",
                "port": 10808,
                "protocol": "socks",
                "settings": {
                    "udp": True,
                },
            },
            {
                "tag": "http-in",
                "listen": "127.0.0.1",
                "port": 10809,
                "protocol": "http",
            },
        ],
        "outbounds": [
            {
                "tag": "VLx-XHTTP",
                "protocol": "vless",
                "settings": {
                    "vnext": [
                        {
                            "address": settings.public_domain,
                            "port": settings.public_tcp_port,
                            "users": [
                                {
                                    "id": str(device.vless_uuid),
                                    "encryption": "none",
                                }
                            ],
                        }
                    ]
                },
                "streamSettings": {
                    "network": "xhttp",
                    "security": "reality",
                    "xhttpSettings": {
                        "path": settings.xhttp_path,
                        "mode": "auto",
                    },
                    "realitySettings": {
                        "serverName": settings.reality_sni,
                        "fingerprint": settings.client_fingerprint,
                        "publicKey": settings.reality_public_key,
                        "shortId": settings.reality_short_id,
                    },
                },
            },
            {
                "tag": "direct",
                "protocol": "freedom",
            },
            {
                "tag": "block",
                "protocol": "blackhole",
            },
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "domain": [
                        f"domain:{domain}" for domain in _own_domains(settings)
                    ],
                    "outboundTag": "direct",
                },
                {
                    "type": "field",
                    "domain": [
                        f"domain:{domain}" for domain in RU_DIRECT_DOMAINS
                    ],
                    "outboundTag": "direct",
                },
                {
                    "type": "field",
                    "protocol": [
                        "bittorrent",
                    ],
                    "outboundTag": "block",
                },
                {
                    "type": "field",
                    "port": "25,465,587",
                    "network": "tcp",
                    "outboundTag": "block",
                },
            ],
        },
    }


def build_singbox_subscription(device: Device, settings: Settings) -> dict[str, Any]:
    return build_naive_subscription(device, settings)


def _country_flag(code: str) -> str:
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def build_hysteria2_uri(device: Device, settings: Settings) -> str:
    """Hysteria2 URI для V2RayTun и аналогов. userpass-auth передаётся как user:pass@ в URI."""
    params = urlencode({
        "sni": settings.hysteria_domain,
    })
    display_name = f"{_country_flag(settings.server_country)} {settings.subscription_profile_title} Hysteria @{device.user.name}{device.name}"
    name = quote(display_name, safe="")
    user = quote(device.hysteria_username, safe="")
    password = quote(device.hysteria_password, safe="")
    return f"hysteria2://{user}:{password}@{settings.hysteria_domain}:{settings.public_udp_port}?{params}#{name}"


def build_hysteria2_subscription(device: Device, settings: Settings) -> str:
    """Base64-encoded Hysteria2 URI — стандартный subscription формат."""
    uri = build_hysteria2_uri(device, settings)
    return base64.b64encode(uri.encode()).decode()


def build_vless_xhttp_uri(device: Device, settings: Settings) -> str:
    """VLESS URI для XHTTP+Reality — стандартный формат для v2ray-совместимых клиентов."""
    params = urlencode({
        "encryption": "none",
        "type": "xhttp",
        "path": settings.xhttp_path,
        "mode": "auto",
        "security": "reality",
        "sni": settings.reality_sni,
        "fp": settings.client_fingerprint,
        "pbk": settings.reality_public_key,
        "sid": settings.reality_short_id,
    })
    display_name = f"{_country_flag(settings.server_country)} {settings.subscription_profile_title} VLESS @{device.user.name}{device.name}"
    name = quote(display_name, safe="")
    return f"vless://{device.vless_uuid}@{settings.public_domain}:{settings.public_tcp_port}?{params}#{name}"


def build_vless_splithttp_uri(device: Device, settings: Settings) -> str:
    """VLESS URI с SplitHTTP+Reality — для sing-box-совместимых клиентов (Karing, NekoBox)."""
    params = urlencode({
        "encryption": "none",
        "type": "splithttp",
        "path": settings.xhttp_path,
        "security": "reality",
        "sni": settings.reality_sni,
        "fp": settings.client_fingerprint,
        "pbk": settings.reality_public_key,
        "sid": settings.reality_short_id,
    })
    display_name = f"{_country_flag(settings.server_country)} {settings.subscription_profile_title} VLESS @{device.user.name}{device.name}"
    name = quote(display_name, safe="")
    return f"vless://{device.vless_uuid}@{settings.public_domain}:{settings.public_tcp_port}?{params}#{name}"


def build_splithttp_subscription(device: Device, settings: Settings) -> str:
    uri = build_vless_splithttp_uri(device, settings)
    return base64.b64encode(uri.encode()).decode()


def build_v2ray_subscription(device: Device, settings: Settings) -> str:
    """Base64-encoded список URI — стандартный subscription формат для V2RayTun и аналогов."""
    uris = [
        build_vless_xhttp_uri(device, settings),
        build_hysteria2_uri(device, settings),
    ]
    return base64.b64encode("\n".join(uris).encode()).decode()


def build_karing_subscription(device: Device, settings: Settings) -> dict[str, Any]:
    """Sing-box JSON subscription для Karing и Hiddify: Hysteria2 + NaiveProxy."""
    flag = _country_flag(settings.server_country)
    title = settings.subscription_profile_title
    suffix = f"@{device.user.name}{device.name}"
    hysteria_password = f"{device.hysteria_username}:{device.hysteria_password}"

    return {
        "outbounds": [
            {
                "type": "hysteria2",
                "tag": f"{flag} {title} Hysteria {suffix}",
                "server": settings.hysteria_domain,
                "server_port": settings.public_udp_port,
                "password": hysteria_password,
                "tls": {
                    "enabled": True,
                    "server_name": settings.hysteria_domain,
                },
            },
            {
                "type": "http",
                "tag": f"{flag} {title} NaiveProxy {suffix}",
                "server": settings.naive_domain,
                "server_port": settings.public_tcp_port,
                "username": device.naive_username,
                "password": device.naive_password,
                "tls": {
                    "enabled": True,
                    "server_name": settings.naive_domain,
                },
            },
        ]
    }


def build_clash_meta_config(device: Device, settings: Settings) -> dict[str, Any]:
    """
    Clash Meta (Mihomo) YAML-конфиг: Hysteria2 + VLESS XHTTP+Reality + NaiveProxy.

    NaiveProxy выставляется как HTTP CONNECT proxy с TLS — Caddy forward_proxy
    принимает стандартный HTTP CONNECT, поэтому совместимость сохраняется.
    VLESS XHTTP+Reality требует Mihomo >= 1.19.
    """
    flag = _country_flag(settings.server_country)
    title = settings.subscription_profile_title
    suffix = f"@{device.user.name}{device.name}"

    name_hy = f"{flag} {title} Hysteria2 {suffix}"
    name_vless = f"{flag} {title} VLESS {suffix}"
    name_naive = f"{flag} {title} NaiveProxy {suffix}"
    all_proxy_names = [name_hy, name_vless, name_naive]

    hysteria_password = f"{device.hysteria_username}:{device.hysteria_password}"

    proxies = [
        {
            "name": name_hy,
            "type": "hysteria2",
            "server": settings.hysteria_domain,
            "port": settings.public_udp_port,
            "password": hysteria_password,
            "sni": settings.hysteria_domain,
            "skip-cert-verify": False,
        },
        {
            "name": name_vless,
            "type": "vless",
            "server": settings.public_domain,
            "port": settings.public_tcp_port,
            "uuid": str(device.vless_uuid),
            "network": "xhttp",
            "tls": True,
            "client-fingerprint": settings.client_fingerprint,
            "servername": settings.reality_sni,
            "reality-opts": {
                "public-key": settings.reality_public_key,
                "short-id": settings.reality_short_id,
            },
            "xhttp-opts": {
                "path": settings.xhttp_path,
                "mode": "auto",
            },
        },
        {
            "name": name_naive,
            "type": "http",
            "server": settings.naive_domain,
            "port": settings.public_tcp_port,
            "username": device.naive_username,
            "password": device.naive_password,
            "tls": True,
            "sni": settings.naive_domain,
            "skip-cert-verify": False,
        },
    ]

    proxy_groups = [
        {
            "name": "🚀 PROXY",
            "type": "select",
            "proxies": ["⚡ Auto"] + all_proxy_names + ["DIRECT"],
        },
        {
            "name": "⚡ Auto",
            "type": "url-test",
            "url": "http://www.gstatic.com/generate_204",
            "interval": 300,
            "tolerance": 50,
            "proxies": all_proxy_names,
        },
    ]

    own = _own_domains(settings)
    direct_domains = sorted(own) + RU_DIRECT_DOMAINS

    nameserver_policy = {
        f"+.{domain}": "system" for domain in direct_domains
    }

    rules = []
    for domain in direct_domains:
        rules.append(f"DOMAIN-SUFFIX,{domain},DIRECT")
    rules += [
        "DST-PORT,25,REJECT",
        "DST-PORT,465,REJECT",
        "DST-PORT,587,REJECT",
        "MATCH,🚀 PROXY",
    ]

    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "ipv6": False,
        "mode": "rule",
        "log-level": "warning",
        "unified-delay": True,
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "redir-host",
            "nameserver": ["8.8.8.8", "1.1.1.1"],
            "nameserver-policy": nameserver_policy,
        },
        "proxies": proxies,
        "proxy-groups": proxy_groups,
        "rules": rules,
    }