from __future__ import annotations

from datetime import datetime, timezone
from manager.config import Settings
from manager.models import Device

RU_DIRECT_DOMAINS = [
    "gosuslugi.ru", "nalog.gov.ru", "mos.ru", "mosreg.ru", "zakupki.gov.ru",
    "sberbank.ru", "tbank.ru", "vtb.ru", "alfabank.ru", "yandex.ru",
    "yastatic.net", "vk.com", "vk.ru", "mail.ru", "ok.ru",
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


def build_singbox_subscription(device: Device, settings: Settings) -> dict:
    title = f"{settings.subscription_profile_title} / {device.user.name} / {device.name}"
    hysteria_password = f"{device.hysteria_username}:{device.hysteria_password}"
    return {
        "log": {"level": "warn", "timestamp": True},
        "dns": {
            "servers": [
                {"tag": "cloudflare", "address": "https://1.1.1.1/dns-query", "detour": "PROXY"},
                {"tag": "local", "address": "local"},
            ],
            "rules": [{"domain_suffix": RU_DIRECT_DOMAINS, "server": "local"}],
            "final": "cloudflare",
            "strategy": "prefer_ipv4",
        },
        "outbounds": [
            {"type": "selector", "tag": "PROXY", "outbounds": ["AUTO", "VLx-XHTTP", "Hysteria2", "NaiveProxy"], "default": "AUTO"},
            {"type": "urltest", "tag": "AUTO", "outbounds": ["VLx-XHTTP", "Hysteria2", "NaiveProxy"], "url": "https://www.gstatic.com/generate_204", "interval": "5m"},
            {
                "type": "vless", "tag": "VLx-XHTTP", "server": settings.public_domain, "server_port": settings.public_tcp_port,
                "uuid": device.vless_uuid,
                "tls": {"enabled": True, "server_name": settings.reality_sni, "utls": {"enabled": True, "fingerprint": settings.client_fingerprint}, "reality": {"enabled": True, "public_key": settings.reality_public_key, "short_id": settings.reality_short_id}},
                "transport": {"type": "xhttp", "path": settings.xhttp_path},
            },
            {"type": "hysteria2", "tag": "Hysteria2", "server": settings.hysteria_domain, "server_port": settings.public_udp_port, "password": hysteria_password, "tls": {"enabled": True, "server_name": settings.hysteria_domain}},
            {"type": "naive", "tag": "NaiveProxy", "server": settings.naive_domain, "server_port": settings.public_tcp_port, "username": device.naive_username, "password": device.naive_password, "tls": {"enabled": True, "server_name": settings.naive_domain}},
            {"type": "direct", "tag": "direct"},
            {"type": "block", "tag": "block"},
        ],
        "route": {
            "auto_detect_interface": True,
            "rules": [
                {"domain_suffix": RU_DIRECT_DOMAINS, "outbound": "direct"},
                {"geoip": ["ru"], "outbound": "direct"},
                {"protocol": ["bittorrent"], "outbound": "block"},
                {"port": [25, 465, 587], "network": "tcp", "outbound": "block"},
            ],
            "final": "PROXY",
        },
        "experimental": {"cache_file": {"enabled": True}},
        "_trykuhn": {"title": title, "device": device.name, "user": device.user.name},
    }
