"""Tests for vpn_manager.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from vpn_manager.config import Settings


def test_from_env_reads_required_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SERVER_IP", "1.2.3.4")
    monkeypatch.setenv("SERVER_PORT", "443")
    monkeypatch.setenv("SNI", "example.com")
    monkeypatch.setenv("PUBLIC_KEY", "pubkey")
    monkeypatch.setenv("SHORT_ID", "shortid")

    s = Settings.from_env()

    assert s.server_ip == "1.2.3.4"
    assert s.server_port == 443
    assert s.sni == "example.com"
    assert s.public_key == "pubkey"
    assert s.short_id == "shortid"


def test_from_env_uses_optional_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SERVER_IP", "SERVER_PORT", "SNI", "PUBLIC_KEY", "SHORT_ID"):
        monkeypatch.setenv(name, "x" if name != "SERVER_PORT" else "443")
    monkeypatch.delenv("COUNTRY_FLAG", raising=False)
    monkeypatch.delenv("SERVER_TAG", raising=False)

    s = Settings.from_env()

    assert s.country_flag == "🇫🇮"
    assert s.server_tag == "VPN"
    assert s.xray_api_addr == "127.0.0.1:10085"


def test_from_env_raises_on_missing_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SERVER_IP", raising=False)

    with pytest.raises(RuntimeError, match="SERVER_IP"):
        Settings.from_env()


def test_derived_paths(settings: Settings, tmp_path: Path) -> None:
    assert settings.users_db_path == tmp_path / "users.json"
    assert settings.xray_config_path == tmp_path / "xray" / "config.json"


def test_settings_is_frozen(settings: Settings) -> None:
    with pytest.raises(AttributeError):
        settings.server_ip = "9.9.9.9"  # type: ignore[misc]
