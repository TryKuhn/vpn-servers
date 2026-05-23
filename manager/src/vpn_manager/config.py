"""Application configuration: settings loaded from environment.

Settings are immutable after creation. To use:

    >>> settings = Settings.from_env()
    >>> settings.users_db_path
    PosixPath('/data/users.json')
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime configuration for vpn-manager.

    All values are loaded from environment variables, with sensible defaults
    for development. In production (the docker container), values come from
    the .env file mounted via env_file in docker-compose.yml.
    """

    # --- Server identity (used in VLESS links) ------------------------------
    server_ip: str
    server_port: int
    sni: str
    public_key: str
    short_id: str

    # --- Cosmetics ----------------------------------------------------------
    country_flag: str = "🇫🇮"
    server_tag: str = "VPN"

    # --- Xray API endpoint --------------------------------------------------
    xray_api_addr: str = "127.0.0.1:10085"
    xray_inbound_tag: str = "vless-in"
    xray_ws_inbound_tag: str | None = None

    # --- WebSocket / Cloudflare endpoint ------------------------------------
    server_domain: str = ""
    ws_path: str = ""
    ws_port: int = 8443

    # --- File paths (resolved to absolute) ----------------------------------
    data_dir: Path = field(default_factory=lambda: Path("/data"))

    # --- Subscription server settings ---------------------------------------
    subscription_base_url: str = "http://localhost:8080"

    @classmethod
    def from_env(cls) -> Settings:
        """Build Settings from environment variables.

        Required env vars:
            SERVER_IP, SERVER_PORT, SNI, PUBLIC_KEY, SHORT_ID

        Optional:
            COUNTRY_FLAG, SERVER_TAG, XRAY_API_ADDR, XRAY_INBOUND_TAG, DATA_DIR
        """
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
            xray_ws_inbound_tag=os.environ.get("XRAY_WS_INBOUND_TAG") or None,
            server_domain=os.environ.get("NGINX_DOMAIN", ""),
            ws_path=os.environ.get("WS_PATH", ""),
            ws_port=int(os.environ.get("WS_PORT", "8443")),
            data_dir=Path(os.environ.get("DATA_DIR", "/data")),
            subscription_base_url=os.environ.get(
                "SUBSCRIPTION_BASE_URL", "http://localhost:8080"
            ),
        )

    @property
    def subscription_url(self) -> str:
        """Base for building per-user subscription URLs.

        e.g. settings.subscription_url + '/sub/' + token
        """
        return self.subscription_base_url.rstrip("/")

    # --- Derived paths ------------------------------------------------------

    @property
    def users_db_path(self) -> Path:
        """Path to the users database (users.json)."""
        return self.data_dir / "users.json"

    @property
    def xray_config_path(self) -> Path:
        """Path to the live xray config (rendered from template)."""
        return self.data_dir / "xray" / "config.json"


def _require_env(name: str) -> str:
    """Get an environment variable or raise with a clear error message."""
    value = os.environ.get(name)
    if value is None or value == "":
        raise RuntimeError(
            f"Required environment variable {name!r} is not set. "
            f"Check your .env file or docker-compose.yml env_file directive."
        )
    return value
