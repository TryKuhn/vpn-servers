"""Tests for vpn_manager.utils.qr."""

from __future__ import annotations

from vpn_manager.utils.qr import render_qr_to_terminal


def test_render_returns_non_empty_string() -> None:
    out = render_qr_to_terminal("hello")
    assert out
    assert isinstance(out, str)


def test_render_is_multiline() -> None:
    out = render_qr_to_terminal("hello world")
    assert out.count("\n") > 5  # QR is at least a few lines tall


def test_render_handles_long_input() -> None:
    """A typical VLESS link is ~250 chars; make sure it doesn't crash."""
    long_text = "vless://" + "a" * 300
    out = render_qr_to_terminal(long_text)
    assert out
