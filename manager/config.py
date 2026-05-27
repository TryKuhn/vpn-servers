from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    public_domain: str = "trykuhn.xyz"
    sub_domain: str = "trykuhn.xyz"
    naive_domain: str = "nv.trykuhn.xyz"
    hysteria_domain: str = "hy.trykuhn.xyz"

    public_tcp_port: int = 443
    public_udp_port: int = 443
    xray_listen_port: int = 1443
    naive_listen_port: int = 2443
    manager_port: int = 8080

    tls_cert: str = "/certs/fullchain.pem"
    tls_key: str = "/certs/privkey.pem"

    database_url: str = Field(default="postgresql+asyncpg://vpn:vpn@postgres:5432/vpn")

    reality_private_key: str = "change_me"
    reality_public_key: str = "change_me"
    reality_short_id: str = "change_me"
    reality_sni: str = "gateway.icloud.com"
    reality_target: str = "gateway.icloud.com:443"
    xhttp_path: str = "/assets/api"
    client_fingerprint: str = "chrome"

    subscription_base_url: str = "https://trykuhn.xyz/sub"
    subscription_profile_title: str = "TryKuhn VPN"
    server_country: str = "FI"

    fallback_auth_username: str = "fallback"
    fallback_auth_password: str = "change_me"

    rendered_dir: str = "rendered"


@lru_cache
def get_settings() -> Settings:
    return Settings()
