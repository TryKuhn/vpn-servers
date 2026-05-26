from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    server_ip: str
    server_port: int
    sni: str
    public_key: str
    short_id: str

    country_flag: str = "🇫🇮"
    server_tag: str = "VPN"

    xray_api_addr: str = "127.0.0.1:10085"
    xray_inbound_tag: str = "vless-in"

    server_domain: str = ""

    data_dir: Path = field(default_factory=lambda: Path("/data"))

    subscription_base_url: str = "http://localhost:8080"

    @classmethod
    def from_env(cls) -> Settings:
        """Build Settings from environment variables."""
        return cls(
            server_ip=_require_env("SERVER_IP"),
            server_port=int(_require_env("SERVER_PORT")),
            sni=_require_env("SNI"),
            public_key=_require_env("PUBLIC_KEY"),
            short_id=_require_env("SHORT_ID"),
            country_flag=os.environ.get("COUNTRY_FLAG", "🇫🇮"),
            server_tag=os.environ.get("SERVER_TAG", "VPN"),
            xray_api_addr=os.environ.get("XRAY_API_ADDR", "127.0.0.1:10085"),
            xray_inbound_tag=os.environ.get("XRAY_INBOUND_TAG", "vless-in"),
            server_domain=os.environ.get("NGINX_DOMAIN", ""),
            data_dir=Path(os.environ.get("DATA_DIR", "/data")),
            subscription_base_url=os.environ.get(
                "SUBSCRIPTION_BASE_URL", "http://localhost:8080"
            ),
        )

    @property
    def subscription_url(self) -> str:
        """Base URL for constructing per-user subscription links."""
        return self.subscription_base_url.rstrip("/")

    @property
    def users_db_path(self) -> Path:
        """Absolute path to users.json."""
        return self.data_dir / "users.json"

    @property
    def xray_config_path(self) -> Path:
        """Absolute path to the rendered xray config.json."""
        return self.data_dir / "xray" / "config.json"


def _require_env(name: str) -> str:
    """Return the value of a required environment variable, raising RuntimeError if missing or empty."""
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            f"Check your .env file or docker-compose.yml env_file directive."
        )
    return value
