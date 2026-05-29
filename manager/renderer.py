from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable
import yaml

from manager.config import Settings
from manager.models import Device


def ensure_dirs(settings: Settings) -> dict[str, Path]:
    base = Path(settings.rendered_dir)
    paths = {"base": base, "haproxy": base / "haproxy", "xray": base / "xray", "hysteria": base / "hysteria", "naive": base / "naive"}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def render_all(devices: list[Device], settings: Settings) -> None:
    paths = ensure_dirs(settings)
    (paths["xray"] / "config.json").write_text(json.dumps(build_xray_config(devices, settings), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (paths["hysteria"] / "config.yaml").write_text(yaml.safe_dump(build_hysteria_config(devices, settings), sort_keys=False, allow_unicode=True), encoding="utf-8")
    (paths["naive"] / "Caddyfile").write_text(build_caddyfile(devices, settings), encoding="utf-8")
    (paths["haproxy"] / "haproxy.cfg").write_text(build_haproxy_config(settings), encoding="utf-8")


def active_auth_devices(devices: Iterable[Device]) -> list[Device]:
    return [d for d in devices if d.enabled and d.user.enabled and d.revoked_at is None]


def build_xray_config(devices: list[Device], settings: Settings) -> dict:
    clients = [{"id": d.vless_uuid, "email": f"{d.user.name}.{d.name}"} for d in active_auth_devices(devices)]
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "tag": "vless-reality-xhttp", "listen": "0.0.0.0", "port": settings.xray_listen_port, "protocol": "vless",
            "settings": {"clients": clients, "decryption": "none"},
            "streamSettings": {"network": "xhttp", "security": "reality", "xhttpSettings": {"path": settings.xhttp_path, "mode": "auto"}, "realitySettings": {"show": False, "target": settings.reality_target, "serverNames": [settings.reality_sni], "privateKey": settings.reality_private_key, "shortIds": [settings.reality_short_id]}},
            "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"], "metadataOnly": False},
        }],
        "routing": {"domainStrategy": "UseIPv4", "rules": [
            {"type": "field", "domain": ["domain:anthropic.com", "domain:claude.ai"], "outboundTag": "warp"},
            {"type": "field", "protocol": ["bittorrent"], "outboundTag": "block"},
            {"type": "field", "port": "25,465,587", "network": "tcp", "outboundTag": "block"},
        ]},
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "block", "protocol": "blackhole"},
            {"tag": "warp", "protocol": "socks", "settings": {"servers": [{"address": settings.warp_proxy_host, "port": settings.warp_proxy_port}]}},
        ],
    }


def build_hysteria_config(devices: list[Device], settings: Settings) -> dict:
    userpass = {d.hysteria_username: d.hysteria_password for d in active_auth_devices(devices)}
    if not userpass:
        userpass[settings.fallback_auth_username] = settings.fallback_auth_password
    return {
        "listen": ":443", "tls": {"cert": settings.tls_cert, "key": settings.tls_key}, "auth": {"type": "userpass", "userpass": userpass},
        "sniff": {"enable": True, "timeout": "2s", "tcpPorts": "80,443", "udpPorts": "all"},
        "outbounds": [
            {"name": "direct"},
            {"name": "warp", "type": "socks5", "socks5": {"addr": f"{settings.warp_proxy_host}:{settings.warp_proxy_port}"}},
        ],
        "acl": {"inline": ["proxy(warp, domain:anthropic.com)", "proxy(warp, domain:claude.ai)", "reject(all, tcp/25)", "reject(all, tcp/465)", "reject(all, tcp/587)", "reject(all, tcp/6881-6999)", "reject(all, udp/6881-6999)", "direct(all)"]},
        "masquerade": {"type": "proxy", "proxy": {"url": f"https://{settings.public_domain}", "rewriteHost": True}},
    }


def build_caddyfile(devices: list[Device], settings: Settings) -> str:
    auth_lines = [f"        basic_auth {d.naive_username} {d.naive_password}" for d in active_auth_devices(devices)]
    if not auth_lines:
        auth_lines.append(f"        basic_auth {settings.fallback_auth_username} {settings.fallback_auth_password}")
    auth_block = "\n".join(auth_lines)
    return f"""{{
    order forward_proxy before reverse_proxy
    admin off
}}

:2443 {{
    tls {settings.tls_cert} {settings.tls_key}
    encode zstd gzip

    forward_proxy {{
{auth_block}
        ports 80 443
        hide_ip
        hide_via
        probe_resistance
    }}

    reverse_proxy manager:8080
}}
"""


def build_haproxy_config(settings: Settings) -> str:
    return f"""global
    log stdout format raw local0
    maxconn 4096

defaults
    log global
    mode tcp
    option tcplog
    timeout connect 5s
    timeout client  2m
    timeout server  2m

frontend ft_https
    bind *:443
    mode tcp
    tcp-request inspect-delay 5s
    tcp-request content accept if {{ req.ssl_hello_type 1 }}

    acl sni_xray   req.ssl_sni -i {settings.reality_sni}
    acl sni_naive  req.ssl_sni -i {settings.naive_domain}
    acl sni_public req.ssl_sni -i {settings.public_domain}
    acl sni_sub    req.ssl_sni -i {settings.sub_domain}
    acl sni_hy     req.ssl_sni -i {settings.hysteria_domain}

    use_backend bk_xray  if sni_xray
    use_backend bk_naive if sni_naive
    use_backend bk_naive if sni_public
    use_backend bk_naive if sni_sub
    use_backend bk_naive if sni_hy
    default_backend bk_naive

frontend ft_http
    bind *:80
    mode http
    http-request return status 200 content-type text/plain string "ok\\n"

backend bk_xray
    mode tcp
    server xray xray:{settings.xray_listen_port} check

backend bk_naive
    mode tcp
    server naive naive:{settings.naive_listen_port} check
"""
