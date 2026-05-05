"""Unit tests for vpn_manager.utils.client_config."""

from __future__ import annotations

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.utils.client_config import build_client_config


def test_config_has_three_outbounds(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    tags = {o["tag"] for o in config["outbounds"]}
    assert tags == {"proxy", "direct", "block"}


def test_config_has_user_uuid_in_proxy(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")
    user_id = proxy["settings"]["vnext"][0]["users"][0]["id"]
    assert user_id == alice.uuid


def test_config_uses_server_settings(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")
    vnext = proxy["settings"]["vnext"][0]
    assert vnext["address"] == settings.server_ip
    assert vnext["port"] == settings.server_port

    reality = proxy["streamSettings"]["realitySettings"]
    assert reality["serverName"] == settings.sni
    assert reality["publicKey"] == settings.public_key
    assert reality["shortId"] == settings.short_id


def test_config_blocks_ads(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["routing"]["rules"]

    ads_rule = next(
        r for r in rules
        if r.get("domain") and "geosite:category-ads-all" in r["domain"]
    )
    assert ads_rule["outboundTag"] == "block"


def test_config_routes_ru_directly(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["routing"]["rules"]

    ru_ip_rule = next(
        r for r in rules
        if r.get("ip") and "geoip:ru" in r["ip"]
    )
    assert ru_ip_rule["outboundTag"] == "direct"


def test_config_default_route_is_proxy(alice: User, settings: Settings) -> None:
    """The fall-through rule should send traffic through the VPN."""
    config = build_client_config(alice, settings)
    rules = config["routing"]["rules"]

    # The last rule should be the catch-all -> proxy
    last_rule = rules[-1]
    assert last_rule["outboundTag"] == "proxy"
    # And it should match all networks (no domain/ip filter)
    assert "domain" not in last_rule
    assert "ip" not in last_rule
