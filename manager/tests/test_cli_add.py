"""Tests for the `add` CLI command, focusing on output formatting."""

from __future__ import annotations

import pytest

from vpn_manager.cli.commands.add import _print_multiple_users, _print_single_user
from vpn_manager.config import Settings
from vpn_manager.models.user import User


def test_single_user_output_contains_subscription_url(
    alice: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """Single user output highlights subscription URL as primary."""
    _print_single_user(alice, settings)
    out = capsys.readouterr().out

    assert "✓ User 'alice' created." in out
    assert "Subscription URL" in out
    # The subscription URL itself
    expected_sub_url = f"{settings.subscription_url}/sub/{alice.subscription_token}"
    assert expected_sub_url in out


def test_single_user_output_also_includes_legacy_vless_link(
    alice: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy VLESS link is still shown for backwards compat."""
    _print_single_user(alice, settings)
    out = capsys.readouterr().out

    assert "VLESS link" in out
    assert f"vless://{alice.uuid}" in out


def test_single_user_output_contains_qr(
    alice: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """Single user output includes a QR code (encoding the subscription URL)."""
    _print_single_user(alice, settings)
    out = capsys.readouterr().out

    assert "QR code" in out


def test_multiple_users_output_lists_subscription_urls(
    alice: User, bob: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """Multi-user output lists subscription URLs (compact, no QRs)."""
    _print_multiple_users([alice, bob], settings)
    out = capsys.readouterr().out

    assert "Created 2 user(s)" in out
    assert alice.name in out
    assert bob.name in out

    expected_alice_url = f"{settings.subscription_url}/sub/{alice.subscription_token}"
    expected_bob_url = f"{settings.subscription_url}/sub/{bob.subscription_token}"
    assert expected_alice_url in out
    assert expected_bob_url in out


def test_multiple_users_output_does_not_render_qr(
    alice: User, bob: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """For multi-user output, no QR codes — just compact links."""
    _print_multiple_users([alice, bob], settings)
    out = capsys.readouterr().out

    line_count = out.count("\n")
    assert line_count < 15, (
        f"Expected compact output, got {line_count} lines. "
        f"Did we accidentally render QRs?"
    )
