"""Tests for the `add` CLI command, focusing on output formatting."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from vpn_manager.cli.commands.add import _print_multiple_users, _print_single_user
from vpn_manager.config import Settings
from vpn_manager.models.user import User


def test_single_user_output_contains_link_and_qr(
    alice: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    _print_single_user(alice, settings)
    out = capsys.readouterr().out

    assert "✓ User 'alice' created." in out
    assert "VLESS link:" in out
    assert f"vless://{alice.uuid}@" in out
    assert "QR code" in out


def test_multiple_users_output_lists_all_links(
    alice: User, bob: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    _print_multiple_users([alice, bob], settings)
    out = capsys.readouterr().out

    assert "Created 2 user(s)" in out
    assert alice.name in out
    assert bob.name in out
    assert f"vless://{alice.uuid}" in out
    assert f"vless://{bob.uuid}" in out


def test_multiple_users_output_does_not_render_qr(
    alice: User, bob: User, settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    """For multi-user output, no QR codes — just compact links."""
    _print_multiple_users([alice, bob], settings)
    out = capsys.readouterr().out

    # QR codes use unicode block chars and are tall; if rendered, output
    # would be ~30+ lines. For 2 users it should be ~10 lines max.
    line_count = out.count("\n")
    assert line_count < 15, (
        f"Expected compact output, got {line_count} lines. "
        f"Did we accidentally render QRs?"
    )
