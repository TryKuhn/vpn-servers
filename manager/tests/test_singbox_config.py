"""Unit tests for vpn_manager.utils.singbox_config."""

from __future__ import annotations

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.utils.singbox_config import build_client_config


def test_config_top_level_keys(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    assert set(config.keys()) == {"log", "outbounds", "route", "experimental"}


def test_three_outbounds_proxy_direct_block(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    tags = {o["tag"] for o in config["outbounds"]}
    assert tags == {"proxy", "direct", "block"}


def test_proxy_outbound_is_vless_with_user_uuid(
    alice: User, settings: Settings
) -> None:
    config = build_client_config(alice, settings)
    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")

    assert proxy["type"] == "vless"
    assert proxy["uuid"] == alice.uuid
    assert proxy["server"] == settings.server_ip
    assert proxy["server_port"] == settings.server_port
    assert proxy["flow"] == "xtls-rprx-vision"


def test_proxy_outbound_uses_reality(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    proxy = next(o for o in config["outbounds"] if o["tag"] == "proxy")

    tls = proxy["tls"]
    assert tls["enabled"] is True
    assert tls["server_name"] == settings.sni
    assert tls["utls"] == {"enabled": True, "fingerprint": "chrome"}
    assert tls["reality"]["enabled"] is True
    assert tls["reality"]["public_key"] == settings.public_key
    assert tls["reality"]["short_id"] == settings.short_id


def test_final_outbound_is_proxy(alice: User, settings: Settings) -> None:
    """Anything not caught by an explicit rule → proxy through VPN."""
    config = build_client_config(alice, settings)
    assert config["route"]["final"] == "proxy"


def test_ads_rule_blocks(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    ads = next(
        r for r in rules
        if "geosite-category-ads-all" in r.get("rule_set", [])
    )
    assert ads["outbound"] == "block"


def test_ru_blocked_goes_to_proxy(alice: User, settings: Settings) -> None:
    """Twitter, LinkedIn, etc. — must be tunneled."""
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    blocked = next(
        r for r in rules
        if "geosite-ru-blocked" in r.get("rule_set", [])
    )
    assert blocked["outbound"] == "proxy"


def test_ru_services_go_direct(alice: User, settings: Settings) -> None:
    """Banks, gov, medicine, ecommerce — use direct route."""
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    direct_categories = {
        "geosite-category-bank-ru",
        "geosite-category-gov-ru",
        "geosite-category-medicine-ru",
        "geosite-category-ecommerce-ru",
    }
    direct_rule = next(
        r for r in rules
        if direct_categories.issubset(set(r.get("rule_set", [])))
    )
    assert direct_rule["outbound"] == "direct"


def test_geoip_ru_goes_direct(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    geoip_rule = next(
        r for r in rules if "geoip-ru" in r.get("rule_set", [])
    )
    assert geoip_rule["outbound"] == "direct"


def test_private_addresses_go_direct(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    private = next(r for r in rules if r.get("ip_is_private") is True)
    assert private["outbound"] == "direct"


def test_rule_order_ads_before_ru_blocked(
    alice: User, settings: Settings
) -> None:
    """Ads must be checked first — even if hosted on RU-blocked domains."""
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    ads_idx = next(
        i for i, r in enumerate(rules)
        if "geosite-category-ads-all" in r.get("rule_set", [])
    )
    blocked_idx = next(
        i for i, r in enumerate(rules)
        if "geosite-ru-blocked" in r.get("rule_set", [])
    )
    assert ads_idx < blocked_idx


def test_all_referenced_rule_sets_have_definitions(
    alice: User, settings: Settings
) -> None:
    """Every rule_set tag in `rules` must be defined in `rule_set`."""
    config = build_client_config(alice, settings)

    referenced: set[str] = set()
    for rule in config["route"]["rules"]:
        referenced.update(rule.get("rule_set", []))

    defined = {rs["tag"] for rs in config["route"]["rule_set"]}
    assert referenced.issubset(defined), (
        f"undefined rule-sets: {referenced - defined}"
    )


def test_rule_set_definitions_are_remote(alice: User, settings: Settings) -> None:
    """All rule-sets must be remote with proxy detour."""
    config = build_client_config(alice, settings)

    for rs in config["route"]["rule_set"]:
        assert rs["type"] == "remote"
        assert rs["format"] == "binary"
        assert rs["url"].startswith("https://")
        # Critical: download via VPN, not directly
        assert rs["download_detour"] == "proxy"


def test_ruleset_urls_point_to_runetfreedom(
    alice: User, settings: Settings
) -> None:
    config = build_client_config(alice, settings)

    for rs in config["route"]["rule_set"]:
        assert "runetfreedom/russia-v2ray-rules-dat" in rs["url"]
        assert rs["url"].endswith(".srs")


def test_cache_file_enabled(alice: User, settings: Settings) -> None:
    """sing-box requires this for remote rule-sets to actually persist."""
    config = build_client_config(alice, settings)
    assert config["experimental"]["cache_file"]["enabled"] is True


def test_telegram_routed_through_proxy(alice: User, settings: Settings) -> None:
    """Telegram IPs are RU-registered but blocked in Russia.

    Must go through VPN, not direct, despite matching geoip-ru.
    """
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    tg_rule = next(
        r for r in rules
        if "geoip-telegram" in r.get("rule_set", [])
    )
    assert tg_rule["outbound"] == "proxy"


def test_telegram_rule_comes_before_geoip_ru(
        alice: User, settings: Settings
) -> None:
    """Order matters: Telegram → proxy must be checked BEFORE geoip-ru → direct,
    otherwise Telegram IPs (registered RU) get sent direct and fail."""
    config = build_client_config(alice, settings)
    rules = config["route"]["rules"]

    tg_idx = next(
        i for i, r in enumerate(rules)
        if "geoip-telegram" in r.get("rule_set", [])
    )
    geoip_ru_idx = next(
        i for i, r in enumerate(rules)
        if "geoip-ru" in r.get("rule_set", [])
    )
    assert tg_idx < geoip_ru_idx
