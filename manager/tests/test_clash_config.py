"""Unit tests for vpn_manager.utils.clash_config."""

from __future__ import annotations

import yaml

from vpn_manager.config import Settings
from vpn_manager.models.user import User
from vpn_manager.utils.clash_config import build_client_config, render_yaml


def test_config_top_level_keys(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    expected = {
        "mixed-port",
        "mode",
        "log-level",
        "ipv6",
        "allow-lan",
        "dns",
        "proxies",
        "proxy-groups",
        "rule-providers",
        "rules",
    }
    assert set(config.keys()) == expected


def test_mode_is_rule(alice: User, settings: Settings) -> None:
    """Mode 'rule' is required for our routing rules to take effect."""
    config = build_client_config(alice, settings)
    assert config["mode"] == "rule"


def test_proxy_is_vless_with_user_uuid(
    alice: User, settings: Settings
) -> None:
    config = build_client_config(alice, settings)
    proxy = config["proxies"][0]

    assert proxy["type"] == "vless"
    assert proxy["uuid"] == alice.uuid
    assert proxy["server"] == settings.server_ip
    assert proxy["port"] == settings.server_port
    assert proxy["flow"] == "xtls-rprx-vision"


def test_proxy_uses_reality(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    proxy = config["proxies"][0]

    assert proxy["tls"] is True
    assert proxy["servername"] == settings.sni
    assert proxy["client-fingerprint"] == "chrome"
    assert proxy["reality-opts"]["public-key"] == settings.public_key
    assert proxy["reality-opts"]["short-id"] == settings.short_id


def test_proxy_group_contains_proxy_and_direct(
    alice: User, settings: Settings
) -> None:
    """Users can manually switch to DIRECT in client UI if needed."""
    config = build_client_config(alice, settings)
    group = config["proxy-groups"][0]

    assert group["name"] == "PROXY"
    assert "TryKuhnVpn" in group["proxies"]
    assert "DIRECT" in group["proxies"]


def test_rules_have_match_proxy_last(
    alice: User, settings: Settings
) -> None:
    """Final fallback rule must be MATCH,PROXY (everything else → VPN)."""
    config = build_client_config(alice, settings)
    rules = config["rules"]
    assert rules[-1] == "MATCH,PROXY"


def test_ads_rule_rejects(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["rules"]
    assert "RULE-SET,ads,REJECT" in rules


def test_telegram_routed_through_proxy(
    alice: User, settings: Settings
) -> None:
    """Telegram IPs are RU-registered but blocked in Russia."""
    config = build_client_config(alice, settings)
    rules = config["rules"]
    assert "GEOIP,telegram,PROXY,no-resolve" in rules


def test_telegram_rule_comes_before_geoip_ru(
    alice: User, settings: Settings
) -> None:
    """Order matters: Telegram → PROXY must come before RU → DIRECT,
    otherwise Telegram IPs get sent direct and fail."""
    config = build_client_config(alice, settings)
    rules = config["rules"]

    tg_idx = next(
        i for i, r in enumerate(rules) if "telegram" in r.lower()
    )
    ru_idx = next(
        i for i, r in enumerate(rules) if r.startswith("GEOIP,RU,")
    )
    assert tg_idx < ru_idx


def test_private_addresses_direct(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["rules"]
    assert "GEOIP,private,DIRECT,no-resolve" in rules


def test_ru_ips_direct(alice: User, settings: Settings) -> None:
    config = build_client_config(alice, settings)
    rules = config["rules"]
    assert "GEOIP,RU,DIRECT,no-resolve" in rules


def test_ads_rule_provider_is_remote_mrs(
    alice: User, settings: Settings
) -> None:
    config = build_client_config(alice, settings)
    ads = config["rule-providers"]["ads"]
    assert ads["type"] == "http"
    assert ads["format"] == "mrs"
    assert ads["behavior"] == "domain"
    assert ads["url"].endswith(".mrs")
    assert "MetaCubeX/meta-rules-dat" in ads["url"]


def test_render_yaml_returns_valid_yaml(
    alice: User, settings: Settings
) -> None:
    """The rendered string must round-trip through yaml.safe_load."""
    rendered = render_yaml(alice, settings)
    parsed = yaml.safe_load(rendered)

    assert parsed["mode"] == "rule"
    assert parsed["proxies"][0]["uuid"] == alice.uuid


def test_render_yaml_does_not_use_python_anchors(
    alice: User, settings: Settings
) -> None:
    """YAML anchors (&foo, *foo) confuse some clients. Avoid them."""
    rendered = render_yaml(alice, settings)
    assert "&" not in rendered
    assert " *" not in rendered  # leading space avoids matching `*.mrs` etc
