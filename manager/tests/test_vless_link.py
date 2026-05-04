"""Tests for vpn_manager.utils.vless_link."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.utils.vless_link import build_vless_link


def test_link_starts_with_vless_scheme(alice: User, settings: Settings) -> None:
    link = build_vless_link(alice, settings)
    assert link.startswith("vless://")


def test_link_contains_uuid_at_host(alice: User, settings: Settings) -> None:
    link = build_vless_link(alice, settings)
    parsed = urlparse(link)

    assert parsed.username == alice.uuid
    assert parsed.hostname == settings.server_ip
    assert parsed.port == settings.server_port


def test_link_query_params(alice: User, settings: Settings) -> None:
    link = build_vless_link(alice, settings)
    params = parse_qs(urlparse(link).query)

    assert params["security"] == ["reality"]
    assert params["pbk"] == [settings.public_key]
    assert params["sni"] == [settings.sni]
    assert params["sid"] == [settings.short_id]
    assert params["flow"] == ["xtls-rprx-vision"]


def test_link_label_contains_flag_and_name(
    alice: User, settings: Settings
) -> None:
    link = build_vless_link(alice, settings)
    fragment = urlparse(link).fragment
    decoded = unquote(fragment)

    assert settings.country_flag in decoded
    assert alice.name in decoded
    assert settings.server_tag in decoded
